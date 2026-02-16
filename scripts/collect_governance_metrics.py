#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "output" / "dashboard"
METRICS_PATH = DASHBOARD_DIR / "governance_metrics.json"

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def run_tests():
    print("Running E2E tests...")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/e2e/test_address_governance_full_cycle.py",
        "-v"
    ]
    start_time = datetime.now()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
        )
        duration = (datetime.now() - start_time).total_seconds()
        output = completed.stdout + completed.stderr
        
        passed = int(re.search(r"(\d+)\s+passed", output).group(1)) if re.search(r"(\d+)\s+passed", output) else 0
        failed = int(re.search(r"(\d+)\s+failed", output).group(1)) if re.search(r"(\d+)\s+failed", output) else 0
        
        return {
            "status": "passed" if completed.returncode == 0 else "failed",
            "passed": passed,
            "failed": failed,
            "duration_sec": duration,
            "output_tail": output[-2000:],
            "executed_at": _now_iso()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "executed_at": _now_iso()
        }

def collect_table_data(conn, table_name, limit=100):
    result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT :limit"), {"limit": limit})
    columns = result.keys()
    rows = []
    for row in result:
        row_dict = dict(zip(columns, row))
        for key, value in row_dict.items():
            if isinstance(value, datetime):
                row_dict[key] = value.isoformat()
        rows.append(row_dict)
    return rows

def collect_db_metrics():
    db_url = os.getenv("DATABASE_URL")
    if not db_url or (not db_url.startswith("postgresql") and not db_url.startswith("sqlite")):
        print("DATABASE_URL not set or not postgres/sqlite, skipping DB metrics.")
        return {"status": "skipped", "reason": "no_db_connection"}

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            raw_count = conn.execute(text("SELECT count(*) FROM addr_raw")).scalar()
            canonical_count = conn.execute(text("SELECT count(*) FROM addr_canonical")).scalar()
            task_success_count = conn.execute(text("SELECT count(*) FROM addr_task_run WHERE status='SUCCEEDED'")).scalar()
            
            samples = []
            rows = conn.execute(text("""
                SELECT 
                    r.raw_text, 
                    c.canon_text, 
                    c.confidence, 
                    c.strategy 
                FROM addr_canonical c
                JOIN addr_raw r ON c.raw_id = r.raw_id
                ORDER BY c.created_at DESC 
                LIMIT 5
            """)).mappings().all()
            
            for row in rows:
                samples.append({
                    "raw_text": row["raw_text"],
                    "canon_text": row["canon_text"],
                    "confidence": float(row["confidence"]),
                    "strategy": row["strategy"]
                })
            
            table_data = {
                "task_batch": {
                    "addr_batch": collect_table_data(conn, "addr_batch"),
                    "addr_task_run": collect_table_data(conn, "addr_task_run")
                },
                "data_governance": {
                    "addr_raw": collect_table_data(conn, "addr_raw"),
                    "addr_canonical": collect_table_data(conn, "addr_canonical"),
                    "addr_review": collect_table_data(conn, "addr_review")
                },
                "rules_changes": {
                    "addr_ruleset": collect_table_data(conn, "addr_ruleset"),
                    "addr_change_request": collect_table_data(conn, "addr_change_request")
                },
                "audit_logs": {
                    "addr_audit_event": collect_table_data(conn, "addr_audit_event"),
                    "api_audit_log": collect_table_data(conn, "api_audit_log"),
                    "agent_execution_log": collect_table_data(conn, "agent_execution_log")
                }
            }

            return {
                "status": "connected",
                "counts": {
                    "addr_raw": raw_count,
                    "addr_canonical": canonical_count,
                    "successful_tasks": task_success_count
                },
                "samples": samples,
                "tables": table_data
            }
    except Exception as e:
        print(f"Error collecting DB metrics: {e}")
        return {"status": "error", "error": str(e)}

def main():
    test_results = run_tests()
    db_metrics = collect_db_metrics()
    
    report = {
        "generated_at": _now_iso(),
        "test_execution": test_results,
        "governance_data": db_metrics
    }
    
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Metrics saved to {METRICS_PATH}")

if __name__ == "__main__":
    main()
