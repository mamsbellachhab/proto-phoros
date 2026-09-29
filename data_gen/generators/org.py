import random

import config
from names import ordinal, COMPANY_LETTERS, FIRST_NAMES, LAST_NAMES


def _insert_unit(conn, name, unit_type, parent_id, terrain):
    cur = conn.execute(
        "INSERT INTO unit (name, type, parent_unit_id, terrain_type) "
        "VALUES (?, ?, ?, ?)",
        (name, unit_type, parent_id, terrain),
    )
    return cur.lastrowid


def _insert_warehouse(conn, name, unit_id):
    cur = conn.execute(
        "INSERT INTO warehouse (name, unit_id) VALUES (?, ?)", (name, unit_id)
    )
    return cur.lastrowid


def _insert_user(conn, username, full_name, role, unit_id):
    cur = conn.execute(
        "INSERT INTO app_user (username, full_name, role, unit_id) "
        "VALUES (?, ?, ?, ?)",
        (username, full_name, role, unit_id),
    )
    return cur.lastrowid


def _random_name(used):
    while True:
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        if name not in used:
            used.add(name)
            return name


def generate(conn):
    division_id = _insert_unit(conn, "1st Division", "division", None, None)

    brigades = []
    battalions = []
    companies = []

    for b in range(1, config.N_BRIGADES + 1):
        terrain = config.BRIGADE_TERRAIN[(b - 1) % len(config.BRIGADE_TERRAIN)]
        brigade_name = f"{ordinal(b)} Brigade"
        brigade_id = _insert_unit(conn, brigade_name, "brigade", division_id, terrain)
        brigades.append({"id": brigade_id, "name": brigade_name, "terrain": terrain})

        for t in range(1, config.N_BATTALIONS_PER_BRIGADE + 1):
            bn_name = f"{ordinal(t)} Battalion, {brigade_name}"
            bn_id = _insert_unit(conn, bn_name, "battalion", brigade_id, terrain)
            battalions.append(
                {
                    "id": bn_id,
                    "name": bn_name,
                    "terrain": terrain,
                    "brigade_id": brigade_id,
                }
            )

            for c in range(config.N_COMPANIES_PER_BATTALION):
                letter = COMPANY_LETTERS[c]
                co_name = f"{letter} Company, {bn_name}"
                co_id = _insert_unit(conn, co_name, "company", bn_id, terrain)
                companies.append(
                    {
                        "id": co_id,
                        "name": co_name,
                        "terrain": terrain,
                        "battalion_id": bn_id,
                    }
                )

    central_wh_id = _insert_warehouse(conn, "Central Depot", None)
    for bn in battalions:
        bn["warehouse_id"] = _insert_warehouse(conn, f"{bn['name']} Supply Point", bn["id"])

    users = []
    used_names = set()
    admin_id = _insert_user(conn, "admin", "System Administrator", "admin", None)
    users.append({"id": admin_id, "role": "admin", "unit_id": None})

    for bn in battalions:
        username = "u" + "".join(ch for ch in bn["name"].lower() if ch.isalnum())[:16]
        full_name = _random_name(used_names)
        uid = _insert_user(conn, username, full_name, "unit", bn["id"])
        users.append({"id": uid, "role": "unit", "unit_id": bn["id"]})

    return {
        "division_id": division_id,
        "brigades": brigades,
        "battalions": battalions,
        "companies": companies,
        "central_warehouse_id": central_wh_id,
        "users": users,
        "admin_id": admin_id,
    }
