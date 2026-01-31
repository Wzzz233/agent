"""
Base Tool - Standard interface for OpenAI function calling

All tools in the system should follow this interface and use OpenAI JSON Schema format.
This provides a unified, vendor-agnostic tool definition layer.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import json


class BaseTool(ABC):
    """
    Base class for all tools in the system.
    
    Designed for OpenAI function calling format but vendor-agnostic.
    Tools can be used with any LLM that supports function calling.
    """

    # Tool metadata - must be set by subclasses
    name: str
    description: str
    
    # OpenAI JSON Schema format for parameters
    # Example: {"type": "object", "properties": {...}, "required": [...]}
    parameters: Dict[str, Any]

    @abstractmethod
    def call(self, params: Union[str, Dict[str, Any]], **kwargs) -> str:
        """
        Execute the tool with the given parameters.

        Args:
            params: Parameters as JSON string or dict
            **kwargs: Additional keyword arguments

        Returns:
            Result of the tool execution as a string
        """
        pass

    def parse_params(self, params: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse parameters from JSON string or dict.

        Args:
            params: Parameters as JSON string or dict

        Returns:
            Parsed parameters dictionary
        """
        if isinstance(params, dict):
            return params
        try:
            return json.loads(params)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in parameters: {params}")

    def to_openai_tool(self) -> Dict[str, Any]:
        """
        Convert to OpenAI tools format (for chat completions API).

        Returns:
            OpenAI tool definition dict
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_openai_function(self) -> Dict[str, Any]:
        """
        Convert to OpenAI functions format (legacy format).

        Returns:
            OpenAI function definition dict
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get the full JSON Schema definition for this tool.

        Returns:
            Complete JSON Schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class MCPProxyTool(BaseTool):
    """
    Proxy tool that delegates to MCP servers.
    Wraps MCP tools in the standard BaseTool interface.
    """

    def __init__(
        self, 
        name: str, 
        description: str, 
        parameters: Dict[str, Any],
        mcp_server: str,
        mcp_client_manager
    ):
        """
        Initialize MCP proxy tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: OpenAI JSON Schema parameters
            mcp_server: Name of the MCP server
            mcp_client_manager: Reference to MCPClientManager
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self._mcp_server = mcp_server
        self._mcp_client = mcp_client_manager

    def call(self, params: Union[str, Dict[str, Any]], **kwargs) -> str:
        """
        Call the MCP tool through the client manager.

        Uses call_tool_sync which properly schedules the async call
        on the main event loop where the MCP session was created.

        Args:
            params: Tool parameters

        Returns:
            Tool result as string
        """
        arguments = self.parse_params(params)

        try:
            # Use the synchronous wrapper which properly handles cross-thread calls
            result = self._mcp_client.call_tool_sync(self.name, arguments)
            return self._format_result(result)
        except RuntimeError as e:
            # MCP client not connected or loop issue
            return f"MCP tool {self.name} unavailable: {str(e)}"
        except Exception as e:
            return f"Error executing MCP tool {self.name}: {str(e)}"

    def _format_result(self, result: Any) -> str:
        """Format MCP result to string."""
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, indent=2)