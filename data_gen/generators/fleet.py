import random
from datetime import timedelta

import config

VEHICLE_TEMPLATES = [
    ("truck", "Model T-6 Cargo Truck", 8, 40),
    ("truck", "Model T-8 Tanker Truck", 2, 45),
    ("ifv", "Model AV-12 Infantry Carrier", 4, 25),
    ("jeep", "Model J-4 Light Utility Vehicle", 5, 60),
    ("ambulance", "Model M-2 Field Ambulance", 1, 20),
]

TERRAIN_WEAR = {"desert": 1.3, "mountain": 1.2, "coastal": 1.0, "temperate": 1.0}

DEFECT_SYSTEMS = [
    "brakes", "lights", "tires", "engine",
    "transmission", "suspension", "electrical", "steering",
]

SYSTEM_DESCRIPTIONS = {
    "brakes": "Pad wear beyond service limit",
    "lights": "Lamp unit not functioning",
    "tires": "Tread depth below minimum",
    "engine": "Abnormal noise under load",
    "transmission": "Rough shifting between gears",
    "suspension": "Excessive play under load",
    "electrical": "Intermittent circuit fault",
    "steering": "Excessive free play",
}

TERRAIN_SYSTEM_WEIGHT = {
    "desert": {"tires": 3, "engine": 2, "electrical": 1},
    "mountain": {"brakes": 3, "suspension": 3, "transmission": 1},
    "coastal": {"electrical": 3, "lights": 1},
    "temperate": {},
}


def _random_date(start, end):
    span = (end - start).days
    if span <= 0:
        return start
    return start + timedelta(days=random.randint(0, span))


def _pick_system(terrain):
    weights = {s: 1 for s in DEFECT_SYSTEMS}
    for s, w in TERRAIN_SYSTEM_WEIGHT.get(terrain, {}).items():
        weights[s] = w
    systems, wts = zip(*weights.items())
    return random.choices(systems, weights=wts, k=1)[0]


def _insert_vehicle(conn, serial, model, category, unit_id, status, mileage, in_service_date):
    cur = conn.execute(
        "INSERT INTO vehicle (serial_number, model, category, unit_id, status, "
        "mileage_km, in_service_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (serial, model, category, unit_id, status, mileage, in_service_date.isoformat()),
    )
    return cur.lastrowid


def _insert_inspection(conn, vehicle_id, date, mileage, result):
    cur = conn.execute(
        "INSERT INTO inspection (vehicle_id, date, mileage_km, result) "
        "VALUES (?, ?, ?, ?)",
        (vehicle_id, date.isoformat(), mileage, result),
    )
    return cur.lastrowid


def _insert_defect(conn, inspection_id, system, severity, description):
    cur = conn.execute(
        "INSERT INTO defect (inspection_id, system, severity, description) "
        "VALUES (?, ?, ?, ?)",
        (inspection_id, system, severity, description),
    )
    return cur.lastrowid


def _insert_repair(conn, vehicle_id, defect_id, date, rtype, item_id, quantity, labor_hours, outcome):
    cur = conn.execute(
        "INSERT INTO repair (vehicle_id, defect_id, date, type, item_id, "
        "quantity, labor_hours, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (vehicle_id, defect_id, date.isoformat(), rtype, item_id, quantity, labor_hours, outcome),
    )
    return cur.lastrowid


def generate(conn, org, catalog):
    vehicles = []
    repairs = []
    seq = 1

    for bn in org["battalions"]:
        for category, model, count, daily_km in VEHICLE_TEMPLATES:
            for _ in range(count):
                serial = f"VH-{bn['id']:03d}-{seq:04d}"
                seq += 1

                status = random.choices(
                    ["active", "in_repair", "decommissioned"], weights=[85, 10, 5], k=1
                )[0]
                in_service_date = _random_date(
                    config.FLEET_START_DATE, config.TODAY - timedelta(days=60)
                )
                wear = TERRAIN_WEAR.get(bn["terrain"], 1.0) * random.uniform(0.75, 1.25)

                end_date = config.TODAY
                if status == "decommissioned":
                    end_date = _random_date(
                        max(in_service_date, config.START_DATE), config.TODAY
                    )

                days_active = max((end_date - in_service_date).days, 0)
                final_mileage = int(days_active * daily_km * wear)

                vehicle_id = _insert_vehicle(
                    conn, serial, model, category, bn["id"], status,
                    final_mileage, in_service_date,
                )

                vehicles.append(
                    {
                        "id": vehicle_id,
                        "battalion_id": bn["id"],
                        "warehouse_id": bn["warehouse_id"],
                        "terrain": bn["terrain"],
                        "category": category,
                        "status": status,
                        "in_service_date": in_service_date,
                        "end_date": end_date,
                        "daily_km": daily_km,
                        "wear": wear,
                    }
                )

    for v in vehicles:
        insp_start = max(v["in_service_date"], config.START_DATE)
        cursor_date = insp_start + timedelta(days=random.randint(30, 180))

        while cursor_date <= v["end_date"]:
            days_elapsed = (cursor_date - v["in_service_date"]).days
            mileage = int(max(days_elapsed, 0) * v["daily_km"] * v["wear"])

            result = "defects_found" if random.random() < 0.30 else "passed"
            inspection_id = _insert_inspection(conn, v["id"], cursor_date, mileage, result)

            if result == "defects_found":
                n_defects = random.choices([1, 2], weights=[75, 25], k=1)[0]
                for _ in range(n_defects):
                    system = _pick_system(v["terrain"])
                    severity = random.choices([1, 2, 3], weights=[50, 35, 15], k=1)[0]
                    defect_id = _insert_defect(
                        conn, inspection_id, system, severity, SYSTEM_DESCRIPTIONS[system]
                    )

                    if random.random() < 0.75:
                        repair_date = cursor_date + timedelta(days=random.randint(1, 14))
                        if repair_date > config.TODAY:
                            repair_date = config.TODAY

                        parts = catalog["spare_parts_by_category"].get(system)
                        if parts and random.random() < 0.90:
                            rtype = "part_replacement"
                            item = random.choice(parts)
                            item_id = item["id"]
                            quantity = random.choices([1, 2], weights=[80, 20], k=1)[0]
                        else:
                            rtype = random.choice(["adjustment", "repair"])
                            item_id = None
                            quantity = None

                        labor_hours = round(severity * random.uniform(1.0, 3.0), 1)
                        outcome = "recurred" if random.random() < 0.12 else "fixed"

                        repair_id = _insert_repair(
                            conn, v["id"], defect_id, repair_date, rtype,
                            item_id, quantity, labor_hours, outcome,
                        )
                        repairs.append(
                            {
                                "id": repair_id,
                                "vehicle_id": v["id"],
                                "warehouse_id": v["warehouse_id"],
                                "date": repair_date,
                                "item_id": item_id,
                                "quantity": quantity,
                            }
                        )

            cursor_date += timedelta(days=random.randint(150, 210))

    for v in vehicles:
        years_active = max((min(v["end_date"], config.TODAY) - config.START_DATE).days / 365.0, 0)
        n_standalone = sum(1 for _ in range(3) if random.random() < 0.5 * min(years_active, 1))

        for _ in range(n_standalone):
            repair_date = _random_date(config.START_DATE, min(v["end_date"], config.TODAY))
            category = v["category"]
            system = _pick_system(v["terrain"])
            parts = catalog["spare_parts_by_category"].get(system)

            rtype = random.choice(["part_replacement", "adjustment", "repair"])
            if rtype == "part_replacement" and parts:
                item = random.choice(parts)
                item_id = item["id"]
                quantity = 1
            else:
                item_id = None
                quantity = None

            labor_hours = round(random.uniform(0.5, 4.0), 1)
            outcome = "recurred" if random.random() < 0.1 else "fixed"

            repair_id = _insert_repair(
                conn, v["id"], None, repair_date, rtype, item_id, quantity,
                labor_hours, outcome,
            )
            repairs.append(
                {
                    "id": repair_id,
                    "vehicle_id": v["id"],
                    "warehouse_id": v["warehouse_id"],
                    "date": repair_date,
                    "item_id": item_id,
                    "quantity": quantity,
                }
            )

    repairs.sort(key=lambda r: r["date"])
    return {"vehicles": vehicles, "repairs": repairs}
