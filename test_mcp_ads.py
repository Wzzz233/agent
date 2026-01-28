
import sys
import os
import time

# Ensure we can import ads_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ads_plugin.ads_client import ADSClient

def test_mcp_ads_fix():
    print("=== Testing MCP Underlying ADS Operations ===")
    
    try:
        client = ADSClient(port=5000)
        pong = client.ping()
        print(f"Ping: {pong}")
        if pong.get("status") != "success":
            print("Failed to ping ADS server.")
            return
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # Check available libraries
    info = client.get_workspace_info()
    print(f"\nWorkspace Info: {info}")
    if info.get("status") == "success":
        libs = info.get("data", {}).get("libs", [])
        print(f"Open Libraries: {libs}")

    lib_name = "MyLibrary3_lib"
    cell_name = "test_analog_rf_fix"
    
    print(f"\n1. Creating Schematic: {lib_name}:{cell_name}")
    try:
        res = client.create_schematic(lib_name, cell_name)
        print(f"Result: {res}")
        design_uri = res.get("data", {}).get("uri")
        if not design_uri:
            design_uri = f"{lib_name}:{cell_name}:schematic"
    except Exception as e:
        print(f"Create Failed: {e}")
        return

    # Test adding components using the new library mapping
    print("\n2. Testing Specific Library Mappings...")
    
    # 1. Source: ads_sources:V_DC
    print("  -> Adding V_DC (ads_sources:V_DC)")
    res = client._send_command("add_instance", {
        "design_uri": design_uri,
        "component_lib": "ads_sources",
        "component_cell": "V_DC",
        "x": 0, "y": 0,
        "name": "V1"
    })
    print(f"     Result: {res}")

    # 2. RF Component: ads_rflib:R
    print("  -> Adding R (ads_rflib:R)")
    res = client._send_command("add_instance", {
        "design_uri": design_uri,
        "component_lib": "ads_rflib",
        "component_cell": "R",
        "x": 50, "y": 0,
        "name": "R1"
    })
    print(f"     Result: {res}")

    # 3. Ground: ads_rflib:GROUND (Must be uppercase)
    print("  -> Adding GROUND (ads_rflib:GROUND)")
    res = client._send_command("add_instance", {
        "design_uri": design_uri,
        "component_lib": "ads_rflib",
        "component_cell": "GROUND",
        "x": 50, "y": 50,
        "name": "GND1"
    })
    print(f"     Result: {res}")

    # 4. Simulation: ads_simulation:SP
    print("  -> Adding SP (ads_simulation:SP)")
    res = client._send_command("add_instance", {
        "design_uri": design_uri,
        "component_lib": "ads_simulation",
        "component_cell": "S_Param",
        "x": 100, "y": 0,
        "name": "S_Param1"
    })
    print(f"     Result: {res}")

    print("\n3. Saving Design")
    res = client._send_command("save_design", {"design_uri": design_uri})
    print(f"Result: {res}")
    
    print("\nTest Complete. Please check 'test_analog_rf_fix' in ADS.")

if __name__ == "__main__":
    test_mcp_ads_fix()
