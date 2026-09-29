import random
from datetime import timedelta

import config

BASE_ALLOWANCE = {
    "CO-AMM-01": (8000, 2000),
    "CO-AMM-02": (4000, 1000),
    "CO-AMM-03": (1500, 400),
    "CO-AMM-04": (800, 200),
    "CO-AMM-05": (200, 50),
    "CO-FUE-01": (5000, 1500),
    "CO-FUE-02": (1500, 400),
    "CO-LUB-01": (300, 80),
    "CO-LUB-02": (300, 80),
    "CO-MED-01": (100, 25),
    "CO-MED-02": (100, 25),
    "CO-RAT-01": (2000, 500),
}
DEFAULT_SPARE_PART = (20, 5)
DEFAULT_SERIAL_EQUIPMENT = (30, 8)
CENTRAL_MULTIPLIER = 6

REJECT_NOTES = [
    "Denied pending budget review this cycle",
    "Quantity not justified by current usage",
    "Covered by incoming transfer, no purchase needed",
]
EDIT_NOTES = [
    "Rounded to standard order batch size",
    "Reduced pending confirmation of usage rate",
    "Increased to cover known upcoming exercise",
]


def _base_allowance(item):
    if item["code"] in BASE_ALLOWANCE:
        return BASE_ALLOWANCE[item["code"]]
    if item["type"] == "spare_part":
        return DEFAULT_SPARE_PART
    return DEFAULT_SERIAL_EQUIPMENT


def _add_months(d, n):
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    days_in_month = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(d.day, days_in_month[month - 1])
    return d.replace(year=year, month=month, day=day)


def _insert_allowance(conn, warehouse_id, item_id, authorized, minimum):
    conn.execute(
        "INSERT INTO allowance (warehouse_id, item_id, authorized_qty, minimum_qty) "
        "VALUES (?, ?, ?, ?)",
        (warehouse_id, item_id, authorized, minimum),
    )


def _insert_movement(conn, date, warehouse_id, item_id, mtype, quantity,
                      dest_warehouse_id=None, repair_id=None, lot_id=None, exercise_id=None):
    conn.execute(
        "INSERT INTO movement (date, warehouse_id, item_id, type, quantity, "
        "dest_warehouse_id, repair_id, lot_id, exercise_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (date.isoformat(), warehouse_id, item_id, mtype, quantity,
         dest_warehouse_id, repair_id, lot_id, exercise_id),
    )


def _insert_purchase_order(conn, warehouse_id, item_id, quantity, order_date, expected_date, received_date):
    cur = conn.execute(
        "INSERT INTO purchase_order (warehouse_id, item_id, quantity, order_date, "
        "expected_date, received_date) VALUES (?, ?, ?, ?, ?, ?)",
        (warehouse_id, item_id, quantity, order_date.isoformat(), expected_date.isoformat(),
         received_date.isoformat() if received_date else None),
    )
    return cur.lastrowid


def _mark_po_received(conn, po_id, received_date):
    conn.execute(
        "UPDATE purchase_order SET received_date = ? WHERE id = ?",
        (received_date.isoformat(), po_id),
    )


def _insert_requirement_line(conn, warehouse_id, item_id, created_date, gap_qty, reason,
                              status, reviewed_by, reviewed_date, final_qty, notes, order_id):
    conn.execute(
        "INSERT INTO requirement_line (warehouse_id, item_id, created_date, "
        "computed_gap_qty, reason, status, reviewed_by, reviewed_date, final_qty, "
        "notes, order_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (warehouse_id, item_id, created_date.isoformat(), gap_qty, reason, status,
         reviewed_by, reviewed_date.isoformat() if reviewed_date else None,
         final_qty, notes, order_id),
    )


def _insert_ammo_lot(conn, item_id, lot_number, manufacture_date, expiry_date):
    cur = conn.execute(
        "INSERT INTO ammo_lot (item_id, lot_number, manufacture_date, expiry_date) "
        "VALUES (?, ?, ?, ?)",
        (item_id, lot_number, manufacture_date.isoformat(), expiry_date.isoformat()),
    )
    return cur.lastrowid


