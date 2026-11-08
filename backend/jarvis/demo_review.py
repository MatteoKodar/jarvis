"""Ren, spårbar rollgranskning av den befintliga syntetiska prisberäkningen."""
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import Field, model_validator

from . import demo_research as research
from .betting_demo import ScenarioAnalysisInput, explain
from .demo_research import StrictFrozen, ResearchRules, ResearchPacket, build_packet, make_input
from .odds_lab import digest
from .roles import ROLES

WORKFLOW_VERSION = "betting-demo-review-v2"
ROLE_ORDER = ("researcher", "analyst", "finance", "critic")
META_KEYS = ("workflow_version", "research_version", "research_rules", "review_roles")
BLOCKERS = ("PROPOSAL_ON_REJECTED_MATCH", "STALE_OR_FUTURE_SOURCE", "UNKNOWN_SOURCE",
            "PACKET_MISMATCH", "AMOUNT_MISMATCH")
LIMITATIONS = ("CONTEXT_MISSING", "SOURCE_INDEPENDENCE_UNVERIFIED")
FORBIDDEN = {"settlement_data", "home_score", "away_score", "simulated_finished_at", "result", "results"}
CORE_KEYS = {"proposal_version", "analysis_input_hash", "matches", "proposals",
             "total_stake_ore", "simulated_cost_ore", "messages", "proposal_hash"}
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def _require(condition, message):
    if not condition:
        raise ValueError("Granskningskedjan: " + message)


class RoleRef(StrictFrozen):
    role_id: Literal["researcher", "analyst", "finance", "critic"]
    name: str
    version: str


class ReviewContract(StrictFrozen):
    workflow_version: Literal["betting-demo-review-v2"]
    research_version: Literal["demo-research-v1"]
    research_rules: ResearchRules
    review_roles: tuple[RoleRef, ...]

    @model_validator(mode="after")
    def ordered_roles(self):
        _require(tuple(r.role_id for r in self.review_roles) == ROLE_ORDER, "fel rollordning.")
        return self


class Proposal(StrictFrozen):
    event_id: str
    home: str
    away: str
    outcome: Literal["home", "draw", "away"]
    book: str
    paper_odds: int = Field(strict=True, gt=0)
    stake_ore: int = Field(strict=True, gt=0)
    explanation: str


class MoneyFacts(StrictFrozen):
    initial_capital_ore: int = Field(strict=True)
    simulated_cost_ore: int = Field(strict=True, ge=0)
    proposal_count: int = Field(strict=True, ge=0)
    fixed_stake_ore: int = Field(strict=True, gt=0)
    expected_fixed_total_ore: int = Field(strict=True, ge=0)
    total_stake_ore: int = Field(strict=True, ge=0)
    projected_available_ore: int = Field(strict=True)
    capital_sufficient: bool = Field(strict=True)


class ResearchFacts(StrictFrozen):
    kind: Literal["researcher"] = "researcher"
    event_ids: tuple[str, ...]
    packet_hashes: tuple[Hash, ...]
    fresh_counts: tuple[int, ...]
    rejected_event_ids: tuple[str, ...]


class AnalystFacts(StrictFrozen):
    kind: Literal["analyst"] = "analyst"
    core_input_hash: Hash
    core_output_hash: Hash
    candidate_event_ids: tuple[str, ...]


class FinanceFacts(MoneyFacts):
    kind: Literal["finance"] = "finance"


class CriticFacts(StrictFrozen):
    kind: Literal["critic"] = "critic"
    retained_event_ids: tuple[str, ...]
    removed_event_ids: tuple[str, ...]
    findings_hash: Hash
    final_money: MoneyFacts


Facts = Annotated[ResearchFacts | AnalystFacts | FinanceFacts | CriticFacts, Field(discriminator="kind")]


class StepContent(StrictFrozen):
    role_id: Literal["researcher", "analyst", "finance", "critic"]
    role_name: str
    role_version: str
    input_hash: Hash
    status: Literal["completed", "with_limitations", "with_abstentions"]
    facts: Facts
    limitations: tuple[str, ...]

    @model_validator(mode="after")
    def own_facts(self):
        _require(self.facts.kind == self.role_id, "rollens fakta har fel schema.")
        return self


