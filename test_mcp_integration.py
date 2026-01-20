"""Integration test for MCP client transformation."""
import asyncio
import os
import json
from app.config.settings import config
from app.mcp.client import get_mcp_client_manager
from app.agents.services.agent_service import get_agent_service


async def test_mcp_integration():
    """Test the MCP client transformation."""
    print("Testing MCP Client Integration...")

    # Set up MCP server configuration for testing
    os.environ['MCP_ENABLED'] = 'true'
    os.environ['MCP_SERVERS'] = json.dumps([
        {
            "name": "laser_server",
            "transport_type": "stdio",
            "command": "python servers/laser_server.py"
        },
        {
            "name": "search_server",
            "transport_type": "stdio",
            "command": "python servers/search_server.py"
        }
    ])

    # Reload configuration to pick up new environment variables
    new_config = config.__class__.from_env()

    print(f"MCP Enabled: {new_config.mcp.enabled}")
    print(f"MCP Servers: {len(new_config.mcp.servers)}")

    # Test MCP client manager
    print("\n--- Testing MCP Client Manager ---")
    mcp_manager = get_mcp_client_manager()

    try:
        await mcp_manager.connect_all()
        print("Successfully connected to MCP servers")

        tools = mcp_manager.get_all_tools()
        print(f"Discovered tools: {len(tools)}")

        # Show tool mappings
        mappings = mcp_manager.get_tool_mappings()
        print(f"Tool mappings: {mappings}")

    except Exception as e:
        print(f"Error connecting to MCP servers: {e}")
        import traceback
        traceback.print_exc()

    # Test Agent Service
    print("\n--- Testing Agent Service ---")
    agent_service = get_agent_service()

    try:
        # Initialize MCP tools for the agent
        await agent_service.initialize_mcp_tools()
        print("Successfully initialized MCP tools in agent service")

        tools = agent_service.get_available_tools()
        print(f"Available tools in agent: {len(tools)}")

        for tool in tools:
            print(f"- Tool: {tool.get('name', 'unknown')}")

    except Exception as e:
        print(f"Error initializing agent service: {e}")
        import traceback
        traceback.print_exc()

    # Test a simple message processing (without actual tool calls)
    print("\n--- Testing Message Processing ---")
    try:
        response = await agent_service.process_message_async("Hello, how are you?")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- Integration Test Complete ---")


def test_with_local_servers():
    """Test using the locally defined MCP servers."""
    print("Setting up local MCP server configuration...")

    # For this test, we'll simulate what the configuration should look like
    test_config = {
        "enabled": True,
        "servers": [
            {
                "name": "laser_server",
                "transport_type": "stdio",
                "command": "python servers/laser_server.py",
                "url": None
            },
            {
                "name": "search_server",
                "transport_type": "stdio",
                "command": "python servers/search_server.py",
                "url": None
            }
        ]
    }

    print(f"Test configuration: {test_config}")

    print("\nYou can now test by:")
    print("1. Starting the MCP servers: python servers/laser_server.py")
    print("2. Running the main application: python -m app.main")
    print("3. Making requests to the API endpoints")


if __name__ == "__main__":
    print("MCP Integration Test Suite")
    print("=" * 40)

    # Run async test
    asyncio.run(test_mcp_integration())

    print("\n")
    test_with_local_servers()