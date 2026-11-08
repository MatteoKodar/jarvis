from copy import deepcopy
from datetime import datetime
import inspect
import json
from pathlib import Path
import socket
import builtins
import ast
import time
import datetime as datetime_module
import pydantic.types

import pytest
from pydantic import ValidationError, BaseModel, PastDatetime, create_model

from jarvis import paper_data as paper, db, odds_lab
from jarvis.betting_demo import AnalysisInput, analyze_match
from jarvis.odds_lab import POLICY, canonical, digest, event_key

FIXTURE=Path(__file__).parent/'fixtures/paper_input_v1.json'


def raw():return json.loads(FIXTURE.read_text(encoding='utf-8'))
def load():return paper.PaperInput.model_validate(raw())


def test_complete_conversion_exact_fields_and_fixture_cases():
    data=load();quality=paper.quality_report(data,POLICY)
    assert [r['blocked_missing_time'] for r in quality['records']]==[False,False,True,True,False,False,False]
    assert [r['fresh_count'] for r in quality['records']]==[4,4,0,3,3,4,4]
    assert quality['records'][5]['too_close_to_kickoff'] is True
    for r in data.records:
        if r.missing_times:
            with pytest.raises(ValueError,match='Saknade tider'):paper.to_snapshot(r)
        else:assert paper.to_snapshot(r).model_dump(mode='json')==r.model_dump(mode='json')
    decisions=[analyze_match(AnalysisInput(observation=paper.to_snapshot(r),simulated_analysis_at=r.captured_at,rules=deepcopy(POLICY),available_capital_ore=100000)) for r in data.records if not r.missing_times]
    assert [d['selected'] for d in decisions]==[True,False,False,False,True]
    assert decisions[-1]['book']=='z_offer'
    assert sorted(c['book'] for c in decisions[-1]['checks'] if c['accepted'])[0]=='a_ref'


@pytest.mark.parametrize('value',[1700000000,True,'2025-01-01','2025-01-01T10:00:00','2025-01-01T10:00:00.5Z','2025-13-01T10:00:00Z'])
@pytest.mark.parametrize('field',['starts_at','captured_at','updated_at'])
def test_strict_timestamp_text(value,field):
    v=raw();target=v['records'][0]['quotes'][0] if field=='updated_at' else v['records'][0];target[field]=value
    with pytest.raises(ValidationError):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('location',['top','record','quote','odds','source'])
def test_future_fields_rejected_at_every_object_boundary(location):
    v=raw();target={'top':v,'record':v['records'][0],'quote':v['records'][0]['quotes'][0],
      'odds':v['records'][0]['quotes'][0]['odds'],'source':v['source']}[location]
    target['home_score']=99
    with pytest.raises(ValidationError,match='Extra inputs'):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('value',[True,1.5,'20',-1,100001])
def test_money_is_bounded_integer(value):
    v=raw();v['records'][0]['data_cost_ore']=value
    with pytest.raises(ValidationError):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('url',['https://user:secret@example.invalid/x','https://example.invalid/x?q=key','https://example.invalid/x#foo','file:///example.invalid/x','https://example.invalid/x\n'])
def test_unsafe_references_rejected(url):
    v=raw();v['source']['reference_url']=url
    with pytest.raises(ValidationError):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('field,value',[('name','Spoof\u202e'),('permission_note','Hello\x85')])
def test_control_bidi_text_rejected(field,value):
    v=raw();v['source'][field]=value
    with pytest.raises(ValidationError):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('kind',['book','id','swapped_pair','case_space_pair'])
def test_duplicate_book_id_and_normalized_match_day(kind):
    v=raw()
    if kind=='book':v['records'][0]['quotes'][1]['book']=v['records'][0]['quotes'][0]['book']
    elif kind=='id':v['records'][1]['event_id']=v['records'][0]['event_id']
    else:
        other=deepcopy(v['records'][0]);other['event_id']='different'
        if kind=='swapped_pair':other['home'],other['away']=other['away'],other['home']
        else:other['home']='  '+other['home'].upper()+'  '
        v['records'][1]=other
    with pytest.raises(ValidationError,match='Duplicerad bok' if kind=='book' else 'Dubblett av match-ID'):
        paper.PaperInput.model_validate(v)
    assert event_key(load().records[0])==event_key(paper.to_snapshot(load().records[0]))


def test_same_pair_on_different_local_day_is_accepted():
    v=raw();v['records'][1]['home']=v['records'][0]['home'];v['records'][1]['away']=v['records'][0]['away']
    assert len(paper.PaperInput.model_validate(v).records)==7


