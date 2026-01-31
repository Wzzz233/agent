"""
ADS 2025 MCP Server - Live Automation Mode

This MCP server connects to the ADS Automation Server running inside ADS
via Socket, enabling real-time schematic creation and manipulation.

Features:
- Real-time ADS control via Socket client
- User confirmation before execution
- Project structure awareness (workspace/library info)
"""

import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add ads_plugin to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "ads_plugin"))

# MCP imports
from mcp.server import FastMCP

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
logger = logging.getLogger("ads2025-live-server")

# Create MCP server instance
mcp = FastMCP("ads2025-live-server")

# Persistent storage for pending operations (file-based to work across process calls)
PENDING_OPS_FILE = os.path.join(os.path.dirname(__file__), ".pending_operations.json")

def load_pending_operations() -> Dict[str, Any]:
    """Load pending operations from file."""
    try:
        if os.path.exists(PENDING_OPS_FILE):
            with open(PENDING_OPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load pending operations: {e}")
    return {}

def save_pending_operations(ops: Dict[str, Any]):
    """Save pending operations to file."""
    try:
        with open(PENDING_OPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ops, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save pending operations: {e}")

# Global state - loaded from file on startup
pending_operations: Dict[str, Any] = load_pending_operations()


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


# ============== MCP Resources ==============

@mcp.resource("ads://connection_status")
def get_connection_status() -> str:
    """
    获取 ADS 连接状态。Agent 应在执行任何操作前检查此资源。
    """
    status = check_ads_connection()
    return json.dumps(status, ensure_ascii=False, indent=2)


@mcp.resource("ads://workspace_info")
def get_workspace_info_resource() -> str:
    """
    获取当前 ADS 工作区信息，包括可用库列表。
    Agent 应使用此信息了解项目结构。
    """
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


@mcp.resource("ads://api_reference")
def get_api_reference() -> str:
    """
    ADS 自动化 API 参考，包含可用的组件和操作。
    """
    reference = """
# ADS Automation API Reference (Live Mode)

## 可用操作

### 1. 工作区操作
- `get_workspace_info`: 获取工作区路径和库列表
- `list_libraries`: 列出所有可写库

### 2. 设计操作
- `create_schematic(lib_name, cell_name)`: 创建新原理图
- `open_design(design_uri)`: 打开现有设计
- `save_design(design_uri)`: 保存设计

### 3. 元件操作
- `add_instance(design_uri, component_lib, component_cell, x, y, name, angle)`: 添加元件

### 4. 连线操作
- `add_wire(design_uri, points)`: 添加连线

## 常用元件库

| 库名 | 元件 | 说明 |
|------|------|------|
| ads_rflib | R, C, L, GROUND | 基本无源元件和接地 |
| ads_rflib | MLIN, MTEE | 微带线元件 |
| ads_sources | V_DC, V_AC, I_DC | 电压源和电流源 |
| ads_simulation | Term, S_Param, DC | 端口和仿真控制 |

## 坐标系统

- ADS 使用浮点坐标，单位通常是 mils 或 mm
- 建议坐标范围: 0-500 用于元件放置
- 元件间距建议: 50-100 单位

## 工作流程

1. 检查连接状态 (ads://connection_status)
2. 获取工作区信息 (ads://workspace_info)
3. 使用 plan_circuit 生成计划并等待用户确认
4. 使用 execute_plan 或直接调用工具执行
"""
    return reference


# ============== MCP Tools ==============

@mcp.tool()
async def check_connection() -> str:
    """
    检查与 ADS 服务器的连接状态。
    在执行任何 ADS 操作前应先调用此工具。
    
    Returns:
        连接状态信息 (JSON)
    """
    status = check_ads_connection()
    return json.dumps(status, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_project_structure() -> str:
    """
    获取 ADS 项目结构，包括工作区路径和可用库。
    Agent 应使用此信息来了解当前项目状态。
    
    Returns:
        项目结构信息 (JSON)
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"error": "ADS client not available"}, ensure_ascii=False)
    
    try:
        # Get workspace info
        ws_result = client.get_workspace_info()
        
        # Get library list
        lib_result = client._send_command("list_libraries")
        
        structure = {
            "workspace": ws_result.get("data", {}),
            "libraries": lib_result.get("data", {}).get("libraries", []),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(structure, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def plan_circuit(
    circuit_name: str,
    circuit_type: str,
    components: List[Dict[str, Any]],
    library_name: Optional[str] = None,
    description: str = ""
) -> str:
    """
    生成电路创建计划，返回给用户确认。不会立即执行。

    用户确认后，需调用 execute_circuit_plan 来执行。

    Args:
        circuit_name: 电路/单元名称 (e.g., "my_filter")
        circuit_type: 电路类型描述 (e.g., "low_pass_filter", "amplifier")
        components: 元件列表，每个元件包含:
            - type: 元件类型，**必须使用以下标准代码**:
              * 基本元件: "R" (电阻), "C" (电容), "L" (电感)
              * 源: "V_DC" (直流电压源), "V_AC" (交流电压源), "I_DC" (直流电流源)
              * 接地: "GROUND" (必须大写)
              * 微带线: "MLIN", "MTEE", "MCROSS"
              * 仿真: "S_Param" (S参数), "DC" (直流), "HB" (谐波平衡)
            - name: 实例名称 (R1, C1, etc.)
            - x, y: 坐标（单位：mils，建议间隔50-100）
            - value: 参数值 (可选, e.g., "50 Ohm", "1 uF", "5 V")
            - angle: 旋转角度 (可选, 0/90/180/270)
        library_name: 目标库名称 (可选，不指定则使用第一个可写库)
        description: 电路描述

    **示例调用**:
    ```python
        components = [
            {"type": "C", "name": "C1", "x": 0, "y": 0, "value": "1uF"},
            {"type": "R", "name": "R1", "x": 50, "y": 0, "value": "1k"},
            {"type": "GROUND", "name": "GND", "x": 100, "y": 0},
            {"type": "V_DC", "name": "V1", "x": 150, "y": 0, "value": "5V"}
        ]
    ```

    Returns:
        计划详情 (JSON)，包含 plan_id 用于后续执行
    """
    import uuid

    logger.info(f"plan_circuit called with: circuit_name={circuit_name}, circuit_type={circuit_type}, component_count={len(components)}")

    # Generate plan ID
    plan_id = str(uuid.uuid4())[:8]

    # Check connection first
    connection_status = check_ads_connection()
    logger.info(f"Connection status: {connection_status.get('connected', False)}")

    # Get available libraries
    available_libs = []
    if connection_status.get("connected"):
        try:
            client = get_ads_client()
            lib_result = client._send_command("list_libraries")
            available_libs = lib_result.get("data", {}).get("libraries", [])
            logger.info(f"Available libraries: {available_libs}")
        except Exception as e:
            logger.error(f"Error getting libraries: {e}")
            pass

    # Determine target library
    target_lib = library_name
    if not target_lib and available_libs:
        target_lib = available_libs[0]
        logger.info(f"Using default library: {target_lib}")

    # Build plan
    plan = {
        "plan_id": plan_id,
        "status": "pending_confirmation",
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
        "instructions": (
            f"Plan generated with ID: {plan_id}\n"
            f"To execute this plan, call execute_circuit_plan with plan_id='{plan_id}'\n"
            f"Awaiting user confirmation."
        )
    }

    # Store plan for later execution and persist to file
    pending_operations[plan_id] = plan
    save_pending_operations(pending_operations)
    logger.info(f"Plan stored with ID: {plan_id}, total pending operations: {len(pending_operations)}")

    # Return with plan_id prominently displayed at the beginning in a machine-readable format
    result_json = json.dumps(plan, ensure_ascii=False, indent=2)
    logger.info(f"Returning plan with ID: {plan_id}")
    return f"PLAN_ID: {plan_id}\n\n{result_json}"

@mcp.tool()
async def execute_circuit_plan(plan_id: Optional[str] = None) -> str:
    """
    执行之前创建的电路计划 - 只创建原理图，不添加元件。

    此工具会创建空的原理图设计并保存，然后提示用户打开设计。
    用户需要在 ADS 中打开设计后，调用 add_components_from_plan 来添加元件。

    Args:
        plan_id: 由 plan_circuit 返回的计划 ID（可选，如果不提供则自动使用最近的计划）

    Returns:
        执行结果 (JSON)，包含 design_uri 和下一步操作提示
    """
    global pending_operations

    logger.info(f"execute_circuit_plan called with plan_id: {plan_id}")

    # Reload pending operations from file (in case they were saved by another process)
    pending_operations = load_pending_operations()
    logger.info(f"Loaded {len(pending_operations)} pending operations from file")

    # 如果没有提供 plan_id，或者是明显错误的 plan_id，使用最近的计划
    if not plan_id or plan_id in ["12345", "example", "test"]:
        if not pending_operations:
            logger.warning("No pending operations found")
            return json.dumps({
                "status": "error",
                "message": "没有待执行的计划。请先调用 plan_circuit 创建计划。"
            }, ensure_ascii=False)

        # 使用最近的计划（字典中最后一个）
        plan_id = list(pending_operations.keys())[-1]
        logger.info(f"No valid plan_id provided, using most recent: {plan_id}")

    # Retrieve plan
    if plan_id not in pending_operations:
        logger.warning(f"Plan {plan_id} not found in pending operations. Available: {list(pending_operations.keys())}")
        return json.dumps({
            "status": "error",
            "message": f"Plan {plan_id} not found. Available plans: {list(pending_operations.keys())}"
        }, ensure_ascii=False)

    logger.info(f"Executing plan with ID: {plan_id}")
    plan = pending_operations[plan_id]

    client = get_ads_client()
    if not client:
        logger.error("ADS client not available")
        return json.dumps({
            "status": "error",
            "message": "ADS client not available"
        }, ensure_ascii=False)

    results = {
        "plan_id": plan_id,
        "steps": [],
        "success": True
    }

    try:
        # Step 1: Create schematic (ONLY - no components yet)
        circuit = plan["circuit"]
        lib_name = circuit["library"]
        cell_name = circuit["name"]

        logger.info(f"Creating schematic: {lib_name}:{cell_name}")
        create_result = client.create_schematic(lib_name, cell_name)
        results["steps"].append({
            "action": "create_schematic",
            "result": create_result
        })

        if create_result.get("status") != "success":
            results["success"] = False
            results["error"] = f"Failed to create schematic: {create_result}"
            logger.error(f"Schematic creation failed: {create_result}")
            return json.dumps(results, ensure_ascii=False, indent=2)

        design_uri = create_result.get("data", {}).get("uri")
        if not design_uri:
            design_uri = f"{lib_name}:{cell_name}:schematic"
            logger.info(f"Using manual URI fallback: {design_uri}")
        else:
            logger.info(f"Schematic created with URI: {design_uri}")

        # Step 2: Save the empty schematic
        logger.info(f"Saving empty schematic: {design_uri}")
        save_result = client._send_command("save_design", {"design_uri": design_uri})
        results["steps"].append({
            "action": "save_design",
            "result": save_result
        })

        # Update plan status to "schematic_created"
        pending_operations[plan_id]["status"] = "schematic_created"
        pending_operations[plan_id]["circuit"]["design_uri"] = design_uri
        save_pending_operations(pending_operations)
        logger.info(f"Plan {plan_id} marked as schematic_created")

        results["design_uri"] = design_uri
        results["next_step"] = "add_components"
        results["instruction"] = (
            f"✓ 原理图已创建: {design_uri}\n"
            f"✓ 设计已保存\n\n"
            f"**重要**：请在 ADS 中打开此设计，然后回复 '已打开' 来添加元件。\n"
            f"或者调用 add_components_from_plan(plan_id='{plan_id}') 来添加元件。"
        )
        results["summary"] = f"原理图 '{cell_name}' 创建成功。请在 ADS 中打开 {design_uri} 后添加元件。"

    except Exception as e:
        logger.error(f"Error executing plan {plan_id}: {str(e)}")
        results["success"] = False
        results["error"] = str(e)

    logger.info(f"Schematic creation completed. Success: {results['success']}")
    return json.dumps(results, ensure_ascii=False, indent=2)


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
    直接向设计添加单个元件（跳过确认步骤）。

    Args:
        design_uri: 设计 URI (格式: "library:cell:schematic")
        component_type: 元件类型 (R, C, L, Term, Ground, etc.)
        instance_name: 实例名称 (R1, C1, etc.)
        x: X 坐标
        y: Y 坐标
        component_lib: 元件库 (默认 "ads_rflib")
        angle: 旋转角度 (可选)

    Returns:
        执行结果 (JSON)
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"status": "error", "message": "ADS client not available"})

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
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def add_wire(
    design_uri: str,
    points: List[List[float]]
) -> str:
    """
    在原理图中添加连线。

    Args:
        design_uri: 设计 URI (格式: "library:cell:schematic")
        points: 连线点列表，每个点是 [x, y] 坐标。例如: [[0, 0], [50, 0], [50, 50]]

    Returns:
        添加结果 (JSON)
    
    示例:
        add_wire("MyLib:cell:schematic", [[0, 0], [100, 0]])  # 水平线
        add_wire("MyLib:cell:schematic", [[0, 0], [0, 100]])  # 垂直线
        add_wire("MyLib:cell:schematic", [[0, 0], [50, 0], [50, 50]])  # L形线
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"status": "error", "message": "ADS client not available"})

    # 将 [[x1,y1], [x2,y2]] 转换为 [(x1,y1), (x2,y2)]
    point_tuples = [(p[0], p[1]) for p in points]
    
    result = client._send_command("add_wire", {
        "design_uri": design_uri,
        "points": point_tuples
    })
    return json.dumps(result, ensure_ascii=False, indent=2)

@mcp.tool()
async def create_schematic(
    cell_name: str,
    library_name: Optional[str] = None
) -> str:
    """
    创建新的原理图设计。

    Args:
        cell_name: 单元/设计名称
        library_name: 库名称 (可选，不指定则使用第一个可写库)

    Returns:
        创建结果，包含 design_uri (JSON)
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"status": "error", "message": "ADS client not available"})

    result = client.create_schematic(library_name or "", cell_name)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def save_current_design(design_uri: str) -> str:
    """
    保存指定的设计。

    Args:
        design_uri: 设计 URI (格式: "library:cell:schematic")

    Returns:
        保存结果 (JSON)
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"status": "error", "message": "ADS client not available"})

    result = client._send_command("save_design", {"design_uri": design_uri})
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_cells(library_name: str) -> str:
    """
    列出指定 library 中的所有 cells。

    Args:
        library_name: 库名称 (例如 "MyLibrary3_lib")

    Returns:
        包含所有 cell 名称的列表 (JSON)
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"error": "ADS client not available"}, ensure_ascii=False)

    try:
        result = client._send_command("list_cells", {"library_name": library_name})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def check_cell_exists(library_name: str, cell_name: str) -> str:
    """
    检查指定的 cell 是否存在。

    Args:
        library_name: 库名称 (例如 "MyLibrary3_lib")
        cell_name: 单元名称 (例如 "my_design")

    Returns:
        检查结果 (JSON)，包含 exists (bool) 和 design_uri
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"error": "ADS client not available"}, ensure_ascii=False)

    try:
        result = client._send_command("check_cell_exists", {
            "library_name": library_name,
            "cell_name": cell_name
        })
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def get_current_design() -> str:
    """
    获取当前在 ADS 中打开的设计信息。

    Returns:
        当前设计的 URI，如果没有打开的设计则返回 None (JSON)
    """
    client = get_ads_client()
    if not client:
        return json.dumps({"error": "ADS client not available"}, ensure_ascii=False)

    try:
        result = client._send_command("get_current_design", {})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def add_components_from_plan(plan_id: Optional[str] = None) -> str:
    """
    向已打开的设计添加元件（从之前的计划中）。

    前提条件：
    - 用户必须已经在 ADS 中打开了对应的设计
    - 设计必须是通过 execute_circuit_plan 创建的

    Args:
        plan_id: 计划 ID（可选，默认使用最近的计划）

    Returns:
        添加结果 (JSON)
    """
    global pending_operations

    # Reload pending operations from file
    pending_operations = load_pending_operations()

    # Get plan_id if not provided
    if not plan_id:
        if not pending_operations:
            return json.dumps({
                "status": "error",
                "message": "没有待执行的计划。请先调用 plan_circuit 创建计划。"
            }, ensure_ascii=False)
        plan_id = list(pending_operations.keys())[-1]
        logger.info(f"No plan_id provided, using most recent: {plan_id}")

    # Retrieve plan
    if plan_id not in pending_operations:
        logger.warning(f"Plan {plan_id} not found. Available: {list(pending_operations.keys())}")
        return json.dumps({
            "status": "error",
            "message": f"Plan {plan_id} not found. Available plans: {list(pending_operations.keys())}"
        }, ensure_ascii=False)

    plan = pending_operations[plan_id]
    client = get_ads_client()

    if not client:
        return json.dumps({"status": "error", "message": "ADS client not available"}, ensure_ascii=False)

    results = {
        "plan_id": plan_id,
        "steps": [],
        "success": True
    }

    try:
        # Get design_uri from plan
        circuit = plan["circuit"]
        design_uri = circuit.get("design_uri")

        if not design_uri:
            return json.dumps({
                "status": "error",
                "message": "Plan does not contain design_uri. Please call execute_circuit_plan first."
            }, ensure_ascii=False)

        logger.info(f"Adding components to design: {design_uri}")

        # Add components
        failed_count = 0

        for comp in plan["components"]:
            comp_type = comp.get("type", "R")
            comp_name = comp.get("name", "")
            x = comp.get("x", 0)
            y = comp.get("y", 0)
            angle = comp.get("angle")
            value = comp.get("value")

            # Determine library and cell name based on component type
            # 正确的库映射（根据 ADS 2025）:
            # - ads_rflib: R, C, L, GROUND
            # - ads_sources: V_DC, V_AC, I_DC
            # - ads_simulation: Term, S_Param, DC
            if comp_type in ["V_DC", "V_AC", "I_DC", "P_1Tone", "Vsrc", "VCC", "Power", "DC_Source"]:
                comp_lib = "ads_sources"
                if comp_type in ["Vsrc", "VCC", "Power", "DC_Source"]:
                    real_cell_name = "V_DC"
                else:
                    real_cell_name = comp_type
            elif comp_type in ["R", "C", "L", "DC_Block", "DC_Feed", "MLIN", "MTEE", "MCROSS", "TLIN"]:
                comp_lib = "ads_rflib"
                real_cell_name = comp_type
            elif comp_type in ["Ground", "GND", "GROUND"]:
                comp_lib = "ads_rflib"
                real_cell_name = "GROUND"  # Must be uppercase
            elif comp_type in ["Term", "DC", "S_Param", "HB", "Trans", "SP"]:
                # Term 和仿真控制都在 ads_simulation
                comp_lib = "ads_simulation"
                if comp_type == "S_Param":
                    real_cell_name = "S_Param"  # 保持原名
                elif comp_type == "SP":
                    real_cell_name = "S_Param"  # SP 是 S_Param 的别名
                else:
                    real_cell_name = comp_type
            elif comp_type in ["I_Probe"]:
                comp_lib = "ads_common_cmpts"
                real_cell_name = comp_type
            else:
                # Default fallback
                comp_lib = "ads_rflib"
                real_cell_name = comp_type

            logger.info(f"Adding component: {real_cell_name} from {comp_lib} at ({x}, {y})")

            params = {}
            if value:
                if real_cell_name == "R":
                    params["R"] = value
                elif real_cell_name == "C":
                    params["C"] = value
                elif real_cell_name == "L":
                    params["L"] = value
                elif real_cell_name == "V_DC":
                    params["Vdc"] = value

            # Prepare payload
            payload = {
                "design_uri": design_uri,
                "component_lib": comp_lib,
                "component_cell": real_cell_name,
                "x": x,
                "y": y,
                "name": comp_name
            }

            # Add angle if provided
            if angle is not None:
                payload["angle"] = angle

            # Add parameters if any
            if params:
                payload["parameters"] = params

            # Send command
            add_result = client._send_command("add_instance", payload)

            step_result = {
                "action": "add_instance",
                "component": comp_name,
                "type": comp_type,
                "result": add_result
            }
            results["steps"].append(step_result)

            if add_result.get("status") != "success":
                logger.warning(f"Failed to add {comp_name}: {add_result}")
                failed_count += 1
            else:
                logger.info(f"Successfully added {comp_name}")

        # Save design
        logger.info(f"Saving design: {design_uri}")
        save_result = client._send_command("save_design", {"design_uri": design_uri})
        results["steps"].append({
            "action": "save_design",
            "result": save_result
        })

        results["design_uri"] = design_uri
        if failed_count > 0:
            results["success"] = False
            results["summary"] = f"添加了元件，但有 {failed_count} 个失败。"
        else:
            results["summary"] = f"成功添加 {len(plan['components'])} 个元件。"

    except Exception as e:
        logger.error(f"Error adding components from plan {plan_id}: {str(e)}")
        results["success"] = False
        results["error"] = str(e)

    logger.info(f"Component addition completed. Success: {results['success']}")
    return json.dumps(results, ensure_ascii=False, indent=2)


# ============== Main ==============

if __name__ == "__main__":
    logger.info("ADS2025 Live MCP Server 启动中...")
    logger.info(f"ADS Client Available: {ADS_CLIENT_AVAILABLE}")
    
    # Check initial connection
    status = check_ads_connection()
    if status.get("connected"):
        logger.info("ADS 服务器连接成功！")
    else:
        logger.warning(f"ADS 服务器未连接: {status.get('error')}")
        logger.info("请在ADS中启动服务器后再使用自动化功能。")
    
    mcp.run()