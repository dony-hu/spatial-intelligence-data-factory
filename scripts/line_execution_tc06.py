#!/usr/bin/env python3
"""TC-06 产线执行脚本：单条显式任务入口 + 失败回放。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.factory_framework import ProductRequirement, ProductType, generate_id
from tools.factory_workflow import FactoryWorkflow


DEFAULT_RUNTIME_DB = PROJECT_ROOT / "database" / "tc06_line_execution.db"
DEFAULT_QUEUE_FILE = PROJECT_ROOT / "output" / "line_runs" / "failed_replay_queue.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "line_runs"
DEFAULT_WORKPACKAGE = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.2.json"
DEFAULT_LINE_FEEDBACK_OUT = PROJECT_ROOT / "output" / "workpackages" / "line_feedback.latest.json"

SQLITE_REF_RE = re.compile(r"^sqlite://(?P<path>[^#]+)#(?P<table>[A-Za-z_][A-Za-z0-9_]*)$")
PG_REF_RE = re.compile(r"^pg://(?P<schema>[A-Za-z_][A-Za-z0-9_]*)\.(?P<table>[A-Za-z_][A-Za-z0-9_]*)$")


def now_iso() -> str:
    return datetime.now().isoformat()


def today_tag() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def run_tag() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")


def _resolve_observability_entrypoint(workpackage: Dict[str, Any]) -> Optional[Path]:
    bundle = workpackage.get("observability_bundle") if isinstance(workpackage, dict) else {}
    entrypoints = bundle.get("entrypoints") if isinstance(bundle, dict) else []
    if isinstance(entrypoints, list):
        for item in entrypoints:
            candidate = PROJECT_ROOT / str(item)
            if candidate.suffix == ".py" and candidate.exists():
                return candidate

    wp_id = str(workpackage.get("workpackage_id") or "")
    wp_version = str(workpackage.get("version") or "")
    if wp_id and wp_version:
        bundle_slug = wp_id.replace("wp-", "", 1)
        fallback = PROJECT_ROOT / "workpackages" / "bundles" / bundle_slug / "observability" / "line_observe.py"
        if fallback.exists():
            return fallback
    return None


def _load_observability_module(workpackage: Dict[str, Any]) -> Any:
    entrypoint = _resolve_observability_entrypoint(workpackage)
    if entrypoint is None:
        return None
    spec = importlib.util.spec_from_file_location("line_observe_runtime", str(entrypoint))
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _collect_step_events(workflow_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    stages = workflow_result.get("stages", {}) if isinstance(workflow_result, dict) else {}
    task_executions = stages.get("task_executions", {}) if isinstance(stages, dict) else {}
    failed_cases = task_executions.get("failed_cases", []) if isinstance(task_executions.get("failed_cases"), list) else []

    failed_cleaning_ids = {
        str(item.get("source_id") or "")
        for item in failed_cases
        if str(item.get("stage") or "") == "cleaning"
    }
    failed_graph_ids = {
        str(item.get("source_id") or "")
        for item in failed_cases
        if str(item.get("stage") or "") == "graph"
    }

    events: List[Dict[str, Any]] = []
    for row in task_executions.get("cleaning_case_details", []) if isinstance(task_executions.get("cleaning_case_details"), list) else []:
        source_id = str((row or {}).get("source_id") or "")
        events.append(
            {
                "task_id": source_id,
                "step_code": "parse",
                "status": "failed" if source_id in failed_cleaning_ids else "success",
                "payload": {"stage": "cleaning"},
            }
        )
    for row in task_executions.get("graph_case_details", []) if isinstance(task_executions.get("graph_case_details"), list) else []:
        source_id = str((row or {}).get("source_id") or "")
        events.append(
            {
                "task_id": source_id,
                "step_code": "topology_build",
                "status": "failed" if source_id in failed_graph_ids else "success",
                "payload": {"stage": "graph"},
            }
        )
    return events


def _collect_runtime_observability_metrics(workflow_result: Dict[str, Any], workpackage: Dict[str, Any]) -> Dict[str, Any]:
    module = _load_observability_module(workpackage)
    events = _collect_step_events(workflow_result)
    if module is None:
        total_steps = len(events)
        failed_steps = sum(1 for event in events if str(event.get("status") or "") == "failed")
        return {
            "step_total": total_steps,
            "step_failed": failed_steps,
            "step_error_rate": round(float(failed_steps) / float(total_steps), 6) if total_steps > 0 else 0.0,
            "collector": "fallback_inline",
        }

    observe_step = getattr(module, "observe_step", None)
    aggregate_runtime_metrics = getattr(module, "aggregate_runtime_metrics", None)
    observed_events: List[Dict[str, Any]] = []
    if callable(observe_step):
        for event in events:
            observed_events.append(
                observe_step(
                    task_id=str(event.get("task_id") or ""),
                    step_code=str(event.get("step_code") or ""),
                    status=str(event.get("status") or ""),
                    payload=event.get("payload") or {},
                )
            )
    else:
        observed_events = events

    if callable(aggregate_runtime_metrics):
        metrics = aggregate_runtime_metrics(observed_events)
        if isinstance(metrics, dict):
            metrics["collector"] = "line_observe.aggregate_runtime_metrics"
            return metrics

    total_steps = len(observed_events)
    failed_steps = sum(1 for event in observed_events if str(event.get("status") or "") == "failed")
    return {
        "step_total": total_steps,
        "step_failed": failed_steps,
        "step_error_rate": round(float(failed_steps) / float(total_steps), 6) if total_steps > 0 else 0.0,
        "collector": "line_observe.observe_step_only",
    }


def collect_failed_replay_cases(workflow_result: Dict[str, Any], requirement_input: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failed_cases = (
        workflow_result.get("stages", {})
        .get("task_executions", {})
        .get("failed_cases", [])
        or []
    )
    source_to_raw: Dict[str, str] = {}
    for item in requirement_input:
        source_id = str(item.get("id") or item.get("source") or item.get("raw") or item.get("address") or "").strip()
        raw = str(item.get("raw") or item.get("address") or "").strip()
        if source_id and raw:
            source_to_raw[source_id] = raw

    normalized = []
    for item in failed_cases:
        source_id = str(item.get("source_id", "")).strip()
        raw = source_to_raw.get(source_id, source_id)
        normalized.append(
            {
                "raw_address": raw,
                "source_id": source_id,
                "stage": str(item.get("stage", "unknown")),
                "reason": str(item.get("reason", "UNKNOWN")),
                "first_failed_at": now_iso(),
                "last_replayed_at": "",
                "attempts": 0,
            }
        )
    return normalized


def load_failed_queue(queue_path: Path) -> List[Dict[str, Any]]:
    if not queue_path.exists():
        return []
    try:
        return json.loads(queue_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_failed_queue(queue_path: Path, items: List[Dict[str, Any]]) -> None:
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_failed_queue(existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in existing + new_items:
        key = f"{item.get('raw_address','')}::{item.get('stage','')}"
        if key in merged:
            merged[key]["reason"] = item.get("reason", merged[key].get("reason", "UNKNOWN"))
            merged[key]["source_id"] = item.get("source_id", merged[key].get("source_id", ""))
            if not merged[key].get("first_failed_at"):
                merged[key]["first_failed_at"] = item.get("first_failed_at", "")
        else:
            merged[key] = dict(item)
    return list(merged.values())


def replay_failed_queue(
    queue_path: Path,
    run_one: Callable[[str], Dict[str, Any]],
    limit: int = 10,
) -> Dict[str, Any]:
    queue = load_failed_queue(queue_path)
    replayed = 0
    recovered = 0
    remaining: List[Dict[str, Any]] = []

    for item in queue:
        if replayed >= limit:
            remaining.append(item)
            continue

        raw = str(item.get("raw_address", "")).strip()
        if not raw:
            continue
        replayed += 1

        result = run_one(raw)
        status = str(result.get("status", "unknown"))
        if status == "completed":
            recovered += 1
            continue

        item["attempts"] = int(item.get("attempts", 0)) + 1
        item["last_replayed_at"] = now_iso()
        remaining.append(item)

    save_failed_queue(queue_path, remaining)
    return {
        "timestamp": now_iso(),
        "queue_path": str(queue_path),
        "replayed": replayed,
        "recovered": recovered,
        "remaining": len(remaining),
    }


def run_single_explicit_task(
    raw_address: str,
    runtime_db: Path,
    quality_threshold: float = 0.9,
    workpackage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    workflow = FactoryWorkflow(
        factory_name="TC-06-产线执行",
        db_path=str(runtime_db),
        init_production_lines=True,
    )
    workflow.approve_all_required_gates(
        approver="tc06-line-execution",
        note="TC-06 autonomous execution",
    )

    requirement = ProductRequirement(
        requirement_id=generate_id("req"),
        product_name="TC-06-Explicit-Address",
        product_type=ProductType.ADDRESS_TO_GRAPH,
        input_format="raw_addresses",
        output_format="graph_nodes_and_relationships",
        input_data=[{"id": "tc06-explicit-1", "raw": raw_address, "source": "tc06_explicit"}],
        sla_metrics={"max_duration": 60, "quality_threshold": quality_threshold},
        priority=1,
    )

    workflow.submit_product_requirement(requirement)
    workflow_result = workflow.create_production_workflow(requirement, auto_execute=True)
    summary = workflow.get_workflow_summary()
    quality = workflow.get_quality_report()
    failures = collect_failed_replay_cases(workflow_result, requirement.input_data)
    runtime_observability = _collect_runtime_observability_metrics(
        workflow_result=workflow_result,
        workpackage=workpackage or {},
    )
    return {
        "timestamp": now_iso(),
        "status": str(workflow_result.get("status", "unknown")),
        "raw_address": raw_address,
        "workflow_result": workflow_result,
        "summary": summary,
        "quality": quality,
        "failed_replay_cases": failures,
        "runtime_observability": runtime_observability,
    }


def write_markdown(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate_sqlite_ref(ref: str, expected_table: str) -> bool:
    match = SQLITE_REF_RE.match(ref)
    if not match:
        return False
    return match.group("table") == expected_table


def _validate_pg_ref(ref: str, expected_table: str) -> bool:
    match = PG_REF_RE.match(ref)
    if not match:
        return False
    return match.group("table") == expected_table


def _line_feedback_store_mode(contract: Dict[str, Any]) -> str:
    failure_ref = str(contract.get("failure_queue_snapshot_ref") or "")
    replay_ref = str(contract.get("replay_result_ref") or "")
    if _validate_pg_ref(failure_ref, "failure_queue") and _validate_pg_ref(replay_ref, "replay_runs"):
        return "pg"
    return "sqlite"


def _parse_pg_ref(ref: str, expected_table: str) -> tuple[str, str]:
    match = PG_REF_RE.match(ref)
    if not match or match.group("table") != expected_table:
        raise ValueError(f"invalid pg ref: {ref}")
    return match.group("schema"), match.group("table")


def _pg_enabled() -> bool:
    return str(os.getenv("DATABASE_URL") or "").startswith("postgresql")


def _pg_engine():
    from sqlalchemy import create_engine

    database_url = str(os.getenv("DATABASE_URL") or "")
    if not database_url.startswith("postgresql"):
        raise RuntimeError("DATABASE_URL must be postgresql://... for pg line feedback store")
    return create_engine(database_url)


def _ensure_pg_feedback_tables(schema: str) -> None:
    from sqlalchemy import text

    engine = _pg_engine()
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.failure_queue (
                    failure_id TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    status TEXT NOT NULL,
                    payload_json JSONB NOT NULL DEFAULT '{{}}'::jsonb
                )
                """
            )
        )
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.replay_runs (
                    replay_id TEXT PRIMARY KEY,
                    failure_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    status TEXT NOT NULL,
                    result_json JSONB NOT NULL DEFAULT '{{}}'::jsonb
                )
                """
            )
        )


def _failure_id(item: Dict[str, Any]) -> str:
    raw = str(item.get("raw_address") or "")
    stage = str(item.get("stage") or "")
    digest = hashlib.sha1(f"{raw}::{stage}".encode("utf-8")).hexdigest()[:20]
    return f"fq_{digest}"


def _load_failed_queue_pg(failure_ref: str) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    schema, table = _parse_pg_ref(failure_ref, "failure_queue")
    _ensure_pg_feedback_tables(schema)
    engine = _pg_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(f"SELECT payload_json FROM {schema}.{table} WHERE status = 'pending' ORDER BY created_at ASC")
        ).fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        payload = row[0]
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _save_failed_queue_pg(failure_ref: str, items: List[Dict[str, Any]]) -> None:
    from sqlalchemy import text

    schema, table = _parse_pg_ref(failure_ref, "failure_queue")
    _ensure_pg_feedback_tables(schema)
    engine = _pg_engine()
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE {schema}.{table} SET status = 'resolved' WHERE status = 'pending'"))
        for item in items:
            failure_id = _failure_id(item)
            conn.execute(
                text(
                    f"""
                    INSERT INTO {schema}.{table}(failure_id, created_at, status, payload_json)
                    VALUES (:failure_id, NOW(), 'pending', CAST(:payload AS jsonb))
                    ON CONFLICT (failure_id)
                    DO UPDATE SET status = 'pending', payload_json = CAST(:payload AS jsonb), created_at = NOW()
                    """
                ),
                {"failure_id": failure_id, "payload": json.dumps(item, ensure_ascii=False)},
            )


def _append_replay_run_pg(replay_ref: str, report: Dict[str, Any]) -> None:
    from sqlalchemy import text

    schema, table = _parse_pg_ref(replay_ref, "replay_runs")
    _ensure_pg_feedback_tables(schema)
    replay_id = f"replay_{uuid.uuid4().hex[:12]}"
    engine = _pg_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {schema}.{table}(replay_id, failure_id, created_at, status, result_json)
                VALUES (:replay_id, :failure_id, NOW(), :status, CAST(:result_json AS jsonb))
                """
            ),
            {
                "replay_id": replay_id,
                "failure_id": "batch",
                "status": "done",
                "result_json": json.dumps(report, ensure_ascii=False),
            },
        )


