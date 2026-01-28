"""
Agent Service - Real implementation using Qwen Agent with OpenAI-compatible API
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from app.config.settings import config

# ============== 限制 Qwen Agent 的内部循环次数 ==============
# 这可以防止 LLM 一直调用同一个工具导致无限循环
import qwen_agent.settings
qwen_agent.settings.MAX_LLM_CALL_PER_RUN = 5  # 默认是 20，限制为 5 次

# ============== 导入控制层 ==============
from app.agents.control_layer import ControlLayer, ControlLayerConfig


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
            # CustomAssistant definition removed - properly handling XML loop in process_message_async


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
                
            # === Load MCP Tools ===
            if config.mcp.enabled:
                try:
                    from app.mcp.client import get_mcp_client_manager
                    from app.agents.adapters.qwen_adapter import create_mcp_proxy_tools
                    
                    mcp_manager = get_mcp_client_manager()
                    
                    # Connect to servers
                    print("[AgentService] Connecting to MCP servers...")
                    await mcp_manager.connect_all()
                    
                    # Get tool definitions
                    mcp_defs = mcp_manager.get_all_tools_definitions()
                    print(f"[AgentService] Found {len(mcp_defs)} MCP tools")
                    
                    if mcp_defs:
                        # Convert to Qwen tools
                        mcp_proxy_tools = create_mcp_proxy_tools(mcp_defs)
                        self._tools.extend(mcp_proxy_tools)
                        for t in mcp_proxy_tools:
                            print(f"[AgentService] Added MCP tool: {t.name}")
                            
                except Exception as e:
                    print(f"[AgentService] Failed to load MCP tools: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Create the Assistant agent (using standard Assistant, loop handled manually)
            # Remove function_list here if we don't want Qwen to manage tools via OpenAI API
            # But we keep it so agent knows about them, though we'll bypass standard loop
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
                    
                    # ✅ 修复：过滤不支持的角色
                    if role not in ['user', 'assistant', 'system']:
                        if role == 'tool':
                            role = 'user'
                            # 可选：保留工具信息的上下文
                            tool_name = msg.get('tool_name', 'unknown')
                            content = f"[Previous tool call: {tool_name}]\n{content}"
                        else:
                            role = 'user'  # 其他未知角色统一转为 user
                    
                    messages.append({'role': role, 'content': content})
            
            # Add current message
            messages.append({'role': 'user', 'content': message})
            
            # 重置全局工具调用计数器（每次新消息开始时）
            try:
                from app.agents.adapters.qwen_adapter import reset_tool_call_counter
                reset_tool_call_counter()
            except ImportError:
                pass  # 如果导入失败，继续执行
            
            print(f"[AgentService] Processing message: {message[:50]}...")
            
            # Run the agent in a separate thread
            def run_agent_worker():
                import re
                import json

                current_messages = list(messages)
                max_turns = 10  # 增加轮次，因为每轮只调用一个工具
                turn_count = 0

                final_text = ""
                all_thoughts = []

                # NEW: Initialize control layer
                control_config = ControlLayerConfig()
                control_layer = ControlLayer(control_config)

                # 初始化循环检测变量
                last_tool_call_sig = ""
                tool_loop_count = 0
                tools_called_in_turn = []

                # 简化：每轮只允许调用一个工具
                while turn_count < max_turns:
                    turn_count += 1
                    print(f"--- [AgentWorker] Turn {turn_count}/{max_turns} ---")
                    
                    resp_txt = ""
                    last_response = []
                    
                    try:
                        for response in self._agent.run(messages=current_messages):
                            if isinstance(response, list) and len(response) > 0:
                                last_response = response
                                last_msg = response[-1]
                                if isinstance(last_msg, dict):
                                    content = last_msg.get('content', '')
                                    if content:
                                        resp_txt = content
                    except Exception as e:
                        print(f"[AgentWorker] Error in LLM call: {e}")
                        break
                    
                    if not resp_txt:
                        break

                    final_text = resp_txt
                        
                    # Parse tool call
                    tool_found = False
                    
                    if isinstance(resp_txt, str) and '<tool_call>' in resp_txt:
                        try:
                            pattern = r"<tool_call>(.*?)</tool_call>"
                            match = re.search(pattern, resp_txt, re.DOTALL)
                            if match:
                                json_str = match.group(1).strip()
                                if json_str.startswith("```json"): json_str = json_str[7:]
                                if json_str.startswith("```"): json_str = json_str[3:]
                                if json_str.endswith("```"): json_str = json_str[:-3]
                                
                                tool_call_data = json.loads(json_str)
                                tool_name = tool_call_data.get('name')
                                tool_args = tool_call_data.get('arguments', {})

                                # NEW: Record tool call in control layer
                                control_layer.record_tool_call(tool_name, tool_args)

                                # Loop detection
                                current_sig = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                                if current_sig == last_tool_call_sig:
                                    tool_loop_count += 1
                                else:
                                    tool_loop_count = 0
                                last_tool_call_sig = current_sig
                                
                                if tool_loop_count >= 3:
                                    print(f"[AgentWorker] DETECTED INFINITE LOOP on {tool_name}. Stopping.")
                                    final_text = resp_txt + "\n\n(System: Tool loop detected, stopping execution)"
                                    break

                                print(f"[AgentWorker] Executing tool: {tool_name}")
                                print(f"[AgentWorker] Tools called in this turn: {tools_called_in_turn + [tool_name]}")

                                # 防止过多工具调用
                                tools_called_in_turn.append(tool_name)
                                if len(tools_called_in_turn) > 8:
                                    print(f"[AgentWorker] ⚠️ Too many tools called ({len(tools_called_in_turn)}). Stopping.")
                                    final_text = resp_txt + "\n\n(System: Called too many tools, please confirm before continuing)"
                                    break

                                # Execute
                                tool_result = "Tool execution failed"
                                target_tool = next((t for t in self._tools if t.name == tool_name), None)
                                
                                if target_tool:
                                    try:
                                        args_to_pass = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
                                        tool_result = target_tool.call(args_to_pass)
                                    except Exception as te:
                                        tool_result = f"Error executing {tool_name}: {str(te)}"
                                else:
                                    tool_result = f"Tool {tool_name} not found"
                                    
                                print(f"[AgentWorker] Tool Result (prefix): {str(tool_result)[:100]}...")

                                # ✅ 检查是否被阻止（全局计数器限制）
                                if isinstance(tool_result, str) and '"status": "blocked"' in tool_result:
                                    print(f"[AgentWorker] ⛔ Tool call blocked by rate limiter. Stopping immediately.")
                                    final_text = tool_result
                                    break

                                # NEW: Check termination AFTER tool execution
                                should_terminate, reason, message = control_layer.should_terminate_after_tool(
                                    tool_name, tool_result
                                )

                                if should_terminate:
                                    print(f"[AgentWorker] 🛑 Termination triggered: {reason.value}")
                                    print(f"[AgentWorker] Message: {message}")

                                    # Generate user-friendly response
                                    termination_message = control_layer.get_termination_message(reason, tool_result)
                                    final_text = f"{resp_txt}\n\n{termination_message}"

                                    # Append to conversation history
                                    current_messages.append({'role': 'assistant', 'content': resp_txt})
                                    current_messages.append({'role': 'user', 'content': f"Tool: {tool_name}\nResult: {termination_message}"})

                                    all_thoughts.append(last_msg)
                                    all_thoughts.append({
                                        'role': 'user',
                                        'content': termination_message,
                                        'tool_name': tool_name,
                                        'is_tool_result': True,
                                        'termination_reason': reason.value
                                    })

                                    break  # Exit loop

                                # Append to history
                                current_messages.append({'role': 'assistant', 'content': resp_txt})
                                current_messages.append({'role': 'user', 'content': f"<tool_response>\n{tool_result}\n</tool_response>"})
                                
                                tool_found = True
                                
                                # ✅ 修复：不使用 'tool' 角色
                                all_thoughts.append(last_msg)
                                all_thoughts.append({
                                    'role': 'user',  # 改为 user 而不是 tool
                                    'content': f"Tool: {tool_name}\nResult: {tool_result}",
                                    'tool_name': tool_name,
                                    'is_tool_result': True  # 标记用于前端显示
                                })

                        except Exception as parse_e:
                            print(f"[AgentWorker] Error parsing XML: {parse_e}")
                    
                    if not tool_found:
                        if last_response:
                            all_thoughts.append(last_response[-1])
                        break
                
                return final_text, all_thoughts

            # Execute in thread pool
            loop = asyncio.get_running_loop()
            response_text, final_responses = await loop.run_in_executor(None, run_agent_worker)
            
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
            
    def process_message(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Synchronous wrapper for process_message_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
             # We are already in a loop, this is tricky if called from sync. 
             # But usually Flask is threaded.
             # If we are here, we might need a thread-safe way.
             # However, assuming standard usage:
             import concurrent.futures
             with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, self.process_message_async(message, history)).result()
        else:
            return loop.run_until_complete(self.process_message_async(message, history))


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