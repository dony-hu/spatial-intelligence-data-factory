from __future__ import annotations

import os
from pathlib import Path


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def bootstrap_pg_env() -> None:
    """Load DB-related env vars from project-level files if process env is empty."""
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / ".env.local",
        root / ".env",
        root / "config" / "database.postgres.env",
        root / "config" / "database.postgres.example.env",
    ]

    for env_path in candidates:
        for key, value in _parse_env_file(env_path).items():
            os.environ.setdefault(key, value)

    db_url = str(os.getenv("DATABASE_URL") or "").strip()
    if not db_url:
        fallback = (
            str(os.getenv("TRUST_META_DATABASE_URL") or "").strip()
            or str(os.getenv("TRUST_TRUSTDB_DSN") or "").strip()
        )
        if fallback:
            os.environ["DATABASE_URL"] = fallback
            db_url = fallback

    if db_url:
        os.environ.setdefault("TRUST_META_DATABASE_URL", db_url)
        os.environ.setdefault("TRUST_TRUSTDB_DSN", db_url)
        os.environ.setdefault("READONLY_DATABASE_URL", db_url)

