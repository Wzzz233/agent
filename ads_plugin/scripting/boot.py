"""
boot.py - ADS Automation Server

This script implements a resident Socket server inside ADS that:
1. Listens for JSON commands on a configurable TCP port (default: 5000)
2. Uses QTimer to safely dispatch commands to the main GUI thread
3. Executes keysight.ads.de API calls and returns results

Architecture:
- Worker Thread: Runs socket.accept() in a loop, pushes commands to a Queue
- Main Thread: QTimer polls the Queue every 50ms and executes ADS API calls

Usage:
  This script is automatically loaded by boot.ael when ADS opens the workspace.
  External clients can connect via TCP and send JSON commands.
"""

import threading
import socket
import queue
import json
import sys
import os
import traceback
from typing import Optional, Any, Dict, Tuple

# ==============================================================================
# Configuration
# ==============================================================================
SERVER_HOST = 'localhost'
SERVER_PORT = 5000
TIMER_INTERVAL_MS = 50  # QTimer polling interval
MAX_RECV_SIZE = 1024 * 1024  # 1MB max message size

# ==============================================================================
# Global State
# ==============================================================================
command_queue: queue.Queue = queue.Queue()
_server_instance: Optional['ADSServer'] = None
_socket_thread: Optional[threading.Thread] = None

# ==============================================================================
# ADS API Import (with fallback for testing outside ADS)
# ==============================================================================
try:
    import keysight.ads.de as de
    from keysight.ads.de import db_uu
    ADS_AVAILABLE = True
except ImportError:
    # Mock for testing outside ADS environment
    de = None
    db_uu = None
    ADS_AVAILABLE = False
    print("[WARNING] keysight.ads.de not available. Running in mock mode.")

# ==============================================================================
# Qt Import (PySide2/PyQt5 compatibility)
# ==============================================================================
QTimer = None
QObject = None

def _import_qt():
    """Try to import Qt components from available backends."""
    global QTimer, QObject
    try:
        from PySide2.QtCore import QTimer as _QTimer, QObject as _QObject
        QTimer, QObject = _QTimer, _QObject
        return True
    except ImportError:
        pass
    try:
        from PyQt5.QtCore import QTimer as _QTimer, QObject as _QObject
        QTimer, QObject = _QTimer, _QObject
        return True
    except ImportError:
        pass
    # Try keysight's bundled Qt if available
    try:
        from keysight.ads.gui import QTimer as _QTimer, QObject as _QObject
        QTimer, QObject = _QTimer, _QObject
        return True
    except ImportError:
        pass
    return False

QT_AVAILABLE = _import_qt()
if not QT_AVAILABLE:
    print("[WARNING] Qt (PySide2/PyQt5) not available. QTimer disabled.")


