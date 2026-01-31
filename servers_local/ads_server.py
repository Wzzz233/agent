"""
ADS 2025 MCP Server - Stateful Workflow Mode

This MCP server implements the MCP 1.0 protocol with:
- Workflow State Machine for structured design flow
- Dynamic tool visibility based on current state
- Dynamic prompt injection for context-aware LLM guidance
- Proper capability negotiation

Architecture:
    MCP Client <-> ads_server.py (Protocol) <-> workflow_manager.py (State) <-> ads_client.py (ADS)
"""

import sys
import os
import logging
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add ads_plugin to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "ads_plugin"))

# MCP imports
from mcp.server import FastMCP

# Workflow Manager import
from workflow_manager import (
    get_workflow_manager,
    WorkflowManager,
    WorkflowState,
)

# ADS Client import
try:
    from ads_client import ADSClient
    ADS_CLIENT_AVAILABLE = True
except ImportError:
    ADS_CLIENT_AVAILABLE = False
    ADSClient = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ads2025-stateful-server")

# ============== MCP Server Instance ==============

mcp = FastMCP("ads2025-stateful-server")


# Server capabilities (for MCP initialize response)
SERVER_CAPABILITIES = {
    "ads_version": "2025_update2",
    "workflow_modes": ["stateful"],
    "features": {
        "dynamic_tools": True,
        "state_persistence": True,
        "prompt_injection": True,
    }
}


# ============== Helper Functions ==============

def get_ads_client() -> Optional[ADSClient]:
    """Get an ADS client instance, or None if not available."""
    if not ADS_CLIENT_AVAILABLE:
        return None
    try:
        client = ADSClient(host='localhost', port=5000, timeout=10.0)
        return client
    except Exception as e:
        logger.error(f"Failed to create ADS client: {e}")
        return None


def check_ads_connection() -> Dict[str, Any]:
    """Check if ADS server is running and return status."""
    client = get_ads_client()
    if not client:
        return {
            "connected": False,
            "error": "ADS client not available. Make sure ads_client.py is in the path."
        }
    
    try:
        result = client.ping()
        if result.get("status") == "success":
            return {
                "connected": True,
                "ads_available": result.get("data", {}).get("ads_available", False),
                "qt_available": result.get("data", {}).get("qt_available", False)
            }
        else:
            return {
                "connected": False,
                "error": result.get("message", "Unknown error")
            }
    except ConnectionRefusedError:
        return {
            "connected": False,
            "error": "ADS server not running. Please start the server in ADS Python Console:\n"
                     "exec(open('C:/Users/Wzzz2/OneDrive/Desktop/agent/ads_plugin/scripting/boot_standalone.py').read())"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }


def format_human_response(message: str, data: Optional[Dict] = None) -> str:
    """
    Format a structured response for MCP tools.
    
    Returns JSON with:
    - message: Human-readable summary (MOST IMPORTANT)
    - status: success/error
    - data: Optional structured data for agent
    
    The tool_wrapper will extract and format this appropriately.
    """
    result = {
        "status": "success",
        "message": message,
    }
    if data:
        result["data"] = data
    return json.dumps(result, ensure_ascii=False, indent=2)


def check_tool_allowed(tool_name: str) -> Optional[str]:
    """
    Check if a tool is allowed in the current state.
    Returns error message if not allowed, None if OK.
    """
    wm = get_workflow_manager()
    if not wm.is_tool_allowed(tool_name):
        allowed = list(wm.get_allowed_tools())
        return (
            f"工具 '{tool_name}' 在当前状态 ({wm.state.value}) 下不可用。\n"
            f"当前可用工具: {allowed}\n"
            f"如需重置工作流，请使用 reset_workflow 工具。"
        )
    return None


# ============== MCP Resources ==============

@mcp.resource("ads://connection_status")
def get_connection_status() -> str:
    """获取 ADS 连接状态。"""
    status = check_ads_connection()
    return json.dumps(status, ensure_ascii=False, indent=2)


