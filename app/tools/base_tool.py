from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json


class BaseTool(ABC):
    """Base class for all tools in the system"""

    name: str
    description: str
    parameters: List[Dict[str, Any]]

    @abstractmethod
    def call(self, params: str, **kwargs) -> str:
        """
        Execute the tool with the given parameters

        Args:
            params: JSON string containing tool parameters
            **kwargs: Additional keyword arguments

        Returns:
            Result of the tool execution as a string
        """
        pass

    def validate_params(self, params: str) -> Dict[str, Any]:
        """
        Validate and parse the parameters

        Args:
            params: JSON string containing tool parameters

        Returns:
            Parsed parameters dictionary
        """
        try:
            parsed_params = json.loads(params)
            return parsed_params
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in parameters")

    def get_spec(self) -> Dict[str, Any]:
        """
        Get the tool specification in JSON format

        Returns:
            Dictionary containing tool specification
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


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