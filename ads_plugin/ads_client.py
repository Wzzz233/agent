"""
ADS Automation Client

This module provides a Python client to communicate with the ADS Automation Server
running inside Keysight ADS.

Usage:
    from ads_client import ADSClient
    
    client = ADSClient()
    client.connect()
    
    # Create a schematic
    result = client.create_schematic("mylib", "my_lna")
    
    # Add components
    client.add_instance("ads_rflib", "R", x=1.0, y=2.0, name="R1", parameters={"R": "50 Ohm"})
    client.add_instance("ads_rflib", "C", x=3.0, y=2.0, name="C1")
    
    # Add wires
    client.add_wire([(1.0, 2.5), (3.0, 2.5)])
    
    # Save
    client.save_design()
    
    client.close()
"""

import socket
import json
from typing import Optional, Dict, Any, List, Tuple


class ADSClient:
    """
    Client for communicating with the ADS Automation Server.
    
    The server must be running inside ADS (started via boot.ael/boot.py).
    """
    
    def __init__(self, host: str = 'localhost', port: int = 5000, timeout: float = 30.0):
        """
        Initialize the ADS client.
        
        Args:
            host: Server hostname (default: localhost)
            port: Server port (default: 5000)
            timeout: Socket timeout in seconds (default: 30)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
    
    def _send_command(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a command to the ADS server and return the response.
        
        Args:
            action: The action to perform (e.g., "create_schematic")
            params: Parameters for the action
            
        Returns:
            Server response as a dictionary
            
        Raises:
            ConnectionError: If unable to connect to the server
            TimeoutError: If the server doesn't respond in time
        """
        if params is None:
            params = {}
        
        command = {
            "action": action,
            "params": params
        }
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        try:
            sock.connect((self.host, self.port))
            
            # Send command
            message = json.dumps(command).encode('utf-8')
            sock.sendall(message)
            
            # Signal end of sending (for server to know we're done)
            sock.shutdown(socket.SHUT_WR)
            
            # Receive response
            response_data = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
            
            if not response_data:
                return {"status": "error", "message": "Empty response from server"}
            
            return json.loads(response_data.decode('utf-8'))
            
        except socket.timeout:
            raise TimeoutError(f"Server did not respond within {self.timeout} seconds")
        except ConnectionRefusedError:
            raise ConnectionError(f"Could not connect to ADS server at {self.host}:{self.port}")
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON response: {e}", "raw": response_data.decode('utf-8', errors='replace')}
        finally:
            sock.close()
    
    # =========================================================================
    # High-Level API
    # =========================================================================
    
    def ping(self) -> Dict[str, Any]:
        """
        Check if the server is alive.
        
        Returns:
            Server status information
        """
        return self._send_command("ping")
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """
        Get information about the current ADS workspace.
        
        Returns:
            Workspace information including path and libraries
        """
        return self._send_command("get_workspace_info")
    
    def create_schematic(self, lib_name: str = "work", cell_name: str = "untitled") -> Dict[str, Any]:
        """
        Create a new schematic cell.
        
        Args:
            lib_name: Library name (default: "work")
            cell_name: Cell name
            
        Returns:
            Result with URI of created schematic
        """
        return self._send_command("create_schematic", {
            "lib_name": lib_name,
            "cell_name": cell_name
        })
    
    def add_instance(
        self,
        component_lib: str,
        component_cell: str,
        x: float = 0.0,
        y: float = 0.0,
        angle: int = 0,
        name: Optional[str] = None,
        component_view: str = "symbol",
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a component instance to the current schematic.
        
        Args:
            component_lib: Component library (e.g., "ads_rflib")
            component_cell: Component cell name (e.g., "R", "C", "L")
            x: X coordinate
            y: Y coordinate
            angle: Rotation angle in degrees (0, 90, 180, 270)
            name: Instance name (optional)
            component_view: View name (default: "symbol")
            parameters: Component parameters (e.g., {"R": "50 Ohm"})
            
        Returns:
            Result with instance information
        """
        return self._send_command("add_instance", {
            "component_lib": component_lib,
            "component_cell": component_cell,
            "component_view": component_view,
            "x": x,
            "y": y,
            "angle": angle,
            "name": name,
            "parameters": parameters or {}
        })
    
    def add_wire(self, points: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Add a wire connecting multiple points.
        
        Args:
            points: List of (x, y) coordinate tuples
            
        Returns:
            Result indicating success
        """
        return self._send_command("add_wire", {
            "points": points
        })
    
    def save_design(self) -> Dict[str, Any]:
        """
        Save the current design.
        
        Returns:
            Result indicating success
        """
        return self._send_command("save_design")
    
    def run_simulation(self, output_dir: str = "./simulation_results") -> Dict[str, Any]:
        """
        Run a simulation on the current design.
        
        Args:
            output_dir: Directory for simulation output
            
        Returns:
            Result with netlist path and output directory
        """
        return self._send_command("run_simulation", {
            "output_dir": output_dir
        })


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_test(host: str = 'localhost', port: int = 5000) -> bool:
    """
    Quick test to check if ADS server is reachable.
    
    Returns:
        True if server responds, False otherwise
    """
    try:
        client = ADSClient(host, port, timeout=5.0)
        result = client.ping()
        print(f"Server Status: {result}")
        return result.get("status") == "success"
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    print("ADS Client Test")
    print("=" * 40)
    
    # Test connection
    if quick_test():
        print("\n✓ Server is running!")
        
        # Create a simple circuit
        client = ADSClient()
        
        print("\nCreating schematic...")
        result = client.create_schematic("work", "test_circuit")
        print(f"  Result: {result}")
        
        print("\nAdding resistor...")
        result = client.add_instance("ads_rflib", "R", x=1.0, y=2.0, name="R1", parameters={"R": "50 Ohm"})
        print(f"  Result: {result}")
        
        print("\nSaving design...")
        result = client.save_design()
        print(f"  Result: {result}")
    else:
        print("\n✗ Server is not running. Make sure ADS is open with the automation workspace.")