@mcp.resource("ads://workflow_state")
def get_workflow_state_resource() -> str:
    """
    获取当前工作流状态和上下文。
    Agent 应读取此资源以了解当前在哪个阶段。
    """
    wm = get_workflow_manager()
    return json.dumps(wm.get_full_system_context(), ensure_ascii=False, indent=2)


@mcp.resource("ads://workspace_info")
def get_workspace_info_resource() -> str:
    """获取当前 ADS 工作区信息。"""
    client = get_ads_client()
    if not client:
        return json.dumps({"error": "ADS client not available"})
    
    try:
        result = client.get_workspace_info()
        if result.get("status") == "success":
            return json.dumps(result.get("data", {}), ensure_ascii=False, indent=2)
        else:
            return json.dumps({"error": result.get("message", "Unknown error")})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("ads://system_prompt")
def get_system_prompt_resource() -> str:
    """
    获取当前状态的系统提示词。
    这是动态 Prompt 注入的核心 - Agent 应在每次交互前读取此资源。
    """
    wm = get_workflow_manager()
    return wm.get_state_prompt()


@mcp.resource("ads://allowed_tools")
def get_allowed_tools_resource() -> str:
    """
    获取当前状态下可用的工具列表。
    Agent 应只使用此列表中的工具。
    """
    wm = get_workflow_manager()
    return json.dumps({
        "state": wm.state.value,
        "allowed_tools": list(wm.get_allowed_tools())
    }, ensure_ascii=False, indent=2)


# ============== MCP Tools - Always Available ==============

@mcp.tool()
async def check_connection() -> str:
    """
    检查与 ADS 服务器的连接状态。
    此工具在所有状态下都可用。
    
    Returns:
        连接状态信息和当前工作流状态
    """
    wm = get_workflow_manager()
    connection = check_ads_connection()
    
    response = {
        "connection": connection,
        "workflow": {
            "state": wm.state.value,
            "allowed_tools": list(wm.get_allowed_tools())
        }
    }
    
    if connection.get("connected"):
        message = f"✓ ADS 服务器已连接。当前工作流状态: {wm.state.value}"
    else:
        message = f"✗ ADS 服务器未连接: {connection.get('error')}"
    
    return format_human_response(message, response)


@mcp.tool()
async def reset_workflow() -> str:
    """
    重置工作流到初始状态 (IDLE)。
    这是"逃生舱"工具，用于在流程卡住时恢复。
    
    **注意**: 这将清除当前的计划和上下文数据。
    
    Returns:
        重置结果
    """
    wm = get_workflow_manager()
    
    # Can't reset from IDLE (already there)
    if wm.state == WorkflowState.IDLE:
        return format_human_response(
            "工作流已经处于 IDLE 状态，无需重置。",
            {"state": "IDLE"}
        )
    
    result = wm.reset()
    return format_human_response(
        result["message"],
        result
    )


@mcp.tool()
async def get_workflow_status() -> str:
    """
    获取当前工作流状态的详细信息。
    包括当前状态、可用工具、和上下文数据。
    
    Returns:
        工作流状态详情
    """
    wm = get_workflow_manager()
    context = wm.get_full_system_context()
    
    message = (
        f"**工作流状态**: {context['state']}\n\n"
        f"{context['prompt']}\n\n"
        f"**可用工具**: {', '.join(context['allowed_tools'])}"
    )
    
    return format_human_response(message, context)


# ============== MCP Tools - State: IDLE / Project Exploration ==============

