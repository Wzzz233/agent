"""
ADS Automation Server - Standalone Version

This is an ALTERNATIVE approach that doesn't rely on boot.ael.
Instead, you manually run this script INSIDE ADS using:
  Tools > Command Line > load("boot_standalone.py")

Or from the ADS Python Console:
  exec(open("C:/Users/Wzzz2/OneDrive/Desktop/agent/ads_plugin/scripting/boot_standalone.py").read())
"""

import threading
import socket
import queue
import json
import sys
import os
import traceback
import circuit_templates
from typing import Optional, Any, Dict

# ==============================================================================
# Configuration
# ==============================================================================
SERVER_HOST = 'localhost'
SERVER_PORT = 5000
TIMER_INTERVAL_MS = 50
MAX_RECV_SIZE = 1024 * 1024

# Global command queue
command_queue = queue.Queue()
_server_running = False

# ==============================================================================
# ADS API Import
# ==============================================================================
try:
    import keysight.ads.de as de
    from keysight.ads.de import db_uu
    ADS_AVAILABLE = True
    print("[OK] keysight.ads.de imported successfully")
except ImportError as e:
    de = None
    db_uu = None
    ADS_AVAILABLE = False
    print(f"[WARNING] keysight.ads.de not available: {e}")

# ==============================================================================
# Qt Import (for QTimer)
# ==============================================================================
QTimer = None
QObject = None
QT_AVAILABLE = False

try:
    from PySide2.QtCore import QTimer as _QTimer, QObject as _QObject
    QTimer, QObject = _QTimer, _QObject
    QT_AVAILABLE = True
    print("[OK] PySide2.QtCore imported successfully")
except ImportError:
    try:
        from PyQt5.QtCore import QTimer as _QTimer, QObject as _QObject
        QTimer, QObject = _QTimer, _QObject
        QT_AVAILABLE = True
        print("[OK] PyQt5.QtCore imported successfully")
    except ImportError:
        print("[WARNING] Qt not available - will use polling fallback")


