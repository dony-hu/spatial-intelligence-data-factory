# 数据工厂演示系统 - 基于Agent的制造工厂模型

## 🎯 系统概述

**数据工厂演示系统**是一个创新的、面向客户和销售的演示平台。它采用**真实制造工厂的运营模型**，通过多个Agent角色的协作，模拟数据处理流程，充分展示数据工厂的能力、灵活性和专业性。

### 核心概念

系统将数据处理过程隐喻为真实的制造工厂运营：

```
产品需求 → 工艺设计 → 生产线创建 → 任务执行 → 质量检验 → 成本统计
```

每个环节都由不同的Agent角色负责，实现真正的**多角色协作**和**职责分离**。

---

## 👥 5大工厂角色

### 1. 厂长 (Factory Director) - 👔
**职责：** 整体工厂运营和决策

- 接收新产品需求
- 评估需求可行性
- 制定生产计划
- 聚合工厂整体KPI和运营状态
- 生成运营建议

**示例行为：**
```
"需要1条生产线，3个工人，预期2小时完成"
```

### 2. 工艺专家 (Process Expert) - 🔧
**职责：** 工艺规范设计和优化

- 根据产品需求设计最优工艺规范
- 定义处理步骤（解析→标准化→验证等）
- 设置质量规则和资源需求
- 基于历史执行数据优化流程

**示例行为：**
```
设计工序: 地址解析 → 标准化 → 验证
每个地址预期耗时: 0.5分钟
```

### 3. 生产线组长 (Production Line Leader) - 👷
**职责：** 生产线创建、任务分配和进度监控

- 创建新的生产线并配置工人
- 分配任务到具体生产线
- 监控生产线运营状态
- 跟踪任务完成进度
- 管理工人资源

**示例行为：**
```
创建生产线 "地址清洗_线_1"
配置 3 个工人，最大处理 100 项/小时
```

### 4. 工人 (Worker) - 👨‍💼
**职责：** 执行具体的数据处理任务

- 按照工艺规范执行处理步骤
- 处理输入数据并产出结果
- 记录处理耗时和token消耗
- 报告质量指标

**示例行为：**
```
处理地址: "上海黄浦中山东路1号"
结果: "上海市黄浦区中山东一路1号"
耗时: 1.2秒, Token: 0.12
```

### 5. 质检员 (Quality Inspector) - ✅
**职责：** 质量控制和检验

- 验证任务输出质量
- 生成质检报告
- 识别不合格品
- 提出改进建议
- 统计整体质检率

**示例行为：**
```
检验结果: 合格 ✓
质量分数: 0.97 / 1.0
```

---

## 🏭 系统架构

```
┌──────────────────────────────────────────────┐
│       Factory Dashboard (HTML看板)            │
│  实时展示工厂运营状态和成本数据              │
└──────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────┐
│    Factory Workflow (工作流编排层)           │
│  管理完整的生产流程和任务分配                │
└──────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────┐
│         5-Role Agent System                  │
│  ┌─────────┬──────────┬────────┬────────┐    │
│  │ Director│  Expert  │ Leader │ Worker │    │
│  └─────────┴──────────┴────────┴────────┘    │
│         ↓                                     │
│    Inspector (质检员)                        │
│    (跨角色质量控制)                         │
└──────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────┐
│    SQLite Database (持久化层)                │
│    工厂状态、任务、成本、质检数据            │
└──────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
spatial-intelligence-data-factory/
├── tools/
│   ├── factory_framework.py      # 核心数据模型和框架
│   ├── factory_agents.py         # 5个Agent实现
│   ├── factory_workflow.py       # 工作流编排
│   ├── factory_dashboard.py      # HTML看板生成
│   ├── factory_integration.py    # 与现有系统集成
│   └── address_governance.py     # 现有地址治理模块（复用）
│
├── database/
│   ├── factory_db.py             # SQLite数据库层
│   ├── factory.db                # 工厂数据库文件
│   └── sqlite_adapter.py         # 现有SQLite适配器（复用）
│
├── testdata/
│   └── factory_demo_scenarios.py # 预定义演示场景
│
├── scripts/
│   ├── factory_demo_workflow.py  # 演示工作流脚本
│   └── factory_quickstart.sh     # 快速启动脚本
│
├── output/
│   └── factory_dashboard.html    # 生成的看板文件
│
└── docs/
    └── README_FACTORY_DEMO.md    # 本文档
```

