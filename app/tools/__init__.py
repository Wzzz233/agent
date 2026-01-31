"""
Tools Package - Standard OpenAI function calling compatible tools

This package provides:
- BaseTool: Base class for all tools
- MCPProxyTool: Proxy for MCP server tools
- ToolRegistry: Central tool registration and management
- Tool Factory: Initialization and export utilities

All tools use OpenAI JSON Schema format for parameters.
"""

from app.tools.base_tool import BaseTool, MCPProxyTool
from app.tools.registry import registry, register_tool
from app.tools.tool_factory import (
    initialize_tools,
    initialize_tools_async,
    get_tool_by_name,
    list_available_tools,
    get_openai_tools,
    get_openai_functions,
    call_tool,
)

__all__ = [
    # Base classes
    "BaseTool",
    "MCPProxyTool",
    
    # Registry
    "registry",
    "register_tool",
    
    # Factory functions
    "initialize_tools",
    "initialize_tools_async",
    "get_tool_by_name",
    "list_available_tools",
    "get_openai_tools",
    "get_openai_functions",
    "call_tool",
]
