"""Strikt, transportfri indata för manuellt angiven pappersgranskning."""
import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from .odds_lab import POLICY, Prices, Quote, Snapshot, canonical, digest, event_key

INPUT_VERSION = 'paper-input-v1'
INPUT_BYTES = 36000
IDENTITY = r'^[A-Za-z0-9_-]{1,80}$'
TIME = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$')


def iso_text(value):
    if not isinstance(value, str) or not TIME.fullmatch(value):
        raise ValueError('Tid kräver ISO-text med sekunder och tidszon, utan bråkdelar.')
    return value


IsoTime = Annotated[AwareDatetime, BeforeValidator(iso_text)]


def safe_text(value):
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 or ord(c) in {0x200e, 0x200f}
           or 0x202a <= ord(c) <= 0x202e or 0x2066 <= ord(c) <= 0x2069 for c in value):
        raise ValueError('Kontrolltecken och riktningsstyrning tillåts inte.')
    if not value.strip():
        raise ValueError('Tom text tillåts inte.')
    return value


def reference(value):
    safe_text(value)
    return Quote.public_reference(value)


class StrictData(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Source(StrictData):
    name: str = Field(strict=True, min_length=1, max_length=120)
    reference_url: str = Field(strict=True, min_length=10, max_length=300)
    permission_note: str = Field(strict=True, min_length=1, max_length=500)
    _text = field_validator('name', 'permission_note')(safe_text)
    _url = field_validator('reference_url')(reference)


class PaperQuote(StrictData):
    book: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,39}$', strict=True)
    source_url: str = Field(strict=True, min_length=10, max_length=300)
    updated_at: IsoTime | None
    odds: Prices
    _url = field_validator('source_url')(reference)


class PaperRecord(StrictData):
    event_id: str = Field(pattern=IDENTITY, strict=True)
    sport: Literal['football']
    market: Literal['1x2_90min']
    home: str = Field(strict=True, min_length=1, max_length=100)
    away: str = Field(strict=True, min_length=1, max_length=100)
    starts_at: IsoTime
    captured_at: IsoTime | None
    data_cost_ore: int = Field(strict=True, ge=0, le=100000)
    quotes: tuple[PaperQuote, ...] = Field(min_length=1, max_length=12)
    _text = field_validator('home', 'away')(safe_text)

    @model_validator(mode='after')
    def consistent(self):
        if self.home.strip().casefold() == self.away.strip().casefold():
            raise ValueError('Två olika lag krävs.')
        if len({q.book for q in self.quotes}) != len(self.quotes):
            raise ValueError('Duplicerad bok i samma match.')
        if not self.missing_times:
            Snapshot.model_validate(self.model_dump(mode='json'))
        return self

    @property
    def missing_times(self):
        return self.captured_at is None or any(q.updated_at is None for q in self.quotes)


class PaperInput(StrictData):
    version: Literal['paper-input-v1']
    dataset_id: str = Field(pattern=IDENTITY, strict=True)
    origin: Literal['synthetic_fixture', 'manual_unverified']
    source: Source
    records: tuple[PaperRecord, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def boundaries(self):
        if len({r.event_id for r in self.records}) != len(self.records) or len({event_key(r) for r in self.records}) != len(self.records):
            raise ValueError('Dubblett av match-ID eller lagpar på samma lokala matchdag.')
        if sum(r.data_cost_ore for r in self.records) > POLICY['initial_bankroll_ore']:
            raise ValueError('Deklarerade datakostnader överstiger låtsaskapitalet.')
        if self.origin == 'synthetic_fixture':
            urls = [self.source.reference_url, *(q.source_url for r in self.records for q in r.quotes)]
            for url in urls:
                host = urlsplit(url).hostname
                if host is None:
                    raise ValueError('Källreferensen saknar värdnamn.')
                if not (host.endswith(('.invalid', '.test')) or host in {'example.com', 'example.org', 'example.net'}):
                    raise ValueError('Syntetiskt exempel kräver reserverade URL-värdar.')
        if len(canonical(self.model_dump(mode='json')).encode('utf-8')) > INPUT_BYTES:
            raise ValueError('Indata överstiger 36000 UTF-8-byte.')
        return self


def to_snapshot(record: PaperRecord) -> Snapshot:
    if record.missing_times:
        raise ValueError('Saknade tider får inte ersättas med påhittade tidsstämplar.')
    return Snapshot.model_validate(record.model_dump(mode='json'))


def quality_record(record: PaperRecord, rules: dict):
    sources = []
    for q in record.quotes:
        age = int((record.captured_at - q.updated_at).total_seconds()) if record.captured_at is not None and q.updated_at is not None else None
        reason = ('MISSING_TIME' if age is None else 'FUTURE_QUOTE' if age < 0
                  else 'STALE_QUOTE' if age > rules['max_quote_age_seconds'] else None)
        sources.append({'book': q.book, 'source_url': q.source_url,
            'updated_at': q.model_dump(mode='json')['updated_at'], 'age_seconds': age,
            'fresh': reason is None, 'reason': reason})
    seconds = int((record.starts_at - record.captured_at).total_seconds()) if record.captured_at is not None else None
    fresh = sum(s['fresh'] for s in sources)
    return {'event_id': record.event_id, 'blocked_missing_time': record.missing_times,
        'captured_at': record.model_dump(mode='json')['captured_at'],
        'sources': sources, 'fresh_count': fresh, 'minimum_fresh_sources': rules['min_reference_books'] + 1,
        'max_quote_age_seconds': rules['max_quote_age_seconds'], 'seconds_to_kickoff': seconds,
        'too_close_to_kickoff': seconds < rules['min_seconds_before_kickoff'] if seconds is not None else None,
        'insufficient_fresh_sources': fresh < rules['min_reference_books'] + 1,
        'missing_context': ['form', 'injuries', 'lineups'], 'independence': 'unverified'}


def quality_report(data: PaperInput, rules: dict):
    content = {'input_hash': digest(data.model_dump(mode='json')),
        'records': [quality_record(r, rules) for r in sorted(data.records, key=lambda r: (r.starts_at, r.event_id))]}
    return {**content, 'quality_hash': digest(content)}