# ==============================================================================
# ADS Command Handler
# ==============================================================================
class ADSCommandHandler:
    """
    Handles the execution of specific ADS commands.
    All methods run in the main (GUI) thread.
    """
    
    @staticmethod
    def create_schematic(params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new schematic cell in the workspace."""
        lib_name = params.get("lib_name", "work")
        cell_name = params.get("cell_name", "untitled")
        
        if not ADS_AVAILABLE:
            return {"created": False, "message": "ADS API not available (mock mode)"}
        
        design_uri = f"{lib_name}:{cell_name}:schematic"
        
        try:
            # Create the schematic
            db_uu.create_schematic(design_uri)
            # Open it in the editor
            design = db_uu.open_design(design_uri)
            return {"created": True, "uri": design_uri}
        except Exception as e:
            return {"created": False, "error": str(e)}
    
    @staticmethod
    def add_instance(params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a component instance to the current schematic."""
        lib = params.get("component_lib", "ads_rflib")
        cell = params.get("component_cell", "R")
        view = params.get("component_view", "symbol")
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        angle = params.get("angle", 0)
        name = params.get("name", None)
        parameters = params.get("parameters", {})
        
        if not ADS_AVAILABLE:
            return {"added": False, "message": "ADS API not available (mock mode)"}
        
        try:
            # Get current design context
            design = db_uu.get_current_design()
            if design is None:
                return {"added": False, "error": "No design is currently open"}
            
            # Add the instance
            component_id = (lib, cell, view)
            instance = design.add_instance(component_id, (x, y), angle=angle, name=name)
            
            # Set parameters if provided
            for param_name, param_value in parameters.items():
                if hasattr(instance, 'parameters'):
                    setattr(instance.parameters, param_name, param_value)
            
            return {"added": True, "instance_name": name or str(instance)}
        except Exception as e:
            return {"added": False, "error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def add_wire(params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a wire (net) to the current schematic."""
        points = params.get("points", [])  # List of [x, y] coordinate pairs
        
        if not ADS_AVAILABLE:
            return {"added": False, "message": "ADS API not available (mock mode)"}
        
        if len(points) < 2:
            return {"added": False, "error": "Wire requires at least 2 points"}
        
        try:
            design = db_uu.get_current_design()
            if design is None:
                return {"added": False, "error": "No design is currently open"}
            
            # Convert list to tuple format
            point_tuples = [tuple(p) for p in points]
            wire = design.add_wire(point_tuples)
            
            return {"added": True}
        except Exception as e:
            return {"added": False, "error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def save_design(params: Dict[str, Any]) -> Dict[str, Any]:
        """Save the current design."""
        if not ADS_AVAILABLE:
            return {"saved": False, "message": "ADS API not available (mock mode)"}
        
        try:
            design = db_uu.get_current_design()
            if design is None:
                return {"saved": False, "error": "No design is currently open"}
            
            design.save()
            return {"saved": True}
        except Exception as e:
            return {"saved": False, "error": str(e)}
    
    @staticmethod
    def run_simulation(params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a simulation on the current design."""
        if not ADS_AVAILABLE:
            return {"success": False, "message": "ADS API not available (mock mode)"}
        
        try:
            from keysight.edatoolbox import ads as edat_ads
            
            design = db_uu.get_current_design()
            if design is None:
                return {"success": False, "error": "No design is currently open"}
            
            # Save and generate netlist
            design.save()
            netlist_path = design.generate_netlist()
            
            # Run simulation
            simulator = edat_ads.CircuitSimulator()
            output_dir = params.get("output_dir", "./simulation_results")
            simulator.run_netlist(netlist_path, output_dir=output_dir)
            
            return {"success": True, "netlist": netlist_path, "output_dir": output_dir}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def get_workspace_info(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about the current workspace."""
        if not ADS_AVAILABLE:
            return {"available": False, "message": "ADS API not available (mock mode)"}
        
        try:
            workspace = de.get_current_workspace()
            if workspace is None:
                return {"available": False, "error": "No workspace is open"}
            
            libraries = [lib.name for lib in workspace.libraries] if hasattr(workspace, 'libraries') else []
            return {
                "available": True,
                "workspace_path": str(workspace.path) if hasattr(workspace, 'path') else "unknown",
                "libraries": libraries
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    @staticmethod
    def ping(params: Dict[str, Any]) -> Dict[str, Any]:
        """Simple ping to check server is alive."""
        return {"pong": True, "ads_available": ADS_AVAILABLE, "qt_available": QT_AVAILABLE}


# ==============================================================================
# ADS Server (Main Thread QTimer-based dispatcher)
# ==============================================================================
class ADSServer:
    """
    The main server object that runs in the ADS GUI thread.
    Uses QTimer to poll a command queue and dispatch to handlers.
    """
    
    def __init__(self):
        self.handler = ADSCommandHandler()
        self.timer = None
        
        # Action dispatch table
        self.actions = {
            "ping": self.handler.ping,
            "create_schematic": self.handler.create_schematic,
            "add_instance": self.handler.add_instance,
            "add_wire": self.handler.add_wire,
            "save_design": self.handler.save_design,
            "run_simulation": self.handler.run_simulation,
            "get_workspace_info": self.handler.get_workspace_info,
        }
        
        if QT_AVAILABLE:
            self._setup_timer()
        else:
            print("[WARNING] QTimer not available. Using fallback polling.")
    
    def _setup_timer(self):
        """Initialize QTimer for queue polling."""
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_queue)
        self.timer.start(TIMER_INTERVAL_MS)
        print(f"[ADSServer] QTimer started with {TIMER_INTERVAL_MS}ms interval")
    
    def _process_queue(self):
        """
        Called by QTimer in the main thread.
        Processes all pending commands in the queue.
        """
        try:
            while not command_queue.empty():
                client_socket, message = command_queue.get_nowait()
                self._execute_command(client_socket, message)
        except Exception as e:
            print(f"[ADSServer] Error in process_queue: {e}")
            traceback.print_exc()
    
    def _execute_command(self, client_socket: socket.socket, message: str):
        """
        Parse and execute a command, then send response.
        Runs in the main thread.
        """
        response = {"status": "error", "data": None, "message": "Unknown error"}
        
        try:
            cmd_data = json.loads(message)
            action = cmd_data.get("action", "")
            params = cmd_data.get("params", {})
            
            print(f"[ADSServer] Executing action: {action}")
            
            if action in self.actions:
                result = self.actions[action](params)
                response = {"status": "success", "data": result}
            else:
                response = {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "available_actions": list(self.actions.keys())
                }
        
        except json.JSONDecodeError as e:
            response = {"status": "error", "message": f"Invalid JSON: {e}"}
        except Exception as e:
            response = {
                "status": "error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }
        
        # Send response back to client
        self._send_response(client_socket, response)
    
    def _send_response(self, client_socket: socket.socket, response: dict):
        """Send JSON response and close connection."""
        try:
            response_bytes = json.dumps(response).encode('utf-8')
            client_socket.sendall(response_bytes)
        except Exception as e:
            print(f"[ADSServer] Failed to send response: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass


# ==============================================================================
# Socket Listener (Worker Thread)
# ==============================================================================
def _socket_listener(host: str, port: int):
    """
    Background thread that listens for incoming TCP connections.
    Received messages are placed in the command_queue for main thread processing.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"[SocketListener] Listening on {host}:{port}")
        
        while True:
            try:
                client_socket, addr = server_socket.accept()
                print(f"[SocketListener] Connection from {addr}")
                
                # Receive data (simple protocol: read until connection closes or max size)
                data = b''
                while True:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) >= MAX_RECV_SIZE:
                        break
                    # Check for end of JSON (simple heuristic)
                    try:
                        json.loads(data.decode('utf-8'))
                        break  # Valid JSON received
                    except:
                        continue  # Keep reading
                
                if data:
                    # Push to queue for main thread processing
                    # Note: We keep the socket open so main thread can respond
                    # Re-create socket for response since we can't pass the original safely
                    response_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    response_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    # For simplicity, we'll respond on the same connection
                    command_queue.put((client_socket, data.decode('utf-8')))
                else:
                    client_socket.close()
                    
            except Exception as e:
                print(f"[SocketListener] Error handling connection: {e}")
                traceback.print_exc()
                
    except Exception as e:
        print(f"[SocketListener] Fatal error: {e}")
        traceback.print_exc()
    finally:
        try:
            server_socket.close()
        except:
            pass


# ==============================================================================
# Public API
# ==============================================================================
def start_server(host: str = SERVER_HOST, port: int = SERVER_PORT):
    """
    Start the ADS automation server.
    Called from boot.ael on workspace load.
    
    Args:
        host: Host to bind to (default: localhost)
        port: Port to listen on (default: 5000)
    """
    global _server_instance, _socket_thread
    
    print("=" * 60)
    print("ADS Automation Server - Initializing")
    print("=" * 60)
    print(f"  ADS API Available: {ADS_AVAILABLE}")
    print(f"  Qt Available: {QT_AVAILABLE}")
    print(f"  Server Address: {host}:{port}")
    print("=" * 60)
    
    # Start socket listener in background thread
    _socket_thread = threading.Thread(
        target=_socket_listener,
        args=(host, port),
        daemon=True,
        name="ADSSocketListener"
    )
    _socket_thread.start()
    
    # Initialize main thread server (with QTimer)
    _server_instance = ADSServer()
    
    print("[ADSServer] Server started successfully!")
    print("[ADSServer] Ready to receive commands.")


def stop_server():
    """Stop the automation server (if possible)."""
    global _server_instance, _socket_thread
    
    if _server_instance and _server_instance.timer:
        _server_instance.timer.stop()
    
    _server_instance = None
    _socket_thread = None
    
    print("[ADSServer] Server stopped.")


# ==============================================================================
# Direct Execution (for testing outside ADS)
# ==============================================================================
if __name__ == "__main__":
    print("Running boot.py directly for testing...")
    print("This mode simulates the server without ADS/Qt.")
    
    # Simple blocking test mode
    start_server()
    
    # Keep main thread alive
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_server()
