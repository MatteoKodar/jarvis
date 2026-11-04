"""Lokalt A0: rena funktioner och uttryckligen syntetiska svar, inga adaptrar."""
import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from .models import Strict

VERSION = "a0-1.0.0"
NOTICE = "A0 · Simulerade svar och syntetiska källor. Ingen modellkvalitet eller marknadsefterfrågan har mätts."
LEVELS = ("avsta", "vidare_research", "billigt_experiment")
LABELS = {"avsta": "Avstå", "vidare_research": "Vidare research", "billigt_experiment": "Billigt experiment"}
FLOW_NAMES = {"S1": "Ensam AI", "S2": "Självgranskning", "RK": "Researcher + Kritiker"}
INSTRUCTIONS = {
    "researcher": "A0: lämna ett strukturerat förutbestämt exempel med stabila påstående-ID:n och källutdrag. Inget modell- eller nätverksanrop.",
    "self_review": "A0: simulera en granskning av föregående strukturerade rapport. Inget modell- eller nätverksanrop.",
    "critic": "A0: simulera ett separat granskningssteg. Ett kritikeromdöme är inte verifierad sanning. Inget modell- eller nätverksanrop.",
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class Source(Strict):
    id: str = Field(pattern=r"^[A-Z][A-Z0-9_-]{0,39}$")
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=8000)
    origin: str = Field(min_length=1, max_length=100)
    synthetic: Literal[True] = True


class SourcePackage(Strict):
    id: str = Field(pattern=r"^A0-[1-3]$")
    title: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=1000)
    sources: list[Source] = Field(min_length=1, max_length=10)
    synthetic: Literal[True] = True

    @model_validator(mode="after")
    def limits(self):
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("Käll-ID:n måste vara unika.")
        if len(canonical(self.model_dump()).encode("utf-8")) > 64000:
            raise ValueError("Källpaketet är för stort. Inget innehåll kapas.")
        return self


class Citation(Strict):
    source_id: str = Field(min_length=1, max_length=40)
    quote: str = Field(min_length=1, max_length=2000)
    start_byte: int = Field(ge=0)
    end_byte: int = Field(gt=0)


class Claim(Strict):
    id: str = Field(pattern=r"^P[1-8]$")
    text: str = Field(min_length=1, max_length=1200)
    kind: Literal["observation", "hypotes", "forslag"]
    essential: bool
    citations: list[Citation] = Field(max_length=3)


class Report(Strict):
    claims: list[Claim] = Field(max_length=8)
    recommendation: Literal["avsta", "vidare_research", "billigt_experiment"]
    depends_on: list[str] = Field(max_length=8)

    @model_validator(mode="after")
    def dependencies(self):
        ids = [c.id for c in self.claims]
        if len(ids) != len(set(ids)) or len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("Påstående-ID:n och beroenden måste vara unika.")
        if not set(self.depends_on) <= set(ids):
            raise ValueError("Rekommendationen hänvisar till okända påståenden.")
        if self.recommendation != "avsta" and not self.depends_on:
            raise ValueError("En positiv rekommendation kräver uttryckliga faktaberoenden.")
        if any(c.id in self.depends_on and (c.kind != "observation" or not c.citations or not c.essential) for c in self.claims):
            raise ValueError("Hypoteser och ociterade eller oviktiga påståenden får inte bära rekommendationen.")
        return self


class ClaimReview(Strict):
    claim_id: str = Field(pattern=r"^P[1-8]$")
    status: Literal["stod", "indirekt", "saknas", "motsagt"]
    reason: str = Field(min_length=1, max_length=1500)


class Review(Strict):
    claims: list[ClaimReview] = Field(max_length=8)
    recommendation: Literal["avsta", "vidare_research", "billigt_experiment"]


def validate_citations(package: SourcePackage, report: Report):
    """Kontrollerar bytepositioner och citat, INTE citatets semantiska stöd."""
    sources = {s.id: s.text.encode("utf-8") for s in package.sources}
    for claim in report.claims:
        if len({canonical(c.model_dump()) for c in claim.citations}) != len(claim.citations):
            raise ValueError("Samma källhänvisning får inte dubbleras.")
        for citation in claim.citations:
            text = sources.get(citation.source_id)
            if text is None:
                raise ValueError("Okänt käll-ID.")
            if not 0 <= citation.start_byte < citation.end_byte <= len(text):
                raise ValueError("Källutdragets bytepositioner är ogiltiga.")
            if text[citation.start_byte:citation.end_byte] != citation.quote.encode("utf-8"):
                raise ValueError("Källutdraget stämmer inte med den sparade texten.")


def revise(package: SourcePackage, report: Report, review: Review | None):
    validate_citations(package, report)
    checks = {}
    if review is not None:
        checks = {c.claim_id: c for c in review.claims}
        if len(checks) != len(review.claims) or set(checks) != {c.id for c in report.claims}:
            raise ValueError("Granskningen måste täcka varje påstående exakt en gång.")
    retained = [c for c in report.claims if review is None or checks[c.id].status == "stod"]
    rejected = [c for c in report.claims if c not in retained]
    missing = sorted(set(report.depends_on) - {c.id for c in retained})
    level = report.recommendation
    if review is not None:
        level = LEVELS[min(LEVELS.index(level), LEVELS.index(review.recommendation))]
    if missing:
        level = "avsta"
    # All text is rendered from retained records; no stale narrative survives.
    sections = [LABELS[level]]
    if missing:
        sections.append("Nödvändigt stöd saknas efter granskning: " + ", ".join(missing) + ".")
    sections.extend(c.id + ": " + c.text for c in retained)
    return {
        "recommendation": level,
        "claims": [c.model_dump() for c in retained],
        "removed_ids": [c.id for c in rejected],
        "missing_dependencies": missing,
        "text": "\n\n".join(sections),
        "support_verified": False,
    }


