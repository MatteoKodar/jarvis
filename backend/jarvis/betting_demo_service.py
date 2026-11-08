"""Beständiga, atomiska demoövergångar. Ingen worker eller extern transport."""
import json
from typing import Literal

from pydantic import Field

from . import config
from . import demo_review
from .budget import RuleError
from .db import connect, now, uid
from .odds_lab import Action, canonical, digest
from .roles import ROLES
from .betting_demo import (SCENARIO_VERSION, SETTLEMENT_VERSION, build_scenario, validate_scenario,
                           analysis_input, analyze_scenario, settle_bet, summary)


class Decision(Action):
    decision: Literal["approved", "declined"]
    proposal_version: int = Field(strict=True, ge=1)
    proposal_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class ApprovedBatch(Action):
    proposal_version: int = Field(strict=True, ge=1)
    proposal_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


def require_demo():
    if config.mode() != "DEMO":
        raise RuleError("Bettingdemot är endast tillgängligt i DEMO. Inga riktiga spel stöds.")


def _load(c, session_id):
    row = c.execute("SELECT * FROM betting_demo_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise RuleError("Demo-omgången saknas.")
    value = dict(row)
    try:
        frozen = json.loads(value["frozen"])
        if digest(frozen) != value["frozen_hash"]:
            raise ValueError()
        value["frozen"] = frozen
        value["analysis"] = json.loads(value["analysis"]) if value["analysis"] else None
        if value["analysis"] is not None and not isinstance(value["analysis"], dict):
            raise ValueError()
        if value["analysis"] is not None:
            analysis = value["analysis"]
            if digest({k: v for k, v in analysis.items() if k != "proposal_hash"}) != analysis["proposal_hash"]:
                raise ValueError()
        value["summary"] = json.loads(value["summary"])
        value["settlement"] = json.loads(value["settlement"]) if value["settlement"] else None
    except (ValueError, TypeError, KeyError, AttributeError):
        raise RuleError("Demo-omgångens sparade underlag har ogiltig kontrollsumma eller format.") from None
    return value


def _state(row, expected):
    if row["state"] != expected:
        raise RuleError(f"Inaktuell övergång: omgången är {row['state']}, inte {expected}. Läs det sparade läget.")


def _ledger(c, session_id):
    costs = [dict(r) for r in c.execute("SELECT * FROM betting_demo_costs WHERE session_id=? ORDER BY event_id,cost_kind", (session_id,))]
    bets = [dict(r) for r in c.execute("SELECT * FROM betting_demo_bets WHERE session_id=? ORDER BY event_id", (session_id,))]
    return costs, bets


def _economy(c, row):
    return summary(row["frozen"]["initial_capital_ore"], *_ledger(c, row["id"]))


def _perform(session_id, operation, body, execute):
    require_demo()
    request_hash = digest({"session_id": session_id, "operation": operation, "body": body.model_dump(mode="json")})
    with connect(True) as c:
        old = c.execute("SELECT * FROM betting_demo_actions WHERE action_id=?", (body.action_id,)).fetchone()
        if old:
            if old["request_hash"] != request_hash:
                raise RuleError("Åtgärds-ID:t är bundet till annan omgång, operation eller annat innehåll.")
            return json.loads(old["response"])
        if c.execute("SELECT state FROM settings WHERE id=1").fetchone()[0] != "running":
            raise RuleError("Demot är pausat eller nödstoppat. Återuppta uttryckligen innan en ny åtgärd.")
        row = _load(c, session_id) if session_id else None
        result = execute(c, row)
        c.execute("INSERT INTO betting_demo_actions VALUES(?,?,?,?,?,?)",
                  (body.action_id, result["id"], operation, request_hash, canonical(result), now()))
        c.execute("INSERT INTO betting_demo_events(session_id,operation,from_state,to_state,recorded_at) VALUES(?,?,?,?,?)",
                  (result["id"], operation, row["state"] if row else None, result["state"], now()))
        return result


def create(body: Action):
    def execute(c, _):
        try:
            frozen = build_scenario()
            validate_scenario(frozen)
            frozen = demo_review.build_scenario_v2(frozen)
        except (ValueError, KeyError, TypeError) as exc:
            raise RuleError("Demots fasta scenario är felkonfigurerat: " + str(exc)) from None
        if not {"researcher", "analyst", "finance", "critic"}.issubset(ROLES):
            raise RuleError("Demots befintliga roller saknas.")
        session_id, created = uid(), now()
        c.execute("INSERT INTO betting_demo_sessions(id,state,frozen,frozen_hash,summary,created_at,updated_at) VALUES(?,'created',?,?,?,?,?)",
                  (session_id, canonical(frozen), digest(frozen), canonical(summary(frozen["initial_capital_ore"], [], [])), created, created))
        return {"id": session_id, "state": "created"}
    return _perform(None, "create", body, execute)


def analyze(session_id, body: Action):
    def execute(c, row):
        _state(row, "created")
        try:
            data = analysis_input(row["frozen"])
            contract = demo_review.contract_from_frozen(row["frozen"])
            if contract:
                demo_review.validate_review_input(data, contract)
            core_analysis = analyze_scenario(data)
            analysis = (demo_review.analyze_v2(data, contract, core_analysis) if contract else core_analysis)
        except ValueError as exc:
            raise RuleError(str(exc)) from None
        except (KeyError, TypeError, AttributeError):
            raise RuleError("Demots sparade analysunderlag har felaktigt format.") from None
        recorded = now()
        for cost in row["frozen"]["cost_definitions"]:
            c.execute("INSERT INTO betting_demo_costs VALUES(?,?,?,?,?,?)",
                      (session_id, cost["event_id"], cost["cost_kind"], cost["amount_ore"], cost["simulated_at"], recorded))
        state = "analyzed" if analysis["proposals"] else "no_bets"
        c.execute("UPDATE betting_demo_sessions SET state=?,analysis=?,summary=?,updated_at=? WHERE id=?",
                  (state, canonical(analysis), canonical(_economy(c, row)), recorded, session_id))
        return {"id": session_id, "state": state}
    return _perform(session_id, "analyze", body, execute)


def _bound(row, body):
    if (body.proposal_version != row["analysis"]["proposal_version"]
            or body.proposal_hash != row["analysis"]["proposal_hash"]):
        raise RuleError("Förslagsversionen eller innehållshashen stämmer inte. Läs den sparade batchen.")


def _review_bound(row):
    try:
        contract = demo_review.contract_from_frozen(row["frozen"], row["analysis"])
        if contract:
            demo_review.verify_saved_chain(analysis_input(row["frozen"]), contract, row["analysis"])
    except ValueError as exc:
        raise RuleError(str(exc)) from None
    except (KeyError, TypeError, AttributeError):
        raise RuleError("Demots sparade granskningskedja har felaktigt format.") from None


def decide(session_id, body: Decision):
    def execute(c, row):
        _state(row, "analyzed")
        _review_bound(row)
        _bound(row, body)
        recorded = now()
        c.execute("UPDATE betting_demo_sessions SET state=?,decision=?,decision_version=?,decision_hash=?,decision_at=?,updated_at=? WHERE id=?",
                  (body.decision, body.decision, body.proposal_version, body.proposal_hash, recorded, recorded, session_id))
        return {"id": session_id, "state": body.decision}
    return _perform(session_id, "decision", body, execute)


def simulate(session_id, body: ApprovedBatch):
    def execute(c, row):
        _state(row, "approved")
        _review_bound(row)
        _bound(row, body)
        if (row["decision"] != "approved" or row["decision_version"] != body.proposal_version
                or row["decision_hash"] != body.proposal_hash):
            raise RuleError("Batchen saknar ett matchande ägarbeslut.")
        proposals = row["analysis"]["proposals"]
        total = sum(p["stake_ore"] for p in proposals)
        available = _economy(c, row)["available_ore"]
        if total > available:
            raise RuleError(f"Hela batchen kräver {total} öre men bara {available} öre är tillgängliga. Inga insatser registrerades.")
        recorded = now()
        for proposal in proposals:
            c.execute("INSERT INTO betting_demo_bets(session_id,event_id,outcome,paper_odds,stake_ore,proposal_version,proposal_hash,state,placed_at) VALUES(?,?,?,?,?,?,?,'open',?)",
                      (session_id, proposal["event_id"], proposal["outcome"], proposal["paper_odds"], proposal["stake_ore"],
                       body.proposal_version, body.proposal_hash, recorded))
        c.execute("UPDATE betting_demo_sessions SET state='simulated',summary=?,updated_at=? WHERE id=?",
                  (canonical(_economy(c, row)), recorded, session_id))
        return {"id": session_id, "state": "simulated"}
    return _perform(session_id, "simulate", body, execute)


def settle(session_id, body: Action):
    def execute(c, row):
        _state(row, "simulated")
        _review_bound(row)
        if row["frozen"]["settlement_version"] != SETTLEMENT_VERSION:
            raise RuleError("Omgångens frysta avräkningsversion stöds inte. Ingen avräkning gjordes.")
        _, bets = _ledger(c, session_id)
        if len(bets) != len(row["analysis"]["proposals"]) or any(b["state"] != "open" for b in bets):
            raise RuleError("Den öppna batchen är ofullständig. Ingen avräkning gjordes.")
        proposals = {p["event_id"]: p for p in row["analysis"]["proposals"]}
        for bet in bets:
            proposal = proposals.get(bet["event_id"])
            if (not proposal or any(bet[k] != proposal[k] for k in ("outcome", "paper_odds", "stake_ore"))
                    or bet["proposal_version"] != row["decision_version"] or bet["proposal_hash"] != row["decision_hash"]):
                raise RuleError("Insatsbatchen matchar inte ägarbeslutet. Ingen avräkning gjordes.")
        recorded = now()
        for bet in bets:
            result = row["frozen"]["settlement_data"][bet["event_id"]]
            value = settle_bet(bet, result)
            c.execute("UPDATE betting_demo_bets SET state=?,return_ore=?,profit_ore=?,result=?,settled_at=? WHERE session_id=? AND event_id=?",
                      (value["state"], value["return_ore"], value["profit_ore"], canonical(result), recorded, session_id, bet["event_id"]))
        economy = _economy(c, row)
        settlement = {"results": [{"event_id": event_id, **result} for event_id, result in row["frozen"]["settlement_data"].items()],
                      "summary": economy, "rules_version": row["frozen"]["rules_version"],
                      "settlement_version": row["frozen"]["settlement_version"], "recorded_at": recorded}
        c.execute("UPDATE betting_demo_sessions SET state='settled',summary=?,settlement=?,updated_at=? WHERE id=?",
                  (canonical(economy), canonical(settlement), recorded, session_id))
        return {"id": session_id, "state": "settled"}
    return _perform(session_id, "settle", body, execute)


def _pick(value, keys):
    return {k: value[k] for k in keys if k in value}


def _object(value):
    return value if isinstance(value, dict) else {}


def _array(value):
    return value if isinstance(value, list) else []


def _scalars(value):
    return [v for v in _array(value) if v is None or type(v) in (str, int, float, bool)]


def _scalar_pick(value, keys):
    return {k: v for k, v in _pick(_object(value), keys).items()
            if v is None or type(v) in (str, int, float, bool)}


def _public_core_analysis(analysis, include_input=False):
    analysis = _object(analysis)
    result = _scalar_pick(analysis, ("proposal_version", "proposal_hash", "total_stake_ore", "simulated_cost_ore"))
    if include_input:
        result.update(_scalar_pick(analysis, ("analysis_input_hash",)))
    result["matches"] = []
    for raw in _array(analysis.get("matches")):
        match = _object(raw)
        view = _scalar_pick(match, ("event_id", "simulated_analysis_at", "explanation", "role_id", "notice"))
        decision = _object(match.get("decision"))
        view["decision"] = _scalar_pick(decision, ("selected", "reason", "book", "outcome", "quoted_odds", "paper_odds", "edge_bp", "reference_probability_ppm", "stake_ore"))
        if "reference_books" in decision:
            view["decision"]["reference_books"] = _scalars(decision["reference_books"])
        view["decision"]["checks"] = [_scalar_pick(check, ("book", "accepted", "reason", "overround_bp")) for check in _array(decision.get("checks"))]
        result["matches"].append(view)
    result["proposals"] = [_scalar_pick(p, ("event_id", "home", "away", "outcome", "book", "paper_odds", "stake_ore", "explanation")) for p in _array(analysis.get("proposals"))]
    result["messages"] = [_scalar_pick(m, ("role_id", "notice", "text")) for m in _array(analysis.get("messages"))]
    return result


def _public_money(value):
    return _scalar_pick(value, ("initial_capital_ore", "simulated_cost_ore", "proposal_count", "fixed_stake_ore",
                               "expected_fixed_total_ore", "total_stake_ore", "projected_available_ore", "capital_sufficient"))


def _public_facts(value):
    value = _object(value)
    result = _scalar_pick(value, ("kind",))
    if value.get("kind") == "researcher":
        for key in ("event_ids", "packet_hashes", "fresh_counts", "rejected_event_ids"):
            result[key] = _scalars(value.get(key))
    elif value.get("kind") == "analyst":
        result.update(_scalar_pick(value, ("core_input_hash", "core_output_hash")))
        result["candidate_event_ids"] = _scalars(value.get("candidate_event_ids"))
    elif value.get("kind") == "finance":
        result.update(_public_money(value))
    elif value.get("kind") == "critic":
        for key in ("retained_event_ids", "removed_event_ids"):
            result[key] = _scalars(value.get(key))
        result.update(_scalar_pick(value, ("findings_hash",)))
        result["final_money"] = _public_money(value.get("final_money"))
    return result


def _public_analysis(analysis):
    if analysis is None:
        return None
    analysis = _object(analysis)
    v2 = analysis.get("review_version") == demo_review.WORKFLOW_VERSION
    result = _public_core_analysis(analysis, include_input=v2)
    if not v2:
        return result
    result.update(_scalar_pick(analysis, ("review_version", "core_proposal_hash", "notice")))
    result["core_analysis"] = _public_core_analysis(analysis.get("core_analysis"), include_input=True)
    research = _object(analysis.get("research"))
    result["research"] = {**_scalar_pick(research, ("version",)), "packets": []}
    for raw in _array(research.get("packets")):
        packet = _object(raw)
        view = _scalar_pick(packet, ("research_version", "data_kind", "event_id", "observation_hash", "as_of", "starts_at",
            "seconds_to_kickoff", "max_quote_age_seconds", "minimum_fresh_sources", "fresh_count", "source_independence", "notice", "packet_hash"))
        for key in ("missing_context", "rejections"):
            view[key] = _scalars(packet.get(key))
        view["sources"] = [_scalar_pick(s, ("book", "source_url", "updated_at", "age_seconds", "fresh", "reason"))
                           for s in _array(packet.get("sources"))]
        result["research"]["packets"].append(view)
    review = _object(analysis.get("review"))
    contract = _object(review.get("contract"))
    rules = _object(contract.get("research_rules"))
    result["review"] = {"contract": {
        **_scalar_pick(contract, ("workflow_version", "research_version")),
        "research_rules": {**_scalar_pick(rules, ("as_of_source", "notice")), "required_context": _scalars(rules.get("required_context"))},
        "review_roles": [_scalar_pick(r, ("role_id", "name", "version")) for r in _array(contract.get("review_roles"))]},
        "steps": [], "findings": [_scalar_pick(f, ("code", "severity", "event_id")) for f in _array(review.get("findings"))]}
    for raw in _array(review.get("steps")):
        step = _object(raw)
        result["review"]["steps"].append({**_scalar_pick(step, ("role_id", "role_name", "role_version", "input_hash", "status", "output_hash")),
            "facts": _public_facts(step.get("facts")), "limitations": _scalars(step.get("limitations"))})
    return result


def _public_header(row):
    result = {**_pick(row, ("id", "state", "created_at", "updated_at")),
            **_pick(row["frozen"], ("scenario_version", "rules_version", "explanation_version", "initial_capital_ore", "stake_ore")),
            "summary": row["summary"]}
    if "workflow_version" in row["frozen"]:
        value = row["frozen"]["workflow_version"]
        result["workflow_version"] = value if isinstance(value, str) else "unknown"
    return result


def _public_observation(observation):
    # Läs det sparade underlaget; tillämpa inte en senare Snapshot-validator på historiken.
    result = _pick(observation, ("event_id", "sport", "market", "home", "away", "starts_at", "captured_at", "data_cost_ore"))
    result["quotes"] = [{**_pick(q, ("book", "source_url", "updated_at")),
                         "odds": _pick(q["odds"], ("home", "draw", "away"))} for q in observation["quotes"]]
    return result


def get_session(session_id):
    require_demo()
    with connect() as c:
        c.execute("BEGIN")  # Behåll samma lässnapshot för rad, ledger och historik.
        row = _load(c, session_id)
        costs, bets = _ledger(c, session_id)
        result = {**_public_header(row),
                  "observations": [_public_observation(o) for o in row["frozen"]["observations"]],
                  "analysis": _public_analysis(row["analysis"]),
                  "decision": ({"value": row["decision"], "proposal_version": row["decision_version"],
                                "proposal_hash": row["decision_hash"], "recorded_at": row["decision_at"]} if row["decision"] else None),
                  "costs": [_pick(cost, ("event_id", "cost_kind", "amount_ore", "simulated_at", "recorded_at")) for cost in costs],
                  "bets": [],
                  "history": [dict(r) for r in c.execute("SELECT operation,from_state,to_state,recorded_at FROM betting_demo_events WHERE session_id=? ORDER BY seq", (session_id,))]}
        for bet in bets:
            view = _pick(bet, ("event_id", "outcome", "paper_odds", "stake_ore", "proposal_version", "proposal_hash", "state", "placed_at"))
            if row["state"] == "settled":
                view.update(_pick(bet, ("return_ore", "profit_ore", "settled_at")))
                view["result"] = _pick(json.loads(bet["result"]), ("status", "home_score", "away_score", "simulated_finished_at"))
            result["bets"].append(view)
        if row["state"] == "settled":
            result["results"] = [_pick(r, ("event_id", "status", "home_score", "away_score", "simulated_finished_at")) for r in row["settlement"]["results"]]
        return result


def catalog():
    require_demo()
    with connect() as c:
        c.execute("BEGIN")  # Alla omgångar ska komma från samma lässnapshot.
        ids = [r[0] for r in c.execute("SELECT id FROM betting_demo_sessions ORDER BY created_at DESC,id DESC")]
        return {"scenario_version": SCENARIO_VERSION, "real_money_enabled": False,
                "sessions": [_public_header(_load(c, session_id)) for session_id in ids]}
