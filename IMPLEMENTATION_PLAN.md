# 折中方案落地实施计划

## 📋 项目概览

**目标**：改进当前自建Agent框架，引入Tool Registry + 状态机 + 标准化接口

**时间**：1-2周（4个Phase，每个2-3天）

**产出**：
- agent_server.py: 1300行 → 400行（精简核心逻辑）
- agent_framework/: 新增~650行（框架代码）
- process_tools/: 新增~500行（转换现有工具）
- 完整的文档和测试

**ProcessCompiler**：保持完全不变

---

## 🎬 Phase 1: 建立Agent框架基础（2天）

### 目标
建立标准的Tool接口和Tool Registry，为后续工具转换做准备。

### 工作清单

#### 任务 1.1: 创建 tools/agent_framework/ 目录结构
```bash
tools/agent_framework/
├── __init__.py
├── tool_interface.py      # Tool标准接口
├── tool_registry.py       # Tool注册表
├── state_machine.py       # 会话状态机
├── request_response.py    # 标准请求/响应格式
└── error_handler.py       # 错误处理和重试
```

#### 任务 1.2: 实现 tool_interface.py (~150行)
- Tool基类定义
- Tool协议（Protocol）
- input_schema定义
- validate() 和 execute() 接口

代码框架：
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ToolSchema:
    """工具参数schema"""
    type: str = "object"
    properties: Dict[str, Any] = None
    required: list = None

class BaseTool(ABC):
    """所有工具的基类"""
    name: str
    description: str
    input_schema: ToolSchema

    @abstractmethod
    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[list]]:
        """返回(是否有效, 错误列表)"""
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """执行工具"""
        pass
```

#### 任务 1.3: 实现 tool_registry.py (~200行)
- ToolRegistry 类
- register() 方法
- execute() 方法
- 工具管理逻辑

#### 任务 1.4: 实现 state_machine.py (~150行)
- ChatState 枚举定义
- SessionState 数据类
- StateTransition 状态转移验证
- 状态转移规则

代码框架：
```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict

class ChatState(Enum):
    """会话状态"""
    NORMAL = "normal"                          # 正常对话
    PENDING_CONFIRMATION = "pending_confirmation"  # 等待确认
    EXECUTING = "executing"                   # 执行中
    ERROR = "error"                           # 错误

@dataclass
class SessionState:
    """会话状态对象"""
    session_id: str
    current_state: ChatState = ChatState.NORMAL
    message_history: List[Dict] = field(default_factory=list)
    pending_operation: Optional[Dict] = None
    draft_id: Optional[str] = None

    def transition_to(self, new_state: ChatState) -> bool:
        """转移到新状态"""
        # 验证转移合法性
        # 更新状态
        pass
```

#### 任务 1.5: 实现 request_response.py (~80行)
- ToolRequest 数据类
- ToolResponse 数据类
- 标准化的请求/响应格式

#### 任务 1.6: 实现 error_handler.py (~80行)
- 错误分类
- 重试逻辑
- 降级策略
- LLM调用失败处理

### 验收标准
- [ ] 所有文件创建完成
- [ ] 代码无语法错误
- [ ] 基本的单元测试通过
- [ ] 可以 import agent_framework

---

## 🔧 Phase 2: 转换现有工具（2-3天）

### 目标
将当前在 agent_server.py 中的工具逻辑转换为标准的 Tool 类。

### 工作清单

#### 任务 2.1: 创建 tools/process_tools/ 目录
```bash
tools/process_tools/
├── __init__.py
├── design_tool.py        # DesignProcessTool + ModifyProcessTool
├── publish_tool.py       # PublishDraftTool
├── compile_tool.py       # CompileProcessTool
├── query_tools.py        # QueryProcessTool等
└── db_tools.py           # 数据库操作工具
```

#### 任务 2.2: 实现 design_tool.py (~150行)

```python
from tools.agent_framework.tool_interface import BaseTool, ToolSchema
from typing import Dict, Any, Optional, Tuple

