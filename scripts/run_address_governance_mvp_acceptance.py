#!/usr/bin/env python3
"""地址治理 MVP A1-A6 验收脚本（输出 JSON + Markdown）。"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from init_governance_sqlite import init_db
except ImportError:  # pragma: no cover - 兼容作为模块导入执行
    from scripts.init_governance_sqlite import init_db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_bundle(bundle_dir: Path, *, name: str, version: str) -> str:
    bundle_name = f"{name}-{version}"
    target = bundle_dir / bundle_name
    target.mkdir(parents=True, exist_ok=True)
    (target / "workpackage.json").write_text(
        json.dumps({"name": name, "version": version, "sources": ["gaode", "baidu"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (target / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    (target / "skills").mkdir(exist_ok=True)
    (target / "observability").mkdir(exist_ok=True)
    return bundle_name


def _prepare_runtime(db_url: str) -> None:
    os.environ["DATABASE_URL"] = db_url
    os.environ["GOVERNANCE_ALLOW_MEMORY_FALLBACK"] = "0"
    if db_url.startswith("sqlite:///"):
        init_db(db_url.replace("sqlite:///", ""))


def run_acceptance(*, output_dir: Path, db_url: str, workdir: Path) -> dict[str, Any]:
    old_cwd = Path.cwd()
    old_db_url = os.environ.get("DATABASE_URL")
    old_fallback = os.environ.get("GOVERNANCE_ALLOW_MEMORY_FALLBACK")
    try:
        _prepare_runtime(db_url)

        repo_mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
        importlib.reload(repo_mod)
        ops_router_mod = importlib.import_module("services.governance_api.app.routers.ops")
        importlib.reload(ops_router_mod)
        app_mod = importlib.import_module("services.governance_api.app.main")
        importlib.reload(app_mod)
        agent_mod = importlib.import_module("packages.factory_agent.agent")
        importlib.reload(agent_mod)

        from fastapi.testclient import TestClient

        REPOSITORY = repo_mod.REPOSITORY
        app = app_mod.app
        FactoryAgent = agent_mod.FactoryAgent

        os.chdir(workdir)
        bundles = Path("workpackages/bundles")
        bundles.mkdir(parents=True, exist_ok=True)
        bundle_v1 = _write_bundle(bundles, name="acceptance-demo", version="v1.0.0")
        bundle_v2 = _write_bundle(bundles, name="acceptance-demo", version="v1.1.0")

        agent = FactoryAgent()
        publish_v1 = agent.converse(f"发布 {bundle_v1} 到 runtime")
        publish_v2 = agent.converse(f"发布 {bundle_v2} 到 runtime")
        blocked = agent.converse("发布 acceptance-missing-v9.9.9 到 runtime")

        client = TestClient(app)
        detail = client.get("/v1/governance/ops/workpackages/acceptance-demo-v1.0.0/versions/v1.0.0")
        listed = client.get("/v1/governance/ops/workpackages/acceptance-demo-v1.0.0/versions?status=published")
        compared = client.get(
            "/v1/governance/ops/workpackages/acceptance-demo-v1.0.0/compare"
            "?baseline_version=v1.0.0&candidate_version=v1.1.0"
        )
        blocked_events = [evt for evt in REPOSITORY.list_audit_events() if evt.get("event_type") == "workpackage_publish_blocked"]

        db_publish_count = 0
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute("SELECT COUNT(*) FROM addr_workpackage_publish").fetchone()
                db_publish_count = int(row[0] if row else 0)
            finally:
                conn.close()
    finally:
        os.chdir(old_cwd)
        if old_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_db_url
        if old_fallback is None:
            os.environ.pop("GOVERNANCE_ALLOW_MEMORY_FALLBACK", None)
        else:
            os.environ["GOVERNANCE_ALLOW_MEMORY_FALLBACK"] = old_fallback

    checks = {
        "A1_cli_agent_llm_interaction": {
            "passed": publish_v1.get("status") == "ok",
            "evidence": str(publish_v1.get("message") or ""),
        },
        "A2_governance_plan_dialogue": {
            "passed": bool(publish_v1.get("runtime", {}).get("version")),
            "evidence": str(publish_v1.get("runtime", {}).get("version") or ""),
        },
        "A3_dryrun_publish_workpackage": {
            "passed": publish_v1.get("runtime", {}).get("status") == "published"
            and publish_v2.get("runtime", {}).get("status") == "published",
            "evidence": [
                str(publish_v1.get("runtime", {}).get("evidence_ref") or ""),
                str(publish_v2.get("runtime", {}).get("evidence_ref") or ""),
            ],
        },
        "A4_runtime_query_api": {
            "passed": detail.status_code == 200 and listed.status_code == 200 and compared.status_code == 200,
            "evidence": {
                "detail_status": detail.status_code,
                "list_total": int((listed.json() if listed.status_code == 200 else {}).get("total") or 0),
                "compare_changed_fields": (compared.json() if compared.status_code == 200 else {}).get("changed_fields", []),
            },
        },
        "A5_blocked_audit_confirmation": {
            "passed": blocked.get("status") == "blocked" and len(blocked_events) > 0,
            "evidence": {
                "blocked_status": blocked.get("status"),
                "blocked_event_count": len(blocked_events),
            },
        },
        "A6_db_persistence": {
            "passed": db_publish_count >= 2,
            "evidence": {"addr_workpackage_publish_count": db_publish_count},
        },
    }
    required_keys = [
        "A3_dryrun_publish_workpackage",
        "A4_runtime_query_api",
        "A5_blocked_audit_confirmation",
        "A6_db_persistence",
    ]
    all_passed = all(bool(checks.get(key, {}).get("passed")) for key in required_keys)
    return {
        "generated_at": _now_iso(),
        "db_url": db_url,
        "workspace": str(workdir),
        "all_passed": all_passed,
        "checks": checks,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 地址治理 MVP 验收报告",
        "",
        f"- 生成时间：`{report.get('generated_at')}`",
        f"- 数据库：`{report.get('db_url')}`",
        f"- 全量结论：`{'PASS' if report.get('all_passed') else 'FAIL'}`",
        "",
        "## 检查项",
    ]
    for key, value in report.get("checks", {}).items():
        mark = "x" if value.get("passed") else " "
        lines.append(f"- [{mark}] `{key}`")
        lines.append(f"  - 证据：`{json.dumps(value.get('evidence', ''), ensure_ascii=False)}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run address governance MVP acceptance")
    parser.add_argument("--db-url", default="sqlite:///output/runtime/governance.db")
    parser.add_argument("--output-dir", default="output/acceptance")
    parser.add_argument("--workdir", default=".")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = run_acceptance(output_dir=output_dir, db_url=args.db_url, workdir=Path(args.workdir).resolve())
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"address-governance-mvp-acceptance-{ts}.json"
    md_path = output_dir / f"address-governance-mvp-acceptance-{ts}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Acceptance JSON: {json_path}")
    print(f"Acceptance Markdown: {md_path}")
    return 0 if report.get("all_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
