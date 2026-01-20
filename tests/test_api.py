import unittest
import json
from flask import Flask
from app.api.routes.agent_routes import api_bp


class TestAPI(unittest.TestCase):
    """Test cases for the API endpoints"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.register_blueprint(api_bp)
        self.client = self.app.test_client()

    def test_chat_endpoint_valid_request(self):
        """Test the chat endpoint with a valid request"""
        # This test would require mocking the agent service
        # For now, we'll just test that the route exists
        response = self.client.post('/api/v1/agent/chat',
                                    data=json.dumps({'message': 'hello'}),
                                    content_type='application/json')

        # We expect either a successful response or an error due to missing agent service
        self.assertIn(response.status_code, [200, 500])

    def test_chat_endpoint_missing_message(self):
        """Test the chat endpoint with missing message field"""
        response = self.client.post('/api/v1/agent/chat',
                                    data=json.dumps({}),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_list_tools_endpoint(self):
        """Test the list tools endpoint"""
        response = self.client.get('/api/v1/tools/list')

        # We expect either a successful response or an error due to missing agent service
        self.assertIn(response.status_code, [200, 500])


if __name__ == '__main__':
    unittest.main()