import random
from datetime import date, timedelta

N_PER_TYPE = 10


def _log(conn, table_name, row_id, anomaly_type, notes):
    conn.execute(
        "INSERT INTO synthetic_anomaly_log (table_name, row_id, anomaly_type, notes) "
        "VALUES (?, ?, ?, ?)",
        (table_name, row_id, anomaly_type, notes),
    )


def generate(conn):
    rows = conn.execute(
        "SELECT id, quantity FROM movement WHERE type IN ('consumption','issue') "
        "ORDER BY RANDOM() LIMIT ?", (N_PER_TYPE,)
    ).fetchall()
    for row_id, qty in rows:
        new_qty = max(qty + 1, round(qty * random.uniform(4, 8)))
        conn.execute("UPDATE movement SET quantity = ? WHERE id = ?", (new_qty, row_id))
        _log(conn, "movement", row_id, "quantity_spike",
             f"Quantity inflated from {qty} to {new_qty}")

    rows = conn.execute(
        "SELECT id, labor_hours FROM repair ORDER BY RANDOM() LIMIT ?", (N_PER_TYPE,)
    ).fetchall()
    for row_id, hours in rows:
        new_hours = round(random.uniform(15, 25), 1)
        conn.execute("UPDATE repair SET labor_hours = ? WHERE id = ?", (new_hours, row_id))
        _log(conn, "repair", row_id, "labor_hours_outlier",
             f"Labor hours raised from {hours} to {new_hours}")

    rows = conn.execute(
        "SELECT id, date, lot_id FROM movement "
        "WHERE type = 'consumption' AND lot_id IS NOT NULL "
        "ORDER BY RANDOM() LIMIT ?", (N_PER_TYPE,)
    ).fetchall()
    for row_id, date_str, lot_id in rows:
        move_date = date.fromisoformat(date_str)
        new_expiry = move_date - timedelta(days=random.randint(1, 60))
        conn.execute("UPDATE ammo_lot SET expiry_date = ? WHERE id = ?", (new_expiry.isoformat(), lot_id))
        _log(conn, "ammo_lot", lot_id, "expired_lot_used",
             f"Expiry backdated to {new_expiry.isoformat()}, consumed on {date_str}")

    rows = conn.execute(
        "SELECT id, computed_gap_qty, final_qty FROM requirement_line "
        "WHERE status = 'approved' ORDER BY RANDOM() LIMIT ?", (N_PER_TYPE,)
    ).fetchall()
    for row_id, gap, final_qty in rows:
        new_final = round(gap * random.uniform(3, 5))
        conn.execute("UPDATE requirement_line SET final_qty = ? WHERE id = ?", (new_final, row_id))
        _log(conn, "requirement_line", row_id, "over_approval",
             f"final_qty raised from {final_qty} to {new_final} against gap {gap}")
