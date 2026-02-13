"""
PublishDraftTool - Publish draft to production process definition

Transitions a draft from editable state to published process definition,
making it available for task execution.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from ..agent_framework import BaseTool, ToolSchema


@dataclass
class PublishDraftTool(BaseTool):
    """
    Tool for publishing process draft to production.

    Takes an editable draft and publishes it as an active process definition,
    optionally creating a versioned release.
    """

    name: str = "publish_draft"
    description: str = "发布工艺草案为正式工艺流程"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "draft_id": {
                "type": "string",
                "description": "草案ID",
                "pattern": "^draft_[a-z0-9]{8,}$"
            },
            "reason": {
                "type": "string",
                "description": "发布原因或说明（可选）",
                "maxLength": 500
            },
            "version_label": {
                "type": "string",
                "description": "版本标签（可选，如v1.0）",
                "pattern": "^v?[0-9]+\\.[0-9]+(\\.[0-9]+)?$"
            }
        },
        required=["draft_id"],
        additionalProperties=False
    ))

    # Injected dependencies
    runtime_store: Any = None
    process_db_api: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_db_api: Optional[Any] = None):
        """Initialize PublishDraftTool with dependencies"""
        super().__init__()
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate publish draft parameters.

        Args:
            params: Tool parameters

        Returns:
            (is_valid, error_list)
        """
        errors = []

        # draft_id is required
        draft_id = str(params.get("draft_id", "")).strip()
        if not draft_id:
            errors.append("缺少必要参数 draft_id")
        elif not draft_id.startswith("draft_"):
            errors.append("draft_id 格式无效，应以 draft_ 开头")

        # Validate reason if provided
        reason = str(params.get("reason", "")).strip()
        if reason and len(reason) > 500:
            errors.append("reason 超过 500 字符限制")

        # Validate version_label if provided
        version_label = str(params.get("version_label", "")).strip()
        if version_label:
            # Simple validation: should look like v1.0 or 1.0 etc
            if not self._is_valid_version_label(version_label):
                errors.append("version_label 格式无效，应为 v1.0 格式")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute draft publication tool.

        Args:
            params: Validated parameters
            session_id: Current session ID

        Returns:
            {
                "status": "ok" | "error",
                "draft_id": str,
                "process_code": str,
                "published_at": str,
                "version_info": {...},
                "error": str (if error)
            }
        """
        try:
            draft_id = str(params.get("draft_id", "")).strip()
            reason = str(params.get("reason", "")).strip()
            version_label = str(params.get("version_label", "")).strip()

            if not self.runtime_store:
                return {
                    "status": "error",
                    "error": "Runtime store not available",
                    "error_type": "service_error"
                }

            # Get draft
            draft = self.runtime_store.get_process_draft(draft_id)
            if not draft:
                return {
                    "status": "error",
                    "error": f"草案不存在: {draft_id}",
                    "error_type": "not_found"
                }

            if draft.get("status") == "published":
                return {
                    "status": "error",
                    "error": f"草案已发布: {draft_id}",
                    "error_type": "invalid_state"
                }

            process_code = draft.get("process_code", "")
            process_name = draft.get("process_name", "")
            domain = draft.get("domain", "address_governance")

            # Use process_db_api if available to create process definition
            result = {}
            if self.process_db_api:
                try:
                    db_result = self.process_db_api.publish_draft({
                        "draft_id": draft_id,
                        "reason": reason
                    })
                    result = db_result if isinstance(db_result, dict) else {}
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"发布失败: {str(e)}",
                        "error_type": "db_error"
                    }

            # Mark draft as published in runtime store
            self.runtime_store.mark_process_draft_published(draft_id)

            # Build response
            return {
                "status": "ok",
                "draft_id": draft_id,
                "process_code": process_code,
                "process_name": process_name,
                "domain": domain,
                "reason": reason,
                "version_label": version_label,
                "published_at": self._now_iso(),
                "message": f"已发布工艺 {process_code} ({process_name})",
                **result  # Include any additional fields from db_api
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error"
            }

    def _is_valid_version_label(self, label: str) -> bool:
        """Check if version label is valid (e.g., v1.0, 1.0, etc)"""
        import re
        pattern = r"^v?\d+\.\d+(\.\d+)?$"
        return bool(re.match(pattern, label))

    @staticmethod
    def _now_iso() -> str:
        """Return current time in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
