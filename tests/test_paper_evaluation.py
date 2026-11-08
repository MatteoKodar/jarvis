from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from jarvis import paper_evaluation as evaluation,paper_review as review,paper_data as paper
from jarvis.betting_demo import AnalysisInput,analyze_match
from jarvis.odds_lab import POLICY,canonical,digest
from test_paper_data import raw,load


def results():return json.loads((Path(__file__).parent/'fixtures/paper_results_v1.json').read_text(encoding='utf-8'))
def run(data=None,outcomes=None):
    data=data or load()
    return evaluation.evaluate(data,results() if outcomes is None else outcomes,review.build_review(data)['report_hash'])


def test_hand_calculated_profit_cost_baseline_and_no_input_mutation():
    data=load();outcomes=results();before=deepcopy(outcomes);a=run(data,outcomes)
    for key,stake,payout,profit,net,capital,count in [
      ('primary',2000,2475,475,335,100335,2),('baseline',3000,3960,960,820,100820,3)]:
        s=a[key]['summary']
        assert (s['total_stake_ore'],s['payout_ore'],s['game_profit_ore'],s['net_ore'],s['capital_ore'],s['bet_count'])==(stake,payout,profit,net,capital,count)
        assert s['simulated_cost_ore']==140 and s['open_stake_ore']==0 and a[key]['pending_count']==0
        assert a[key]['roi_bp']==profit*10000//stake
    assert a['primary']['results_without_bet']==5 and a['baseline']['results_without_bet']==4
    assert outcomes==before and run(data,outcomes)==a
    assert a['evaluation_hash']==digest({k:v for k,v in a.items() if k!='evaluation_hash'})


def test_all_losses_stay_negative_for_both_tracks_and_floor_negative_roi():
    out=results()
    for r in out['records']:r.update(home_score=0,away_score=1)
    a=run(outcomes=out)
    assert a['primary']['summary']['net_ore']==-2140 and a['baseline']['summary']['net_ore']==-3140
    assert a['primary']['roi_bp']==a['baseline']['roi_bp']==-10000
    # One loss/one win gives a negative fractional baseline return with floor.
    v=raw();v['records']=[v['records'][0],v['records'][6]];data=paper.PaperInput.model_validate(v)
    out['records']=[r for r in out['records'] if r['event_id'] in {'paper-test-1','paper-test-7'}]
    out['records'][1].update(home_score=2,away_score=0);a=run(data,out)
    assert a['baseline']['summary']['game_profit_ore']==-20 and a['baseline']['roi_bp']==-100


def test_void_and_pending_keep_open_stakes_and_never_make_complete_roi():
    out=results();out['records'][0].update(status='void',home_score=None,away_score=None)
    out['records']=[r for r in out['records'] if r['event_id']!='paper-test-7'];a=run(outcomes=out)
    p=a['primary'];b=a['baseline']
    assert p['void_count']==p['pending_count']==1 and p['roi_bp'] is None
    assert p['summary']['payout_ore']==1000 and p['summary']['game_profit_ore']==0
    assert p['summary']['capital_ore']==99860 and p['summary']['available_ore']==98860
    assert b['void_count']==b['pending_count']==1 and b['roi_bp'] is None
    assert b['summary']['game_profit_ore']==980 and b['summary']['available_ore']==99840


def test_empty_results_are_all_pending_and_zero_bets_have_no_roi():
    out=results();out['records']=[];a=run(outcomes=out)
    assert a['primary']['pending_count']==2 and a['baseline']['pending_count']==3
    v=raw();v['records']=[v['records'][2]];data=paper.PaperInput.model_validate(v)
    a=run(data,out)
    assert a['primary']['summary']['bet_count']==a['baseline']['summary']['bet_count']==0
    assert a['primary']['roi_bp'] is a['baseline']['roi_bp'] is None
    assert a['primary']['summary']['net_ore']==-20


@pytest.mark.parametrize('fault',['unknown','duplicate','early','at_kickoff','null_final','scored_void','bool','numeric_time','dataset','version','unsafe_url'])
def test_invalid_results_rejected(fault):
    out=results();r=out['records'][0]
    if fault=='unknown':r['event_id']='unknown'
    elif fault=='duplicate':out['records'].append(deepcopy(r))
    elif fault in {'early','at_kickoff'}:r['finished_at']='2024-01-01T00:00:00Z' if fault=='early' else raw()['records'][0]['starts_at']
    elif fault=='null_final':r['home_score']=None
    elif fault=='scored_void':r['status']='void'
    elif fault=='bool':r['home_score']=True
    elif fault=='numeric_time':r['finished_at']=1700000000
    elif fault=='dataset':out['dataset_id']='wrong'
    elif fault=='version':out['version']='unknown-v99'
    else:r['source_url']='https://user:secret@example.invalid/result'
    with pytest.raises(ValueError):run(outcomes=out)


