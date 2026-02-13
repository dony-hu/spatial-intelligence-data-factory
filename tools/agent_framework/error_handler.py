"""
错误处理和重试机制

定义：
- ErrorType: 错误类型枚举
- ErrorHandler: 错误处理器
"""

from enum import Enum
import time
import logging
from typing import Optional, Callable, Any


logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型"""
    VALIDATION_ERROR = "validation_error"       # 参数验证错误
    TOOL_NOT_FOUND = "tool_not_found"           # 工具不存在
    EXECUTION_ERROR = "execution_error"         # 执行错误
    TIMEOUT_ERROR = "timeout_error"             # 超时错误
    LLM_ERROR = "llm_error"                     # LLM调用错误
    NETWORK_ERROR = "network_error"             # 网络错误
    UNKNOWN_ERROR = "unknown_error"             # 未知错误


class ErrorHandler:
    """错误处理器

    提供重试、降级等错误处理能力
    """

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """初始化错误处理器

        Args:
            max_retries: 最大重试次数
            backoff_factor: 重试退避因子（指数退避）
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """带重试的函数调用

        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    logger.warning(
                        f"重试 {attempt + 1}/{self.max_retries}, "
                        f"等待 {wait_time}s: {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"重试失败，已达最大重试次数: {str(e)}")

        raise last_exception

    @staticmethod
    def classify_error(exception: Exception) -> ErrorType:
        """分类错误

        Args:
            exception: 异常对象

        Returns:
            错误类型
        """
        error_str = str(exception).lower()

        if "validation" in error_str:
            return ErrorType.VALIDATION_ERROR
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif "network" in error_str or "connection" in error_str:
            return ErrorType.NETWORK_ERROR
        elif "llm" in error_str or "api" in error_str:
            return ErrorType.LLM_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR

    @staticmethod
    def should_retry(error_type: ErrorType) -> bool:
        """判断错误是否应该重试

        某些错误可以通过重试恢复（如网络超时），
        某些错误不适合重试（如参数验证错误）

        Args:
            error_type: 错误类型

        Returns:
            是否应该重试
        """
        retryable_errors = {
            ErrorType.TIMEOUT_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.LLM_ERROR,
        }
        return error_type in retryable_errors
