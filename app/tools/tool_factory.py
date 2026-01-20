from typing import List
from app.tools.registry import registry
from app.tools.base_tool import BaseTool


def initialize_tools() -> List[BaseTool]:
    """
    Initialize and return all registered tools

    Returns:
        List of tool instances
    """
    # Register all available tools
    from app.tools.mock_laser_control import MockLaserControl
    from app.tools.web_search_tool import WebSearchTool

    # Register the tools with the registry
    registry.register_tool(MockLaserControl)
    registry.register_tool(WebSearchTool)

    # Create instances of all registered tools
    tools = []
    for tool_name in registry.list_tool_names():
        tool_instance = registry.get_tool_instance(tool_name)
        tools.append(tool_instance)

    return tools


def get_tool_by_name(name: str) -> BaseTool:
    """
    Get a specific tool by name

    Args:
        name: Name of the tool to retrieve

    Returns:
        Tool instance
    """
    return registry.get_tool_instance(name)


def list_available_tools() -> List[dict]:
    """
    Get a list of all available tool specifications

    Returns:
        List of tool specifications
    """
    return registry.list_tool_specs()