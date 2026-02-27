#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

def main() -> int:
    if str(os.getenv("ALLOW_LEGACY_DDL_INIT", "0")).strip() != "1":
        print("[blocked] Legacy SQL init is disabled by default.")
        print("Use Alembic instead: alembic upgrade head")
        print("If you must run this script, set ALLOW_LEGACY_DDL_INIT=1 explicitly.")
        return 2

    try:
        from sqlalchemy import create_engine, text
    except Exception:
        print("[ERROR] sqlalchemy is required. Install with: /Users/huda/Code/.venv/bin/python -m pip install sqlalchemy")
        return 2

    db_url = str(os.getenv("DATABASE_URL") or "")
    if not db_url.startswith("postgresql"):
        print("[ERROR] DATABASE_URL must be postgresql://...")
        return 2

    root = Path(__file__).resolve().parent.parent
    sql_files = [
        root / "database" / "postgres" / "sql" / "001_enable_extensions.sql",
        root / "database" / "postgres" / "sql" / "002_init_tables.sql",
        root / "database" / "postgres" / "sql" / "003_init_indexes.sql",
    ]

    engine = create_engine(db_url)
    with engine.begin() as conn:
        for path in sql_files:
            if not path.exists():
                print(f"[ERROR] sql file missing: {path}")
                return 2
            sql_text = path.read_text(encoding="utf-8")
            conn.execute(text(sql_text))
            print(f"[OK] applied: {path.name}")

    print("[DONE] governance pg schema initialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
