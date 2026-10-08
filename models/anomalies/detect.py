import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

DB_PATH = Path(__file__).resolve().parents[2] / "db" / "proto_phoros.db"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
SEED = 20260930


def _load(conn, query):
    return pd.read_sql_query(query, conn)


def _flag(df, feature_cols, contamination):
    features = df[feature_cols].fillna(0)
    model = IsolationForest(contamination=contamination, random_state=SEED)
    pred = model.fit_predict(features)
    return df.loc[pred == -1]


def detect_movement_anomalies(conn):
    # a consumption/issue is unusual relative to how that item normally
    # moves through that same movement type, not relative to its raw size
    # (a fuel issue and a rifle-optic issue live on completely different
    # scales, so the z-score against the item's own history is what
    # actually carries the signal, not the quantity itself)
    df = _load(conn, """
        SELECT id, item_id, type, quantity
        FROM movement
        WHERE type IN ('consumption', 'issue')
    """)
    stats = df.groupby(["item_id", "type"])["quantity"].agg(["mean", "std"]).reset_index()
    stats["std"] = stats["std"].replace(0, np.nan)
    df = df.merge(stats, on=["item_id", "type"], how="left")
    df["zscore"] = ((df["quantity"] - df["mean"]) / df["std"]).fillna(0)

    flagged = _flag(df, ["zscore"], contamination=0.002)
    return flagged[["id"]].assign(table_name="movement")


def detect_repair_anomalies(conn):
    # labor_hours only means something next to the defect's own severity --
    # 8 hours on a severity-3 job is normal, 8 hours on a severity-1 one is not
    df = _load(conn, """
        SELECT r.id, r.labor_hours, d.severity
        FROM repair r
        LEFT JOIN defect d ON r.defect_id = d.id
    """)
    df["severity"] = df["severity"].fillna(0)
    df["labor_residual"] = df["labor_hours"] - df.groupby("severity")["labor_hours"].transform("mean")

    flagged = _flag(df, ["labor_residual"], contamination=0.02)
    return flagged[["id"]].assign(table_name="repair")


def detect_requirement_line_anomalies(conn):
    # the ratio of what got approved to what was actually needed is the
    # tell here -- final_qty and computed_gap_qty on their own just track
    # the item's normal order size, which varies hugely across items
    df = _load(conn, """
        SELECT id, computed_gap_qty, final_qty
        FROM requirement_line
        WHERE status IN ('approved', 'edited') AND final_qty IS NOT NULL
    """)
    df["ratio"] = (df["final_qty"] / df["computed_gap_qty"].replace(0, np.nan)).fillna(1)

    flagged = _flag(df, ["ratio"], contamination=0.02)
    return flagged[["id"]].assign(table_name="requirement_line")


def detect_expired_lot_usage(conn):
    # this one isn't a statistical outlier, it's a rule: ammo used after
    # its own lot's expiry date is a violation on its face, no model needed
    df = _load(conn, """
        SELECT m.lot_id AS id, m.date AS movement_date, al.expiry_date
        FROM movement m
        JOIN ammo_lot al ON m.lot_id = al.id
        WHERE m.type = 'consumption' AND m.lot_id IS NOT NULL
    """)
    df["days_past_expiry"] = (
        pd.to_datetime(df["movement_date"]) - pd.to_datetime(df["expiry_date"])
    ).dt.days

    expired = df.groupby("id")["days_past_expiry"].max()
    flagged_ids = expired[expired > 0].index
    return pd.DataFrame({"id": flagged_ids, "table_name": "ammo_lot"})


def evaluate(flagged, conn):
    truth = _load(conn, "SELECT table_name, row_id, anomaly_type FROM synthetic_anomaly_log")
    truth_set = set(zip(truth["table_name"], truth["row_id"]))
    flagged_set = set(zip(flagged["table_name"], flagged["id"]))

    tp = len(truth_set & flagged_set)
    precision = tp / len(flagged_set) if flagged_set else 0.0
    recall = tp / len(truth_set) if truth_set else 0.0

    print(f"flagged: {len(flagged_set)}  true anomalies: {len(truth_set)}  matched: {tp}")
    print(f"precision: {precision:.2f}  recall: {recall:.2f}\n")

    print("recall by anomaly_type:")
    for atype, sub in truth.groupby("anomaly_type"):
        sub_set = set(zip(sub["table_name"], sub["row_id"]))
        hit = len(sub_set & flagged_set)
        print(f"  {atype:<22} {hit}/{len(sub_set)}")

    return {"precision": precision, "recall": recall, "true_positives": tp}


def main():
    conn = sqlite3.connect(DB_PATH)

    flagged = pd.concat([
        detect_movement_anomalies(conn),
        detect_repair_anomalies(conn),
        detect_requirement_line_anomalies(conn),
        detect_expired_lot_usage(conn),
    ], ignore_index=True)

    evaluate(flagged, conn)
    conn.close()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACT_DIR / "flagged_anomalies.csv"
    flagged.to_csv(out_path, index=False)
    print(f"\nflagged rows -> {out_path}")


if __name__ == "__main__":
    main()