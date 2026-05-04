"""
Database Connection & Pool Manager.

Provides both sync (psycopg2) and async (asyncpg) PostgreSQL
connection pools for the MandiSense platform.

Design:
  • Connection pooling via pool objects (not per-query connections)
  • Environment-variable driven configuration
  • Graceful fallback: if DB unavailable, callers get None
  • Thread-safe sync pool for background tasks (Celery, CLI)
  • Async pool for FastAPI request handlers
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

def _get_db_url() -> str:
    """Build DATABASE_URL from environment or use default."""
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://mandisense:mandisense@localhost:5432/mandisense_db"
    )
    # Render/Heroku use postgres:// but asyncpg/psycopg2 might prefer postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _parse_db_url(url: str) -> Dict[str, Any]:
    """Parse a postgresql:// URL into connection kwargs."""
    # postgresql://user:pass@host:port/dbname
    url = url.replace("postgresql://", "")
    userpass, hostdb = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, dbname = hostdb.split("/", 1)

    if ":" in hostport:
        host, port = hostport.split(":", 1)
        port = int(port)
    else:
        host = hostport
        port = 5432

    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "database": dbname,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Sync Connection Pool (psycopg2) — for background tasks, CLI, migrations
# ═══════════════════════════════════════════════════════════════════════════════

_sync_pool = None


def get_sync_pool():
    """Get or create the sync connection pool."""
    global _sync_pool
    if _sync_pool is not None:
        return _sync_pool

    try:
        import psycopg2
        from psycopg2 import pool as pg_pool

        dsn = _get_db_url()
        _sync_pool = pg_pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=dsn,
        )
        logger.info(f"[DB] Sync pool created via DSN")
        return _sync_pool
    except Exception as e:
        logger.warning(f"[DB] Sync pool creation failed: {e}")
        return None


@contextmanager
def get_sync_connection():
    """Context manager for a sync DB connection from the pool."""
    pool = get_sync_pool()
    if pool is None:
        yield None
        return

    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def execute_sync(query: str, params: tuple = None) -> Optional[List[Tuple]]:
    """Execute a query synchronously. Returns rows for SELECT, None for others."""
    with get_sync_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return None


def execute_many_sync(query: str, params_list: List[tuple]) -> int:
    """Execute a query with many parameter sets. Returns affected row count."""
    with get_sync_connection() as conn:
        if conn is None:
            return 0
        with conn.cursor() as cur:
            cur.executemany(query, params_list)
            return cur.rowcount


def ping_db_sync() -> bool:
    """Check if the database is reachable synchronously."""
    try:
        rows = execute_sync("SELECT 1")
        return rows is not None and len(rows) > 0
    except Exception:
        return False



# ═══════════════════════════════════════════════════════════════════════════════
# Async Connection Pool (asyncpg) — for FastAPI request handlers
# ═══════════════════════════════════════════════════════════════════════════════

_async_pool = None


async def get_async_pool():
    """Get or create the async connection pool."""
    global _async_pool
    if _async_pool is not None:
        return _async_pool

    try:
        import asyncpg
        _async_pool = await asyncpg.create_pool(
            dsn=_get_db_url(),
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("[DB] Async pool created")
        return _async_pool
    except Exception as e:
        logger.warning(f"[DB] Async pool creation failed: {e}")
        return None


async def close_async_pool():
    """Close the async pool (call on shutdown)."""
    global _async_pool
    if _async_pool:
        await _async_pool.close()
        _async_pool = None


async def execute_async(query: str, *args) -> Optional[List]:
    """Execute a query asynchronously. Returns rows for SELECT."""
    pool = await get_async_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def execute_one_async(query: str, *args):
    """Execute and return a single row."""
    pool = await get_async_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute_write_async(query: str, *args) -> Optional[str]:
    """Execute a write query (INSERT/UPDATE). Returns status string."""
    pool = await get_async_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def ping_db_async() -> bool:
    """Check if the database is reachable asynchronously."""
    try:
        res = await execute_one_async("SELECT 1")
        return res is not None
    except Exception:
        return False

