"""
db.py — PostgreSQL connection pool for the ML service.

Architecture note (mirrors backend/src/config/db.js):
    A single connection pool is created once at import time and reused across
    requests. Credentials come exclusively from environment variables. This is
    the SAME PostgreSQL database the Express backend uses — the ML service
    reads existing SCARLET data (products, markets, demand) rather than
    maintaining a second source of truth.
"""
import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool

from app import config

logger = logging.getLogger("scarlet.ml.db")

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = pg_pool.SimpleConnectionPool(
            1, 10,
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
        )
        logger.info("PostgreSQL connection pool created (%s:%s/%s)",
                    config.DB_HOST, config.DB_PORT, config.DB_NAME)
    return _pool


@contextmanager
def get_conn():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def check_connection() -> bool:
    """Lightweight reachability check, mirroring Express's `SELECT 1` health check."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception as exc:  # noqa: BLE001 — health check must never raise
        logger.error("Database check failed: %s", exc)
        return False


def fetch_all(query: str, params: tuple = ()):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if cur.description is None:  # INSERT/UPDATE with no RETURNING
                conn.commit()
                return []
            rows = cur.fetchall()
        conn.commit()  # commits any INSERT/UPDATE ... RETURNING too
        return rows


def fetch_one(query: str, params: tuple = ()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def execute(query: str, params: tuple = ()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
