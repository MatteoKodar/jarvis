"""Versionslåst, ren prisgranskning. Inga resultat, transporter eller DB-anrop."""
from copy import deepcopy
from decimal import Decimal

from .betting_demo import AnalysisInput, analyze_match
from .odds_lab import POLICY, digest, normalize_prices
from .paper_data import PaperInput, quality_report, to_snapshot
from .roles import ROLES

REVIEW_VERSION = 'paper-review-v1'
POLICY_SHA256 = '7e080fc3bf767ebbc1d544529c19e400947b3d5a3f6720a51c3340cd4a4e6da7'
ROLE_PIN = (
    ('researcher', 'Researcher / Fotbollsdata', '2.0.0-football'),
    ('analyst', 'Oddsanalytiker', '2.0.0-football'),
    ('finance', 'Ekonom / Risk', '2.0.0-football'),
    ('critic', 'Kritiker / Kvalitetskontroll', '2.0.0-football'),
)
BASELINE = 'home-first-accepted-book-v1'
BASELINE_DEFINITION = {
    'universe': 'Kompletta tider, minst fyra accepterade kärnkontroller och minst60sekunder till avspark.',
    'book': 'Lexikografiskt första bok med accepted=True i kärnans checks.',
    'outcome': 'home', 'price': 'home * (10000 - price_haircut_bp) // 10000',
    'stake': 'Fast stake_ore från den låsta policyn.',
    'capital': 'Egen sekventiell pott efter samma totala deklarerade kostnader; inga resultat används.',
}
INTERPRETATION = {
    'origin': 'Ursprunget är påstått. Tider och leverantör är inte oberoende verifierade.',
    'baseline': 'Baseline är en referens, aldrig en rekommendation.',
    'exposure': 'Spåren kan ha olika exponering. Resultatskillnad visar inte kausal alpha.',
    'critic': 'Noll fynd i en frisk deterministisk körning innebär inte verklig research.',
}
NOTICE = 'Regelbaserad konsistenskontroll, inte oberoende AI-bedömning. Källor och tider är inte oberoende verifierade.'
LIMITATIONS = ['Form, skador och laguppställningar saknas.', 'Källoberoende och verklig spelbarhet är inte verifierade.']


class ContractDrift(ValueError):
    """Känd version kan inte användas efter ändrad policy/rollsemantik."""


def contract():
    roles = tuple((i, ROLES.get(i, {}).get('name'), ROLES.get(i, {}).get('version')) for i, _, _ in ROLE_PIN)
    if digest(POLICY) != POLICY_SHA256 or roles != ROLE_PIN or len(ROLES) != 10:
        raise ContractDrift('Policy eller roller har ändrats. Paper-versionen måste granskas och versionshöjas.')
    return {'version': REVIEW_VERSION, 'policy': deepcopy(POLICY), 'policy_hash': POLICY_SHA256,
        'roles': [{'role_id': i, 'name': name, 'version': version} for i, name, version in ROLE_PIN],
        'baseline': BASELINE, 'baseline_definition': deepcopy(BASELINE_DEFINITION), 'notice': NOTICE}


def _candidate(event_id, decision):
    if not decision or not decision['selected']:
        return None
    return {'event_id': event_id, **{k: deepcopy(decision[k]) for k in
        ('book', 'outcome', 'paper_odds', 'stake_ore', 'reference_books')}}


def _accepted(record, rules):
    accepted = {}
    if record.missing_times:
        return accepted
    for quote in record.quotes:
        age = (record.captured_at - quote.updated_at).total_seconds()
        _, margin = normalize_prices(quote.odds)
        if 0 <= age <= rules['max_quote_age_seconds'] and Decimal('0.95') <= margin <= Decimal('1.25'):
            accepted[quote.book] = quote
    return accepted


def critic_problem(candidate, record, rules, available):
    if record.missing_times or (record.starts_at - record.captured_at).total_seconds() < rules['min_seconds_before_kickoff']:
        return 'DATA_BLOCKED'
    quotes = {q.book: q for q in record.quotes}
    used = [candidate['book'], *candidate['reference_books']]
    if any(book not in quotes for book in used):
        return 'UNKNOWN_SOURCE'
    accepted = _accepted(record, rules)
    if any(book not in accepted for book in used):
        return 'UNUSABLE_SOURCE'
    refs = candidate['reference_books']
    if len(refs) < rules['min_reference_books'] or len(set(refs)) != len(refs) or candidate['book'] in refs:
        return 'REFERENCE_MISMATCH'
    expected = getattr(quotes[candidate['book']].odds, candidate['outcome']) * (10000-rules['price_haircut_bp']) // 10000
    if type(candidate['paper_odds']) is not int or candidate['paper_odds'] != expected:
        return 'PRICE_MISMATCH'
    if type(candidate['stake_ore']) is not int or candidate['stake_ore'] != rules['stake_ore']:
        return 'STAKE_MISMATCH'
    if candidate['stake_ore'] > available:
        return 'CAPITAL_SHORTFALL'
    return None


