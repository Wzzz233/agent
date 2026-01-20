"""
Test script for the HTTP API - comprehensive tool testing
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"OK Health check: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"ERROR Health check failed: {e}")
        return False


def test_list_all_tools():
    """Test the tools listing endpoint"""
    try:
        url = f"{BASE_URL}/api/v1/tools/list"
        response = requests.get(url)
        print(f"OK Tools list response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            tools = result.get('tools', [])
            print(f"   Available tools: {len(tools)}")
            for i, tool in enumerate(tools, 1):
                print(f"   {i}. {tool.get('name', 'Unknown')} - {tool.get('description', 'No description')[:60]}...")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Tools list test failed: {e}")
        return False


def test_agent_chat_basic():
    """Test basic agent chat functionality"""
    try:
        url = f"{BASE_URL}/api/v1/agent/chat"
        payload = {
            "message": "你好，请介绍一下自己",
            "history": []
        }

        response = requests.post(url, json=payload)
        print(f"OK Basic chat response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            response_content = result.get('response', 'No response')
            print(f"   Agent introduction preview: {str(response_content)[:100]}...")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Basic chat test failed: {e}")
        return False


def test_laser_control_on():
    """Test laser control - turn on command"""
    try:
        url = f"{BASE_URL}/api/v1/agent/chat"
        payload = {
            "message": "帮我打开激光器",
            "history": []
        }

        response = requests.post(url, json=payload)
        print(f"OK Laser ON command: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            response_content = result.get('response', 'No response')
            print(f"   Laser ON response preview: {str(response_content)[:200]}...")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Laser ON test failed: {e}")
        return False


def test_laser_control_power():
    """Test laser control - set power command"""
    try:
        url = f"{BASE_URL}/api/v1/agent/chat"
        payload = {
            "message": "把激光器功率调到 500mW",
            "history": []
        }

        response = requests.post(url, json=payload)
        print(f"OK Laser power command: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            response_content = result.get('response', 'No response')
            print(f"   Laser power response preview: {str(response_content)[:200]}...")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Laser power test failed: {e}")
        return False


def test_laser_control_off():
    """Test laser control - turn off command"""
    try:
        url = f"{BASE_URL}/api/v1/agent/chat"
        payload = {
            "message": "关闭激光器",
            "history": []
        }

        response = requests.post(url, json=payload)
        print(f"OK Laser OFF command: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            response_content = result.get('response', 'No response')
            print(f"   Laser OFF response preview: {str(response_content)[:200]}...")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Laser OFF test failed: {e}")
        return False


def test_web_search():
    """Test web search functionality"""
    try:
        url = f"{BASE_URL}/api/v1/agent/chat"
        payload = {
            "message": "Search for information about terahertz spectroscopy technology advances in 2024",
            "history": []
        }

        response = requests.post(url, json=payload)
        print(f"OK Web search command: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            response_content = result.get('response', 'No response')
            print(f"   Web search response preview: {str(response_content)[:200]}...")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Web search test failed: {e}")
        return False


def test_complex_command():
    """Test a complex command that uses multiple tools"""
    try:
        url = f"{BASE_URL}/api/v1/agent/chat"
        payload = {
            "message": "帮我打开激光器，然后把功率调到 300mW，然后再搜索一下太赫兹光谱技术的最新进展",
            "history": []
        }

        response = requests.post(url, json=payload)
        print(f"OK Complex command (multi-tool): {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            response_content = result.get('response', 'No response')
            print(f"   Complex command response preview: {str(response_content)[:200]}...")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Complex command test failed: {e}")
        return False


def test_session_creation():
    """Test session creation endpoint"""
    try:
        url = f"{BASE_URL}/api/v1/sessions/create"
        response = requests.post(url)
        print(f"OK Session creation: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Session created: {result.get('success', False)}")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR Session creation test failed: {e}")
        return False


def test_mcp_list_tools():
    """Test MCP tools listing endpoint"""
    try:
        url = f"{BASE_URL}/mcp/v1/tools"
        response = requests.get(url)
        print(f"OK MCP tools list: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   MCP tools response structure: {type(result)}")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR MCP tools list test failed: {e}")
        return False


def run_all_tests():
    """Run all API tests"""
    print("Starting comprehensive API tests...")
    print(f"Testing against: {BASE_URL}")
    print()

    tests = [
        ("Health Check", test_health),
        ("List All Tools", test_list_all_tools),
        ("Basic Chat", test_agent_chat_basic),
        ("Laser Control ON", test_laser_control_on),
        ("Laser Power Setting", test_laser_control_power),
        ("Laser Control OFF", test_laser_control_off),
        ("Web Search", test_web_search),
        ("Complex Multi-Tool Command", test_complex_command),
        ("Session Creation", test_session_creation),
        ("MCP Tools Endpoint", test_mcp_list_tools),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        success = test_func()
        results.append((test_name, success))
        print()  # Empty line for readability
        time.sleep(1)  # Brief pause between tests

    # Print summary
    print("Test Results Summary:")
    print("-" * 40)
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1

    print("-" * 40)
    print(f"Total: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("All tests passed! Your API is working perfectly!")
    else:
        print(f"{len(results) - passed} test(s) failed. Please check the server.")

    return passed == len(results)


if __name__ == "__main__":
    print("Testing THz Agent API with comprehensive tool testing...")
    print()

    run_all_tests()

    print("\nNotes:")
    print("   - Make sure your server is running on http://localhost:8000")
    print("   - Make sure your local model is accessible at http://127.0.0.1:1234/v1")
    print("   - The model should be named 'qwen3-8b-finetuned'")