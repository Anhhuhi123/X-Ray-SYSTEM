"""
Tools module for NFD deep agent.

This module contains all the tools available to the NFD agent.
To add a new tool, see the documentation in registry.py.

Available tools:
- search_knowledge_base: Search the user's personal knowledge base
- search_nfd_docs: Search NFD documentation for usage help
"""

# Registry exports
# Tool factory exports (for direct use)
from .knowledge_base import (
    CONNECTOR_DESCRIPTIONS,
    create_search_knowledge_base_tool,
    format_documents_for_context,
    search_knowledge_base_async,
)
from .registry import (
    BUILTIN_TOOLS,
    ToolDefinition,
    build_tools,
    get_all_tool_names,
    get_default_enabled_tools,
    get_tool_by_name,
)
from .search_nfd_docs import create_search_nfd_docs_tool

__all__ = [
    # Registry
    "BUILTIN_TOOLS",
    # Knowledge base utilities
    "CONNECTOR_DESCRIPTIONS",
    "ToolDefinition",
    "build_tools",
    # Tool factories
    "create_search_knowledge_base_tool",
    "create_search_nfd_docs_tool",
    "format_documents_for_context",
    "get_all_tool_names",
    "get_default_enabled_tools",
    "get_tool_by_name",
    "search_knowledge_base_async",
]
