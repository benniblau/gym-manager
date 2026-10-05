"""Connection setup shared by the web app and the MCP server."""

import sqlite3
from datetime import datetime


def connect(path, check_same_thread=True):
    """Open a connection with row access by name and foreign keys enforced."""
    conn = sqlite3.connect(path, timeout=10, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def now():
    """Timestamp format used for every stored datetime: naive local time.

    Workout start/end times are entered through datetime-local inputs and
    sent to Strava as local time, so everything is kept in the same frame.
    """
    return datetime.now().isoformat(timespec="seconds")


def parse_dt(value):
    """Parse a stored timestamp to a naive local datetime (None if empty/invalid).

    Older rows may hold timezone-aware UTC strings; those are converted so
    arithmetic between any two stored timestamps is always valid.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed
