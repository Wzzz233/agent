from typing import List, Dict, Any, Optional
from qwen_agent.agents import Assistant
from app.config.settings import config
from app.mcp.client import get_mcp_client_manager
from app.agents.adapters.qwen_adapter import create_mcp_proxy_tools


class AgentService:
    """Service class to manage the THz agent instance"""

    def __init__(self):
        """Initialize the agent service"""
        self._assistant = None
        self._mcp_client = get_mcp_client_manager()
        self._proxy_tools = []

    @property
    def assistant(self):
        """Lazy load the assistant on first access"""
        if self._assistant is None:
            self._create_assistant()
        return self._assistant

    async def initialize_mcp_tools(self):
        """Initialize MCP tools by connecting to servers and creating proxy tools."""
        # Connect to all MCP servers
        await self._mcp_client.connect_all()

        # Get tools from all connected servers
        mcp_tools = self._mcp_client.get_all_tools()

        # Create proxy tools from MCP tools
        self._proxy_tools = create_mcp_proxy_tools(mcp_tools)

    def _create_assistant(self):
        """Create the Qwen Assistant instance with configured settings"""
        # Initialize MCP tools asynchronously
        import asyncio
        try:
            # Try to get running loop, if available
            loop = asyncio.get_running_loop()

            # If already in a loop, schedule the async initialization
            async def init_tools():
                await self.initialize_mcp_tools()

            # Schedule the initialization but continue with empty tools for now
            # The actual tools will be available after initialization
            asyncio.create_task(init_tools())
        except RuntimeError:
            # No running loop, safe to run directly
            asyncio.run(self.initialize_mcp_tools())

        self._assistant = Assistant(
            llm={
                "model": config.llm.model,
                "model_server": config.llm.model_server,
                "api_key": config.llm.api_key,
                "generate_cfg": {"temperature": config.llm.temperature}
            },
            name=config.agent.name,
            description=config.agent.description,
            function_list=self._proxy_tools,  # Use MCP proxy tools instead of local tools
            system_message=config.agent.system_message
        )

    async def process_message_async(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a message asynchronously and return the agent's response

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
        responses = []
        async for response in self.assistant.run(messages=messages):
            responses.append(response)

        # Return the last response (there may be multiple intermediate steps)
        if responses:
            return responses[-1]  # Return the final response
        else:
            return "无法生成响应，请重试。"

    def process_message(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a message and return the agent's response

        Args:
            message: Input message to process
            history: Conversation history (optional)

        Returns:
            Agent's response as a string
        """
        # For backward compatibility, run the async version
        import asyncio

        try:
            # Try to get running loop
            loop = asyncio.get_running_loop()
            # If we're already in a loop, we need to handle this differently
            # We'll use run_in_executor to avoid blocking
            import concurrent.futures
            import threading

            def run_async_process():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return asyncio.run(self.process_message_async(message, history))
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_process)
                return future.result()

        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self.process_message_async(message, history))

    def run_conversation(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Run a conversation with multiple messages

        Args:
            messages: List of messages to process

        Returns:
            List of response messages
        """
        # Process all messages using the assistant
        responses = []
        for response in self.assistant.run(messages=messages):
            responses.append(response)

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
        # Return the proxy tools' function specs
        tools = []
        for proxy_tool in self._proxy_tools:
            tools.append(proxy_tool.function)
        return tools


# Global agent service instance (but without immediate initialization)
_agent_service_instance = None


def get_agent_service():
    """Get the agent service instance (lazy loaded)"""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance