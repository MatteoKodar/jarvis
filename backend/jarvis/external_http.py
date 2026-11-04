"""Versionsgranskade klienter. Testerna ersätter enbart innersta HTTP-transporten."""
import hashlib
import json
from importlib.metadata import version
import httpx
import httpx2
from .budget import RuleError
from . import dispatch

VERIFIED = {"openai-agents": "0.24.0", "openai": "3.35.1", "httpx": "0.28.1",
            "httpcore": "1.0.9", "httpx2": "2.13.1", "httpcore2": "2.13.1"}


def verified_versions():
    actual = {name: version(name) for name in VERIFIED}
    if actual != VERIFIED:
        raise RuleError("Klientversionerna saknar granskning; externa anrop är spärrade.")
    return actual


def model_transport():
    return httpx2.AsyncHTTPTransport(retries=0, http2=False, trust_env=False,
                                    limits=httpx2.Limits(max_connections=1, max_keepalive_connections=0))


def research_transport():
    return httpx.AsyncHTTPTransport(retries=0, http2=False, trust_env=False,
                                   limits=httpx.Limits(max_connections=1, max_keepalive_connections=0))


def validate_model(request, raw, frozen, text):
    body = json.loads(raw)
    if (str(request.url) != "https://api.openai.com/v1/responses" or request.method != "POST"
            or body.get("model") != frozen["price"]["model"] or body.get("stream", False) is not False
            or body.get("store") is not False or body.get("tools") != []
            or body.get("max_output_tokens") != dispatch.MAX_OUTPUT
            or body.get("instructions") != frozen["role"]["instructions"]
            or body.get("input") != [{"role": "user", "content": text}]
            or any(body.get(k) for k in ("background", "previous_response_id", "conversation", "prompt"))):
        fields = {"stream": body.get("stream", False) is False, "store": body.get("store") is False,
                  "tools": body.get("tools") == [], "max_output_tokens": body.get("max_output_tokens") == dispatch.MAX_OUTPUT,
                  "instructions": body.get("instructions") == frozen["role"]["instructions"],
                  "input": body.get("input") == [{"role": "user", "content": text}]}
        raise RuleError("Modelltransporten avviker från det tillåtna anropet: " + ",".join(k for k, v in fields.items() if not v))


class ModelBoundary(httpx2.AsyncBaseTransport):
    def __init__(self, oid, text):
        self.oid, self.text = oid, text
        self.frozen = dispatch.frozen(oid)
        self.inner = model_transport()

    async def handle_async_request(self, request):
        raw = await request.aread()
        validate_model(request, raw, self.frozen, self.text)
        dispatch.authorize(self.oid, hashlib.sha256(raw).hexdigest(), dispatch.digest(self.text))
        # No await between committed authorization and transport delegation.
        response = await self.inner.handle_async_request(request)
        # Bound receipt parsing prevents a missing SDK usage field becoming zero cost.
        data = bytearray()
        try:
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > 1000000:
                    raise RuleError("Modellsvaret överskred resursgränsen.")
        finally:
            await response.aclose()
        if 200 <= response.status_code < 300:
            receipt = json.loads(data)
            usage = receipt.get("usage") or {}
            if (receipt.get("status") != "completed" or receipt.get("model") != self.frozen["price"]["model"]
                    or type(usage.get("input_tokens")) is not int or type(usage.get("output_tokens")) is not int
                    or not 0 <= usage["input_tokens"] <= dispatch.MAX_INPUT
                    or not 0 <= usage["output_tokens"] <= dispatch.MAX_OUTPUT):
                raise RuleError("Modellsvaret saknar ett giltigt slutligt användningskvitto.")
        headers = dict(response.headers)
        # aiter_bytes already decoded Content-Encoding. Do not decode the body twice.
        for name in ("content-encoding", "content-length", "transfer-encoding"):
            headers.pop(name, None)
        return httpx2.Response(response.status_code, headers=headers, content=bytes(data),
                               request=request, extensions=response.extensions)

    async def aclose(self):
        await self.inner.aclose()


class ResearchBoundary(httpx.AsyncBaseTransport):
    def __init__(self, oid, params):
        self.oid, self.params = oid, {k: str(v) for k, v in params.items()}
        self.payload_hash = dispatch.digest(params)
        self.inner = research_transport()

    async def handle_async_request(self, request):
        if (request.method != "GET" or str(request.url.copy_with(query=None)) != "https://sv.wikipedia.org/w/api.php"
                or dict(request.url.params) != self.params or len(request.url.params.multi_items()) != len(self.params)):
            raise RuleError("Researchtransporten avviker från den fasta Wikipedia-integrationen.")
        dispatch.authorize(self.oid, dispatch.digest(str(request.url)), self.payload_hash)
        return await self.inner.handle_async_request(request)

    async def aclose(self):
        await self.inner.aclose()


def model_client(oid, text):
    return httpx2.AsyncClient(transport=ModelBoundary(oid, text), timeout=60, follow_redirects=False,
                             trust_env=False, auth=None)


def research_client(oid, params):
    return httpx.AsyncClient(transport=ResearchBoundary(oid, params), timeout=12, follow_redirects=False,
                            trust_env=False, auth=None)