---

## 🚀 快速开始

### 最简单的方法：快速启动脚本

```bash
# 使用默认场景 (quick_test)
bash scripts/factory_quickstart.sh

# 或指定特定场景
bash scripts/factory_quickstart.sh address_cleaning
bash scripts/factory_quickstart.sh entity_fusion
bash scripts/factory_quickstart.sh multi
```

### 手动执行演示工作流

```bash
# 快速测试场景（3个地址）
python3 scripts/factory_demo_workflow.py --scenario quick_test

# 地址清洗场景（10个地址）
python3 scripts/factory_demo_workflow.py --scenario address_cleaning

# 实体融合场景
python3 scripts/factory_demo_workflow.py --scenario entity_fusion

# 关系抽取场景
python3 scripts/factory_demo_workflow.py --scenario relationship_extraction

# 多工作流并行演示
python3 scripts/factory_demo_workflow.py --multi

# 只创建工作流不执行任务
python3 scripts/factory_demo_workflow.py --scenario quick_test --no-execute
```

### 生成工厂看板

```bash
# 生成HTML看板
python3 tools/factory_dashboard.py

# 输出: output/factory_dashboard.html
# 在浏览器中打开查看实时数据
open output/factory_dashboard.html
```

---

## 📊 演示场景详解

### 场景 1: 地址数据清洗 (address_cleaning)

**产品需求：** 清洗和标准化10个上海地址

**工艺流程：**
```
原始地址 → 解析 → 标准化 → 验证 → 标准化地址
```

**工人执行步骤：**
1. **解析阶段** - 分解地址为省市区街道
2. **标准化阶段** - 转换为标准格式
3. **验证阶段** - 检查数据完整性

**质检规则：**
- 精准度 ≥ 95%
- 完整性验证
- 格式一致性检查

**成本预测：** ~1.5 tokens / 地址

---

### 场景 2: 多源实体融合 (entity_fusion)

**产品需求：** 融合5个来自多个数据源的实体

**工艺流程：**
```
多源数据 → 解析 → 重复检测 → 融合 → 验证 → 融合实体
```

**工人执行步骤：**
1. **解析** - 理解多个数据源的格式
2. **融合** - 匹配和合并重复实体
3. **验证** - 质量检查

**质检规则：**
- 去重准确率 ≥ 92%
- 融合一致性 ≥ 95%

**成本预测：** ~2.0 tokens / 实体

---

### 场景 3: 关系抽取 (relationship_extraction)

**产品需求：** 从10个标准化地址抽取实体关系

**工艺流程：**
```
标准化地址 → 特征提取 → 关系识别 → 验证 → 关系图谱
```

**生产线指标：**
- 工人数：3
- 处理能力：每小时100条
- 预期耗时：120分钟

---

### 场景 4: 快速测试 (quick_test)

**产品需求：** 快速演示（3个地址）

**用途：** 演示系统功能和性能，验证完整工作流

**预期耗时：** < 2 分钟

---

## 💡 使用示例

### 示例 1: 程序化使用工厂系统

