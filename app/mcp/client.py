"""MCP Client Manager for managing connections to MCP servers."""
import asyncio
import os
import sys
from contextlib import AsyncExitStack
from typing import Dict, List, Any, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: 'mcp' library not found. MCP functionality will be disabled.")

from app.config.settings import config


class MCPClientManager:
    """Manages connections to multiple MCP servers and handles tool discovery/calls."""

    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}
        self.tools: List[Dict[str, Any]] = []
        self._connected = False
        self._main_loop = None

    async def connect_all(self):
        """Connect to all configured MCP servers and discover their tools."""
        # Capture the main loop where connections are established
        self._main_loop = asyncio.get_running_loop()

        if not MCP_AVAILABLE or not config.mcp.enabled:
            return

        if self._connected:
            return

        for server_config in config.mcp.servers:
            try:
                print(f"[MCP] Connecting to server: {server_config.name}")

                if server_config.transport_type == "stdio":
                    # Sets PYTHONPATH to current directory to ensure imports in server scripts work
                    env = os.environ.copy()
                    cwd = os.getcwd()
                    if "PYTHONPATH" in env:
                        env["PYTHONPATH"] = cwd + os.pathsep + env["PYTHONPATH"]
                    else:
                        env["PYTHONPATH"] = cwd
                    
                    server_params = StdioServerParameters(
                        command=server_config.command,
                        args=server_config.args,
                        env=env
                    )

                    # Enter context
                    read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
                    session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                    
                    await session.initialize()
                    self.sessions[server_config.name] = session

                    # List tools
                    result = await session.list_tools()
                    
                    for tool in result.tools:
                        # Store minimal info for routing
                        self.tools.append({
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema,
                            "server": server_config.name
                        })
                    
                    tool_names = [t.name for t in result.tools]
                    print(f"[MCP] Connected to {server_config.name}. Tools: {tool_names}")

                # TODO: Implement SSE/HTTP support if needed
                
            except Exception as e:
                print(f"[MCP] Failed to connect to {server_config.name}: {e}")
                import traceback
                traceback.print_exc()

        self._connected = True

    def call_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool synchronously from a different thread, ensuring execution 
        happens on the main event loop where the MCP session lives.
        """
        if not self._main_loop:
            raise RuntimeError("MCP Client not connected or loop not captured")
            
        future = asyncio.run_coroutine_threadsafe(
            self.call_tool(tool_name, arguments), 
            self._main_loop
        )
        return future.result()

    def get_all_tools_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions in MCP JSON format (name, description, inputSchema)."""
        return [{
            "name": t["name"],
            "description": t["description"],
            "inputSchema": t["input_schema"],
            "server": t["server"] # Helper for debugging, ignored by adapter usually
        } for t in self.tools]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool by name."""
        target_tool = next((t for t in self.tools if t["name"] == tool_name), None)
        if not target_tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        server_name = target_tool["server"]
        session = self.sessions.get(server_name)
        if not session:
            raise RuntimeError(f"Session for server '{server_name}' is not active")

        try:
            result = await session.call_tool(tool_name, arguments)
            
            # Result is a CallToolResult object
            # It has 'content' which is a list of TextContent or ImageContent
            # We strictly return text or json here for the agent
            
            output = []
            if hasattr(result, 'content'):
                for content in result.content:
                    if hasattr(content, 'text'):
                        output.append(content.text)
                    else:
                        output.append(str(content))
            
            return "\n".join(output)

        except Exception as e:
            print(f"[MCP] Error calling {tool_name}: {e}")
            raise

    async def cleanup(self):
        """Close connections."""
        print("[MCP] Cleaning up connections...")
        await self.exit_stack.aclose()


# Global MCP client manager instance
_mcp_client_manager = None

def get_mcp_client_manager():
    """Get the MCP client manager instance."""
    global _mcp_client_manager
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
    return _mcp_client_manager