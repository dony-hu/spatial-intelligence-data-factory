#!/usr/bin/env python3
"""地址治理 MVP A1-A6 验收脚本（输出 JSON + Markdown）。"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
    if not db_url.startswith("postgresql://"):
        raise ValueError("blocked: --db-url must be postgresql:// in PG-only mode")
    os.environ["DATABASE_URL"] = db_url


def _default_db_url() -> str:
    return str(os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/spatial_db")


def _resolve_llm_gate(*, llm_config: str) -> tuple[bool, dict[str, Any]]:
    try:
        from tools.agent_cli import load_config

        config_path = Path(llm_config)
        if not config_path.is_absolute() and not config_path.exists():
            repo_candidate = REPO_ROOT / config_path
            if repo_candidate.exists():
                config_path = repo_candidate
        cfg = load_config(str(config_path))
        return True, {
            "mode": "real",
            "provider": str(cfg.get("provider") or ""),
            "endpoint": str(cfg.get("endpoint") or ""),
            "model": str(cfg.get("model") or ""),
        }
    except Exception as exc:
        return False, {
            "mode": "real",
            "status": "blocked",
            "reason": "llm_config_invalid",
            "error": str(exc),
            "config_path": str(llm_config),
        }


def _skipped_check(reason: str = "profile_skipped") -> dict[str, Any]:
    return {"passed": False, "skipped": True, "evidence": {"reason": reason}}


def run_acceptance(*, output_dir: Path, db_url: str, workdir: Path, llm_config: str, profile: str = "full") -> dict[str, Any]:
    old_cwd = Path.cwd()
    old_db_url = os.environ.get("DATABASE_URL")
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
        should_run_llm = profile in {"full", "unit", "real-llm-gate"}
        should_run_dryrun = profile in {"full", "unit"}
        should_run_publish = profile in {"full", "integration"}
        should_run_runtime_query = profile in {"full", "integration"}
        should_run_db_check = profile in {"full", "integration"}

        llm_gate_passed = True
        llm_gate_evidence: dict[str, Any] = {"mode": "skipped", "reason": "profile_skipped"}
        if should_run_llm:
            llm_gate_passed, llm_gate_evidence = _resolve_llm_gate(llm_config=llm_config)

        requirement: dict[str, Any] = {"status": "skipped", "reason": "profile_skipped"}
        if should_run_llm:
            if llm_gate_passed:
                requirement = agent.converse("请生成地址治理 MVP 方案")
            else:
                requirement = {"status": "blocked", "reason": "llm_gate_blocked"}

        dryrun: dict[str, Any] = {"status": "skipped", "reason": "profile_skipped"}
        if should_run_dryrun:
            if (not should_run_llm) or llm_gate_passed:
                dryrun = agent.converse(f"试运行 {bundle_v1}")
            else:
                dryrun = {"status": "blocked", "reason": "llm_gate_blocked"}

        publish_v1: dict[str, Any] = {"status": "skipped", "reason": "profile_skipped"}
        publish_v2: dict[str, Any] = {"status": "skipped", "reason": "profile_skipped"}
        blocked: dict[str, Any] = {"status": "skipped", "reason": "profile_skipped"}
        if should_run_publish:
            if profile == "integration" or llm_gate_passed:
                publish_v1 = agent.converse(f"发布 {bundle_v1} 到 runtime")
                publish_v2 = agent.converse(f"发布 {bundle_v2} 到 runtime")
                blocked = agent.converse("发布 acceptance-missing-v9.9.9 到 runtime")
            else:
                publish_v1 = {"status": "blocked", "reason": "llm_gate_blocked"}
                publish_v2 = {"status": "blocked", "reason": "llm_gate_blocked"}
                blocked = {"status": "blocked", "reason": "llm_gate_blocked"}

        detail_status = 0
        list_total = 0
        changed_fields: list[str] = []
        blocked_events: list[dict[str, Any]] = []
        if should_run_runtime_query:
            client = TestClient(app)
            detail = client.get("/v1/governance/ops/workpackages/acceptance-demo-v1.0.0/versions/v1.0.0")
            listed = client.get("/v1/governance/ops/workpackages/acceptance-demo-v1.0.0/versions?status=published")
            compared = client.get(
                "/v1/governance/ops/workpackages/acceptance-demo-v1.0.0/compare"
                "?baseline_version=v1.0.0&candidate_version=v1.1.0"
            )
            detail_status = int(detail.status_code)
            list_total = int((listed.json() if listed.status_code == 200 else {}).get("total") or 0)
            changed_fields = list((compared.json() if compared.status_code == 200 else {}).get("changed_fields", []))
            blocked_events = [
                evt for evt in REPOSITORY.list_audit_events() if evt.get("event_type") == "workpackage_publish_blocked"
            ]

        db_publish_count = 0
        if should_run_db_check and db_url.startswith("postgresql://"):
            from sqlalchemy import create_engine, text

            engine = create_engine(db_url)
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "SET search_path TO governance, runtime, trust_meta, trust_data, audit, "
                        "control_plane, address_line, public"
                    )
                )
                row = conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM runtime.publish_record
                        WHERE status = 'published'
                          AND workpackage_id IN (:wp_v1, :wp_v2)
                        """
                    ),
                    {
                        "wp_v1": "acceptance-demo-v1.0.0",
                        "wp_v2": "acceptance-demo-v1.1.0",
                    },
                ).fetchone()
                db_publish_count = int(row[0] if row else 0)
    finally:
        os.chdir(old_cwd)
        if old_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_db_url

    checks = {
        "A1_llm_real_service_gate": (
            {"passed": llm_gate_passed, "evidence": llm_gate_evidence}
            if should_run_llm
            else _skipped_check()
        ),
        "A1_cli_agent_llm_interaction": (
            {
                "passed": requirement.get("status") == "ok"
                and requirement.get("action") == "confirm_requirement"
                and isinstance(requirement.get("summary"), dict),
                "evidence": requirement,
            }
            if should_run_llm
            else _skipped_check()
        ),
        "A2_governance_dryrun": (
            {
                "passed": dryrun.get("status") == "ok"
                and dryrun.get("action") == "dryrun_workpackage"
                and str((dryrun.get("dryrun") or {}).get("status") or "") == "success",
                "evidence": dryrun,
            }
            if should_run_dryrun
            else _skipped_check()
        ),
        "A3_dryrun_publish_workpackage": (
            {
                "passed": publish_v1.get("runtime", {}).get("status") == "published"
                and publish_v2.get("runtime", {}).get("status") == "published",
                "evidence": [
                    str(publish_v1.get("runtime", {}).get("evidence_ref") or ""),
                    str(publish_v2.get("runtime", {}).get("evidence_ref") or ""),
                ],
            }
            if should_run_publish
            else _skipped_check()
        ),
        "A4_runtime_query_api": (
            {
                "passed": detail_status == 200 and list_total >= 1 and isinstance(changed_fields, list),
                "evidence": {
                    "detail_status": detail_status,
                    "list_total": list_total,
                    "compare_changed_fields": changed_fields,
                },
            }
            if should_run_runtime_query
            else _skipped_check()
        ),
        "A5_blocked_audit_confirmation": (
            {
                "passed": blocked.get("status") == "blocked" and len(blocked_events) > 0,
                "evidence": {
                    "blocked_status": blocked.get("status"),
                    "blocked_event_count": len(blocked_events),
                },
            }
            if should_run_publish
            else _skipped_check()
        ),
        "A6_db_persistence": (
            {
                "passed": db_publish_count >= 2,
                "evidence": {"runtime_publish_record_count": db_publish_count},
            }
            if should_run_db_check
            else _skipped_check()
        ),
    }
    required_keys = [
        "A1_llm_real_service_gate",
        "A1_cli_agent_llm_interaction",
        "A2_governance_dryrun",
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
        "profile": profile,
        "required_keys": required_keys,
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


def _required_keys_for_profile(profile: str) -> list[str]:
    profile_map = {
        "full": [
            "A1_llm_real_service_gate",
            "A1_cli_agent_llm_interaction",
            "A2_governance_dryrun",
            "A3_dryrun_publish_workpackage",
            "A4_runtime_query_api",
            "A5_blocked_audit_confirmation",
            "A6_db_persistence",
        ],
        "unit": [
            "A1_cli_agent_llm_interaction",
            "A2_governance_dryrun",
        ],
        "integration": [
            "A3_dryrun_publish_workpackage",
            "A4_runtime_query_api",
            "A5_blocked_audit_confirmation",
            "A6_db_persistence",
        ],
        "real-llm-gate": [
            "A1_llm_real_service_gate",
            "A1_cli_agent_llm_interaction",
        ],
    }
    return list(profile_map[profile])


def _recompute_all_passed(report: dict[str, Any], required_keys: list[str]) -> dict[str, Any]:
    checks = report.get("checks") or {}
    report["required_keys"] = required_keys
    report["all_passed"] = all(bool(checks.get(key, {}).get("passed")) for key in required_keys)
    return report


def main_with_args(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run address governance MVP acceptance")
    parser.add_argument("--db-url", default=_default_db_url())
    parser.add_argument("--output-dir", default="output/acceptance")
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--llm-config", default="config/llm_api.json")
    parser.add_argument(
        "--profile",
        default="full",
        choices=["full", "unit", "integration", "real-llm-gate"],
        help="验收执行剖面：full/unit/integration/real-llm-gate",
    )
    parser.add_argument(
        "--required-check",
        action="append",
        default=[],
        help="显式覆盖 required keys（可重复传入）",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        report = run_acceptance(
            output_dir=output_dir,
            db_url=args.db_url,
            workdir=Path(args.workdir).resolve(),
            llm_config=args.llm_config,
            profile=str(args.profile),
        )
    except Exception as exc:
        print(str(exc))
        return 2
    required_keys = list(args.required_check) if args.required_check else _required_keys_for_profile(str(args.profile))
    report["profile"] = str(args.profile)
    report = _recompute_all_passed(report, required_keys)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"address-governance-mvp-acceptance-{ts}.json"
    md_path = output_dir / f"address-governance-mvp-acceptance-{ts}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Acceptance JSON: {json_path}")
    print(f"Acceptance Markdown: {md_path}")
    return 0 if report.get("all_passed") else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
