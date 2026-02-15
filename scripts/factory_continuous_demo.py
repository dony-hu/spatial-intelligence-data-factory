#!/usr/bin/env python3
"""
Factory Continuous Demo - 持续演示系统
两条产线流水线模式：
  产线1: 地址清洗 (原始地址 -> 标准化地址)
  产线2: 地址到图谱 (标准化地址 -> 图谱节点和关系)
持续生成地址数据，逐个处理，实时更新看板，完成后清理重新开始
"""

import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.factory_workflow import FactoryWorkflow
from tools.factory_framework import ProductRequirement, ProductType, generate_id
from tools.factory_dashboard import FactoryDashboard
from scripts._mode_guard import ensure_demo_allowed


# 上海地区的地址样本
SHANGHAI_STREETS = [
    "中山东一路", "中山东二路", "中山东三路", "中山西路",
    "南京东路", "南京西路", "南京中路",
    "陆家嘴环路", "陆家嘴东路", "陆家嘴西路",
    "淮海中路", "淮海西路", "淮海东路",
    "南京西路", "静安寺路", "南京北路",
    "四川北路", "四川南路",
    "延安东路", "延安西路", "延安中路",
]

SHANGHAI_DISTRICTS = [
    "黄浦区", "浦东新区", "徐汇区", "静安区",
    "虹口区", "杨浦区", "闵行区", "宝山区",
    "嘉定区", "奉贤区", "青浦区", "松江区"
]

BUILDING_NUMBERS = list(range(1, 10001, 10))  # 1, 11, 21, ..., 9991


def generate_address_batch(start_id: int, batch_size: int = 1) -> list:
    """生成一批地址数据"""
    addresses = []
    for i in range(batch_size):
        addr_id = start_id + i
        street = random.choice(SHANGHAI_STREETS)
        district = random.choice(SHANGHAI_DISTRICTS)
        building = random.choice(BUILDING_NUMBERS)

        address = {
            'raw': f"{district}{street}{building}号",
            'source': f'demo_batch_{addr_id}',
            'id': addr_id
        }
        addresses.append(address)

    return addresses


