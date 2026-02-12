#!/usr/bin/env python3
"""
Factory Continuous Demo Web Service
后台持续执行用例 + 自动清理环境数据 + 动态看板服务
"""

import argparse
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from testdata.factory_demo_scenarios import get_all_scenarios
from tools.factory_framework import ProductRequirement, ProductType, generate_id
from tools.factory_simple_server import start_server, factory_state, register_action_handlers
from tools.factory_workflow import FactoryWorkflow


SHANGHAI_STREETS = [
    "中山东一路", "中山东二路", "中山东三路", "中山西路",
    "南京东路", "南京西路", "南京中路",
    "陆家嘴环路", "陆家嘴东路", "陆家嘴西路",
    "淮海中路", "淮海西路", "淮海东路",
    "静安寺路", "南京北路", "四川北路", "四川南路",
    "延安东路", "延安西路", "延安中路",
]

SHANGHAI_DISTRICTS = [
    "黄浦区", "浦东新区", "徐汇区", "静安区",
    "虹口区", "杨浦区", "闵行区", "宝山区",
    "嘉定区", "奉贤区", "青浦区", "松江区",
]

BUILDING_NUMBERS = list(range(1, 10001, 10))
SCENARIO_SEQUENCE = ["quick_test", "address_cleaning", "entity_fusion", "relationship_extraction"]


def now_iso() -> str:
    return datetime.now().isoformat()


def reset_runtime_db(db_path: str) -> None:
    """清理演示数据库，避免长期堆积影响演示效果。"""
    if os.path.exists(db_path):
        os.remove(db_path)


def make_address_requirement(case_id: int) -> ProductRequirement:
    district = random.choice(SHANGHAI_DISTRICTS)
    street = random.choice(SHANGHAI_STREETS)
    building = random.choice(BUILDING_NUMBERS)
    address = f"{district}{street}{building}号"

    return ProductRequirement(
        requirement_id=generate_id("req"),
        product_name=f"连续演示地址样本-{case_id}",
        product_type=ProductType.ADDRESS_TO_GRAPH,
        input_format="raw_addresses",
        output_format="graph_nodes_and_relationships",
        input_data=[{"raw": address, "source": "continuous-demo", "id": case_id}],
        sla_metrics={"max_duration": 60, "quality_threshold": 0.9},
        priority=1,
    )


def make_case_requirement(case_id: int, case_mode: str, scenarios: Dict[str, callable]) -> Tuple[ProductRequirement, str]:
    if case_mode == "scenario":
        scenario_name = SCENARIO_SEQUENCE[case_id % len(SCENARIO_SEQUENCE)]
        base_requirement = scenarios[scenario_name]()
        if not base_requirement.input_data:
            return base_requirement, scenario_name
        round_index = case_id // len(SCENARIO_SEQUENCE)
        item_index = round_index % len(base_requirement.input_data)
        single_item = base_requirement.input_data[item_index]
        requirement = ProductRequirement(
            requirement_id=generate_id("req"),
            product_name=f"{base_requirement.product_name}-single-{item_index + 1}",
            product_type=base_requirement.product_type,
            input_format=base_requirement.input_format,
            output_format=base_requirement.output_format,
            input_data=[single_item],
            sla_metrics=dict(base_requirement.sla_metrics),
            priority=base_requirement.priority,
        )
        return requirement, scenario_name

    requirement = make_address_requirement(case_id)
    return requirement, "random_address"


def extract_case_preview(requirement: ProductRequirement) -> str:
    if not requirement.input_data:
        return ""
    first = requirement.input_data[0]
    return str(first.get("raw") or first.get("address") or first)