def generate(conn, org, catalog, repairs, range_sessions, exercises):
    items = catalog["items"]
    items_by_id = {i["id"]: i for i in items}

    central_id = org["central_warehouse_id"]
    warehouses = [{"id": central_id, "mult": CENTRAL_MULTIPLIER, "battalion": None}]
    for bn in org["battalions"]:
        warehouses.append({"id": bn["warehouse_id"], "mult": 1, "battalion": bn})

    users_by_battalion = {u["unit_id"]: u["id"] for u in org["users"] if u["role"] == "unit"}
    admin_id = org["admin_id"]

    exercises_by_battalion = {}
    for ex in exercises:
        exercises_by_battalion.setdefault(ex["battalion_id"], []).append(ex)

    # ---- allowance ----
    allowance_map = {}
    for wh in warehouses:
        for item in items:
            base_auth, base_min = _base_allowance(item)
            jitter = random.uniform(0.85, 1.15)
            authorized = max(1, round(base_auth * wh["mult"] * jitter))
            minimum = max(1, round(base_min * wh["mult"] * jitter))
            _insert_allowance(conn, wh["id"], item["id"], authorized, minimum)
            allowance_map[(wh["id"], item["id"])] = (authorized, minimum)

    # ---- legacy ammo lots (pre-existing stock at dataset start) ----
    lots_by_item = {}
    for caliber, item in catalog["ammo_by_caliber"].items():
        manufacture_date = config.START_DATE - timedelta(days=random.randint(60, 400))
        expiry_date = manufacture_date + timedelta(days=1825)
        lot_id = _insert_ammo_lot(conn, item["id"], f"{item['code']}-LEGACY", manufacture_date, expiry_date)
        lots_by_item[item["id"]] = [{"id": lot_id, "manufacture_date": manufacture_date, "expiry_date": expiry_date}]

    def new_lot(item_id, near_date):
        item = items_by_id[item_id]
        manufacture_date = near_date - timedelta(days=random.randint(5, 30))
        expiry_date = manufacture_date + timedelta(days=1825)
        seq = len(lots_by_item.get(item_id, [])) + 1
        lot_number = f"{item['code']}-{manufacture_date.strftime('%y%m')}-{seq:03d}"
        lot_id = _insert_ammo_lot(conn, item_id, lot_number, manufacture_date, expiry_date)
        lot = {"id": lot_id, "manufacture_date": manufacture_date, "expiry_date": expiry_date}
        lots_by_item.setdefault(item_id, []).append(lot)
        return lot_id

    def pick_lot(item_id, event_date):
        lots = lots_by_item.get(item_id, [])
        for lot in lots:
            if lot["expiry_date"] > event_date:
                return lot["id"]
        return lots[-1]["id"] if lots else None

    # ---- opening stock ----
    on_hand = {}
    for wh in warehouses:
        for item in items:
            authorized, _ = allowance_map[(wh["id"], item["id"])]
            qty = round(authorized * random.uniform(0.7, 1.0))
            lot_id = pick_lot(item["id"], config.START_DATE) if item["category"] == "ammunition" else None
            _insert_movement(conn, config.START_DATE, wh["id"], item["id"], "receipt", qty, lot_id=lot_id)
            on_hand[(wh["id"], item["id"])] = qty

    # ---- demand events ----
    events = []
    for r in repairs:
        if r["item_id"] is not None:
            events.append({
                "date": r["date"], "warehouse_id": r["warehouse_id"], "item_id": r["item_id"],
                "quantity": r["quantity"], "type": "consumption",
                "repair_id": r["id"], "exercise_id": None, "lot": False,
            })

    for rs in range_sessions:
        item = catalog["ammo_by_caliber"][rs["caliber"]]
        events.append({
            "date": rs["date"], "warehouse_id": rs["warehouse_id"], "item_id": item["id"],
            "quantity": rs["rounds"], "type": "consumption",
            "repair_id": None, "exercise_id": rs["exercise_id"], "lot": True,
        })

    fuel_id = catalog["fuel_item"]["id"]
    ration_id = catalog["ration_item"]["id"]
    for ex in exercises:
        duration = (ex["end_date"] - ex["start_date"]).days + 1
        fuel_qty = duration * (random.randint(50, 150) if ex["type"] == "drill" else random.randint(200, 500))
        events.append({
            "date": ex["start_date"], "warehouse_id": ex["warehouse_id"], "item_id": fuel_id,
            "quantity": fuel_qty, "type": "issue", "repair_id": None, "exercise_id": ex["id"], "lot": False,
        })
        if ex["type"] == "field_exercise":
            ration_qty = duration * random.randint(50, 150)
            events.append({
                "date": ex["start_date"], "warehouse_id": ex["warehouse_id"], "item_id": ration_id,
                "quantity": ration_qty, "type": "issue", "repair_id": None, "exercise_id": ex["id"], "lot": False,
            })

    events.sort(key=lambda e: e["date"])

    def has_upcoming_exercise(battalion_id, from_date, horizon_days=30):
        for ex in exercises_by_battalion.get(battalion_id, []):
            if ex["type"] in ("live_fire", "field_exercise"):
                delta = (ex["start_date"] - from_date).days
                if 0 <= delta <= horizon_days:
                    return True
        return False

    def pick_reviewer(wh):
        if wh["battalion"] is None:
            return admin_id
        return users_by_battalion[wh["battalion"]["id"]]

    def review(wh, item, review_date, pending_receipts):
        key = (wh["id"], item["id"])
        authorized, minimum = allowance_map[key]
        current = on_hand[key]

        reason, gap = None, 0
        if current < minimum:
            reason, gap = "below_minimum", authorized - current
        elif item["category"] in ("ammunition", "fuel") and wh["battalion"] is not None:
            if has_upcoming_exercise(wh["battalion"]["id"], review_date) and random.random() < 0.5:
                reason, gap = "forecasted_demand", round(authorized * 0.2)
        if reason is None and random.random() < 0.02:
            reason, gap = "manual_request", round(authorized * random.uniform(0.05, 0.15))

        if reason is None or gap <= 0:
            return

        reviewer = pick_reviewer(wh)
        reviewed_date = review_date + timedelta(days=random.randint(1, 5))
        roll = random.random()

        if roll < 0.05:
            _insert_requirement_line(conn, wh["id"], item["id"], review_date, gap, reason,
                                      "rejected", reviewer, reviewed_date, None,
                                      random.choice(REJECT_NOTES), None)
            return

        if roll < 0.20:
            status = "edited"
            final_qty = max(1, round(gap * random.uniform(0.7, 1.3)))
            notes = random.choice(EDIT_NOTES)
        else:
            status = "approved"
            final_qty = gap
            notes = None

        order_date = reviewed_date
        expected_date = order_date + timedelta(days=item["lead_time_days"])
        po_id = _insert_purchase_order(conn, wh["id"], item["id"], final_qty, order_date, expected_date, None)

        if expected_date <= config.TODAY:
            receive_date = expected_date + timedelta(days=random.randint(-2, 5))
            receive_date = max(order_date, min(receive_date, config.TODAY))
            pending_receipts.append({
                "receive_date": receive_date, "warehouse_id": wh["id"], "item_id": item["id"],
                "quantity": final_qty, "is_ammo": item["category"] == "ammunition", "po_id": po_id,
            })

        _insert_requirement_line(conn, wh["id"], item["id"], review_date, gap, reason,
                                  status, reviewer, reviewed_date, final_qty, notes, po_id)

    def maybe_adjustment(wh, item, period_date):
        if random.random() >= 0.015:
            return
        authorized, _ = allowance_map[(wh["id"], item["id"])]
        magnitude = max(1, round(authorized * random.uniform(0.01, 0.05)))
        qty = magnitude * random.choice([1, -1])
        _insert_movement(conn, period_date, wh["id"], item["id"], "adjustment", qty)
        on_hand[(wh["id"], item["id"])] += qty

    def do_transfers(review_date):
        for wh in warehouses:
            if wh["battalion"] is None:
                continue
            for item in items:
                key = (wh["id"], item["id"])
                central_key = (central_id, item["id"])
                authorized, _ = allowance_map[key]
                current = on_hand[key]
                if current >= authorized * 0.6:
                    continue

                target = round(authorized * 0.8)
                needed = target - current
                central_authorized, central_minimum = allowance_map[central_key]
                headroom = max(on_hand[central_key] - central_minimum, 0)
                qty = int(min(needed, headroom))
                if qty > 0 and random.random() < 0.6:
                    _insert_movement(conn, review_date, central_id, item["id"], "transfer", qty,
                                      dest_warehouse_id=wh["id"])
                    on_hand[key] += qty
                    on_hand[central_key] -= qty

    # ---- monthly simulation ----
    periods = []
    cursor = config.START_DATE
    while cursor < config.TODAY:
        nxt = min(_add_months(cursor, 1), config.TODAY)
        periods.append((cursor, nxt))
        cursor = nxt

    event_idx = 0
    n_events = len(events)
    pending_receipts = []

    for period_index, (p_start, p_end) in enumerate(periods):
        while event_idx < n_events and events[event_idx]["date"] <= p_end:
            e = events[event_idx]
            event_idx += 1
            on_hand[(e["warehouse_id"], e["item_id"])] -= e["quantity"]
            lot_id = pick_lot(e["item_id"], e["date"]) if e["lot"] else None
            _insert_movement(conn, e["date"], e["warehouse_id"], e["item_id"], e["type"], e["quantity"],
                              repair_id=e["repair_id"], lot_id=lot_id, exercise_id=e["exercise_id"])

        still_pending = []
        for pr in pending_receipts:
            if pr["receive_date"] <= p_end:
                on_hand[(pr["warehouse_id"], pr["item_id"])] += pr["quantity"]
                lot_id = new_lot(pr["item_id"], pr["receive_date"]) if pr["is_ammo"] else None
                _insert_movement(conn, pr["receive_date"], pr["warehouse_id"], pr["item_id"], "receipt",
                                  pr["quantity"], lot_id=lot_id)
                _mark_po_received(conn, pr["po_id"], pr["receive_date"])
            else:
                still_pending.append(pr)
        pending_receipts = still_pending

        for wh in warehouses:
            for item in items:
                maybe_adjustment(wh, item, p_end)
                review(wh, item, p_end, pending_receipts)

        if period_index % 3 == 2:
            do_transfers(p_end)

    return {"on_hand": on_hand, "allowance_map": allowance_map}
