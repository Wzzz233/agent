#!/usr/bin/env python3
"""
Startup script for the THz Agent with MCP Server integration.

This script configures the environment to connect to MCP servers
and starts the main application.
"""

import os
import json
import subprocess
import sys
import signal
import time


def setup_environment():
    """Set up the environment variables for MCP servers."""
    print("Setting up MCP server configuration...")

    # Define MCP server configuration
    # Define MCP server configuration
    mcp_servers_config = [
        {
            "name": "ads2025_server",
            "transport_type": "stdio",
            "command": "python",
            "args": ["servers_local\\ads_server.py"]
        }
    ]

    # Set environment variables
    os.environ['MCP_ENABLED'] = 'true'
    os.environ['MCP_SERVERS'] = json.dumps(mcp_servers_config)

    print("Environment configured successfully!")
    print(f"MCP Servers: {[s['name'] for s in mcp_servers_config]}")


def main():
    """Main startup function."""
    print("Starting THz Agent with MCP Server Integration...")
    print("-" * 50)

    # Set up environment
    setup_environment()

    print("\nMCP Configuration:")
    print(f"  MCP Enabled: {os.environ.get('MCP_ENABLED', 'false')}")
    print(f"  MCP Servers: {os.environ.get('MCP_SERVERS', '[]')}")

    print("\nStarting main application...")
    print("-" * 50)

    try:
        # Run the main application
        from app.main import main as run_main_app
        run_main_app()
    except KeyboardInterrupt:
        print("\n\n🛑 Received interrupt signal. Shutting down...")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()