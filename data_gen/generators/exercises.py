import math
import random
from datetime import timedelta

import config

EXERCISE_TYPE_WEIGHTS = {"field_exercise": 45, "drill": 35, "live_fire": 20}
EXERCISE_DURATION_DAYS = {
    "drill": (1, 1),
    "field_exercise": (3, 7),
    "live_fire": (1, 3),
}

TERRAIN_CLIMATE = {
    "desert": {"mean_temp": 28, "amplitude": 12, "rain_chance": 0.05, "rain_scale": 6},
    "coastal": {"mean_temp": 20, "amplitude": 8, "rain_chance": 0.25, "rain_scale": 10},
    "mountain": {"mean_temp": 10, "amplitude": 10, "rain_chance": 0.30, "rain_scale": 15},
    "temperate": {"mean_temp": 15, "amplitude": 10, "rain_chance": 0.20, "rain_scale": 10},
}


def _insert_exercise(conn, unit_id, name, etype, start_date, end_date):
    cur = conn.execute(
        "INSERT INTO training_exercise (unit_id, name, type, start_date, end_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (unit_id, name, etype, start_date.isoformat(), end_date.isoformat()),
    )
    return cur.lastrowid


def _insert_weather(conn, unit_id, date, temp, precip):
    conn.execute(
        "INSERT INTO weather_reading (unit_id, date, temperature_c, precipitation_mm) "
        "VALUES (?, ?, ?, ?)",
        (unit_id, date.isoformat(), round(temp, 1), round(precip, 1)),
    )


def generate_exercises(conn, battalions):
    exercises = []
    types, weights = zip(*EXERCISE_TYPE_WEIGHTS.items())

    for bn in battalions:
        n = random.randint(8, 14)
        cursor_date = config.START_DATE + timedelta(days=random.randint(0, 60))
        counters = {"live_fire": 0, "field_exercise": 0, "drill": 0}

        for _ in range(n):
            if cursor_date > config.TODAY:
                break

            etype = random.choices(types, weights=weights, k=1)[0]
            counters[etype] += 1
            lo, hi = EXERCISE_DURATION_DAYS[etype]
            duration = random.randint(lo, hi)
            end_date = min(cursor_date + timedelta(days=duration - 1), config.TODAY)

            label = etype.replace("_", " ").title()
            name = f"{label} {counters[etype]}"
            exercise_id = _insert_exercise(conn, bn["id"], name, etype, cursor_date, end_date)

            exercises.append(
                {
                    "id": exercise_id,
                    "battalion_id": bn["id"],
                    "warehouse_id": bn["warehouse_id"],
                    "type": etype,
                    "start_date": cursor_date,
                    "end_date": end_date,
                }
            )

            cursor_date = end_date + timedelta(days=random.randint(60, 150))

    exercises.sort(key=lambda e: e["start_date"])
    return exercises


def generate_weather(conn, battalions):
    total_days = (config.TODAY - config.START_DATE).days + 1

    for bn in battalions:
        climate = TERRAIN_CLIMATE.get(bn["terrain"], TERRAIN_CLIMATE["temperate"])
        for offset in range(total_days):
            date = config.START_DATE + timedelta(days=offset)
            day_of_year = date.timetuple().tm_yday
            seasonal = math.sin(2 * math.pi * (day_of_year - 80) / 365)
            temp = climate["mean_temp"] + climate["amplitude"] * seasonal + random.gauss(0, 2.5)

            precip = 0.0
            if random.random() < climate["rain_chance"]:
                precip = random.uniform(1, climate["rain_scale"])

            _insert_weather(conn, bn["id"], date, temp, precip)