# ==============================================================================
# Command Handlers
# ==============================================================================
class CommandHandler:
    """Handles ADS API commands - all methods run in main thread."""
    
    @staticmethod
    def ping(params: Dict) -> Dict:
        return {"pong": True, "ads_available": ADS_AVAILABLE, "qt_available": QT_AVAILABLE}
    
    @staticmethod
    def get_workspace_info(params: Dict) -> Dict:
        """Get workspace and library information."""
        if not ADS_AVAILABLE:
            return {"error": "ADS API not available"}
        
        try:
            # Use active_workspace() instead of get_current_workspace()
            ws = de.active_workspace()
            
            # Get list of writable libraries
            writable_libs = de.get_open_writable_library_names()
            
            # Check if workspace is open
            ws_open = de.workspace_is_open()
            
            return {
                "workspace_open": ws_open,
                "workspace": str(ws) if ws else None,
                "writable_libraries": list(writable_libs) if writable_libs else []
            }
        except Exception as e:
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def list_libraries(params: Dict) -> Dict:
        """List all open writable libraries."""
        if not ADS_AVAILABLE:
            return {"error": "ADS API not available"}
        
        try:
            libs = de.get_open_writable_library_names()
            return {"libraries": list(libs) if libs else []}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def create_schematic(params: Dict) -> Dict:
        """Create a new schematic in a library."""
        lib_name = params.get("lib_name")
        cell_name = params.get("cell_name", "untitled")
        
        if not ADS_AVAILABLE:
            return {"created": False, "error": "ADS API not available"}
        
        try:
            # If no library specified, try to get first writable library
            if not lib_name:
                libs = de.get_open_writable_library_names()
                if libs:
                    lib_name = list(libs)[0]
                else:
                    return {"created": False, "error": "No writable library found. Please open a workspace with a writable library."}
            
            # Verify library is open
            lib = de.get_open_library(lib_name)
            if lib is None:
                return {"created": False, "error": f"Library '{lib_name}' is not open"}
            
            # Build design URI
            design_uri = f"{lib_name}:{cell_name}:schematic"
            
            # Use db_uu.create_schematic() to create the schematic
            # This should create the cell and schematic view, then open it
            design = db_uu.create_schematic(design_uri)
            
            return {"created": True, "uri": design_uri, "library": lib_name, "design": str(design)}
        except Exception as e:
            return {"created": False, "error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def open_design(params: Dict) -> Dict:
        """Open an existing design."""
        design_uri = params.get("design_uri")
        
        if not ADS_AVAILABLE:
            return {"opened": False, "error": "ADS API not available"}
        
        if not design_uri:
            return {"opened": False, "error": "design_uri is required (format: lib:cell:view)"}
        
        try:
            design = db_uu.open_design(design_uri)
            return {"opened": True, "uri": design_uri, "design": str(design)}
        except Exception as e:
            return {"opened": False, "error": str(e)}
    
    @staticmethod
    def add_instance(params: Dict) -> Dict:
        """Add a component instance to the currently open design."""
        if not ADS_AVAILABLE:
            return {"added": False, "error": "ADS API not available"}
        
        try:
            # Get design using db_uu.open_design()
            design_uri = params.get("design_uri")
            if not design_uri:
                return {"added": False, "error": "design_uri is required"}
            
            design = db_uu.open_design(design_uri)
            if design is None:
                return {"added": False, "error": "No design open"}
            
            lib = params.get("component_lib", "ads_rflib")
            cell = params.get("component_cell", "R")
            view = params.get("component_view", "symbol")
            x = float(params.get("x", 0.0))
            y = float(params.get("y", 0.0))
            angle = params.get("angle")
            name = params.get("name")
            instance_params = params.get("parameters", {})
            
            # Build component reference string (this format worked in testing)
            component_ref = f"{lib}:{cell}:{view}"
            position = (x, y)
            
            # Add instance - use kwargs only if values are provided
            kwargs = {}
            if name:
                kwargs['name'] = name
            if angle is not None:
                kwargs['angle'] = float(angle)
            
            instance = design.add_instance(component_ref, position, **kwargs)
            
            # Set additional parameters if provided
            if instance and instance_params:
                print(f"[add_instance] Setting parameters: {instance_params}")
                for key, val in instance_params.items():
                    try:
                        # Try standard dictionary-like access first
                        instance.parameters[key] = str(val)
                    except Exception:
                        try:
                            # Fallback to set_parameter if available
                            if hasattr(instance, 'set_parameter'):
                                instance.set_parameter(key, str(val))
                        except Exception as pe:
                            print(f"[add_instance] Failed to set param {key}={val}: {pe}")
            
            # Debug: print instance count
            print(f"[add_instance] Added {instance}, total instances: {len(design.instances)}")
            
            return {"added": True, "name": str(instance), "instance_count": len(design.instances)}
        except Exception as e:
            return {"added": False, "error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def add_wire(params: Dict) -> Dict:
        """Add a wire to the current design."""
        if not ADS_AVAILABLE:
            return {"added": False, "error": "ADS API not available"}
        
        try:
            design_uri = params.get("design_uri")
            if not design_uri:
                return {"added": False, "error": "design_uri is required"}
            
            design = db_uu.open_design(design_uri)
            if design is None:
                return {"added": False, "error": "No design open"}
            
            points = [tuple(p) for p in params.get("points", [])]
            if len(points) < 2:
                return {"added": False, "error": "Need at least 2 points"}
            
            if hasattr(design, 'add_wire'):
                design.add_wire(points)
            elif hasattr(design, 'create_wire'):
                design.create_wire(points)
            else:
                return {"added": False, "error": "Could not find method to add wire"}
            
            return {"added": True}
        except Exception as e:
            return {"added": False, "error": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def save_design(params: Dict) -> Dict:
        """Save the current design."""
        if not ADS_AVAILABLE:
            return {"saved": False, "error": "ADS API not available"}

        try:
            design_uri = params.get("design_uri")
            if not design_uri:
                return {"saved": False, "error": "design_uri is required"}

            design = db_uu.open_design(design_uri)
            if design is None:
                return {"saved": False, "error": "No design found"}

            if hasattr(design, 'save'):
                design.save()

            return {"saved": True, "uri": design_uri}
        except Exception as e:
            return {"saved": False, "error": str(e)}

    @staticmethod
    def list_cells(params: Dict) -> Dict:
        """List all cells in a library."""
        if not ADS_AVAILABLE:
            return {"status": "error", "error": "ADS API not available"}

        library_name = params.get("library_name")
        if not library_name:
            return {"status": "error", "error": "library_name is required"}

        try:
            lib = de.get_open_library(library_name)
            if lib is None:
                return {"status": "error", "error": f"Library '{library_name}' is not open"}

            cells = []
            if hasattr(lib, 'cells'):
                for cell in lib.cells:
                    cells.append({
                        "name": cell.name,
                        "type": str(cell.cell_type) if hasattr(cell, 'cell_type') else "unknown"
                    })

            return {
                "status": "success",
                "library": library_name,
                "cells": cells,
                "count": len(cells)
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

    @staticmethod
    def check_cell_exists(params: Dict) -> Dict:
        """Check if a cell exists in a library."""
        if not ADS_AVAILABLE:
            return {"status": "error", "error": "ADS API not available"}

        library_name = params.get("library_name")
        cell_name = params.get("cell_name")

        if not library_name or not cell_name:
            return {"status": "error", "error": "Both library_name and cell_name are required"}

        try:
            lib = de.get_open_library(library_name)
            if lib is None:
                return {"status": "error", "error": f"Library '{library_name}' is not open"}

            # Try to get the cell
            try:
                cell = lib.cell(cell_name)
                design_uri = f"{library_name}:{cell_name}:schematic"
                return {
                    "status": "success",
                    "exists": True,
                    "design_uri": design_uri,
                    "cell_name": cell_name
                }
            except Exception:
                # Cell doesn't exist
                return {
                    "status": "success",
                    "exists": False,
                    "design_uri": f"{library_name}:{cell_name}:schematic",
                    "cell_name": cell_name
                }
        except Exception as e:
            return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

    @staticmethod
    def get_current_design(params: Dict) -> Dict:
        """Get design status - Note: ADS API doesn't support getting the currently focused design."""
        if not ADS_AVAILABLE:
            return {"status": "error", "error": "ADS API not available"}

        # 注意: keysight.ads.de 模块没有 active_design() 或类似函数
        # 无法通过 API 获取用户在 GUI 中当前打开的设计
        # 需要用户提供 design_uri 或使用 execute_circuit_plan 创建的设计
        
        # 返回说明信息
        return {
            "status": "success",
            "design_open": False,
            "design_uri": None,
            "message": "ADS API 不支持获取当前打开的设计。请提供 design_uri (格式: library:cell:schematic)，或使用 plan_circuit + execute_circuit_plan 创建新设计。",
            "example_uri": "MyLibrary3_lib:your_cell:schematic"
        }


    @staticmethod
    def build_template(params: Dict) -> Dict:
        """Execute a predefined circuit template."""
        template_type = params.get("template_type")
        design_uri = params.get("design_uri")
        args = params.get("args", {})
        
        if not design_uri:
            return {"status": "error", "message": "design_uri is required"}
            
        try:
            if template_type == "tline_test":
                w = float(args.get("w", 1.0))
                l = float(args.get("l", 10.0))
                er = float(args.get("er", 4.4))
                h = float(args.get("h", 1.6))
                
                result = circuit_templates.create_tline_test_circuit(
                    design_uri, w, l, er, h
                )
                return result
            else:
                return {"status": "error", "message": f"Unknown template type: {template_type}"}
        except Exception as e:
            return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

# Action dispatch table
ACTIONS = {
    "ping": CommandHandler.ping,
    "get_workspace_info": CommandHandler.get_workspace_info,
    "list_libraries": CommandHandler.list_libraries,
    "list_cells": CommandHandler.list_cells,
    "check_cell_exists": CommandHandler.check_cell_exists,
    "get_current_design": CommandHandler.get_current_design,
    "create_schematic": CommandHandler.create_schematic,
    "open_design": CommandHandler.open_design,
    "add_instance": CommandHandler.add_instance,
    "add_wire": CommandHandler.add_wire,
    "save_design": CommandHandler.save_design,
    "build_template": CommandHandler.build_template,
}


# ==============================================================================
# Socket Listener (Background Thread)
# ==============================================================================
def socket_listener(host: str, port: int):
    """Background thread for accepting socket connections."""
    global _server_running
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((host, port))
        server.listen(5)
        print(f"[SocketListener] Listening on {host}:{port}")
        
        while _server_running:
            try:
                server.settimeout(1.0)  # Allow checking _server_running
                try:
                    client, addr = server.accept()
                except socket.timeout:
                    continue
                
                print(f"[SocketListener] Connection from {addr}")
                
                # Read data
                data = b''
                client.settimeout(5.0)
                while True:
                    try:
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                        # Try to parse JSON
                        try:
                            json.loads(data.decode('utf-8'))
                            break
                        except:
                            continue
                    except socket.timeout:
                        break
                
                if data:
                    command_queue.put((client, data.decode('utf-8')))
                else:
                    client.close()
                    
            except Exception as e:
                print(f"[SocketListener] Error: {e}")
                
    except Exception as e:
        print(f"[SocketListener] Fatal: {e}")
    finally:
        server.close()
        print("[SocketListener] Stopped")


# ==============================================================================
# Queue Processor
# ==============================================================================
def process_command_queue():
    """Process queued commands. Call this from main thread."""
    while not command_queue.empty():
        try:
            client_socket, message = command_queue.get_nowait()
            
            response = {"status": "error", "message": "Unknown error"}
            
            try:
                cmd = json.loads(message)
                action = cmd.get("action", "")
                params = cmd.get("params", {})
                
                print(f"[Processor] Executing: {action}")
                
                if action in ACTIONS:
                    result = ACTIONS[action](params)
                    response = {"status": "success", "data": result}
                else:
                    response = {"status": "error", "message": f"Unknown action: {action}"}
                    
            except json.JSONDecodeError as e:
                response = {"status": "error", "message": f"Invalid JSON: {e}"}
            except Exception as e:
                response = {"status": "error", "message": str(e), "traceback": traceback.format_exc()}
            
            # Send response
            try:
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            except:
                pass
            finally:
                try:
                    client_socket.close()
                except:
                    pass
                    
        except queue.Empty:
            break
        except Exception as e:
            print(f"[Processor] Error: {e}")


# ==============================================================================
# Main Entry Points
# ==============================================================================
_timer = None
_socket_thread = None

def start_server(host: str = SERVER_HOST, port: int = SERVER_PORT):
    """Start the automation server."""
    global _server_running, _timer, _socket_thread
    
    print("=" * 60)
    print("ADS Automation Server - Starting")
    print("=" * 60)
    print(f"  ADS API: {ADS_AVAILABLE}")
    print(f"  Qt: {QT_AVAILABLE}")
    print(f"  Address: {host}:{port}")
    print("=" * 60)
    
    _server_running = True
    
    # Start socket thread
    _socket_thread = threading.Thread(target=socket_listener, args=(host, port), daemon=True)
    _socket_thread.start()
    
    # Setup QTimer if available
    if QT_AVAILABLE and QTimer is not None:
        _timer = QTimer()
        _timer.timeout.connect(process_command_queue)
        _timer.start(TIMER_INTERVAL_MS)
        print(f"[Server] QTimer started ({TIMER_INTERVAL_MS}ms)")
    else:
        print("[Server] No QTimer - use manual polling with process_command_queue()")
    
    print("[Server] Ready!")


def stop_server():
    """Stop the automation server."""
    global _server_running, _timer
    
    _server_running = False
    
    if _timer:
        _timer.stop()
        _timer = None
    
    print("[Server] Stopped")


def poll():
    """Manual polling - call this if QTimer is not available."""
    process_command_queue()


# ==============================================================================
# Auto-start when script is executed
# ==============================================================================
if __name__ == "__main__" or 'keysight' in sys.modules:
    # If running inside ADS or directly
    start_server()
    
    if not QT_AVAILABLE:
        print("\n[IMPORTANT] QTimer not available!")
        print("You must call poll() periodically to process commands.")
        print("Example: Create a timer callback that calls poll()")
