#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_PATH = ROOT / "testdata" / "address_samples_50.json"


def _database_url() -> str:
    return str(os.getenv("DATABASE_URL") or "postgresql://huda@127.0.0.1:5432/si_factory")


def _apply_schema(engine) -> None:
    sql_files = [
        ROOT / "database" / "postgres" / "sql" / "001_enable_extensions.sql",
        ROOT / "database" / "postgres" / "sql" / "002_init_tables.sql",
        ROOT / "database" / "postgres" / "sql" / "003_init_indexes.sql",
    ]
    with engine.begin() as conn:
        for path in sql_files:
            conn.execute(text(path.read_text(encoding="utf-8")))


def _load_samples(limit: int = 10) -> list[dict]:
    payload = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    samples = payload.get("samples", []) if isinstance(payload, dict) else []
    if not isinstance(samples, list):
        return []
    return [item for item in samples if isinstance(item, dict)][:limit]


def main() -> int:
    db_url = _database_url()
    if not db_url.startswith("postgresql"):
        raise SystemExit("DATABASE_URL must be postgresql://...")

    engine = create_engine(db_url)
    _apply_schema(engine)

    samples = _load_samples(limit=12)
    if not samples:
        raise SystemExit(f"no samples found at {SAMPLES_PATH}")

    with engine.begin() as conn:
        for idx, sample in enumerate(samples, 1):
            task_id = f"seed_task_{idx:03d}"
            batch_id = task_id
            raw_id = str(sample.get("input_id") or f"seed_raw_{idx:03d}")
            raw_text = str(sample.get("raw_address") or "")
            district = str(sample.get("district") or "")
            street = str(sample.get("street") or "")
            detail = str(sample.get("building") or "")
            canon_text = str(sample.get("standard_full_address") or raw_text)

            confidence = 0.52 if idx % 4 == 1 else (0.78 if idx % 4 == 2 else (0.87 if idx % 4 == 3 else 0.93))
            strategy = "human_required" if confidence < 0.85 else "auto_pass"

            conn.execute(
                text(
                    """
                    INSERT INTO addr_batch (batch_id, batch_name, status, created_at, updated_at)
                    VALUES (:batch_id, :batch_name, 'SUCCEEDED', NOW(), NOW())
                    ON CONFLICT (batch_id)
                    DO UPDATE SET batch_name = EXCLUDED.batch_name, status = EXCLUDED.status, updated_at = NOW();
                    """
                ),
                {"batch_id": batch_id, "batch_name": f"manual-review-seed-{idx:03d}"},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO addr_task_run (task_id, batch_id, status, runtime, created_at, updated_at)
                    VALUES (:task_id, :batch_id, 'SUCCEEDED', 'seed_script', NOW(), NOW())
                    ON CONFLICT (task_id)
                    DO UPDATE SET batch_id = EXCLUDED.batch_id, status = EXCLUDED.status, runtime = EXCLUDED.runtime, updated_at = NOW();
                    """
                ),
                {"task_id": task_id, "batch_id": batch_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO addr_raw (raw_id, batch_id, raw_text, province, city, district, street, detail, raw_hash, ingested_at)
                    VALUES (:raw_id, :batch_id, :raw_text, :province, :city, :district, :street, :detail, :raw_hash, NOW())
                    ON CONFLICT (raw_id)
                    DO UPDATE SET batch_id = EXCLUDED.batch_id, raw_text = EXCLUDED.raw_text, province = EXCLUDED.province,
                                  city = EXCLUDED.city, district = EXCLUDED.district, street = EXCLUDED.street, detail = EXCLUDED.detail;
                    """
                ),
                {
                    "raw_id": raw_id,
                    "batch_id": batch_id,
                    "raw_text": raw_text,
                    "province": "上海市",
                    "city": "上海市",
                    "district": district,
                    "street": street,
                    "detail": detail,
                    "raw_hash": f"seed_hash_{raw_id}",
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO addr_canonical (canonical_id, raw_id, canon_text, confidence, strategy, evidence, ruleset_version, created_at, updated_at)
                    VALUES (:canonical_id, :raw_id, :canon_text, :confidence, :strategy, CAST(:evidence AS jsonb), 'default', NOW(), NOW())
                    ON CONFLICT (canonical_id)
                    DO UPDATE SET canon_text = EXCLUDED.canon_text, confidence = EXCLUDED.confidence,
                                  strategy = EXCLUDED.strategy, evidence = EXCLUDED.evidence, updated_at = NOW();
                    """
                ),
                {
                    "canonical_id": f"seed_canon_{idx:03d}",
                    "raw_id": raw_id,
                    "canon_text": canon_text,
                    "confidence": confidence,
                    "strategy": strategy,
                    "evidence": json.dumps({"items": [{"source": "seed_manual_review_pg_data", "sample_index": idx}]}, ensure_ascii=False),
                },
            )

        # Seed one already-reviewed sample for "已人工决策" UI验证。
        first_raw = str(samples[0].get("input_id") or "seed_raw_001")
        conn.execute(
            text(
                """
                INSERT INTO addr_review (review_id, raw_id, review_status, reviewer, comment, reviewed_at, created_at, updated_at)
                VALUES ('seed_review_001', :raw_id, 'approved', 'seed-bot', 'seed reviewed sample', NOW(), NOW(), NOW())
                ON CONFLICT (review_id)
                DO UPDATE SET raw_id = EXCLUDED.raw_id, review_status = EXCLUDED.review_status, reviewer = EXCLUDED.reviewer,
                              comment = EXCLUDED.comment, reviewed_at = EXCLUDED.reviewed_at, updated_at = NOW();
                """
            ),
            {"raw_id": first_raw},
        )

        counts = {}
        for table in ["addr_task_run", "addr_raw", "addr_canonical", "addr_review"]:
            counts[table] = int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)

    print(json.dumps({"ok": True, "database_url": db_url, "counts": counts}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
