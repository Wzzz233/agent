from app.mcp.protocol import MCPProtocolHandler, MCPMessage
from app.agents.services.agent_service import get_agent_service


class MCPAgentHandler:
    """Handler for MCP agent interactions"""

    def __init__(self):
        self.agent_service = get_agent_service()
        self.protocol_handler = MCPProtocolHandler(self.agent_service)

    def handle_mcp_message(self, message_data: dict) -> dict:
        """
        Handle an MCP message and return the response

        Args:
            message_data: Dictionary containing the MCP message

        Returns:
            Dictionary containing the MCP response
        """
        try:
            # Parse the incoming message
            incoming_message = MCPMessage.from_dict(message_data)

            # Process the message using the protocol handler
            response_message = self.protocol_handler.handle_request(incoming_message)

            # Return the response as a dictionary
            return response_message.to_dict()

        except Exception as e:
            # Return an error response if something goes wrong
            from app.mcp.protocol import MCPErrorResponse
            error_response = MCPErrorResponse(500, f"Error processing MCP message: {str(e)}")
            if 'id' in message_data:
                error_response.id = message_data['id']
            return error_response.to_dict()

    def get_available_tools(self) -> dict:
        """
        Get available tools through MCP protocol

        Returns:
            Dictionary containing available tools
        """
        from app.mcp.protocol import MCPListToolsRequest
        import uuid

        # Get tools from the agent service
        tools = self.agent_service.get_available_tools()

        # Create response manually without needing a request
        return {
            'result': {'tools': tools}
        }