@mcp.tool()
async def get_project_structure() -> str:
    """
    获取 ADS 项目结构，包括工作区路径和可用库。
    """
    # Check if tool is allowed
    error = check_tool_allowed("get_project_structure")
    if error:
        return format_human_response(error)
    
    # DEBUG: Capture stdout/stderr for debugging
    import io
    from contextlib import redirect_stdout, redirect_stderr
    log_capture = io.StringIO()
    
    # Try to get client
    client = get_ads_client()
    
    debug_info = []
    debug_info.append(f"Client: {client}")
    
    if not client:
        return format_human_response(f"ADS 客户端不可用。Debug: {'; '.join(debug_info)}")
    
    try:
        ws_result = client.get_workspace_info()
        debug_info.append(f"Workspace: {ws_result}")
        
        lib_result = client._send_command("list_libraries")
        debug_info.append(f"Libs Raw: {lib_result}")
        
        libs = lib_result.get("data", {}).get("libraries", [])
        
        # Build clear message
        message = "**ADS 项目结构**\n\n"
        
        if libs:
            message += f"**用户项目库** (可存放设计):\n"
            for lib in libs:
                message += f"  - `{lib}`\n"
        else:
            message += "⚠️ 没有找到可用的项目库。\n\n"
            message += "**Debugging Info**:\n"
            for info in debug_info:
                message += f"- {info}\n"
        
        message += "\n**元件库**:\n"
        message += "  - `ads_rflib`\n"
        
        structure = {
            "project_libraries": libs,
            "component_libraries": ["ads_rflib", "ads_sources", "ads_simulation"],
            "timestamp": datetime.now().isoformat(),
            "debug": debug_info
        }
        
        return format_human_response(message, structure)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return format_human_response(f"获取项目结构失败: {str(e)}\nTraceback: {tb}")


@mcp.tool()
async def list_cells(library_name: str) -> str:
    """
    列出用户项目库中的所有设计单元(cells)。
    
    **重要**: library_name 应该是用户的项目库（如 "MyLibrary3_lib"），
    不是元件库（如 ads_rflib, ads_sources）！
    
    使用 get_project_structure 工具可以获取可用的项目库列表。
    
    **可用状态**: IDLE
    
    Args:
        library_name: 用户项目库名称 (例如 "MyLibrary3_lib")，不是元件库！
    
    Returns:
        该库中的设计单元列表
    """
    error = check_tool_allowed("list_cells")
    if error:
        return format_human_response(error)
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    try:
        result = client._send_command("list_cells", {"library_name": library_name})
        cells = result.get("data", {}).get("cells", [])
        message = f"库 '{library_name}' 中有 {len(cells)} 个单元: {', '.join(cells[:10]) if cells else '无'}"
        if len(cells) > 10:
            message += f" ... (还有 {len(cells) - 10} 个)"
        return format_human_response(message, result)
    except Exception as e:
        return format_human_response(f"列出单元失败: {str(e)}")


@mcp.tool()
async def check_cell_exists(library_name: str, cell_name: str) -> str:
    """
    检查用户项目库中是否存在指定的设计单元。
    
    **重要**: library_name 应该是用户的项目库（如 "MyLibrary3_lib"），
    不是元件库（如 ads_rflib, ads_sources）！
    
    元件库用于存放 R, C, L 等元器件，用户设计存放在项目库中。
    使用 get_project_structure 工具可以获取可用的项目库列表。
    
    **可用状态**: IDLE
    
    Args:
        library_name: 用户项目库名称 (例如 "MyLibrary3_lib")，不是元件库！
        cell_name: 要查找的设计单元名称
    
    Returns:
        存在性检查结果
    """
    error = check_tool_allowed("check_cell_exists")
    if error:
        return format_human_response(error)
    
    # Validate library_name - it should look like a project library, not a cell name or component library
    known_component_libs = ["ads_rflib", "ads_sources", "ads_simulation"]
    if library_name in known_component_libs:
        return format_human_response(
            f"❌ 错误：'{library_name}' 是元件库，不能用于存放设计！\n\n"
            f"请先调用 `get_project_structure` 获取正确的项目库名（如 MyLibrary3_lib）。",
            {"error": "component_library_used_as_project", "library_name": library_name}
        )
    
    # Check if library_name looks suspicious (same as cell_name, or doesn't contain typical library naming patterns)
    if library_name == cell_name:
        return format_human_response(
            f"❌ 错误：库名和 cell 名相同（'{library_name}'），这通常是错误的！\n\n"
            f"library_name 应该是项目库（如 'MyLibrary3_lib'），不是 cell 名称。\n"
            f"请先调用 `get_project_structure` 获取正确的项目库名。",
            {"error": "library_same_as_cell", "library_name": library_name, "cell_name": cell_name}
        )
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    try:
        result = client._send_command("check_cell_exists", {
            "library_name": library_name,
            "cell_name": cell_name
        })
        exists = result.get("data", {}).get("exists", False)
        if exists:
            message = f"✓ 单元 '{cell_name}' 在库 '{library_name}' 中已存在。"
        else:
            message = f"✗ 单元 '{cell_name}' 在库 '{library_name}' 中不存在。"
        return format_human_response(message, result)
    except Exception as e:
        error_str = str(e)
        # Check for common library not found error
        if "not open" in error_str.lower() or "library" in error_str.lower():
            return format_human_response(
                f"❌ 库 '{library_name}' 不存在或未打开！\n\n"
                f"可能的原因：'{library_name}' 不是有效的项目库名。\n"
                f"请先调用 `get_project_structure` 获取正确的项目库名。",
                {"error": "library_not_found", "library_name": library_name}
            )
        return format_human_response(f"检查单元失败: {error_str}")