def build_line_feedback_payload(
    contract: Dict[str, Any],
    replay_report_ref: str,
    status: str = "done",
    runtime_observability: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    failure_ref = str(contract.get("failure_queue_snapshot_ref") or "")
    replay_ref = str(contract.get("replay_result_ref") or "")
    valid_failure_ref = _validate_sqlite_ref(failure_ref, "failure_queue") or _validate_pg_ref(failure_ref, "failure_queue")
    valid_replay_ref = _validate_sqlite_ref(replay_ref, "replay_runs") or _validate_pg_ref(replay_ref, "replay_runs")
    if not valid_failure_ref:
        raise ValueError("line_feedback_contract.failure_queue_snapshot_ref 必须是 sqlite://...#failure_queue 或 pg://<schema>.failure_queue")
    if not valid_replay_ref:
        raise ValueError("line_feedback_contract.replay_result_ref 必须是 sqlite://...#replay_runs 或 pg://<schema>.replay_runs")

    done_items = ["runtime_unify", "package_split", "r2_gate_closure"] if status == "done" else ["runtime_unify", "package_split"]
    next_items = [] if status == "done" else ["r2_gate_closure"]
    release_decision = "GO" if status == "done" else "NO_GO"
    payload = {
        "status": status,
        "done": done_items,
        "next": next_items,
        "blocker": "" if status == "done" else "r2_gate_closure_pending",
        "eta": now_iso(),
        "test_report_ref": replay_report_ref,
        "failure_queue_snapshot_ref": failure_ref,
        "replay_result_ref": replay_ref,
        "release_decision": release_decision,
    }
    if isinstance(runtime_observability, dict) and runtime_observability:
        payload["runtime_observability"] = runtime_observability
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="TC-06 产线执行与失败回放")
    sub = parser.add_subparsers(dest="cmd", required=True)

    single = sub.add_parser("single", help="执行单条显式任务")
    single.add_argument("--address", required=True, help="raw_address 输入")
    single.add_argument("--runtime-db", default=str(DEFAULT_RUNTIME_DB))
    single.add_argument("--queue-file", default=str(DEFAULT_QUEUE_FILE))
    single.add_argument("--workpackage", default=str(DEFAULT_WORKPACKAGE))

    replay = sub.add_parser("replay", help="回放失败队列")
    replay.add_argument("--runtime-db", default=str(DEFAULT_RUNTIME_DB))
    replay.add_argument("--queue-file", default=str(DEFAULT_QUEUE_FILE))
    replay.add_argument("--limit", type=int, default=10)
    replay.add_argument("--workpackage", default=str(DEFAULT_WORKPACKAGE))

    loop = sub.add_parser("auto-loop", help="自治循环执行（默认5分钟）")
    loop.add_argument("--minutes", type=int, default=5)
    loop.add_argument("--interval-seconds", type=float, default=30.0)
    loop.add_argument("--runtime-db", default=str(DEFAULT_RUNTIME_DB))
    loop.add_argument("--queue-file", default=str(DEFAULT_QUEUE_FILE))
    loop.add_argument("--seed-address", default="上海市浦东新区世纪大道100号")
    loop.add_argument("--seed-failure-address", default="中山东一路1号")
    loop.add_argument("--workpackage", default=str(DEFAULT_WORKPACKAGE))

    feedback = sub.add_parser("feedback", help="按 workpackage 合同生成产线回传")
    feedback.add_argument("--workpackage", default=str(DEFAULT_WORKPACKAGE))
    feedback.add_argument("--replay-report", required=True)
    feedback.add_argument("--output", default=str(DEFAULT_LINE_FEEDBACK_OUT))
    feedback.add_argument("--status", choices=["done", "blocked"], default="done")

    args = parser.parse_args()
    runtime_db = Path(getattr(args, "runtime_db", DEFAULT_RUNTIME_DB))
    queue_file = Path(getattr(args, "queue_file", DEFAULT_QUEUE_FILE))
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    workpackage_payload: Dict[str, Any] = {}
    if hasattr(args, "workpackage"):
        wp_path = Path(getattr(args, "workpackage"))
        if wp_path.exists():
            try:
                workpackage_payload = json.loads(wp_path.read_text(encoding="utf-8"))
            except Exception:
                workpackage_payload = {}

    if args.cmd == "single":
        result = run_single_explicit_task(args.address, runtime_db, workpackage=workpackage_payload)
        contract = workpackage_payload.get("line_feedback_contract") if isinstance(workpackage_payload, dict) else {}
        contract = contract if isinstance(contract, dict) else {}
        store_mode = _line_feedback_store_mode(contract)
        if store_mode == "pg" and not _pg_enabled():
            raise RuntimeError("PG line feedback store requires DATABASE_URL=postgresql://...")
        queue = load_failed_queue(queue_file)
        if store_mode == "pg":
            queue = _load_failed_queue_pg(str(contract.get("failure_queue_snapshot_ref") or ""))
        queue = merge_failed_queue(queue, result["failed_replay_cases"])
        if store_mode == "pg":
            _save_failed_queue_pg(str(contract.get("failure_queue_snapshot_ref") or ""), queue)
        save_failed_queue(queue_file, queue)

        tag = run_tag()
        out_json = output_dir / f"tc06_single_run_{tag}.json"
        out_md = output_dir / f"tc06_single_run_{tag}.md"
        out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        write_markdown(
            out_md,
            [
                "# TC-06 单条显式任务执行记录",
                "",
                f"- 时间：{result['timestamp']}",
                f"- 输入地址：`{result['raw_address']}`",
                f"- 工作流状态：`{result['status']}`",
                f"- 失败样本入队：{len(result['failed_replay_cases'])}",
                f"- 失败队列文件：`{queue_file}`",
            ],
        )
        print(f"[TC-06] single status={result['status']} json={out_json} md={out_md}")
        return

    def _runner(raw_address: str) -> Dict[str, Any]:
        result = run_single_explicit_task(raw_address, runtime_db, workpackage=workpackage_payload)
        return {"status": result["status"]}

    if args.cmd == "replay":
        contract = workpackage_payload.get("line_feedback_contract") if isinstance(workpackage_payload, dict) else {}
        contract = contract if isinstance(contract, dict) else {}
        store_mode = _line_feedback_store_mode(contract)
        if store_mode == "pg" and not _pg_enabled():
            raise RuntimeError("PG line feedback store requires DATABASE_URL=postgresql://...")
        if store_mode == "pg":
            queue = _load_failed_queue_pg(str(contract.get("failure_queue_snapshot_ref") or ""))
            save_failed_queue(queue_file, queue)
        report = replay_failed_queue(queue_file, _runner, limit=max(1, args.limit))
        if store_mode == "pg":
            remaining = load_failed_queue(queue_file)
            _save_failed_queue_pg(str(contract.get("failure_queue_snapshot_ref") or ""), remaining)
            _append_replay_run_pg(str(contract.get("replay_result_ref") or ""), report)
        tag = run_tag()
        out_json = output_dir / f"tc06_failure_replay_{tag}.json"
        out_md = output_dir / f"tc06_failure_replay_{tag}.md"
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        write_markdown(
            out_md,
            [
                "# TC-06 失败回放记录",
                "",
                f"- 时间：{report['timestamp']}",
                f"- 回放条数：{report['replayed']}",
                f"- 恢复条数：{report['recovered']}",
                f"- 队列剩余：{report['remaining']}",
                f"- 队列文件：`{queue_file}`",
            ],
        )
        print(f"[TC-06] replay replayed={report['replayed']} recovered={report['recovered']} remaining={report['remaining']}")
        return

    if args.cmd == "auto-loop":
        deadline = time.time() + max(1, args.minutes) * 60
        iteration = 0
        # 启动时注入一条成功样本与一条失败样本，确保回放链路有可观测数据。
        run_single_explicit_task(args.seed_address, runtime_db, workpackage=workpackage_payload)
        failed_seed = run_single_explicit_task(args.seed_failure_address, runtime_db, workpackage=workpackage_payload)
        queue = merge_failed_queue(load_failed_queue(queue_file), failed_seed["failed_replay_cases"])
        save_failed_queue(queue_file, queue)
        contract = workpackage_payload.get("line_feedback_contract") if isinstance(workpackage_payload, dict) else {}
        contract = contract if isinstance(contract, dict) else {}
        if _line_feedback_store_mode(contract) == "pg" and not _pg_enabled():
            raise RuntimeError("PG line feedback store requires DATABASE_URL=postgresql://...")
        if _line_feedback_store_mode(contract) == "pg":
            _save_failed_queue_pg(str(contract.get("failure_queue_snapshot_ref") or ""), queue)

        while time.time() < deadline:
            iteration += 1
            replay_failed_queue(queue_file, _runner, limit=1)
            time.sleep(max(0.1, args.interval_seconds))

        report = {
            "timestamp": now_iso(),
            "loop_minutes": args.minutes,
            "iterations": iteration,
            "queue_remaining": len(load_failed_queue(queue_file)),
            "queue_file": str(queue_file),
        }
        tag = run_tag()
        out_json = output_dir / f"tc06_autoloop_{tag}.json"
        out_md = output_dir / f"tc06_autoloop_{tag}.md"
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        write_markdown(
            out_md,
            [
                "# TC-06 5分钟自治循环记录",
                "",
                f"- 时间：{report['timestamp']}",
                f"- 循环分钟数：{report['loop_minutes']}",
                f"- 执行轮数：{report['iterations']}",
                f"- 队列剩余：{report['queue_remaining']}",
                f"- 队列文件：`{queue_file}`",
            ],
        )
        print(f"[TC-06] autoloop iterations={iteration} remaining={report['queue_remaining']} md={out_md}")
        return

    if args.cmd == "feedback":
        workpackage = json.loads(Path(args.workpackage).read_text(encoding="utf-8"))
        contract = workpackage.get("line_feedback_contract") or {}
        payload = build_line_feedback_payload(
            contract=contract,
            replay_report_ref=str(args.replay_report),
            status=str(args.status),
            runtime_observability=workpackage.get("runtime_observability") if isinstance(workpackage.get("runtime_observability"), dict) else None,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[TC-06] feedback generated output={output_path}")
        return


if __name__ == "__main__":
    main()
