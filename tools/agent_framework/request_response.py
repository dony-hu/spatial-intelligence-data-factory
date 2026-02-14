"""
请求/响应格式标准化

定义：
- RequestFormat: 标准请求格式
- ResponseFormat: 标准响应格式
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class RequestFormat:
    """标准请求格式"""
    intent: str                         # 用户意图
    params: Dict[str, Any]              # 参数
    session_id: str                     # 会话ID
    request_id: Optional[str] = None    # 请求ID

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResponseFormat:
    """标准响应格式"""
    status: str                         # "ok", "error", "validation_error"
    message: Optional[str] = None       # 响应消息
    data: Optional[Dict[str, Any]] = None        # 响应数据
    errors: Optional[List[str]] = None          # 错误列表
    request_id: Optional[str] = None    # 对应的请求ID

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
