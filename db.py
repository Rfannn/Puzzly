"""Lightweight SQLite usage logging for Puzzly (stdlib only)."""

import os
import json
import sqlite3
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "puzzly.db")

_conn = None


def get_db():
    global _conn
    if _conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(_SCHEMA)
    return _conn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    picture TEXT,
    options TEXT,
    ip TEXT,
    user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""


def log_event(kind, picture=None, options=None, ip=None, user_agent=None):
    """Record a usage event. Never raises to the caller."""
    try:
        ts = datetime.now(timezone.utc).isoformat()
        opts = json.dumps(options) if options is not None else None
        conn = get_db()
        with conn:
            conn.execute(
                "INSERT INTO events (ts, kind, picture, options, ip, user_agent)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (ts, kind, picture, opts, ip, user_agent),
            )
    except Exception:
        pass


def total_by_kind():
    conn = get_db()
    rows = conn.execute(
        "SELECT kind, COUNT(*) AS n FROM events GROUP BY kind"
    ).fetchall()
    return {r["kind"]: r["n"] for r in rows}


def top_pictures(limit=10):
    conn = get_db()
    rows = conn.execute(
        "SELECT picture, COUNT(*) AS n FROM events"
        " WHERE kind = 'generate' AND picture IS NOT NULL"
        " GROUP BY picture ORDER BY n DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"picture": r["picture"], "count": r["n"]} for r in rows]


def recent_events(limit=100):
    conn = get_db()
    rows = conn.execute(
        "SELECT ts, kind, picture, options, ip, user_agent FROM events"
        " ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def generations_by_day(days=30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_db()
    rows = conn.execute(
        "SELECT substr(ts, 1, 10) AS day, COUNT(*) AS n FROM events"
        " WHERE kind = 'generate' AND ts >= ?"
        " GROUP BY day ORDER BY day",
        (since,),
    ).fetchall()
    return [{"day": r["day"], "count": r["n"]} for r in rows]


def count_generations_since(days=30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE kind = 'generate' AND ts >= ?",
        (since,),
    ).fetchone()
    return row["n"] if row else 0
