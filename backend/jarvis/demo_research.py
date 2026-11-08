"""Versionsbundet researchunderlag för offline-demot. Ingen transport eller klocka."""
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from .odds_lab import Snapshot, digest

RESEARCH_VERSION = "demo-research-v1"
NOTICE = "Regelbaserad offline-demo – ingen språkmodell, inga hämtade källor."
CONTEXT = ("form", "injuries", "lineups")
RESEARCH_POLICY = {"required_context": list(CONTEXT), "as_of_source": "captured_at", "notice": NOTICE}


class StrictFrozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchRules(StrictFrozen):
    required_context: tuple[Literal["form", "injuries", "lineups"], ...]
    as_of_source: Literal["captured_at"]
    notice: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def supported_context(self):
        if self.required_context != CONTEXT:
            raise ValueError("Researchversionens kontexttyper stämmer inte.")
        return self


class ResearchInput(StrictFrozen):
    """Fryst envelope; befintlig Snapshot är grundfryst och får inte muteras av anroparen."""
    research_version: Literal["demo-research-v1"]
    observation: Snapshot
    as_of: AwareDatetime
    max_quote_age_seconds: int = Field(strict=True, ge=0)
    min_reference_books: int = Field(strict=True, ge=1)
    research_rules: ResearchRules

    @field_validator("as_of")
    @classmethod
    def capture_representation(cls, value, info):
        observation = info.data.get("observation")
        if observation is not None and value == observation.captured_at:
            return observation.captured_at
        return value

    @model_validator(mode="after")
    def captured_clock(self):
        if self.as_of != self.observation.captured_at:
            raise ValueError("Researchens simulerade tid måste vara underlagets fångsttid.")
        return self


class ResearchSource(StrictFrozen):
    book: str
    source_url: str
    updated_at: AwareDatetime
    age_seconds: float = Field(allow_inf_nan=False)
    fresh: bool = Field(strict=True)
    reason: Literal["FUTURE_QUOTE", "STALE_QUOTE"] | None


class ResearchContent(StrictFrozen):
    research_version: Literal["demo-research-v1"]
    data_kind: Literal["synthetic_demo"]
    event_id: str
    observation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of: AwareDatetime
    starts_at: AwareDatetime
    seconds_to_kickoff: float = Field(allow_inf_nan=False)
    max_quote_age_seconds: int = Field(strict=True, ge=0)
    minimum_fresh_sources: int = Field(strict=True, ge=2)
    sources: tuple[ResearchSource, ...]
    fresh_count: int = Field(strict=True, ge=0)
    missing_context: tuple[Literal["form", "injuries", "lineups"], ...]
    source_independence: Literal["unverified"]
    rejections: tuple[Literal["KICKOFF_PASSED", "INSUFFICIENT_FRESH_SOURCES"], ...]
    notice: str

    @model_validator(mode="after")
    def facts_match(self):
        if (self.fresh_count != sum(source.fresh for source in self.sources)
                or len({source.book for source in self.sources}) != len(self.sources)
                or self.seconds_to_kickoff != (self.starts_at - self.as_of).total_seconds()
                or self.missing_context != CONTEXT):
            raise ValueError("Researchpaketets fakta är motsägelsefulla.")
        for source in self.sources:
            age = (self.as_of - source.updated_at).total_seconds()
            reason = "FUTURE_QUOTE" if age < 0 else "STALE_QUOTE" if age > self.max_quote_age_seconds else None
            if (source.age_seconds != age or source.fresh != (0 <= age <= self.max_quote_age_seconds)
                    or source.reason != reason):
                raise ValueError("Researchpaketets offertkontroll stämmer inte.")
        expected = []
        if self.seconds_to_kickoff <= 0:
            expected.append("KICKOFF_PASSED")
        if self.fresh_count < self.minimum_fresh_sources:
            expected.append("INSUFFICIENT_FRESH_SOURCES")
        if self.rejections != tuple(expected):
            raise ValueError("Researchpaketets avvisningsskäl stämmer inte.")
        return self


class ResearchPacket(ResearchContent):
    packet_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def checksum(self):
        if digest(self.model_dump(mode="json", exclude={"packet_hash"})) != self.packet_hash:
            raise ValueError("Researchpaketets innehållshash stämmer inte.")
        return self


def make_input(observation: Snapshot, rules: dict, research_rules: dict) -> ResearchInput:
    return ResearchInput(research_version=RESEARCH_VERSION, observation=observation,
                         as_of=observation.captured_at,
                         max_quote_age_seconds=rules["max_quote_age_seconds"],
                         min_reference_books=rules["min_reference_books"],
                         research_rules=ResearchRules.model_validate(research_rules))


def build_packet(data: ResearchInput) -> ResearchPacket:
    observation = data.observation
    sources = []
    for quote in observation.quotes:
        age = (data.as_of - quote.updated_at).total_seconds()
        fresh = 0 <= age <= data.max_quote_age_seconds
        reason = None if fresh else "FUTURE_QUOTE" if age < 0 else "STALE_QUOTE"
        sources.append(ResearchSource(book=quote.book, source_url=quote.source_url,
            updated_at=quote.updated_at, age_seconds=age, fresh=fresh, reason=reason))
    count = sum(source.fresh for source in sources)
    seconds = (observation.starts_at - data.as_of).total_seconds()
    rejections = []
    if seconds <= 0:
        rejections.append("KICKOFF_PASSED")
    if count < data.min_reference_books + 1:
        rejections.append("INSUFFICIENT_FRESH_SOURCES")
    content = ResearchContent(research_version=data.research_version, data_kind="synthetic_demo",
        event_id=observation.event_id, observation_hash=digest(observation.model_dump(mode="json")),
        as_of=data.as_of, starts_at=observation.starts_at, seconds_to_kickoff=seconds,
        max_quote_age_seconds=data.max_quote_age_seconds, minimum_fresh_sources=data.min_reference_books + 1,
        sources=tuple(sources), fresh_count=count, missing_context=data.research_rules.required_context,
        source_independence="unverified", rejections=tuple(rejections), notice=data.research_rules.notice)
    value = content.model_dump(mode="json")
    return ResearchPacket(**value, packet_hash=digest(value))