def test_origin_does_not_prove_source_and_reserved_hosts_are_required_for_fixture():
    v=raw();v['source']['reference_url']='https://provider.com/data'
    with pytest.raises(ValidationError,match='reserverade'):paper.PaperInput.model_validate(v)
    v['origin']='manual_unverified';data=paper.PaperInput.model_validate(v)
    assert paper.quality_report(data,POLICY)['records']==paper.quality_report(load(),POLICY)['records']


def test_unknown_version_rejected():
    v=raw();v['version']='future-v9'
    with pytest.raises(ValidationError,match='paper-input-v1'):paper.PaperInput.model_validate(v)


def twenty_records(count=20):
    v=load().model_dump(mode='json');v['records']=[{**deepcopy(v['records'][0]),'event_id':f'match-{i}','home':f'Team {i}'} for i in range(count)]
    return v


def test_21_unique_records_fail_count_only():
    with pytest.raises(ValidationError,match='at most 20'):paper.PaperInput.model_validate(twenty_records(21))


def sized_input(target):
    v=twenty_records();needed=target-len(canonical(v).encode('utf-8'))
    for r in v['records']:
        for q in r['quotes']:
            count=min(300-len(q['source_url']),needed);q['source_url']+='x'*count;needed-=count
    assert needed==0 and len(canonical(v).encode('utf-8'))==target
    return v


def test_exact_byte_boundary_independent_of_url_and_snapshot_limits():
    v=sized_input(36000);assert len(canonical(paper.PaperInput.model_validate(v).model_dump(mode='json')).encode())==36000
    v=sized_input(36001)
    with pytest.raises(ValidationError,match='överstiger 36000 UTF-8-byte'):paper.PaperInput.model_validate(v)


def test_exact_cost_sum_boundary():
    v=raw()
    for r in v['records']:r['data_cost_ore']=0
    v['records'][0]['data_cost_ore']=100000
    assert sum(r.data_cost_ore for r in paper.PaperInput.model_validate(v).records)==100000
    v['records'][1]['data_cost_ore']=1
    with pytest.raises(ValidationError,match='datakostnader överstiger'):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('bad',[25000.0,'25000',True])
def test_odds_do_not_coerce(bad):
    v=raw();v['records'][0]['quotes'][0]['odds']['home']=bad
    with pytest.raises(ValidationError,match='valid integer'):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('field',['home','away'])
@pytest.mark.parametrize('bad',['Text\x85','Text\u202e'])
def test_team_text_control_and_bidi(field,bad):
    v=raw();v['records'][0][field]=bad
    with pytest.raises(ValidationError,match='Kontrolltecken'):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('url',['https://user:secret@example.invalid/x','https://example.invalid/x?q=key','https://example.invalid/x#foo'])
def test_quote_reference_unsafe_forms(url):
    v=raw();v['records'][0]['quotes'][0]['source_url']=url
    with pytest.raises(ValidationError,match='referens utan credentials'):paper.PaperInput.model_validate(v)


def test_synthetic_quote_host_must_be_reserved():
    v=raw();v['records'][0]['quotes'][0]['source_url']='https://provider.com/odds'
    with pytest.raises(ValidationError,match='reserverade'):paper.PaperInput.model_validate(v)


@pytest.mark.parametrize('field',['captured_at','updated_at'])
def test_absent_time_is_not_explicit_null(field):
    v=raw();target=v['records'][0]['quotes'][0] if field=='updated_at' else v['records'][0];target.pop(field)
    with pytest.raises(ValidationError,match='Field required'):paper.PaperInput.model_validate(v)
    target[field]=None;r=paper.PaperInput.model_validate(v).records[0]
    assert r.missing_times


@pytest.mark.parametrize('seconds,blocked',[(59,True),(60,False)])
def test_kickoff_boundary_parity(seconds,blocked):
    from datetime import timedelta
    v=raw();r=v['records'][0];r['starts_at']=(datetime.fromisoformat(r['captured_at'])+timedelta(seconds=seconds)).isoformat()
    r=paper.PaperInput.model_validate(v).records[0];q=paper.quality_record(r,POLICY)
    decision=analyze_match(AnalysisInput(observation=paper.to_snapshot(r),simulated_analysis_at=r.captured_at,rules=POLICY,available_capital_ore=100000))
    assert q['too_close_to_kickoff'] is blocked and decision['selected'] is (not blocked)


