"""Migration: add api_keys table for MCP server authentication."""

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "exercises.db"


def run(dry_run: bool = False) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'"
    )
    if cursor.fetchone():
        print("Table 'api_keys' already exists — nothing to do.")
        conn.close()
        return

    sql = """
    CREATE TABLE api_keys (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash     TEXT UNIQUE NOT NULL,
        key_prefix   TEXT NOT NULL,
        user_id      INTEGER NOT NULL REFERENCES users(id),
        scope        TEXT NOT NULL DEFAULT 'read',
        label        TEXT,
        last_used_at TEXT,
        created_at   TEXT NOT NULL
    )
    """

    if dry_run:
        print("[dry-run] Would execute:")
        print(sql.strip())
    else:
        conn.execute(sql)
        conn.commit()
        print("Created table 'api_keys'.")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add api_keys table")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
