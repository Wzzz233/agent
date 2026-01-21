"""MCP Server for laser control - Standard implementation."""
import asyncio
import json
import sys
import logging
from typing import Dict, Any
from mcp.server import Server
from mcp.types import Tool, StaticResource, ToolResult
import argparse


# Set up logging to stderr to avoid interfering with MCP protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("laser-control-server")


class LaserController:
    """Laser controller implementing the actual business logic."""

    def __init__(self):
        self._is_on = False
        self._power_level = 0

    def execute_command(self, params: Dict[str, Any]) -> str:
        """Execute the laser control command."""
        command = params.get('command', '')

        if command == 'on':
            self._is_on = True
            return "【硬件反馈】激光器已开启，预热中..."
        elif command == 'off':
            self._is_on = False
            return "【硬件反馈】激光器已关闭"
        elif command == 'set_power':
            value = params.get('value', 0)
            self._power_level = value
            return f"【硬件反馈】功率已调节至 {value} mW"
        else:
            return "【硬件反馈】指令无效"


laser_controller = LaserController()


@server.tool(
    "mock_laser_control",
    "控制飞秒激光器的开关和功率",
    # Define input schema with proper types and descriptions
)
async def mock_laser_control(command: str, value: int = None) -> str:
    """
    控制飞秒激光器的开关和功率

    Args:
        command: 指令内容，只能是 'on', 'off' 或 'set_power'
        value: 当指令为 'set_power' 时，设置的具体功率值(mW)
    """
    params = {"command": command}
    if value is not None:
        params["value"] = value

    logger.info(f"Executing laser command: {params}")

    try:
        result = laser_controller.execute_command(params)
        logger.info(f"Laser command result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error executing laser command: {str(e)}"
        logger.error(error_msg)
        return error_msg


async def main():
    """Main entry point for the laser server."""
    logger.info("Starting MCP Laser Control Server...")

    # Run the server
    async with server.run():
        logger.info("Laser server running, waiting for connections...")
        # Keep the server running indefinitely
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    # Use asyncio.run to run the main function
    asyncio.run(main())