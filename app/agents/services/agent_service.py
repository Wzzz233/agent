from typing import List, Dict, Any, Optional
from qwen_agent.agents import Assistant
from app.config.settings import config
from app.tools.mock_laser_control import MockLaserControl
from app.tools.web_search_tool import WebSearchTool


class AgentService:
    """Service class to manage the THz agent instance"""

    def __init__(self):
        """Initialize the agent service"""
        self._assistant = None

    @property
    def assistant(self):
        """Lazy load the assistant on first access"""
        if self._assistant is None:
            self._create_assistant()
        return self._assistant

    def _create_assistant(self):
        """Create the Qwen Assistant instance with configured settings"""
        self._assistant = Assistant(
            llm={
                "model": config.llm.model,
                "model_server": config.llm.model_server,
                "api_key": config.llm.api_key,
                "generate_cfg": {"temperature": config.llm.temperature}
            },
            name=config.agent.name,
            description=config.agent.description,
            function_list=[MockLaserControl(), WebSearchTool()],  # Directly instantiate tools as in the original
            system_message=config.agent.system_message
        )

    def process_message(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a message and return the agent's response

        Args:
            message: Input message to process
            history: Conversation history (optional)

        Returns:
            Agent's response as a string
        """
        messages = []
        if history:
            messages.extend(history)
        messages.append({'role': 'user', 'content': message})

        # Process the message using the assistant
        responses = list(self.assistant.run(messages=messages))

        # Return the last response (there may be multiple intermediate steps)
        if responses:
            return responses[-1]  # Return the final response
        else:
            return "无法生成响应，请重试。"

    def run_conversation(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Run a conversation with multiple messages

        Args:
            messages: List of messages to process

        Returns:
            List of response messages
        """
        # Process all messages using the assistant
        responses = list(self.assistant.run(messages=messages))

        # Convert responses to the expected format
        result = []
        for response in responses:
            result.append({'role': 'assistant', 'content': response})

        return result

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get a list of available tools

        Returns:
            List of tool specifications
        """
        # Return static list of known tools using their function property from base class
        laser_tool = MockLaserControl()
        search_tool = WebSearchTool()

        tools = [
            laser_tool.function,  # qwen-agent BaseTool has a 'function' property with spec
            search_tool.function  # qwen-agent BaseTool has a 'function' property with spec
        ]
        return tools


# Global agent service instance (but without immediate initialization)
_agent_service_instance = None


def get_agent_service():
    """Get the agent service instance (lazy loaded)"""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance