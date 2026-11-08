from copy import deepcopy
from decimal import Decimal, ROUND_FLOOR, localcontext
import inspect

import pytest

from jarvis import paper_review as review, paper_data as paper
from jarvis.betting_demo import AnalysisInput, analyze_match
from jarvis.odds_lab import POLICY, digest
from jarvis.roles import ROLES
from test_paper_data import load,raw


def test_core_parity_hand_oracle_baseline_opportunities_and_provenance():
    data=load();report=review.build_review(data);lookup={r.event_id:r for r in data.records}
    for row in report['core_decisions']:
        record=lookup[row['event_id']]
        if record.missing_times:assert row['decision'] is None;continue
        direct=analyze_match(AnalysisInput(observation=paper.to_snapshot(record),simulated_analysis_at=record.captured_at,
            rules=deepcopy(POLICY),available_capital_ore=row['available_capital_ore']))
        assert row['decision']==direct
    assert [p['event_id'] for p in report['proposals']]==['paper-test-1','paper-test-7']
    assert [p['event_id'] for p in report['baseline']]==['paper-test-1','paper-test-2','paper-test-7']
    assert report['proposals'][-1]['book']=='z_offer' and report['baseline'][-1]['book']=='a_ref'
    assert report['proposals'][0]['paper_odds']==25000*9900//10000==24750
    assert 1000*report['proposals'][0]['paper_odds']//10000==2475
    with localcontext() as ctx:
        ctx.prec=40
        p=(Decimal(1)/Decimal('2.0'))/sum(Decimal(1)/Decimal(v) for v in ('2.0','3.4','3.6'))
        edge=int(((p*Decimal('2.475')-1)*10000).to_integral_value(rounding=ROUND_FLOOR))
    assert report['core_decisions'][0]['decision']['edge_bp']==edge
    assert report['money_before']==report['primary_money']=={'initial_capital_ore':100000,'declared_data_cost_ore':140,
        'proposal_count':2,'total_stake_ore':2000,'projected_available_ore':97860}
    assert report['baseline_money']['total_stake_ore']==3000 and report['findings']==[]
    assert report['proposals']==report['candidates']
    assert [s['role_id'] for s in report['steps']]==['researcher','analyst','finance','critic']
    assert report['origin']=='synthetic_fixture' and report['real_money_enabled'] is False
    assert 'inte oberoende AI-bedömning' in report['notice']
    assert report['contract']['baseline_definition']==review.BASELINE_DEFINITION
    assert set(report['contract']['baseline_definition'])=={'universe','book','outcome','price','stake','capital'}
    assert report['interpretation']==review.INTERPRETATION
    for key,text in [('origin','påstått'),('baseline','aldrig en rekommendation'),('exposure','inte kausal alpha'),('critic','inte verklig research')]:
        assert text in report['interpretation'][key]


def test_missing_time_never_reaches_snapshot_or_core(monkeypatch):
    v=raw();v['records']=[v['records'][2],v['records'][3]];data=paper.PaperInput.model_validate(v)
    def forbidden(*a,**k):raise AssertionError('Incomplete record reached computation')
    monkeypatch.setattr(review,'to_snapshot',forbidden);monkeypatch.setattr(review,'analyze_match',forbidden)
    result=review.build_review(data)
    assert result['proposals']==result['baseline']==[]
    assert [s['decision'] for s in result['core_decisions']]==[None,None]


def test_no_result_parameter_or_result_fields():
    assert list(inspect.signature(review.build_review).parameters)==['input']
    v=raw();v['records'][0]['result']={'home_score':99}
    with pytest.raises(ValueError,match='Extra inputs'):paper.PaperInput.model_validate(v)
    assert 'result' not in review.build_review(load())


def three_candidates():
    v=raw();base=v['records'][0];v['records']=[{**deepcopy(base),'event_id':f'capital-{i}','home':f'Team{i}'} for i in range(3)]
    for r in v['records']:r['data_cost_ore']=0
    v['records'][0]['data_cost_ore']=98000
    return v


def test_sequential_reservations_no_reinvestment_and_file_order_independence():
    v=three_candidates();a=review.build_review(paper.PaperInput.model_validate(v))
    assert [p['event_id'] for p in a['proposals']]==['capital-0','capital-1']
    assert [r['available_capital_ore'] for r in a['core_decisions']]==[2000,1000,0]
    assert 'Låtsaskapitalet' in a['core_decisions'][2]['decision']['reason']
    assert len(a['baseline'])==2 and a['primary_money']['projected_available_ore']==0
    v['records'].reverse();b=review.build_review(paper.PaperInput.model_validate(v))
    for key in ['proposals','baseline','core_decisions','primary_money','baseline_money']:assert a[key]==b[key]
    assert a['input_hash']!=b['input_hash']  # File order remains part of evidence identity.


@pytest.mark.parametrize('fault,code',[('book','UNKNOWN_SOURCE'),('price','PRICE_MISMATCH'),('stake','STAKE_MISMATCH'),
 ('reference','UNKNOWN_SOURCE'),('blocked','DATA_BLOCKED'),('unusable','UNUSABLE_SOURCE'),
 ('duplicate_ref','REFERENCE_MISMATCH'),('capital','CAPITAL_SHORTFALL')])
