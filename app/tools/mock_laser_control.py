import json
from qwen_agent.tools.base import BaseTool
from typing import Dict, Any


class MockLaserControl(BaseTool):
    """Tool for controlling the femtosecond laser"""

    name = "mock_laser_control"
    description = "控制飞秒激光器的开关和功率"
    parameters = [{
        "name": "command",
        "type": "string",
        "description": "指令内容，只能是 'on', 'off' 或 'set_power'",
        "required": True
    }, {
        "name": "value",
        "type": "integer",
        "description": "当指令为 'set_power' 时，设置的具体功率值(mW)",
        "required": False
    }]

    def call(self, params: str, **kwargs) -> str:
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