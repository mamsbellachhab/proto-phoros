from pathlib import Path

import pandas as pd

from features import build_panel
from train_ets import forecast as ets_forecast
from train_xgboost import forecast as xgboost_forecast, train as train_xgboost

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

# starting weights -- xgboost carries more weight since it beat the naive
# baseline clearly in holdout, ets mainly contributes on items with a
# strong, stable seasonal pattern. Revisit once real usage data comes in.
XGBOOST_WEIGHT = 0.6
ETS_WEIGHT = 0.4


def build_forecast(horizon=6):
    panel = build_panel()

    model = train_xgboost(panel)
    xgb_fc = xgboost_forecast(model, panel, horizon)
    ets_fc = ets_forecast(panel, horizon)

    merged = xgb_fc.merge(ets_fc, on=["warehouse_id", "item_id", "month"], how="outer")
    merged["xgboost_forecast"] = merged["xgboost_forecast"].fillna(0)
    merged["ets_forecast"] = merged["ets_forecast"].fillna(0)

    merged["ensemble_forecast"] = (
        XGBOOST_WEIGHT * merged["xgboost_forecast"] + ETS_WEIGHT * merged["ets_forecast"]
    )

    return merged.sort_values(["warehouse_id", "item_id", "month"])


if __name__ == "__main__":
    result = build_forecast()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACT_DIR / "demand_forecast.csv"
    result.to_csv(out_path, index=False)

    print(f"final forecast: {len(result)} rows -> {out_path}")
    print(result.head(10))