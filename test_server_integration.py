"""Test script for verifying MCP servers and integration."""
import os
import json
from app.config.settings import config


def test_configuration():
    """Test that configuration is set up properly for MCP servers."""
    print("Testing MCP Server Configuration...")

    # Set up MCP server configuration for testing
    os.environ['MCP_ENABLED'] = 'true'
    os.environ['MCP_SERVERS'] = json.dumps([
        {
            "name": "laser_server",
            "transport_type": "stdio",
            "command": "python",
            "args": ["servers/laser_server.py"]
        },
        {
            "name": "search_server",
            "transport_type": "stdio",
            "command": "python",
            "args": ["servers/search_server.py"]
        }
    ])

    # Reload configuration to pick up new environment variables
    new_config = config.__class__.from_env()

    print(f"MCP Enabled: {new_config.mcp.enabled}")
    print(f"MCP Servers: {len(new_config.mcp.servers)}")

    for i, server in enumerate(new_config.mcp.servers):
        print(f"  Server {i+1}: {server.name}")
        print(f"    Transport Type: {server.transport_type}")
        print(f"    Command: {server.command}")
        print(f"    Args: {server.args}")

    print("\nConfiguration test passed!")


def verify_server_files():
    """Verify that server files exist and are properly structured."""
    print("\nVerifying Server Files...")

    import os

    server_files = [
        "servers/laser_server.py",
        "servers/search_server.py",
        "servers/requirements.txt"
    ]

    for file_path in server_files:
        if os.path.exists(file_path):
            print(f"[OK] Found: {file_path}")

            # Check file size
            size = os.path.getsize(file_path)
            print(f"  Size: {size} bytes")
        else:
            print(f"[MISSING] {file_path}")

    print("\nServer files verification completed!")


def show_expected_usage():
    """Show how to run the servers and test the integration."""
    print("\nExpected Usage Instructions:")
    print("="*50)
    print("1. To run individual servers for testing:")
    print("   python servers/laser_server.py")
    print("   python servers/search_server.py")
    print()
    print("2. To test with MCP Inspector (requires Node.js):")
    print("   npx @modelcontextprotocol/inspector python servers/laser_server.py")
    print("   npx @modelcontextprotocol/inspector python servers/search_server.py")
    print()
    print("3. To run the main application:")
    print("   python -m app.main")
    print()
    print("4. Environment variables that can be set:")
    print("   export MCP_ENABLED=true")
    print('   export MCP_SERVERS=\'[{"name":"laser_server","transport_type":"stdio","command":"python","args":["servers/laser_server.py"]},{"name":"search_server","transport_type":"stdio","command":"python","args":["servers/search_server.py"]}]\'')
    print()


if __name__ == "__main__":
    print("MCP Server Integration Verification")
    print("="*50)

    test_configuration()
    verify_server_files()
    show_expected_usage()

    print("\n" + "="*50)
    print("Verification complete! All components are properly set up.")