class DesignProcessTool(BaseTool):
    """设计工艺工具"""
    name = "design_process"
    description = "设计新工艺"

    input_schema = ToolSchema(
        properties={
            "requirement": {
                "type": "string",
                "description": "工艺需求描述"
            },
            "process_code": {
                "type": "string",
                "description": "工艺编码（可选，会自动生成）"
            },
            "process_name": {
                "type": "string",
                "description": "工艺名称"
            },
            "domain": {
                "type": "string",
                "enum": ["address_governance", "graph_modeling", "verification"],
                "description": "工艺领域"
            },
            "goal": {
                "type": "string",
                "description": "工艺目标"
            }
        },
        required=["requirement"]
    )

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[list]]:
        """验证参数"""
        errors = []
        if not params.get("requirement"):
            errors.append("缺少必填字段: requirement")
        if params.get("domain") and params["domain"] not in ["address_governance", "graph_modeling", "verification"]:
            errors.append(f"无效的domain: {params['domain']}")
        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """执行设计工艺"""
        from tools.agent_server import _create_design_draft

        result = _create_design_draft(
            requirement=params.get("requirement"),
            process_code=params.get("process_code", ""),
            process_name=params.get("process_name", ""),
            domain=params.get("domain", "address_governance"),
            goal=params.get("goal", ""),
            session_id=session_id,
        )
        return result

class ModifyProcessTool(BaseTool):
    """修改工艺工具"""
    name = "modify_process"
    description = "修改现有工艺"
    # ... 类似实现
```

#### 任务 2.3: 实现 publish_tool.py (~80行)

```python
class PublishDraftTool(BaseTool):
    """发布草案工具"""
    name = "publish_draft"
    description = "发布工艺草案为版本"

    input_schema = ToolSchema(
        properties={
            "draft_id": {
                "type": "string",
                "description": "草案ID"
            }
        },
        required=["draft_id"]
    )

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[list]]:
        errors = []
        if not params.get("draft_id"):
            errors.append("缺少必填字段: draft_id")
        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        from tools.agent_server import _publish_draft
        return _publish_draft(params.get("draft_id"))
```

#### 任务 2.4: 实现 compile_tool.py (~80行)

```python
class CompileProcessTool(BaseTool):
    """编译工艺工具"""
    name = "compile_process"
    description = "编译工艺规范和生成工具脚本"

    input_schema = ToolSchema(
        properties={
            "draft": {
                "type": "object",
                "description": "工艺草案对象"
            }
        },
        required=["draft"]
    )

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[list]]:
        errors = []
        if not params.get("draft"):
            errors.append("缺少必填字段: draft")
        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        from tools.process_compiler import ProcessCompiler
        compiler = ProcessCompiler()
        result = compiler.compile(params.get("draft"), session_id=session_id)
        return {
            "status": "ok" if result.success else "error",
            "success": result.success,
            "process_code": result.process_code,
            "execution_readiness": result.execution_readiness,
            "tool_metadata": result.tool_metadata,
            "validation_errors": result.validation_errors,
        }
```

#### 任务 2.5: 实现 __init__.py

```python
from .design_tool import DesignProcessTool, ModifyProcessTool
from .publish_tool import PublishDraftTool
from .compile_tool import CompileProcessTool
from .query_tools import QueryProcessTool, QueryVersionTool
from .db_tools import CreateProcessTool, CreateVersionTool

__all__ = [
    "DesignProcessTool",
    "ModifyProcessTool",
    "PublishDraftTool",
    "CompileProcessTool",
    "QueryProcessTool",
    "QueryVersionTool",
    "CreateProcessTool",
    "CreateVersionTool",
]
```

### 验收标准
- [ ] 所有工具类创建完成
- [ ] 每个工具都实现了 validate() 和 execute()
- [ ] schema 定义完整准确
- [ ] 可以正常import所有工具

---

## 🔗 Phase 3: 改进 agent_server.py（2-3天）

### 目标
精简 agent_server.py，使用 Tool Registry 管理工具调用，集成状态机。

### 工作清单

#### 任务 3.1: 导入新框架和工具

在 agent_server.py 顶部添加：
```python
from tools.agent_framework.tool_registry import ToolRegistry, ToolRequest, ToolResponse
from tools.agent_framework.state_machine import SessionState, ChatState
from tools.agent_framework.error_handler import ErrorHandler
from tools.process_tools import (
    DesignProcessTool,
    ModifyProcessTool,
    PublishDraftTool,
    CompileProcessTool,
    QueryProcessTool,
    # ... 其他工具
)
```

#### 任务 3.2: 初始化工具注册表

```python
# 全局工具注册表
tool_registry = ToolRegistry()

