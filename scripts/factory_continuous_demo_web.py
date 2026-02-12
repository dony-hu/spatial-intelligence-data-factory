#!/usr/bin/env python3
"""
Factory Continuous Demo with Web Dashboard
两条产线流水线演示 - 带动态Web看板
"""

import sys
import time
import json
import random
import threading
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.factory_workflow import FactoryWorkflow
from tools.factory_framework import ProductRequirement, ProductType, generate_id
from tools.factory_web_server import app, factory_state

# Shanghai addresses
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

BUILDING_NUMBERS = list(range(1, 10001, 10))

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
    """从地址列表创建产品需求"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name=f'上海地址数据处理 - 批次 {len(addresses)}',
        product_type=ProductType.ADDRESS_TO_GRAPH,
        input_format='raw_addresses',
        output_format='graph_nodes_and_relationships',
        input_data=addresses,
        sla_metrics={
            'max_duration': 60,
            'quality_threshold': 0.90
        },
        priority=1
    )

def run_continuous_demo_web(total_addresses: int = 10000, demo_iterations: int = 1):
    """
    运行带Web看板的持续演示
    """
    print("\n" + "=" * 80)
    print("  🏭 数据工厂实时看板系统")
    print("  【两条产线流水线】")
    print("  产线 1: 地址清洗 (原始地址 -> 标准化地址)")
    print("  产线 2: 地址到图谱 (标准化地址 -> 图谱节点和关系)")
    print("=" * 80)
    print("\n📡 Web看板服务已启动: http://localhost:5000")
    print("   请在浏览器中打开上述地址查看实时运行状态\n")

    for iteration in range(1, demo_iterations + 1):
        print(f"\n{'='*80}")
        print(f"  演示迭代 #{iteration}/{demo_iterations}")
        print(f"{'='*80}\n")

        # 初始化工厂
        print("📋 Step 1: 初始化工厂系统和两条产线")
        workflow = FactoryWorkflow(
            factory_name=f"上海数据工厂 - 迭代 {iteration}",
            init_production_lines=True
        )
        workflow.approve_all_required_gates(
            approver="continuous-web-demo",
            note="Auto approval for local demonstration"
        )
        print("✓ 工厂系统和两条产线初始化完成\n")

        # 更新Web服务状态
        factory_state['factory_name'] = f"上海数据工厂 - 迭代 {iteration}"
        factory_state['start_time'] = datetime.now().isoformat()

        # 持续生成和处理数据
        print(f"📊 Step 2: 持续生成和处理 {total_addresses:,} 条地址数据\n")
        print(f"  处理速度: 1条/秒 (每条地址处理1秒)")
        print(f"  预计耗时: {total_addresses} 秒 (~{total_addresses//60} 分钟)\n")

        start_time = time.time()
        processed = 0

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

            # 每秒延迟 (使得每条地址处理需要1秒)
            time.sleep(1)

            # 实时更新Web服务状态
            if processed % 10 == 0:  # 每10条更新一次
                summary = workflow.get_workflow_summary()
                cost = workflow.get_worker_cost_summary()
                quality = workflow.get_quality_report()

                # 获取产线信息
                production_lines_info = {}
                for line_id, line in workflow.factory_state.production_lines.items():
                    production_lines_info[line_id] = {
                        'line_name': line.line_name,
                        'completed_tasks': line.completed_tasks,
                        'total_tokens_consumed': line.total_tokens_consumed,
                        'workers': len(line.workers)
                    }

                # 更新全局状态
                factory_state['production_lines'] = production_lines_info
                factory_state['work_orders'] = summary.get('work_orders', {})
                factory_state['metrics'] = {
                    'processed_count': processed,
                    'total_tokens': summary['metrics']['total_tokens_consumed'],
                    'quality_rate': quality.get('pass_rate', 0) if quality else 0
                }

            # 显示进度
            elapsed = time.time() - start_time
            if processed > 0:
                rate = processed / elapsed
                remaining = (total_addresses - processed) / rate if rate > 0 else 0
            else:
                remaining = 0

            percentage = (processed / total_addresses) * 100
            bar_length = 50
            filled = int(bar_length * processed / total_addresses)
            bar = '█' * filled + '░' * (bar_length - filled)

            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)

            print(f'\r  进度: [{bar}] {percentage:6.2f}% ({processed:,}/{total_addresses:,}) '
                  f'剩余: {hours:02d}:{minutes:02d}:{seconds:02d}', end='', flush=True)

        print()  # 换行

        # 最终统计
        total_time = time.time() - start_time
        print(f"\n✅ 数据处理完成！")
        print(f"  总耗时: {total_time:.1f} 秒")
        print(f"  处理速度: {processed/total_time:.2f} 条/秒")

        # 最终报告
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

    # 完成所有迭代
    print("\n" + "="*80)
    print("  🎉 所有演示迭代完成！")
    print("="*80 + "\n")

    print("看板已启动: http://localhost:5000")
    print("数据库位置: database/factory.db")
    print("\n按 Ctrl+C 停止服务器\n")

    # 保持Web服务运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✓ 服务器已停止")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Factory Continuous Demo with Web Dashboard")
    parser.add_argument(
        '--addresses',
        type=int,
        default=100,
        help='Total addresses to process (default: 100)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=1,
        help='Number of demo iterations (default: 1)'
    )

    args = parser.parse_args()

    # Start Flask web server in background thread
    web_thread = threading.Thread(
        target=lambda: app.run(debug=False, host='127.0.0.1', port=5000, threaded=True),
        daemon=True
    )
    web_thread.start()

    # Give the server time to start
    time.sleep(1)

    # Run the demo
    run_continuous_demo_web(
        total_addresses=args.addresses,
        demo_iterations=args.iterations
    )

if __name__ == '__main__':
    main()
