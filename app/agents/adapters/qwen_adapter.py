"""Adapter to convert MCP tools to Qwen format."""
import json
import time
import threading
from typing import Dict, Any, List
from qwen_agent.tools.base import BaseTool

# ============== 导入工具包装器和适配器层 ==============
from app.agents.tool_wrapper import wrap_tool_result, ToolResult
from app.agents.adapter_layer import AdapterLayer

# ============== 全局调用计数器（防止无限调用循环） ==============
_tool_call_counter = {
    "total_count": 0,
    "per_tool_count": {},  # 每个工具的调用次数
    "last_reset": time.time(),
    "max_total_calls": 15,  # 每次会话最多调用 15 次工具（总计）
    "max_per_tool_calls": 5,  # 每个工具最多调用 5 次
}
_counter_lock = threading.Lock()


def _check_and_increment_call_count(tool_name: str) -> tuple[bool, str]:
    """
    检查并增加调用计数。
    
    Args:
        tool_name: 工具名称
    
    Returns:
        (is_allowed, message): 是否允许调用，以及消息
    """
    global _tool_call_counter
    
    with _counter_lock:
        # 检查是否超过单个工具的最大调用次数
        per_tool = _tool_call_counter["per_tool_count"].get(tool_name, 0)
        if per_tool >= _tool_call_counter["max_per_tool_calls"]:
            msg = f"⚠️ 工具 '{tool_name}' 已调用 {per_tool} 次，达到上限。请使用其他工具继续任务。"
            print(f"[MCPProxyTool] ⛔ {msg}")
            return False, msg
        
        # 检查是否超过总调用次数
        if _tool_call_counter["total_count"] >= _tool_call_counter["max_total_calls"]:
            return False, f"⚠️ 已达到工具调用总上限 ({_tool_call_counter['max_total_calls']} 次)。请回复确认后再继续。"
        
        # 增加计数
        _tool_call_counter["total_count"] += 1
        _tool_call_counter["per_tool_count"][tool_name] = per_tool + 1
        
        print(f"[MCPProxyTool] Tool '{tool_name}' call #{per_tool + 1}/{_tool_call_counter['max_per_tool_calls']} (total: {_tool_call_counter['total_count']}/{_tool_call_counter['max_total_calls']})")
        
        return True, ""


def reset_tool_call_counter():
    """重置工具调用计数器（在新会话开始时调用）"""
    global _tool_call_counter
    with _counter_lock:
        _tool_call_counter["total_count"] = 0
        _tool_call_counter["per_tool_count"] = {}
        _tool_call_counter["last_reset"] = time.time()
        print("[MCPProxyTool] Tool call counter reset.")


# 工具分类：需要打开原理图的操作类工具
# 注意：create_schematic 和 execute_circuit_plan 不在列表中，
# 因为它们会创建cell，不需要提前打开
TOOLS_REQUIRING_OPEN_DESIGN = {
    "add_component",
    "save_current_design"
}

# ============== 全局适配器层实例 ==============
_adapter_layer = AdapterLayer()


