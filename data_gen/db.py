import sqlite3
from pathlib import Path


def fresh_connection(db_path, schema_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(Path(schema_path).read_text())
    return conn


def insert_many(conn, table, columns, rows):
    if not rows:
        return
    placeholders = ", ".join("?" for _ in columns)
    col_list = ", ".join(columns)
    conn.executemany(
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})", rows
    )


def last_id(conn):
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