```python
from tools.factory_workflow import FactoryWorkflow
from testdata.factory_demo_scenarios import get_address_cleaning_scenario

# 初始化工厂
workflow = FactoryWorkflow(factory_name="My Data Factory")

# 提交产品需求
requirement = get_address_cleaning_scenario()
submission = workflow.submit_product_requirement(requirement)
print(f"Requirement ID: {submission['requirement_id']}")

# 创建并执行生产工作流
wf_result = workflow.create_production_workflow(requirement, auto_execute=True)
print(f"Workflow Status: {wf_result['status']}")

# 获取工厂状态
status = workflow.get_factory_status()
print(f"Factory Status: {status['factory_status']}")

# 获取成本汇总
cost_summary = workflow.get_worker_cost_summary()
print(f"Total Tokens: {cost_summary['total_tokens']}")

# 获取质检报告
quality_report = workflow.get_quality_report()
print(f"Quality Pass Rate: {quality_report['pass_rate']:.1%}")
```

### 示例 2: 创建自定义产品需求

```python
from tools.factory_framework import ProductRequirement, ProductType

requirement = ProductRequirement(
    requirement_id="custom_req_001",
    product_name="Custom Data Processing",
    product_type=ProductType.ADDRESS_CLEANING,
    input_format="raw_data",
    output_format="cleaned_data",
    input_data=[
        {"raw": "data_item_1"},
        {"raw": "data_item_2"},
        # ... more items
    ],
    sla_metrics={
        "max_duration": 60,      # 60 minutes
        "quality_threshold": 0.95  # 95% quality
    },
    priority=1
)

# 提交需求
workflow.submit_product_requirement(requirement)
```

### 示例 3: 查询数据库

```bash
# 连接到工厂数据库
sqlite3 database/factory.db

# 查看所有工作订单
SELECT * FROM work_orders;

# 查看任务执行记录
SELECT * FROM task_executions ORDER BY created_at DESC;

# 统计生产线成本
SELECT line_id, SUM(total_tokens_consumed) as total_tokens
FROM production_lines
GROUP BY line_id;

# 查看质检结果
SELECT COUNT(*) as total, SUM(passed) as passed
FROM quality_checks;

# 查看最新工厂指标
SELECT * FROM factory_metrics ORDER BY timestamp DESC LIMIT 1;
```

---

## 📈 看板功能详解

### 顶部概览 (KPI Summary)

- **总生产线数** - 当前活跃的生产线数量
- **已完成任务** - 完成的工作订单数
- **质检合格率** - 通过质检的比例
- **总Tokens消耗** - 累计成本

### 生产线状态面板

表格展示每条生产线的：
- 生产线ID和名称
- 分配的工人数
- 完成的任务数
- 资源利用率（百分比进度条）
- 平均质量分数
- 单位成本

### 质量指标

#### 质检合格率饼图
- 显示合格/不合格的比例
- 实时更新

#### 生产线成本柱状图
- 对比各生产线的token消耗
- 识别高成本生产线

#### 成本趋势曲线
- 展示全天成本累积趋势
- 预测运营成本

### 工厂角色表

展示5个工厂角色的职责和运行状态：
- 厂长 - 整体运营
- 工艺专家 - 流程优化
- 生产线组长 - 线管理
- 工人 - 任务执行
- 质检员 - 质量控制

---

## 🔧 深入理解：Agent协作流程

### 完整工作流例子

假设客户需要清洗50个地址：

```
1. 提交需求
   客户: "我需要清洗50个地址数据"

   ↓

2. 厂长评估 (Director)
   - 评估需求可行性
   - 估算: 1条生产线, 3个工人, 120分钟

   ↓

3. 工艺专家设计 (Expert)
   - 设计工艺: 解析 → 标准化 → 验证
   - 定义质量规则: 精准度≥95%

   ↓

4. 组长创建生产线 (Leader)
   - 创建生产线 "地址清洗_线_1"
   - 分配3个工人

   ↓

5. 工人执行任务 (Workers)
   - 工人1: 处理地址1-17
   - 工人2: 处理地址18-33
   - 工人3: 处理地址34-50
   - 并行执行，记录token消耗

   ↓

6. 质检验证 (Inspector)
   - 逐个检验输出结果
   - 计算质量分数
   - 标记不合格品

   ↓

7. 成果交付
   - 标准化地址列表
   - 质检报告
   - 成本统计
```

