from typing import Dict, Any, Optional, List
from enum import Enum
import json


class MCPMessageType(Enum):
    """Enumeration for MCP message types"""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"


class MCPMethodType(Enum):
    """Enumeration for MCP method types"""
    CALL_TOOL = "tools/call"
    LIST_TOOLS = "tools/list"
    PROMPT = "prompts/get"
    LIST_PROMPTS = "prompts/list"
    HEALTH_CHECK = "health/check"


class MCPMessage:
    """Base class for MCP messages"""

    def __init__(self, message_type: MCPMessageType, method: str, params: Optional[Dict[str, Any]] = None):
        self.message_type = message_type
        self.method = method
        self.params = params or {}
        self.id = None  # Will be set by transport layer

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary representation"""
        result = {
            "method": self.method,
            "params": self.params
        }

        if self.id is not None:
            result["id"] = self.id

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create an MCP message from a dictionary"""
        message_type = MCPMessageType.REQUEST  # Default assumption
        method = data.get("method", "")
        params = data.get("params", {})
        msg_id = data.get("id")

        message = cls(message_type, method, params)
        message.id = msg_id

        return message


class MCPCallToolRequest(MCPMessage):
    """MCP request for calling a tool"""

    def __init__(self, tool_name: str, arguments: Dict[str, Any], req_id: Optional[str] = None):
        super().__init__(MCPMessageType.REQUEST, MCPMethodType.CALL_TOOL.value, {
            "name": tool_name,
            "arguments": arguments
        })
        self.id = req_id


class MCPCallToolResponse(MCPMessage):
    """MCP response for tool call result"""

    def __init__(self, result: Any, resp_id: Optional[str] = None):
        super().__init__(MCPMessageType.RESPONSE, "", {"result": result})
        self.id = resp_id


class MCPListToolsRequest(MCPMessage):
    """MCP request for listing available tools"""

    def __init__(self, req_id: Optional[str] = None):
        super().__init__(MCPMessageType.REQUEST, MCPMethodType.LIST_TOOLS.value)
        self.id = req_id


class MCPListToolsResponse(MCPMessage):
    """MCP response with list of available tools"""

    def __init__(self, tools: List[Dict[str, Any]], resp_id: Optional[str] = None):
        super().__init__(MCPMessageType.RESPONSE, "", {"tools": tools})
        self.id = resp_id


class MCPErrorResponse(MCPMessage):
    """MCP error response"""

    def __init__(self, error_code: int, error_message: str, error_data: Optional[Dict[str, Any]] = None, resp_id: Optional[str] = None):
        super().__init__(MCPMessageType.ERROR, "", {
            "error": {
                "code": error_code,
                "message": error_message,
                "data": error_data or {}
            }
        })
        self.id = resp_id


class MCPProtocolHandler:
    """Handler for MCP protocol messages"""

    def __init__(self, agent_service):
        self.agent_service = agent_service

    def handle_request(self, message: MCPMessage) -> MCPMessage:
        """Handle an incoming MCP request message"""
        try:
            if message.method == MCPMethodType.CALL_TOOL.value:
                return self.handle_call_tool(message)
            elif message.method == MCPMethodType.LIST_TOOLS.value:
                return self.handle_list_tools(message)
            elif message.method == MCPMethodType.HEALTH_CHECK.value:
                return self.handle_health_check(message)
            else:
                return MCPErrorResponse(400, f"Unknown method: {message.method}", resp_id=message.id)

        except Exception as e:
            return MCPErrorResponse(500, f"Error processing request: {str(e)}", resp_id=message.id)

    def handle_call_tool(self, message: MCPMessage) -> MCPMessage:
        """Handle a tool call request"""
        from app.tools.registry import registry

        try:
            params = message.params
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return MCPErrorResponse(400, "Missing tool name in parameters", resp_id=message.id)

            # Get the tool instance
            tool_instance = registry.get_tool_instance(tool_name)

            # Call the tool with JSON string of arguments
            result = tool_instance.call(json.dumps(arguments))

            # Return the result
            return MCPCallToolResponse(result, resp_id=message.id)

        except KeyError:
            return MCPErrorResponse(404, f"Tool '{tool_name}' not found", resp_id=message.id)
        except Exception as e:
            return MCPErrorResponse(500, f"Error calling tool: {str(e)}", resp_id=message.id)

    def handle_list_tools(self, message: MCPMessage) -> MCPMessage:
        """Handle a request to list available tools"""
        tools = self.agent_service.get_available_tools()
        return MCPListToolsResponse(tools, resp_id=message.id)

    def handle_health_check(self, message: MCPMessage) -> MCPMessage:
        """Handle a health check request"""
        return MCPCallToolResponse({"status": "healthy"}, resp_id=message.id)