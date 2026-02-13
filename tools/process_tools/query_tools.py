"""
Query tools - Tools for querying process definitions and metadata
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from ..agent_framework import BaseTool, ToolSchema


@dataclass
class QueryProcessTool(BaseTool):
    """Tool for querying process definitions"""

    name: str = "query_process"
    description: str = "查询工艺流程定义"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "code": {
                "type": "string",
                "description": "工艺编码（可选）"
            },
            "domain": {
                "type": "string",
                "description": "业务域（可选）"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量（可选，默认20）",
                "minimum": 1,
                "maximum": 100,
                "default": 20
            }
        },
        required=[],
        additionalProperties=False
    ))

    runtime_store: Any = None
    process_db_api: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_db_api: Optional[Any] = None):
        super().__init__()
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """Validate query process parameters"""
        errors = []

        limit = params.get("limit")
        if limit is not None:
            if not isinstance(limit, int) or limit < 1 or limit > 100:
                errors.append("limit 应为 1-100 之间的整数")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute query process tool"""
        try:
            if not self.process_db_api:
                return {
                    "status": "error",
                    "error": "Process DB API not available",
                    "error_type": "service_error"
                }

            result = self.process_db_api.execute("query_process", params)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error"
            }


@dataclass
class QueryProcessVersionTool(BaseTool):
    """Tool for querying process versions"""

    name: str = "query_version"
    description: str = "查询工艺流程版本"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "code": {
                "type": "string",
                "description": "工艺编码（可选）"
            },
            "version": {
                "type": "string",
                "description": "版本标签（可选）"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量（可选）",
                "minimum": 1,
                "maximum": 100,
                "default": 20
            }
        },
        required=[],
        additionalProperties=False
    ))

    runtime_store: Any = None
    process_db_api: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_db_api: Optional[Any] = None):
        super().__init__()
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """Validate query version parameters"""
        errors = []

        limit = params.get("limit")
        if limit is not None and (not isinstance(limit, int) or limit < 1 or limit > 100):
            errors.append("limit 应为 1-100 之间的整数")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute query version tool"""
        try:
            if not self.process_db_api:
                return {
                    "status": "error",
                    "error": "Process DB API not available",
                    "error_type": "service_error"
                }

            result = self.process_db_api.execute("query_version", params)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error"
            }


@dataclass
class QueryProcessTasksTool(BaseTool):
    """Tool for querying process tasks"""

    name: str = "query_process_tasks"
    description: str = "查询工艺流程的任务"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "code": {
                "type": "string",
                "description": "工艺编码"
            },
            "status": {
                "type": "string",
                "description": "任务状态（可选）",
                "enum": ["pending", "running", "completed", "failed"]
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量（可选）",
                "minimum": 1,
                "maximum": 100,
                "default": 20
            }
        },
        required=["code"],
        additionalProperties=False
    ))

    runtime_store: Any = None
    process_db_api: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_db_api: Optional[Any] = None):
        super().__init__()
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """Validate query tasks parameters"""
        errors = []

        code = str(params.get("code", "")).strip()
        if not code:
            errors.append("缺少必要参数 code")

        limit = params.get("limit")
        if limit is not None and (not isinstance(limit, int) or limit < 1 or limit > 100):
            errors.append("limit 应为 1-100 之间的整数")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute query tasks tool"""
        try:
            if not self.process_db_api:
                return {
                    "status": "error",
                    "error": "Process DB API not available",
                    "error_type": "service_error"
                }

            result = self.process_db_api.execute("query_process_tasks", params)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error"
            }


@dataclass
class QueryTaskIOTool(BaseTool):
    """Tool for querying task input/output"""

    name: str = "query_task_io"
    description: str = "查询任务的输入输出数据"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "task_id": {
                "type": "string",
                "description": "任务ID"
            },
            "include_input": {
                "type": "boolean",
                "description": "是否包含输入数据（可选，默认true）",
                "default": True
            },
            "include_output": {
                "type": "boolean",
                "description": "是否包含输出数据（可选，默认true）",
                "default": True
            }
        },
        required=["task_id"],
        additionalProperties=False
    ))

    runtime_store: Any = None
    process_db_api: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_db_api: Optional[Any] = None):
        super().__init__()
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """Validate query task IO parameters"""
        errors = []

        task_id = str(params.get("task_id", "")).strip()
        if not task_id:
            errors.append("缺少必要参数 task_id")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute query task IO tool"""
        try:
            if not self.process_db_api:
                return {
                    "status": "error",
                    "error": "Process DB API not available",
                    "error_type": "service_error"
                }

            result = self.process_db_api.execute("query_task_io", params)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error"
            }
