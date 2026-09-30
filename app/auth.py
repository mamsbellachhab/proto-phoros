from fastapi import Depends, Header, HTTPException

from db import get_connection


def _subtree_unit_ids(conn, root_unit_id):
    rows = conn.execute(
        """
        WITH RECURSIVE subtree(id) AS (
            SELECT id FROM unit WHERE id = ?
            UNION ALL
            SELECT u.id FROM unit u JOIN subtree s ON u.parent_unit_id = s.id
        )
        SELECT id FROM subtree
        """,
        (root_unit_id,),
    ).fetchall()
    return [row["id"] for row in rows]


def login(username):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, full_name, role, unit_id FROM app_user WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=401, detail="unknown username")

    return {
        "user_id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
        "unit_id": row["unit_id"],
    }


# prototype auth -- a known username is enough, no password or token yet.
# real login/session handling is a later pass once the API shape is settled.
def current_user(x_username: str = Header(...)):
    return login(x_username)


def visible_warehouse_ids(user=Depends(current_user)):
    conn = get_connection()

    if user["role"] == "admin":
        rows = conn.execute("SELECT id FROM warehouse").fetchall()
    else:
        unit_ids = _subtree_unit_ids(conn, user["unit_id"])
        placeholders = ",".join("?" * len(unit_ids))
        rows = conn.execute(
            f"SELECT id FROM warehouse WHERE unit_id IN ({placeholders})", unit_ids
        ).fetchall()

    conn.close()
    return [row["id"] for row in rows]