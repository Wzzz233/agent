"""Adapter to convert MCP tools to Qwen format."""
import json
from typing import Dict, Any, List
from qwen_agent.tools.base import BaseTool


def mcp_tool_to_qwen_tool(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an MCP tool schema to Qwen tool format.

    Args:
        mcp_tool: MCP tool definition

    Returns:
        Qwen-compatible tool definition
    """
    # Extract name and description
    name = mcp_tool.get('name', '')
    description = mcp_tool.get('description', '')

    # Convert MCP input schema to Qwen parameters format
    input_schema = mcp_tool.get('inputSchema', {})
    qwen_params = _convert_input_schema(input_schema)

    return {
        'name': name,
        'description': description,
        'parameters': qwen_params
    }


def _convert_input_schema(input_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert MCP input schema to Qwen parameters format.

    Args:
        input_schema: MCP input schema in JSON Schema format

    Returns:
        Qwen parameters format
    """
    properties = input_schema.get('properties', {})
    required = input_schema.get('required', [])

    qwen_params = []

    for prop_name, prop_details in properties.items():
        param = {
            'name': prop_name,
            'type': prop_details.get('type', 'string'),
            'description': prop_details.get('description', ''),
            'required': prop_name in required
        }

        # Handle additional properties like enum, default, etc.
        if 'enum' in prop_details:
            param['enum'] = prop_details['enum']
        if 'default' in prop_details:
            param['default'] = prop_details['default']

        qwen_params.append(param)

    return qwen_params


class MCPProxyTool(BaseTool):
    """
    Proxy tool that delegates to MCP servers.
    This class acts as a bridge between Qwen's expectations and MCP protocol.
    """

    def __init__(self, tool_info: Dict[str, Any]):
        """
        Initialize the MCP proxy tool.

        Args:
            tool_info: Tool information in Qwen format
        """
        super().__init__()

        self.name = tool_info.get('name', '')
        self.description = tool_info.get('description', '')
        self.parameters = tool_info.get('parameters', [])

        # Store the original MCP tool name for routing
        self._original_name = tool_info.get('original_name', self.name)

        # Reference to the MCP client manager
        from app.mcp.client import get_mcp_client_manager
        self._mcp_client = get_mcp_client_manager()

    def call(self, params: str, **kwargs) -> str:
        """
        Call the MCP tool through the client manager.

        Args:
            params: JSON string of parameters

        Returns:
            Tool result as string
        """
        import asyncio

        # Parse the parameters
        try:
            arguments = json.loads(params)
        except json.JSONDecodeError as e:
            return f"Error parsing parameters: {str(e)}"

        # Asynchronously call the MCP tool
        # Since this method needs to be synchronous for Qwen compatibility,
        # we'll run the async call in a new event loop if none exists
        try:
            loop = asyncio.get_running_loop()
            # If we're already in a loop, we need to handle differently
            # This is a limitation - we may need to modify the calling code to be async
            import concurrent.futures
            import threading

            def run_async_call():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return asyncio.run(self._async_call_tool(arguments))
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_call)
                result = future.result()

        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            result = asyncio.run(self._async_call_tool(arguments))

        # Return the result as a string
        if isinstance(result, dict) and 'result' in result:
            return json.dumps(result['result'], ensure_ascii=False)
        else:
            return json.dumps(result, ensure_ascii=False)

    async def _async_call_tool(self, arguments: Dict[str, Any]) -> Any:
        """
        Asynchronously call the tool via MCP.

        Args:
            arguments: Arguments to pass to the tool

        Returns:
            Tool result
        """
        try:
            result = await self._mcp_client.call_tool(self._original_name, arguments)
            return result
        except Exception as e:
            return {"error": str(e)}


def create_mcp_proxy_tools(mcp_tools: List[Dict[str, Any]]) -> List[MCPProxyTool]:
    """
    Create MCP proxy tools from MCP tool definitions.

    Args:
        mcp_tools: List of MCP tool definitions

    Returns:
        List of MCPProxyTool instances
    """
    qwen_tools = []

    for mcp_tool in mcp_tools:
        # Convert MCP tool to Qwen format
        qwen_tool_def = mcp_tool_to_qwen_tool(mcp_tool)
        qwen_tool_def['original_name'] = mcp_tool.get('name', '')

        # Create proxy tool instance
        proxy_tool = MCPProxyTool(qwen_tool_def)
        qwen_tools.append(proxy_tool)

    return qwen_tools