def create_product_requirement(addresses: list) -> ProductRequirement:
    """从地址列表创建产品需求 - 用于地址到图谱的流水线"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name=f'上海地址数据处理 - 批次 {len(addresses)}',
        product_type=ProductType.ADDRESS_TO_GRAPH,  # 改为地址到图谱
        input_format='raw_addresses',
        output_format='graph_nodes_and_relationships',  # 改为图谱输出
        input_data=addresses,
        sla_metrics={
            'max_duration': 60,
            'quality_threshold': 0.90
        },
        priority=1
    )


def print_progress(current: int, total: int, start_time: float):
    """打印进度条"""
    elapsed = time.time() - start_time
    if current > 0:
        rate = current / elapsed
        remaining = (total - current) / rate if rate > 0 else 0
    else:
        remaining = 0

    percentage = (current / total) * 100
    bar_length = 50
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)

    hours = int(remaining // 3600)
    minutes = int((remaining % 3600) // 60)
    seconds = int(remaining % 60)

    print(f'\r  处理进度: [{bar}] {percentage:6.2f}% ({current:,}/{total:,}) '
          f'剩余时间: {hours:02d}:{minutes:02d}:{seconds:02d}', end='', flush=True)


def run_continuous_demo(total_addresses: int = 10000, demo_iterations: int = 2):
    """
    运行持续演示

    Args:
        total_addresses: 总地址数量
        demo_iterations: 演示迭代次数
    """

    print("\n" + "=" * 80)
    print("  🏭 数据工厂持续演示系统")
    print("  【两条产线流水线】")
    print("  产线 1: 地址清洗 (原始地址 -> 标准化地址)")
    print("  产线 2: 地址到图谱 (标准化地址 -> 图谱节点和关系)")
    print("=" * 80)

    for iteration in range(1, demo_iterations + 1):
        print(f"\n\n{'='*80}")
        print(f"  演示迭代 #{iteration}/{demo_iterations}")
        print(f"{'='*80}\n")

        # 初始化工厂
        print("📋 Step 1: 初始化工厂系统和两条产线")
        workflow = FactoryWorkflow(factory_name=f"上海数据工厂 - 迭代 {iteration}", init_production_lines=True)
        workflow.approve_all_required_gates(
            approver="continuous-demo",
            note="Auto approval for local demonstration"
        )
        print("✓ 工厂系统和两条产线初始化完成\n")

        # 持续生成和处理数据
        print(f"📊 Step 2: 持续生成和处理 {total_addresses:,} 条地址数据\n")
        print(f"  处理速度: 1条/秒")
        print(f"  预计耗时: {total_addresses} 秒 (~{total_addresses//60} 分钟)\n")

        start_time = time.time()
        processed = 0
        last_update = 0
        update_interval = 100  # 每处理100条更新一次看板

        # 逐条处理地址
        for batch_start in range(0, total_addresses, 1):
            # 生成1条地址
            addresses = generate_address_batch(batch_start, batch_size=1)

            # 创建产品需求
            requirement = create_product_requirement(addresses)

            # 提交并执行
            try:
                workflow.submit_product_requirement(requirement)
                wf_result = workflow.create_production_workflow(requirement, auto_execute=True)
                processed += 1

            except Exception as e:
                print(f"\n✗ 处理地址 {batch_start} 失败: {e}")
                continue

            # 每处理100条地址更新一次看板和显示统计
            if processed % update_interval == 0:
                # 生成看板
                dashboard = FactoryDashboard(workflow)
                dashboard.generate_html_dashboard()

                # 显示统计
                summary = workflow.get_workflow_summary()
                cost = workflow.get_worker_cost_summary()

                print(f"\n  📈 当前统计 (已处理 {processed:,} 条):")
                print(f"     生产线: {summary['production_lines']['total']}")
                print(f"     完成任务: {summary['work_orders']['completed']}")
                print(f"     质检率: {summary['metrics']['quality_rate']:.1%}")
                print(f"     总成本: {summary['metrics']['total_tokens_consumed']:.2f} tokens")
                print(f"     看板已更新: output/factory_dashboard.html\n")

            # 显示进度
            print_progress(processed, total_addresses, start_time)

            # 延迟1秒处理下一条
            time.sleep(1)

        print()  # 换行

        # 最终统计
        total_time = time.time() - start_time
        print(f"\n✅ 数据处理完成！\n")
        print(f"  总耗时: {total_time:.1f} 秒")
        print(f"  处理速度: {processed/total_time:.2f} 条/秒")

        # 最终看板和统计
        print("\n" + "="*80)
        print("  📊 最终工厂状态")
        print("="*80 + "\n")

        summary = workflow.get_workflow_summary()
        cost = workflow.get_worker_cost_summary()
        quality = workflow.get_quality_report()

        print("工厂概览:")
        print(f"  工厂名称: {summary['factory_name']}")
        print(f"  运营状态: {summary['factory_status']}")

        print("\n生产线统计:")
        print(f"  总生产线数: {summary['production_lines']['total']}")
        print(f"  运行中: {summary['production_lines']['running']}")
        print(f"  空闲: {summary['production_lines']['idle']}")

        print("\n生产任务统计:")
        print(f"  总任务数: {summary['work_orders']['total']}")
        print(f"  完成: {summary['work_orders']['completed']}")
        print(f"  进行中: {summary['work_orders']['in_progress']}")
        print(f"  等待: {summary['work_orders']['pending']}")

        print("\n关键指标:")
        print(f"  质检合格率: {summary['metrics']['quality_rate']:.1%}")
        print(f"  总Tokens消耗: {summary['metrics']['total_tokens_consumed']:.2f}")
        print(f"  平均周期时间: {summary['metrics']['average_turnaround_minutes']:.1f} 分钟")

        print("\n成本分析:")
        print(f"  总Tokens消耗: {cost['total_tokens']:.2f}")
        print(f"  平均成本/项: {cost['average_cost_per_item']:.4f} tokens")

        print("\n质检分析:")
        print(f"  总检查: {quality['total_checks']}")
        print(f"  合格: {quality['passed_checks']}")
        print(f"  合格率: {quality['pass_rate']:.1%}")

        # 生成最终看板
        print("\n" + "="*80)
        print("  📊 生成最终看板")
        print("="*80 + "\n")

        dashboard = FactoryDashboard(workflow)
        dashboard_file = dashboard.generate_html_dashboard()
        print(f"✓ 看板已生成: {dashboard_file}")
        print(f"  打开方式: open {dashboard_file}\n")

        # 清理数据（如果不是最后一次迭代）
        if iteration < demo_iterations:
            print("="*80)
            print("  🧹 清理数据，准备下一次迭代")
            print("="*80 + "\n")

            import os
            import sqlite3

            db_path = "database/factory.db"
            if os.path.exists(db_path):
                # 清理数据库中的数据
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    tables = [
                        'factory_products',
                        'factory_processes',
                        'production_lines',
                        'workers',
                        'work_orders',
                        'task_executions',
                        'quality_checks',
                        'factory_metrics'
                    ]

                    for table in tables:
                        cursor.execute(f'DELETE FROM {table}')

                    conn.commit()
                    conn.close()
                    print("✓ 数据库已清理\n")
                except Exception as e:
                    print(f"✗ 清理数据库失败: {e}\n")

            # 等待5秒后开始下一次迭代
            print("⏳ 5秒后开始下一次迭代...\n")
            time.sleep(5)

    # 完成所有迭代
    print("\n" + "="*80)
    print("  🎉 所有演示迭代完成！")
    print("="*80 + "\n")

    print("最终输出文件:")
    print("  📄 database/factory.db - SQLite数据库")
    print("  📊 output/factory_dashboard.html - 交互式看板")
    print("  📄 README_FACTORY_DEMO.md - 完整文档\n")

    print("打开看板查看演示效果:")
    print("  open output/factory_dashboard.html\n")


def main():
    """主函数"""
    ensure_demo_allowed("scripts/factory_continuous_demo.py")
    import argparse

    parser = argparse.ArgumentParser(description="Factory Continuous Demo")
    parser.add_argument(
        '--addresses',
        type=int,
        default=10000,
        help='Total addresses to process (default: 10000)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=2,
        help='Number of demo iterations (default: 2)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: 100 addresses, 1 iteration, fast processing'
    )

    args = parser.parse_args()

    if args.quick:
        print("\n🚀 快速模式: 100条地址，1次迭代，快速处理\n")
        run_continuous_demo(total_addresses=100, demo_iterations=1)
    else:
        run_continuous_demo(
            total_addresses=args.addresses,
            demo_iterations=args.iterations
        )


if __name__ == '__main__':
    main()