@mcp.tool()
async def open_existing_design(library_name: str, cell_name: str) -> str:
    """
    打开现有设计并进入元件添加模式。
    用于在已存在的原理图中添加元件，跳过创建新设计的流程。
    
    **可用状态**: IDLE
    **下一步**: add_component, add_wire
    
    Args:
        library_name: 项目库名称 (例如 "MyLibrary3_lib")
        cell_name: 设计单元名称 (例如 "test_user5")
    
    Returns:
        打开结果，成功后可以直接添加元件
    """
    error = check_tool_allowed("open_existing_design")
    if error:
        return format_human_response(error)
    
    wm = get_workflow_manager()
    client = get_ads_client()
    
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    try:
        # First check if the cell exists
        check_result = client._send_command("check_cell_exists", {
            "library_name": library_name,
            "cell_name": cell_name
        })
        
        exists = check_result.get("data", {}).get("exists", False)
        if not exists:
            return format_human_response(
                f"❌ 设计 '{cell_name}' 在库 '{library_name}' 中不存在！\n\n"
                f"请先确认设计名称，或使用 `plan_circuit` 创建新设计。",
                {"error": "cell_not_found", "library_name": library_name, "cell_name": cell_name}
            )
        
        design_uri = f"{library_name}:{cell_name}:schematic"
        
        # IMPORTANT: Clear any existing plan data - we're opening an existing design,
        # not executing a plan. Agent should use add_component directly.
        wm.context.plan_id = None
        wm.context.plan_data = None
        wm.context.components_added = 0
        wm.context.total_components = 0
        
        # Update workflow context and transition directly to COMPONENT_ADDING
        wm.context.library_name = library_name
        wm.context.cell_name = cell_name
        wm.context.design_uri = design_uri
        wm.transition_to(WorkflowState.COMPONENT_ADDING)
        
        message = (
            f"✓ **准备在现有设计中添加元件**\n\n"
            f"- **设计**: `{design_uri}`\n"
            f"- **状态**: COMPONENT_ADDING\n\n"
            f"⚠️ **重要**: 请确保您已在 ADS 中打开此设计！\n\n"
            f"**注意**: 这是现有设计模式，没有预定义的计划。\n"
            f"请使用 `add_component` 直接添加元件（不要使用 add_components_from_plan）。\n\n"
            f"**可用操作**:\n"
            f"- `add_component(design_uri, component_type, instance_name, x, y)` - 添加单个元件\n"
            f"- `add_wire` - 添加连线\n"
            f"- `save_current_design` - 保存设计\n"
            f"- `finish_design` - 完成工作流"
        )
        
        return format_human_response(message, {
            "design_uri": design_uri,
            "state": WorkflowState.COMPONENT_ADDING.value,
            "library_name": library_name,
            "cell_name": cell_name,
            "mode": "existing_design",
            "has_plan": False
        })
        
    except Exception as e:
        return format_human_response(f"打开设计失败: {str(e)}")


