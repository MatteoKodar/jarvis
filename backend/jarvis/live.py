"""Ett modellsteg bakom den beständiga anropsgränsen; inga verktyg eller handoffs."""
import os
from .budget import RuleError
from .models import AgentResult
from .roles import ROLES
from .research import search
from . import dispatch, external_http
from .dispatch import MAX_INPUT, MAX_OUTPUT, pricing, cost


def make_agents(model):
    from agents import Agent, ModelSettings
    from agents.retry import ModelRetrySettings
    return {key: Agent(name=role["name"], instructions=role["instructions"], model=model,
                       output_type=AgentResult, tools=[], model_settings=ModelSettings(
                           max_tokens=MAX_OUTPUT, store=False, retry=ModelRetrySettings(max_retries=0)))
            for key, role in ROLES.items()}


async def run(task):
    oid = None
    try:
        handle = {"id": task.get("id"), "run_id": task.get("run_id")}
        oid, task = dispatch.prepare(handle)
        frozen = dispatch.frozen(oid)
        sources = await search(handle, model_operation=oid) if "wikipedia_search" in ROLES[task["agent_id"]]["tools"] and task["phase"] == "work" else []
        if task["phase"] == "review" and task.get("parent_id"):
            sources = frozen["review_sources"]
        text = dispatch.payload(task, sources)
        dispatch.bind(oid, text)
        from agents import Runner, RunConfig, OpenAIResponsesModel, set_tracing_disabled
        from openai import AsyncOpenAI
        set_tracing_disabled(True)
        async with AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url="https://api.openai.com/v1",
                               max_retries=0, timeout=60, http_client=external_http.model_client(oid, text)) as client:
            model = OpenAIResponsesModel(model=frozen["price"]["model"], openai_client=client)
            result = await Runner.run(make_agents(model)[task["agent_id"]], text, max_turns=1,
                                      run_config=RunConfig(tracing_disabled=True, trace_include_sensitive_data=False))
        # Parsing failures inside the SDK leave unknown cost. A valid usage receipt
        # is settled once even when a later semantic check rejects the answer.
        output = AgentResult.model_validate(result.final_output)
        dispatch.complete(oid, output.model_dump(), result.context_wrapper.usage)
        allowed = {s["id"] for s in sources}
        for claim in output.claims:
            if not set(claim.source_ids).issubset(allowed):
                raise RuleError("Modellen refererade till en källa som inte hämtats.")
            if (claim.kind == "FAKTA" and not claim.source_ids) or claim.kind == "TESTRESULTAT":
                claim.kind = "ANTAGANDE"
        return output
    except BaseException:
        dispatch.abort(oid)
        raise
