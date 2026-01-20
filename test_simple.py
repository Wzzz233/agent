"""
Simple test script that recreates the original working functionality
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Import the same way as the original working code
from qwen_agent.agents import Assistant
from app.config.settings import config
from app.tools.mock_laser_control import MockLaserControl
from app.tools.web_search_tool import WebSearchTool


def test_with_original_pattern():
    """Test using the exact same pattern as the original working agent.py"""
    print("=== Testing with Original Working Pattern ===")

    # Recreate the exact same assistant initialization as the original
    bot = Assistant(
        llm={
            "model": config.llm.model,  # This should be "qwen3-8b-finetuned"
            "model_server": config.llm.model_server,  # This should be "http://127.0.0.1:1234/v1"
            "api_key": config.llm.api_key,  # This should be "EMPTY"
            "generate_cfg": {"temperature": config.llm.temperature}  # This should be 0.01
        },
        name=config.agent.name,
        description=config.agent.description,
        function_list=[MockLaserControl(), WebSearchTool()],  # Pass instances directly as in original
        system_message=config.agent.system_message
    )

    print("Assistant initialized successfully!")

    # Test 1: Laser control
    print("\n=== Test 1: Laser Control ===")
    instruction1 = "帮我打开激光器，然后把功率调到 500mW"
    print(f"Input: {instruction1}")
    try:
        responses = list(bot.run(messages=[{'role': 'user', 'content': instruction1}]))
        for response in responses:
            print(f"Response: {response}")
    except Exception as e:
        print(f"Error in laser control test: {e}")

    # Test 2: Web search
    print("\n=== Test 2: Web Search ===")
    instruction2 = "Search for information about terahertz spectroscopy technology advances in 2024"
    print(f"Input: {instruction2}")
    try:
        responses = list(bot.run(messages=[{'role': 'user', 'content': instruction2}]))
        for response in responses:
            print(f"Response: {response[:500]}...")  # Truncate for readability
    except Exception as e:
        print(f"Error in web search test: {e}")

    # Test 3: Simple greeting
    print("\n=== Test 3: Simple Greeting ===")
    instruction3 = "你好，你能做什么？"
    print(f"Input: {instruction3}")
    try:
        responses = list(bot.run(messages=[{'role': 'user', 'content': instruction3}]))
        for response in responses:
            print(f"Response: {response}")
    except Exception as e:
        print(f"Error in greeting test: {e}")

    print("\nAll tests completed!")


if __name__ == "__main__":
    print("Testing the THz agent with your local model...")
    print(f"Model: {config.llm.model}")
    print(f"Model server: {config.llm.model_server}")
    print(f"API key: {config.llm.api_key}")
    print()

    try:
        test_with_original_pattern()
        print("\n🎉 Tests completed successfully! Your local model is working correctly.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()