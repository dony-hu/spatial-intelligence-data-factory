"""
Tool注册表 - 管理和执行工具

定义：
- ToolRequest: 工具请求
- ToolResponse: 工具响应
- ToolRegistry: 工具注册表和执行引擎
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid

from .tool_interface import BaseTool


@dataclass
class ToolRequest:
    """工具请求

    表示对工具的调用请求
    """
    name: str                           # 意图名称（不是工具名）
    params: Dict[str, Any]              # 工具参数
    session_id: Optional[str] = None    # 会话ID
    request_id: Optional[str] = None    # 请求ID（自动生成）

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = f"req_{uuid.uuid4().hex[:12]}"


@dataclass
class ToolResponse:
    """工具响应

    表示工具执行的结果
    """
    status: str                         # "ok", "error", "validation_error"
    tool_name: str                      # 执行的工具名称
    result: Optional[Dict[str, Any]] = None    # 执行结果
    error: Optional[str] = None         # 错误信息
    validation_errors: Optional[List[str]] = None  # 参数验证错误
    request_id: Optional[str] = None    # 对应的请求ID

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class ToolRegistry:
    """工具注册表和执行引擎

    管理所有可用的工具，处理工具的注册和执行
    """

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}           # tool_name -> Tool
        self.intent_to_tool: Dict[str, str] = {}       # intent -> tool_name

    def register(self, tool: BaseTool, intents: List[str]) -> None:
        """注册工具

        Args:
            tool: Tool实例
            intents: 该工具支持的意图列表
                例: DesignProcessTool 可以支持 ["design_process", "modify_process"]

        Raises:
            ValueError: 如果工具名重复或意图重复
        """
        # 检查工具名是否已存在
        if tool.name in self.tools:
            raise ValueError(f"工具已存在: {tool.name}")

        # 检查意图是否已被注册
        for intent in intents:
            if intent in self.intent_to_tool:
                raise ValueError(f"意图已被注册: {intent} -> {self.intent_to_tool[intent]}")

        # 注册工具
        self.tools[tool.name] = tool

        # 注册意图映射
        for intent in intents:
            self.intent_to_tool[intent] = tool.name

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """根据工具名称获取工具"""
        return self.tools.get(tool_name)

    def get_tool_by_intent(self, intent: str) -> Optional[BaseTool]:
        """根据意图获取工具

        Args:
            intent: 意图名称

        Returns:
            对应的Tool实例，如果不存在返回None
        """
        tool_name = self.intent_to_tool.get(intent)
        return self.tools.get(tool_name) if tool_name else None

    def list_tools(self) -> Dict[str, str]:
        """列出所有已注册的工具

        Returns:
            {tool_name: description}
        """
        return {name: tool.description for name, tool in self.tools.items()}

    def list_intents(self) -> Dict[str, str]:
        """列出所有已注册的意图

        Returns:
            {intent: tool_name}
        """
        return dict(self.intent_to_tool)

    def has_intent(self, intent: str) -> bool:
        """检查是否支持某个意图"""
        return intent in self.intent_to_tool

    def execute(self, request: ToolRequest) -> ToolResponse:
        """执行工具

        Args:
            request: ToolRequest对象

        Returns:
            ToolResponse对象
        """
        # 查找工具
        tool = self.get_tool_by_intent(request.name)

        if not tool:
            return ToolResponse(
                status="error",
                tool_name=request.name,
                error=f"未知的意图: {request.name}",
                request_id=request.request_id
            )

        # 参数验证
        is_valid, validation_errors = tool.validate(request.params)
        if not is_valid:
            return ToolResponse(
                status="validation_error",
                tool_name=tool.name,
                validation_errors=validation_errors,
                request_id=request.request_id
            )

        # 执行工具
        try:
            result = tool.execute(request.params, request.session_id)
            return ToolResponse(
                status="ok",
                tool_name=tool.name,
                result=result,
                request_id=request.request_id
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                tool_name=tool.name,
                error=str(e),
                request_id=request.request_id
            )

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={len(self.tools)} intents={len(self.intent_to_tool)}>"