@mcp.tool()
async def get_current_design() -> str:
    """
    获取当前在 ADS 中打开的设计信息，以及当前工作流状态。
    此工具在所有状态下都可用（只读）。
    
    Returns:
        当前设计信息和工作流状态
    """
    wm = get_workflow_manager()
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    try:
        result = client._send_command("get_current_design", {})
        design_uri = result.get("data", {}).get("design_uri")
        
        # Build comprehensive response with workflow guidance
        state = wm.state.value
        allowed_tools = list(wm.get_allowed_tools())
        
        if design_uri:
            message = f"**当前打开的设计**: `{design_uri}`\n"
        else:
            message = "**当前没有打开的设计**\n"
        
        message += f"\n**工作流状态**: {state}\n"
        message += f"**可用工具**: {', '.join(allowed_tools)}\n"
        
        # Add state-specific guidance
        if state == "SCHEMATIC_CREATED":
            message += f"\n⚠️ **下一步**: 请调用 `execute_circuit_plan` 创建原理图文件。"
        elif state == "WAITING_USER":
            message += f"\n⚠️ **下一步**: 用户确认打开设计后，调用 `confirm_design_open`。"
        elif state == "COMPONENT_ADDING":
            message += f"\n**下一步**: 使用 `add_component` 或 `add_components_from_plan` 添加元件。"
        
        return format_human_response(message, {
            "design_uri": design_uri,
            "workflow_state": state,
            "allowed_tools": allowed_tools
        })
    except Exception as e:
        return format_human_response(f"获取当前设计失败: {str(e)}")


# ============== MCP Tools - State: PLANNING ==============

@mcp.tool()
async def plan_circuit(
    circuit_name: str,
    circuit_type: str,
    components: List[Dict[str, Any]],
    library_name: Optional[str] = None,
    description: str = ""
) -> str:
    """
    创建电路设计计划。这是新建设计的第一步。
    
    **可用状态**: IDLE, PLANNING
    **下一步**: execute_circuit_plan
    
    Args:
        circuit_name: 电路名称 (e.g., "my_filter")
        circuit_type: 电路类型 (e.g., "low_pass_filter")
        components: 元件列表，每个包含:
            - type: 元件类型 (R, C, L, GROUND, V_DC, etc.)
            - name: 实例名 (R1, C1, etc.)
            - x, y: 坐标
            - value: 参数值 (可选)
            - angle: 旋转角度 (可选)
        library_name: 目标库 (可选)
        description: 描述
    
    Returns:
        计划详情，包含 plan_id
    """
    error = check_tool_allowed("plan_circuit")
    if error:
        return format_human_response(error)
    
    wm = get_workflow_manager()
    
    logger.info(f"plan_circuit: {circuit_name}, {len(components)} components")
    
    # Generate plan ID
    plan_id = str(uuid.uuid4())[:8]
    
    # Check connection
    connection_status = check_ads_connection()
    
    # Get available libraries
    available_libs = []
    if connection_status.get("connected"):
        try:
            client = get_ads_client()
            lib_result = client._send_command("list_libraries")
            available_libs = lib_result.get("data", {}).get("libraries", [])
        except Exception as e:
            logger.error(f"Error getting libraries: {e}")
    
    # Determine target library
    target_lib = library_name
    if not target_lib and available_libs:
        target_lib = available_libs[0]
    
    # Build plan
    plan = {
        "plan_id": plan_id,
        "status": "pending_execution",
        "connection": connection_status,
        "circuit": {
            "name": circuit_name,
            "type": circuit_type,
            "description": description,
            "library": target_lib,
            "design_uri": f"{target_lib}:{circuit_name}:schematic" if target_lib else None
        },
        "available_libraries": available_libs,
        "components": components,
        "component_count": len(components),
    }
    
    # Store plan in workflow manager
    wm.set_plan(plan_id, plan)
    
    # Format human-friendly message
    message = (
        f"✓ **电路计划已创建**\n\n"
        f"- **Plan ID**: `{plan_id}`\n"
        f"- **电路名称**: {circuit_name}\n"
        f"- **类型**: {circuit_type}\n"
        f"- **目标库**: {target_lib}\n"
        f"- **元件数量**: {len(components)}\n\n"
        f"**下一步**: 调用 `execute_circuit_plan` 创建原理图文件。"
    )
    
    return format_human_response(message, plan)


