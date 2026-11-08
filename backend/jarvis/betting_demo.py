"""Ren, versionsbunden syntetisk matchanalys. Ingen DB, klocka eller transport."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, localcontext
from statistics import median

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from .odds_lab import POLICY, Snapshot, digest, example_snapshot, normalize_prices

SCENARIO_VERSION = "seven-matches-demo-v1"
ENGINE_VERSION = "betting-demo-analysis-v1"
EXPLANATION_VERSION = "betting-demo-explanations-v1"
SETTLEMENT_VERSION = "effective-odds-floor-ore-v1"
AGENT_NOTICE = "Simulerat agentsvar – lokal demologik."
OUTCOMES = {"home": "hemmaseger", "draw": "oavgjort", "away": "bortaseger"}
STATES = ("created", "analyzed", "no_bets", "approved", "declined", "simulated", "settled")


class AnalysisInput(BaseModel):
    """Endast tillgängliga offerter; framtida resultat får inte passera gränsen."""
    model_config = ConfigDict(extra="forbid")
    observation: Snapshot
    simulated_analysis_at: AwareDatetime
    rules: dict
    available_capital_ore: int = Field(strict=True, ge=0)


class ScenarioAnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_version: str
    rules_version: str
    engine_version: str
    explanation_version: str
    initial_capital_ore: int = Field(strict=True, gt=0)
    stake_ore: int = Field(strict=True, gt=0)
    rules: dict
    observations: list[Snapshot]
    cost_definitions: list[dict]
    role_labels: dict[str, str]


def analysis_input(frozen):
    """Bygg gränsobjektet innan någon analysfunktion anropas."""
    return ScenarioAnalysisInput.model_validate({k: frozen[k] for k in ScenarioAnalysisInput.model_fields})


def build_scenario():
    # Samma sju observationer, tider, kostnader och resultat som odds_service._synthetic.
    observations, results, costs = [], {}, []
    start = datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    for index in range(7):
        at = start + timedelta(days=index)
        data = example_snapshot(at)
        data.update(event_id=f"syntetisk-{index + 1}", home=f"Påhittat hemmalag {index + 1}",
                    away=f"Påhittat bortalag {index + 1}", data_cost_ore=20)
        if index == 4:
            for quote in data["quotes"]:
                quote["updated_at"] = (at - timedelta(minutes=5)).isoformat()
        elif index == 5:
            data["quotes"] = data["quotes"][:3]
        elif index == 6:
            data["quotes"][0]["odds"]["home"] = 20000
        observation = Snapshot.model_validate(data).model_dump(mode="json")
        observations.append(observation)
        results[data["event_id"]] = {
            "status": "final", "home_score": 2 if index % 2 == 0 else 0,
            "away_score": 0 if index % 2 == 0 else 1,
            "simulated_finished_at": (at + timedelta(hours=5)).isoformat(),
        }
        costs.append({"event_id": data["event_id"], "cost_kind": "analysis_data",
                      "amount_ore": 20, "simulated_at": at.isoformat(),
                      "description": "Simulerad datakostnad vid sparad analys, även vid avstående."})
    return {
        "scenario_version": SCENARIO_VERSION, "rules_version": POLICY["version"],
        "engine_version": ENGINE_VERSION, "explanation_version": EXPLANATION_VERSION,
        "settlement_version": SETTLEMENT_VERSION,
        "initial_capital_ore": POLICY["initial_bankroll_ore"], "stake_ore": POLICY["stake_ore"],
        "rules": deepcopy(POLICY), "observations": observations, "settlement_data": results,
        "cost_definitions": costs,
        "role_labels": {"analyst": "Oddsanalytiker", "finance": "Ekonom / Risk", "critic": "Kritiker / Kvalitetskontroll"},
    }


def validate_scenario(scenario):
    for field in ("initial_capital_ore", "stake_ore"):
        if type(scenario[field]) is not int or scenario[field] <= 0:
            raise ValueError("Scenariot måste ha positivt heltalskapital och fast insats.")
    ids = [Snapshot.model_validate(o).event_id for o in scenario["observations"]]
    if not ids or len(ids) != len(set(ids)) or set(ids) != set(scenario["settlement_data"]):
        raise ValueError("Scenariots matchidentiteter är ofullständiga eller duplicerade.")
    if scenario["rules"]["stake_ore"] != scenario["stake_ore"]:
        raise ValueError("Scenariots fasta insats stämmer inte med de frysta reglerna.")
    keys = set()
    for cost in scenario["cost_definitions"]:
        key = (cost["event_id"], cost["cost_kind"])
        if (key in keys or key[0] not in ids or type(cost["amount_ore"]) is not int
                or cost["amount_ore"] < 0):
            raise ValueError("Scenariots kostnadsdefinitioner är ogiltiga.")
        keys.add(key)
    if sum(c["amount_ore"] for c in scenario["cost_definitions"]) > scenario["initial_capital_ore"]:
        raise ValueError("Scenariots obligatoriska analyskostnader överstiger startkapitalet.")


def analyze_match(data: AnalysisInput):
    """Samma prismatematik som v1, med uttryckliga frysta parametrar."""
    snapshot, rules = data.observation, data.rules
    checks, valid = [], []
    with localcontext() as ctx:
        ctx.prec = 40
        for quote in snapshot.quotes:
            age = (snapshot.captured_at - quote.updated_at).total_seconds()
            probabilities, total = normalize_prices(quote.odds)
            reason = None
            if not 0 <= age <= rules["max_quote_age_seconds"]:
                reason = "För gammal offert eller offert från framtiden."
            if not Decimal("0.95") <= total <= Decimal("1.25"):
                reason = "Avvikande marginal; offerten behöver kontrolleras."
            checks.append({"book": quote.book, "accepted": reason is None, "reason": reason,
                           "overround_bp": int(total * 10000)})
            if reason is None:
                valid.append((quote, probabilities))
        decision = {"selected": False, "reason": "Ingen avvikelse klarar de låsta provreglerna.", "checks": checks}
        if (snapshot.starts_at - data.simulated_analysis_at).total_seconds() < rules["min_seconds_before_kickoff"]:
            return {**decision, "reason": "För nära avspark eller redan startad match."}
        if len(valid) < rules["min_reference_books"] + 1:
            return {**decision, "reason": "Färre än fyra giltiga källor; tre andra jämförelsekällor krävs."}
        candidates = []
        for quote, _ in valid:
            references = [(other, probs) for other, probs in valid if other.book != quote.book]
            for outcome in OUTCOMES:
                probability = median(p[outcome] for _, p in references)
                offered = getattr(quote.odds, outcome)
                effective = offered * (10000 - rules["price_haircut_bp"]) // 10000
                edge = int(((probability * effective / 10000 - 1) * 10000).to_integral_value(rounding=ROUND_FLOOR))
                if rules["min_edge_bp"] <= edge <= rules["max_edge_bp"]:
                    candidates.append({"book": quote.book, "outcome": outcome, "quoted_odds": offered,
                                       "paper_odds": effective, "edge_bp": edge,
                                       "reference_probability_ppm": int(probability * 1000000),
                                       "reference_books": sorted(q.book for q, _ in references)})
        if not candidates:
            return decision
        if data.available_capital_ore < rules["stake_ore"]:
            return {**decision, "reason": "Låtsaskapitalet täcker inte en fast insats."}
        chosen = sorted(candidates, key=lambda c: (-c["edge_bp"], c["book"], c["outcome"]))[0]
        return {**decision, **chosen, "selected": True, "stake_ore": rules["stake_ore"],
                "reason": "Regelbaserat syntetiskt förslag. Referensen är ingen verifierad vinstchans."}


def explain(decision):
    if not decision["selected"]:
        return f"Avstå: {decision['reason']} Kostnaden för analysen kvarstår."
    return (f"Förslag: {OUTCOMES[decision['outcome']]} hos {decision['book']}. "
            f"Effektivt odds {Decimal(decision['paper_odds']) / 10000:.4f} efter det enda prisavdraget; "
            f"beräknad referensavvikelse {Decimal(decision['edge_bp']) / 100:.2f} %. "
            f"Referens utan målbolaget: {', '.join(decision['reference_books'])}. "
            "Käll-ID:n bevisar inte oberoende källfamiljer eller verklig spelbarhet.")


def analyze_scenario(data: ScenarioAnalysisInput):
    frozen = data.model_dump(mode="json")
    if frozen["engine_version"] != ENGINE_VERSION or frozen["explanation_version"] != EXPLANATION_VERSION:
        raise ValueError("Den frysta analysversionen stöds inte. Sparad historik kan fortfarande läsas.")
    cost = sum(c["amount_ore"] for c in frozen["cost_definitions"])
    matches, proposals = [], []
    for observation in frozen["observations"]:
        data = AnalysisInput(observation=observation, simulated_analysis_at=observation["captured_at"],
                             rules=frozen["rules"], available_capital_ore=frozen["initial_capital_ore"] - cost)
        decision = analyze_match(data)
        explanation = explain(decision)
        matches.append({"event_id": data.observation.event_id, "decision": decision,
                        "simulated_analysis_at": data.simulated_analysis_at.isoformat(),
                        "explanation": explanation, "role_id": "analyst", "notice": AGENT_NOTICE})
        if decision["selected"]:
            proposals.append({"event_id": data.observation.event_id, "home": data.observation.home,
                              "away": data.observation.away, "outcome": decision["outcome"],
                              "book": decision["book"], "paper_odds": decision["paper_odds"],
                              "stake_ore": decision["stake_ore"], "explanation": explanation})
    # Framtida avräkningsdata påverkar inte ens analysens innehållshash.
    analysis_input_hash = digest(frozen)
    value = {"proposal_version": 1, "analysis_input_hash": analysis_input_hash, "matches": matches,
             "proposals": proposals, "total_stake_ore": sum(p["stake_ore"] for p in proposals),
             "simulated_cost_ore": cost,
             "messages": [
                 {"role_id": "finance", "notice": AGENT_NOTICE,
                  "text": f"{len(proposals)} förslag. Analysen kostar {cost} simulerade öre även om du avstår. Kapitalet tillhör endast denna omgång."},
                 {"role_id": "critic", "notice": AGENT_NOTICE,
                  "text": "Påhittade odds och utfall prövar arbetsflödet. De ger inget tillstånd till riktiga insatser och inget belägg för lönsamhet."},
             ]}
    return {**value, "proposal_hash": digest(value)}


def settle_bet(bet, result):
    """Avräkna det redan godkända effektiva oddset; inget nytt prisavdrag."""
    if result["status"] == "void":
        return {"state": "void", "return_ore": bet["stake_ore"], "profit_ore": 0}
    outcome = "home" if result["home_score"] > result["away_score"] else "away" if result["away_score"] > result["home_score"] else "draw"
    payout = bet["stake_ore"] * bet["paper_odds"] // 10000 if outcome == bet["outcome"] else 0
    return {"state": "won" if payout else "lost", "return_ore": payout, "profit_ore": payout - bet["stake_ore"]}


def summary(initial, costs, bets):
    cost = sum(c["amount_ore"] for c in costs)
    closed = [b for b in bets if b["state"] != "open"]
    profit = sum(b["profit_ore"] for b in closed)
    open_stake = sum(b["stake_ore"] for b in bets if b["state"] == "open")
    return {"initial_capital_ore": initial, "game_profit_ore": profit, "simulated_cost_ore": cost,
            "net_ore": profit - cost, "capital_ore": initial + profit - cost,
            "open_stake_ore": open_stake, "available_ore": initial + profit - cost - open_stake,
            "total_stake_ore": sum(b["stake_ore"] for b in bets),
            "payout_ore": sum(b["return_ore"] for b in closed), "bet_count": len(bets),
            "settled_count": len(closed), "won_count": sum(b["state"] == "won" for b in closed),
            "lost_count": sum(b["state"] == "lost" for b in closed)}
