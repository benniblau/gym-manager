"""API key authentication and per-request auth context."""

import sqlite3
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from mcp_server.api_key_repository import ApiKeyRepository


@dataclass
class AuthContext:
    user_id: int
    scope: str

    def can_write(self) -> bool:
        return self.scope == "readwrite"


_current_auth: ContextVar[Optional[AuthContext]] = ContextVar("current_auth", default=None)


def get_current_auth() -> AuthContext:
    """Return the AuthContext for the current request/task.

    Raises:
        PermissionError: If no auth context has been set.
    """
    auth = _current_auth.get()
    if auth is None:
        raise PermissionError("Unauthenticated — missing or invalid API key")
    return auth


def set_current_auth(auth: AuthContext) -> None:
    """Set the AuthContext for the current async task."""
    _current_auth.set(auth)


def resolve_auth(conn: sqlite3.Connection, raw_key: str) -> AuthContext:
    """Validate the raw API key and return an AuthContext.

    Raises:
        PermissionError: If the key is missing, invalid, or the user doesn't exist.
    """
    if not raw_key or not raw_key.startswith("gm_"):
        raise PermissionError("API key is missing or malformed (must start with 'gm_')")

    repo = ApiKeyRepository(db=conn)
    result = repo.validate_key(raw_key)

    if result is None:
        raise PermissionError("Invalid API key")

    row = conn.execute(
        "SELECT id FROM users WHERE id = ?", (result["user_id"],)
    ).fetchone()
    if not row:
        raise PermissionError("User not found")

    return AuthContext(user_id=result["user_id"], scope=result["scope"])
