import random
from datetime import timedelta

import config

WEAPON_TEMPLATES = [
    ("rifle", "5.56x45mm", 18),
    ("sidearm", "9x19mm", 4),
    ("machine_gun", "7.62x51mm", 2),
    ("designated_marksman_rifle", "7.62x51mm", 1),
]

ROUNDS_PER_SESSION = {
    "rifle": (20, 40),
    "sidearm": (10, 20),
    "machine_gun": (60, 150),
    "designated_marksman_rifle": (10, 20),
}


def _insert_weapon(conn, serial, wtype, caliber, unit_id, status, last_inspection):
    cur = conn.execute(
        "INSERT INTO weapon (serial_number, type, caliber, unit_id, status, "
        "last_inspection_date) VALUES (?, ?, ?, ?, ?, ?)",
        (serial, wtype, caliber, unit_id, status, last_inspection),
    )
    return cur.lastrowid


def _insert_range_session(conn, weapon_id, exercise_id, date):
    cur = conn.execute(
        "INSERT INTO range_session (weapon_id, exercise_id, date) VALUES (?, ?, ?)",
        (weapon_id, exercise_id, date.isoformat()),
    )
    return cur.lastrowid


def generate(conn, companies, battalions_by_id, exercises):
    live_fire_by_battalion = {}
    for ex in exercises:
        if ex["type"] == "live_fire":
            live_fire_by_battalion.setdefault(ex["battalion_id"], []).append(ex)

    weapons = []
    range_sessions = []
    seq = 1

    for co in companies:
        bn = battalions_by_id[co["battalion_id"]]
        for wtype, caliber, count in WEAPON_TEMPLATES:
            for _ in range(count):
                serial = f"WP-{co['id']:03d}-{seq:04d}"
                seq += 1

                status = random.choices(
                    ["active", "in_repair", "decommissioned"], weights=[90, 7, 3], k=1
                )[0]
                last_inspection = None
                if random.random() < 0.8:
                    last_inspection = (
                        config.TODAY - timedelta(days=random.randint(1, 180))
                    ).isoformat()

                weapon_id = _insert_weapon(
                    conn, serial, wtype, caliber, co["id"], status, last_inspection
                )
                weapons.append(
                    {
                        "id": weapon_id,
                        "company_id": co["id"],
                        "battalion_id": bn["id"],
                        "warehouse_id": bn["warehouse_id"],
                        "type": wtype,
                        "caliber": caliber,
                        "status": status,
                    }
                )

                n_sessions = random.randint(6, 12)
                for _ in range(n_sessions):
                    exercise_id = None
                    if random.random() < 0.4 and live_fire_by_battalion.get(bn["id"]):
                        ex = random.choice(live_fire_by_battalion[bn["id"]])
                        span = (ex["end_date"] - ex["start_date"]).days
                        date = ex["start_date"] + timedelta(days=random.randint(0, max(span, 0)))
                        exercise_id = ex["id"]
                    else:
                        span = (config.TODAY - config.START_DATE).days
                        date = config.START_DATE + timedelta(days=random.randint(0, span))

                    lo, hi = ROUNDS_PER_SESSION[wtype]
                    rounds = random.randint(lo, hi)

                    session_id = _insert_range_session(conn, weapon_id, exercise_id, date)
                    range_sessions.append(
                        {
                            "id": session_id,
                            "weapon_id": weapon_id,
                            "warehouse_id": bn["warehouse_id"],
                            "caliber": caliber,
                            "date": date,
                            "exercise_id": exercise_id,
                            "rounds": rounds,
                        }
                    )

    range_sessions.sort(key=lambda r: r["date"])
    return {"weapons": weapons, "range_sessions": range_sessions}
