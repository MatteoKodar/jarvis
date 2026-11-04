from .db import day, uid, now, pack

class RuleError(Exception):
    pass

def totals(c):
    s = dict(c.execute("SELECT * FROM settings WHERE id=1").fetchone())
    s["spent"] = c.execute("SELECT COALESCE(SUM(amount),0) FROM costs").fetchone()[0]
    s["reserved"] = c.execute("SELECT COALESCE(SUM(amount),0) FROM reservations WHERE status IN ('held','unknown')").fetchone()[0]
    s["available"] = s["total"] - s["locked"] - s["spent"] - s["reserved"]
    s["today"] = c.execute("SELECT COALESCE(SUM(amount),0) FROM costs WHERE day=?", (day(),)).fetchone()[0]
    # Old unknown reservations still count against today's allowance.
    s["daily_reserved"] = s["reserved"]
    return s

def check_running(c):
    if c.execute("SELECT state FROM settings WHERE id=1").fetchone()[0] == "stopped":
        raise RuleError("Nödstopp är aktivt. Ägaren måste återuppta arbetet.")

def reserve(c, task, amount, metadata):
    check_running(c)
    s = totals(c)
    task_spent = c.execute("SELECT COALESCE(SUM(amount),0) FROM costs WHERE task_id=?", (task["id"],)).fetchone()[0]
    task_held = c.execute("SELECT COALESCE(SUM(amount),0) FROM reservations WHERE task_id=? AND status IN ('held','unknown')", (task["id"],)).fetchone()[0]
    if amount < 0 or amount + task_spent + task_held > min(task["cap"], s["per_task"]):
        raise RuleError("Uppgiftens kostnadstak räcker inte för maximal beräknad användning.")
    if amount > s["available"] or amount + s["today"] + s["daily_reserved"] > s["daily"]:
        raise RuleError("Budgetspärr: otillräckligt totalt eller dagligt utrymme.")
    rid = uid()
    c.execute("INSERT INTO reservations VALUES(?,?,?,?,?,?)", (rid, task["id"], amount, day(), "held", pack(metadata)))
    return rid

def settle(c, rid, amount, agent_id, metadata):
    row = c.execute("SELECT * FROM reservations WHERE id=? AND status='held'", (rid,)).fetchone()
    if not row:
        raise RuleError("Reservationen saknas eller kräver avstämning.")
    if amount > row["amount"]:
        raise RuleError("Leverantörsanvändningen överstiger reservationen; manuell avstämning krävs.")
    c.execute("UPDATE reservations SET status='settled' WHERE id=?", (rid,))
    c.execute("INSERT INTO costs VALUES(?,?,?,?,?,?,?,?)", (uid(), row["task_id"], agent_id, amount, row["day"], "estimate", pack(metadata), now()))
