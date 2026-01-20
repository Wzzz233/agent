import unittest
from app.tools.mock_laser_control import MockLaserControl


class TestMockLaserControl(unittest.TestCase):
    """Test cases for the MockLaserControl tool"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.laser_tool = MockLaserControl()

    def test_on_command(self):
        """Test the 'on' command"""
        result = self.laser_tool.call('{"command": "on"}')
        self.assertEqual(result, "【硬件反馈】激光器已开启，预热中...")

    def test_set_power_command(self):
        """Test the 'set_power' command"""
        result = self.laser_tool.call('{"command": "set_power", "value": 500}')
        self.assertEqual(result, "【硬件反馈】功率已调节至 500 mW")

    def test_off_command(self):
        """Test the 'off' command"""
        result = self.laser_tool.call('{"command": "off"}')
        self.assertEqual(result, "【硬件反馈】激光器已关闭")

    def test_invalid_command(self):
        """Test an invalid command"""
        result = self.laser_tool.call('{"command": "invalid"}')
        self.assertEqual(result, "【硬件反馈】指令无效")

    def test_missing_command_param(self):
        """Test when command parameter is missing"""
        result = self.laser_tool.call('{}')
        self.assertEqual(result, "【硬件反馈】指令无效")

    def test_invalid_json(self):
        """Test with invalid JSON input"""
        result = self.laser_tool.call('invalid json')
        self.assertEqual(result, "参数格式错误，请使用 JSON")


if __name__ == '__main__':
    unittest.main()