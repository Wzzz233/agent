"""
Test script to verify the tools listing works without Flask server
"""
from app.api.routes.agent_routes import list_tools
from flask import Flask
import json

def simulate_api_call():
    """Simulate the API call without actually running the server"""
    print("Testing tools list functionality...")

    # Create a minimal Flask app for testing
    app = Flask(__name__)

    with app.test_request_context('/api/v1/tools/list', method='GET'):
        try:
            result = list_tools()
            print(f"Result type: {type(result)}")

            # Extract the actual content
            if hasattr(result, 'response'):
                # It's a Flask Response object
                response_text = b''.join(list(result.response)).decode('utf-8')
                status_code = result.status_code
                print(f"Status code: {status_code}")
                print(f"Response content: {response_text}")

                if status_code == 200:
                    data = json.loads(response_text)
                    print("Parsed JSON data:", json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print("Error response received")
            elif isinstance(result, tuple):
                response_data, status_code = result
                print(f"Status code: {status_code}")
                print(f"Response: {response_data}")
            else:
                print(f"Response: {result}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    simulate_api_call()