def test_hash_mismatch_precedes_all_result_model_validation(monkeypatch):
    def forbidden(*a,**k):raise AssertionError('Results used before matching decision identity')
    monkeypatch.setattr(evaluation.PaperResults,'model_validate',forbidden)
    with pytest.raises(evaluation.ReportMismatch):evaluation.evaluate(load(),{'anything':'invalid'},'0'*64)


def test_result_changes_never_reach_builder_or_change_report_identity(monkeypatch):
    actual=evaluation.build_review;seen=[]
    def capture(input):
        seen.append(input.model_dump(mode='json'));return actual(input)
    monkeypatch.setattr(evaluation,'build_review',capture)
    a=run();out=results()
    for r in out['records']:r.update(home_score=99,away_score=0)
    b=run(outcomes=out)
    assert seen[0]==seen[1] and a['report_hash']==b['report_hash']
    assert a['results_hash']!=b['results_hash'] and a['evaluation_hash']!=b['evaluation_hash']


def test_results_exact_size_boundary():
    out=results();out['records']=[{**deepcopy(out['records'][0]),'event_id':f'boundary-{i}'} for i in range(20)]
    out=evaluation.PaperResults.model_validate(out).model_dump(mode='json')
    needed=9000-len(canonical(out).encode('utf-8'))
    for r in out['records']:
        add=min(300-len(r['source_url']),needed);r['source_url']+='x'*add;needed-=add
    for r in out['records']:
        add=min(80-len(r['event_id']),needed);r['event_id']+='x'*add;needed-=add
    assert needed==0
    assert len(canonical(evaluation.PaperResults.model_validate(out).model_dump(mode='json')).encode('utf-8'))==9000
    next(r for r in out['records'] if len(r['event_id'])<80)['event_id']+='x'
    with pytest.raises(ValidationError,match='överstiger 9000'):evaluation.PaperResults.model_validate(out)


def test_negative_fractional_roi_uses_floor_not_truncation():
    v=raw();v['records'][6]['quotes'][1]['odds']['home']=20011
    data=paper.PaperInput.model_validate(v);out=results()
    for r in out['records']:r.update(home_score=0,away_score=1)
    out['records'][6].update(home_score=2,away_score=0)
    a=run(data,out);b=a['baseline']
    assert b['bets'][-1]['paper_odds']==20011*9900//10000==19810
    assert b['summary']['payout_ore']==1981 and b['summary']['game_profit_ore']==-1019
    assert b['roi_bp']==-3397 and int(-1019*10000/3000)==-3396


def test_evaluation_pure_and_result_schema_has_no_relative_clock(monkeypatch):
    import builtins,socket
    from jarvis import db
    from pydantic import PastDatetime,create_model
    data=load();out=results();expected=review.build_review(data)['report_hash']
    def forbidden(*a,**k):raise AssertionError('Evaluation tried an external effect')
    monkeypatch.setattr(builtins,'open',forbidden);monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(db,'connect',forbidden);monkeypatch.setattr(db,'now',forbidden)
    a=evaluation.evaluate(data,out,expected);assert evaluation.evaluate(data,out,expected)==a
    def walk(v):
        if isinstance(v,dict):
            assert 'now_op' not in v,'Relative now_op constraint'
            for item in v.values():walk(item)
        elif isinstance(v,(tuple,list)):
            for item in v:walk(item)
    walk(evaluation.PaperResults.__pydantic_core_schema__)
    with pytest.raises(AssertionError,match='Relative now_op'):
        walk(create_model('ResultClockPositiveControl',t=(PastDatetime,...)).__pydantic_core_schema__)


@pytest.mark.parametrize('prices,accepted',[(dict(home=20000,draw=40000,away=50000),True),
 (dict(home=20000,draw=20000,away=40000),True),(dict(home=40000,draw=40000,away=40000),False),
 (dict(home=20000,draw=20000,away=20000),False)])
def test_critic_margin_parity_at_boundaries_and_outside(prices,accepted):
    v=raw();v['records']=[v['records'][0]];v['records'][0]['quotes'][0]['odds']=prices
    r=paper.PaperInput.model_validate(v).records[0]
    decision=analyze_match(AnalysisInput(observation=paper.to_snapshot(r),simulated_analysis_at=r.captured_at,rules=POLICY,available_capital_ore=99980))
    assert decision['checks'][0]['accepted'] is accepted
    assert set(review._accepted(r,POLICY))=={c['book'] for c in decision['checks'] if c['accepted']}
