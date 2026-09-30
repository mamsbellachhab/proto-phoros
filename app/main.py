from fastapi import Depends, FastAPI

import needs
from auth import current_user, visible_warehouse_ids
from db import get_connection

app = FastAPI(title="proto-phoros")
app.include_router(needs.router)


@app.get("/me")
def me(user=Depends(current_user)):
    return user


@app.get("/inventory/stock")
def stock(warehouse_ids=Depends(visible_warehouse_ids)):
    conn = get_connection()
    placeholders = ",".join("?" * len(warehouse_ids))
    rows = conn.execute(
        f"""
        SELECT s.warehouse_id, w.name AS warehouse_name, s.item_id, i.name AS item_name,
               i.category, s.on_hand_qty, a.minimum_qty, a.authorized_qty
        FROM stock_on_hand s
        JOIN warehouse w ON w.id = s.warehouse_id
        JOIN item i ON i.id = s.item_id
        LEFT JOIN allowance a ON a.warehouse_id = s.warehouse_id AND a.item_id = s.item_id
        WHERE s.warehouse_id IN ({placeholders})
        ORDER BY w.name, i.name
        """,
        warehouse_ids,
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/inventory/vehicles")
def vehicles(warehouse_ids=Depends(visible_warehouse_ids)):
    conn = get_connection()
    placeholders = ",".join("?" * len(warehouse_ids))
    rows = conn.execute(
        f"""
        SELECT v.id, v.serial_number, v.model, v.category, v.status,
               v.mileage_km, v.in_service_date, u.name AS unit_name
        FROM vehicle v
        JOIN unit u ON u.id = v.unit_id
        JOIN warehouse w ON w.unit_id = u.id
        WHERE w.id IN ({placeholders})
        ORDER BY u.name, v.serial_number
        """,
        warehouse_ids,
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/inventory/weapons")
def weapons(warehouse_ids=Depends(visible_warehouse_ids)):
    conn = get_connection()
    # a weapon's unit is a company; its warehouse lives one level up, at the
    # parent battalion -- there's no warehouse at company level
    placeholders = ",".join("?" * len(warehouse_ids))
    rows = conn.execute(
        f"""
        SELECT wp.id, wp.serial_number, wp.type, wp.caliber, wp.status, u.name AS unit_name
        FROM weapon wp
        JOIN unit u ON u.id = wp.unit_id
        JOIN warehouse w ON w.unit_id = u.parent_unit_id
        WHERE w.id IN ({placeholders})
        ORDER BY u.name, wp.serial_number
        """,
        warehouse_ids,
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]