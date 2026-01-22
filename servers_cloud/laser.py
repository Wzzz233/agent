"""MCP Server for laser control - Standard implementation using FastMCP (MCP 1.25+)."""
import asyncio
import sys
import logging
import platform
from typing import Dict, Any

# MCP imports - 使用新版 FastMCP
from mcp.server import FastMCP

# Set up logging to stderr to avoid interfering with MCP protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Create MCP server instance using FastMCP
mcp = FastMCP("laser-control-server")


class LaserController:
    """Laser controller implementing the actual business logic."""

    def __init__(self):
        self._is_on = False
        self._power_level = 0

    def execute_command(self, command: str, value: int = None) -> str:
        """Execute the laser control command."""
        if command == 'on':
            self._is_on = True
            return "【硬件反馈】激光器已开启，预热中..."
        elif command == 'off':
            self._is_on = False
            return "【硬件反馈】激光器已关闭"
        elif command == 'set_power':
            if value is not None:
                self._power_level = value
                return f"【硬件反馈】功率已调节至 {value} mW"
            return "【硬件反馈】set_power 指令需要 value 参数"
        elif command == 'status':
            status = "开启" if self._is_on else "关闭"
            return f"【硬件反馈】激光器状态: {status}, 功率: {self._power_level} mW"
        else:
            return "【硬件反馈】指令无效"


laser_controller = LaserController()


@mcp.tool()
async def mock_laser_control(command: str, value: int = None) -> str:
    """
    控制飞秒激光器的开关和功率

    Args:
        command: 指令内容，可选值: 'on', 'off', 'set_power', 'status'
        value: 当指令为 'set_power' 时，设置的具体功率值(mW)
    """
    logger.info(f"Executing laser command: {command}, value: {value}")

    try:
        result = laser_controller.execute_command(command, value)
        logger.info(f"Laser command result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error executing laser command: {str(e)}"
        logger.error(error_msg)
        return error_msg


if __name__ == "__main__":
    logger.info("Starting MCP Laser Control Server...")
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    mcp.run()