# ============== MCP Tools - State: SCHEMATIC_CREATED ==============

@mcp.tool()
async def execute_circuit_plan(plan_id: Optional[str] = None) -> str:
    """
    执行电路计划 - 在 ADS 中创建原理图文件。
    
    **可用状态**: SCHEMATIC_CREATED
    **前置条件**: 必须先调用 plan_circuit
    **下一步**: 用户打开设计后，调用 confirm_design_open
    
    Args:
        plan_id: 计划 ID (可选，默认使用最近的计划)
    
    Returns:
        执行结果
    """
    error = check_tool_allowed("execute_circuit_plan")
    if error:
        return format_human_response(error)
    
    wm = get_workflow_manager()
    plan = wm.get_plan()
    
    if not plan:
        return format_human_response(
            "没有待执行的计划。请先调用 plan_circuit 创建计划。"
        )
    
    # Use plan_id from context if not provided
    if not plan_id:
        plan_id = wm.context.plan_id
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    try:
        circuit = plan["circuit"]
        lib_name = circuit["library"]
        cell_name = circuit["name"]
        
        logger.info(f"Creating schematic: {lib_name}:{cell_name}")
        
        # Create schematic
        create_result = client.create_schematic(lib_name, cell_name)
        
        if create_result.get("status") != "success":
            wm.context.error_message = str(create_result)
            return format_human_response(
                f"创建原理图失败: {create_result.get('message', 'Unknown error')}"
            )
        
        design_uri = create_result.get("data", {}).get("uri")
        if not design_uri:
            design_uri = f"{lib_name}:{cell_name}:schematic"
        
        # Save design
        save_result = client._send_command("save_design", {"design_uri": design_uri})
        
        # Update workflow state
        wm.set_design_uri(design_uri)
        wm.transition_to(WorkflowState.WAITING_USER)
        
        message = (
            f"✓ **原理图已创建**\n\n"
            f"- **Design URI**: `{design_uri}`\n"
            f"- **保存状态**: {'成功' if save_result.get('status') == 'success' else '失败'}\n\n"
            f"**⚠️ 重要**: 请在 ADS 中打开此设计:\n"
            f"1. 在 ADS 左侧导航栏找到 `{lib_name}` -> `{cell_name}`\n"
            f"2. 双击打开原理图\n"
            f"3. 回复 '已打开' 或调用 `confirm_design_open`"
        )
        
        return format_human_response(message, {
            "design_uri": design_uri,
            "plan_id": plan_id,
            "next_action": "confirm_design_open"
        })
        
    except Exception as e:
        logger.error(f"Error executing plan: {str(e)}")
        return format_human_response(f"执行计划时出错: {str(e)}")


# ============== MCP Tools - State: WAITING_USER ==============

@mcp.tool()
async def confirm_design_open() -> str:
    """
    确认用户已在 ADS 中打开设计。
    这将解锁元件添加工具。
    
    **可用状态**: WAITING_USER
    **下一步**: add_component, add_components_from_plan
    
    Returns:
        确认结果
    """
    error = check_tool_allowed("confirm_design_open")
    if error:
        return format_human_response(error)
    
    wm = get_workflow_manager()
    
    # Optionally verify with ADS that a design is actually open
    client = get_ads_client()
    if client:
        try:
            result = client._send_command("get_current_design", {})
            current_uri = result.get("data", {}).get("design_uri")
            expected_uri = wm.context.design_uri
            
            if current_uri and expected_uri and current_uri != expected_uri:
                logger.warning(f"Design mismatch: expected {expected_uri}, got {current_uri}")
                # Still allow proceeding, but warn
        except Exception as e:
            logger.warning(f"Could not verify open design: {e}")
    
    # Transition to COMPONENT_ADDING
    wm.transition_to(WorkflowState.COMPONENT_ADDING)
    
    message = (
        f"✓ **设计已确认打开**\n\n"
        f"现在可以添加元件了。可用操作:\n"
        f"- `add_components_from_plan` - 批量添加计划中的所有元件\n"
        f"- `add_component` - 添加单个元件\n"
        f"- `add_wire` - 添加连线\n"
        f"- `save_current_design` - 保存设计\n"
        f"- `finish_design` - 完成设计"
    )
    
    return format_human_response(message, {
        "state": WorkflowState.COMPONENT_ADDING.value,
        "design_uri": wm.context.design_uri
    })


