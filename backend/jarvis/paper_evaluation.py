"""Ny deterministisk omräkning, därefter separat hypotetisk avräkning."""
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .betting_demo import settle_bet, summary
from .odds_lab import Result, canonical, digest
from .paper_data import IDENTITY, IsoTime, PaperInput, StrictData, reference
from .paper_review import build_review

EVALUATION_VERSION = 'paper-evaluation-v1'
RESULT_BYTES = 9000
RECOMPUTATION = ('Ny deterministisk beräkning från indata med paper-review-v1 och samma öppna checksumma som granskningen du såg. '
    'Checksumman är inte signerad och bevisar inte att beslutet sparades före matchen. Ändrade filer kan ge en ny giltig hash.')
SELECTION_LIMITS = [
    'En enskild fil kan inte skilja efterhandsurval från förhandsurval. 20 matcher är ett tekniskt batchtak, inget statistiskt underlag.',
    'Påhittade fångsttider på stängningsodds kan passera strukturella kontroller.',
    'Filer kan ändras och prövas om; exporten är vald av användaren och inget revisionssäkert arkiv.',
    'Datakostnader är manuellt deklarerade och behöver inte vara fullständiga.',
]


class ReportMismatch(ValueError):
    pass


class PaperResult(StrictData):
    event_id: str = Field(pattern=IDENTITY, strict=True)
    status: Literal['final', 'void']
    home_score: int | None = Field(strict=True, ge=0, le=100)
    away_score: int | None = Field(strict=True, ge=0, le=100)
    finished_at: IsoTime
    source_url: str = Field(strict=True, min_length=10, max_length=300)
    _url = field_validator('source_url')(reference)

    @model_validator(mode='after')
    def score_rule(self):
        return Result.scores(self)


class PaperResults(StrictData):
    version: Literal['paper-results-v1']
    dataset_id: str = Field(pattern=IDENTITY, strict=True)
    records: tuple[PaperResult, ...] = Field(max_length=20)

    @model_validator(mode='after')
    def bounds(self):
        if len({r.event_id for r in self.records}) != len(self.records):
            raise ValueError('Dubblett av resultat-ID.')
        if len(canonical(self.model_dump(mode='json')).encode('utf-8')) > RESULT_BYTES:
            raise ValueError('Resultat överstiger 9000 UTF-8-byte.')
        return self


def _settle_track(proposals, results, input, rules):
    by_id = {r.event_id: r for r in results.records}
    bets = []
    for proposal in proposals:
        result = by_id.get(proposal['event_id'])
        bet = {**proposal, 'state': 'open', 'profit_ore': None, 'return_ore': None}
        if result is not None:
            bet.update(settle_bet(proposal, result.model_dump(mode='json')))
            bet['result'] = result.model_dump(mode='json')
        bets.append(bet)
    costs = [{'amount_ore': r.data_cost_ore} for r in input.records]
    total = summary(rules['initial_bankroll_ore'], costs, bets)
    pending = sum(b['state']=='open' for b in bets)
    return {'summary': total, 'void_count': sum(b['state']=='void' for b in bets), 'pending_count': pending,
        'results_without_bet': len(set(by_id)-{p['event_id'] for p in proposals}),
        'roi_bp': total['game_profit_ore']*10000//total['total_stake_ore'] if not pending and total['total_stake_ore'] else None,
        'bets': bets}


def evaluate(input: PaperInput, raw_results: dict, expected_report_hash: str):
    # Only the typed pre-match input reaches review. Result-model validation
    # starts after this new report has been fixed and its identity compared.
    review = build_review(input)
    if review['report_hash'] != expected_report_hash:
        raise ReportMismatch('Granskningen du såg motsvarar inte denna indata/version. Granska indata igen.')
    results = PaperResults.model_validate(raw_results)
    if results.dataset_id != input.dataset_id:
        raise ValueError('Resultatfilens dataset-ID matchar inte indata.')
    records = {r.event_id: r for r in input.records}
    for result in results.records:
        if result.event_id not in records:
            raise ValueError('Resultatet gäller en okänd match.')
        if result.finished_at <= records[result.event_id].starts_at:
            raise ValueError('Resultattiden måste ligga efter avspark.')
    value = {'version': EVALUATION_VERSION, 'dataset_id': input.dataset_id, 'origin': input.origin,
        'input_hash': review['input_hash'], 'report_hash': review['report_hash'],
        'results_hash': digest(results.model_dump(mode='json')), 'notice': RECOMPUTATION,
        'limitations': list(SELECTION_LIMITS), 'primary': _settle_track(review['proposals'],results,input,review['contract']['policy']),
        'baseline': _settle_track(review['baseline'],results,input,review['contract']['policy']), 'real_money_enabled': False}
    return {**value, 'evaluation_hash': digest(value)}
