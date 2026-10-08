import random
import time

import config
from db import fresh_connection
from generators import org, catalog, fleet, exercises, weapons, stock, anomalies

TABLES = [
    "unit", "warehouse", "item", "app_user", "vehicle", "inspection", "defect",
    "repair", "training_exercise", "weapon", "range_session", "ammo_lot",
    "allowance", "movement", "purchase_order", "requirement_line",
    "weather_reading", "synthetic_anomaly_log",
]


def main():
    random.seed(config.SEED)
    started = time.time()

    conn = fresh_connection(config.DB_PATH, config.SCHEMA_PATH)

    org_data = org.generate(conn)
    catalog_data = catalog.generate(conn)
    fleet_data = fleet.generate(conn, org_data, catalog_data)

    battalions_by_id = {bn["id"]: bn for bn in org_data["battalions"]}
    exercise_list = exercises.generate_exercises(conn, org_data["battalions"])
    exercises.generate_weather(conn, org_data["battalions"])

    weapons_data = weapons.generate(conn, org_data["companies"], battalions_by_id, exercise_list)

    stock.generate(
        conn, org_data, catalog_data,
        fleet_data["repairs"], weapons_data["range_sessions"], exercise_list,
    )

    anomalies.generate(conn)

    conn.commit()

    print(f"generated in {time.time() - started:.1f}s\n")
    for table in TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<22} {count}")

    conn.close()


if __name__ == "__main__":
    main()
