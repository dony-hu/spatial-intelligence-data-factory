#!/usr/bin/env python3
"""TC-06 产线执行脚本：单条显式任务入口 + 失败回放。"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
DEFAULT_WORKPACKAGE = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.1.json"


def now_iso() -> str:
    return datetime.now().isoformat()


def today_tag() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def run_tag() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")


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


def run_single_explicit_task(raw_address: str, runtime_db: Path, quality_threshold: float = 0.9) -> Dict[str, Any]:
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
    return {
        "timestamp": now_iso(),
        "status": str(workflow_result.get("status", "unknown")),
        "raw_address": raw_address,
        "workflow_result": workflow_result,
        "summary": summary,
        "quality": quality,
        "failed_replay_cases": failures,
    }


def write_markdown(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="TC-06 产线执行与失败回放")
    sub = parser.add_subparsers(dest="cmd", required=True)

    single = sub.add_parser("single", help="执行单条显式任务")
    single.add_argument("--address", required=True, help="raw_address 输入")
    single.add_argument("--runtime-db", default=str(DEFAULT_RUNTIME_DB))
    single.add_argument("--queue-file", default=str(DEFAULT_QUEUE_FILE))

    replay = sub.add_parser("replay", help="回放失败队列")
    replay.add_argument("--runtime-db", default=str(DEFAULT_RUNTIME_DB))
    replay.add_argument("--queue-file", default=str(DEFAULT_QUEUE_FILE))
    replay.add_argument("--limit", type=int, default=10)

    loop = sub.add_parser("auto-loop", help="自治循环执行（默认5分钟）")
    loop.add_argument("--minutes", type=int, default=5)
    loop.add_argument("--interval-seconds", type=float, default=30.0)
    loop.add_argument("--runtime-db", default=str(DEFAULT_RUNTIME_DB))
    loop.add_argument("--queue-file", default=str(DEFAULT_QUEUE_FILE))
    loop.add_argument("--seed-address", default="上海市浦东新区世纪大道100号")
    loop.add_argument("--seed-failure-address", default="中山东一路1号")

    args = parser.parse_args()
    runtime_db = Path(getattr(args, "runtime_db"))
    queue_file = Path(getattr(args, "queue_file"))
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.cmd == "single":
        result = run_single_explicit_task(args.address, runtime_db)
        queue = load_failed_queue(queue_file)
        queue = merge_failed_queue(queue, result["failed_replay_cases"])
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
        result = run_single_explicit_task(raw_address, runtime_db)
        return {"status": result["status"]}

    if args.cmd == "replay":
        report = replay_failed_queue(queue_file, _runner, limit=max(1, args.limit))
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
        run_single_explicit_task(args.seed_address, runtime_db)
        failed_seed = run_single_explicit_task(args.seed_failure_address, runtime_db)
        save_failed_queue(queue_file, merge_failed_queue(load_failed_queue(queue_file), failed_seed["failed_replay_cases"]))

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


if __name__ == "__main__":
    main()
