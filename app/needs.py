from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import current_user, visible_warehouse_ids
from db import get_connection

router = APIRouter(prefix="/needs", tags=["needs"])


class CreateRequest(BaseModel):
    warehouse_id: int
    item_id: int
    computed_gap_qty: int
    notes: str | None = None


class ApproveRequest(BaseModel):
    final_qty: int | None = None


class EditRequest(BaseModel):
    final_qty: int
    notes: str | None = None


class RejectRequest(BaseModel):
    notes: str | None = None


def _get_line(conn, line_id):
    row = conn.execute(
        "SELECT * FROM requirement_line WHERE id = ?", (line_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="requirement line not found")
    return row


def _check_scope(line, warehouse_ids):
    if line["warehouse_id"] not in warehouse_ids:
        raise HTTPException(status_code=403, detail="outside your unit's scope")


def _check_pending(line):
    if line["status"] != "proposed":
        raise HTTPException(status_code=409, detail=f"already {line['status']}")


@router.get("")
def list_pending(warehouse_ids=Depends(visible_warehouse_ids)):
    conn = get_connection()
    placeholders = ",".join("?" * len(warehouse_ids))
    rows = conn.execute(
        f"""
        SELECT rl.id, rl.warehouse_id, w.name AS warehouse_name, rl.item_id,
               i.name AS item_name, rl.created_date, rl.computed_gap_qty, rl.reason
        FROM requirement_line rl
        JOIN warehouse w ON w.id = rl.warehouse_id
        JOIN item i ON i.id = rl.item_id
        WHERE rl.status = 'proposed' AND rl.warehouse_id IN ({placeholders})
        ORDER BY rl.created_date
        """,
        warehouse_ids,
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.post("")
def create(body: CreateRequest, warehouse_ids=Depends(visible_warehouse_ids)):
    if body.warehouse_id not in warehouse_ids:
        raise HTTPException(status_code=403, detail="outside your unit's scope")

    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO requirement_line
            (warehouse_id, item_id, created_date, computed_gap_qty, reason, status, notes)
        VALUES (?, ?, ?, ?, 'manual_request', 'proposed', ?)
        """,
        (body.warehouse_id, body.item_id, date.today().isoformat(), body.computed_gap_qty, body.notes),
    )
    conn.commit()
    line_id = cur.lastrowid
    conn.close()
    return {"id": line_id, "status": "proposed"}


def _resolve(line_id, status, final_qty, notes, user, warehouse_ids, create_order):
    conn = get_connection()
    line = _get_line(conn, line_id)
    _check_scope(line, warehouse_ids)
    _check_pending(line)

    order_id = None
    if create_order:
        item = conn.execute("SELECT lead_time_days FROM item WHERE id = ?", (line["item_id"],)).fetchone()
        order_date = date.today()
        expected_date = order_date + timedelta(days=item["lead_time_days"])
        cur = conn.execute(
            """
            INSERT INTO purchase_order (warehouse_id, item_id, quantity, order_date, expected_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (line["warehouse_id"], line["item_id"], final_qty, order_date.isoformat(), expected_date.isoformat()),
        )
        order_id = cur.lastrowid

    conn.execute(
        """
        UPDATE requirement_line
        SET status = ?, reviewed_by = ?, reviewed_date = ?, final_qty = ?, notes = ?, order_id = ?
        WHERE id = ?
        """,
        (status, user["user_id"], date.today().isoformat(), final_qty, notes, order_id, line_id),
    )
    conn.commit()
    conn.close()
    return {"id": line_id, "status": status, "final_qty": final_qty, "order_id": order_id}


@router.post("/{line_id}/approve")
def approve(line_id: int, body: ApproveRequest, user=Depends(current_user), warehouse_ids=Depends(visible_warehouse_ids)):
    conn = get_connection()
    line = _get_line(conn, line_id)
    conn.close()
    final_qty = body.final_qty if body.final_qty is not None else line["computed_gap_qty"]
    return _resolve(line_id, "approved", final_qty, None, user, warehouse_ids, create_order=True)


@router.post("/{line_id}/edit")
def edit(line_id: int, body: EditRequest, user=Depends(current_user), warehouse_ids=Depends(visible_warehouse_ids)):
    return _resolve(line_id, "edited", body.final_qty, body.notes, user, warehouse_ids, create_order=True)


@router.post("/{line_id}/reject")
def reject(line_id: int, body: RejectRequest, user=Depends(current_user), warehouse_ids=Depends(visible_warehouse_ids)):
    return _resolve(line_id, "rejected", None, body.notes, user, warehouse_ids, create_order=False)