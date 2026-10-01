import os

import requests

BASE_URL = os.environ.get("PROTO_PHOROS_API", "http://127.0.0.1:8000")
TIMEOUT = 15


def _request(method, path, username, **kwargs):
    headers = {"x-username": username}
    try:
        resp = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        return {"error": f"could not reach backend: {exc}"}

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        return {"error": f"{resp.status_code}: {detail}"}

    if not resp.content:
        return {}
    return resp.json()


def _filter_rows(rows, **filters):
    if isinstance(rows, dict) and "error" in rows:
        return rows
    out = rows
    for key, needle in filters.items():
        if needle is None:
            continue
        needle = needle.lower()
        out = [row for row in out if needle in str(row.get(key, "")).lower()]
    return out


def get_stock(username, item_name=None, warehouse_name=None):
    rows = _request("GET", "/inventory/stock", username)
    return _filter_rows(rows, item_name=item_name, warehouse_name=warehouse_name)


def get_vehicles(username, status=None, unit_name=None):
    rows = _request("GET", "/inventory/vehicles", username)
    return _filter_rows(rows, status=status, unit_name=unit_name)


def get_weapons(username, status=None, unit_name=None):
    rows = _request("GET", "/inventory/weapons", username)
    return _filter_rows(rows, status=status, unit_name=unit_name)


def list_pending_needs(username):
    return _request("GET", "/needs", username)


def create_need(username, warehouse_id, item_id, computed_gap_qty, notes=None):
    body = {
        "warehouse_id": warehouse_id,
        "item_id": item_id,
        "computed_gap_qty": computed_gap_qty,
        "notes": notes,
    }
    return _request("POST", "/needs", username, json=body)


def approve_need(username, line_id, final_qty=None):
    body = {"final_qty": final_qty}
    return _request("POST", f"/needs/{line_id}/approve", username, json=body)


def edit_need(username, line_id, final_qty, notes=None):
    body = {"final_qty": final_qty, "notes": notes}
    return _request("POST", f"/needs/{line_id}/edit", username, json=body)


def reject_need(username, line_id, notes=None):
    body = {"notes": notes}
    return _request("POST", f"/needs/{line_id}/reject", username, json=body)


def get_demand_forecast(username, item_id=None):
    params = {}
    if item_id is not None:
        params["item_id"] = item_id
    return _request("GET", "/forecast/demand", username, params=params)


def get_anomalies(username):
    return _request("GET", "/anomalies", username)


TOOL_FUNCTIONS = {
    "get_stock": get_stock,
    "get_vehicles": get_vehicles,
    "get_weapons": get_weapons,
    "list_pending_needs": list_pending_needs,
    "create_need": create_need,
    "approve_need": approve_need,
    "edit_need": edit_need,
    "reject_need": reject_need,
    "get_demand_forecast": get_demand_forecast,
    "get_anomalies": get_anomalies,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock",
            "description": "Get current on-hand stock, minimum and authorized levels for supply items, scoped to the units the acting user can see. Optionally filter by item name or warehouse name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string"},
                    "warehouse_name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicles",
            "description": "Get vehicles in the acting user's scope, with serial number, model, status and mileage. Optionally filter by status or unit name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "unit_name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weapons",
            "description": "Get weapons in the acting user's scope, with serial number, type, caliber and status. Optionally filter by status or unit name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "unit_name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pending_needs",
            "description": "List requirement lines awaiting review in the acting user's scope.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_need",
            "description": "Raise a new requirement line (supply request) for a warehouse in the acting user's scope.",
            "parameters": {
                "type": "object",
                "properties": {
                    "warehouse_id": {"type": "integer"},
                    "item_id": {"type": "integer"},
                    "computed_gap_qty": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["warehouse_id", "item_id", "computed_gap_qty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_need",
            "description": "Approve a pending requirement line, opening a purchase order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "line_id": {"type": "integer"},
                    "final_qty": {"type": "integer"},
                },
                "required": ["line_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_need",
            "description": "Approve a pending requirement line with a changed quantity, opening a purchase order for the new quantity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "line_id": {"type": "integer"},
                    "final_qty": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["line_id", "final_qty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reject_need",
            "description": "Reject a pending requirement line. No purchase order is created.",
            "parameters": {
                "type": "object",
                "properties": {
                    "line_id": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["line_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_demand_forecast",
            "description": "Get the ensemble demand forecast for items in the acting user's scope.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomalies",
            "description": "Get flagged anomalies from the anomaly detection model. Admin role only.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def call_tool(name, arguments, username):
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return {"error": f"unknown tool '{name}'"}
    try:
        return func(username, **arguments)
    except TypeError as exc:
        return {"error": f"bad arguments for '{name}': {exc}"}