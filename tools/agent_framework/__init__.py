"""
Agent框架 - 工艺Agent的核心框架

包含以下核心组件：
- tool_interface: Tool标准接口
- tool_registry: Tool注册表和管理
- state_machine: 会话状态机
- request_response: 标准请求/响应格式
- error_handler: 错误处理和重试逻辑
"""

from .tool_interface import BaseTool, ToolSchema
from .tool_registry import ToolRegistry, ToolRequest, ToolResponse
from .state_machine import ChatState, SessionState, StateTransition
from .request_response import RequestFormat, ResponseFormat
from .error_handler import ErrorHandler, ErrorType

__all__ = [
    # Tool接口
    "BaseTool",
    "ToolSchema",
    # Tool注册表
    "ToolRegistry",
    "ToolRequest",
    "ToolResponse",
    # 状态机
    "ChatState",
    "SessionState",
    "StateTransition",
    # 请求响应
    "RequestFormat",
    "ResponseFormat",
    # 错误处理
    "ErrorHandler",
    "ErrorType",
]

__version__ = "1.0.0"
__description__ = "工艺Agent核心框架"
