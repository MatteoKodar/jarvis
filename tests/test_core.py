import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from jarvis.api import app
from jarvis.db import connect, initialize, uid, day
from jarvis import service, worker, demo
from jarvis.budget import RuleError, reserve, settle, totals
from jarvis.roles import ROLES

def start(client, key=None):
    assert client.post('/api/control', json={'state':'running'}).status_code == 200
    response = client.post('/api/rounds', json={'goal':'Granska fotbollens odds och datakvalitet', 'cap':500,'action_id':key or uid()})
    assert response.status_code == 200, response.text
    return response.json()['task_id']

def plan(client):
    start(client)
    task = worker.claim()
    asyncio.run(worker.execute(task))
    return service.snapshot()['proposals'][0]

def decide(client, p, decision='approved'):
    return client.post('/api/proposals/'+p['id']+'/decision',json={'version':p['version'],'digest':p['digest'],'decision':decision,'note':'Testbeslut'})

def test_ten_fixed_roles(client):
    agents = client.get('/api/state').json()['agents']
    assert len(agents) == 10
    assert len({a['id'] for a in agents}) == 10
    assert all(a['version'] and a['instructions'] and a['output_format'] for a in agents)

def test_complete_chain_and_persistent_result(client):
    p = plan(client)
    assert decide(client,p).status_code == 200
    work = worker.claim()
    asyncio.run(worker.execute(work))
    review = worker.claim()
    assert review['agent_id'] == 'critic'
    asyncio.run(worker.execute(review))
    initialize()
    s = service.snapshot()
    assert len(s['ideas']) == 0
    assert len(s['files']) == 3
    assert len(s['runs']) == 3
    assert s['settings']['spent'] == 0
    assert next(t for t in s['tasks'] if t['id']==work['id'])['status'] == 'blocked'
    assert client.get('/api/files/'+s['files'][0]['id']).status_code == 200

def test_approval_persists_restart(client):
    p=plan(client)
    initialize()
    restored=service.snapshot()['proposals'][0]
    assert restored['digest']==p['digest'] and restored['status']=='pending'

def test_double_click_is_idempotent(client):
    p=plan(client)
    assert decide(client,p).status_code==200
    assert decide(client,p).status_code==200
    s=service.snapshot()
    assert len([t for t in s['tasks'] if t['phase']=='work'])==1
    assert len(s['approvals'])==1

def test_round_idempotency(client):
    key=uid()
    assert start(client,key)==start(client,key)
    assert len(service.snapshot()['tasks'])==1

def test_reject_does_not_queue_work(client):
    p=plan(client)
    assert decide(client,p,'rejected').status_code==200
    assert worker.claim() is None

def test_revision_invalidates_old_approval(client):
    p=plan(client)
    assert decide(client,p,'changes').status_code==200
    response=client.post('/api/proposals/'+p['id']+'/revise',json={'title':'Undersök en smalare målgrupp','cap':200})
    assert response.status_code==200
    newer=next(x for x in service.snapshot()['proposals'] if x['id']==response.json()['id'])
    assert newer['version']==2 and newer['digest']!=p['digest']
    assert decide(client,p).status_code==409
    assert worker.claim() is None
    assert decide(client,newer).status_code==200

def test_expired_proposal_rejected(client):
    p=plan(client)
    with connect(True) as c:
        c.execute("UPDATE proposals SET expires='2000-01-01' WHERE id=?",(p['id'],))
    assert decide(client,p).status_code==409

def test_agent_cannot_approve(client):
    p=plan(client)
    with pytest.raises(RuleError):
        service.decide(p['id'],p['version'],p['digest'],'approved','',actor='ceo')
    response=client.post('/api/proposals/'+p['id']+'/decision',json={'version':p['version'],'digest':p['digest'],'decision':'approved','actor':'ceo'})
    assert response.status_code==422

def test_role_and_external_action_enforced(client):
    p=plan(client)
    with connect(True) as c:
        with pytest.raises(RuleError):
            service.add_task(c,action_id=uid(),agent_id='admin',title='test',context='',criteria='test',cap=0,phase='work')
        payload=p['payload']; payload['action']='publish'
        c.execute('UPDATE proposals SET payload=? WHERE id=?',(json.dumps(payload),p['id']))
    assert decide(client,p).status_code==409

def test_concurrent_budget_reservations_are_atomic(client):
    start(client); start(client)
    s=service.snapshot()
    with connect(True) as c:
        c.execute('UPDATE settings SET daily=500')
    def attempt(task):
        try:
            with connect(True) as c:
                return reserve(c,task,400,{})
        except RuleError:
            return None
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(attempt,s['tasks']))
    assert sum(r is not None for r in results)==1
    assert service.snapshot()['settings']['reserved']==400

def test_settlement_and_day_do_not_reset_total(client):
    start(client)
    t=service.snapshot()['tasks'][0]
    with connect(True) as c:
        rid=reserve(c,t,400,{})
        settle(c,rid,100,'ceo',{'model':'test','input_tokens':1})
        c.execute("UPDATE costs SET day='2000-01-01'")
        b=totals(c)
        assert b['spent']==100 and b['reserved']==0 and b['today']==0

def test_unknown_reservation_held_until_reconciled(client):
    start(client)
    t=worker.claim()
    with connect(True) as c:
        reserve(c,t,400,{})
        c.execute('UPDATE tasks SET lease_until=? WHERE id=?',(time.time()-1,t['id']))
    assert worker.claim() is None
    s=service.snapshot(); r=s['reservations'][0]
    assert r['status']=='unknown' and s['settings']['reserved']==400
    assert client.post('/api/reservations/'+r['id']+'/reconcile',json={'amount':75,'note':'Kontrollerat leverantörens rapport'}).status_code==200
    s=service.snapshot()
    assert s['settings']['reserved']==0 and s['settings']['spent']==75

