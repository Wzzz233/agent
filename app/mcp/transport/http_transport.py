from flask import Blueprint, request, jsonify
from app.mcp.handlers.agent_handler import MCPAgentHandler
from typing import Dict, Any


mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp/v1')


@mcp_bp.route('/call', methods=['POST'])
def handle_mcp_call():
    """Handle MCP calls through HTTP"""
    try:
        # Get the JSON payload
        data = request.get_json()

        # Validate the request
        if not isinstance(data, dict):
            return jsonify({
                'error': {
                    'code': 400,
                    'message': 'Request must be a JSON object'
                }
            }), 400

        # Create the MCP agent handler
        handler = MCPAgentHandler()

        # Process the MCP message
        response = handler.handle_mcp_message(data)

        # Return the response
        return jsonify(response)

    except Exception as e:
        return jsonify({
            'error': {
                'code': 500,
                'message': f'Internal server error: {str(e)}'
            }
        }), 500


@mcp_bp.route('/tools', methods=['GET'])
def list_mcp_tools():
    """List available tools through MCP"""
    try:
        handler = MCPAgentHandler()
        tools_response = handler.get_available_tools()

        return jsonify(tools_response)

    except Exception as e:
        return jsonify({
            'error': {
                'code': 500,
                'message': f'Internal server error: {str(e)}'
            }
        }), 500


@mcp_bp.route('/health', methods=['GET'])
def mcp_health():
    """MCP health check endpoint"""
    try:
        return jsonify({
            'id': None,
            'result': {'status': 'healthy'}
        })
    except Exception as e:
        return jsonify({
            'error': {
                'code': 500,
                'message': f'Health check failed: {str(e)}'
            }
        }), 500