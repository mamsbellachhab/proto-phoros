import pickle
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
import xgboost as xgb

from features import FEATURE_COLS, LAGS, ROLLING_WINDOWS, build_panel

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
SEED = 20260930


def train(panel):
    usable = panel.dropna(subset=[f"lag_{max(LAGS)}"])

    train_df, test_df = train_test_split(usable, test_size=0.15, random_state=SEED, shuffle=True)

    model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=SEED,
    )
    model.fit(train_df[FEATURE_COLS], train_df["qty"])

    preds = model.predict(test_df[FEATURE_COLS])
    mae = mean_absolute_error(test_df["qty"], preds)
    baseline_mae = mean_absolute_error(test_df["qty"], test_df["lag_1"])
    print(f"holdout MAE: {mae:.2f} (naive last-month baseline: {baseline_mae:.2f})")

    return model


def _next_month_features(history, target_month):
    latest = (
        history.sort_values("month")
        .groupby(["warehouse_id", "item_id"])
        .tail(1)
        .copy()
    )
    latest["month"] = target_month

    for lag in LAGS:
        src_month = target_month - pd.DateOffset(months=lag)
        src = history.loc[history["month"] == src_month, ["warehouse_id", "item_id", "qty"]]
        src = src.rename(columns={"qty": f"lag_{lag}"})
        latest = latest.drop(columns=[f"lag_{lag}"]).merge(
            src, on=["warehouse_id", "item_id"], how="left"
        )

    window_start = target_month - pd.DateOffset(months=max(ROLLING_WINDOWS))
    recent = history[(history["month"] >= window_start) & (history["month"] < target_month)]

    for window in ROLLING_WINDOWS:
        cutoff = target_month - pd.DateOffset(months=window)
        recent_window = recent[recent["month"] >= cutoff]
        stats = recent_window.groupby(["warehouse_id", "item_id"])["qty"].agg(["mean", "std"])
        stats = stats.rename(columns={"mean": f"roll_mean_{window}", "std": f"roll_std_{window}"})
        latest = latest.drop(columns=[f"roll_mean_{window}", f"roll_std_{window}"]).merge(
            stats, on=["warehouse_id", "item_id"], how="left"
        )

    latest["month_num"] = latest["month"].dt.month
    return latest


def forecast(model, panel, horizon=6):
    history = panel[["warehouse_id", "item_id", "month", "qty"] + FEATURE_COLS].copy()
    last_month = history["month"].max()
    results = []

    for step in range(1, horizon + 1):
        target_month = last_month + pd.DateOffset(months=step)
        latest = _next_month_features(history, target_month)

        latest["qty"] = model.predict(latest[FEATURE_COLS].fillna(0)).clip(min=0)

        results.append(latest[["warehouse_id", "item_id", "month", "qty"]])
        history = pd.concat([history, latest], ignore_index=True)

    return pd.concat(results, ignore_index=True).rename(columns={"qty": "xgboost_forecast"})


if __name__ == "__main__":
    panel = build_panel()
    model = train(panel)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACT_DIR / "xgboost_model.pkl", "wb") as f:
        pickle.dump(model, f)

    fc = forecast(model, panel)
    fc.to_csv(ARTIFACT_DIR / "xgboost_forecast.csv", index=False)
    print(f"\nforecast: {len(fc)} rows -> {ARTIFACT_DIR / 'xgboost_forecast.csv'}")
    print(fc.head(10))