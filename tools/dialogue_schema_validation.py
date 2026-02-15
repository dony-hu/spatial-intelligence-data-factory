"""Dialogue schema validation for process expert agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import jsonschema
except ImportError:
    jsonschema = None


class DialogueIntent(Enum):
    """Valid dialogue intents for process expert agent."""

    DESIGN_PROCESS = "design_process"
    MODIFY_PROCESS = "modify_process"
    CREATE_PROCESS = "create_process"
    CREATE_VERSION = "create_version"
    PUBLISH_DRAFT = "publish_draft"
    QUERY_PROCESS = "query_process"
    QUERY_VERSION = "query_version"
    QUERY_PROCESS_TASKS = "query_process_tasks"
    QUERY_TASK_IO = "query_task_io"
    CHAT = "chat"


@dataclass
class ValidationResult:
    """Result of parameter validation."""

    is_valid: bool
    intent: str
    params: Dict[str, Any]
    errors: List[str]
    sanitized_params: Dict[str, Any]


class DialogueSchemaValidator:
    """Validates LLM-extracted parameters against whitelisted schemas."""

    # Define JSON Schema for each intent
    INTENT_SCHEMAS = {
        "create_process": {
            "type": "object",
            "required": ["code", "name", "domain"],
            "properties": {
                "code": {
                    "type": "string",
                    "pattern": "^[A-Z0-9_]{1,32}$",
                    "description": "Process code (uppercase letters, numbers, underscores)",
                },
                "name": {"type": "string", "minLength": 1, "maxLength": 100},
                "domain": {
                    "type": "string",
                    "enum": [
                        "address_governance",
                        "graph_modeling",
                        "verification",
                        "other",
                    ],
                },
                "owner_agent": {"type": "string", "default": "process_expert"},
            },
            "additionalProperties": False,
        },
        "publish_draft": {
            "type": "object",
            "required": ["draft_id"],
            "properties": {
                "draft_id": {
                    "type": "string",
                    "pattern": "^draft_[a-z0-9]{8,}$",
                },
                "reason": {"type": "string", "maxLength": 500},
            },
            "additionalProperties": False,
        },
        "design_process": {
            "type": "object",
            "required": ["process_code", "goal"],
            "properties": {
                "process_code": {"type": "string", "pattern": "^[A-Z0-9_]{1,32}$"},
                "process_name": {"type": "string", "maxLength": 100},
                "goal": {"type": "string", "maxLength": 500},
                "domain": {
                    "type": "string",
                    "enum": [
                        "address_governance",
                        "graph_modeling",
                        "verification",
                    ],
                },
                "auto_execute": {"type": "boolean", "default": False},
                "max_duration_sec": {
                    "type": "integer",
                    "minimum": 60,
                    "maximum": 3600,
                },
            },
            "additionalProperties": False,
        },
        "create_version": {
            "type": "object",
            "required": ["process_definition_id", "version"],
            "properties": {
                "process_definition_id": {"type": "string"},
                "version": {"type": "string", "pattern": "^\\d+\\.\\d+(\\.\\d+)?$"},
                "goal": {"type": "string", "maxLength": 500},
                "publish": {"type": "boolean", "default": False},
                "reason": {"type": "string", "maxLength": 500},
                "tool_bundle_version": {"type": "string", "maxLength": 128},
                "engine_version": {"type": "string", "maxLength": 128},
                "engine_compatibility": {"type": "object"},
            },
            "additionalProperties": False,
        },
        "modify_process": {
            "type": "object",
            "required": ["draft_id", "change_request"],
            "properties": {
                "draft_id": {"type": "string", "pattern": "^draft_[a-z0-9]{8,}$"},
                "change_request": {"type": "string", "maxLength": 500},
                "goal": {"type": "string", "maxLength": 500},
            },
            "additionalProperties": False,
        },
    }

    def validate(self, intent: str, params: Dict[str, Any]) -> ValidationResult:
        """Validate intent and parameters against registered schemas.

        Returns:
            ValidationResult with validation status, errors, and sanitized parameters.
        """
        intent_lower = intent.strip().lower()
        schema = self.INTENT_SCHEMAS.get(intent_lower)

        if not schema:
            # Unknown intent - may be a non-write operation, allow it
            return ValidationResult(
                is_valid=True,
                intent=intent_lower,
                params=params,
                errors=[],
                sanitized_params=params,
            )

        errors = []

        # jsonschema validation
        if jsonschema:
            try:
                jsonschema.validate(params, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Parameter validation failed: {e.message}")
            except jsonschema.SchemaError as e:
                errors.append(f"Schema definition error: {str(e)}")
        else:
            # Basic validation without jsonschema
            required = schema.get("required", [])
            for req_field in required:
                if req_field not in params:
                    errors.append(f"Missing required parameter: {req_field}")

        # Sanitize parameters (remove non-whitelisted fields)
        sanitized = self._sanitize_params(intent_lower, params, schema)

        return ValidationResult(
            is_valid=len(errors) == 0,
            intent=intent_lower,
            params=params,
            errors=errors,
            sanitized_params=sanitized,
        )

    def _sanitize_params(
        self, intent: str, params: Dict[str, Any], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Remove non-whitelisted parameters from params dict."""
        if "properties" not in schema:
            return params

        allowed_keys = set(schema.get("properties", {}).keys())
        return {k: v for k, v in params.items() if k in allowed_keys}

    @staticmethod
    def get_allowed_intents() -> List[str]:
        """Get list of valid intent values."""
        return [intent.value for intent in DialogueIntent]
