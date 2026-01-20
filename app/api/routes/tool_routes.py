from flask import Blueprint, request, jsonify
from app.tools.registry import registry
from typing import Dict, Any


tools_bp = Blueprint('tools', __name__, url_prefix='/api/v1/tools')


@tools_bp.route('/list', methods=['GET'])
def list_tools():
    """Endpoint to list all registered tools"""
    try:
        tool_specs = registry.list_tool_specs()
        return jsonify({
            'success': True,
            'tools': tool_specs
        })
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@tools_bp.route('/register', methods=['POST'])
def register_tool():
    """Admin endpoint to register a new tool (placeholder - implementation would require admin auth)"""
    try:
        # This is a placeholder - in a real implementation, this would require authentication
        # and the ability to dynamically load and register new tools

        return jsonify({
            'success': False,
            'error': 'Dynamic tool registration not implemented in this version'
        }), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@tools_bp.route('/<tool_name>', methods=['GET'])
def get_tool_details(tool_name: str):
    """Get details for a specific tool"""
    try:
        # Check if the tool exists
        if tool_name not in registry.list_tool_names():
            return jsonify({'error': f'Tool "{tool_name}" not found'}), 404

        tool_class = registry.get_tool_class(tool_name)
        tool_instance = registry.get_tool_instance(tool_name)

        return jsonify({
            'success': True,
            'tool': tool_instance.get_spec()
        })
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500