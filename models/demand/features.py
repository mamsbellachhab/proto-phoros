import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parents[2] / "db" / "proto_phoros.db"

LAGS = [1, 2, 3, 6, 12]
ROLLING_WINDOWS = [3, 6]

FEATURE_COLS = (
    [f"lag_{l}" for l in LAGS]
    + [f"roll_mean_{w}" for w in ROLLING_WINDOWS]
    + [f"roll_std_{w}" for w in ROLLING_WINDOWS]
    + ["exercise_count", "avg_temp", "total_precip", "criticality", "lead_time_days", "month_num"]
)


def _load_monthly_consumption(conn):
    query = """
        SELECT warehouse_id, item_id,
               strftime('%Y-%m', date) AS month,
               SUM(quantity) AS qty
        FROM movement
        WHERE type IN ('consumption', 'issue')
        GROUP BY warehouse_id, item_id, month
    """
    df = pd.read_sql_query(query, conn)
    df["month"] = pd.to_datetime(df["month"])
    return df


def _load_exercise_counts(conn):
    query = """
        SELECT unit_id, strftime('%Y-%m', start_date) AS month, COUNT(*) AS exercise_count
        FROM training_exercise
        GROUP BY unit_id, month
    """
    df = pd.read_sql_query(query, conn)
    df["month"] = pd.to_datetime(df["month"])
    return df


def _load_weather(conn):
    query = """
        SELECT unit_id, strftime('%Y-%m', date) AS month,
               AVG(temperature_c) AS avg_temp,
               SUM(precipitation_mm) AS total_precip
        FROM weather_reading
        GROUP BY unit_id, month
    """
    df = pd.read_sql_query(query, conn)
    df["month"] = pd.to_datetime(df["month"])
    return df


def _load_warehouse_unit_map(conn):
    return pd.read_sql_query("SELECT id AS warehouse_id, unit_id FROM warehouse", conn)


def _load_items(conn):
    return pd.read_sql_query(
        "SELECT id AS item_id, category, criticality, lead_time_days FROM item", conn
    )


def _add_lag_features(panel):
    panel = panel.sort_values(["warehouse_id", "item_id", "month"])
    group = panel.groupby(["warehouse_id", "item_id"])["qty"]

    for lag in LAGS:
        panel[f"lag_{lag}"] = group.shift(lag)

    for window in ROLLING_WINDOWS:
        shifted = group.shift(1)
        panel[f"roll_mean_{window}"] = shifted.rolling(window).mean()
        panel[f"roll_std_{window}"] = shifted.rolling(window).std()

    return panel


def build_panel(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)

    consumption = _load_monthly_consumption(conn)
    warehouse_unit = _load_warehouse_unit_map(conn)
    exercises = _load_exercise_counts(conn)
    weather = _load_weather(conn)
    items = _load_items(conn)
    conn.close()

    # full (warehouse, item, month) grid so gaps become explicit zero-consumption rows
    all_months = pd.date_range(consumption["month"].min(), consumption["month"].max(), freq="MS")
    combos = consumption[["warehouse_id", "item_id"]].drop_duplicates()
    grid = combos.merge(pd.DataFrame({"month": all_months}), how="cross")

    panel = grid.merge(consumption, on=["warehouse_id", "item_id", "month"], how="left")
    panel["qty"] = panel["qty"].fillna(0)

    panel = panel.merge(warehouse_unit, on="warehouse_id", how="left")
    panel = panel.merge(exercises, on=["unit_id", "month"], how="left")
    panel = panel.merge(weather, on=["unit_id", "month"], how="left")
    panel = panel.merge(items, on="item_id", how="left")

    panel["exercise_count"] = panel["exercise_count"].fillna(0)
    panel["avg_temp"] = panel.groupby("item_id")["avg_temp"].transform(lambda s: s.fillna(s.mean()))
    panel["total_precip"] = panel["total_precip"].fillna(0)

    panel = _add_lag_features(panel)
    panel["month_num"] = panel["month"].dt.month

    return panel


if __name__ == "__main__":
    panel = build_panel()
    out_path = Path(__file__).resolve().parent / "panel.pkl"
    panel.to_pickle(out_path)
    print(f"panel: {len(panel)} rows, {panel['warehouse_id'].nunique()} warehouses, "
          f"{panel['item_id'].nunique()} items -> {out_path}")
    print(panel[["warehouse_id", "item_id", "month", "qty"] + FEATURE_COLS].head())