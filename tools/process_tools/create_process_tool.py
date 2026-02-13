"""
CreateProcessTool - Create process definition from existing draft

Transitions a published draft into an active process definition
with version 1.0 and makes it available for task execution.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from ..agent_framework import BaseTool, ToolSchema


@dataclass
class CreateProcessTool(BaseTool):
    """
    Tool for creating process definition from draft.

    Wraps draft into process definition with version tracking
    and makes it available for task execution.
    """

    name: str = "create_process"
    description: str = "从草案创建工艺流程定义"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "code": {
                "type": "string",
                "description": "工艺编码（可选，草案中可获取）",
                "pattern": "^[A-Z0-9_]{1,32}$"
            },
            "name": {
                "type": "string",
                "description": "工艺名称（可选）",
                "maxLength": 100
            },
            "domain": {
                "type": "string",
                "description": "业务域",
                "enum": ["address_governance", "graph_modeling", "verification", "other"]
            }
        },
        required=[],
        additionalProperties=False
    ))

    # Injected dependencies
    runtime_store: Any = None
    process_db_api: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_db_api: Optional[Any] = None):
        """Initialize CreateProcessTool with dependencies"""
        super().__init__()
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """Validate create process parameters"""
        errors = []

        # Validate code if provided
        code = str(params.get("code", "")).strip()
        if code and not self._is_valid_code(code):
            errors.append("code 格式无效")

        # Validate name if provided
        name = str(params.get("name", "")).strip()
        if name and len(name) > 100:
            errors.append("name 超过 100 字符限制")

        # Validate domain if provided
        domain = str(params.get("domain", "")).strip()
        if domain:
            valid_domains = ["address_governance", "graph_modeling", "verification", "other"]
            if domain not in valid_domains:
                errors.append(f"domain 无效")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute create process tool"""
        try:
            if not self.process_db_api:
                return {
                    "status": "error",
                    "error": "Process DB API not available",
                    "error_type": "service_error"
                }

            # Call process_db_api to create process
            result = self.process_db_api.execute("create_process", params)
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
