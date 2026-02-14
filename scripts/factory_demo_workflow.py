#!/usr/bin/env python3
"""
Factory Demo Workflow - Complete demonstration of the factory system
Automatically executes a production workflow from product requirement to delivery
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.factory_workflow import FactoryWorkflow
from testdata.factory_demo_scenarios import get_all_scenarios
from scripts._mode_guard import ensure_demo_allowed


def print_section(title: str, width: int = 80) -> None:
    """Print a formatted section header"""
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_subsection(title: str, width: int = 70) -> None:
    """Print a formatted subsection header"""
    print(f"\n{title}")
    print("-" * width)


def demo_workflow(scenario_name: str = 'address_cleaning', auto_execute: bool = True) -> None:
    """Run a complete factory demonstration workflow"""

    print_section("Factory Demonstration System - Complete Workflow", 80)

    # Initialize factory
    print_subsection("Step 1: Initializing Factory System")
    workflow = FactoryWorkflow(factory_name="Shanghai Data Factory")
    workflow.approve_all_required_gates(
        approver="demo-system",
        note="Auto approval for local demonstration"
    )
    print("✓ Factory system initialized")
    print(f"  Database: database/factory.db")

    # Get scenario
    print_subsection("Step 2: Loading Product Requirement Scenario")
    scenarios = get_all_scenarios()
    if scenario_name not in scenarios:
        print(f"✗ Scenario '{scenario_name}' not found")
        print(f"  Available scenarios: {list(scenarios.keys())}")
        return

    scenario_func = scenarios[scenario_name]
    requirement = scenario_func()

    print(f"✓ Scenario loaded: {scenario_name}")
    print(f"  Product Name: {requirement.product_name}")
    print(f"  Product Type: {requirement.product_type.value}")
    print(f"  Input Data: {len(requirement.input_data)} items")
    print(f"  Priority: {requirement.priority}")
    print(f"  SLA: {json.dumps(requirement.sla_metrics, indent=2)}")

    # Submit requirement
    print_subsection("Step 3: Submitting Product Requirement")
    submission = workflow.submit_product_requirement(requirement)
    print(f"✓ Requirement submitted")
    print(f"  Requirement ID: {submission['requirement_id']}")
    print(f"  Status: {submission['status']}")

    # Create workflow
    print_subsection("Step 4: Creating Production Workflow")
    print("  Stages:")
    print("  1. Director evaluates requirement feasibility")
    print("  2. Process Expert designs optimal workflow")
    print("  3. Production Line Leader creates production lines")
    print("  4. Workers execute data processing tasks")
    print("  5. Quality Inspector verifies output quality")

    wf = workflow.create_production_workflow(requirement, auto_execute=auto_execute)

    print(f"\n✓ Production workflow created: {wf['workflow_id']}")
    print(f"  Status: {wf['status']}")

    # Director evaluation
    director_eval = wf['stages'].get('director_evaluation', {})
    print(f"\n  Director Evaluation:")
    print(f"    Feasible: {director_eval.get('feasible')}")
    print(f"    Estimated Lines: {director_eval.get('details', {}).get('estimated_lines_needed')}")
    print(f"    Estimated Workers: {director_eval.get('details', {}).get('estimated_workers_needed')}")
    print(f"    Estimated Duration: {director_eval.get('details', {}).get('estimated_duration_minutes')}m")

    # Process design
    expert_design = wf['stages'].get('expert_design', {})
    print(f"\n  Process Design:")
    print(f"    Process ID: {expert_design.get('process_id')}")
    print(f"    Steps: {', '.join(expert_design.get('steps', []))}")
    print(f"    Estimated Duration: {expert_design.get('estimated_duration')}m")

    # Production plan
    plan = wf['stages'].get('production_plan', {})
    print(f"\n  Production Plan:")
    print(f"    Plan ID: {plan.get('plan_id')}")
    print(f"    Lines Needed: {plan.get('production_lines_needed')}")
    print(f"    Workers per Line: {plan.get('workers_per_line')}")

    # Production lines
    lines_created = wf['stages'].get('production_lines_created', {})
    print(f"\n  Production Lines Created: {lines_created.get('count')}")
    for line_id in lines_created.get('line_ids', []):
        print(f"    - {line_id}")

    # Work orders
    wo_created = wf['stages'].get('work_orders_created', {})
    wo_count = wo_created.get('count', wo_created.get('total_orders', 0))
    print(f"\n  Work Orders Created: {wo_count}")

    # Executions (if auto_execute)
    if auto_execute:
        executions = wf['stages'].get('task_executions', {})
        cleaning_completed = executions.get('cleaning_completed', 0)
        graph_completed = executions.get('graph_completed', 0)
        total_executed = executions.get('count', cleaning_completed + graph_completed)
        quality_passed = executions.get('quality_passed', 'N/A')
        # Fallback to live metrics when workflow stage does not return token summary
        total_tokens = executions.get('total_tokens')
        if total_tokens is None:
            summary = workflow.get_workflow_summary()
            total_tokens = summary.get('metrics', {}).get('total_tokens_consumed', 0.0)

        print(f"\n  Task Executions:")
        print(f"    Total Executed: {total_executed}")
        print(f"    Quality Passed: {quality_passed}")
        print(f"    Total Tokens: {float(total_tokens):.2f}")

    # Factory status
    print_subsection("Step 5: Factory Status Snapshot")
    status = workflow.get_factory_status()
    print(f"  Overall Status: {status['factory_status']['overall_status']}")
    print(f"  Production Lines: {status['factory_status']['production_lines']}")
    print(f"  Active Tasks: {status['factory_status']['active_tasks']}")
    print(f"  Pending Tasks: {status['factory_status']['pending_tasks']}")

    metrics = status['factory_status'].get('metrics', {})
    print(f"\n  Factory Metrics:")
    print(f"    Total Tasks Completed: {metrics.get('total_tasks_completed')}")
    print(f"    Quality Rate: {metrics.get('quality_rate', 1.0):.2%}")
    print(f"    Total Tokens Consumed: {metrics.get('total_tokens_consumed', 0):.2f}")

    # Cost summary
    print_subsection("Step 6: Cost Analysis")
    cost_summary = workflow.get_worker_cost_summary()
    print(f"  Total Tokens: {cost_summary['total_tokens']:.2f}")
    print(f"  Average Cost per Item: {cost_summary['average_cost_per_item']:.4f}")

    for line_id, line_data in cost_summary.get('lines', {}).items():
        print(f"\n  Line: {line_data['line_name']}")
        print(f"    Tokens Used: {line_data['total_tokens']:.2f}")
        print(f"    Tasks Completed: {line_data['completed_tasks']}")
        print(f"    Cost per Item: {line_data['average_cost_per_item']:.4f}")
        print(f"    Utilization: {line_data['utilization']:.1%}")

    # Quality report
    if auto_execute:
        print_subsection("Step 7: Quality Inspection Report")
        quality_report = workflow.get_quality_report()
        print(f"  Report ID: {quality_report.get('report_id')}")
        print(f"  Total Checks: {quality_report.get('total_checks')}")
        print(f"  Passed: {quality_report.get('passed_checks')}")
        print(f"  Pass Rate: {quality_report.get('pass_rate', 0):.1%}")
        print(f"  Avg Quality Score: {quality_report.get('avg_quality_score', 1.0):.2f}")

    # Workflow summary
    print_subsection("Step 8: Complete Workflow Summary")
    workflow_summary = workflow.get_workflow_summary()

    print(f"  Factory: {workflow_summary['factory_name']}")
    print(f"  Status: {workflow_summary['factory_status']}")

    prod_lines = workflow_summary.get('production_lines', {})
    print(f"\n  Production Lines:")
    print(f"    Total: {prod_lines.get('total')}")
    print(f"    Running: {prod_lines.get('running')}")
    print(f"    Idle: {prod_lines.get('idle')}")

    work_orders = workflow_summary.get('work_orders', {})
    print(f"\n  Work Orders:")
    print(f"    Total: {work_orders.get('total')}")
    print(f"    Pending: {work_orders.get('pending')}")
    print(f"    In Progress: {work_orders.get('in_progress')}")
    print(f"    Completed: {work_orders.get('completed')}")

    # Completion summary
    print_section("Demonstration Complete", 80)
    print("\n✓ Factory demonstration workflow executed successfully!")
    print("\nGenerated Files:")
    print("  - database/factory.db (Factory state and operations)")
    print("\nNext Steps:")
    print("  1. View factory dashboard: python3 tools/factory_dashboard.py")
    print("  2. Query database: sqlite3 database/factory.db")
    print("  3. Export state: python3 -c \"from tools.factory_workflow import FactoryWorkflow; wf = FactoryWorkflow(); print(wf.export_state_to_json())\"")

    return workflow


def demo_multi_workflow() -> None:
    """Run multiple parallel workflows to demonstrate scalability"""
    print_section("Multi-Workflow Demonstration - Parallel Processing", 80)

    workflow = FactoryWorkflow(factory_name="Shanghai Data Factory")
    workflow.approve_all_required_gates(
        approver="demo-system",
        note="Auto approval for local demonstration"
    )
    scenarios = get_all_scenarios()

    print("\nRunning 3 parallel product requirements...\n")

    # Run multiple scenarios
    scenario_sequence = ['quick_test', 'address_cleaning', 'entity_fusion']

    for scenario_name in scenario_sequence:
        print(f"\n>>> Running scenario: {scenario_name}")
        scenario_func = scenarios[scenario_name]
        requirement = scenario_func()

        # Submit and execute
        workflow.submit_product_requirement(requirement)
        wf_result = workflow.create_production_workflow(requirement, auto_execute=True)

        print(f"    Status: {wf_result['status']}")
        print(f"    Workflow ID: {wf_result['workflow_id']}")

    # Print aggregated summary
    print_subsection("Aggregated Factory Summary")
    summary = workflow.get_workflow_summary()

    print(f"Total Production Lines: {summary['production_lines']['total']}")
    print(f"Total Work Orders: {summary['work_orders']['total']}")
    print(f"  - Completed: {summary['work_orders']['completed']}")
    print(f"  - In Progress: {summary['work_orders']['in_progress']}")

    print(f"\nFactory Metrics:")
    metrics = summary.get('metrics', {})
    print(f"  Quality Rate: {metrics.get('quality_rate', 1.0):.2%}")
    print(f"  Total Tokens: {metrics.get('total_tokens_consumed', 0):.2f}")
    print(f"  Avg Turnaround: {metrics.get('average_turnaround_minutes', 0):.1f}m")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Factory Demonstration Workflow")
        ensure_demo_allowed("scripts/factory_demo_workflow.py")
    parser.add_argument(
        '--scenario',
        choices=['address_cleaning', 'entity_fusion', 'relationship_extraction', 'quick_test'],
        default='address_cleaning',
        help='Scenario to run (default: address_cleaning)'
    )
    parser.add_argument(
        '--multi',
        action='store_true',
        help='Run multiple parallel workflows'
    )
    parser.add_argument(
        '--no-execute',
        action='store_true',
        help='Create workflow but do not auto-execute tasks'
    )

    args = parser.parse_args()

    if args.multi:
        demo_multi_workflow()
    else:
        demo_workflow(
            scenario_name=args.scenario,
            auto_execute=not args.no_execute
        )


if __name__ == '__main__':
    main()