def mcp_tool_to_qwen_tool(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an MCP tool schema to Qwen tool format.

    Args:
        mcp_tool: MCP tool definition

    Returns:
        Qwen-compatible tool definition
    """
    # Extract name and original description
    name = mcp_tool.get('name', '')
    description = mcp_tool.get('description', '')

    # NEW: Inject dynamic constraints into description
    enhanced_description = _adapter_layer.inject_constraints(name, description)

    # Convert MCP input schema to Qwen parameters format
    input_schema = mcp_tool.get('inputSchema', {})
    qwen_params = _convert_input_schema(input_schema)

    return {
        'name': name,
        'description': enhanced_description,  # Use enhanced description
        'parameters': qwen_params
    }


def _convert_input_schema(input_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert MCP input schema to Qwen parameters format.

    Args:
        input_schema: MCP input schema in JSON Schema format

    Returns:
        Qwen parameters format
    """
    properties = input_schema.get('properties', {})
    required = input_schema.get('required', [])

    qwen_params = []

    for prop_name, prop_details in properties.items():
        param = {
            'name': prop_name,
            'type': prop_details.get('type', 'string'),
            'description': prop_details.get('description', ''),
            'required': prop_name in required
        }

        # Handle additional properties like enum, default, etc.
        if 'enum' in prop_details:
            param['enum'] = prop_details['enum']
        if 'default' in prop_details:
            param['default'] = prop_details['default']

        qwen_params.append(param)

    return qwen_params


class MCPProxyTool(BaseTool):
    """
    Proxy tool that delegates to MCP servers.
    This class acts as a bridge between Qwen's expectations and MCP protocol.
    """

    def __init__(self, tool_info: Dict[str, Any]):
        """
        Initialize the MCP proxy tool.

        Args:
            tool_info: Tool information in Qwen format
        """
        # Pass configuration to BaseTool
        super().__init__(cfg=tool_info)

        # Ensure properties are set (BaseTool usually sets these from cfg, but we double check)
        self.name = tool_info.get('name', '')
        self.description = tool_info.get('description', '')
        self.parameters = tool_info.get('parameters', [])

        # Store the original MCP tool name for routing
        self._original_name = tool_info.get('original_name', self.name)

        # Reference to the MCP client manager
        from app.mcp.client import get_mcp_client_manager
        self._mcp_client = get_mcp_client_manager()

    def call(self, params: str, **kwargs) -> str:
        """
        Call the MCP tool through the client manager.

        Args:
            params: JSON string of parameters

        Returns:
            Tool result as string
        """
        import json
        import asyncio

        # ============== 调用计数检查（防止无限循环） ==============
        is_allowed, error_msg = _check_and_increment_call_count(self._original_name)
        if not is_allowed:
            return json.dumps({
                "status": "blocked",
                "error": error_msg,
                "tool_name": self._original_name,
                "suggestion": "请使用其他工具继续任务，或回复确认后重试。"
            }, ensure_ascii=False)

        # Parse parameters
        try:
            arguments = json.loads(params)
        except json.JSONDecodeError as e:
            return f"Error parsing parameters: {str(e)}"

        # 检查是否为需要打开原理图的工具
        if self._original_name in TOOLS_REQUIRING_OPEN_DESIGN:
            # 检查用户是否已确认（跳过检查）
            skip_check = arguments.get("skip_open_check", False)
            if not skip_check:
                # 首次调用，返回提示信息
                return self._generate_design_open_prompt(self._original_name, arguments)

        # Asynchronously call the MCP tool
        # Since this method needs to be synchronous for Qwen compatibility,
        # we'll run the async call in a new event loop if none exists
        try:
            loop = asyncio.get_running_loop()
            # If we're already in a loop, we need to handle differently
            # This is a limitation - we may need to modify the calling code to be async
            import concurrent.futures
            import threading

            def run_async_call():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return asyncio.run(self._async_call_tool(arguments))
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_call)
                result = future.result()

        except RuntimeError:
            # No event loop running (we are in a worker thread)
            # We must use call_tool_sync to schedule execution on the main loop
            # where the MCP session was created.
            try:
                result = self._mcp_client.call_tool_sync(self._original_name, arguments)
            except Exception as e:
                return f"Error executing tool: {str(e)}"

        # NEW: Wrap the result using tool wrapper
        wrapped_result = wrap_tool_result(
            tool_name=self._original_name,
            raw_result=result,
            context={
                "arguments": arguments,
                "tool_name": self._original_name
            }
        )

        # Return wrapped JSON
        return wrapped_result.to_json()

    async def _async_call_tool(self, arguments: Dict[str, Any]) -> Any:
        """
        Asynchronously call the tool via MCP.

        Args:
            arguments: Arguments to pass to the tool

        Returns:
            Tool result
        """
        try:
            result = await self._mcp_client.call_tool(self._original_name, arguments)
            return result
        except Exception as e:
            return {"error": str(e)}

    def _generate_design_open_prompt(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        生成提示用户打开原理图的消息。
        注意：仅对操作类工具（add_component, save_current_design）调用此方法。
        创建类工具（create_schematic, execute_circuit_plan）在call()方法中单独处理。

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            提示消息（JSON格式）
        """
        design_uri = arguments.get("design_uri", "unknown")

        prompt = f"""
📋 **操作: 修改现有设计**

**设计路径**: `{design_uri}`

请按以下步骤操作：

1. **在ADS中打开现有原理图**:
   - 选择 `File -> Open Design`
   - 输入路径: `{design_uri}`

2. **确认原理图已打开后，请回复\"继续执行\"

---

💡 提示: 如果设计不存在，我可以帮您创建一个新设计。
"""

        return json.dumps({
            "status": "requires_design_open",
            "tool_name": tool_name,
            "design_uri": design_uri,
            "message": prompt.strip(),
            "next_action": "请确认原理图已打开后回复\"继续执行\""
        }, ensure_ascii=False, indent=2)


def create_mcp_proxy_tools(mcp_tools: List[Dict[str, Any]]) -> List[MCPProxyTool]:
    """
    Create MCP proxy tools from MCP tool definitions.

    Args:
        mcp_tools: List of MCP tool definitions

    Returns:
        List of MCPProxyTool instances
    """
    qwen_tools = []

    for mcp_tool in mcp_tools:
        # Convert MCP tool to Qwen format
        qwen_tool_def = mcp_tool_to_qwen_tool(mcp_tool)
        qwen_tool_def['original_name'] = mcp_tool.get('name', '')

        tool_name = qwen_tool_def.get('name', 'unknown_tool')

        # Create proxy tool instance
        # Fix for qwen-agent BaseTool validation:
        # We must create a dynamic class for each tool because BaseTool
        # checks the 'name' attribute on the class or requires @register_tool.

        # Define attributes for the dynamic class
        class_attrs = {
            'name': tool_name,
            'description': qwen_tool_def.get('description', ''),
            'parameters': qwen_tool_def.get('parameters', [])
        }

        # Create dynamic subclass of MCPProxyTool
        DynamicToolClass = type(
            f"MCPTool_{tool_name}",
            (MCPProxyTool,),
            class_attrs
        )

        # Instantiate with config
        proxy_tool = DynamicToolClass(qwen_tool_def)
        qwen_tools.append(proxy_tool)

    return qwen_tools