def update_dashboard_state(
    workflow: FactoryWorkflow,
    requirement: ProductRequirement,
    workflow_result: Dict[str, Any],
    case_name: str,
    case_preview: str,
    processed_in_cycle: int,
    cycle: int,
    max_cycles: int,
    cases_per_cycle: int,
) -> None:
    summary = workflow.get_workflow_summary()
    quality = workflow.get_quality_report()
    stage_exec = workflow_result.get("stages", {}).get("task_executions", {})
    input_count = len(requirement.input_data)
    failed_cases = stage_exec.get("failed_cases", [])
    cleaning_pass = not any(item.get("stage") == "cleaning" for item in failed_cases)
    graph_pass = cleaning_pass and (not any(item.get("stage") == "graph" for item in failed_cases))

    production_lines_info = {}
    for line_id, line in workflow.factory_state.production_lines.items():
        production_lines_info[line_id] = {
            "line_name": line.line_name,
            "completed_tasks": line.completed_tasks,
            "total_tokens_consumed": line.total_tokens_consumed,
            "workers": len(line.workers),
        }

    record_ts = now_iso()
    details = factory_state.setdefault("address_details", [])
    details.append(
        {
            "addr_id": processed_in_cycle,
            "raw_address": case_preview,
            "status": "completed",
            "case_name": case_name,
            "line_owner": "地址清洗产线 + 地址-图谱产线",
            "timestamp": record_ts,
            "detail": {
                "case_name": case_name,
                "input_count": input_count,
                "input_sample": requirement.input_data[:2],
                "cleaning_output": {
                    "completed": stage_exec.get("cleaning_completed", 0),
                },
                "graph_output": {
                    "completed": stage_exec.get("graph_completed", 0),
                    "graph_nodes_generated_total": stage_exec.get("graph_nodes_generated_total", stage_exec.get("graph_nodes_total", 0)),
                    "graph_relationships_generated_total": stage_exec.get("graph_relationships_generated_total", stage_exec.get("graph_relationships_total", 0)),
                    "graph_nodes_merged_total": stage_exec.get("graph_nodes_merged_total", 0),
                    "graph_relationships_merged_total": stage_exec.get("graph_relationships_merged_total", 0),
                    "graph_case_details": stage_exec.get("graph_case_details", []),
                },
                "line_results": [
                    {
                        "line_id": "line_address_cleaning",
                        "line_name": "地址清洗产线",
                        "output": {
                            "cleaning_completed": stage_exec.get("cleaning_completed", 0),
                        },
                    },
                    {
                        "line_id": "line_address_to_graph",
                        "line_name": "地址-图谱产线",
                        "output": {
                            "graph_completed": stage_exec.get("graph_completed", 0),
                            "graph_nodes_generated_total": stage_exec.get("graph_nodes_generated_total", stage_exec.get("graph_nodes_total", 0)),
                            "graph_relationships_generated_total": stage_exec.get("graph_relationships_generated_total", stage_exec.get("graph_relationships_total", 0)),
                            "graph_nodes_merged_total": stage_exec.get("graph_nodes_merged_total", 0),
                            "graph_relationships_merged_total": stage_exec.get("graph_relationships_merged_total", 0),
                        },
                    },
                ],
                "gate_result": {
                    "cleaning_gate_pass": cleaning_pass,
                    "graph_gate_pass": graph_pass,
                    "failed_cases": failed_cases,
                    "final_status": workflow_result.get("status", "unknown"),
                },
            },
        }
    )
    if len(details) > 300:
        del details[:-300]

    change_log = factory_state.setdefault("graph_change_log", [])
    change_log.append(
        {
            "addr_id": processed_in_cycle,
            "case_name": case_name,
            "timestamp": record_ts,
            "line_ids": ["line_address_cleaning", "line_address_to_graph"],
            "source_ids": list({
                str(item.get("source_id", "")).strip()
                for item in (stage_exec.get("graph_case_details", []) or [])
                if str(item.get("source_id", "")).strip()
            }),
            "nodes_merged": stage_exec.get("graph_nodes_merged_total", 0),
            "relationships_merged": stage_exec.get("graph_relationships_merged_total", 0),
        }
    )
    if len(change_log) > 1000:
        del change_log[:-1000]

    factory_state.update(
        {
            "factory_name": summary.get("factory_name", "Factory Continuous Demo"),
            "status": "running",
            "production_lines": production_lines_info,
            "work_orders": summary.get("work_orders", {}),
            "metrics": {
                "processed_count": processed_in_cycle,
                "total_tokens": summary.get("metrics", {}).get("total_tokens_consumed", 0.0),
                "quality_rate": quality.get("pass_rate", 0.0),
            },
            "run": {
                "cycle": cycle,
                "max_cycles": max_cycles,
                "cases_per_cycle": cases_per_cycle,
                "processed_in_cycle": processed_in_cycle,
                "last_reset_at": factory_state.get("run", {}).get("last_reset_at"),
            },
        }
    )


