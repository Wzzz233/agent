"""
Agent Service - Real implementation using Qwen Agent with OpenAI-compatible API
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from app.config.settings import config


class AgentService:
    """Service class to manage the THz agent instance using Qwen Agent framework."""

    def __init__(self):
        """Initialize the agent service with LLM configuration."""
        self._agent = None
        self._tools = []
        self._initialized = False
        self._init_lock = asyncio.Lock()
        
    async def _ensure_initialized(self):
        """Ensure the agent is initialized (lazy initialization)."""
        if self._initialized:
            return
            
        async with self._init_lock:
            if self._initialized:
                return
            await self._initialize_agent()
            self._initialized = True
    
    async def _initialize_agent(self):
        """Initialize the Qwen agent with tools."""
        try:
            from qwen_agent.agents import Assistant
            from app.tools.web_search_tool import WebSearchTool
            from app.tools.mock_laser_control import MockLaserControl
            
            # Configure LLM settings for OpenAI-compatible API
            llm_cfg = {
                'model': config.llm.model,
                'model_server': config.llm.model_server,
                'api_key': config.llm.api_key,
                'generate_cfg': {
                    'temperature': config.llm.temperature,
                }
            }
            
            print(f"[AgentService] Initializing with LLM config:")
            print(f"  Model: {config.llm.model}")
            print(f"  Server: {config.llm.model_server}")
            print(f"  API Key: {config.llm.api_key[:10]}..." if config.llm.api_key else "  API Key: Not set")
            
            # Initialize tools
            self._tools = []
            
            # Add web search tool if enabled
            if config.web.search_enabled:
                try:
                    web_search = WebSearchTool()
                    self._tools.append(web_search)
                    print(f"[AgentService] Added tool: {web_search.name}")
                except Exception as e:
                    print(f"[AgentService] Failed to initialize WebSearchTool: {e}")
            
            # Add laser control tool
            try:
                laser_control = MockLaserControl()
                self._tools.append(laser_control)
                print(f"[AgentService] Added tool: {laser_control.name}")
            except Exception as e:
                print(f"[AgentService] Failed to initialize MockLaserControl: {e}")
            
            # Create the Assistant agent
            self._agent = Assistant(
                llm=llm_cfg,
                name=config.agent.name,
                description=config.agent.description,
                system_message=config.agent.system_message,
                function_list=self._tools
            )
            
            print(f"[AgentService] Agent initialized successfully with {len(self._tools)} tools")
            
        except ImportError as e:
            print(f"[AgentService] Import error during initialization: {e}")
            print("[AgentService] Falling back to simple mode without qwen-agent")
            self._agent = None
        except Exception as e:
            print(f"[AgentService] Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None


    async def process_message_async(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process a message using the Qwen agent.
        
        Args:
            message: The user's message
            history: Optional conversation history
            
        Returns:
            Dict containing 'response' (str) and 'thoughts' (List[Dict])
        """
        await self._ensure_initialized()
        
        if self._agent is None:
            # Fallback mode - just echo with a note
            return {
                "response": f"[Agent未初始化] 无法处理消息: {message}",
                "thoughts": []
            }
        
        try:
            # Prepare messages for the agent
            messages = []
            
            # Add history if provided
            if history:
                for msg in history:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    messages.append({'role': role, 'content': content})
            
            # Add current message
            messages.append({'role': 'user', 'content': message})
            
            print(f"[AgentService] Processing message: {message[:50]}...")
            
            # Run the agent - collect all responses
            response_text = ""
            final_responses = []
            
            # The agent.run() returns a generator of response chunks
            for response in self._agent.run(messages=messages):
                # Each response is a list of message dicts
                if isinstance(response, list) and len(response) > 0:
                    final_responses = response
                    last_msg = response[-1]
                    if isinstance(last_msg, dict):
                        content = last_msg.get('content', '')
                        if content:
                            response_text = content
            
            if not response_text:
                response_text = "抱歉，我无法生成回复。请稍后再试。"
            
            print(f"[AgentService] Response generated: {response_text[:100]}...")
            
            return {
                "response": response_text,
                "thoughts": final_responses
            }
            
        except Exception as e:
            error_msg = f"处理消息时发生错误: {str(e)}"
            print(f"[AgentService] Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                "response": error_msg,
                "thoughts": []
            }
            


    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        tools_list = []
        for tool in self._tools:
            tools_list.append({
                'name': getattr(tool, 'name', 'unknown'),
                'description': getattr(tool, 'description', ''),
                'parameters': getattr(tool, 'parameters', [])
            })
        return tools_list


# Global agent service instance
_agent_service_instance = None


def get_agent_service():
    """Get the global agent service instance."""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance