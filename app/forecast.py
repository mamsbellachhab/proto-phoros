import csv
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import current_user, visible_warehouse_ids

router = APIRouter(tags=["forecast"])

DEMAND_CSV = Path(__file__).resolve().parent.parent / "models" / "demand" / "artifacts" / "demand_forecast.csv"
ANOMALIES_CSV = Path(__file__).resolve().parent.parent / "models" / "anomalies" / "artifacts" / "flagged_anomalies.csv"


def _read_csv(path):
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"{path.name} not generated yet -- run the model script first")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


@router.get("/forecast/demand")
def demand_forecast(item_id: int | None = Query(None), warehouse_ids=Depends(visible_warehouse_ids)):
    rows = _read_csv(DEMAND_CSV)
    scoped = [row for row in rows if int(row["warehouse_id"]) in warehouse_ids]
    if item_id is not None:
        scoped = [row for row in scoped if int(row["item_id"]) == item_id]
    return scoped


@router.get("/anomalies")
def anomalies(user=Depends(current_user)):
    # anomaly review sits above the unit level -- it's an oversight
    # function, not something a battalion audits on itself
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return _read_csv(ANOMALIES_CSV)