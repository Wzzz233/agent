import unittest
from unittest.mock import patch, MagicMock
from app.agents.services.agent_service import AgentService


class TestAgentService(unittest.TestCase):
    """Test cases for the AgentService"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.agent_service = AgentService()

    @patch('app.agents.services.agent_service.initialize_tools')
    @patch('app.agents.services.agent_service.Assistant')
    def test_initialization(self, mock_assistant, mock_initialize_tools):
        """Test that the agent service initializes correctly"""
        # Mock the tools and assistant
        mock_tools = ['tool1', 'tool2']
        mock_initialize_tools.return_value = mock_tools
        mock_assistant_instance = MagicMock()
        mock_assistant.return_value = mock_assistant_instance

        # Recreate the agent service with mocks
        service = AgentService()

        # Verify that initialization worked
        self.assertIsNotNone(service)
        self.assertEqual(service.tools, mock_tools)

    def test_get_available_tools(self):
        """Test getting available tools"""
        tools = self.agent_service.get_available_tools()
        self.assertIsInstance(tools, list)
        # At least the two tools we created should be available
        self.assertGreaterEqual(len(tools), 2)


if __name__ == '__main__':
    unittest.main()