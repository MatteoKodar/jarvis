"""En fast, uttryckligen obetald MediaWiki-operation bakom samma anropsgräns."""
import html
import json
import re
from .budget import RuleError
from .db import connect, now, uid, pack
from . import dispatch, external_http


async def search(task, *, model_operation=None):
    # Arkiverade verktyg nekas före modellreservation, med uppgift från databasen.
    with connect() as c:
        dispatch.authoritative(c, task, dispatch.WIKI)
    standalone = model_operation is None
    oid = None
    try:
        if standalone:
            # Direct calls also check and reserve model budget before Wikipedia.
            model_operation, _ = dispatch.prepare(task)
        oid, task = dispatch.prepare(task, dispatch.WIKI, model_operation=model_operation)
        params = {"action": "query", "list": "search", "srsearch": task["title"], "srlimit": 3, "format": "json"}
        dispatch.bind(oid, params)
        async with external_http.research_client(oid, params) as client:
            async with client.stream("GET", "https://sv.wikipedia.org/w/api.php", params=params,
                                     headers={"User-Agent": "JarvisMoneyLab/1.0 (local research prototype)"}) as response:
                response.raise_for_status()
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 100000:
                        raise RuleError("Researchsvaret överskred storleksgränsen.")
        items = json.loads(raw)["query"]["search"]
        if not isinstance(items, list) or len(items) > 3:
            raise RuleError("Researchsvaret överskred antalet tillåtna källor.")
        sources = []
        for item in items:
            page_id = int(item["pageid"])
            title = str(item["title"])
            snippet = html.unescape(re.sub(r"<[^>]*>", "", item.get("snippet", "")))
            if page_id <= 0 or len(title) > 300 or len(snippet) > 1500:
                raise RuleError("Researchmaterialet överskred resursgränsen; inget underlag kapas.")
            sources.append({"id": uid(), "url": f"https://sv.wikipedia.org/?curid={page_id}", "title": title,
                            "retrieved": now(), "origin": f"wikipedia:sv:{page_id}", "claim": snippet,
                            "kind": "Bakgrundskälla; ej verifierad betalningssignal"})
        with connect(True) as c:
            row = c.execute("SELECT state FROM operations WHERE id=?", (oid,)).fetchone()
            if row[0] != "possible_send":
                raise RuleError("Researchoperationen kräver granskning efter avbrott.")
            for s in sources:
                c.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)", (s["id"], task["id"], s["url"], s["title"], s["retrieved"], s["origin"], s["claim"], s["kind"]))
            c.execute("UPDATE operations SET state='completed',finished=?,uncertainty=NULL,result=? WHERE id=?",
                      (now(), pack(sources), oid))
        return sources
    except BaseException:
        dispatch.abort(oid)
        raise
    finally:
        if standalone:
            dispatch.abort(model_operation)
