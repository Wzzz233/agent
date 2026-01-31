"""
Agent Service - Native OpenAI API Implementation with Session Support

This module implements the core agent loop using:
1. Native OpenAI SDK for API calls
2. OpenAI Function Calling for tool execution
3. ControlLayer for loop termination and safety checks
4. Session-based state management (no global singleton)
5. Standard JSON Schema tools from the tools package

No qwen-agent dependency - pure OpenAI compatible implementation.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional

from openai import OpenAI

from app.config.settings import config
from app.agents.control_layer import ControlLayer, ControlLayerConfig, TerminationReason
from app.agents.services.session_manager import Session, SessionManager, get_session_manager


class AgentService:
    """
    Service class to manage the agent using pure OpenAI API.
    
    Now supports session-based state management:
    - Each session has its own message history
    - Each session has its own ControlLayer
    - No global state - fully stateless service
    
    Implements a "Think-Execute-Feedback" loop with:
    - Native OpenAI function calling
    - ControlLayer for safety and termination
    - Async support for MCP tool initialization
    """

    def __init__(self):
        """Initialize the agent service with LLM configuration."""
        self._client: Optional[OpenAI] = None
        self._tools: List[Dict[str, Any]] = []  # OpenAI tools format
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
        """Initialize the OpenAI client and tools."""
        try:
            # Configure OpenAI client
            base_url = self._get_base_url()
            
            self._client = OpenAI(
                api_key=config.llm.api_key,
                base_url=base_url
            )
            
            print(f"[AgentService] Initializing OpenAI client:")
            print(f"  Model: {config.llm.model}")
            print(f"  Base URL: {base_url}")
            print(f"  API Key: {config.llm.api_key[:10]}..." if config.llm.api_key else "  API Key: Not set")
            
            # Initialize tools using the new tool factory
            from app.tools import initialize_tools_async, get_openai_tools
            
            await initialize_tools_async()
            self._tools = get_openai_tools()
            
            print(f"[AgentService] Loaded {len(self._tools)} tools in OpenAI format")
            for tool in self._tools:
                print(f"  - {tool['function']['name']}")
            
        except Exception as e:
            print(f"[AgentService] Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            self._client = None

    def _get_base_url(self) -> str:
        """Get the properly formatted base URL for OpenAI client."""
        base_url = config.llm.model_server
        
        # Remove trailing /chat/completions if present
        if base_url.endswith('/chat/completions'):
            base_url = base_url.replace('/chat/completions', '')
        
        # Ensure it ends with /v1 for OpenAI compatibility
        if not base_url.endswith('/v1'):
            if base_url.endswith('/'):
                base_url += 'v1'
            else:
                base_url += '/v1'
        
        return base_url

    # ==================== Session-Based API ====================

    async def chat_with_session(
        self,
        session_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Process a message within a specific session.
        
        This is the primary API for session-based conversations.
        Messages are automatically added to session history.
        
        Args:
            session_id: The session ID
            message: The user's message
            
        Returns:
            Dict containing 'response', 'thoughts', 'session_id'
        """
        await self._ensure_initialized()
        
        if self._client is None:
            return {
                "response": "[Agent未初始化] 无法处理消息，请检查配置。",
                "thoughts": [],
                "session_id": session_id
            }
        
        # Get or create session
        session_manager = get_session_manager()
        session = session_manager.get_or_create_session(session_id)
        
        try:
            # Run the agent loop in a thread pool
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                self._run_session_agent_loop, 
                session, 
                message
            )
            
            return {
                **result,
                "session_id": session.session_id
            }
            
        except Exception as e:
            error_msg = f"处理消息时发生错误: {str(e)}"
            print(f"[AgentService] Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                "response": error_msg,
                "thoughts": [],
                "session_id": session.session_id
            }

    def _run_session_agent_loop(
        self,
        session: Session,
        message: str
    ) -> Dict[str, Any]:
        """
        Main agent loop with session state.
        
        Uses session's message history and control layer.
        """
        from app.tools import call_tool
        
        # Add user message to session
        session.add_message("user", message)
        
        # Build messages for LLM (system + session history)
        messages = self._build_messages_from_session(session)
        
        # Use session's control layer
        control_layer = session.control_layer
        
        # Tracking
        all_thoughts = []
        max_turns = 10
        turn_count = 0
        final_response = ""
        
        print(f"[AgentService] Session {session.session_id}: Processing '{message[:50]}...'")
        print(f"[AgentService] Session history: {len(session.messages)} messages")
        
        while turn_count < max_turns:
            turn_count += 1
            print(f"\n--- [AgentLoop] Session {session.session_id} Turn {turn_count}/{max_turns} ---")
            
            try:
                # ========== THINK: Call LLM ==========
                response = self._call_llm(messages)
                
                if not response:
                    print("[AgentLoop] Empty response from LLM")
                    break
                
                response_message = response.choices[0].message
                
                # Record the assistant's response
                all_thoughts.append({
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": self._serialize_tool_calls(response_message.tool_calls)
                })
                
                # Check if LLM wants to call tools
                if response_message.tool_calls:
                    # ========== EXECUTE: Process each tool call ==========
                    # Add assistant message to messages (for next LLM call)
                    messages.append(response_message)
                    
                    # Also add to session (for persistence)
                    session.add_tool_call_message(response_message)
                    
                    should_stop = False
                    
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        print(f"[AgentLoop] Executing tool: {tool_name}")
                        
                        # Record tool call in control layer
                        control_layer.record_tool_call(tool_name, tool_args)
                        
                        # Execute the tool
                        try:
                            tool_result = call_tool(tool_name, tool_args)
                        except Exception as e:
                            tool_result = f"Error executing {tool_name}: {str(e)}"
                        
                        print(f"[AgentLoop] Tool result (prefix): {str(tool_result)[:100]}...")
                        
                        # ========== FEEDBACK: Add tool result ==========
                        tool_msg = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result
                        }
                        messages.append(tool_msg)
                        session.add_tool_result(tool_call.id, tool_name, tool_result)
                        
                        # Record in thoughts
                        all_thoughts.append({
                            "role": "tool",
                            "tool_name": tool_name,
                            "content": tool_result,
                            "is_tool_result": True
                        })
                        
                        # ========== CONTROL: Check termination ==========
                        should_terminate, reason, term_message = control_layer.should_terminate_after_tool(
                            tool_name, tool_result
                        )
                        
                        if should_terminate:
                            print(f"[AgentLoop] 🛑 Termination triggered: {reason.value if reason else 'unknown'}")
                            
                            termination_response = control_layer.get_termination_message(reason, tool_result)
                            
                            if response_message.content:
                                final_response = f"{response_message.content}\n\n{termination_response}"
                            else:
                                final_response = termination_response
                            
                            # Add assistant response to session
                            session.add_message("assistant", final_response)
                            should_stop = True
                            break
                    
                    if should_stop:
                        break
                    
                    continue
                
                else:
                    # ========== DONE: Final response ==========
                    final_response = response_message.content or ""
                    
                    # Add to session history
                    session.add_message("assistant", final_response)
                    
                    print(f"[AgentLoop] Final response received")
                    break
                    
            except Exception as e:
                print(f"[AgentLoop] Error in turn {turn_count}: {e}")
                import traceback
                traceback.print_exc()
                final_response = f"处理过程中出错: {str(e)}"
                session.add_message("assistant", final_response)
                break
        
        if not final_response and turn_count >= max_turns:
            final_response = "⚠️ 达到最大对话轮次限制，请简化您的请求或分步骤进行。"
            session.add_message("assistant", final_response)
        
        # Clean up response
        final_response = self._clean_response(final_response)
        
        print(f"[AgentService] Response: {final_response[:100]}...")
        
        return {
            "response": final_response,
            "thoughts": all_thoughts
        }

    def _build_messages_from_session(self, session: Session) -> List[Dict[str, Any]]:
        """
        Build messages list from session history.
        
        Includes system message + all session messages.
        """
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": config.agent.system_message
        })
        
        # Add session history
        for msg in session.messages:
            # Handle different message types
            if isinstance(msg, dict):
                messages.append(msg)
            else:
                # OpenAI message object
                messages.append(msg)
        
        return messages

    # ==================== Legacy API (without session) ====================

    async def process_message_async(
        self, 
        message: str, 
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process a message using the OpenAI API with function calling.
        
        LEGACY API: Creates a temporary session for this request.
        For persistent conversations, use chat_with_session() instead.
        
        Args:
            message: The user's message
            history: Optional conversation history
            
        Returns:
            Dict containing 'response' (str) and 'thoughts' (List[Dict])
        """
        await self._ensure_initialized()
        
        if self._client is None:
            return {
                "response": "[Agent未初始化] 无法处理消息，请检查配置。",
                "thoughts": []
            }
        
        try:
            # Run the agent loop in a thread pool
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._run_agent_loop, message, history)
            return result
            
        except Exception as e:
            error_msg = f"处理消息时发生错误: {str(e)}"
            print(f"[AgentService] Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                "response": error_msg,
                "thoughts": []
            }

    def _run_agent_loop(
        self, 
        message: str, 
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Main agent loop - Think-Execute-Feedback cycle.
        
        LEGACY: Uses provided history instead of session.
        """
        from app.tools import call_tool
        
        # Create temporary control layer for this request
        control_layer = ControlLayer(ControlLayerConfig())
        
        # Build messages list
        messages = self._build_messages(message, history)
        
        # Tracking
        all_thoughts = []
        max_turns = 10
        turn_count = 0
        final_response = ""
        
        print(f"[AgentService] Starting agent loop for: {message[:50]}...")
        
        while turn_count < max_turns:
            turn_count += 1
            print(f"\n--- [AgentLoop] Turn {turn_count}/{max_turns} ---")
            
            try:
                # ========== THINK: Call LLM ==========
                response = self._call_llm(messages)
                
                if not response:
                    print("[AgentLoop] Empty response from LLM")
                    break
                
                response_message = response.choices[0].message
                
                # Record the assistant's response
                all_thoughts.append({
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": self._serialize_tool_calls(response_message.tool_calls)
                })
                
                # Check if LLM wants to call tools
                if response_message.tool_calls:
                    # ========== EXECUTE: Process each tool call ==========
                    messages.append(response_message)
                    
                    should_stop = False
                    
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        print(f"[AgentLoop] Executing tool: {tool_name}")
                        print(f"[AgentLoop] Arguments: {json.dumps(tool_args, ensure_ascii=False)[:200]}")
                        
                        # Record tool call in control layer
                        control_layer.record_tool_call(tool_name, tool_args)
                        
                        # Execute the tool
                        try:
                            tool_result = call_tool(tool_name, tool_args)
                        except Exception as e:
                            tool_result = f"Error executing {tool_name}: {str(e)}"
                        
                        print(f"[AgentLoop] Tool result (prefix): {str(tool_result)[:100]}...")
                        
                        # ========== FEEDBACK: Add tool result to messages ==========
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result
                        })
                        
                        # Record in thoughts
                        all_thoughts.append({
                            "role": "tool",
                            "tool_name": tool_name,
                            "content": tool_result,
                            "is_tool_result": True
                        })
                        
                        # ========== CONTROL: Check termination conditions ==========
                        should_terminate, reason, term_message = control_layer.should_terminate_after_tool(
                            tool_name, tool_result
                        )
                        
                        if should_terminate:
                            print(f"[AgentLoop] 🛑 Termination triggered: {reason.value if reason else 'unknown'}")
                            print(f"[AgentLoop] Message: {term_message}")
                            
                            termination_response = control_layer.get_termination_message(reason, tool_result)
                            
                            if response_message.content:
                                final_response = f"{response_message.content}\n\n{termination_response}"
                            else:
                                final_response = termination_response
                            
                            should_stop = True
                            break
                    
                    if should_stop:
                        break
                    
                    continue
                
                else:
                    # ========== DONE: LLM gave final response ==========
                    final_response = response_message.content or ""
                    print(f"[AgentLoop] Final response received (no more tool calls)")
                    break
                    
            except Exception as e:
                print(f"[AgentLoop] Error in turn {turn_count}: {e}")
                import traceback
                traceback.print_exc()
                final_response = f"处理过程中出错: {str(e)}"
                break
        
        if not final_response and turn_count >= max_turns:
            final_response = "⚠️ 达到最大对话轮次限制，请简化您的请求或分步骤进行。"
        
        # Clean up response
        final_response = self._clean_response(final_response)
        
        print(f"[AgentService] Response generated: {final_response[:100]}...")
        
        return {
            "response": final_response,
            "thoughts": all_thoughts
        }

    def _call_llm(self, messages: List[Dict[str, Any]]) -> Any:
        """
        Call the LLM with messages and tools.
        
        Returns the raw response from OpenAI API.
        """
        try:
            params = {
                "model": config.llm.model,
                "messages": messages,
                "temperature": config.llm.temperature,
            }
            
            if self._tools:
                params["tools"] = self._tools
                params["tool_choice"] = "auto"
            
            response = self._client.chat.completions.create(**params)
            return response
            
        except Exception as e:
            print(f"[AgentService] LLM call error: {e}")
            raise

    def _build_messages(
        self, 
        message: str, 
        history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Build the messages list for the LLM.
        
        Includes system message, history, and current user message.
        """
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": config.agent.system_message
        })
        
        # Add history if provided
        if history:
            for msg in history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                
                if role == 'tool':
                    role = 'user'
                    tool_name = msg.get('tool_name', 'unknown')
                    content = f"[Previous tool result: {tool_name}]\n{content}"
                elif role not in ['user', 'assistant', 'system']:
                    role = 'user'
                
                messages.append({'role': role, 'content': content})
        
        # Add current user message
        messages.append({'role': 'user', 'content': message})
        
        return messages

    def _serialize_tool_calls(self, tool_calls) -> Optional[List[Dict[str, Any]]]:
        """Serialize tool calls for storage in thoughts."""
        if not tool_calls:
            return None
        
        return [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in tool_calls
        ]

    def _clean_response(self, text: str) -> str:
        """Clean up model response to remove formatting artifacts."""
        import re
        
        if not text:
            return text
        
        # Remove <think>...</think> blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'</think>', '', text)
        text = re.sub(r'<think>.*$', '', text, flags=re.DOTALL)
        
        # Remove tool_call blocks if they leaked through
        text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
        
        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        text = text.strip()
        
        return text

    def process_message(
        self, 
        message: str, 
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for process_message_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(
                    asyncio.run, 
                    self.process_message_async(message, history)
                ).result()
        else:
            return loop.run_until_complete(self.process_message_async(message, history))

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools in OpenAI format."""
        return self._tools


# Global agent service instance
_agent_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """Get the global agent service instance."""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance