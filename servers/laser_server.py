"""Temporary MCP server for laser control - for local testing."""
import asyncio
import json
import sys
from typing import Dict, Any, Callable, List


class MockLaserControl:
    """Original laser control implementation to reuse."""

    @staticmethod
    def execute_command(params: str) -> str:
        """Execute the laser control command"""
        try:
            args = json.loads(params)
        except json.JSONDecodeError:
            return "参数格式错误，请使用 JSON"

        cmd = args.get('command')
        if cmd == 'on':
            return "【硬件反馈】激光器已开启，预热中..."
        elif cmd == 'off':
            return "【硬件反馈】激光器已关闭"
        elif cmd == 'set_power':
            val = args.get('value', 0)
            return f"【硬件反馈】功率已调节至 {val} mW"
        else:
            return "【硬件反馈】指令无效"


# MCP protocol constants
MCP_PROTOCOL_VERSION = "2024-11-05"
PROTOCOL_HEADER = f"MCP {MCP_PROTOCOL_VERSION}"


class MCPLaserServer:
    """Simple MCP server implementation for laser control."""

    def __init__(self):
        self.running = True

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method", "")

        if method == "tools/list":
            return self._handle_list_tools(request.get("id"))
        elif method == "tools/call":
            return await self._handle_call_tool(request)
        else:
            return {
                "error": {
                    "code": 400,
                    "message": f"Unknown method: {method}"
                },
                "id": request.get("id")
            }

    def _handle_list_tools(self, req_id: str) -> Dict[str, Any]:
        """Handle list tools request."""
        tools = [{
            "name": "mock_laser_control",
            "description": "控制飞秒激光器的开关和功率",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "指令内容，只能是 'on', 'off' 或 'set_power'",
                        "enum": ["on", "off", "set_power"]
                    },
                    "value": {
                        "type": "integer",
                        "description": "当指令为 'set_power' 时，设置的具体功率值(mW)",
                    }
                },
                "required": ["command"]
            }
        }]

        return {
            "result": {"tools": tools},
            "id": req_id
        }

    async def _handle_call_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request."""
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "mock_laser_control":
            # Convert arguments to JSON string to match original interface
            args_json = json.dumps(arguments)
            result = MockLaserControl.execute_command(args_json)

            return {
                "result": {"content": result},
                "id": request.get("id")
            }
        else:
            return {
                "error": {
                    "code": 404,
                    "message": f"Tool '{tool_name}' not found"
                },
                "id": request.get("id")
            }

    async def run(self):
        """Run the MCP server."""
        print(f"{PROTOCOL_HEADER}", file=sys.stderr)
        print(f"Content-Type: application/json", file=sys.stderr)
        print(file=sys.stderr)  # Empty line signals end of headers

        sys.stderr.flush()

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while self.running:
            try:
                # Read length header
                line = await reader.readline()
                if not line:
                    break

                line = line.decode().strip()
                if line.startswith("Content-Length:"):
                    length = int(line.split(":")[1].strip())

                    # Read empty line
                    await reader.readline()

                    # Read JSON body
                    data = await reader.readexactly(length)
                    request = json.loads(data.decode())

                    # Process request
                    response = await self.handle_request(request)

                    # Send response
                    response_json = json.dumps(response, ensure_ascii=False)
                    response_bytes = response_json.encode()

                    print(f"Content-Length: {len(response_bytes)}", file=sys.stdout)
                    print(file=sys.stdout)  # Empty line
                    sys.stdout.buffer.write(response_bytes)
                    sys.stdout.flush()

            except Exception as e:
                print(f"Error in MCP server: {e}", file=sys.stderr)
                break


async def main():
    """Main entry point for the laser server."""
    server = MCPLaserServer()
    print("Starting MCP Laser Control Server...", file=sys.stderr)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())