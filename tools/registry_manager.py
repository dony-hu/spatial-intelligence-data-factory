"""
Tool Registry Initialization Module

Centralizes registration of all process tools with the ToolRegistry,
providing a clean initialization interface for agent_server.py.

This module handles:
1. Creating the ToolRegistry instance
2. Instantiating all Tool classes with dependencies
3. Registering tools with their intent mappings
4. Providing initialization interface for other modules
"""

from typing import Optional, Dict, Any
import logging

from .agent_framework import ToolRegistry, ToolRequest, ToolResponse
from .process_tools import (
    DesignProcessTool,
    ModifyProcessTool,
    PublishDraftTool,
    CreateProcessTool,
    CreateProcessVersionTool,
    QueryProcessTool,
    QueryProcessVersionTool,
    QueryProcessTasksTool,
    QueryTaskIOTool,
)


logger = logging.getLogger(__name__)


class ToolRegistryManager:
    """
    Manager for initializing and providing access to the ToolRegistry.

    Singleton pattern: maintains a single instance of ToolRegistry
    with all tools registered and ready to use.
    """

    _instance: Optional["ToolRegistryManager"] = None
    _registry: Optional[ToolRegistry] = None

    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(
        cls,
        runtime_store: Optional[Any] = None,
        process_compiler: Optional[Any] = None,
        process_db_api: Optional[Any] = None,
        llm_service: Optional[Any] = None,
    ) -> ToolRegistry:
        """
        Initialize the ToolRegistry with all process tools.

        Args:
            runtime_store: Runtime store instance
            process_compiler: ProcessCompiler instance
            process_db_api: Process DB API instance
            llm_service: LLM service instance

        Returns:
            Initialized ToolRegistry instance

        Raises:
            RuntimeError: If already initialized
        """
        if cls._registry is not None:
            logger.warning("ToolRegistry already initialized, returning existing instance")
            return cls._registry

        cls._registry = ToolRegistry()

        # Register all write operation tools (require more dependencies)
        cls._register_write_tools(
            runtime_store=runtime_store,
            process_compiler=process_compiler,
            process_db_api=process_db_api,
            llm_service=llm_service,
        )

        # Register all read operation tools (simple delegation)
        cls._register_read_tools(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )

        logger.info(f"ToolRegistry initialized with {len(cls._registry.tools)} tools")
        return cls._registry

    @classmethod
    def get_registry(cls) -> ToolRegistry:
        """
        Get the ToolRegistry instance.

        Returns:
            ToolRegistry instance

        Raises:
            RuntimeError: If registry not initialized
        """
        if cls._registry is None:
            raise RuntimeError(
                "ToolRegistry not initialized. Call ToolRegistryManager.initialize() first."
            )
        return cls._registry

    @classmethod
    def _register_write_tools(
        cls,
        runtime_store: Optional[Any] = None,
        process_compiler: Optional[Any] = None,
        process_db_api: Optional[Any] = None,
        llm_service: Optional[Any] = None,
    ) -> None:
        """Register write operation tools (create, modify, publish, etc)"""

        # Design Process Tool
        design_tool = DesignProcessTool(
            runtime_store=runtime_store,
            process_compiler=process_compiler,
            llm_service=llm_service,
        )
        cls._registry.register(design_tool, ["design_process"])
        logger.debug("Registered: DesignProcessTool (design_process)")

        # Modify Process Tool
        modify_tool = ModifyProcessTool(
            runtime_store=runtime_store,
            process_compiler=process_compiler,
            llm_service=llm_service,
        )
        cls._registry.register(modify_tool, ["modify_process"])
        logger.debug("Registered: ModifyProcessTool (modify_process)")

        # Publish Draft Tool
        publish_tool = PublishDraftTool(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )
        cls._registry.register(publish_tool, ["publish_draft"])
        logger.debug("Registered: PublishDraftTool (publish_draft)")

        # Create Process Tool
        create_process_tool = CreateProcessTool(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )
        cls._registry.register(create_process_tool, ["create_process"])
        logger.debug("Registered: CreateProcessTool (create_process)")

        # Create Process Version Tool
        create_version_tool = CreateProcessVersionTool(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )
        cls._registry.register(create_version_tool, ["create_version"])
        logger.debug("Registered: CreateProcessVersionTool (create_version)")

    @classmethod
    def _register_read_tools(
        cls,
        runtime_store: Optional[Any] = None,
        process_db_api: Optional[Any] = None,
    ) -> None:
        """Register read operation tools (queries)"""

        # Query Process Tool
        query_process_tool = QueryProcessTool(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )
        cls._registry.register(query_process_tool, ["query_process"])
        logger.debug("Registered: QueryProcessTool (query_process)")

        # Query Process Version Tool
        query_version_tool = QueryProcessVersionTool(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )
        cls._registry.register(query_version_tool, ["query_version"])
        logger.debug("Registered: QueryProcessVersionTool (query_version)")

        # Query Process Tasks Tool
        query_tasks_tool = QueryProcessTasksTool(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )
        cls._registry.register(query_tasks_tool, ["query_process_tasks"])
        logger.debug("Registered: QueryProcessTasksTool (query_process_tasks)")

        # Query Task IO Tool
        query_task_io_tool = QueryTaskIOTool(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
        )
        cls._registry.register(query_task_io_tool, ["query_task_io"])
        logger.debug("Registered: QueryTaskIOTool (query_task_io)")

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (for testing)"""
        cls._registry = None
        logger.info("ToolRegistry reset")

    @classmethod
    def list_tools(cls) -> Dict[str, str]:
        """List all registered tools"""
        registry = cls.get_registry()
        return registry.list_tools()

    @classmethod
    def list_intents(cls) -> Dict[str, str]:
        """List all registered intents"""
        registry = cls.get_registry()
        return registry.list_intents()

    @classmethod
    def execute_tool(
        cls, intent: str, params: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool by intent.

        Args:
            intent: Tool intent name
            params: Tool parameters
            session_id: Current session ID

        Returns:
            Tool execution result as dict
        """
        registry = cls.get_registry()
        request = ToolRequest(name=intent, params=params, session_id=session_id)
        response = registry.execute(request)

        # Convert ToolResponse to dict for API responses
        return {
            "status": response.status,
            "tool_name": response.tool_name,
            "result": response.result,
            "error": response.error,
            "validation_errors": response.validation_errors,
            "request_id": response.request_id,
        }


# Convenience functions for module-level access
def initialize_registry(
    runtime_store: Optional[Any] = None,
    process_compiler: Optional[Any] = None,
    process_db_api: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> ToolRegistry:
    """Initialize the global ToolRegistry"""
    return ToolRegistryManager.initialize(
        runtime_store=runtime_store,
        process_compiler=process_compiler,
        process_db_api=process_db_api,
        llm_service=llm_service,
    )


def get_registry() -> ToolRegistry:
    """Get the global ToolRegistry instance"""
    return ToolRegistryManager.get_registry()


def execute_tool(
    intent: str, params: Dict[str, Any], session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a tool through the registry"""
    return ToolRegistryManager.execute_tool(intent, params, session_id)


def list_registered_tools() -> Dict[str, str]:
    """List all registered tools"""
    return ToolRegistryManager.list_tools()


def list_registered_intents() -> Dict[str, str]:
    """List all registered intents"""
    return ToolRegistryManager.list_intents()
