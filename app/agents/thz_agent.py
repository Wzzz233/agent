from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.agents.services.agent_service import get_agent_service
from app.tools.mock_laser_control import MockLaserControl
from app.tools.web_search_tool import WebSearchTool


class THzAgent(BaseAgent):
    """THz-specific agent implementation"""

    name = "THz_Operator"
    description = "实验操作员"

    def __init__(self):
        """Initialize the THz agent"""
        self.service = get_agent_service()

    def process_message(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a message and return the agent's response

        Args:
            message: Input message to process
            history: Conversation history (optional)

        Returns:
            Agent's response as a string
        """
        return self.service.process_message(message, history)

    def run(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Run the agent with a series of messages

        Args:
            messages: List of messages to process

        Returns:
            List of response messages
        """
        return self.service.run_conversation(messages)

    def add_tool(self, tool: 'BaseTool'):
        """
        Add a tool to the agent

        Args:
            tool: Tool to add to the agent
        """
        # This is a simplified implementation - in a more complex system,
        # this would dynamically register tools with the assistant
        pass

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get a list of available tools

        Returns:
            List of tool specifications
        """
        return self.service.get_available_tools()