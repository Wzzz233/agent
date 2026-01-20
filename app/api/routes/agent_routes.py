from flask import Blueprint, request, jsonify
from app.agents.services.agent_service import get_agent_service
from typing import Dict, Any, List
import asyncio


api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.route('/agent/chat', methods=['POST'])
def chat():
    """Endpoint for chat interaction with the agent"""
    try:
        data = request.get_json()

        # Validate required fields
        if 'message' not in data:
            return jsonify({'error': 'Missing message field'}), 400

        message = data['message']
        history = data.get('history', [])

        # Validate history format if provided
        if history:
            if not isinstance(history, list):
                return jsonify({'error': 'History must be a list of message objects'}), 400

            for msg in history:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    return jsonify({'error': 'Each message in history must have role and content fields'}), 400

        # Process the message
        agent_service = get_agent_service()

        # Handle the async nature of the agent service
        try:
            # Try to get running loop
            loop = asyncio.get_running_loop()
            # If already in a loop, use run_in_executor
            import concurrent.futures

            def run_sync_chat():
                return agent_service.process_message(message, history)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_sync_chat)
                response = future.result()
        except RuntimeError:
            # No event loop running, safe to call directly
            response = agent_service.process_message(message, history)

        return jsonify({
            'success': True,
            'response': response,
            'message': message
        })

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@api_bp.route('/sessions/create', methods=['POST'])
def create_session():
    """Endpoint to create a new conversation session"""
    try:
        # For now, we just return a placeholder session ID
        # In a more advanced implementation, this would create a session in storage
        import uuid
        session_id = 'session_' + str(uuid.uuid4())
        return jsonify({
            'success': True,
            'session_id': session_id
        })

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@api_bp.route('/tools/list', methods=['GET'])
def list_tools():
    """Endpoint to list available tools"""
    try:
        agent_service = get_agent_service()
        tools = agent_service.get_available_tools()
        return jsonify({
            'success': True,
            'tools': tools
        })

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500