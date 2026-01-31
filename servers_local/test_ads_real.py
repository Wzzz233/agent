"""
ADS Real Connection Test

Tests actual ADS operations via the ADSClient.
Make sure:
1. ADS 2025 is open
2. ADS Automation Server is running (boot_standalone.py in ADS Python Console)

Run this script to verify ADS control is working.
"""

import sys
import os
import time

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "ads_plugin"))

from ads_client import ADSClient


def test_ads_connection():
    """Test suite for real ADS operations."""
    
    print("=" * 60)
    print("ADS Real Connection Test")
    print("=" * 60)
    
    # Step 1: Connect
    print("\n[1] Connecting to ADS Server...")
    try:
        client = ADSClient(host='localhost', port=5000, timeout=10.0)
        print("    ✓ Client created")
    except Exception as e:
        print(f"    ✗ Failed to create client: {e}")
        return False
    
    # Step 2: Ping
    print("\n[2] Pinging ADS Server...")
    try:
        result = client.ping()
        if result.get("status") == "success":
            print(f"    ✓ Ping successful")
            print(f"    ADS Available: {result.get('data', {}).get('ads_available')}")
            print(f"    QT Available: {result.get('data', {}).get('qt_available')}")
        else:
            print(f"    ✗ Ping failed: {result}")
            return False
    except ConnectionRefusedError:
        print("    ✗ Connection refused - Is ADS Server running?")
        print("    Run this in ADS Python Console:")
        print("    exec(open('C:/Users/Wzzz2/OneDrive/Desktop/agent/ads_plugin/scripting/boot_standalone.py').read())")
        return False
    except Exception as e:
        print(f"    ✗ Ping error: {e}")
        return False
    
    # Step 3: Get workspace info
    print("\n[3] Getting Workspace Info...")
    try:
        result = client.get_workspace_info()
        if result.get("status") == "success":
            data = result.get("data", {})
            print(f"    ✓ Workspace: {data.get('workspace_path', 'N/A')}")
            libs = data.get("libs", [])
            print(f"    ✓ Libraries: {libs if libs else 'None found'}")
        else:
            print(f"    ✗ Failed: {result}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Step 4: List libraries
    print("\n[4] Listing Libraries...")
    try:
        result = client._send_command("list_libraries")
        if result.get("status") == "success":
            libs = result.get("data", {}).get("libraries", [])
            print(f"    ✓ Found {len(libs)} libraries: {libs}")
            if libs:
                test_lib = libs[0]
            else:
                test_lib = None
        else:
            print(f"    ✗ Failed: {result}")
            test_lib = None
    except Exception as e:
        print(f"    ✗ Error: {e}")
        test_lib = None
    
    if not test_lib:
        print("\n    ⚠ No library available for testing. Skipping schematic tests.")
        return True
    
    # Step 5: Create schematic
    test_cell = f"mcp_test_{int(time.time())}"
    print(f"\n[5] Creating Test Schematic: {test_lib}:{test_cell}...")
    try:
        result = client.create_schematic(test_lib, test_cell)
        if result.get("status") == "success":
            design_uri = result.get("data", {}).get("uri", f"{test_lib}:{test_cell}:schematic")
            print(f"    ✓ Schematic created: {design_uri}")
        else:
            print(f"    ✗ Failed: {result}")
            design_uri = None
    except Exception as e:
        print(f"    ✗ Error: {e}")
        design_uri = None
    
    if not design_uri:
        print("\n    ⚠ Could not create schematic. Skipping component tests.")
        return True
    
    # Step 6: Add component (Resistor)
    print("\n[6] Adding Resistor (R1)...")
    try:
        result = client._send_command("add_instance", {
            "design_uri": design_uri,
            "component_lib": "ads_rflib",
            "component_cell": "R",
            "x": 100,
            "y": 100,
            "name": "R1"
        })
        if result.get("status") == "success":
            print(f"    ✓ Resistor R1 added at (100, 100)")
        else:
            print(f"    ✗ Failed: {result}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Step 7: Add component (Capacitor)
    print("\n[7] Adding Capacitor (C1)...")
    try:
        result = client._send_command("add_instance", {
            "design_uri": design_uri,
            "component_lib": "ads_rflib",
            "component_cell": "C",
            "x": 200,
            "y": 100,
            "name": "C1"
        })
        if result.get("status") == "success":
            print(f"    ✓ Capacitor C1 added at (200, 100)")
        else:
            print(f"    ✗ Failed: {result}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Step 8: Add Ground
    print("\n[8] Adding Ground (GND1)...")
    try:
        result = client._send_command("add_instance", {
            "design_uri": design_uri,
            "component_lib": "ads_rflib",
            "component_cell": "GROUND",
            "x": 150,
            "y": 200,
            "name": "GND1"
        })
        if result.get("status") == "success":
            print(f"    ✓ Ground GND1 added at (150, 200)")
        else:
            print(f"    ✗ Failed: {result}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Step 9: Add Wire
    print("\n[9] Adding Wire...")
    try:
        result = client._send_command("add_wire", {
            "design_uri": design_uri,
            "points": [(100, 100), (200, 100)]
        })
        if result.get("status") == "success":
            print(f"    ✓ Wire added from (100,100) to (200,100)")
        else:
            print(f"    ✗ Failed: {result}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Step 10: Save design
    print("\n[10] Saving Design...")
    try:
        result = client._send_command("save_design", {"design_uri": design_uri})
        if result.get("status") == "success":
            print(f"    ✓ Design saved")
        else:
            print(f"    ✗ Failed: {result}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"\nCreated schematic: {design_uri}")
    print("Please check ADS to verify the schematic contains:")
    print("  - Resistor R1 at (100, 100)")
    print("  - Capacitor C1 at (200, 100)")
    print("  - Ground GND1 at (150, 200)")
    print("  - Wire connecting R1 to C1")
    
    return True


if __name__ == "__main__":
    print("\n🔧 Starting ADS Real Connection Test...")
    print("Make sure ADS Automation Server is running!\n")
    
    success = test_ads_connection()
    
    if success:
        print("\n✅ All tests completed!")
    else:
        print("\n❌ Some tests failed. Check ADS connection.")