def money(rules, cost, proposals):
    total = sum(p['stake_ore'] for p in proposals)
    return {'initial_capital_ore': rules['initial_bankroll_ore'], 'declared_data_cost_ore': cost,
        'proposal_count': len(proposals), 'total_stake_ore': total,
        'projected_available_ore': rules['initial_bankroll_ore']-cost-total}


def build_review(input: PaperInput):
    frozen = contract()
    rules = frozen['policy']
    quality = quality_report(input, rules)
    cost = sum(r.data_cost_ore for r in input.records)
    candidates, proposals, baseline, findings, cores = [], [], [], [], []
    reserved, baseline_reserved = 0, 0
    for record in sorted(input.records, key=lambda r: (r.starts_at, r.event_id)):
        available = rules['initial_bankroll_ore']-cost-reserved
        decision = None
        if not record.missing_times:
            decision = analyze_match(AnalysisInput(observation=to_snapshot(record),
                simulated_analysis_at=record.captured_at, rules=deepcopy(rules), available_capital_ore=available))
        cores.append({'event_id': record.event_id, 'available_capital_ore': available, 'decision': deepcopy(decision)})
        candidate = _candidate(record.event_id, decision)
        if candidate is not None:
            candidates.append(candidate)
            reserved += candidate['stake_ore']
            problem = critic_problem(candidate, record, rules, available)
            if problem:
                findings.append({'event_id': record.event_id, 'code': problem})
            else:
                proposals.append(deepcopy(candidate))
        if decision is not None and (record.starts_at-record.captured_at).total_seconds() >= rules['min_seconds_before_kickoff']:
            # Baseline's opportunity universe is fixed before any results exist.
            checked = {c['book'] for c in decision['checks'] if c['accepted']}
            quotes = {q.book: q for q in record.quotes}
            books = sorted(checked)
            if len(books) >= rules['min_reference_books']+1 and rules['initial_bankroll_ore']-cost-baseline_reserved >= rules['stake_ore']:
                quote = quotes[books[0]]
                baseline.append({'event_id': record.event_id, 'book': quote.book, 'outcome': 'home',
                    'paper_odds': quote.odds.home*(10000-rules['price_haircut_bp'])//10000, 'stake_ore': rules['stake_ore']})
                baseline_reserved += rules['stake_ore']
    input_hash = digest(input.model_dump(mode='json'))
    before, after, baseline_money = (money(rules,cost,values) for values in (candidates,proposals,baseline))
    facts = [
        {'quality_hash': quality['quality_hash'], 'fresh_counts': [r['fresh_count'] for r in quality['records']],
         'missing_event_ids': [r['event_id'] for r in quality['records'] if r['blocked_missing_time']]},
        {'core_decisions_hash': digest(cores), 'candidate_event_ids': [p['event_id'] for p in candidates]},
        before,
        {'removed_event_ids': [f['event_id'] for f in findings], 'findings_hash': digest(findings), 'final_money': after},
    ]
    previous = digest({'contract': frozen, 'input_hash': input_hash, 'quality_hash': quality['quality_hash']})
    steps = []
    for role, fact in zip(frozen['roles'], facts):
        step = {**role, 'input_hash': digest({'role_id': role['role_id'], 'previous_output_hash': previous}),
            'facts': fact, 'status': 'removed' if role['role_id']=='critic' and findings else 'with_limitations',
            'limitations': list(LIMITATIONS)}
        step['output_hash'] = digest(step)
        previous = step['output_hash'];steps.append(step)
    value = {'version': REVIEW_VERSION, 'dataset_id': input.dataset_id, 'origin': input.origin,
        'source': input.source.model_dump(mode='json'), 'contract': frozen, 'input_hash': input_hash,
        'quality': quality, 'core_decisions': cores, 'candidates': candidates, 'proposals': proposals,
        'baseline': baseline, 'findings': findings, 'money_before': before, 'primary_money': after,
        'baseline_money': baseline_money, 'steps': steps, 'notice': NOTICE,
        'limitations': list(LIMITATIONS), 'interpretation': deepcopy(INTERPRETATION), 'real_money_enabled': False}
    return {**value, 'report_hash': digest(value)}
