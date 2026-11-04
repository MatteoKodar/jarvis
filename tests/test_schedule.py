from jarvis.db import connect, initialize
from jarvis.schedule import tick
from jarvis.service import snapshot

def test_schedule_authorized_bounded_idempotent(client):
    client.post('/api/control',json={'state':'running'})
    response=client.post('/api/schedule',json={'enabled':True,'at':'00:00','goal':'Undersök efterfrågan','cap':200,'remaining':2})
    assert response.status_code==200
    tick();tick();initialize();tick()
    s=snapshot()
    assert len(s['tasks'])==1 and s['schedule']['remaining']==1
    assert s['tasks'][0]['agent_id']=='ceo'

def test_paused_schedule_does_not_run(client):
    client.post('/api/schedule',json={'enabled':True,'at':'00:00','goal':'Undersök efterfrågan','cap':200,'remaining':1})
    tick()
    assert not snapshot()['tasks']

def test_expired_schedule_and_excess_rounds(client):
    assert client.post('/api/schedule',json={'enabled':True,'at':'00:00','goal':'Undersök efterfrågan','cap':200,'remaining':8}).status_code==422
    client.post('/api/control',json={'state':'running'})
    client.post('/api/schedule',json={'enabled':True,'at':'00:00','goal':'Undersök efterfrågan','cap':200,'remaining':1})
    with connect(True) as c:c.execute("UPDATE schedule SET expires='2000-01-01'")
    tick()
    assert not snapshot()['tasks']
