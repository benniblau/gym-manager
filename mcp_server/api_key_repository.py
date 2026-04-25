"""API key repository for MCP server authentication.

Self-contained — no BaseRepository dependency. Accepts a raw sqlite3.Connection
so it works both in Flask request context (pass get_db()) and in the standalone
MCP server process (pass open_db()).
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone


class ApiKeyRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            (raw_key, key_hash, key_prefix)
            raw_key    = "gm_" + 32 hex chars (35 chars total)
            key_hash   = sha256(raw_key) hex digest
            key_prefix = first 11 chars of raw_key ("gm_" + 8 chars)
        """
        raw_key = "gm_" + secrets.token_hex(16)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:11]
        return raw_key, key_hash, key_prefix

    def create_key(self, user_id: int, scope: str = "read", label: str | None = None) -> dict:
        """Create and persist a new API key.

        Returns:
            Dict with {id, raw_key, key_prefix, scope, label, created_at}.
            raw_key is only returned here — never stored.
        """
        if scope not in ("read", "readwrite"):
            raise ValueError(f"Invalid scope: {scope}")

        raw_key, key_hash, key_prefix = self.generate_key()
        now = datetime.now(timezone.utc).isoformat()

        cursor = self._db.execute(
            """INSERT INTO api_keys (key_hash, key_prefix, user_id, scope, label, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_hash, key_prefix, user_id, scope, label, now),
        )
        self._db.commit()

        return {
            "id": cursor.lastrowid,
            "raw_key": raw_key,
            "key_prefix": key_prefix,
            "scope": scope,
            "label": label,
            "created_at": now,
        }

    def validate_key(self, raw_key: str) -> dict | None:
        """Validate a raw API key and update last_used_at.

        Returns:
            Dict with {user_id, scope} if valid, None otherwise.
        """
        if not raw_key or not raw_key.startswith("gm_"):
            return None

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        row = self._db.execute(
            "SELECT id, user_id, scope FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        ).fetchone()

        if not row:
            return None

        self._db.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), row["id"]),
        )
        self._db.commit()

        return {"user_id": row["user_id"], "scope": row["scope"]}

    def get_keys_for_user(self, user_id: int) -> list[dict]:
        """Return API keys for a user (without hashes)."""
        rows = self._db.execute(
            """SELECT id, key_prefix, scope, label, last_used_at, created_at
               FROM api_keys
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_key(self, key_id: int, user_id: int) -> bool:
        """Delete a key if it belongs to the given user.

        Returns:
            True if deleted, False if not found or not owned by user.
        """
        cursor = self._db.execute(
            "DELETE FROM api_keys WHERE id = ? AND user_id = ?",
            (key_id, user_id),
        )
        self._db.commit()
        return cursor.rowcount > 0