class ManualDemoController:
    """手动模式：一次执行一个用例，或复位测试环境。"""

    def __init__(self, runtime_db: str, case_mode: str = "scenario", startup_reset: bool = True):
        self.runtime_db = runtime_db
        self.case_mode = case_mode
        self.scenarios = get_all_scenarios()
        self.case_id = 0
        self.cycle = 1
        self.workflow = None
        if startup_reset:
            self._wipe_runtime_state(mark_reset=True)
        self._init_workflow()

    def _wipe_runtime_state(self, mark_reset: bool):
        reset_runtime_db(self.runtime_db)
        factory_state["address_details"] = []
        factory_state["graph_change_log"] = []
        if mark_reset:
            run = factory_state.get("run", {}) or {}
            factory_state["run"] = {
                "cycle": run.get("cycle", self.cycle),
                "max_cycles": 0,
                "cases_per_cycle": 0,
                "processed_in_cycle": 0,
                "last_reset_at": now_iso(),
            }

    def _init_workflow(self):
        self.workflow = FactoryWorkflow(
            factory_name=f"上海数据工厂-手动演示-第{self.cycle}轮",
            db_path=self.runtime_db,
            init_production_lines=True,
        )
        self.workflow.approve_all_required_gates(
            approver="manual-demo-service",
            note="Manual local dashboard demo",
        )
        factory_state["runtime_db_path"] = self.runtime_db
        factory_state["status"] = "idle_manual"
        factory_state["run"] = {
            "cycle": self.cycle,
            "max_cycles": 0,
            "cases_per_cycle": 0,
            "processed_in_cycle": len(factory_state.get("address_details", [])),
            "last_reset_at": factory_state.get("run", {}).get("last_reset_at"),
        }

    def run_next_case(self):
        requirement, case_name = make_case_requirement(self.case_id, self.case_mode, self.scenarios)
        self.workflow.submit_product_requirement(requirement)
        workflow_result = self.workflow.create_production_workflow(requirement, auto_execute=True)

        processed = len(factory_state.get("address_details", [])) + 1
        update_dashboard_state(
            workflow=self.workflow,
            requirement=requirement,
            workflow_result=workflow_result,
            case_name=case_name,
            case_preview=extract_case_preview(requirement),
            processed_in_cycle=processed,
            cycle=self.cycle,
            max_cycles=0,
            cases_per_cycle=0,
        )
        self.case_id += 1
        factory_state["status"] = "manual_last_case_done"
        return {
            "status": "ok",
            "action": "run_next_case",
            "case_id": self.case_id,
            "case_name": case_name,
            "workflow_status": workflow_result.get("status", "unknown"),
        }

    def run_custom_address(self, payload):
        if isinstance(payload, str):
            raw = payload.strip()
        else:
            payload = payload or {}
            raw = str(payload.get("raw") or payload.get("address") or "").strip()
        if not raw:
            return {"status": "error", "error": "raw/address 不能为空"}

        requirement = ProductRequirement(
            requirement_id=generate_id("req"),
            product_name="Manual Input Address Case",
            product_type=ProductType.ADDRESS_TO_GRAPH,
            input_format="raw_addresses",
            output_format="graph_nodes_and_relationships",
            input_data=[{"raw": raw, "source": "manual_input", "id": self.case_id}],
            sla_metrics={"max_duration": 60, "quality_threshold": 0.9},
            priority=1,
        )
        self.workflow.submit_product_requirement(requirement)
        workflow_result = self.workflow.create_production_workflow(requirement, auto_execute=True)
        processed = len(factory_state.get("address_details", [])) + 1
        update_dashboard_state(
            workflow=self.workflow,
            requirement=requirement,
            workflow_result=workflow_result,
            case_name="manual_input",
            case_preview=raw,
            processed_in_cycle=processed,
            cycle=self.cycle,
            max_cycles=0,
            cases_per_cycle=0,
        )
        self.case_id += 1
        factory_state["status"] = "manual_last_case_done"
        return {
            "status": "ok",
            "action": "run_custom_address",
            "case_name": "manual_input",
            "workflow_status": workflow_result.get("status", "unknown"),
        }

    def reset_environment(self):
        self._wipe_runtime_state(mark_reset=True)
        self.case_id = 0
        self.cycle += 1
        factory_state["run"] = {
            "cycle": self.cycle,
            "max_cycles": 0,
            "cases_per_cycle": 0,
            "processed_in_cycle": 0,
            "last_reset_at": now_iso(),
        }
        self._init_workflow()
        return {"status": "ok", "action": "reset_environment"}


