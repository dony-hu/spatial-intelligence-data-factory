"""
Tool标准接口 - 所有工具的基类和协议定义

定义：
- ToolSchema: 工具参数schema
- BaseTool: 所有工具的基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field


@dataclass
class ToolSchema:
    """工具参数schema定义

    遵循JSON Schema标准，定义工具的输入参数
    """
    type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.required is None:
            self.required = []


class BaseTool(ABC):
    """所有工具的基类

    所有具体的工具都应继承此类并实现validate()和execute()方法

    示例:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "My custom tool"

            input_schema = ToolSchema(
                properties={
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                required=["param1"]
            )

            def validate(self, params):
                # 验证参数逻辑
                return (True, None)

            def execute(self, params, session_id=None):
                # 执行工具逻辑
                return {"status": "ok", "result": {...}}
    """

    name: str                           # 工具名称，必须唯一
    description: str                    # 工具描述
    input_schema: ToolSchema = ToolSchema()  # 输入参数schema

    @abstractmethod
    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """验证参数

        Args:
            params: 工具参数字典

        Returns:
            (是否有效, 错误列表)
            - 有效: (True, None)
            - 无效: (False, ["错误1", "错误2", ...])
        """
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """执行工具

        Args:
            params: 工具参数字典（已通过validate验证）
            session_id: 可选的会话ID，用于跟踪和日志

        Returns:
            执行结果字典，应包含:
            - status: "ok" 或 "error"
            - result: 执行结果（如果成功）
            - error: 错误信息（如果失败）
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
