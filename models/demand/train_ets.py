import warnings
from pathlib import Path

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from features import build_panel

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MIN_HISTORY_MONTHS = 24
SEASONAL_PERIODS = 12

warnings.filterwarnings("ignore")


def _fit_series(series, horizon):
    if len(series) >= MIN_HISTORY_MONTHS and series.sum() > 0:
        try:
            model = ExponentialSmoothing(
                series,
                trend="add",
                seasonal="add",
                seasonal_periods=SEASONAL_PERIODS,
                initialization_method="estimated",
            ).fit()
            return model.forecast(horizon).clip(lower=0)
        except Exception:
            pass

    # too little history, or the fit failed outright (flat/sparse series) -- fall back
    # to the trailing average rather than skip the combo
    level = series.tail(6).mean() if len(series) else 0.0
    return pd.Series([max(level, 0.0)] * horizon)


def forecast(panel, horizon=6):
    last_month = panel["month"].max()
    future_months = pd.date_range(last_month + pd.DateOffset(months=1), periods=horizon, freq="MS")

    rows = []
    for (warehouse_id, item_id), group in panel.sort_values("month").groupby(["warehouse_id", "item_id"]):
        series = group.set_index("month")["qty"]
        preds = _fit_series(series, horizon)

        for month, value in zip(future_months, preds):
            rows.append({
                "warehouse_id": warehouse_id,
                "item_id": item_id,
                "month": month,
                "ets_forecast": float(value),
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    panel = build_panel()
    fc = forecast(panel)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    fc.to_csv(ARTIFACT_DIR / "ets_forecast.csv", index=False)
    print(f"forecast: {len(fc)} rows -> {ARTIFACT_DIR / 'ets_forecast.csv'}")
    print(fc.head(10))