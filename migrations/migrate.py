"""Apply pending schema migrations (see gymcore/migrations.py).

Usage:
    python migrations/migrate.py [--dry-run] [--db PATH]

Additive and idempotent: already-applied versions are skipped. With --dry-run
every step runs and is then rolled back.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gymcore.db import connect
from gymcore.migrations import current_version, migrate


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="run, then roll back")
    parser.add_argument("--db", default=os.environ.get("DATABASE_PATH", str(ROOT / "exercises.db")))
    args = parser.parse_args()

    if not Path(args.db).exists():
        sys.exit(f"Database not found: {args.db}")

    conn = connect(args.db)
    conn.isolation_level = None
    print(f"{args.db}: schema version {current_version(conn)}")
    applied = migrate(conn, dry_run=args.dry_run)
    if not applied:
        print("Nothing to do.")
    elif args.dry_run:
        print(f"Dry run: would apply {applied}; rolled back.")
    else:
        print(f"Applied {applied}; now at version {current_version(conn)}.")


if __name__ == "__main__":
    main()