# ============== MCP Tools - State: COMPONENT_ADDING ==============

@mcp.tool()
async def add_component(
    design_uri: str,
    component_type: str,
    instance_name: str,
    x: float,
    y: float,
    component_lib: str = "ads_rflib",
    angle: Optional[float] = None
) -> str:
    """
    添加单个元件到设计。
    
    **可用状态**: COMPONENT_ADDING
    
    Args:
        design_uri: 设计 URI
        component_type: 元件类型 (R, C, L, GROUND, etc.)
        instance_name: 实例名称
        x, y: 坐标
        component_lib: 元件库 (默认 ads_rflib)
        angle: 旋转角度
    
    Returns:
        添加结果
    """
    error = check_tool_allowed("add_component")
    if error:
        return format_human_response(error)
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    wm = get_workflow_manager()
    
    params = {
        "design_uri": design_uri,
        "component_lib": component_lib,
        "component_cell": component_type,
        "x": x,
        "y": y,
        "name": instance_name
    }
    if angle is not None:
        params["angle"] = angle
    
    result = client._send_command("add_instance", params)
    
    if result.get("status") == "success":
        wm.increment_components_added()
        message = f"✓ 已添加元件 {instance_name} ({component_type}) 到坐标 ({x}, {y})"
    else:
        message = f"✗ 添加元件失败: {result.get('message', 'Unknown error')}"
    
    return format_human_response(message, result)


@mcp.tool()
async def add_wire(
    design_uri: str,
    points: List[List[float]]
) -> str:
    """
    添加连线到设计。
    
    **可用状态**: COMPONENT_ADDING
    
    Args:
        design_uri: 设计 URI
        points: 点列表 [[x1,y1], [x2,y2], ...]
    
    Returns:
        添加结果
    """
    error = check_tool_allowed("add_wire")
    if error:
        return format_human_response(error)
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    point_tuples = [(p[0], p[1]) for p in points]
    
    result = client._send_command("add_wire", {
        "design_uri": design_uri,
        "points": point_tuples
    })
    
    if result.get("status") == "success":
        message = f"✓ 已添加连线，包含 {len(points)} 个点"
    else:
        message = f"✗ 添加连线失败: {result.get('message', 'Unknown error')}"
    
    return format_human_response(message, result)


