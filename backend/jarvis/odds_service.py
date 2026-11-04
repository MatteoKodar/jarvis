"""Beständigt papperslabb i DEMO. Ingen betalning, bookmakerinloggning eller HTTP."""
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from . import config
from .budget import RuleError
from .db import connect, event, uid
from .odds_lab import (POLICY, VERSION, Cost, ImportSnapshot, Result, Snapshot, Start,
                       analyze, canonical, digest, event_key, example_snapshot, settlement)


def clock():
    return datetime.now(timezone.utc)


def require_demo():
    if config.mode() != "DEMO":
        raise RuleError("Oddslabb är endast tillgängligt i DEMO. Verkliga spel är avstängda.")


def _load(c, run_id):
    row = c.execute("SELECT * FROM odds_lab_runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise RuleError("Oddsserien saknas.")
    try:
        policy = json.loads(row["policy"])
    except (ValueError, TypeError):
        raise RuleError("Oddsseriens regler har ogiltigt format eller kontrollsumma.") from None
    if digest(policy) != row["policy_hash"] or policy != POLICY:
        raise RuleError("Oddsseriens regelversion eller kontrollsumma kan inte verifieras.")
    records, previous = [], digest([row["id"], row["kind"], row["created"], row["policy_hash"]])
    for record in c.execute("SELECT * FROM odds_lab_records WHERE run_id=? ORDER BY seq", (run_id,)):
        try:
            payload = json.loads(record["payload"])
        except (ValueError, TypeError):
            raise RuleError("Oddsseriens historik har ogiltigt format eller kontrollsumma.") from None
        item = {"kind": record["kind"], "entity_id": record["entity_id"], "recorded_at": record["recorded_at"], "payload": payload}
        if record["previous_hash"] != previous or digest([previous, item]) != record["digest"]:
            raise RuleError("Oddsseriens historik har fel kontrollsumma.")
        previous = record["digest"]
        records.append({**item, "sha256": previous})
    if previous != row["head_hash"]:
        raise RuleError("Oddsseriens historik är ofullständig eller har fel kontrollsumma.")
    return {"id": row["id"], "kind": row["kind"], "created": row["created"], "policy": policy,
            "policy_hash": row["policy_hash"], "records": records, "head_hash": previous}


def _append(c, run_id, kind, entity_id, payload, at):
    run = _load(c, run_id)
    if c.execute("SELECT 1 FROM odds_lab_records WHERE run_id=? AND kind=? AND entity_id=?", (run_id, kind, entity_id)).fetchone():
        raise RuleError("Posten är redan registrerad. Den kan inte skrivas över eller spelas om.")
    item = {"kind": kind, "entity_id": entity_id, "recorded_at": at.isoformat(), "payload": payload}
    checksum = digest([run["head_hash"], item])
    c.execute("INSERT INTO odds_lab_records(run_id,kind,entity_id,recorded_at,payload,previous_hash,digest) VALUES(?,?,?,?,?,?,?)",
              (run_id, kind, entity_id, at.isoformat(), canonical(payload), run["head_hash"], checksum))
    c.execute("UPDATE odds_lab_runs SET head_hash=? WHERE id=?", (checksum, run_id))


def summarize(run, at=None):
    at = at or clock()
    matches, cost, profit, open_stake, peak, drawdown = {}, 0, 0, 0, 0, 0
    for record in run["records"]:
        payload = record["payload"]
        if record["kind"] == "snapshot":
            snapshot, decision = payload["snapshot"], payload["decision"]
            cost += snapshot["data_cost_ore"]
            matches[snapshot["event_id"]] = {"snapshot": snapshot, "decision": decision, "registered_at": record["recorded_at"],
                                             "settlement": None, "result": None}
            if decision["selected"]:
                open_stake += decision["stake_ore"]
        elif record["kind"] == "result":
            item = matches[payload["result"]["event_id"]]
            item.update(result=payload["result"], settlement=payload["settlement"])
            profit += payload["settlement"]["profit_ore"]
            if item["decision"]["selected"]:
                open_stake -= item["decision"]["stake_ore"]
        else:
            cost += payload["amount_ore"]
        # Realiserat netto; öppna positioners risk visas separat.
        net = profit - cost
        peak = max(peak, net)
        drawdown = max(drawdown, peak - net)
    values = list(matches.values())
    selected = [m for m in values if m["decision"]["selected"]]
    closed = [m for m in selected if m["settlement"]]
    resolved = [m for m in closed if m["settlement"]["state"] != "void"]
    stake = sum(m["decision"]["stake_ore"] for m in resolved)
    deadline = datetime.fromisoformat(run["created"]) + timedelta(days=POLICY["min_days_for_review"])
    gates = {"real_observations": run["kind"] == "forward", "window_finished": at >= deadline,
             "enough_settled": len(resolved) >= POLICY["min_settled_for_review"],
             "all_signals_resolved": bool(selected) and len(closed) == len(selected), "positive_reported_net": profit - cost > 0}
    if run["kind"] == "synthetic":
        status = "synthetic_only"
    elif at < deadline:
        status = "collecting"
    elif not gates["all_signals_resolved"] and selected:
        status = "awaiting_results"
    elif not gates["enough_settled"]:
        status = "insufficient_data"
    else:
        status = "positive_observation" if gates["positive_reported_net"] else "nonpositive_observation"
    return {"matches": values, "snapshot_count": len(values), "signal_count": len(selected), "settled_count": len(resolved),
            "open_count": len(selected) - len(closed), "void_count": len(closed) - len(resolved),
            "won_count": sum(m["settlement"]["state"] == "won" for m in closed),
            "lost_count": sum(m["settlement"]["state"] == "lost" for m in closed),
            "paper_profit_ore": profit, "reported_cost_ore": cost, "net_profit_ore": profit - cost,
            "open_stake_ore": open_stake, "available_ore": POLICY["initial_bankroll_ore"] + profit - cost - open_stake,
            "balance_ore": POLICY["initial_bankroll_ore"] + profit - cost,
            "settled_stake_ore": stake, "net_roi_bp": int((profit - cost) * 10000 // stake) if stake else None,
            "max_realized_drawdown_ore": drawdown, "observation_ends": deadline.isoformat(), "status": status, "gates": gates,
            "allows_real_money": False, "costs_verified": False, "availability_verified": False,
            "notice": "Positivt simulerat resultat bevisar inte framtida vinst. Manuell data och oddstillgänglighet är inte oberoende verifierade."}


def _request(action_id, request, execute):
    require_demo()
    request_hash = digest(request)
    with connect(True) as c:
        old = c.execute("SELECT * FROM odds_lab_actions WHERE action_id=?", (action_id,)).fetchone()
        if old:
            if old["request_hash"] != request_hash:
                raise RuleError("Åtgärds-ID:t är bundet till annat innehåll.")
            return json.loads(old["response"])
        if c.execute("SELECT state FROM settings WHERE id=1").fetchone()[0] != "running":
            raise RuleError("Oddslabb är pausat eller nödstoppat. Återuppta först.")
        result = execute(c)
        c.execute("INSERT INTO odds_lab_actions VALUES(?,?,?)", (action_id, request_hash, canonical(result)))
        event(c, "odds_lab", "Oddslabb: " + request["operation"] + ". Endast simulerade insatser.")
        return result


def _import(c, run_id, snapshot, at, synthetic=False):
    run = _load(c, run_id)
    if (run["kind"] == "synthetic") != synthetic:
        raise RuleError("Syntetiskt och verkligt observationsmaterial får inte blandas.")
    summary = summarize(run, at)
    if summary["snapshot_count"] >= POLICY["max_snapshots"]:
        raise RuleError("Seriens förhandsbestämda tak är nått.")
    if not synthetic:
        if any((urlsplit(q.source_url).hostname or "").endswith((".invalid", ".example", ".test")) or
               (urlsplit(q.source_url).hostname or "") in {"example.com", "example.net", "example.org", "localhost"}
               for q in snapshot.quotes):
            raise RuleError("Strukturmallens och reserverade exempeladresser får inte registreras som verkliga källor.")
        delay = (at - snapshot.captured_at).total_seconds()
        if not 0 <= delay <= POLICY["max_import_delay_seconds"]:
            raise RuleError("Verklig observation måste registreras inom 60 sekunder efter fångst, utan framtida tidsstämpel.")
        if at >= datetime.fromisoformat(run["created"]) + timedelta(days=POLICY["min_days_for_review"]):
            raise RuleError("Den låsta observationsperioden har avslutats. Endast resultat och kostnader kan kompletteras.")
        if snapshot.starts_at <= at + timedelta(seconds=POLICY["min_seconds_before_kickoff"]):
            raise RuleError("Observationen måste sparas mer än en minut före avspark.")
    key = event_key(snapshot)
    if any(event_key(Snapshot.model_validate(m["snapshot"])) == key or m["snapshot"]["event_id"] == snapshot.event_id for m in summary["matches"]):
        raise RuleError("Matchen är redan registrerad. Nytt match-ID ger inte en ny signal för samma match.")
    decision = analyze(snapshot, at, summary["available_ore"] - snapshot.data_cost_ore)
    _append(c, run_id, "snapshot", snapshot.event_id,
            {"snapshot": snapshot.model_dump(mode="json"), "decision": decision, "event_key": key}, at)


def _result(c, run_id, body, at, synthetic=False):
    run = _load(c, run_id)
    if (run["kind"] == "synthetic") != synthetic:
        raise RuleError("Resultat får inte blandas mellan exempel och observationsserie.")
    match = next((m for m in summarize(run, at)["matches"] if m["snapshot"]["event_id"] == body.event_id), None)
    if not match:
        raise RuleError("Matchen saknar en tidigare registrerad oddsobservation.")
    start = datetime.fromisoformat(match["snapshot"]["starts_at"])
    if body.finished_at > at or (body.status == "final" and body.finished_at < start + timedelta(minutes=90)):
        raise RuleError("Slutresultat kräver passerad ordinarie matchtid och får inte ligga i framtiden.")
    if body.finished_at < datetime.fromisoformat(match["registered_at"]):
        raise RuleError("Resultatet får inte föregå registreringen.")
    _append(c, run_id, "result", body.event_id,
            {"result": body.model_dump(mode="json", exclude={"action_id"}), "settlement": settlement(match["decision"], body)}, at)


def _synthetic(c, run_id):
    start = datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    for index in range(7):
        at = start + timedelta(days=index)
        data = example_snapshot(at)
        data.update(event_id=f"syntetisk-{index + 1}", home=f"Påhittat hemmalag {index + 1}", away=f"Påhittat bortalag {index + 1}", data_cost_ore=20)
        if index == 4:
            for quote in data["quotes"]:
                quote["updated_at"] = (at - timedelta(minutes=5)).isoformat()
        elif index == 5:
            data["quotes"] = data["quotes"][:3]
        elif index == 6:
            data["quotes"][0]["odds"]["home"] = 20000
        snapshot = Snapshot.model_validate(data)
        _import(c, run_id, snapshot, at, synthetic=True)
        result_at = snapshot.starts_at + timedelta(hours=2)
        result = Result(action_id="00000000-0000-0000-0000-000000000000", event_id=snapshot.event_id,
                        market="1x2_90min", status="final", home_score=2 if index % 2 == 0 else 0,
                        away_score=0 if index % 2 == 0 else 1, finished_at=result_at,
                        source_url="https://example.invalid/syntetiskt-resultat")
        _result(c, run_id, result, result_at, synthetic=True)


def start(body: Start):
    def execute(c):
        if body.policy_hash != digest(POLICY):
            raise RuleError("Provreglerna har ändrats. Läs in Oddslabb igen.")
        if body.kind == "forward":
            if c.execute("SELECT 1 FROM odds_lab_runs WHERE kind='forward'").fetchone():
                raise RuleError("En observationsserie finns redan. Öppna den; den kan inte återställas efter förluster.")
        if c.execute("SELECT COUNT(*) FROM odds_lab_runs").fetchone()[0] >= 50:
            raise RuleError("Arkivets tak på 50 serier är nått.")
        run_id, at = uid(), clock()
        policy_hash = digest(POLICY)
        c.execute("INSERT INTO odds_lab_runs VALUES(?,?,?,?,?,?)",
                  (run_id, body.kind, at.isoformat(), canonical(POLICY), policy_hash, digest([run_id, body.kind, at.isoformat(), policy_hash])))
        if body.kind == "synthetic":
            _synthetic(c, run_id)
        return {"id": run_id}
    return _request(body.action_id, {"operation": "start", **body.model_dump()}, execute)


def import_snapshot(run_id, body: ImportSnapshot):
    def execute(c):
        _import(c, run_id, body.snapshot, clock())
        return {"id": run_id}
    return _request(body.action_id, {"operation": "snapshot", "run_id": run_id, **body.model_dump(mode="json")}, execute)


def record_result(run_id, body: Result):
    def execute(c):
        _result(c, run_id, body, clock())
        return {"id": run_id}
    return _request(body.action_id, {"operation": "result", "run_id": run_id, **body.model_dump(mode="json")}, execute)


def record_cost(run_id, body: Cost):
    def execute(c):
        run = _load(c, run_id)
        if run["kind"] != "forward":
            raise RuleError("Exempelseriens innehåll är låst.")
        if sum(r["kind"] == "cost" for r in run["records"]) >= 100:
            raise RuleError("Tak för kompletterande kostnadsposter är nått.")
        _append(c, run_id, "cost", body.action_id, body.model_dump(exclude={"action_id"}), clock())
        return {"id": run_id}
    return _request(body.action_id, {"operation": "cost", "run_id": run_id, **body.model_dump()}, execute)


def get_run(run_id):
    require_demo()
    with connect() as c:
        run = _load(c, run_id)
    return {"run": run, "summary": summarize(run)}


def catalog():
    with connect() as c:
        runs = [dict(r) for r in c.execute("SELECT id,kind,created FROM odds_lab_runs ORDER BY created DESC,id DESC LIMIT 50")] if config.mode() == "DEMO" else []
    return {"version": VERSION, "policy": POLICY, "policy_hash": digest(POLICY), "runs": runs,
            "mode": config.mode(), "feed_connected": False, "real_money_enabled": False,
            "notice": "Regelbaserad fotbollsanalys. Ingen AI-agent, datatjänst eller spelintegration är ansluten till Oddslabb."}


def template():
    require_demo()
    return example_snapshot()
