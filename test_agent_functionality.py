"""
Test script to verify the THz agent functionality with your local model
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.agents.thz_agent import THzAgent
from app.agents.services.agent_service import agent_service
from app.tools.mock_laser_control import MockLaserControl
from app.tools.web_search_tool import WebSearchTool

def test_laser_control():
    """Test the laser control functionality"""
    print("=== Testing Laser Control ===")

    laser_tool = MockLaserControl()

    # Test turning laser on
    result = laser_tool.call('{"command": "on"}')
    print(f"Laser ON: {result}")

    # Test setting power
    result = laser_tool.call('{"command": "set_power", "value": 500}')
    print(f"Laser Power Set: {result}")

    # Test turning laser off
    result = laser_tool.call('{"command": "off"}')
    print(f"Laser OFF: {result}")

    print("Laser control test completed.\n")


def test_web_search():
    """Test the web search functionality (if available)"""
    print("=== Testing Web Search ===")

    web_tool = WebSearchTool()

    # Test a simple search
    result = web_tool.call('{"query": "terahertz spectroscopy basics"}')
    print(f"Web Search Result Preview: {result[:200]}...")

    print("Web search test completed.\n")


def test_agent_interaction():
    """Test the full agent interaction"""
    print("=== Testing Agent Interaction ===")

    # Create the THz agent
    agent = THzAgent()

    # Test 1: Laser control request
    print("Test 1: Laser control request")
    response = agent.process_message("帮我打开激光器，然后把功率调到 500mW")
    print(f"Response: {response}\n")

    # Test 2: Information request (should trigger web search)
    print("Test 2: Information request")
    response = agent.process_message("Search for information about terahertz spectroscopy technology advances in 2024")
    print(f"Response: {response[:500]}...\n")  # Truncate for readability

    # Test 3: Simple query
    print("Test 3: Simple query")
    response = agent.process_message("你好，你能做什么？")
    print(f"Response: {response}\n")

    print("Agent interaction tests completed.\n")


def test_available_tools():
    """Test listing available tools"""
    print("=== Testing Available Tools ===")

    agent = THzAgent()
    tools = agent.get_available_tools()

    print(f"Available tools: {len(tools)}")
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool['name']} - {tool['description']}")
        print(f"   Parameters: {tool['parameters']}")
        print()

    print("Available tools test completed.\n")


if __name__ == "__main__":
    print("Starting THz Agent functionality tests...\n")

    try:
        # Test individual tools
        test_laser_control()

        # Test web search tool (might need internet connection)
        test_web_search()

        # Test available tools listing
        test_available_tools()

        # Test full agent interaction
        test_agent_interaction()

        print("🎉 All tests completed successfully!")
        print("Your local model (qwen3-8b-finetuned at http://127.0.0.1:1234) is working with the THz agent!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()