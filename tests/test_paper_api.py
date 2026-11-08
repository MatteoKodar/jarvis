from copy import deepcopy
from fastapi.testclient import TestClient
import pytest

from jarvis.api import app
from jarvis import paper_review as review
from jarvis.db import connect,initialize
from jarvis.auth import set_owner
from jarvis.odds_lab import POLICY
from test_paper_data import raw
from test_paper_evaluation import results

BASE='/api/betting-demo/paper-replay/'


def running(client):assert client.post('/api/control',json={'state':'running'}).status_code==200


def counters():
    with connect() as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0].startswith(('betting_demo_','odds_'))]
        return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}


def payload(endpoint='review'):
    value={'input':raw()}
    if endpoint=='evaluate':
        from jarvis.paper_data import PaperInput
        value.update(results=results(),expected_report_hash=review.build_review(PaperInput.model_validate(raw()))['report_hash'])
    return value


@pytest.mark.parametrize('endpoint',['review','evaluate'])
def test_real_api_is_read_only_for_business_data(client,endpoint):
    running(client);before=counters();response=client.post(BASE+endpoint,json=payload(endpoint))
    assert response.status_code==200,response.text
    assert counters()==before
    if endpoint=='review':assert response.json()['primary_money']['proposal_count']==2
    else:assert response.json()['primary']['summary']['net_ore']==335


@pytest.mark.parametrize('endpoint',['review','evaluate'])
def test_auth_csrf_origin_are_required(client,endpoint):
    running(client);body=payload(endpoint)
    assert TestClient(app).post(BASE+endpoint,json=body).status_code==401
    csrf=client.headers.pop('x-csrf-token')
    assert client.post(BASE+endpoint,json=body).status_code==403
    client.headers['x-csrf-token']=csrf;client.headers['origin']='http://other'
    assert client.post(BASE+endpoint,json=body).status_code==403


@pytest.mark.parametrize('endpoint',['review','evaluate'])
@pytest.mark.parametrize('state',['paused','stopped'])
def test_pause_stop_prevent_new_computation(client,endpoint,state,monkeypatch):
    body=payload(endpoint);assert client.post('/api/control',json={'state':state}).status_code==200
    import jarvis.api as api
    def forbidden(*a,**k):raise AssertionError('Stopped computation started')
    monkeypatch.setattr(api,'build_paper_review',forbidden);monkeypatch.setattr(api,'evaluate_paper',forbidden)
    assert client.post(BASE+endpoint,json=body).status_code==409


@pytest.mark.parametrize('endpoint',['review','evaluate'])
def test_live_mode_cannot_use_paper_path(client,endpoint,monkeypatch):
    body=payload(endpoint);monkeypatch.setenv('JARVIS_MODE','LIVE');initialize();set_owner('test-only-password-123')
    login=client.post('/api/login',json={'password':'test-only-password-123'});client.headers['x-csrf-token']=login.json()['csrf']
    assert client.post(BASE+endpoint,json=body).status_code==409


@pytest.mark.parametrize('endpoint',['review','evaluate'])
def test_streaming_and_header_size_guards_precede_parsing(client,endpoint):
    running(client)
    assert client.post(BASE+endpoint,content=b'x'*50001,headers={'content-type':'application/json'}).status_code==413
    request=client.build_request('POST',BASE+endpoint,content=iter([b' '*25000,b' '*25001]),headers={'content-type':'application/json'})
    assert 'content-length' not in request.headers
    assert client.send(request).status_code==413


def test_contract_drift_is_409_validation_is_422_and_hash_mismatch_is_409(client,monkeypatch):
    running(client);body=payload('evaluate');body['expected_report_hash']='0'*64
    assert client.post(BASE+'evaluate',json=body).status_code==409
    body=payload();body['input']['records'][0]['quotes'][0]['odds']['home']=True
    assert client.post(BASE+'review',json=body).status_code==422
    body=payload();monkeypatch.setitem(POLICY,'price_haircut_bp',500)
    assert client.post(BASE+'review',json=body).status_code==409


def test_results_cannot_be_submitted_to_review_or_inside_input(client):
    running(client);body=payload();body['results']=results()
    assert client.post(BASE+'review',json=body).status_code==422
    body=payload();body['input']['records'][0]['home_score']=99
    assert client.post(BASE+'review',json=body).status_code==422


def test_result_errors_are_422_without_business_writes(client):
    running(client);body=payload('evaluate');before=counters();body['results']['records'][0]['event_id']='unknown'
    assert client.post(BASE+'evaluate',json=body).status_code==422
    assert counters()==before


@pytest.mark.parametrize('endpoint',['review','evaluate'])
def test_owner_reset_revokes_old_session_for_new_calculations(client,endpoint):
    running(client);body=payload(endpoint);before=counters();set_owner('replacement-owner-test-password')
    assert client.post(BASE+endpoint,json=body).status_code==401
    assert counters()==before
