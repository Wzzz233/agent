"""
Tool Factory - Initialize and manage all tools for the agent

This module provides:
1. Initialization of built-in tools
2. Loading of MCP tools
3. Registration with the global registry
4. Export of tools in OpenAI format
"""
from typing import List, Dict, Any, Optional
from app.tools.registry import registry
from app.tools.base_tool import BaseTool
from app.config.settings import config


async def initialize_tools_async() -> List[BaseTool]:
    """
    Initialize all tools asynchronously.
    
    This includes:
    1. Built-in tools (web search, laser control, etc.)
    2. MCP tools (ADS, etc.) if enabled
    
    Returns:
        List of all initialized tool instances
    """
    # Clear any existing registrations
    registry.clear()
    
    # 1. Register built-in tools
    from app.tools.mock_laser_control import MockLaserControl
    from app.tools.web_search_tool import WebSearchTool

    # Create and register instances
    if config.web.search_enabled:
        try:
            web_search = WebSearchTool()
            registry.register_instance(web_search)
            print(f"[ToolFactory] Registered: {web_search.name}")
        except Exception as e:
            print(f"[ToolFactory] Failed to init WebSearchTool: {e}")

    try:
        laser_control = MockLaserControl()
        registry.register_instance(laser_control)
        print(f"[ToolFactory] Registered: {laser_control.name}")
    except Exception as e:
        print(f"[ToolFactory] Failed to init MockLaserControl: {e}")

    # 2. Load MCP tools if enabled
    if config.mcp.enabled:
        try:
            await load_mcp_tools()
        except Exception as e:
            print(f"[ToolFactory] Failed to load MCP tools: {e}")
            import traceback
            traceback.print_exc()

    all_tools = registry.list_tools()
    print(f"[ToolFactory] Total tools registered: {len(all_tools)}")
    
    return all_tools


async def load_mcp_tools() -> None:
    """
    Load tools from MCP servers and register them.
    """
    from app.mcp.client import get_mcp_client_manager
    from app.tools.mcp_converter import create_mcp_proxy_tools

    mcp_manager = get_mcp_client_manager()
    
    # Connect to all servers
    print("[ToolFactory] Connecting to MCP servers...")
    await mcp_manager.connect_all()
    
    # Get tool definitions
    mcp_defs = mcp_manager.get_all_tools_definitions()
    print(f"[ToolFactory] Found {len(mcp_defs)} MCP tools")
    
    if mcp_defs:
        # Create proxy tools
        proxy_tools = create_mcp_proxy_tools(mcp_defs, mcp_manager)
        
        # Register with global registry
        registry.register_tools(proxy_tools)


def initialize_tools() -> List[BaseTool]:
    """
    Synchronous wrapper for initialize_tools_async.
    
    Returns:
        List of all initialized tool instances
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Already in async context - this shouldn't happen in normal use
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, initialize_tools_async())
            return future.result()
    else:
        return loop.run_until_complete(initialize_tools_async())


def get_tool_by_name(name: str) -> Optional[BaseTool]:
    """
    Get a specific tool by name.

    Args:
        name: Name of the tool to retrieve

    Returns:
        Tool instance or None
    """
    return registry.get_tool(name)


def list_available_tools() -> List[Dict[str, Any]]:
    """
    Get schemas for all available tools.

    Returns:
        List of tool schemas
    """
    return registry.get_tool_schemas()


def get_openai_tools() -> List[Dict[str, Any]]:
    """
    Get all tools in OpenAI tools format.
    
    This is ready to pass to OpenAI chat completions API.
    
    Returns:
        List of OpenAI tool definitions
    """
    return registry.to_openai_tools()


def get_openai_functions() -> List[Dict[str, Any]]:
    """
    Get all tools in OpenAI functions format (legacy).
    
    Returns:
        List of OpenAI function definitions
    """
    return registry.to_openai_functions()


def call_tool(name: str, arguments: Any) -> str:
    """
    Call a tool by name.
    
    Args:
        name: Tool name
        arguments: Tool arguments (string or dict)
        
    Returns:
        Tool result as string
    """
    return registry.call_tool(name, arguments)