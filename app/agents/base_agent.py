from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseAgent(ABC):
    """Base class for all agents in the system"""

    name: str
    description: str

    @abstractmethod
    def process_message(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a message and return the agent's response

        Args:
            message: Input message to process
            history: Conversation history (optional)

        Returns:
            Agent's response as a string
        """
        pass

    @abstractmethod
    def run(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Run the agent with a series of messages

        Args:
            messages: List of messages to process

        Returns:
            List of response messages
        """
        pass

    @abstractmethod
    def add_tool(self, tool: 'BaseTool'):
        """
        Add a tool to the agent

        Args:
            tool: Tool to add to the agent
        """
        pass