def test_critic_can_only_remove_one_bad_candidate_and_keeps_money_before_after_distinct(monkeypatch,fault,code):
    v=raw();v['records']=[v['records'][0]]
    if fault=='blocked':v['records'][0]['starts_at']=v['records'][0]['captured_at']
    if fault=='unusable':v['records'][0]['quotes'][0]['updated_at']='2025-01-01T09:57:59Z'
    if fault=='capital':v['records'][0]['data_cost_ore']=99500
    data=paper.PaperInput.model_validate(v);original=review.analyze_match
    template=analyze_match(AnalysisInput(observation=paper.to_snapshot(load().records[0]),simulated_analysis_at=load().records[0].captured_at,rules=POLICY,available_capital_ore=100000))
    def wrong(d):
        value=deepcopy(template) if fault in {'blocked','unusable','capital'} else original(d)
        if fault=='book':value['book']='unknown'
        elif fault=='price':value['paper_odds']=99999
        elif fault=='stake':value['stake_ore']=2000
        elif fault=='reference':value['reference_books'][0]='unknown'
        elif fault=='duplicate_ref':value['reference_books'][1]=value['reference_books'][0]
        return value
    monkeypatch.setattr(review,'analyze_match',wrong);report=review.build_review(data)
    assert len(report['candidates'])==1 and report['proposals']==[]
    assert report['findings']==[{'event_id':'paper-test-1','code':code}]
    assert report['steps'][2]['facts']['proposal_count']==1
    assert report['steps'][3]['facts']['final_money']['proposal_count']==0
    assert report['steps'][3]['status']=='removed'


@pytest.mark.parametrize('mutation',['policy','role'])
def test_known_version_refuses_changed_policy_or_role(monkeypatch,mutation):
    data=load()
    if mutation=='policy':monkeypatch.setitem(POLICY,'price_haircut_bp',9000)
    else:monkeypatch.setitem(ROLES,'researcher',{**ROLES['researcher'],'version':'future'})
    with pytest.raises(review.ContractDrift,match='versionshöjas'):review.build_review(data)


def test_hash_chain_each_stage_and_full_report_are_acyclic_and_input_untouched():
    data=load();before=data.model_dump(mode='json');a=review.build_review(data)
    assert review.build_review(data)==a and data.model_dump(mode='json')==before
    previous=digest({'contract':a['contract'],'input_hash':a['input_hash'],'quality_hash':a['quality']['quality_hash']})
    for step in a['steps']:
        assert step['input_hash']==digest({'role_id':step['role_id'],'previous_output_hash':previous})
        assert step['output_hash']==digest({k:v for k,v in step.items() if k!='output_hash'})
        assert 'report_hash' not in str(step)
        previous=step['output_hash']
    assert a['report_hash']==digest({k:v for k,v in a.items() if k!='report_hash'})
    for field in ['baseline','quality','source','steps']:
        altered=deepcopy(a)
        if field=='baseline':altered[field][0]['paper_odds']+=1
        elif field=='quality':altered[field]['records'][0]['fresh_count']=0
        elif field=='source':altered[field]['name']='Changed'
        else:altered[field][0]['status']='changed'
        assert digest({k:v for k,v in altered.items() if k!='report_hash'})!=a['report_hash']


def test_origin_changes_identity_but_not_selection():
    v=raw();v['origin']='manual_unverified';a=review.build_review(load());b=review.build_review(paper.PaperInput.model_validate(v))
    assert a['proposals']==b['proposals'] and a['baseline']==b['baseline']
    assert a['report_hash']!=b['report_hash'] and b['origin']=='manual_unverified'


def test_review_has_no_external_effects(monkeypatch):
    import builtins,socket
    from jarvis import db
    data=load();before=data.model_dump(mode='json')
    def forbidden(*a,**k):raise AssertionError('Review tried an external effect')
    monkeypatch.setattr(builtins,'open',forbidden);monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(db,'connect',forbidden);monkeypatch.setattr(db,'now',forbidden)
    report=review.build_review(data)
    assert report==review.build_review(data) and data.model_dump(mode='json')==before


def test_mixed_offset_and_distinct_start_instants_preserve_sequential_selection():
    from datetime import datetime,timedelta,timezone
    v=three_candidates()
    for i,r in enumerate(v['records']):
        for field in ['captured_at','starts_at']:r[field]=(datetime.fromisoformat(r[field])+timedelta(hours=i)).isoformat()
        for q in r['quotes']:q['updated_at']=(datetime.fromisoformat(q['updated_at'])+timedelta(hours=i)).isoformat()
    a=review.build_review(paper.PaperInput.model_validate(v));offset=deepcopy(v)
    for r,hours in zip(offset['records'],[14,-7,2]):
        zone=timezone(timedelta(hours=hours))
        for field in ['captured_at','starts_at']:r[field]=datetime.fromisoformat(r[field]).astimezone(zone).isoformat()
        for q in r['quotes']:q['updated_at']=datetime.fromisoformat(q['updated_at']).astimezone(zone).isoformat()
    b=review.build_review(paper.PaperInput.model_validate(offset));offset['records'].reverse()
    c=review.build_review(paper.PaperInput.model_validate(offset))
    for other in [b,c]:
        for key in ['proposals','baseline','core_decisions','money_before','primary_money','baseline_money']:assert a[key]==other[key]
        assert a['input_hash']!=other['input_hash'] and a['report_hash']!=other['report_hash']
    assert [p['event_id'] for p in c['proposals']]==['capital-0','capital-1']


def test_independent_critic_acceptance_matches_core_for_every_complete_fixture_record():
    report=review.build_review(load());lookup={r.event_id:r for r in load().records}
    for row in report['core_decisions']:
        if row['decision'] is None:continue
        expected={c['book'] for c in row['decision']['checks'] if c['accepted']}
        assert set(review._accepted(lookup[row['event_id']],POLICY))==expected
