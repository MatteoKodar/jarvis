"""Persisted review workflow, old rows and adversarial binding tests; temporary DB only."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest

from jarvis import betting_demo as core, betting_demo_service as service
from jarvis import demo_review as review, demo_research as research
from jarvis.db import connect
from jarvis.odds_lab import digest, canonical, Snapshot
from jarvis.roles import ROLES

BASE = '/api/betting-demo/sessions'
GOLDEN = json.loads((Path(__file__).parent/'fixtures/betting_demo_v1_golden.json').read_text(encoding='utf-8'))


def post(client, path='', **body):
    return client.post(BASE+path, json={'action_id':str(uuid4()), **body})


def create(client):
    assert client.post('/api/control', json={'state':'running'}).status_code == 200
    response = post(client)
    assert response.status_code == 200, response.text
    return response.json()['id']


def raw(sid):
    with connect() as c:
        row = dict(c.execute('SELECT * FROM betting_demo_sessions WHERE id=?',(sid,)).fetchone())
    for key in ('frozen','analysis','summary'):
        row[key] = json.loads(row[key]) if row[key] else None
    return row


def counts(sid):
    with connect() as c:
        return {name:c.execute('SELECT COUNT(*) FROM betting_demo_'+name+' WHERE session_id=?',(sid,)).fetchone()[0]
                for name in ('costs','bets','actions','events')}


def bound(sid):
    a = raw(sid)['analysis']
    return {key:a[key] for key in ('proposal_version','proposal_hash')}


def analyzed(client, approve=False):
    sid = create(client)
    response = post(client, '/'+sid+'/analyze')
    assert response.status_code == 200, response.text
    if approve:
        assert post(client, '/'+sid+'/decision', decision='approved', **bound(sid)).status_code == 200
    return sid


def write_json(sid, column, value, reseal=True):
    assert column in ('frozen','analysis')
    with connect(True) as c:
        if column == 'frozen' and reseal:
            c.execute('UPDATE betting_demo_sessions SET frozen=?,frozen_hash=? WHERE id=?',(canonical(value),digest(value),sid))
        else:
            if column == 'analysis' and reseal:
                value['proposal_hash'] = digest({k:v for k,v in value.items() if k!='proposal_hash'})
            c.execute('UPDATE betting_demo_sessions SET '+column+'=? WHERE id=?',(canonical(value),sid))


def seed_legacy(client, state):
    assert client.post('/api/control', json={'state':'running'}).status_code == 200
    with connect(True) as c:
        for table, rows in GOLDEN['rows'][state].items():
            for row in rows:
                c.execute('INSERT INTO betting_demo_'+table+'('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
    return GOLDEN['session_id']


def test_wrapper_only_adds_review_contract_and_never_rebuilds_core(monkeypatch):
    base = core.build_scenario(); before = deepcopy(base)
    monkeypatch.setattr(core, 'build_scenario', lambda: (_ for _ in ()).throw(AssertionError('no rebuild')))
    value = review.build_scenario_v2(base)
    assert base == before
    assert {key:value[key] for key in base} == before
    assert set(value)-set(base) == set(review.META_KEYS)
    assert [r['role_id'] for r in value['review_roles']] == ['researcher','analyst','finance','critic']
    assert len(ROLES) == 10


def test_v2_preserves_core_golden_and_standard_economy(client):
    sid = analyzed(client, approve=True)
    a = raw(sid)['analysis']
    assert a['proposal_version'] == 2
    assert a['core_analysis'] == GOLDEN['analysis']
    assert a['analysis_input_hash'] == GOLDEN['analysis']['analysis_input_hash']
    assert a['core_proposal_hash'] == GOLDEN['analysis']['proposal_hash']
    assert a['proposal_hash'] != a['core_proposal_hash']
    assert a['proposals'] == GOLDEN['analysis']['proposals']
    assert a['messages'] == GOLDEN['analysis']['messages']
    assert [p['fresh_count'] for p in a['research']['packets']] == [4,4,4,4,0,3,4]
    assert [s['role_id'] for s in a['review']['steps']] == list(review.ROLE_ORDER)
    assert a['review']['steps'][2]['facts']['total_stake_ore'] == 4000
    assert a['review']['steps'][3]['facts']['final_money']['simulated_cost_ore'] == 140
    assert post(client, '/'+sid+'/simulate', **bound(sid)).status_code == 200
    assert post(client, '/'+sid+'/settle').status_code == 200
    assert raw(sid)['summary'] == GOLDEN['final_summary']


@pytest.mark.parametrize('state',['created','analyzed'])
def test_golden_legacy_rows_keep_exact_views_analysis_and_settlement(client, monkeypatch, state):
    sid = seed_legacy(client,state)
    monkeypatch.setattr(service,'now',lambda:GOLDEN['recorded_at'])
    assert client.get(BASE+'/'+sid).json() == GOLDEN['views'][state]
    if state=='created':
        assert post(client,'/'+sid+'/analyze').status_code == 200
    assert raw(sid)['analysis'] == GOLDEN['analysis']
    assert client.get(BASE+'/'+sid).json() == GOLDEN['views']['analyzed']
    monkeypatch.setattr(review,'verify_saved_chain',lambda *a:(_ for _ in ()).throw(AssertionError('legacy skip')))
    assert post(client,'/'+sid+'/decision',decision='approved',**bound(sid)).status_code == 200
    assert post(client,'/'+sid+'/simulate',**bound(sid)).status_code == 200
    assert post(client,'/'+sid+'/settle').status_code == 200
    assert client.get(BASE+'/'+sid).json() == GOLDEN['views']['settled']


@pytest.mark.parametrize('operation,state',[('analyze','created'),('decision','analyzed'),('simulate','approved')])
def test_unknown_workflow_is_readable_but_cannot_write(client, operation, state):
    sid = create(client) if state=='created' else analyzed(client, approve=state=='approved')
    frozen = raw(sid)['frozen'];frozen['workflow_version']='future-review-v99';write_json(sid,'frozen',frozen)
    before = raw(sid); before_counts=counts(sid)
    body = {} if operation=='analyze' else bound(sid)
    if operation=='decision':body['decision']='approved'
    assert client.get(BASE+'/'+sid).status_code == 200
    assert post(client,'/'+sid+'/'+operation,**body).status_code == 409
    assert raw(sid)==before and counts(sid)==before_counts


def _reseal_review(sid, analysis):
    row=raw(sid);data=core.analysis_input(row['frozen']);contract=review.contract_from_frozen(row['frozen'])
    original=analysis['core_analysis'];original['proposal_hash']=digest({k:v for k,v in original.items() if k!='proposal_hash'})
    analysis['core_proposal_hash']=original['proposal_hash']
    packets=tuple(research.ResearchPacket.model_validate(p) for p in analysis['research']['packets'])
    findings=tuple(review.Finding.model_validate(f) for f in analysis['review']['findings'])
    analysis['review']['steps']=[s.model_dump(mode='json') for s in review._steps(data,contract,original,packets,analysis['proposals'],findings)]
    write_json(sid,'analysis',analysis)


@pytest.mark.parametrize('operation',['decision','simulate'])
def test_consistently_resealed_prices_cannot_override_frozen_quote(client,operation):
    sid=analyzed(client,approve=operation=='simulate');a=raw(sid)['analysis']
    for layer in (a,a['core_analysis']):
        layer['proposals'][0]['paper_odds']=99999
        layer['matches'][0]['decision']['paper_odds']=99999
    _reseal_review(sid,a)
    if operation=='simulate':
        # Full-write attacker also forges the existing decision binding; hashes
        # are not signatures. The source-consistency guard must still reject it.
        with connect(True) as c:c.execute('UPDATE betting_demo_sessions SET decision_hash=? WHERE id=?',(a['proposal_hash'],sid))
    before=counts(sid);before_raw=raw(sid);body=bound(sid)
    if operation=='decision':body['decision']='approved'
    response=post(client,'/'+sid+'/'+operation,**body)
    assert response.status_code==409 and 'fyndkoder' in response.json()['detail']
    assert counts(sid)==before and raw(sid)==before_raw


@pytest.mark.parametrize('fault',['missing_packet','bad_packet_hash','wrong_roles','wrong_total','duplicate_source'])
def test_analyze_faults_roll_back_every_cost_and_event(client, monkeypatch, fault):
    sid=create(client)
    if fault=='duplicate_source':
        frozen=raw(sid)['frozen'];frozen['observations'][0]['quotes'][1]['book']=frozen['observations'][0]['quotes'][0]['book'];write_json(sid,'frozen',frozen)
    elif fault in ('missing_packet','bad_packet_hash'):
        original=review.build_packets
        def broken(*args):
            values=list(original(*args))
            if fault=='missing_packet':return values[:-1]
            values[0]=values[0].model_copy(update={'packet_hash':'0'*64});return values
        monkeypatch.setattr(review,'build_packets',broken)
    elif fault=='wrong_roles':
        original=review._steps
        monkeypatch.setattr(review,'_steps',lambda *args:tuple(reversed(original(*args))))
    else:
        original=service.analyze_scenario
        def wrong(data):
            a=original(data);a['total_stake_ore']+=1;a['proposal_hash']=digest({k:v for k,v in a.items() if k!='proposal_hash'});return a
        monkeypatch.setattr(service,'analyze_scenario',wrong)
    before=raw(sid);before_counts=counts(sid)
    assert post(client,'/'+sid+'/analyze').status_code == 409
    assert raw(sid)==before and counts(sid)==before_counts


def five_source_scenario():
    base=core.build_scenario();quotes=base['observations'][0]['quotes']
    extra=deepcopy(quotes[2]);extra.update(book='kalla_5',source_url='https://example.invalid/kalla-5');quotes.append(extra)
    captured=Snapshot.model_validate(base['observations'][0]).captured_at
    quotes[1]['updated_at']=(captured-timedelta(seconds=300)).isoformat()
    return base


def test_critic_removes_stale_reference_and_preserves_before_after_finance(client,monkeypatch):
    monkeypatch.setattr(service,'build_scenario',five_source_scenario)
    original=service.analyze_scenario
    def wrong(data):
        a=original(data);a['matches'][0]['decision']['reference_books']=['kalla_2','kalla_3','kalla_4']
        a['proposal_hash']=digest({k:v for k,v in a.items() if k!='proposal_hash'});return a
    monkeypatch.setattr(service,'analyze_scenario',wrong)
    sid=analyzed(client,approve=True);a=raw(sid)['analysis']
    assert len(a['core_analysis']['proposals'])==4 and len(a['proposals'])==3
    blockers=[f for f in a['review']['findings'] if f['severity']=='blocker']
    assert blockers==[{'code':'STALE_OR_FUTURE_SOURCE','severity':'blocker','event_id':'syntetisk-1'}]
    assert a['matches'][0]['decision']['selected'] is False
    assert a['review']['steps'][2]['facts']['total_stake_ore']==4000
    assert a['review']['steps'][3]['facts']['final_money']['total_stake_ore']==3000
    assert a['total_stake_ore']==3000 and a['simulated_cost_ore']==140
    assert a['messages'][0]['text'].startswith('3 förslag efter kritik.')
    assert post(client,'/'+sid+'/simulate',**bound(sid)).status_code==200
    assert post(client,'/'+sid+'/settle').status_code==200
    assert raw(sid)['summary']['capital_ore']==99335


def test_blocker_priority_is_fixed_and_one_code_wins():
    assert review.BLOCKERS==('PROPOSAL_ON_REJECTED_MATCH','STALE_OR_FUTURE_SOURCE','UNKNOWN_SOURCE','PACKET_MISMATCH','AMOUNT_MISMATCH')
    base=five_source_scenario();data=core.analysis_input(base);a=core.analyze_scenario(data)
    packet=research.build_packet(research.make_input(data.observations[0],data.rules,research.RESEARCH_POLICY))
    proposal=deepcopy(a['proposals'][0]);match=deepcopy(a['matches'][0]);proposal['book']='unknown'
    match['decision']['reference_books']=['kalla_2','kalla_3','kalla_4']
    assert review._proposal_problem(proposal,match,packet,data.observations[0],data)=='STALE_OR_FUTURE_SOURCE'
    match['decision']['reference_books']=['kalla_3','kalla_4','kalla_5']
    assert review._proposal_problem(proposal,match,packet,data.observations[0],data)=='UNKNOWN_SOURCE'
    proposal['book']='kalla_1';proposal['home']='wrong';proposal['paper_odds']=99999
    assert review._proposal_problem(proposal,match,packet,data.observations[0],data)=='PACKET_MISMATCH'
    proposal['home']=data.observations[0].home;match['decision']['paper_odds']=99999
    assert review._proposal_problem(proposal,match,packet,data.observations[0],data)=='AMOUNT_MISMATCH'


@pytest.mark.parametrize('age',[120,120.000001,-0.000001])
def test_research_and_core_agree_on_freshness_boundaries(age):
    base=core.build_scenario();o=base['observations'][0];captured=Snapshot.model_validate(o).captured_at
    o['quotes'][0]['updated_at']=(captured-timedelta(seconds=age)).isoformat()
    data=core.analysis_input(base);a=core.analyze_scenario(data)
    packet=research.build_packet(research.make_input(data.observations[0],data.rules,research.RESEARCH_POLICY))
    assert bool(packet.rejections)==(age!=120)
    assert a['matches'][0]['decision']['selected']==(age==120)


def test_future_results_and_live_globals_do_not_change_frozen_analysis(client,monkeypatch):
    first=analyzed(client);expected=raw(first)['analysis']
    second=create(client);frozen=raw(second)['frozen']
    for result in frozen['settlement_data'].values():result.update(home_score=99,away_score=98)
    write_json(second,'frozen',frozen)
    monkeypatch.setitem(core.POLICY,'price_haircut_bp',9000)
    monkeypatch.setitem(research.RESEARCH_POLICY,'required_context',['form'])
    monkeypatch.setitem(ROLES,'researcher',{**ROLES['researcher'],'name':'new live name','version':'future'})
    assert post(client,'/'+second+'/analyze').status_code==200
    assert raw(second)['analysis']==expected  # Includes every packet/step and outer hash.


@pytest.mark.parametrize('column',['frozen','analysis'])
def test_unsealed_evidence_tamper_is_rejected(client,column):
    sid=analyzed(client);row=raw(sid);value=row[column]
    if column=='frozen':value['research_rules']['notice']='changed'
    else:value['review']['steps'][0]['facts']['fresh_counts'][0]=99
    write_json(sid,column,value,reseal=False)
    assert client.get(BASE+'/'+sid).status_code==409


def test_resealed_blocker_cannot_keep_a_registered_proposal(client):
    sid=analyzed(client,approve=True);a=raw(sid)['analysis']
    a['review']['findings'].append({'code':'PROPOSAL_ON_REJECTED_MATCH','severity':'blocker','event_id':a['proposals'][0]['event_id']})
    write_json(sid,'analysis',a);before=counts(sid)
    response=post(client,'/'+sid+'/simulate',**bound(sid))
    assert response.status_code==409 and 'borttagna' in response.json()['detail']
    assert counts(sid)==before


@pytest.mark.parametrize('remove_all',[False,True])
def test_resealed_v2_cannot_be_downgraded_to_legacy(client,remove_all):
    sid=analyzed(client,approve=True);f=raw(sid)['frozen']
    for key in (review.META_KEYS if remove_all else ('workflow_version',)):f.pop(key)
    write_json(sid,'frozen',f);before=counts(sid)
    assert post(client,'/'+sid+'/simulate',**bound(sid)).status_code==409
    assert counts(sid)==before


@pytest.mark.parametrize('field',['review','critic_status','research'])
def test_owner_cannot_supply_agent_review(client,field):
    sid=analyzed(client);before=counts(sid)
    assert post(client,'/'+sid+'/decision',decision='approved',**bound(sid),**{field:{}}).status_code==422
    assert counts(sid)==before


def test_decision_and_simulation_do_not_rebuild_any_review(client,monkeypatch):
    sid=analyzed(client)
    def forbidden(*args,**kwargs):raise AssertionError('saved review must not run again')
    monkeypatch.setattr(service,'analyze_scenario',forbidden)
    monkeypatch.setattr(review,'analyze_v2',forbidden)
    monkeypatch.setattr(review,'build_packets',forbidden)
    monkeypatch.setattr(review,'build_packet',forbidden)
    monkeypatch.setattr(research,'build_packet',forbidden)
    monkeypatch.setattr(review,'critic_verify',forbidden)
    assert post(client,'/'+sid+'/decision',decision='approved',**bound(sid)).status_code==200
    assert post(client,'/'+sid+'/simulate',**bound(sid)).status_code==200


def test_analyze_replay_after_stop_skips_review_and_conflicting_decision_is_atomic(client,monkeypatch):
    sid=create(client);body={'action_id':str(uuid4())}
    response=client.post(BASE+'/'+sid+'/analyze',json=body);assert response.status_code==200
    assert post(client,'/'+sid+'/decision',decision='declined',**bound(sid)).status_code==200
    before=raw(sid);before_counts=counts(sid)
    assert post(client,'/'+sid+'/decision',decision='approved',**bound(sid)).status_code==409
    assert raw(sid)==before and counts(sid)==before_counts
    assert client.post('/api/control',json={'state':'stopped'}).status_code==200
    monkeypatch.setattr(review,'verify_saved_chain',lambda *a:(_ for _ in ()).throw(AssertionError('replay skip')))
    assert client.post(BASE+'/'+sid+'/analyze',json=body).json()==response.json()
    assert raw(sid)==before and counts(sid)==before_counts


def test_nested_future_cost_metadata_never_reaches_the_core(client,monkeypatch):
    base=core.build_scenario();base['cost_definitions'][0]['result']={'home_score':99}
    monkeypatch.setattr(service,'build_scenario',lambda:deepcopy(base))
    sid=create(client);before=raw(sid);before_counts=counts(sid)
    def forbidden(*args):raise AssertionError('future metadata reached the core')
    monkeypatch.setattr(service,'analyze_scenario',forbidden)
    response=post(client,'/'+sid+'/analyze')
    assert response.status_code==409 and 'framtida' in response.json()['detail']
    assert raw(sid)==before and counts(sid)==before_counts


def test_resealed_retained_match_cannot_disagree_with_its_core_proposal(client):
    sid=analyzed(client,approve=True);a=raw(sid)['analysis']
    a['matches'][0]['decision']['paper_odds']+=1
    write_json(sid,'analysis',a);before=counts(sid)
    response=post(client,'/'+sid+'/simulate',**bound(sid))
    assert response.status_code==409 and 'kvarvarande matchfakta' in response.json()['detail']
    assert counts(sid)==before


@pytest.mark.parametrize('tamper',['finding_code','critic_status'])
def test_resealed_critic_cannot_misstate_a_real_removal(client,monkeypatch,tamper):
    monkeypatch.setattr(service,'build_scenario',five_source_scenario)
    original=service.analyze_scenario
    def wrong(data):
        a=original(data);a['matches'][0]['decision']['reference_books']=['kalla_2','kalla_3','kalla_4']
        a['proposal_hash']=digest({k:v for k,v in a.items() if k!='proposal_hash'});return a
    monkeypatch.setattr(service,'analyze_scenario',wrong)
    sid=analyzed(client,approve=True);a=raw(sid)['analysis']
    if tamper=='finding_code':
        next(f for f in a['review']['findings'] if f['severity']=='blocker')['code']='UNKNOWN_SOURCE'
        _reseal_review(sid,a)
    else:
        a['review']['steps'][3]['status']='completed'
        step=a['review']['steps'][3];step['output_hash']=digest({k:v for k,v in step.items() if k!='output_hash'})
        write_json(sid,'analysis',a)
    before=counts(sid)
    assert post(client,'/'+sid+'/simulate',**bound(sid)).status_code==409
    assert counts(sid)==before


def test_rejected_match_has_priority_over_all_other_proposal_defects():
    base=core.build_scenario();data=core.analysis_input(base);a=core.analyze_scenario(data)
    observation=data.observations[4]
    packet=research.build_packet(research.make_input(observation,data.rules,research.RESEARCH_POLICY))
    proposal=deepcopy(a['proposals'][0]);proposal.update(event_id=observation.event_id,home='wrong',book='unknown',paper_odds=99999,stake_ore=2000)
    match=deepcopy(a['matches'][0]);match['decision']['reference_books']=['kalla_2','kalla_3','kalla_4']
    assert review._proposal_problem(proposal,match,packet,observation,data)=='PROPOSAL_ON_REJECTED_MATCH'


def test_public_v2_is_complete_and_explicit_at_every_level(client):
    sid=analyzed(client);stored=raw(sid)['analysis'];view=client.get(BASE+'/'+sid).json()
    assert view['workflow_version']==review.WORKFLOW_VERSION
    a=view['analysis'];assert a==stored
    assert set(a)=={'proposal_version','analysis_input_hash','matches','proposals','total_stake_ore','simulated_cost_ore','messages','proposal_hash',
                    'review_version','core_proposal_hash','core_analysis','research','review','notice'}
    assert set(a['core_analysis'])=={'proposal_version','analysis_input_hash','matches','proposals','total_stake_ore','simulated_cost_ore','messages','proposal_hash'}
    assert set(a['research'])=={'version','packets'}
    for packet in a['research']['packets']:
        assert set(packet)=={'research_version','data_kind','event_id','observation_hash','as_of','starts_at','seconds_to_kickoff',
                            'max_quote_age_seconds','minimum_fresh_sources','sources','fresh_count','missing_context','source_independence','rejections','notice','packet_hash'}
        for source in packet['sources']:
            assert set(source)=={'book','source_url','updated_at','age_seconds','fresh','reason'}
        assert all(isinstance(code,str) for code in packet['rejections'])
    assert set(a['review'])=={'contract','steps','findings'}
    assert set(a['review']['contract'])=={'workflow_version','research_version','research_rules','review_roles'}
    assert set(a['review']['contract']['research_rules'])=={'required_context','as_of_source','notice'}
    for role in a['review']['contract']['review_roles']:assert set(role)=={'role_id','name','version'}
    money={'initial_capital_ore','simulated_cost_ore','proposal_count','fixed_stake_ore','expected_fixed_total_ore','total_stake_ore','projected_available_ore','capital_sufficient'}
    fact_keys={'researcher':{'kind','event_ids','packet_hashes','fresh_counts','rejected_event_ids'},
               'analyst':{'kind','core_input_hash','core_output_hash','candidate_event_ids'},
               'finance':money|{'kind'},'critic':{'kind','retained_event_ids','removed_event_ids','findings_hash','final_money'}}
    for step in a['review']['steps']:
        assert set(step)=={'role_id','role_name','role_version','input_hash','status','facts','limitations','output_hash'}
        assert set(step['facts'])==fact_keys[step['role_id']]
        if step['role_id']=='critic':assert set(step['facts']['final_money'])==money
    for finding in a['review']['findings']:assert set(finding)=={'code','severity','event_id'}


def test_get_never_builds_or_verifies_review_and_keeps_all_rows_unchanged(client,monkeypatch):
    sid=analyzed(client);before=client.get(BASE+'/'+sid).json();before_raw=raw(sid);before_counts=counts(sid)
    def forbidden(*args,**kwargs):raise AssertionError('GET must only project saved fields')
    for owner,names in [(service,('build_scenario','analyze_scenario')),
                        (review,('build_scenario_v2','analyze_v2','build_packets','critic_verify','_proposal_problem','verify_saved_chain')),
                        (research,('build_packet',))]:
        for name in names:monkeypatch.setattr(owner,name,forbidden)
    assert client.get(BASE+'/'+sid).json()==before==client.get(BASE+'/'+sid).json()
    assert client.get(BASE).status_code==200
    assert raw(sid)==before_raw and counts(sid)==before_counts


def test_unknown_deep_fields_and_nested_values_are_not_public(client):
    sid=analyzed(client);a=raw(sid)['analysis']
    a['research']['packets'][0]['unknown_future_payload']={'home_score':99}
    a['review']['steps'][0]['unknown_future_payload']={'away_score':98}
    a['review']['steps'][0]['facts']['unknown_future_payload']={'results':[1]}
    a['research']['packets'][0]['sources'][0]['book']={'home_score':97}
    write_json(sid,'analysis',a)
    response=client.get(BASE+'/'+sid);assert response.status_code==200
    body=response.json();text=json.dumps(body)
    assert all(k not in text for k in ('unknown_future_payload','home_score','away_score','results'))
    assert 'book' not in body['analysis']['research']['packets'][0]['sources'][0]


@pytest.mark.parametrize('field',['research','review','core_analysis'])
def test_malformed_new_sections_remain_readable_without_validation(client,field):
    sid=analyzed(client);a=raw(sid)['analysis'];a[field]=['not','an','object'];write_json(sid,'analysis',a)
    assert client.get(BASE+'/'+sid).status_code==200


def test_unknown_saved_review_version_projects_only_base_fields(client):
    sid=analyzed(client);a=raw(sid)['analysis'];a['review_version']='future-review-v99';write_json(sid,'analysis',a)
    f=raw(sid)['frozen'];f['workflow_version']='future-review-v99';write_json(sid,'frozen',f)
    response=client.get(BASE+'/'+sid);assert response.status_code==200
    assert response.json()['workflow_version']=='future-review-v99'
    assert set(response.json()['analysis'])=={'proposal_version','proposal_hash','total_stake_ore','simulated_cost_ore','matches','proposals','messages'}


@pytest.mark.parametrize('fault',['missing_event','bad_decision','bad_packets'])
def test_malformed_resealed_write_is_controlled_409_and_atomic(client,fault):
    sid=analyzed(client,approve=True);a=raw(sid)['analysis']
    if fault=='missing_event':a['core_analysis']['matches'][0].pop('event_id')
    elif fault=='bad_decision':a['core_analysis']['matches'][0]['decision']=None
    else:a['research']['packets']=None
    a['core_analysis']['proposal_hash']=digest({k:v for k,v in a['core_analysis'].items() if k!='proposal_hash'})
    write_json(sid,'analysis',a);before=raw(sid);before_counts=counts(sid)
    assert post(client,'/'+sid+'/simulate',**bound(sid)).status_code==409
    assert raw(sid)==before and counts(sid)==before_counts


def test_resealed_fresh_flag_cannot_hide_a_stale_saved_source(client):
    sid=analyzed(client);packet=raw(sid)['analysis']['research']['packets'][4]
    packet['sources'][0].update(fresh=True,reason=None);packet['fresh_count']=1
    packet['packet_hash']=digest({k:v for k,v in packet.items() if k!='packet_hash'})
    with pytest.raises(ValueError,match='offertkontroll'):
        research.ResearchPacket.model_validate(packet)


def test_real_backend_removal_matches_the_pinned_ui_fixture(client,monkeypatch):
    fixture_path=Path(__file__).parents[1]/'frontend/e2e/fixtures/betting-review-removal.json'
    fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    canonical_fixture=json.dumps(fixture,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    assert hashlib.sha256(canonical_fixture.encode('utf-8')).hexdigest()=='55080e3f4313d811847c7df6b9eaf9f56ba741c33209199842e1cb0042ad0b80'
    monkeypatch.setattr(service,'now',lambda:'2026-11-08T12:00:00+00:00')
    monkeypatch.setattr(service,'uid',lambda:'f'*32)
    monkeypatch.setattr(service,'build_scenario',five_source_scenario)
    original=service.analyze_scenario
    def wrong(data):
        a=original(data);a['matches'][0]['decision']['reference_books']=['kalla_2','kalla_3','kalla_4']
        a['proposal_hash']=digest({k:v for k,v in a.items() if k!='proposal_hash'});return a
    monkeypatch.setattr(service,'analyze_scenario',wrong)
    sid=analyzed(client)
    assert client.get(BASE+'/'+sid).json()==fixture