class ReviewStep(StepContent):
    output_hash: Hash

    @model_validator(mode="after")
    def checksum(self):
        _require(digest(self.model_dump(mode="json", exclude={"output_hash"})) == self.output_hash,
                 "stegets innehållshash stämmer inte.")
        return self


class Finding(StrictFrozen):
    code: Literal["PROPOSAL_ON_REJECTED_MATCH", "STALE_OR_FUTURE_SOURCE", "UNKNOWN_SOURCE",
                  "PACKET_MISMATCH", "AMOUNT_MISMATCH", "CONTEXT_MISSING", "SOURCE_INDEPENDENCE_UNVERIFIED"]
    severity: Literal["blocker", "limitation"]
    event_id: str | None

    @model_validator(mode="after")
    def classification(self):
        _require(self.severity == ("blocker" if self.code in BLOCKERS else "limitation"), "fel fyndklass.")
        _require(self.code not in BLOCKERS or self.event_id is not None, "blockerare saknar match.")
        return self


class ReviewBundle(StrictFrozen):
    contract: ReviewContract
    steps: tuple[ReviewStep, ...]
    findings: tuple[Finding, ...]


def build_scenario_v2(base):
    _require(not any(k in base for k in META_KEYS), "scenariot har redan granskningsmetadata.")
    contract = ReviewContract(workflow_version=WORKFLOW_VERSION, research_version=research.RESEARCH_VERSION,
        research_rules=ResearchRules.model_validate(deepcopy(research.RESEARCH_POLICY)),
        review_roles=tuple(RoleRef(role_id=i, name=ROLES[i]["name"], version=ROLES[i]["version"]) for i in ROLE_ORDER))
    return {**deepcopy(base), **contract.model_dump(mode="json")}


def contract_from_frozen(frozen, analysis=None):
    if "workflow_version" not in frozen:
        _require(not any(k in frozen for k in META_KEYS[1:]), "ofullständig versionsmetadata.")
        if analysis is not None:
            _require(analysis.get("proposal_version") == 1
                     and not {"review", "research", "review_version", "core_analysis", "core_proposal_hash"}.intersection(analysis),
                     "v2-analys kan inte nedgraderas till v1.")
        return None
    try:
        return ReviewContract.model_validate({key: frozen[key] for key in META_KEYS})
    except KeyError:
        raise ValueError("Granskningskedjan: ofullständigt fryst kontrakt.") from None


