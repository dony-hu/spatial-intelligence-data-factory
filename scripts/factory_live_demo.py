#!/usr/bin/env python3
"""
Factory Live Demo with Real-time Web Dashboard
基于两条产线的实时演示系统
"""

import sys
import time
import random
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.factory_workflow import FactoryWorkflow
from tools.factory_framework import ProductRequirement, ProductType, generate_id
from tools.factory_simple_server import start_server, factory_state

# Shanghai data
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

def generate_address(addr_id: int) -> dict:
    """生成单个地址"""
    street = random.choice(SHANGHAI_STREETS)
    district = random.choice(SHANGHAI_DISTRICTS)
    building = random.choice(BUILDING_NUMBERS)
    return {
        'raw': f"{district}{street}{building}号",
        'source': f'demo_{addr_id}',
        'id': addr_id
    }

def create_requirement(address: dict) -> ProductRequirement:
    """创建产品需求"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name=f'上海地址处理',
        product_type=ProductType.ADDRESS_TO_GRAPH,
        input_format='raw_addresses',
        output_format='graph_nodes_and_relationships',
        input_data=[address],
        sla_metrics={'max_duration': 60, 'quality_threshold': 0.90},
        priority=1
    )

def run_live_demo(total_addresses: int = 100):
    """运行实时演示"""
    print("\n" + "=" * 80)
    print("  🏭 数据工厂实时演示系统")
    print("  【两条产线流水线】")
    print("=" * 80)
    print("\n📡 Web看板已启动: http://localhost:5000")
    print("   请在浏览器中打开上述链接查看实时运行效果\n")
    print(f"📊 开始处理 {total_addresses} 条地址")
    print(f"   速度: 1条/秒 (每条需要1秒处理)\n")

    # 初始化工厂
    workflow = FactoryWorkflow(
        factory_name="上海数据工厂",
        init_production_lines=True
    )

    # 初始化Web状态
    factory_state['factory_name'] = "上海数据工厂"
    factory_state['start_time'] = datetime.now().isoformat()

    start_time = time.time()
    
    # 逐条处理地址
    for addr_id in range(total_addresses):
        # 生成地址
        address = generate_address(addr_id)
        
        # 创建需求
        requirement = create_requirement(address)
        
        # 提交和执行
        try:
            workflow.submit_product_requirement(requirement)
            wf_result = workflow.create_production_workflow(requirement, auto_execute=True)
        except Exception as e:
            print(f"✗ 地址 {addr_id} 处理失败: {e}")
            continue

        # 每1秒处理一条
        time.sleep(1)

        # 实时更新Web状态（每条更新）
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

        # 更新全局Web状态
        factory_state['production_lines'] = production_lines_info
        factory_state['work_orders'] = summary.get('work_orders', {})
        factory_state['metrics'] = {
            'processed_count': addr_id + 1,
            'total_tokens': summary['metrics']['total_tokens_consumed'],
            'quality_rate': quality.get('pass_rate', 0) if quality else 0
        }

        # 显示进度
        progress = ((addr_id + 1) / total_addresses) * 100
        bar_filled = int(50 * (addr_id + 1) / total_addresses)
        bar = '█' * bar_filled + '░' * (50 - bar_filled)
        
        elapsed = time.time() - start_time
        if addr_id > 0:
            rate = (addr_id + 1) / elapsed
            remaining = (total_addresses - addr_id - 1) / rate
        else:
            remaining = total_addresses

        print(f'\r  [{bar}] {progress:5.1f}% ({addr_id+1}/{total_addresses}) '
              f'剩余: {int(remaining):3d}s', end='', flush=True)

    print()  # 换行
    
    # 最终统计
    total_time = time.time() - start_time
    print(f"\n✅ 演示完成！")
    print(f"   总耗时: {total_time:.1f} 秒")
    print(f"   处理速度: {total_addresses/total_time:.2f} 条/秒")

    # 最终报告
    summary = workflow.get_workflow_summary()
    cost = workflow.get_worker_cost_summary()
    quality = workflow.get_quality_report()

    print("\n" + "="*80)
    print("  📊 最终统计")
    print("="*80)
    print(f"\n生产线数: {summary['production_lines']['total']}")
    print(f"完成任务: {summary['work_orders']['completed']}")
    print(f"质检合格率: {summary['metrics']['quality_rate']:.1%}")
    print(f"总Tokens消耗: {summary['metrics']['total_tokens_consumed']:.2f}")

    print("\n📊 看板持续运行中...")
    print("   http://localhost:5000\n")
    print("   按 Ctrl+C 停止\n")

    # 保持看板运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✓ 演示已停止")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Factory Live Demo")
    parser.add_argument('--addresses', type=int, default=100,
                       help='Total addresses to process (default: 100)')
    args = parser.parse_args()

    # 启动Web服务器
    server, state = start_server(port=5000)
    time.sleep(0.5)

    # 运行演示
    try:
        run_live_demo(total_addresses=args.addresses)
    except KeyboardInterrupt:
        print("\n✓ 已停止")

if __name__ == '__main__':
    main()
