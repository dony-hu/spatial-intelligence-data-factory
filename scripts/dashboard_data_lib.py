#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "output" / "dashboard"
EVENTS_PATH = DASHBOARD_DIR / "dashboard_events.jsonl"

PROJECT_OVERVIEW_PATH = DASHBOARD_DIR / "project_overview.json"
WORKLINES_OVERVIEW_PATH = DASHBOARD_DIR / "worklines_overview.json"
WORKPACKAGES_LIVE_PATH = DASHBOARD_DIR / "workpackages_live.json"
TEST_STATUS_BOARD_PATH = DASHBOARD_DIR / "test_status_board.json"
MANIFEST_PATH = DASHBOARD_DIR / "dashboard_manifest.json"

WORKPACKAGE_DIR = PROJECT_ROOT / "workpackages"
DISPATCH_DIR = PROJECT_ROOT / "coordination" / "dispatch"
STATUS_DIR = PROJECT_ROOT / "coordination" / "status"
TASK_CARDS_PATH = PROJECT_ROOT / "coordination" / "task-cards.md"
OUTPUT_WORKPACKAGES_DIR = PROJECT_ROOT / "output" / "workpackages"
TESTS_DIR = PROJECT_ROOT / "tests"
OUTPUT_DIR = PROJECT_ROOT / "output"
LAB_MODE_DIR = OUTPUT_DIR / "lab_mode"
WEB_E2E_RESULT_PATH = LAB_MODE_DIR / "web_e2e_latest.json"

REQUIRED_OUTPUTS = {
    "project_overview": "project_overview.json",
    "worklines_overview": "worklines_overview.json",
    "workpackages_live": "workpackages_live.json",
    "test_status_board": "test_status_board.json",
}

STATUS_FILE_TO_LINE = {
    "project-orchestrator.md": ("line_project_orchestrator", "项目管理总控线"),
    "engineering-supervisor.md": ("line_engineering_supervisor", "工程监理线"),
    "factory-tooling.md": ("line_core_runtime", "核心引擎与运行时线"),
    "line-execution.md": ("line_execution_feedback", "产线执行与回传闭环线"),
    "trust-data-hub.md": ("line_trust_hub", "可信数据Hub线"),
    "factory-workpackage.md": ("line_address_algo", "地址算法与治理规则线"),
    "test-quality-gate.md": ("line_test_quality", "测试平台与质量门槛线"),
    "factory-observability-gen.md": ("line_observability_ops", "可观测与运营指标线"),
}

OWNER_BY_LINE_NAME = {
    "项目管理总控线": "项目管理总控线-Codex",
    "工程监理线": "工程监理-Codex",
    "核心引擎与运行时线": "核心引擎与运行时线-Codex",
    "产线执行与回传闭环线": "产线执行与回传闭环线-Codex",
    "可信数据Hub线": "可信数据Hub线-Codex",
    "地址算法与治理规则线": "地址算法与治理规则线-Codex",
    "测试平台与质量门槛线": "测试平台与质量门槛线-Codex",
    "可观测与运营指标线": "可观测与运营指标线-Codex",
}

OWNER_BY_LINE_TYPE = {
    "address_to_topology": "产线执行与回传闭环线-Codex",
    "core_engine_stabilization": "核心引擎与运行时线-Codex",
    "address_core_algorithm_and_tests": "地址算法与治理规则线-Codex",
    "governance_api_and_lab_stabilization": "核心引擎与运行时线-Codex",
    "trust_data_hub_stabilization": "可信数据Hub线-Codex",
    "public_security_address": "产线执行与回传闭环线-Codex",
    "urban_governance": "产线执行与回传闭环线-Codex",
    "pm_dashboard": "项目管理总控线-Codex",
    "test_panel_sql_query": "测试平台与质量门槛线-Codex",
}