def _citation(source):
    return Citation(source_id=source.id, quote=source.text, start_byte=0, end_byte=len(source.text.encode("utf-8")))


def examples():
    """Öppna demonstrationsdata, aldrig ett dolt facit för ett verkligt försök."""
    definitions = [
        ("A0-1", "Föreningars utlägg", "Skilj ett listat pris från verifierade köp.", [
            ("K1", "Fiktiv arbetsnotering", "I detta påhittade exempel beskriver tre föreningspersoner tidsåtgång för utlägg.", "exempel-personer"),
            ("K2", "Fiktiv prislista", "Ett påhittat verktyg erbjuds för 29 kronor per månad. Uppgifter om köp saknas.", "exempel-leverantor"),
        ], "Personerna i exemplet beskriver tidsåtgång för utlägg.",
         "Kunder har bevisligen köpt verktyget för 29 kronor i månaden.", "billigt_experiment"),
        ("A0-2", "Ändringar i kursbokningar", "Se att en granskare också kan underkänna ett stött påstående.", [
            ("K1", "Fiktiv kursnotering", "I detta påhittade exempel beskriver två kursledare dubbel registrering när bokningar ändras.", "exempel-kursledare"),
            ("K2", "Fiktiv avgränsning", "Ingen betalningsvilja eller försäljning har undersökts i exemplet.", "exempel-avgransning"),
        ], "Kursledarna i exemplet beskriver dubbel registrering vid ändringar.", None, "vidare_research"),
        ("A0-3", "Offertuppföljning", "Visa hur otillräckligt underlag kan leda till avstående.", [
            ("K1", "Fiktivt tomt underlag", "Detta påhittade underlag innehåller inga observationer av hantverksföretags offertuppföljning.", "exempel-underlag"),
            ("K2", "Fiktiv fråga", "Det är okänt om problemet förekommer eller om någon vill betala för en lösning.", "exempel-fraga"),
        ], "Underlaget innehåller inga observerade kundproblem.", None, "avsta"),
    ]
    result = []
    for ident, title, question, raw_sources, first, second, recommendation in definitions:
        package = SourcePackage(id=ident, title=title, question=question, sources=[
            Source(id=i, title=t, text=x, origin=o) for i, t, x, o in raw_sources])
        claims = [Claim(id="P1", text=first, kind="observation", essential=True, citations=[_citation(package.sources[0])])]
        if second:
            claims.append(Claim(id="P2", text=second, kind="observation", essential=True, citations=[_citation(package.sources[1])]))
        report = Report(claims=claims, recommendation=recommendation,
                        depends_on=[c.id for c in claims] if recommendation != "avsta" else [])
        reviews = {}
        for flow in ("S2", "RK"):
            checks = [ClaimReview(claim_id="P1", status="stod", reason="Simulerat omdöme: utdraget beskriver observationen i exemplet.")]
            if second:
                checks.append(ClaimReview(claim_id="P2", status="saknas", reason="Simulerat omdöme: ett erbjudet pris visar inte att någon köpt produkten."))
            if ident == "A0-2" and flow == "RK":
                checks[0] = ClaimReview(claim_id="P1", status="saknas", reason="Avsiktligt felaktigt simulerat omdöme: demonstrerar en obefogad invändning.")
            reviews[flow] = Review(claims=checks, recommendation="avsta" if second else recommendation)
        result.append({"package": package.model_dump(), "report": report.model_dump(),
                       "reviews": {k: v.model_dump() for k, v in reviews.items()}})
    return result


def suite():
    return {"version": VERSION, "stage": "A0", "notice": NOTICE, "instructions": INSTRUCTIONS,
            "examples": examples(), "max_reports": 9, "max_steps": 15}


def build_snapshot(role_specs):
    frozen = suite()
    reports = []
    for example in frozen["examples"]:
        package = SourcePackage.model_validate(example["package"])
        original = Report.model_validate(example["report"])
        validate_citations(package, original)
        for flow, name in FLOW_NAMES.items():
            review = Review.model_validate(example["reviews"][flow]) if flow != "S1" else None
            first_input = {"instructions": INSTRUCTIONS["researcher"], "package": package.model_dump()}
            steps = [{"role": "researcher", "kind": "simulated", "input": first_input, "output": original.model_dump()}]
            if review is not None:
                steps.append({"role": "researcher" if flow == "S2" else "critic", "kind": "simulated",
                              "input": {"instructions": INSTRUCTIONS["self_review" if flow == "S2" else "critic"],
                                        "package": package.model_dump(), "report": original.model_dump()},
                              "output": review.model_dump()})
            reports.append({"id": package.id + "-" + flow, "topic_id": package.id, "flow": flow,
                            "name": name, "original": original.model_dump(),
                            "review": review.model_dump() if review else None,
                            "final": revise(package, original, review), "steps": steps})
    return {"stage": "A0", "version": VERSION, "notice": NOTICE, "suite": frozen,
            "suite_hash": digest(frozen), "roles_snapshot": role_specs,
            "packages": [e["package"] for e in frozen["examples"]], "reports": reports,
            "report_count": len(reports), "simulated_steps": sum(len(r["steps"]) for r in reports),
            "external_calls": 0, "cost_ore": 0, "model": None,
            "quality_result": "Inte utvärderad. Svaren är förutbestämda exempel, inklusive avsiktliga fel.",
            "next_stages": {"A1": "Blockerad: verkliga källpaket, fryst metod, anropsskydd, prisprofil och ägarbeslut saknas.",
                            "B": "Blockerad: A1-beslut och säker sökintegration krävs."}}
