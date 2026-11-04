-- Ägarbeslut 2026-11-03: endast fotbollsanalys. Historik och budgetbelopp bevaras.
INSERT INTO events(created,kind,message,task_id)
SELECT strftime('%Y-%m-%dT%H:%M:%fZ','now'),'project_focus',
       'Fokus ändrat till fotbollsanalys och pappersspel. Tidigare mål: ' || goal,NULL FROM settings WHERE id=1;
UPDATE dispatch_control SET epoch=epoch+1 WHERE id=1;
UPDATE reservations SET status='released' WHERE status='held' AND id IN
    (SELECT reservation_id FROM operations WHERE state='prepared');
UPDATE reservations SET status='unknown' WHERE status='held' AND id IN
    (SELECT reservation_id FROM operations WHERE state='possible_send');
UPDATE operations SET state=CASE WHEN state='prepared' THEN 'cancelled' ELSE 'unknown' END,
    finished=strftime('%Y-%m-%dT%H:%M:%fZ','now'),
    uncertainty='Fokusbyte: äldre operation fortsätter inte. Möjlig sändning kräver manuell avstämning.'
    WHERE state IN ('prepared','possible_send');
UPDATE reservations SET status='unknown' WHERE status='held' AND task_id IN
    (SELECT id FROM tasks WHERE status IN ('queued','running','approval','review'));
UPDATE runs SET state='blocked',finished=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE state='running';
UPDATE tasks SET status='blocked',lease_until=NULL,
    error='Äldre uppdrag arkiverat vid fokusbyte. Ett nytt fotbollsuppdrag kräver nytt beslut.'
    WHERE status IN ('queued','running','approval','review');
UPDATE proposals SET status='superseded',note=note || ' Arkiverat vid fokusbyte; ingen fortsatt köning.' WHERE status='pending';
UPDATE schedule SET enabled=0;
UPDATE settings SET goal='Undersök om fotbollens 90-minutersodds ger en genomförbar fördel efter kostnader. Endast simulerade insatser.',
    state=CASE WHEN state='stopped' THEN 'stopped' ELSE 'paused' END WHERE id=1;
INSERT INTO schema_migrations(version) VALUES(6);
