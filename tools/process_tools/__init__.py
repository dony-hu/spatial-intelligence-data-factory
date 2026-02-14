"""
Process tools module - Standard Tool classes for process management

Contains all process-related tools converted to inherit from BaseTool:
- DesignProcessTool: LLM-based process design with compilation
- ModifyProcessTool: Modify existing process design
- CreateProcessTool: Create process definition
- CreateProcessVersionTool: Create process version
- PublishDraftTool: Publish draft to production
- QueryProcessTool: Query process definition
- QueryProcessVersionTool: Query process versions
- QueryProcessTasksTool: Query process tasks
- QueryTaskIOTool: Query task input/output

All tools follow the standard BaseTool interface:
- name: Tool identifier
- description: Human-readable description
- input_schema: ToolSchema for parameter validation
- validate(params): Validate parameters
- execute(params, session_id): Execute tool logic
"""

from .design_process_tool import DesignProcessTool
from .modify_process_tool import ModifyProcessTool
from .create_process_tool import CreateProcessTool
from .create_version_tool import CreateProcessVersionTool
from .publish_draft_tool import PublishDraftTool
from .query_tools import (
    QueryProcessTool,
    QueryProcessVersionTool,
    QueryProcessTasksTool,
    QueryTaskIOTool,
)

__all__ = [
    "DesignProcessTool",
    "ModifyProcessTool",
    "CreateProcessTool",
    "CreateProcessVersionTool",
    "PublishDraftTool",
    "QueryProcessTool",
    "QueryProcessVersionTool",
    "QueryProcessTasksTool",
    "QueryTaskIOTool",
]

__version__ = "1.0.0"