def _no_future(value):
    if isinstance(value, dict):
        _require(not FORBIDDEN.intersection(value), "framtida resultatfält tillåts inte.")
        for item in value.values():
            _no_future(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _no_future(item)


def _check_core(data, core):
    _no_future(core)
    _require(set(core) == CORE_KEYS and core["proposal_version"] == 1, "fel grundanalysversion eller format.")
    _require(core["analysis_input_hash"] == digest(data.model_dump(mode="json")), "grundanalysen har annat underlag.")
    _require(core["proposal_hash"] == digest({k: v for k, v in core.items() if k != "proposal_hash"}), "fel grundanalys-hash.")
    ids = [o.event_id for o in data.observations]
    _require(len(ids) == len(set(ids)), "duplicerade matcher.")
    matches = core["matches"]
    _require([m["event_id"] for m in matches] == ids, "grundanalysens matcher stämmer inte.")
    proposals = [Proposal.model_validate(p) for p in core["proposals"]]
    selected = [m["event_id"] for m in matches if m["decision"]["selected"]]
    _require([p.event_id for p in proposals] == selected and len(selected) == len(set(selected)), "förslagsmängden stämmer inte.")
    cost = sum(c["amount_ore"] for c in data.cost_definitions)
    _require(type(core["simulated_cost_ore"]) is int and core["simulated_cost_ore"] == cost, "analyskostnaden stämmer inte.")
    _require(type(core["total_stake_ore"]) is int and core["total_stake_ore"] == sum(p.stake_ore for p in proposals),
             "grundanalysens totalsumma stämmer inte.")


def validate_review_input(data, contract):
    # Legacy cost/label dictionaries are intentionally unchanged; close their
    # nested result boundary before passing them to the v2 calculation.
    _no_future(data.model_dump(mode="json"))
    _no_future(contract.model_dump(mode="json"))
    _require(data.rules_version == data.rules.get("version"), "reglernas versioner stämmer inte.")


def build_packets(data, contract):
    return tuple(build_packet(make_input(o, data.rules, contract.research_rules.model_dump(mode="json")))
                 for o in data.observations)


def _saved_packets(data, contract, values):
    # Version-specific validators inspect saved facts; no packet builder runs here.
    _require(contract.research_version == research.RESEARCH_VERSION, "okänd researchversion.")
    packets = tuple(ResearchPacket.model_validate(p) for p in values)
    _require([p.event_id for p in packets] == [o.event_id for o in data.observations], "paketmängden stämmer inte.")
    for observation, packet in zip(data.observations, packets):
        _require(packet.observation_hash == digest(observation.model_dump(mode="json"))
                 and packet.as_of == observation.captured_at and packet.starts_at == observation.starts_at
                 and packet.max_quote_age_seconds == data.rules["max_quote_age_seconds"]
                 and packet.minimum_fresh_sources == data.rules["min_reference_books"] + 1
                 and packet.notice == contract.research_rules.notice
                 and packet.missing_context == contract.research_rules.required_context, "paketet hör till annat underlag.")
        _require([(s.book, s.source_url, s.updated_at) for s in packet.sources]
                 == [(q.book, q.source_url, q.updated_at) for q in observation.quotes], "paketets källor stämmer inte.")
    return packets


def _money(data, proposals, cost):
    total = sum(p["stake_ore"] for p in proposals)
    available = data.initial_capital_ore - cost - total
    return MoneyFacts(initial_capital_ore=data.initial_capital_ore, simulated_cost_ore=cost,
        proposal_count=len(proposals), fixed_stake_ore=data.stake_ore,
        expected_fixed_total_ore=len(proposals) * data.stake_ore, total_stake_ore=total,
        projected_available_ore=available, capital_sufficient=available >= 0)


def _proposal_problem(proposal, match, packet, observation, data):
    sources = {s.book: s for s in packet.sources}
    decision = match["decision"]
    references = decision.get("reference_books", [])
    _require(isinstance(references, list) and all(isinstance(v, str) for v in references), "fel referensformat.")
    used = [proposal["book"], *references]
    quotes = {q.book: q for q in observation.quotes}
    quote = quotes.get(proposal["book"])
    expected_price = (getattr(quote.odds, proposal["outcome"]) * (10000 - data.rules["price_haircut_bp"]) // 10000
                      if quote else None)
    problems = {
        "PROPOSAL_ON_REJECTED_MATCH": bool(packet.rejections),
        "STALE_OR_FUTURE_SOURCE": any(book in sources and not sources[book].fresh for book in used),
        "UNKNOWN_SOURCE": any(book not in sources for book in used),
        "PACKET_MISMATCH": (proposal["home"] != observation.home or proposal["away"] != observation.away
            or any(proposal[k] != decision.get(k) for k in ("book", "outcome", "paper_odds", "stake_ore"))
            or len(set(references)) != len(references) or proposal["book"] in references
            or len(references) < data.rules["min_reference_books"]),
        "AMOUNT_MISMATCH": proposal["stake_ore"] != data.stake_ore or proposal["paper_odds"] != expected_price,
    }
    return next((code for code in BLOCKERS if problems[code]), None)


def critic_verify(data, contract, core, packets):
    # Independent reconstruction at analyze only. Never inspect explanation text as instructions.
    expected = tuple(research.build_packet(make_input(o, data.rules, contract.research_rules.model_dump(mode="json")))
                     for o in data.observations)
    _require([p.model_dump(mode="json") for p in packets] == [p.model_dump(mode="json") for p in expected],
             "paketen motsäger kritikerns underlag.")
    by_id = {o.event_id: (o, p, m) for o, p, m in zip(data.observations, packets, core["matches"])}
    findings = [Finding(code=code, severity="limitation", event_id=None) for code in LIMITATIONS]
    for proposal in core["proposals"]:
        observation, packet, match = by_id[proposal["event_id"]]
        code = _proposal_problem(proposal, match, packet, observation, data)
        if code:
            findings.append(Finding(code=code, severity="blocker", event_id=proposal["event_id"]))
    return tuple(findings)


def _seed(core, contract, packets):
    return digest({"core_input_hash": core["analysis_input_hash"], "contract": contract.model_dump(mode="json"),
                   "packet_hashes": [p.packet_hash for p in packets]})


def _fact_models(data, core, packets, proposals, findings):
    removed = tuple(f.event_id for f in findings if f.severity == "blocker")
    return (
        ResearchFacts(event_ids=tuple(p.event_id for p in packets), packet_hashes=tuple(p.packet_hash for p in packets),
                      fresh_counts=tuple(p.fresh_count for p in packets), rejected_event_ids=tuple(p.event_id for p in packets if p.rejections)),
        AnalystFacts(core_input_hash=core["analysis_input_hash"], core_output_hash=core["proposal_hash"],
                     candidate_event_ids=tuple(p["event_id"] for p in core["proposals"])),
        FinanceFacts(**_money(data, core["proposals"], core["simulated_cost_ore"]).model_dump()),
        CriticFacts(retained_event_ids=tuple(p["event_id"] for p in proposals), removed_event_ids=removed,
                    findings_hash=digest([f.model_dump(mode="json") for f in findings]),
                    final_money=_money(data, proposals, core["simulated_cost_ore"])),
    )


def _steps(data, contract, core, packets, proposals, findings):
    facts = _fact_models(data, core, packets, proposals, findings)
    limitations = (
        ("Form, skador och laguppställningar saknas och ingår inte i beräkningen.",),
        ("Prisreferensen är ingen uppmätt vinstchans.",),
        ("Simulerade belopp. Kapital kontrolleras atomiskt vid registrering.",),
        ("Källoberoende och verklig spelbarhet är inte verifierade.",),
    )
    previous, steps = _seed(core, contract, packets), []
    for role, fact, limits in zip(contract.review_roles, facts, limitations):
        status = "with_abstentions" if role.role_id == "critic" and fact.removed_event_ids else "with_limitations"
        content = StepContent(role_id=role.role_id, role_name=role.name, role_version=role.version,
            input_hash=digest({"role_id": role.role_id, "previous_output_hash": previous}), status=status,
            facts=fact, limitations=limits)
        value = content.model_dump(mode="json")
        step = ReviewStep(**value, output_hash=digest(value))
        steps.append(step)
        previous = step.output_hash
    return tuple(steps)


def _final_view(core, blocked):
    """Deterministisk presentation efter urval; ingen analys eller nya källor."""
    value = deepcopy(core)
    value.pop("proposal_hash")
    value["proposals"] = [p for p in value["proposals"] if p["event_id"] not in blocked]
    value["total_stake_ore"] = sum(p["stake_ore"] for p in value["proposals"])
    for match in value["matches"]:
        if match["event_id"] in blocked:
            match["decision"] = {"selected": False, "reason": "Kritikern avstod från ett förslag med motstridigt underlag.",
                                 "checks": match["decision"]["checks"]}
            match["explanation"] = explain(match["decision"])
    if blocked:
        for message in value["messages"]:
            if message["role_id"] == "finance":
                message["text"] = (f"{len(value['proposals'])} förslag efter kritik. Analysen kostar {value['simulated_cost_ore']} "
                                   "simulerade öre även om du avstår. Kapitalet tillhör endast denna omgång.")
    return value


def analyze_v2(data: ScenarioAnalysisInput, contract: ReviewContract, core_analysis: dict):
    validate_review_input(data, contract)
    _check_core(data, core_analysis)
    core = deepcopy(core_analysis)
    packets = _saved_packets(data, contract, [p.model_dump(mode="json") for p in build_packets(data, contract)])
    findings = critic_verify(data, contract, core, packets)
    blocked = {f.event_id for f in findings if f.severity == "blocker"}
    value = _final_view(core, blocked)
    value.update(proposal_version=2, review_version=WORKFLOW_VERSION, core_proposal_hash=core["proposal_hash"],
        core_analysis=core, research={"version": contract.research_version,
                                    "packets": [p.model_dump(mode="json") for p in packets]},
        review=ReviewBundle(contract=contract, steps=_steps(data, contract, core, packets, value["proposals"], findings),
                            findings=findings).model_dump(mode="json"), notice=contract.research_rules.notice)
    value["proposal_hash"] = digest(value)
    verify_saved_chain(data, contract, value)
    return value


def verify_saved_chain(data, contract, analysis):
    """Kontrollera sparade bindningar/summor. Kör aldrig analys, paketbygge eller kritiker."""
    _no_future(analysis)
    validate_review_input(data, contract)
    _require(analysis.get("proposal_version") == 2 and analysis.get("review_version") == WORKFLOW_VERSION,
             "sparad analys har fel granskningsversion.")
    _require(set(analysis) == CORE_KEYS | {"review_version", "core_proposal_hash", "core_analysis", "research", "review", "notice"},
             "sparad analys har fel fält.")
    _require(analysis["proposal_hash"] == digest({k: v for k, v in analysis.items() if k != "proposal_hash"}), "fel yttersta hash.")
    core = analysis["core_analysis"]
    _check_core(data, core)
    _require(analysis["analysis_input_hash"] == core["analysis_input_hash"]
             and analysis["core_proposal_hash"] == core["proposal_hash"]
             and analysis["notice"] == contract.research_rules.notice, "grundbindningen stämmer inte.")
    _require(set(analysis["research"]) == {"version", "packets"}
             and analysis["research"]["version"] == contract.research_version, "fel sparad researchversion.")
    packets = _saved_packets(data, contract, analysis["research"]["packets"])
    review = ReviewBundle.model_validate(analysis["review"])
    _require(review.contract == contract and tuple(s.role_id for s in review.steps) == ROLE_ORDER, "fel sparad rollkedja.")
    originals = {p["event_id"]: p for p in core["proposals"]}
    final = analysis["proposals"]
    final_ids = [p["event_id"] for p in final]
    _require(len(final_ids) == len(set(final_ids))
             and all(p == originals.get(p["event_id"]) for p in final), "förslag har lagts till eller ändrats.")
    removed = set(originals) - set(final_ids)
    blockers = [f for f in review.findings if f.severity == "blocker"]
    _require(len(blockers) == len(removed) and {f.event_id for f in blockers} == removed, "borttagna förslag saknar entydiga blockerare.")
    _require(all(f.event_id is None or f.event_id in {o.event_id for o in data.observations} for f in review.findings), "fynd gäller okänd match.")
    selected = [m["event_id"] for m in analysis["matches"] if m["decision"]["selected"]]
    _require([m["event_id"] for m in analysis["matches"]] == [o.event_id for o in data.observations]
             and selected == final_ids, "slutlig matchlista stämmer inte.")
    expected_view = _final_view(core, removed)
    _require(analysis["matches"] == expected_view["matches"], "kvarvarande matchfakta eller ersättning har ändrats.")
    _require(analysis["messages"] == expected_view["messages"], "sparade meddelanden har ändrats.")
    packet_map = {p.event_id: p for p in packets}
    originals_by_id = {m["event_id"]: m for m in core["matches"]}
    observations_by_id = {o.event_id: o for o in data.observations}
    expected_findings = [Finding(code=code, severity="limitation", event_id=None) for code in LIMITATIONS]
    for proposal in core["proposals"]:
        event = proposal["event_id"]
        code = _proposal_problem(proposal, originals_by_id[event], packet_map[event], observations_by_id[event], data)
        if code:
            expected_findings.append(Finding(code=code, severity="blocker", event_id=event))
    _require(review.findings == tuple(expected_findings), "sparade fyndkoder motsäger källorna eller förslagen.")
    for proposal in final:
        packet = packet_map[proposal["event_id"]]
        _require(not packet.rejections, "kvarvarande förslag gäller en blockerad match.")
        match = next(m for m in analysis["matches"] if m["event_id"] == proposal["event_id"])
        fresh = {s.book for s in packet.sources if s.fresh}
        _require({proposal["book"], *match["decision"].get("reference_books", [])} <= fresh,
                 "kvarvarande förslag använder ofärsk källa.")
    final_money = _money(data, final, core["simulated_cost_ore"])
    _require(analysis["total_stake_ore"] == final_money.total_stake_ore
             and analysis["simulated_cost_ore"] == core["simulated_cost_ore"], "slutliga belopp stämmer inte.")
    _require(review.steps == _steps(data, contract, core, packets, final, review.findings),
             "stegets input, fakta, status eller begränsningar stämmer inte.")