def run_worker(args: argparse.Namespace, stop_event: threading.Event) -> None:
    scenarios = get_all_scenarios()
    cycle = 1
    factory_state["runtime_db_path"] = args.runtime_db

    while not stop_event.is_set() and (args.max_cycles == 0 or cycle <= args.max_cycles):
        factory_state["status"] = "starting_cycle"
        factory_state["start_time"] = now_iso()
        factory_state["run"] = {
            "cycle": cycle,
            "max_cycles": args.max_cycles,
            "cases_per_cycle": args.cases_per_cycle,
            "processed_in_cycle": 0,
            "last_reset_at": factory_state.get("run", {}).get("last_reset_at"),
        }
        factory_state["address_details"] = []
        if args.cleanup_each_cycle:
            factory_state["graph_change_log"] = []

        if args.cleanup_each_cycle:
            reset_runtime_db(args.runtime_db)

        workflow = FactoryWorkflow(
            factory_name=f"上海数据工厂-持续演示-第{cycle}轮",
            db_path=args.runtime_db,
            init_production_lines=True,
        )
        workflow.approve_all_required_gates(
            approver="continuous-demo-service",
            note="Auto approval for continuous local dashboard demo",
        )

        processed = 0
        for case_id in range(args.cases_per_cycle):
            if stop_event.is_set():
                break
            requirement, case_name = make_case_requirement(case_id, args.case_mode, scenarios)

            try:
                workflow.submit_product_requirement(requirement)
                workflow_result = workflow.create_production_workflow(requirement, auto_execute=True)
                processed += 1
                update_dashboard_state(
                    workflow=workflow,
                    requirement=requirement,
                    workflow_result=workflow_result,
                    case_name=case_name,
                    case_preview=extract_case_preview(requirement),
                    processed_in_cycle=processed,
                    cycle=cycle,
                    max_cycles=args.max_cycles,
                    cases_per_cycle=args.cases_per_cycle,
                )
            except Exception as exc:
                factory_state["status"] = "error"
                details = factory_state.setdefault("address_details", [])
                details.append(
                    {
                        "addr_id": case_id,
                        "raw_address": extract_case_preview(requirement),
                        "status": f"error: {exc}",
                        "case_name": case_name,
                        "timestamp": now_iso(),
                    }
                )

            time.sleep(args.case_interval)

        if stop_event.is_set():
            break

        factory_state["status"] = "cycle_completed"
        if args.cleanup_each_cycle:
            factory_state["status"] = "resetting"
            factory_state["run"]["last_reset_at"] = now_iso()
            time.sleep(args.reset_interval)

        cycle += 1

    factory_state["status"] = "stopped"


def main() -> None:
    parser = argparse.ArgumentParser(description="后台持续执行用例并驱动实时看板")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard host")
    parser.add_argument("--port", type=int, default=5000, help="Dashboard port")
    parser.add_argument("--runtime-db", default="database/factory_demo_runtime.db", help="Runtime sqlite db")
    parser.add_argument("--case-mode", choices=["scenario", "address"], default="scenario", help="Use case source")
    parser.add_argument("--cases-per-cycle", type=int, default=30, help="Number of cases in one cycle")
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means infinite loop")
    parser.add_argument("--case-interval", type=float, default=1.0, help="Seconds between cases")
    parser.add_argument("--reset-interval", type=float, default=3.0, help="Seconds to wait between cycles")
    parser.add_argument("--cleanup-each-cycle", action="store_true", help="Reset runtime db every cycle")
    parser.add_argument("--execution-mode", choices=["manual", "auto"], default="manual", help="manual=按钮单步执行, auto=后台持续执行")
    args = parser.parse_args()

    stop_event = threading.Event()
    factory_state["runtime_db_path"] = args.runtime_db

    def _stop_handler(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    if args.execution_mode == "auto":
        worker = threading.Thread(target=run_worker, args=(args, stop_event), daemon=True)
        worker.start()
        register_action_handlers({})
    else:
        controller = ManualDemoController(runtime_db=args.runtime_db, case_mode=args.case_mode)
        register_action_handlers(
            {
                "run_next_case": controller.run_next_case,
                "reset_environment": controller.reset_environment,
                "run_custom_address": controller.run_custom_address,
            }
        )

    print("=" * 80)
    print("数据工厂后台连续演示服务已启动")
    print(f"看板地址: http://{args.host}:{args.port}")
    print(f"运行数据库: {args.runtime_db}")
    print(f"模式: execution_mode={args.execution_mode}, case_mode={args.case_mode}, cases_per_cycle={args.cases_per_cycle}, max_cycles={args.max_cycles or 'infinite'}")
    print(f"自动清理: {'ON' if args.cleanup_each_cycle else 'OFF'}")
    print("按 Ctrl+C 停止")
    print("=" * 80)

    server, _ = start_server(port=args.port)
    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