def test_fixture_wide_time_facts_and_unknown_are_exact():
    for r in load().records:
        q=paper.quality_record(r,POLICY)
        if r.captured_at is None:assert q['too_close_to_kickoff'] is None and q['seconds_to_kickoff'] is None
        else:assert type(q['seconds_to_kickoff']) is int
        if r.missing_times:continue
        decision=analyze_match(AnalysisInput(observation=paper.to_snapshot(r),simulated_analysis_at=r.captured_at,rules=POLICY,available_capital_ore=100000))
        assert len(q['sources'])==len(decision['checks'])
        for source,check in zip(q['sources'],decision['checks']):
            assert source['book']==check['book']
            assert type(source['age_seconds']) is int
            assert source['fresh']==(check['reason']!='För gammal offert eller offert från framtiden.')


@pytest.mark.parametrize('seconds,expected',[(120,True),(121,False),(-1,False)])
def test_freshness_parity_with_core(seconds,expected):
    from datetime import timedelta
    v=raw();r=v['records'][0];at=datetime.fromisoformat(r['captured_at']);r['quotes'][0]['updated_at']=(at-timedelta(seconds=seconds)).isoformat()
    r=paper.PaperInput.model_validate(v).records[0];q=paper.quality_record(r,POLICY)
    core=analyze_match(AnalysisInput(observation=paper.to_snapshot(r),simulated_analysis_at=r.captured_at,rules=POLICY,available_capital_ore=100000))
    assert q['sources'][0]['fresh'] is expected
    assert core['checks'][0]['accepted'] is expected


def test_equivalent_offset_same_decision_different_hash():
    v=raw();v['records'][0]['captured_at']='2025-01-01T12:00:00+02:00'
    a,b=load(),paper.PaperInput.model_validate(v)
    assert digest(a.model_dump(mode='json'))!=digest(b.model_dump(mode='json'))
    def decision(r):return analyze_match(AnalysisInput(observation=paper.to_snapshot(r),simulated_analysis_at=r.captured_at,rules=POLICY,available_capital_ore=100000))
    assert decision(a.records[0])==decision(b.records[0])


def test_no_effects_and_input_unmodified(monkeypatch):
    value=raw();before=deepcopy(value)
    def forbidden(*a,**k):raise AssertionError('Unexpected external effect')
    monkeypatch.setattr(builtins,'open',forbidden);monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(db,'connect',forbidden);monkeypatch.setattr(db,'now',forbidden)
    class Clock(datetime):
        now=staticmethod(forbidden);utcnow=staticmethod(forbidden)
    monkeypatch.setattr(odds_lab,'datetime',Clock)
    monkeypatch.setattr(pydantic.types,'datetime',Clock)
    monkeypatch.setattr(datetime_module,'datetime',Clock)
    outputs=[]
    for fake_now in [0,4000000000]:
        monkeypatch.setattr(time,'time',lambda:fake_now)
        data=paper.PaperInput.model_validate(value);outputs.append(paper.quality_report(data,POLICY))
    a=outputs[0];assert outputs[1]==a and value==before
    assert a['input_hash']==digest(data.model_dump(mode='json'))


def test_no_clock_imports_or_relative_time_constraints():
    tree=ast.parse(Path(paper.__file__).read_text(encoding='utf-8'))
    modules={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}|{a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
    assert modules<={'re','typing','urllib.parse','pydantic','odds_lab'}
    assert not any(isinstance(n,ast.Call) and ((isinstance(n.func,ast.Attribute) and n.func.attr in {'now','utcnow','open','connect'}) or (isinstance(n.func,ast.Name) and n.func.id in {'open','eval','exec'})) for n in ast.walk(tree))
    # Rust's internal clock cannot be monkeypatched from Python. Prove that no
    # datetime schema requests a relative-to-now constraint in the first place.
    def walk(value):
        if isinstance(value,dict):
            assert 'now_op' not in value, 'Relative now_op constraint'
            for item in value.values():walk(item)
        elif isinstance(value,(list,tuple)):
            for item in value:walk(item)
    walk(paper.PaperInput.__pydantic_core_schema__)
    for model in vars(odds_lab).values():
        if isinstance(model,type) and issubclass(model,BaseModel) and model.__module__==odds_lab.__name__:
            walk(model.__pydantic_core_schema__)
    walk(AnalysisInput.__pydantic_core_schema__)
    with pytest.raises(AssertionError,match='Relative now_op'):
        walk(create_model('RelativeClockPositiveControl',t=(PastDatetime,...)).__pydantic_core_schema__)
