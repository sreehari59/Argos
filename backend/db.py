"""Database connection helper for db_new.sqlite"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db_new.sqlite"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a read query and return results as list of dicts."""
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    """Execute a write query and return lastrowid."""
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def executemany(sql: str, params_list: list[tuple]) -> None:
    """Execute a write query for many rows."""
    conn = get_connection()
    try:
        conn.executemany(sql, params_list)
        conn.commit()
    finally:
        conn.close()


def execute_script(sql: str) -> None:
    """Execute a multi-statement SQL script."""
    conn = get_connection()
    try:
        conn.executescript(sql)
    finally:
        conn.close()
