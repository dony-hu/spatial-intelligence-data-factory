"""
CreateProcessVersionTool - Create process version

Creates a new version of an existing process definition for release management.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from ..agent_framework import BaseTool, ToolSchema


@dataclass
class CreateProcessVersionTool(BaseTool):
    """
    Tool for creating process version.

    Creates a versioned snapshot of a process definition for release management.
    """

    name: str = "create_version"
    description: str = "创建工艺流程版本"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "code": {
                "type": "string",
                "description": "工艺编码",
                "pattern": "^[A-Z0-9_]{1,32}$"
            },
            "version": {
                "type": "string",
                "description": "版本标签（如 v1.0）",
                "pattern": "^v?[0-9]+\\.[0-9]+(\\.[0-9]+)?$"
            },
            "reason": {
                "type": "string",
                "description": "创建版本原因（可选）",
                "maxLength": 500
            }
        },
        required=["code", "version"],
        additionalProperties=False
    ))

    # Injected dependencies
    runtime_store: Any = None
    process_db_api: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_db_api: Optional[Any] = None):
        """Initialize CreateProcessVersionTool with dependencies"""
        super().__init__()
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """Validate create version parameters"""
        errors = []

        # code is required
        code = str(params.get("code", "")).strip()
        if not code:
            errors.append("缺少必要参数 code")
        elif not self._is_valid_code(code):
            errors.append("code 格式无效")

        # version is required
        version = str(params.get("version", "")).strip()
        if not version:
            errors.append("缺少必要参数 version")
        elif not self._is_valid_version(version):
            errors.append("version 格式无效")

        # Validate reason if provided
        reason = str(params.get("reason", "")).strip()
        if reason and len(reason) > 500:
            errors.append("reason 超过 500 字符限制")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute create version tool"""
        try:
            if not self.process_db_api:
                return {
                    "status": "error",
                    "error": "Process DB API not available",
                    "error_type": "service_error"
                }

            # Call process_db_api to create version
            result = self.process_db_api.execute("create_version", params)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error"
            }

    def _is_valid_code(self, code: str) -> bool:
        """Check if code matches pattern"""
        if not code or len(code) < 1 or len(code) > 32:
            return False
        return all(c.isupper() or c.isdigit() or c == '_' for c in code)

    def _is_valid_version(self, version: str) -> bool:
        """Check if version matches pattern"""
        import re
        pattern = r"^v?\d+\.\d+(\.\d+)?$"
        return bool(re.match(pattern, version))