### Token消耗追踪

每个Worker任务都精确记录：
```python
execution = {
    'execution_id': 'exec_xxx',
    'worker_id': 'worker_001',
    'process_step': 'standardization',
    'token_consumed': 0.15,  # 精确到小数点后两位
    'duration_minutes': 1.2,
    'quality_score': 0.97
}
```

---

## 🎓 扩展和定制

### 添加新的演示场景

1. 在 `testdata/factory_demo_scenarios.py` 中添加函数：

```python
def get_my_custom_scenario():
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name='My Custom Product',
        product_type=ProductType.CUSTOM,
        input_data=[...],
        sla_metrics={...}
    )
```

2. 注册到 `get_all_scenarios()`:

```python
def get_all_scenarios():
    return {
        'address_cleaning': get_address_cleaning_scenario,
        'my_custom': get_my_custom_scenario,  # 新增
        ...
    }
```

3. 运行演示：
```bash
python3 scripts/factory_demo_workflow.py --scenario my_custom
```

### 自定义工艺流程

在 `ProcessExpert.design_process()` 中修改处理步骤：

```python
# 当前
steps = [ProcessStep.PARSING, ProcessStep.STANDARDIZATION, ProcessStep.VALIDATION]

# 修改为
steps = [
    ProcessStep.PARSING,
    ProcessStep.EXTRACTION,      # 新增
    ProcessStep.VALIDATION,
    ProcessStep.QUALITY_CHECK    # 新增
]
```

### 集成现有系统

工厂系统可以与现有的数据治理模块集成：

```python
from tools.address_governance import AddressGovernanceSystem

# 在Worker.execute_task中
address_gov = AddressGovernanceSystem()
result = address_gov.process_address(input_data)
```

---

## 📊 数据库架构

### 核心表

| 表名 | 用途 | 主要字段 |
|-----|------|--------|
| factory_products | 产品定义 | requirement_id, product_name, product_type, input_data_count |
| factory_processes | 工艺规范 | process_id, steps, estimated_duration, quality_rules |
| production_lines | 生产线 | line_id, status, active_tasks, total_tokens_consumed |
| workers | 工人配置 | worker_id, line_id, capability_level, tokens_consumed |
| work_orders | 生产任务 | work_order_id, status, assigned_line_id, priority |
| task_executions | 任务执行 | execution_id, worker_id, token_consumed, quality_score |
| quality_checks | 质检结果 | check_id, quality_score, passed, issues |
| factory_metrics | KPI指标 | timestamp, quality_rate, total_tokens, active_lines |

### 查询示例

```sql
-- 按生产线统计成本
SELECT line_id, SUM(total_tokens_consumed) FROM production_lines GROUP BY line_id;

-- 查看质检通过率
SELECT CAST(SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) as FLOAT) / COUNT(*)
FROM quality_checks;

-- 找出成本最高的任务
SELECT execution_id, token_consumed FROM task_executions
ORDER BY token_consumed DESC LIMIT 10;
```

---

## 🎯 演示技巧和最佳实践

### 给客户演示时

1. **从小到大演示**
   - 先运行 `quick_test` 快速展示完整流程 (< 2 分钟)
   - 再运行 `address_cleaning` 展示更复杂的场景 (< 5 分钟)
   - 最后运行 `--multi` 展示平行处理能力

2. **强调关键特性**
   - 多角色协作和职责明确
   - 实时成本追踪（token消耗）
   - 自动化质量控制
   - 灵活的工艺设计能力

3. **用数据说话**
   - "该工作流处理了50个地址，质检合格率95.2%，成本0.072 tokens/项"
   - "看板实时显示了每条生产线的利用率、成本和质量"

