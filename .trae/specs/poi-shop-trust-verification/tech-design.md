# 沿街商铺 POI 可信度验证 - 技术设计文档

## 1. 架构设计

### 1.1 整体流程

```
用户自然语言请求
    ↓
工厂 CLI (packages/factory_cli/)
    ↓
工厂 Agent (packages/factory_agent/)
    ↓
可信数据 HUB (packages/trust_hub/) - 存储 API Key
    ↓
生成治理工作流 (workpackages/)
    ↓
治理产线执行工作流
```

### 1.2 模块划分

| 模块 | 职责 | 文件 |
|---|---|---|
| 工厂 CLI | 用户交互、解析自然语言请求 | `packages/factory_cli/` |
| 工厂 Agent | 智能对话、生成工作流 | `packages/factory_agent/` |
| 可信数据 HUB | 管理外部数据源 API Key | `packages/trust_hub/` |
| 治理 Runtime | 加载和执行工作流 | `packages/governance_runtime/` |

---

## 2. 接口设计

### 2.1 工厂 CLI 接口

**入口文件**: `scripts/factory_cli.py`

| 子命令 | 说明 |
|---|---|
| `poi-verify` | 沿街商铺 POI 可信度验证（对话式） |
| `generate` | 生成治理脚本（已有） |
| `list-skills` | 列出技能（已有） |

### 2.2 工厂 Agent 接口

**文件**: `packages/factory_agent/agent.py`

| 方法 | 说明 |
|---|---|
| `converse(prompt)` | 对话交互 |
| `determine_data_sources(prompt)` | 确定 2~3 家可信数据源 |
| `generate_workflow(data_sources)` | 生成治理工作流 |
| `output_skill(skill_name, spec)` | 输出技能包（已有） |

### 2.3 可信数据 HUB 接口

**新建文件**: `packages/trust_hub/__init__.py`

| 方法 | 说明 |
|---|---|
| `store_api_key(source, api_key)` | 存储数据源 API Key |
| `get_api_key(source)` | 获取数据源 API Key |
| `list_sources()` | 列出已配置的数据源 |

---

## 3. 数据结构设计

### 3.1 外部数据源配置

```python
# packages/trust_hub/__init__.py

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class DataSource:
    name: str           # 数据源名称，例如 "高德"、"百度"
    provider: str       # 提供商
    api_key: str        # API Key
    api_endpoint: str   # API 端点
    is_active: bool = True

class TrustHub:
    def __init__(self):
        self._sources: Dict[str, DataSource] = {}
    
    def store_api_key(self, name: str, api_key: str, provider: str = "", api_endpoint: str = ""):
        source = DataSource(
            name=name,
            provider=provider,
            api_key=api_key,
            api_endpoint=api_endpoint
        )
        self._sources[name] = source
    
    def get_api_key(self, name: str) -&gt; Optional[str]:
        source = self._sources.get(name)
        return source.api_key if source else None
    
    def list_sources(self) -&gt; List[str]:
        return list(self._sources.keys())
```

### 3.2 治理工作流 Schema

复用现有的 `contracts/workpackage.schema.json`

---

## 4. 实施步骤

### Phase 1: 可信数据 HUB 基础实现
1. 创建 `packages/trust_hub/` 目录
2. 实现 `TrustHub` 类和 `DataSource` 数据类
3. 简单的内存存储（后续可扩展到 SQLite/PG）

### Phase 2: 工厂 CLI 增强
1. 在 `scripts/factory_cli.py` 中新增 `poi-verify` 子命令
2. 实现对话式交互流程
3. 集成工厂 Agent 和可信数据 HUB

### Phase 3: 工厂 Agent 增强
1. 在 `packages/factory_agent/agent.py` 中新增数据源确定逻辑
2. 新增工作流生成逻辑
3. 集成可信数据 HUB 调用

### Phase 4: 端到端测试
1. 实现测试程序与工厂 Agent 的智能对话
2. 运行完整端到端流程
3. 验证观测项（workpackage 内容由 Agent 生成）

---

## 5. 约束与观测项验证

| 项 | 验证方式 |
|---|---|
| 约束：不直接修改 workpackage | 通过 Git 历史检查，workpackage 中所有变更均由工厂 Agent 生成 |
| 观测项：workpackage 由 Agent 生成 | 检查生成的工作流文件的元数据或日志 |

---

**技术设计完成！请确认后再开工！**
