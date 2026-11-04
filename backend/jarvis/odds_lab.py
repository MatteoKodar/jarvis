"""Fotbollens papperslabb: ren beräkning, inga nätverks- eller spelverktyg."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, localcontext
from statistics import median
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

VERSION = "football-paper-v1"
OUTCOMES = ("home", "draw", "away")
POLICY = {
    "version": VERSION, "sport": "football", "market": "1x2_90min",
    "settlement": "Ordinarie tid inklusive tilläggstid; exklusive förlängning och straffar.",
    "initial_bankroll_ore": 100000, "stake_ore": 1000,
    "min_reference_books": 3, "max_quote_age_seconds": 120,
    "max_import_delay_seconds": 60, "min_seconds_before_kickoff": 60,
    "min_edge_bp": 500, "max_edge_bp": 3000, "price_haircut_bp": 100,
    "max_snapshots": 1000, "min_settled_for_review": 100, "min_days_for_review": 30,
    "selection": "Högst en signal per match; högst beräknad avvikelse, sedan käll-ID och utfall.",
    "reference": "Median av övriga källors marginalnormaliserade sannolikheter. Ingen sann sannolikhet.",
    "costs": "Manuellt angivna datakostnader; fullständighet och faktura är inte verifierade.",
    "real_money_enabled": False,
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Action(Strict):
    action_id: str = Field(min_length=36, max_length=36)

    @field_validator("action_id")
    @classmethod
    def valid_action(cls, value):
        return str(UUID(value))


class Start(Action):
    kind: Literal["synthetic", "forward"]
    policy_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class Prices(Strict):
    # Decimalodds * 10 000. Endast heltal; ingen binär avrundning i pengaberäkning.
    home: int = Field(strict=True, ge=10001, le=1000000)
    draw: int = Field(strict=True, ge=10001, le=1000000)
    away: int = Field(strict=True, ge=10001, le=1000000)


class Quote(Strict):
    book: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    source_url: str = Field(min_length=10, max_length=1000)
    updated_at: AwareDatetime
    odds: Prices

    @field_validator("source_url")
    @classmethod
    def public_reference(cls, value):
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("Ange en http(s)-referens utan credentials, query eller fragment. Ingen URL hämtas av labbet.")
        return value


class Snapshot(Strict):
    event_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    sport: Literal["football"]
    market: Literal["1x2_90min"]
    home: str = Field(min_length=1, max_length=100)
    away: str = Field(min_length=1, max_length=100)
    starts_at: AwareDatetime
    captured_at: AwareDatetime
    data_cost_ore: int = Field(strict=True, ge=0, le=1000000)
    quotes: list[Quote] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def identity(self):
        if not self.home.strip() or not self.away.strip() or self.home.strip().casefold() == self.away.strip().casefold():
            raise ValueError("Två olika lag krävs.")
        if len({q.book for q in self.quotes}) != len(self.quotes):
            raise ValueError("Samma käll-ID får inte räknas flera gånger.")
        if len(canonical(self.model_dump(mode="json")).encode("utf-8")) > 30000:
            raise ValueError("Ögonblicksbilden är för stor.")
        return self


class ImportSnapshot(Action):
    snapshot: Snapshot


class Result(Action):
    event_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    market: Literal["1x2_90min"]
    status: Literal["final", "void"]
    home_score: int | None = Field(default=None, strict=True, ge=0, le=100)
    away_score: int | None = Field(default=None, strict=True, ge=0, le=100)
    finished_at: AwareDatetime
    source_url: str = Field(min_length=10, max_length=1000)

    _url = field_validator("source_url")(Quote.public_reference.__func__)

    @model_validator(mode="after")
    def scores(self):
        if self.status == "final" and (self.home_score is None or self.away_score is None):
            raise ValueError("Slutresultat efter ordinarie tid krävs.")
        if self.status == "void" and (self.home_score is not None or self.away_score is not None):
            raise ValueError("Makulerad match ska inte ha ett slutresultat.")
        return self


class Cost(Action):
    amount_ore: int = Field(strict=True, ge=1, le=1000000)
    note: str = Field(min_length=3, max_length=500)


def event_key(snapshot):
    # Samma lagpar och lokala matchdag får inte en ny chans via ny tid eller nytt ID.
    teams = sorted([" ".join(snapshot.home.casefold().split()), " ".join(snapshot.away.casefold().split())])
    return digest([snapshot.sport, snapshot.market, snapshot.starts_at.astimezone(ZoneInfo("Europe/Stockholm")).date().isoformat(), teams])


def normalize_prices(prices):
    """Ren prisberäkning; gör inget antagande om tid eller tillgänglighet."""
    with localcontext() as ctx:
        ctx.prec = 40
        inverse = {k: Decimal(10000) / getattr(prices, k) for k in OUTCOMES}
        total = sum(inverse.values())
        return {k: v / total for k, v in inverse.items()}, total


def analyze(snapshot, observed_at, available_ore):
    """En offert jämförs alltid med minst tre ANDRA, färska kompletta källor."""
    valid, checks = [], []
    for quote in snapshot.quotes:
        age = (snapshot.captured_at - quote.updated_at).total_seconds()
        reason = None
        if not 0 <= age <= POLICY["max_quote_age_seconds"]:
            reason = "För gammal offert eller offert från framtiden."
        probabilities, total = normalize_prices(quote.odds)
        if not Decimal("0.95") <= total <= Decimal("1.25"):
            reason = "Avvikande marginal; offerten behöver kontrolleras."
        checks.append({"book": quote.book, "accepted": reason is None, "reason": reason,
                       "overround_bp": int(total * 10000)})
        if reason is None:
            valid.append((quote, probabilities))
    base = {"selected": False, "reason": "Ingen avvikelse klarar de låsta provreglerna.", "checks": checks}
    if (snapshot.starts_at - observed_at).total_seconds() < POLICY["min_seconds_before_kickoff"]:
        return {**base, "reason": "För nära avspark eller redan startad match."}
    return select_price_signal(valid, available_ore, checks)


def select_price_signal(valid, available_ore, checks):
    """Delad matematik för kontrollerade nutidsofferter och märkt arkivanalys.

    Anroparen ansvarar för tids-/källkontroll; denna funktion gör ingen sådan.
    """
    base = {"selected": False, "reason": "Ingen avvikelse klarar de låsta provreglerna.", "checks": checks}
    if len(valid) < POLICY["min_reference_books"] + 1:
        return {**base, "reason": "Färre än fyra giltiga källor; tre andra jämförelsekällor krävs."}
    candidates = []
    with localcontext() as ctx:
        ctx.prec = 40
        for quote, _ in valid:
            references = [(other, probs) for other, probs in valid if other.book != quote.book]
            for outcome in OUTCOMES:
                probability = median(probs[outcome] for _, probs in references)
                offered = getattr(quote.odds, outcome)
                paper_odds = offered * (10000 - POLICY["price_haircut_bp"]) // 10000
                edge = int(((probability * paper_odds / 10000 - 1) * 10000).to_integral_value(rounding=ROUND_FLOOR))
                if POLICY["min_edge_bp"] <= edge <= POLICY["max_edge_bp"]:
                    candidates.append({"book": quote.book, "outcome": outcome, "quoted_odds": offered,
                                       "paper_odds": paper_odds, "edge_bp": edge,
                                       "reference_probability_ppm": int(probability * 1000000),
                                       "reference_books": sorted(q.book for q, _ in references)})
    if not candidates:
        return base
    if available_ore < POLICY["stake_ore"]:
        return {**base, "reason": "Låtsaskapitalet täcker inte ytterligare en fast insats."}
    chosen = sorted(candidates, key=lambda r: (-r["edge_bp"], r["book"], r["outcome"]))[0]
    return {**base, **chosen, "selected": True, "stake_ore": POLICY["stake_ore"],
            "reason": "Regelbaserad oddssignal. Sannolikhet, tillgänglighet och lönsamhet är inte verifierade."}


def settlement(decision, result):
    if not decision["selected"]:
        return {"state": "no_signal", "profit_ore": 0, "return_ore": 0}
    stake = decision["stake_ore"]
    if result.status == "void":
        return {"state": "void", "profit_ore": 0, "return_ore": stake}
    outcome = "home" if result.home_score > result.away_score else "away" if result.away_score > result.home_score else "draw"
    payout = stake * decision["paper_odds"] // 10000 if outcome == decision["outcome"] else 0
    return {"state": "won" if payout else "lost", "profit_ore": payout - stake, "return_ore": payout}


def example_snapshot(at=None):
    at = at or datetime.now(timezone.utc).replace(microsecond=0)
    return {"event_id": "byt-till-verkligt-match-id", "sport": "football", "market": "1x2_90min",
            "home": "EXEMPEL Hemmalag", "away": "EXEMPEL Bortalag",
            "starts_at": (at + timedelta(hours=3)).isoformat(), "captured_at": at.isoformat(), "data_cost_ore": 0,
            "quotes": [{"book": f"kalla_{i}", "source_url": f"https://example.invalid/kalla-{i}",
                        "updated_at": at.isoformat(), "odds": {"home": 25000 if i == 1 else 20000, "draw": 34000, "away": 36000}}
                       for i in range(1, 5)]}
