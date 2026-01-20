"""MCP Client Manager for managing connections to MCP servers."""
import asyncio
import subprocess
import json
from typing import Dict, List, Any, Optional
from app.config.settings import config


class MCPClientManager:
    """Manages connections to multiple MCP servers and handles tool discovery/calls."""

    def __init__(self):
        self.sessions: Dict[str, Any] = {}  # Store connection details
        self.tool_to_server_map: Dict[str, str] = {}
        self._connected = False
        self.processes: Dict[str, subprocess.Popen] = {}  # Track stdio processes

    async def connect_all(self):
        """Connect to all configured MCP servers and discover their tools."""
        if not config.mcp.enabled:
            print("MCP functionality is disabled")
            return

        if self._connected:
            print("Already connected to MCP servers")
            return

        for server_config in config.mcp.servers:
            try:
                print(f"Connecting to MCP server: {server_config.name}")

                if server_config.transport_type == "stdio":
                    # Start the MCP server as a subprocess
                    if server_config.command:
                        cmd_parts = server_config.command.split()
                        process = subprocess.Popen(
                            cmd_parts,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        self.processes[server_config.name] = process

                        # Store process reference for later use
                        self.sessions[server_config.name] = {
                            'type': 'stdio',
                            'process': process,
                            'server_config': server_config
                        }

                        print(f"Started stdio server for {server_config.name}")
                    else:
                        print(f"No command specified for stdio server {server_config.name}")
                        continue

                elif server_config.transport_type in ["sse", "http"]:
                    # Store HTTP/SSE connection info
                    self.sessions[server_config.name] = {
                        'type': server_config.transport_type,
                        'url': server_config.url,
                        'server_config': server_config
                    }

                    print(f"Configured {server_config.transport_type} connection for {server_config.name}")
                else:
                    print(f"Unsupported transport type: {server_config.transport_type}")
                    continue

                # Discover tools from this server (simulate for now)
                # In real implementation, we'd call the server to get its tools
                tools = await self._discover_tools_from_server(server_config.name)

                # Map each tool to its server
                for tool in tools:
                    self.tool_to_server_map[tool['name']] = server_config.name

                print(f"Connected to {server_config.name}, found {len(tools)} tools")

            except Exception as e:
                print(f"Failed to connect to {server_config.name}: {e}")
                import traceback
                traceback.print_exc()

        self._connected = True

    async def _discover_tools_from_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools from a specific server (simulated for now)."""
        # This would be implemented with actual MCP protocol calls
        # For now we'll return empty list or could simulate based on server
        return []

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected servers (cached version)."""
        tools_list = []
        for tool_name, server_name in self.tool_to_server_map.items():
            # In a real implementation, we'd have more detailed info
            tools_list.append({
                "name": tool_name,
                "server": server_name
            })
        return tools_list

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool by name, routing to the appropriate server."""
        if tool_name not in self.tool_to_server_map:
            raise ValueError(f"Tool '{tool_name}' not found among registered tools")

        server_name = self.tool_to_server_map[tool_name]
        server_info = self.sessions[server_name]

        try:
            if server_info['type'] == 'stdio':
                # Call tool via stdio process
                result = await self._call_stdio_tool(server_name, tool_name, arguments)
            elif server_info['type'] in ['http', 'sse']:
                # Call tool via HTTP/SSE
                result = await self._call_http_tool(server_name, tool_name, arguments)
            else:
                raise ValueError(f"Unsupported transport type: {server_info['type']}")

            return result
        except Exception as e:
            print(f"Error calling tool '{tool_name}' on server '{server_name}': {e}")
            raise

    async def _call_stdio_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool via stdio transport."""
        # This is a simplified simulation
        # Real implementation would use MCP protocol over stdio
        process = self.processes[server_name]

        # In a real implementation, we would send an MCP message via stdin
        # and read the response from stdout
        # For now we'll simulate
        return {"result": f"Simulated call to {tool_name} with {arguments}"}

    async def _call_http_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool via HTTP/SSE transport."""
        # This would use HTTP requests to communicate with the server
        # For now we'll simulate
        server_info = self.sessions[server_name]
        return {"result": f"HTTP call to {tool_name} on {server_info['url']} with {arguments}"}

    def get_tool_mappings(self) -> Dict[str, str]:
        """Get the mapping of tool names to server names."""
        return self.tool_to_server_map.copy()

    def cleanup(self):
        """Clean up connections and processes."""
        for name, process in self.processes.items():
            if process.poll() is None:  # Process is still running
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


# Global MCP client manager instance
_mcp_client_manager = None


def get_mcp_client_manager():
    """Get the MCP client manager instance."""
    global _mcp_client_manager
    if _mcp_client_manager is None:
        _mcp_client_manager = MCPClientManager()
    return _mcp_client_manager