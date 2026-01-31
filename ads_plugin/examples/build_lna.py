"""
Example: Build a Simple LNA Circuit in ADS

This script demonstrates using the ADS automation client to:
1. Create a new schematic
2. Add components (transistor, resistors, capacitors)
3. Connect them with wires
4. Save the design

Prerequisites:
1. ADS 2025 is running with the automation workspace loaded
2. The boot.ael/boot.py server is active (check ADS status window)
"""

import sys
import os

# Add parent directory to path for importing ads_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ads_plugin.ads_client import ADSClient


def build_simple_lna():
    """Build a simple Low Noise Amplifier schematic."""
    
    # Connect to ADS
    client = ADSClient(host='localhost', port=5000)
    
    print("=" * 50)
    print("ADS Automation: Simple LNA Builder")
    print("=" * 50)
    
    # Step 1: Check server status
    print("\n[1] Checking server status...")
    result = client.ping()
    if result.get("status") != "success":
        print(f"    ✗ Server error: {result}")
        return False
    print(f"    ✓ Server is running. ADS API: {result['data'].get('ads_available')}")
    
    # Step 2: Get workspace info
    print("\n[2] Getting workspace info...")
    result = client.get_workspace_info()
    if result.get("status") == "success":
        data = result.get("data", {})
        print(f"    Workspace: {data.get('workspace_path', 'N/A')}")
        print(f"    Libraries: {data.get('libraries', [])}")
    
    # Step 3: Create schematic
    print("\n[3] Creating schematic 'work:simple_lna'...")
    result = client.create_schematic("work", "simple_lna")
    if result.get("status") == "success":
        print(f"    ✓ Created: {result['data']}")
    else:
        print(f"    ✗ Error: {result}")
        return False
    
    # Step 4: Add components
    print("\n[4] Adding components...")
    
    # Input coupling capacitor
    result = client.add_instance(
        "ads_rflib", "C",
        x=1.0, y=3.0, 
        name="C_in",
        parameters={"C": "10 pF"}
    )
    print(f"    C_in: {result.get('status')}")
    
    # Bias resistor
    result = client.add_instance(
        "ads_rflib", "R",
        x=3.0, y=5.0,
        angle=90,
        name="R_bias",
        parameters={"R": "10 kOhm"}
    )
    print(f"    R_bias: {result.get('status')}")
    
    # Load resistor
    result = client.add_instance(
        "ads_rflib", "R",
        x=5.0, y=5.0,
        angle=90,
        name="R_load",
        parameters={"R": "1 kOhm"}
    )
    print(f"    R_load: {result.get('status')}")
    
    # Output coupling capacitor
    result = client.add_instance(
        "ads_rflib", "C",
        x=7.0, y=3.0,
        name="C_out",
        parameters={"C": "10 pF"}
    )
    print(f"    C_out: {result.get('status')}")
    
    # Step 5: Add wires (simplified - actual coordinates depend on component symbol sizes)
    print("\n[5] Adding wires...")
    
    # Connect C_in to center
    result = client.add_wire([(2.0, 3.0), (3.0, 3.0)])
    print(f"    C_in to center: {result.get('status')}")
    
    # Connect center to C_out
    result = client.add_wire([(5.0, 3.0), (6.0, 3.0)])
    print(f"    Center to C_out: {result.get('status')}")
    
    # Step 6: Save design
    print("\n[6] Saving design...")
    result = client.save_design()
    if result.get("status") == "success":
        print("    ✓ Design saved successfully!")
    else:
        print(f"    ✗ Save error: {result}")
    
    print("\n" + "=" * 50)
    print("Done! Check ADS to see the created schematic.")
    print("=" * 50)
    
    return True


def run_custom_command():
    """Interactive mode for testing individual commands."""
    client = ADSClient()
    
    print("ADS Command Tester")
    print("Available actions: ping, get_workspace_info, create_schematic, add_instance, save_design")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            action = input("Action> ").strip()
            
            if action == 'quit':
                break
            elif action == 'ping':
                print(client.ping())
            elif action == 'get_workspace_info':
                print(client.get_workspace_info())
            elif action == 'create_schematic':
                lib = input("  Library name: ").strip() or "work"
                cell = input("  Cell name: ").strip() or "test"
                print(client.create_schematic(lib, cell))
            elif action == 'save_design':
                print(client.save_design())
            else:
                print(f"Unknown action: {action}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Goodbye!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ADS Automation Examples")
    parser.add_argument("--mode", choices=["lna", "interactive"], default="lna",
                       help="Run mode: 'lna' builds a demo circuit, 'interactive' for manual commands")
    args = parser.parse_args()
    
    if args.mode == "lna":
        build_simple_lna()
    else:
        run_custom_command()
