"""
MCP Tools Integration Test

Tests all MCP tools in ads_server.py to verify they work correctly.
This simulates calling each tool and checking the response.

Run this AFTER starting the ADS server in ADS Python console.
"""

import sys
import os
import json
import asyncio

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "ads_plugin"))

# Import the workflow manager and reset it
from workflow_manager import reset_workflow_manager, get_workflow_manager, WorkflowState

# Reset state before testing
reset_workflow_manager()

# Import the MCP server module (this loads all the tool functions)
import ads_server

# Get the workflow manager
wm = get_workflow_manager()

print("=" * 70)
print("MCP Tools Integration Test")
print("=" * 70)
print(f"Initial State: {wm.state.value}")
print(f"Allowed Tools: {list(wm.get_allowed_tools())}")
print()


async def test_tool(tool_func, *args, **kwargs):
    """Test a tool function and return the result."""
    try:
        result = await tool_func(*args, **kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def run_all_tests():
    """Run all tool tests in order."""
    
    results = {}
    
    # ===================== Phase 1: IDLE State =====================
    print("\n" + "=" * 50)
    print("PHASE 1: IDLE STATE")
    print("=" * 50)
    
    # Test 1: check_connection
    print("\n[1] Testing check_connection...")
    result = await test_tool(ads_server.check_connection)
    results["check_connection"] = result
    if result["success"]:
        print(f"    ✓ Success")
        # Parse and show connection status
        try:
            data = json.loads(result["result"])
            msg = data.get("message", "No message")
            print(f"    Message: {msg[:100]}...")
        except:
            print(f"    Result: {result['result'][:200]}...")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 2: get_workflow_status
    print("\n[2] Testing get_workflow_status...")
    result = await test_tool(ads_server.get_workflow_status)
    results["get_workflow_status"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 3: get_current_design
    print("\n[3] Testing get_current_design...")
    result = await test_tool(ads_server.get_current_design)
    results["get_current_design"] = result
    if result["success"]:
        print(f"    ✓ Success")
        try:
            data = json.loads(result["result"])
            print(f"    State: {data.get('_internal', {}).get('workflow_state', 'N/A')}")
        except:
            pass
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 4: get_project_structure
    print("\n[4] Testing get_project_structure...")
    result = await test_tool(ads_server.get_project_structure)
    results["get_project_structure"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 5: reset_workflow (should say already IDLE)
    print("\n[5] Testing reset_workflow (should say already IDLE)...")
    result = await test_tool(ads_server.reset_workflow)
    results["reset_workflow_idle"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # ===================== Phase 2: PLANNING Phase =====================
    print("\n" + "=" * 50)
    print("PHASE 2: PLAN_CIRCUIT")
    print("=" * 50)
    
    # Test 6: plan_circuit
    print("\n[6] Testing plan_circuit...")
    test_components = [
        {"type": "R", "name": "R1", "x": 0, "y": 0, "value": "1k"},
        {"type": "C", "name": "C1", "x": 100, "y": 0, "value": "10nF"},
        {"type": "GROUND", "name": "GND1", "x": 50, "y": 100},
    ]
    result = await test_tool(
        ads_server.plan_circuit,
        circuit_name="test_mcp_tools",
        circuit_type="test_circuit",
        components=test_components,
        description="Integration test circuit"
    )
    results["plan_circuit"] = result
    if result["success"]:
        print(f"    ✓ Success")
        try:
            data = json.loads(result["result"])
            plan_id = data.get("_internal", {}).get("plan_id", "N/A")
            print(f"    Plan ID: {plan_id}")
        except:
            pass
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Check state after plan_circuit
    print(f"\n    Current State: {wm.state.value}")
    print(f"    Allowed Tools: {list(wm.get_allowed_tools())}")
    
    # ===================== Phase 3: SCHEMATIC_CREATED =====================
    print("\n" + "=" * 50)
    print("PHASE 3: EXECUTE_CIRCUIT_PLAN")
    print("=" * 50)
    
    # Test 7: execute_circuit_plan
    print("\n[7] Testing execute_circuit_plan...")
    result = await test_tool(ads_server.execute_circuit_plan)
    results["execute_circuit_plan"] = result
    if result["success"]:
        print(f"    ✓ Success")
        try:
            data = json.loads(result["result"])
            design_uri = data.get("_internal", {}).get("design_uri", "N/A")
            print(f"    Design URI: {design_uri}")
        except:
            pass
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    print(f"\n    Current State: {wm.state.value}")
    
    # ===================== Phase 4: WAITING_USER =====================
    print("\n" + "=" * 50)
    print("PHASE 4: CONFIRM_DESIGN_OPEN")
    print("=" * 50)
    
    # Test 8: confirm_design_open
    print("\n[8] Testing confirm_design_open...")
    result = await test_tool(ads_server.confirm_design_open)
    results["confirm_design_open"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    print(f"\n    Current State: {wm.state.value}")
    print(f"    Allowed Tools: {list(wm.get_allowed_tools())}")
    
    # ===================== Phase 5: COMPONENT_ADDING =====================
    print("\n" + "=" * 50)
    print("PHASE 5: ADD COMPONENTS")
    print("=" * 50)
    
    design_uri = wm.context.design_uri or "test:test:schematic"
    
    # Test 9: add_component
    print("\n[9] Testing add_component...")
    result = await test_tool(
        ads_server.add_component,
        design_uri=design_uri,
        component_type="R",
        instance_name="R_test",
        x=200,
        y=200
    )
    results["add_component"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 10: add_wire
    print("\n[10] Testing add_wire...")
    result = await test_tool(
        ads_server.add_wire,
        design_uri=design_uri,
        points=[[0, 0], [100, 0], [100, 100]]
    )
    results["add_wire"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 11: add_components_from_plan
    print("\n[11] Testing add_components_from_plan...")
    result = await test_tool(ads_server.add_components_from_plan)
    results["add_components_from_plan"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 12: save_current_design
    print("\n[12] Testing save_current_design...")
    result = await test_tool(ads_server.save_current_design, design_uri=design_uri)
    results["save_current_design"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    # Test 13: finish_design
    print("\n[13] Testing finish_design...")
    result = await test_tool(ads_server.finish_design)
    results["finish_design"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    print(f"\n    Final State: {wm.state.value}")
    
    # ===================== Phase 6: Reset Test =====================
    print("\n" + "=" * 50)
    print("PHASE 6: RESET FROM COMPLETED")
    print("=" * 50)
    
    # Test 14: reset_workflow from COMPLETED
    print("\n[14] Testing reset_workflow from COMPLETED...")
    result = await test_tool(ads_server.reset_workflow)
    results["reset_workflow_completed"] = result
    if result["success"]:
        print(f"    ✓ Success")
    else:
        print(f"    ✗ Failed: {result['error']}")
    
    print(f"\n    Final State: {wm.state.value}")
    
    # ===================== Summary =====================
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print()
    
    for name, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"  {status} {name}")
    
    return results


if __name__ == "__main__":
    print("\nStarting MCP Tools Integration Test...")
    print("Note: Make sure ADS Automation Server is running!")
    print()
    
    asyncio.run(run_all_tests())