### 自定义演示

创建符合客户业务的演示数据：

```python
# 假设客户是电商平台
customer_scenario = ProductRequirement(
    product_name="电商订单地址标准化",
    input_data=[
        {"raw": "收货地址1", "customer_id": "cust_001"},
        # ...
    ],
    sla_metrics={
        "max_duration": 60,
        "quality_threshold": 0.99,  # 电商需要99%准确率
        "delivery_guarantee": True
    }
)
```

---

## 🔍 故障排除

### 问题 1: "ModuleNotFoundError: No module named 'tools'"

**解决方案：** 确保在项目根目录运行脚本
```bash
cd /path/to/spatial-intelligence-data-factory
python3 scripts/factory_demo_workflow.py
```

### 问题 2: SQLite数据库锁定

**解决方案：** 数据库正在被另一个进程访问，等待或重启应用
```bash
# 检查数据库文件
ls -l database/factory.db

# 如需重置数据库
rm database/factory.db
python3 scripts/factory_demo_workflow.py
```

### 问题 3: 看板HTML在浏览器无法显示

**解决方案：** 确保有网络连接以加载CDN资源（Chart.js, Bootstrap）
- 或使用绝对路径打开：`open file://$(pwd)/output/factory_dashboard.html`

---

## 📚 进阶主题

### 性能优化

```python
# 增加工人数量加快处理
worker_count = 10  # 从3增加到10

# 分布式执行（future enhancement）
# workflow.create_production_workflow(requirement, auto_execute=True, distributed=True)
```

### 监控和告警

```python
# 当质检率低于阈值时告警
if quality_report['pass_rate'] < 0.90:
    send_alert("Quality drop detected!")

# 当成本超过预算时告警
if cost_summary['total_tokens'] > budget:
    send_alert("Cost exceed budget!")
```

### 历史分析

```python
# 分析过去一周的趋势
import sqlite3
conn = sqlite3.connect('database/factory.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT DATE(timestamp), AVG(quality_rate), SUM(total_tokens)
    FROM factory_metrics
    WHERE timestamp > datetime('now', '-7 days')
    GROUP BY DATE(timestamp)
""")

for date, avg_quality, total_tokens in cursor:
    print(f"{date}: Quality={avg_quality:.1%}, Cost={total_tokens:.2f}")
```

---

## 🤝 与现有系统的集成

### 地址治理模块集成

工厂系统可以复用现有的地址治理功能：

```python
from tools.address_governance import AddressGovernanceSystem

# Worker可以调用地址治理系统
class Worker(FactoryAgent):
    def __init__(self):
        self.address_gov = AddressGovernanceSystem()

    def execute_task(self, requirement):
        result = self.address_gov.process_address(requirement)
        # ... 继续处理
```

### 关系图谱集成

完成的任务可以导入到关系图谱系统：

```python
from tools.spatial_entity_graph import SpatialEntityGraph

# 从工厂执行结果生成实体关系图
graph = SpatialEntityGraph("Shanghai")
for task_result in task_results:
    graph.add_node_from_execution(task_result)
```

---

## 📞 支持和反馈

### 常见问题

**Q: 演示需要多长时间？**
A: 快速测试 < 2分钟，完整演示 3-5分钟

**Q: 可以处理多大的数据量？**
A: 当前演示系统设计用于中等规模（100-1000项数据）。大规模数据处理需要分布式架构。

**Q: 可以定制演示场景吗？**
A: 完全可以。参考 "扩展和定制" 部分添加自己的场景。

**Q: 成本数据是真实的吗？**
A: 是的，token消耗基于真实的数据处理复杂度估算。

---

## 📄 许可证和贡献

本项目是 `spatial-intelligence-data-factory` 的一部分。

---

**最后更新：** 2026-02-11
**版本：** 1.0.0
**状态：** ✅ 生产就绪

🎉 **享受数据工厂的神奇之处吧！**