# 注册工具
tool_registry.register(DesignProcessTool(), ["design_process", "modify_process"])
tool_registry.register(PublishDraftTool(), ["publish_draft"])
tool_registry.register(CompileProcessTool(), ["compile_process"])
tool_registry.register(QueryProcessTool(), ["query_process"])
# ... 注册其他工具

# 全局会话状态管理
session_states: Dict[str, SessionState] = {}

def _get_or_create_session(session_id: str) -> SessionState:
    """获取或创建会话状态"""
    if session_id not in session_states:
        session_states[session_id] = SessionState(session_id=session_id)
    return session_states[session_id]
```

#### 任务 3.3: 改进核心对话函数 - _run_process_expert_chat_turn()

精简从 ~150行 降到 ~60行：

```python
def _run_process_expert_chat_turn(session_id: str, user_message: str) -> Dict[str, Any]:
    """运行工艺专家的对话轮次（改进版）"""

    # 获取或创建会话状态
    session_state = _get_or_create_session(session_id)
    session_state.add_message("user", user_message)

    # 检查待确认操作
    if session_state.current_state == ChatState.PENDING_CONFIRMATION:
        if _is_confirmation_message(user_message):
            # 执行待确认的操作
            pending_op = session_state.pending_operation
            tool_request = ToolRequest(
                name=pending_op["intent"],
                params=pending_op["params"],
                session_id=session_id
            )
            tool_response = tool_registry.execute(tool_request)

            # 记录日志
            runtime_store.append_process_chat_turn(
                session_id=session_id,
                role="assistant",
                content=f"已执行操作: {pending_op['intent']}"
            )

            session_state.transition_to(ChatState.NORMAL)
            session_state.clear_pending_operation()

            return {
                "status": "ok",
                "session_id": session_id,
                "tool_result": tool_response.to_dict(),
            }

    # LLM 解析意图
    llm_result = _call_llm_with_intent_parsing(user_message, session_state)
    intent = llm_result.get("intent", "chat")
    params = llm_result.get("params", {})

    # 执行工具（通过 registry）
    if tool_registry.get_tool_by_intent(intent):
        tool_request = ToolRequest(
            name=intent,
            params=params,
            session_id=session_id
        )
        tool_response = tool_registry.execute(tool_request)

        # 记录到数据库
        runtime_store.append_process_chat_turn(
            session_id=session_id,
            role="assistant",
            content=f"执行了 {intent}",
        )

        # 更新会话状态
        if tool_response.status == "ok":
            session_state.transition_to(ChatState.NORMAL)
        else:
            session_state.transition_to(ChatState.ERROR)
            session_state.last_error = tool_response.error

        return {
            "status": tool_response.status,
            "session_id": session_id,
            "tool_result": tool_response.to_dict(),
        }
    else:
        # 普通对话
        assistant_reply = llm_result.get("assistant_reply", "")
        session_state.add_message("assistant", assistant_reply)
        runtime_store.append_process_chat_turn(
            session_id=session_id,
            role="assistant",
            content=assistant_reply,
        )
        return {
            "status": "ok",
            "session_id": session_id,
            "assistant_message": assistant_reply,
        }
```

#### 任务 3.4: 简化 _execute_process_expert_intent()

**删除**这个函数中的所有 if-elif，因为 Tool Registry 已经处理路由。

保留原函数用于向后兼容，但实现改为调用 Tool Registry：

```python
def _execute_process_expert_intent(intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """向后兼容的工具执行接口"""
    tool_request = ToolRequest(
        name=intent,
        params=params,
        session_id=None
    )
    tool_response = tool_registry.execute(tool_request)
    return tool_response.to_dict()
```

#### 任务 3.5: 移除不需要的全局变量

**删除**：
```python
# 这些现在由 Tool Registry 和 SessionState 管理
process_design_drafts: Dict[str, Dict[str, Any]] = {}  # 删除，用Tool执行结果返回
process_chat_sessions: Dict[str, List[Dict[str, str]]] = {}  # 删除，用SessionState
process_chat_pending_ops: Dict[str, Dict[str, Any]] = {}  # 删除，用SessionState.pending_operation
```

保留：
```python
session_states: Dict[str, SessionState] = {}  # 使用新的状态管理
tool_registry = ToolRegistry()  # 工具注册表
```

#### 任务 3.6: 清理和优化代码

- 删除重复代码
- 提取公共逻辑
- 添加类型注解
- 更新文档字符串

### 验收标准
- [ ] agent_server.py 从 1300行 降到 ~400行
- [ ] 所有工具调用都通过 Tool Registry
- [ ] 状态机正确运作
- [ ] 功能完全保持一致（无行为变化）
- [ ] 单元测试通过

---

## ✅ Phase 4: 测试和文档（2-3天）

### 目标
验证改进方案的正确性，编写完整文档。

### 工作清单

#### 任务 4.1: 单元测试

创建 tests/test_agent_framework.py：
```python
import pytest
from tools.agent_framework.tool_registry import ToolRegistry, ToolRequest
from tools.agent_framework.state_machine import ChatState, SessionState
from tools.process_tools import DesignProcessTool

def test_tool_registry_register():
    """测试工具注册"""
    registry = ToolRegistry()
    tool = DesignProcessTool()
    registry.register(tool, ["design_process"])
    assert registry.get_tool_by_intent("design_process") is not None

def test_state_machine_transitions():
    """测试状态转移"""
    state = SessionState(session_id="test_1")
    assert state.current_state == ChatState.NORMAL
    assert state.transition_to(ChatState.PENDING_CONFIRMATION)
    assert state.current_state == ChatState.PENDING_CONFIRMATION

def test_tool_request_response():
    """测试工具请求/响应"""
    registry = ToolRegistry()
    registry.register(DesignProcessTool(), ["design_process"])

    request = ToolRequest(
        name="design_process",
        params={
            "requirement": "测试需求",
            "process_name": "测试工艺"
        }
    )

    response = registry.execute(request)
    assert response.status in ["ok", "error", "validation_error"]
```

#### 任务 4.2: 集成测试

创建 tests/test_agent_server_improved.py：
```python
def test_complete_workflow():
    """测试完整工作流：设计 → 编译 → 发布"""
    # 1. 设计工艺
    # 2. 编译工艺
    # 3. 发布工艺
    # 4. 验证结果
    pass

def test_state_transitions():
    """测试对话状态转移"""
    # 测试 NORMAL → PENDING_CONFIRMATION → NORMAL
    # 测试 ERROR 处理
    pass

def test_error_recovery():
    """测试错误恢复"""
    # 测试 LLM 调用失败的重试
    # 测试参数校验失败的处理
    pass
```

#### 任务 4.3: 更新现有测试

检查现有测试是否需要适配新的API。

#### 任务 4.4: 编写文档

创建 docs/AGENT_FRAMEWORK_GUIDE.md：

```markdown
# Agent框架使用指南

## 1. 添加新工具

### 步骤1：创建Tool类

在 tools/process_tools/ 中创建新文件：

\`\`\`python
from tools.agent_framework.tool_interface import BaseTool, ToolSchema

class MyNewTool(BaseTool):
    name = "my_new_tool"
    description = "我的新工具"

    input_schema = ToolSchema(
        properties={
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        required=["param1"]
    )

    def validate(self, params):
        # 验证参数
        pass

    def execute(self, params, session_id=None):
        # 执行逻辑
        return {"status": "ok", "result": {...}}
\`\`\`

### 步骤2：导出工具

在 tools/process_tools/__init__.py 中添加：
\`\`\`python
from .my_tool import MyNewTool

__all__ = [..., "MyNewTool"]
\`\`\`

### 步骤3：注册工具

在 tools/agent_server.py 中添加：
\`\`\`python
tool_registry.register(MyNewTool(), ["my_new_tool"])
\`\`\`

就这样！无需改其他地方。

## 2. 理解状态机

\`\`\`
NORMAL ← → PENDING_CONFIRMATION
  ↓               ↓
ERROR ← ←  ← ← ←
\`\`\`

- NORMAL: 正常对话
- PENDING_CONFIRMATION: 等待用户确认
- EXECUTING: 执行工具中
- ERROR: 发生错误

## 3. ProcessCompiler集成

ProcessCompiler 作为 compile_process_tool 使用，无需改动。

---
```

#### 任务 4.5: 验收清单

运行完整的验收：
```bash
# 1. 运行所有测试
pytest tests/ -v

# 2. 检查代码质量
pylint tools/agent_framework/
pylint tools/process_tools/

# 3. 检查导入
python -c "from tools.agent_framework import *; from tools.process_tools import *"

# 4. 启动服务并测试
python scripts/agent_server.py

# 5. 在UI中测试完整流程
#   - 设计工艺
#   - 编译工艺
#   - 发布工艺
```

### 验收标准
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 代码质量检查通过
- [ ] 文档完整清晰
- [ ] UI功能完全保持
- [ ] 性能无明显下降

---

## 📊 完整的工作量统计

| Phase | 名称 | 天数 | 输出 | 状态 |
|-------|------|------|------|------|
| 1 | Agent框架基础 | 2 | 650行代码 | 待启动 |
| 2 | 工具转换 | 2-3 | 500行代码 | 待启动 |
| 3 | agent_server改进 | 2-3 | agent_server精简 | 待启动 |
| 4 | 测试和文档 | 2-3 | 测试+文档 | 待启动 |
| **总计** | **完整改进方案** | **8-10天** | **~1150行新框架代码** | **准备启动** |

---

## 🎯 里程碑和关键点

### Day 1-2: Phase 1 完成
- [ ] agent_framework 完整实现
- [ ] 基础单元测试通过
- [ ] 可以import和使用

### Day 3-4: Phase 2 完成
- [ ] 所有工具转换为Tool类
- [ ] 工具注册表可用
- [ ] 工具单独测试通过

### Day 5-6: Phase 3 完成
- [ ] agent_server.py 改进完成
- [ ] 1300行 → 400行
- [ ] 功能完全保持

### Day 7-8: Phase 4 完成
- [ ] 所有测试通过
- [ ] 文档完整
- [ ] 可以部署到生产

### Day 8-10: 缓冲和优化
- [ ] 性能调优
- [ ] UI测试
- [ ] 最终验证

---

## ⚠️ 注意事项

### 向后兼容性
- 现有API保持不变（向后兼容）
- 旧的调用方式仍然工作
- 逐步迁移到新接口

### ProcessCompiler位置
- **完全不改**
- 作为 compile_process_tool 的内部实现
- 现有的测试继续有效

### 数据库
- 数据库操作不变
- 只是调用方式通过Tool Registry
- 数据迁移不需要

### 前端
- UI无需改动
- API返回格式兼容
- 功能完全保持

---

## 📝 下一步

### 立即启动 Phase 1

1. **创建目录结构**
   ```bash
   mkdir -p tools/agent_framework
   mkdir -p tools/process_tools
   touch tools/agent_framework/__init__.py
   touch tools/process_tools/__init__.py
   ```

2. **开始实现**
   - tools/agent_framework/tool_interface.py
   - tools/agent_framework/tool_registry.py
   - 其他框架文件

3. **每日检查**
   - 代码审查
   - 单元测试
   - 进度同步

---

## 成功标志

✅ **项目成功完成的标志**：

1. 代码行数
   - agent_server.py: 1300 → 400行 ✅
   - 新增agent_framework/: 650行 ✅
   - 新增process_tools/: 500行 ✅

2. 功能
   - 所有工具通过Tool Registry调用 ✅
   - 状态机正确运作 ✅
   - ProcessCompiler保持不变 ✅

3. 质量
   - 所有测试通过 ✅
   - 代码风格统一 ✅
   - 文档完整 ✅

4. 可维护性
   - 添加新工具只需创建Tool类 ✅
   - 无需修改核心逻辑 ✅
   - 为迁移到框架做准备 ✅

---

这就是完整的落地计划。现在可以开始了！

需要我帮你启动 Phase 1 吗？
