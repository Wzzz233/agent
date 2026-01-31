"""
Mock Laser Control Tool - Pure Python implementation

Simulates control of a femtosecond laser with on/off/power commands.
"""
import json
from typing import Dict, Any, Union
from app.tools.base_tool import BaseTool


class MockLaserControl(BaseTool):
    """Tool for controlling the femtosecond laser (mock implementation)."""

    name = "mock_laser_control"
    description = "控制飞秒激光器的开关和功率。支持 'on', 'off', 'set_power' 三种指令。"
    
    # OpenAI JSON Schema format
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "指令内容，只能是 'on', 'off' 或 'set_power'",
                "enum": ["on", "off", "set_power"]
            },
            "value": {
                "type": "integer",
                "description": "当指令为 'set_power' 时，设置的具体功率值(mW)"
            }
        },
        "required": ["command"]
    }

    def call(self, params: Union[str, Dict[str, Any]], **kwargs) -> str:
        """Execute the laser control command."""
        try:
            args = self.parse_params(params)
        except ValueError as e:
            return f"参数格式错误: {str(e)}"

        cmd = args.get('command')
        
        if cmd == 'on':
            return "【硬件反馈】激光器已开启，预热中..."
        elif cmd == 'off':
            return "【硬件反馈】激光器已关闭"
        elif cmd == 'set_power':
            val = args.get('value', 0)
            return f"【硬件反馈】功率已调节至 {val} mW"
        else:
            return f"【硬件反馈】指令无效: {cmd}"