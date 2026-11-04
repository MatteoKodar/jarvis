from datetime import datetime
from zoneinfo import ZoneInfo
from .config import mode, missing_live
from .db import connect, event
from .service import add_task

def tick():
    local = datetime.now(ZoneInfo('Europe/Stockholm'))
    today, clock = local.date().isoformat(), local.strftime('%H:%M')
    with connect(True) as c:
        s = dict(c.execute('SELECT * FROM schedule WHERE id=1').fetchone())
        if not s['enabled'] or s['remaining'] <= 0 or today > s['expires'] or s['last_day'] == today or clock < s['at']:
            return
        settings = c.execute('SELECT * FROM settings WHERE id=1').fetchone()
        if settings['state'] != 'running' or (mode() == 'LIVE' and missing_live()):
            return
        if s['cap'] > settings['per_task']:
            c.execute('UPDATE schedule SET enabled=0 WHERE id=1')
            event(c,'schedule','Schema pausat: ändrade budgetgränser kräver ett nytt schema.')
            return
        if c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('queued','running','approval','review')").fetchone()[0] >= 12:
            return
        add_task(c,action_id=f"schedule:{s['version']}:{today}",agent_id='ceo',title=s['goal'],context='Ägargodkänt begränsat schema. Föreslå ett internt nästa steg.',criteria='Ett granskningsbart förslag; inget specialistarbete utan nytt ägarbeslut.',cap=s['cap'],phase='plan')
        c.execute('UPDATE schedule SET last_day=?,remaining=remaining-1 WHERE id=1',(today,))
        event(c,'schedule','Schemalagd VD-omgång köad. Specialistarbete kräver separat beslut.')
