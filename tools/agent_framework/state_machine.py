"""
会话状态机 - 管理Agent对话的状态

定义：
- ChatState: 会话状态枚举
- SessionState: 会话状态对象
- StateTransition: 状态转移规则
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ChatState(Enum):
    """会话状态枚举

    NORMAL: 正常对话，等待用户输入
    PENDING_CONFIRMATION: 等待用户确认操作
    EXECUTING: 正在执行工具
    ERROR: 发生错误
    """
    NORMAL = "normal"
    PENDING_CONFIRMATION = "pending_confirmation"
    EXECUTING = "executing"
    ERROR = "error"


class StateTransition:
    """状态转移规则

    定义合法的状态转移路径
    """

    # 允许的状态转移
    ALLOWED = {
        ChatState.NORMAL: [
            ChatState.PENDING_CONFIRMATION,
            ChatState.EXECUTING,
            ChatState.ERROR,
            ChatState.NORMAL  # 保持原状态
        ],
        ChatState.PENDING_CONFIRMATION: [
            ChatState.EXECUTING,
            ChatState.NORMAL,
            ChatState.ERROR
        ],
        ChatState.EXECUTING: [
            ChatState.NORMAL,
            ChatState.ERROR
        ],
        ChatState.ERROR: [
            ChatState.NORMAL,
            ChatState.PENDING_CONFIRMATION
        ]
    }

    @staticmethod
    def is_valid(from_state: ChatState, to_state: ChatState) -> bool:
        """检查状态转移是否合法

        Args:
            from_state: 当前状态
            to_state: 目标状态

        Returns:
            转移是否合法
        """
        allowed = StateTransition.ALLOWED.get(from_state, [])
        return to_state in allowed

    @staticmethod
    def describe() -> str:
        """描述状态转移规则"""
        lines = ["状态转移规则:"]
        for state, allowed in StateTransition.ALLOWED.items():
            targets = ", ".join([s.value for s in allowed])
            lines.append(f"  {state.value} → {targets}")
        return "\n".join(lines)


@dataclass
class SessionState:
    """会话状态对象

    跟踪单个会话的完整状态，包括消息历史、当前状态、待确认操作等
    """
    session_id: str                     # 会话ID
    current_state: ChatState = ChatState.NORMAL    # 当前状态
    message_history: List[Dict[str, str]] = field(default_factory=list)  # 消息历史
    pending_operation: Optional[Dict] = None       # 等待确认的操作
    draft_id: Optional[str] = None                 # 当前草案ID
    last_error: Optional[str] = None               # 最后一个错误信息

    def add_message(self, role: str, content: str) -> None:
        """添加消息到历史

        Args:
            role: 消息角色 ("user", "assistant", "system")
            content: 消息内容
        """
        self.message_history.append({"role": role, "content": content})

    def get_recent_messages(self, limit: int = 8) -> List[Dict[str, str]]:
        """获取最近的消息

        Args:
            limit: 返回的最近消息数量

        Returns:
            最近的消息列表
        """
        return self.message_history[-limit:]

    def transition_to(self, new_state: ChatState) -> bool:
        """转移到新状态

        Args:
            new_state: 目标状态

        Returns:
            转移是否成功
        """
        if not StateTransition.is_valid(self.current_state, new_state):
            return False
        self.current_state = new_state
        return True

    def set_pending_operation(self, intent: str, params: Dict) -> None:
        """设置待确认的操作

        Args:
            intent: 操作意图
            params: 操作参数
        """
        self.pending_operation = {
            "intent": intent,
            "params": params
        }
        self.transition_to(ChatState.PENDING_CONFIRMATION)

    def clear_pending_operation(self) -> None:
        """清除待确认的操作"""
        self.pending_operation = None

    def set_error(self, error_message: str) -> None:
        """设置错误状态

        Args:
            error_message: 错误信息
        """
        self.last_error = error_message
        self.transition_to(ChatState.ERROR)

    def clear_error(self) -> None:
        """清除错误状态"""
        self.last_error = None
        self.transition_to(ChatState.NORMAL)

    def clear_history(self) -> None:
        """清空消息历史"""
        self.message_history = []

    def reset(self) -> None:
        """重置会话状态（保持session_id）"""
        self.current_state = ChatState.NORMAL
        self.message_history = []
        self.pending_operation = None
        self.draft_id = None
        self.last_error = None

    def to_dict(self) -> Dict:
        """转换为字典（用于持久化）"""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value,
            "message_history": self.message_history,
            "pending_operation": self.pending_operation,
            "draft_id": self.draft_id,
            "last_error": self.last_error,
        }

    def __repr__(self) -> str:
        msg_count = len(self.message_history)
        pending = " (待确认)" if self.pending_operation else ""
        error = f" [错误: {self.last_error}]" if self.last_error else ""
        return f"<SessionState {self.session_id} state={self.current_state.value} messages={msg_count}{pending}{error}>"
