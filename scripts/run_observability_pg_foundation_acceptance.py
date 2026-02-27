#!/usr/bin/env python3
"""可观测性 + PG 基础能力验收脚本（Story 2.1）。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("GOVERNANCE_ALLOW_MEMORY_FALLBACK", "1")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_acceptance() -> dict[str, Any]:
    trace_id = "trace_obs_acceptance_001"
    REPOSITORY.record_observation_event(
        source_service="governance_api",
        event_type="task_submitted",
        status="success",
        trace_id=trace_id,
        task_id="task_obs_accept_001",
        payload={"stage": "submit"},
    )
    REPOSITORY.upsert_observation_metric(
        metric_name="task.success_rate",
        metric_value=0.97,
        labels={"env": "dev", "owner_line": "observability"},
        window_start="2026-02-27T14:00:00Z",
        window_end="2026-02-27T14:05:00Z",
    )
    created_alert = REPOSITORY.create_observation_alert(
        alert_rule="blocked_rate_high",
        severity="error",
        trigger_value=0.19,
        threshold_value=0.15,
        trace_id=trace_id,
    )

    client = TestClient(app)
    snapshot = client.get("/v1/governance/observability/snapshot?env=dev")
    events = client.get(f"/v1/governance/observability/events?trace_id={trace_id}&limit=20")
    replay = client.get(f"/v1/governance/observability/traces/{trace_id}/replay")
    timeseries = client.get("/v1/governance/observability/timeseries?metric_name=task.success_rate&limit=20")
    alerts = client.get("/v1/governance/observability/alerts?status=open")
    ack = client.post(
        f"/v1/governance/observability/alerts/{created_alert['alert_id']}/ack",
        json={"actor": "obs_owner"},
    )
    management = client.get("/v1/governance/lab/observability/management/data")

    checks = {
        "snapshot_api": snapshot.status_code == 200,
        "events_api": events.status_code == 200 and (events.json().get("total", 0) >= 1),
        "replay_api": replay.status_code == 200 and replay.json().get("trace_id") == trace_id,
        "timeseries_api": timeseries.status_code == 200 and (timeseries.json().get("total", 0) >= 1),
        "alerts_ack_api": ack.status_code == 200 and ack.json().get("status") == "acked",
        "lab_management_contract": management.status_code == 200 and "observation_foundation" in management.json(),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_passed": all(checks.values()),
        "checks": checks,
    }


def _to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 可观测性与PG基础验收报告",
        "",
        f"- 生成时间：`{report.get('generated_at')}`",
        f"- 结论：`{'PASS' if report.get('all_passed') else 'FAIL'}`",
        "",
        "## 检查项",
    ]
    for key, passed in (report.get("checks") or {}).items():
        lines.append(f"- [{'x' if passed else ' '}] `{key}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output/acceptance")
    args = parser.parse_args()

    report = run_acceptance()
    out_dir = (REPO_ROOT / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = _now_tag()
    json_path = out_dir / f"observability-pg-foundation-acceptance-{tag}.json"
    md_path = out_dir / f"observability-pg-foundation-acceptance-{tag}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    print(f"Acceptance JSON: {json_path}")
    print(f"Acceptance Markdown: {md_path}")
    return 0 if report.get("all_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