@mcp.tool()
async def add_components_from_plan(plan_id: Optional[str] = None) -> str:
    """
    批量添加计划中的所有元件。
    
    **可用状态**: COMPONENT_ADDING
    **前置条件**: 设计必须已打开 (confirm_design_open)
    
    Args:
        plan_id: 计划 ID (可选)
    
    Returns:
        添加结果摘要
    """
    error = check_tool_allowed("add_components_from_plan")
    if error:
        return format_human_response(error)
    
    wm = get_workflow_manager()
    plan = wm.get_plan()
    
    if not plan:
        return format_human_response("没有待执行的计划。")
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    design_uri = wm.context.design_uri
    if not design_uri:
        return format_human_response("设计 URI 未设置。请先执行 execute_circuit_plan。")
    
    success_count = 0
    failed_count = 0
    results = []
    
    for comp in plan["components"]:
        comp_type = comp.get("type", "R")
        comp_name = comp.get("name", "")
        x = comp.get("x", 0)
        y = comp.get("y", 0)
        angle = comp.get("angle")
        
        # Library mapping
        if comp_type in ["V_DC", "V_AC", "I_DC"]:
            comp_lib = "ads_sources"
            real_cell = comp_type
        elif comp_type in ["Ground", "GND", "GROUND"]:
            comp_lib = "ads_rflib"
            real_cell = "GROUND"
        elif comp_type in ["Term", "S_Param", "DC", "HB"]:
            comp_lib = "ads_simulation"
            real_cell = comp_type
        else:
            comp_lib = "ads_rflib"
            real_cell = comp_type
        
        payload = {
            "design_uri": design_uri,
            "component_lib": comp_lib,
            "component_cell": real_cell,
            "x": x,
            "y": y,
            "name": comp_name
        }
        if angle is not None:
            payload["angle"] = angle
        
        add_result = client._send_command("add_instance", payload)
        
        if add_result.get("status") == "success":
            success_count += 1
            wm.increment_components_added()
        else:
            failed_count += 1
            results.append(f"- {comp_name}: {add_result.get('message', 'Failed')}")
    
    # Save design
    save_result = client._send_command("save_design", {"design_uri": design_uri})
    
    message = (
        f"**元件添加完成**\n\n"
        f"- ✓ 成功: {success_count}\n"
        f"- ✗ 失败: {failed_count}\n"
        f"- 保存: {'成功' if save_result.get('status') == 'success' else '失败'}\n"
    )
    
    if failed_count > 0:
        message += f"\n**失败详情**:\n" + "\n".join(results)
    
    message += f"\n\n**下一步**: 使用 `finish_design` 完成工作流。"
    
    return format_human_response(message, {
        "success": success_count,
        "failed": failed_count,
        "design_uri": design_uri
    })


@mcp.tool()
async def save_current_design(design_uri: str) -> str:
    """
    保存当前设计。
    
    **可用状态**: COMPONENT_ADDING
    
    Args:
        design_uri: 设计 URI
    
    Returns:
        保存结果
    """
    error = check_tool_allowed("save_current_design")
    if error:
        return format_human_response(error)
    
    client = get_ads_client()
    if not client:
        return format_human_response("ADS 客户端不可用")
    
    result = client._send_command("save_design", {"design_uri": design_uri})
    
    if result.get("status") == "success":
        message = f"✓ 设计 `{design_uri}` 已保存"
    else:
        message = f"✗ 保存失败: {result.get('message', 'Unknown error')}"
    
    return format_human_response(message, result)


@mcp.tool()
async def finish_design() -> str:
    """
    完成设计工作流。
    保存设计并将工作流状态重置为 COMPLETED。
    
    **可用状态**: COMPONENT_ADDING
    
    Returns:
        完成确认
    """
    error = check_tool_allowed("finish_design")
    if error:
        return format_human_response(error)
    
    wm = get_workflow_manager()
    design_uri = wm.context.design_uri
    
    # Save design
    client = get_ads_client()
    if client and design_uri:
        client._send_command("save_design", {"design_uri": design_uri})
    
    # Transition to COMPLETED
    wm.transition_to(WorkflowState.COMPLETED)
    
    message = (
        f"✓ **设计工作流已完成**\n\n"
        f"- **设计**: `{design_uri}`\n"
        f"- **添加的元件**: {wm.context.components_added}\n\n"
        f"您可以:\n"
        f"- 使用 `plan_circuit` 开始新设计\n"
        f"- 使用 `reset_workflow` 返回初始状态"
    )
    
    return format_human_response(message, {
        "design_uri": design_uri,
        "components_added": wm.context.components_added,
        "state": WorkflowState.COMPLETED.value
    })


# ============== Main ==============

if __name__ == "__main__":
    logger.info("ADS2025 Stateful MCP Server 启动中...")
    logger.info(f"ADS Client Available: {ADS_CLIENT_AVAILABLE}")
    logger.info(f"Server Capabilities: {SERVER_CAPABILITIES}")
    
    # Initialize workflow manager
    wm = get_workflow_manager()
    logger.info(f"Workflow State: {wm.state.value}")
    
    # Check initial connection
    status = check_ads_connection()
    if status.get("connected"):
        logger.info("✓ ADS 服务器连接成功")
    else:
        logger.warning(f"✗ ADS 服务器未连接: {status.get('error')}")
    
    mcp.run()