OWNER_LINE_BY_LINE_TYPE = {
    "address_to_topology": "产线执行与回传闭环线",
    "core_engine_stabilization": "核心引擎与运行时线",
    "address_core_algorithm_and_tests": "地址算法与治理规则线",
    "governance_api_and_lab_stabilization": "核心引擎与运行时线",
    "trust_data_hub_stabilization": "可信数据Hub线",
    "public_security_address": "产线执行与回传闭环线",
    "urban_governance": "产线执行与回传闭环线",
    "pm_dashboard": "项目管理总控线",
    "test_panel_sql_query": "测试平台与质量门槛线",
}


@dataclass
class LineState:
    line_id: str
    line_name: str
    owner: str
    status: str
    progress: int
    done: str
    next: str
    blocker: str
    eta: str
    last_update: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except Exception:
        return str(path)


def _latest_dispatch_iteration() -> str:
    files = sorted(DISPATCH_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return "iteration-unknown"
    return files[0].stem


def _parse_markdown_section_list(content: str, header: str) -> list[str]:
    lines = content.splitlines()
    results: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = line.strip() == f"## {header}"
            continue
        if not in_section:
            continue
        if line.startswith("## "):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            results.append(stripped[2:].strip())
    return results


def _parse_overview_risks() -> list[dict[str, Any]]:
    overview = STATUS_DIR / "overview.md"
    if not overview.exists():
        return []
    content = overview.read_text(encoding="utf-8")
    risk_lines = _parse_markdown_section_list(content, "当前阻塞")
    risks: list[dict[str, Any]] = []
    for idx, line in enumerate(risk_lines[:5], start=1):
        severity = "high" if "硬阻塞" in line or "风险" in line else "medium"
        status = "open"
        if "无" in line:
            status = "mitigated"
            severity = "low"
        risks.append(
            {
                "id": f"R-{idx:03d}",
                "title": line,
                "severity": severity,
                "owner": "总控Codex（Orchestrator）",
                "status": status,
            }
        )
    return risks


def _parse_line_status_files() -> list[LineState]:
    overview_progress = _parse_overview_progress_map()
    lines: list[LineState] = []
    for file_name, (line_id, line_name) in STATUS_FILE_TO_LINE.items():
        path = STATUS_DIR / file_name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")

        progress_match = re.search(r"-\s*进度：\s*(\d+)%", content)
        progress = int(progress_match.group(1)) if progress_match else int(overview_progress.get(line_name, 0))

        done_items = re.findall(r"^\s*-\s*(.+)$", _extract_section(content, "Done"), re.MULTILINE)
        next_items = re.findall(r"^\s*-\s*(.+)$", _extract_section(content, "Next"), re.MULTILINE)
        blocker_match = re.search(r"-\s*Blocker：\s*(.+)", content)
        eta_match = re.search(r"-\s*ETA：\s*(.+)", content)

        blocker = blocker_match.group(1).strip() if blocker_match else ""
        blocker = blocker.lstrip("-").strip()
        if blocker in {"无", "none", "None"}:
            blocker = ""

        if progress >= 95 and not blocker:
            status = "done"
        elif blocker:
            status = "blocked"
        elif progress > 0:
            status = "in_progress"
        else:
            status = "planned"

        lines.append(
            LineState(
                line_id=line_id,
                line_name=line_name,
                owner=OWNER_BY_LINE_NAME.get(line_name, "待分配"),
                status=status,
                progress=progress,
                done="；".join(done_items[:3]) if done_items else "",
                next="；".join(next_items[:3]) if next_items else "",
                blocker=blocker,
                eta=eta_match.group(1).strip() if eta_match else "",
                last_update=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
            )
        )
    return lines


def _parse_overview_progress_map() -> dict[str, int]:
    path = STATUS_DIR / "overview.md"
    if not path.exists():
        return {}
    mapping: dict[str, int] = {}
    regex = re.compile(r"^-\s*(.+)：[^（]+（(\d+)%）")
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = regex.match(raw.strip())
        if not m:
            continue
        mapping[m.group(1).strip()] = int(m.group(2))
    return mapping


def _extract_section(content: str, section_name: str) -> str:
    lines = content.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip().startswith(f"- {section_name}：") or line.strip().startswith(f"## {section_name}"):
            start = idx + 1
            break
    if start is None:
        return ""

    captured: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("- ") and any(stripped.startswith(f"- {x}：") for x in ["Done", "Next", "Blocker", "ETA", "Artifacts"]):
            break
        if stripped.startswith("## "):
            break
        captured.append(line)
    return "\n".join(captured)


def _load_workpackages() -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for path in sorted(WORKPACKAGE_DIR.glob("wp-*.json")):
        if "template" in path.name:
            continue
        payload = _read_json(path, {})
        if not payload:
            continue
        payload["_path"] = path
        packages.append(payload)
    return packages


def _priority_from_id(workpackage_id: str) -> str:
    lowered = workpackage_id.lower()
    if "p0" in lowered:
        return "P0"
    if "v1.0" in lowered:
        return "P1"
    return "P2"


def _latest_event_items(limit: int = 30) -> list[dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    for raw in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return records[-limit:]


def _collect_release_report() -> dict[str, Any]:
    report_path = OUTPUT_WORKPACKAGES_DIR / "wp-core-engine-p0-stabilization-v0.1.0.report.json"
    return _read_json(report_path, {}) if report_path.exists() else {}


def _collect_line_feedback() -> dict[str, Any]:
    path = OUTPUT_WORKPACKAGES_DIR / "line_feedback.latest.json"
    return _read_json(path, {}) if path.exists() else {}


def build_project_overview(as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or _now_iso()
    packages = _load_workpackages()
    release_report = _collect_release_report()
    line_states = _parse_line_status_files()
    live_packages = build_workpackages_live(as_of=as_of)
    open_by_priority = {
        str(item.get("priority") or ""): int(item.get("open") or 0)
        for item in live_packages.get("by_priority", [])
        if isinstance(item, dict)
    }
    p0_open = open_by_priority.get("P0", 0)
    p1_open = open_by_priority.get("P1", 0)
    p2_open = open_by_priority.get("P2", 0)

    decision = str(release_report.get("release_decision") or "HOLD")
    blocked = sum(1 for line in line_states if line.status == "blocked")
    if decision == "NO_GO" or blocked >= 2:
        overall_status = "red"
    elif decision == "HOLD" or blocked == 1:
        overall_status = "yellow"
    else:
        overall_status = "green"

    key_milestones = []
    for wp in packages[:5]:
        wp_id = str(wp.get("workpackage_id") or "")
        eta = str(wp.get("factory_release", {}).get("released_at") or "")
        status = "in_progress"
        if decision == "GO" and "p0-stabilization" in wp_id:
            status = "done"
        key_milestones.append({"name": wp_id, "status": status, "eta": eta})

    return {
        "project_id": "spatial-intelligence-data-factory",
        "project_name": "Spatial Intelligence Data Factory",
        "iteration": _latest_dispatch_iteration(),
        "as_of": as_of,
        "overall_status": overall_status,
        "priority_summary": {
            "p0_open": p0_open,
            "p1_open": p1_open,
            "p2_open": p2_open,
        },
        "key_milestones": key_milestones,
        "top_risks": _parse_overview_risks(),
        "release_decision": decision if decision in {"GO", "NO_GO", "HOLD"} else "HOLD",
    }


def _parse_dispatch_dependencies() -> list[dict[str, str]]:
    files = sorted(DISPATCH_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return []
    content = files[0].read_text(encoding="utf-8")

    dependencies: list[dict[str, str]] = []
    for line in content.splitlines():
        if "依赖" not in line:
            continue
        if "无前置硬依赖" in line:
            dependencies.append(
                {
                    "from_line": "工厂-工作包",
                    "to_line": "产线执行",
                    "topic": line.strip("- "),
                    "status": "clear",
                }
            )
            continue
        dependencies.append(
            {
                "from_line": "工厂-工具/执行引擎",
                "to_line": "工厂-工作包",
                "topic": line.strip("- "),
                "status": "open",
            }
        )
    return dependencies[:8]


def build_worklines_overview(as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or _now_iso()
    lines = _parse_line_status_files()
    return {
        "as_of": as_of,
        "lines": [
            {
                "line_id": line.line_id,
                "line_name": line.line_name,
                "owner": line.owner,
                "status": line.status,
                "progress": line.progress,
                "done": line.done,
                "next": line.next,
                "blocker": line.blocker,
                "eta": line.eta,
                "last_update": line.last_update,
            }
            for line in lines
        ],
        "cross_line_dependencies": _parse_dispatch_dependencies(),
        "blocked_count": sum(1 for line in lines if line.status == "blocked"),
    }


def _status_from_progress(progress: int, blocker: str) -> str:
    if blocker:
        return "blocked"
    if progress >= 95:
        return "done"
    if progress > 0:
        return "in_progress"
    return "planned"


def _normalize_release_decision(payload: dict[str, Any]) -> str:
    raw = str(payload.get("release_decision") or payload.get("result") or "").strip().upper()
    if raw in {"GO", "NO_GO", "HOLD"}:
        return raw
    return "HOLD"


def _workpackage_report_override(wp_id: str) -> tuple[str, int, str] | None:
    report_map: dict[str, Path] = {
        "wp-address-topology-v1.0.1": OUTPUT_WORKPACKAGES_DIR / "wp-address-topology-v1.0.1.acceptance.report.py311.json",
        "wp-address-topology-v1.0.2": OUTPUT_WORKPACKAGES_DIR / "wp-address-topology-v1.0.2.acceptance.report.py311.json",
        "wp-pm-dashboard-test-progress-v0.1.0": OUTPUT_WORKPACKAGES_DIR / "wp-pm-dashboard-test-progress-v0.1.0.report.json",
        "wp-test-panel-sql-query-readonly-v0.1.0": OUTPUT_WORKPACKAGES_DIR / "wp-test-panel-sql-query-readonly-v0.1.0.report.json",
    }
    report_path = report_map.get(wp_id)
    if not report_path or not report_path.exists():
        return None
    payload = _read_json(report_path, {})
    decision = _normalize_release_decision(payload if isinstance(payload, dict) else {})
    status = "done" if decision == "GO" else ("blocked" if decision == "NO_GO" else "in_progress")
    progress = 100 if decision == "GO" else (0 if decision == "NO_GO" else 80)
    return status, progress, _relative(report_path)


def build_workpackages_live(as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or _now_iso()
    packages = _load_workpackages()
    line_states = {line.line_name: line for line in _parse_line_status_files()}
    release_report = _collect_release_report()
    line_feedback = _collect_line_feedback()

    package_rows: list[dict[str, Any]] = []
    for wp in packages:
        wp_id = str(wp.get("workpackage_id") or "")
        title = str(wp.get("line_spec", {}).get("goal") or wp.get("workpackage_name") or wp_id)
        line_type = str(wp.get("line_spec", {}).get("line_type") or "unknown")
        owner_line = OWNER_LINE_BY_LINE_TYPE.get(line_type, line_type)
        owner = OWNER_BY_LINE_TYPE.get(line_type, "待分配")
        line_state = line_states.get(owner_line)
        progress = line_state.progress if line_state else 0
        blocker = line_state.blocker if line_state else ""
        status = _status_from_progress(progress, blocker)

        test_report_ref = ""
        release_decision = "HOLD"
        if "p0-stabilization" in wp_id and release_report:
            release_decision = str(release_report.get("release_decision") or "HOLD")
            test_report_ref = _relative(OUTPUT_WORKPACKAGES_DIR / "wp-core-engine-p0-stabilization-v0.1.0.report.json")
            if line_feedback:
                status = str(line_feedback.get("status") or status)
                status = "done" if status == "done" else status
                progress = 100 if status == "done" else progress
        elif (OUTPUT_WORKPACKAGES_DIR / "p0.address_core.test-report.json").exists() and "address-core" in wp_id:
            test_report_ref = _relative(OUTPUT_WORKPACKAGES_DIR / "p0.address_core.test-report.json")
            release_decision = "GO"
            status = "done"
            progress = 100
        elif (OUTPUT_WORKPACKAGES_DIR / "p0.governance_api_and_lab.test-report.json").exists() and "governance-api-lab" in wp_id:
            test_report_ref = _relative(OUTPUT_WORKPACKAGES_DIR / "p0.governance_api_and_lab.test-report.json")
            release_decision = "GO"
            status = "done"
            progress = 100
        elif (OUTPUT_WORKPACKAGES_DIR / "p0.trust_data_hub.test-report.json").exists() and "trust-data-hub" in wp_id:
            test_report_ref = _relative(OUTPUT_WORKPACKAGES_DIR / "p0.trust_data_hub.test-report.json")
            release_decision = "GO"
            status = "done"
            progress = 100

        override = _workpackage_report_override(wp_id)
        if override is not None:
            status, progress, test_report_ref = override
            release_payload = _read_json(PROJECT_ROOT / test_report_ref, {})
            release_decision = _normalize_release_decision(release_payload if isinstance(release_payload, dict) else {})

        eta = line_state.eta if line_state else ""
        started_at = str(wp.get("factory_release", {}).get("released_at") or "")
        source_path = Path(wp.get("_path"))
        updated_at = datetime.fromtimestamp(source_path.stat().st_mtime, tz=timezone.utc).isoformat()

        package_rows.append(
            {
                "workpackage_id": wp_id,
                "title": title,
                "priority": _priority_from_id(wp_id),
                "owner_line": owner_line,
                "owner": owner,
                "status": status,
                "progress": progress,
                "started_at": started_at,
                "eta": eta,
                "test_report_ref": test_report_ref,
                "release_decision": release_decision,
                "updated_at": updated_at,
            }
        )

    by_owner_line_map: dict[str, dict[str, Any]] = {}
    by_priority_map: dict[str, dict[str, Any]] = {}
    for item in package_rows:
        owner_line = item["owner_line"]
        holder = by_owner_line_map.setdefault(owner_line, {"owner_line": owner_line, "total": 0, "in_progress": 0, "blocked": 0, "done": 0})
        holder["total"] += 1
        if item["status"] == "in_progress":
            holder["in_progress"] += 1
        if item["status"] == "blocked":
            holder["blocked"] += 1
        if item["status"] == "done":
            holder["done"] += 1

        priority = item["priority"]
        p = by_priority_map.setdefault(priority, {"priority": priority, "total": 0, "open": 0})
        p["total"] += 1
        if item["status"] != "done":
            p["open"] += 1

    recent_changes = []
    for event in _latest_event_items(limit=20):
        recent_changes.append(
            {
                "time": str(event.get("time") or ""),
                "event_type": str(event.get("event_type") or ""),
                "workpackage_id": str(event.get("workpackage_id") or ""),
                "summary": str(event.get("summary") or ""),
                "operator": str(event.get("operator") or "system"),
            }
        )

    return {
        "as_of": as_of,
        "packages": sorted(package_rows, key=lambda x: x["workpackage_id"]),
        "by_owner_line": sorted(by_owner_line_map.values(), key=lambda x: x["owner_line"]),
        "by_priority": sorted(by_priority_map.values(), key=lambda x: x["priority"]),
        "recent_changes": recent_changes,
    }


def _parse_pytest_tail(output_tail: str) -> tuple[int, int, float]:
    passed = 0
    failed = 0
    duration = 0.0
    passed_match = re.search(r"(\d+)\s+passed", output_tail)
    failed_match = re.search(r"(\d+)\s+failed", output_tail)
    duration_match = re.search(r"in\s+([0-9.]+)s", output_tail)
    if passed_match:
        passed = int(passed_match.group(1))
    if failed_match:
        failed = int(failed_match.group(1))
    if duration_match:
        duration = float(duration_match.group(1))
    return passed, failed, duration


def _collect_test_suites() -> list[dict[str, Any]]:
    suites: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_WORKPACKAGES_DIR.glob("p0.*.test-report.json")):
        payload = _read_json(path, {})
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        output_tail = str(result.get("output_tail") or "")
        passed, failed, duration = _parse_pytest_tail(output_tail)
        last_run_at = str(result.get("ended_at") or "")
        status = "passed" if bool(payload.get("passed")) else "failed"

        suites.append(
            {
                "suite_id": f"suite_{payload.get('package', path.stem)}",
                "name": str(payload.get("package") or path.stem),
                "scope": str(payload.get("scope") or ""),
                "last_run_at": last_run_at,
                "status": status,
                "passed": passed,
                "failed": failed,
                "duration_sec": duration,
                "report_ref": _relative(path),
            }
        )

    release_report = _collect_release_report()
    if release_report:
        suites.append(
            {
                "suite_id": "suite_release_gate",
                "name": "release_gate_validation",
                "scope": "P0",
                "last_run_at": str(release_report.get("meta", {}).get("executed_at") or ""),
                "status": "passed" if release_report.get("release_decision") == "GO" else "failed",
                "passed": int(bool(release_report.get("release_decision") == "GO")),
                "failed": int(not bool(release_report.get("release_decision") == "GO")),
                "duration_sec": 0.0,
                "report_ref": _relative(OUTPUT_WORKPACKAGES_DIR / "wp-core-engine-p0-stabilization-v0.1.0.report.json"),
            }
        )

    web_e2e_tests = sorted((TESTS_DIR / "web_e2e").glob("test_*.py"))
    if web_e2e_tests:
        web_e2e_report = _read_json(WEB_E2E_RESULT_PATH, {}) if WEB_E2E_RESULT_PATH.exists() else {}
        if isinstance(web_e2e_report, dict) and str(web_e2e_report.get("suite_id") or "") == "suite_web_e2e_catalog":
            suites.append(
                {
                    "suite_id": "suite_web_e2e_catalog",
                    "name": "web_e2e_catalog",
                    "scope": "ui",
                    "last_run_at": str(web_e2e_report.get("last_run_at") or _now_iso()),
                    "status": str(web_e2e_report.get("status") or "unknown"),
                    "passed": int(web_e2e_report.get("passed") or 0),
                    "failed": int(web_e2e_report.get("failed") or 0),
                    "duration_sec": float(web_e2e_report.get("duration_sec") or 0.0),
                    "report_ref": str(web_e2e_report.get("report_ref") or _relative(WEB_E2E_RESULT_PATH)),
                }
            )
        else:
            suites.append(
                {
                    "suite_id": "suite_web_e2e_catalog",
                    "name": "web_e2e_catalog",
                    "scope": "ui",
                    "last_run_at": _now_iso(),
                    "status": "unknown",
                    "passed": 0,
                    "failed": 0,
                    "duration_sec": 0.0,
                    "report_ref": _relative(TESTS_DIR / "web_e2e"),
                }
            )
    return suites


def _quality_gates_from_report() -> dict[str, Any]:
    report = _collect_release_report()
    gates = report.get("gate_results") if isinstance(report, dict) else None
    workpackage_schema_ci = bool(gates.get("workpackage_schema_ci")) if isinstance(gates, dict) else False
    line_feedback_contract = bool(gates.get("line_feedback_contract_enforced")) if isinstance(gates, dict) else False
    failure_replay_contract = bool(gates.get("failure_replay_feedback_closed")) if isinstance(gates, dict) else False
    overall = workpackage_schema_ci and line_feedback_contract and failure_replay_contract
    return {
        "workpackage_schema_ci": workpackage_schema_ci,
        "line_feedback_contract": line_feedback_contract,
        "failure_replay_contract": failure_replay_contract,
        "overall": overall,
    }


def _artifact_link(path: Path | None) -> str:
    if path is None:
        return "-"
    try:
        rel = path.relative_to(OUTPUT_DIR)
    except Exception:
        return "-"
    return f"/artifacts/{rel.as_posix()}"


def _build_overall_progress(suites: list[dict[str, Any]]) -> dict[str, Any]:
    progress_path = LAB_MODE_DIR / "cn1300_module_coverage_progress.json"
    progress_data = _read_json(progress_path, {}) if progress_path.exists() else {}

    total_cases = int(progress_data.get("total_rows") or 0)
    executed_cases = int(progress_data.get("processed_rows") or 0)

    passed_cases = int(sum(int(x.get("passed") or 0) for x in suites if isinstance(x, dict)))
    failed_cases = int(sum(int(x.get("failed") or 0) for x in suites if isinstance(x, dict)))
    skipped_cases = max(executed_cases - passed_cases - failed_cases, 0) if executed_cases > 0 else 0
    pass_rate = round((passed_cases / executed_cases), 4) if executed_cases > 0 else 0.0

    times: list[str] = []
    for suite in suites:
        if not isinstance(suite, dict):
            continue
        t = str(suite.get("last_run_at") or "").strip()
        if t:
            times.append(t)
    updated = str(progress_data.get("updated_at") or "").strip()
    if updated:
        times.append(updated)
    last_run_at = max(times) if times else ""

    mode = str(progress_data.get("status") or "unknown")
    if "completed" in mode:
        mode = "batch_coverage"

    return {
        "total_cases": total_cases if total_cases else "-",
        "executed_cases": executed_cases if executed_cases else "-",
        "passed_cases": passed_cases if passed_cases else 0,
        "failed_cases": failed_cases if failed_cases else 0,
        "skipped_cases": skipped_cases if skipped_cases else 0,
        "pass_rate": pass_rate if executed_cases > 0 else "-",
        "last_run_at": last_run_at or "-",
        "mode": mode or "-",
    }


def _build_coverage_links() -> dict[str, str]:
    return {
        "coverage_view": "http://127.0.0.1:8000/v1/governance/lab/coverage/view",
        "coverage_data": "http://127.0.0.1:8000/v1/governance/lab/coverage/data",
    }


def _current_branch() -> str:
    try:
        output = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(PROJECT_ROOT), text=True)
        return output.strip()
    except Exception:
        return "unknown"


def build_test_status_board(as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or _now_iso()
    suites = _collect_test_suites()
    regressions: list[dict[str, Any]] = []
    for suite in suites:
        if suite["status"] != "failed":
            continue
        regressions.append(
            {
                "suite_id": suite["suite_id"],
                "case_id": "aggregate",
                "first_failed_at": suite["last_run_at"],
                "current_status": "open",
                "owner": "工厂-工具/执行引擎Codex",
            }
        )

    release_report = _collect_release_report()
    baseline = release_report.get("runtime_baseline", {}) if isinstance(release_report, dict) else {}
    baseline_python = str(
        baseline.get("python_version")
        or (
            Path(PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip()
            if (PROJECT_ROOT / ".python-version").exists()
            else ""
        )
        or "unknown"
    )
    runtime_python = sys.version.split()[0]

    return {
        "as_of": as_of,
        "test_suites": suites,
        "overall_progress": _build_overall_progress(suites),
        "links": _build_coverage_links(),
        "quality_gates": _quality_gates_from_report(),
        "regressions": regressions,
        "environment": {
            "python_version": runtime_python,
            "python_target": baseline_python,
            "ci_runtime": str(baseline.get("ci_runtime") or "unknown"),
            "branch": _current_branch(),
        },
    }


def build_manifest(as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or _now_iso()
    return {
        "as_of": as_of,
        "version": "1.0.0",
        "files": {
            "project_overview": REQUIRED_OUTPUTS["project_overview"],
            "worklines_overview": REQUIRED_OUTPUTS["worklines_overview"],
            "workpackages_live": REQUIRED_OUTPUTS["workpackages_live"],
            "test_status_board": REQUIRED_OUTPUTS["test_status_board"],
            "pm_brief_json": "pm_brief_zh-CN.json",
            "pm_brief_md": "pm_brief_zh-CN.md",
            "workline_dispatch_prompts_json": "workline_dispatch_prompts_latest.json",
            "workline_dispatch_prompts_md": "workline_dispatch_prompts_latest.md",
            "management_review_json": "dispatch-address-line-closure-001-management-review.json",
            "management_review_md": "dispatch-address-line-closure-001-management-review.md",
            "management_review_latest_json": "dispatch-address-line-closure-002-management-review.json",
            "management_review_latest_md": "dispatch-address-line-closure-002-management-review.md",
            "dashboard_dev_task_engineering_supervisor_json": "dashboard_dev_task_engineering_supervisor.json",
            "dashboard_dev_task_engineering_supervisor_md": "dashboard_dev_task_engineering_supervisor.md",
            "dashboard_dev_task_overview_optimization_json": "dashboard_dev_task_overview_optimization.json",
            "dashboard_dev_task_overview_optimization_md": "dashboard_dev_task_overview_optimization.md",
            "dashboard_dev_task_next_round_pm_dashboard_json": "dashboard_dev_task_next_round_pm_dashboard.json",
            "dashboard_dev_task_next_round_pm_dashboard_md": "dashboard_dev_task_next_round_pm_dashboard.md",
            "phase1_workpackage_prompts_json": "phase1_workpackage_prompts_latest.json",
            "phase1_workpackage_prompts_md": "phase1_workpackage_prompts_latest.md",
        },
        "refresh_policy": {
            "event_driven": True,
            "scheduled_cron": "*/15 * * * *",
        },
        "observability_fields": {
            "test_overview": [
                "total",
                "executed",
                "passed",
                "failed",
                "skipped",
                "pass_rate",
                "quality_score",
                "last_run_at",
                "gate_decision",
            ],
            "execution_process": [
                "task_batch_id",
                "workpackage_id",
                "status",
                "progress",
                "owner",
                "eta",
                "updated_at",
            ],
            "failure_classification": [
                "failure_type",
                "severity",
                "retryable",
                "gate_impact",
                "evidence_ref",
            ],
            "sql_panel": [
                "readonly_select_with_only",
                "whitelist_tables",
                "limit_enforced",
                "timeout_sec",
                "audit_history_ref",
            ],
        },
    }


def append_event(
    event_type: str,
    workpackage_id: str = "",
    summary: str = "",
    operator: str = "system",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "time": _now_iso(),
        "event_type": event_type,
        "workpackage_id": workpackage_id,
        "summary": summary,
        "operator": operator,
        "payload": payload or {},
    }
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def write_outputs(payloads: dict[str, dict[str, Any]]) -> None:
    for key, payload in payloads.items():
        if key == "project_overview":
            _write_json(PROJECT_OVERVIEW_PATH, payload)
        elif key == "worklines_overview":
            _write_json(WORKLINES_OVERVIEW_PATH, payload)
        elif key == "workpackages_live":
            _write_json(WORKPACKAGES_LIVE_PATH, payload)
        elif key == "test_status_board":
            _write_json(TEST_STATUS_BOARD_PATH, payload)
        elif key == "dashboard_manifest":
            _write_json(MANIFEST_PATH, payload)


def build_all(as_of: str | None = None) -> dict[str, dict[str, Any]]:
    as_of = as_of or _now_iso()
    return {
        "project_overview": build_project_overview(as_of=as_of),
        "worklines_overview": build_worklines_overview(as_of=as_of),
        "workpackages_live": build_workpackages_live(as_of=as_of),
        "test_status_board": build_test_status_board(as_of=as_of),
        "dashboard_manifest": build_manifest(as_of=as_of),
    }


def refresh_by_event(event_type: str, as_of: str | None = None) -> dict[str, dict[str, Any]]:
    as_of = as_of or _now_iso()
    payloads: dict[str, dict[str, Any]] = {}

    if event_type in {"task_dispatched", "progress_refreshed", "status_collected", "release_decision_changed"}:
        payloads["project_overview"] = build_project_overview(as_of=as_of)
        payloads["worklines_overview"] = build_worklines_overview(as_of=as_of)
        payloads["workpackages_live"] = build_workpackages_live(as_of=as_of)

    if event_type in {"test_synced", "release_decision_changed"}:
        payloads["test_status_board"] = build_test_status_board(as_of=as_of)

    payloads["dashboard_manifest"] = build_manifest(as_of=as_of)
    return payloads


def parse_args_for_event() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update dashboard files on event")
    parser.add_argument(
        "--event-type",
        required=True,
        choices=[
            "task_dispatched",
            "progress_refreshed",
            "status_collected",
            "test_synced",
            "release_decision_changed",
        ],
    )
    parser.add_argument("--workpackage-id", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--operator", default="system")
    parser.add_argument("--payload-json", default="{}")
    return parser.parse_args()