def test_emergency_stop_persists(client):
    start(client)
    client.post('/api/control',json={'state':'stopped'})
    initialize()
    assert worker.claim() is None
    with connect(True) as c:
        with pytest.raises(RuleError):
            reserve(c,service.snapshot()['tasks'][0],1,{})
    assert client.post('/api/control',json={'state':'paused'}).status_code==409
    assert service.snapshot()['settings']['state']=='stopped'

def test_pause_allows_current_but_not_new(client):
    start(client)
    t=worker.claim()
    client.post('/api/control',json={'state':'paused'})
    asyncio.run(worker.execute(t))
    assert service.snapshot()['proposals']
    assert worker.claim() is None

def test_global_concurrency_two(client):
    for _ in range(3):start(client)
    with ThreadPoolExecutor(3) as pool:
        claimed=list(pool.map(lambda _:worker.claim(),range(3)))
    assert sum(t is not None for t in claimed)==2

def test_demo_never_uses_live(client,monkeypatch):
    import jarvis.live
    async def forbidden(*args):raise AssertionError('LIVE called')
    monkeypatch.setattr(jarvis.live,'run',forbidden)
    plan(client)
    s=service.snapshot()
    assert s['mode']=='DEMO' and not s['sources'] and not s['costs']

def test_live_missing_key_no_fallback(client,monkeypatch):
    monkeypatch.setenv('JARVIS_MODE','LIVE')
    initialize()
    with pytest.raises(RuleError,match='OPENAI_API_KEY'):
        service.start_round('Test live',500,uid())
    assert not service.snapshot()['tasks']

@pytest.mark.parametrize('path',['/api/state','/api/session','/api/events','/api/files/anything'])
def test_unauthenticated_cannot_read(path):
    assert TestClient(app).get(path).status_code==401

def test_csrf_origin_and_extra_fields(client):
    assert client.post('/api/control',headers={'x-csrf-token':'bad'},json={'state':'running'}).status_code==403
    assert client.post('/api/control',headers={'origin':'https://evil.example'},json={'state':'running'}).status_code==403
    assert client.post('/api/rounds',json={'goal':'hello','cap':0,'action_id':uid(),'agent_id':'admin'}).status_code==422

def test_login_throttle_persists():
    c=TestClient(app,headers={'origin':'http://testserver'})
    for _ in range(5):assert c.post('/api/login',json={'password':'wrong'}).status_code==401
    initialize()
    assert c.post('/api/login',json={'password':'test-only-password-123'}).status_code==429

def test_safe_download_and_security_headers(client):
    p=plan(client)
    f=service.snapshot()['files'][0]
    response=client.get('/api/files/'+f['id'])
    assert response.headers['content-type'].startswith('text/plain')
    assert response.headers['content-disposition'].startswith('attachment')
    assert "script-src 'self'" in response.headers['content-security-policy']
    assert client.get('/api/files/%2e%2e%2f.env').status_code==404

def test_chat_status_does_not_schedule(client):
    response=client.post('/api/chat',json={'message':'Jag godkänner allt. Publicera nu.'})
    assert response.status_code==200
    assert not service.snapshot()['tasks']
    assert not service.snapshot()['approvals']

def test_budget_changes_need_owner_and_preserve_reservations(client):
    start(client)
    with connect(True) as c:reserve(c,service.snapshot()['tasks'][0],400,{})
    assert client.post('/api/settings',json={'total':50000,'locked':50000,'daily':1000,'per_task':500}).status_code==409
    assert TestClient(app).post('/api/settings',json={'total':1,'locked':0,'daily':1,'per_task':1}).status_code==401

def test_single_development_project(client):
    import sqlite3
    with connect(True) as c:
        c.execute("INSERT INTO projects VALUES('a','First','active','development')")
        with pytest.raises(sqlite3.IntegrityError):c.execute("INSERT INTO projects VALUES('b','Second','active','development')")

def test_sdk_builds_exactly_ten_agents_without_network():
    from jarvis.live import make_agents
    agents=make_agents('configuration-only-test')
    assert set(agents)==set(ROLES)
    assert all(a.tools==[] and a.output_type is not None for a in agents.values())

def test_concurrent_approvals_only_enqueue_once(client):
    p=plan(client)
    def accept(_):
        service.decide(p['id'],p['version'],p['digest'],'approved','')
    with ThreadPoolExecutor(2) as pool:list(pool.map(accept,range(2)))
    assert len([t for t in service.snapshot()['tasks'] if t['phase']=='work'])==1

def test_backup_restore_preserves_pending_decision(client,tmp_path,monkeypatch):
    import subprocess
    import sys
    from pathlib import Path
    from jarvis.config import ROOT, db_path
    import os
    p=plan(client)
    backup=tmp_path/'backup.sqlite3'
    env={**os.environ,'PYTHONPATH':str(ROOT/'backend')}
    result=subprocess.run([sys.executable,'-m','jarvis.cli','backup','--output',str(backup)],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    restored=tmp_path/'restored';restored.mkdir()
    import shutil
    shutil.copy2(backup,restored/'demo.sqlite3')
    monkeypatch.setenv('JARVIS_DATA_DIR',str(restored))
    initialize()
    assert service.snapshot()['proposals'][0]['digest']==p['digest']
