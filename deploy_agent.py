"""Modal deployment script for the THz Agent with MCP Server integration."""

import modal
from modal import Image, Secret, asgi_app

# Define the Modal app (updated API)
app = modal.App("thz-agent-mcp")

# 构建镜像并直接挂载代码
image = (
    Image.debian_slim()
    .pip_install(
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "pydantic>=2.4.2",
        "qwen-agent[all]>=0.0.30",
        "ddgs>=0.1.8",
        "typing-extensions>=4.8.0",
        "requests>=2.31.0",
        "mcp>=1.0.0",
        "httpx>=0.25.0",
        "python-dateutil>=2.8.0"
    )
    .add_local_dir("app", remote_path="/root/app")
    .add_local_dir("servers", remote_path="/root/servers")
)

@app.function(
    image=image,
    secrets=[Secret.from_name("agent-secrets")],
    min_containers=1,
    timeout=300
)
@asgi_app()
def fastapi_app():
    """Deploy the FastAPI application on Modal."""
    import os
    import json

    # Set MCP configuration via environment variables
    # Following the JSON format specification from the requirements
    mcp_servers_config = []

    # Add search server as stdio process (running on the same container)
    mcp_servers_config.append({
        "name": "search",
        "transport_type": "stdio",
        "command": "python",
        "args": ["/root/servers/search_server.py"]
    })

    # Add laser server configuration (using HTTP/SSE if NGROK_URL is provided via secrets)
    # First, let's get the secrets to access NGROK_URL
    try:
        # The secrets are automatically available in the function environment
        ngrok_url = os.environ.get("NGROK_URL")

        if ngrok_url and ngrok_url != "" and ngrok_url != "${NGROK_URL}":
            # Add laser server using HTTP transport pointing to ngrok URL
            mcp_servers_config.append({
                "name": "laser",
                "transport_type": "http",  # Using HTTP instead of SSE for simplicity
                "url": f"{ngrok_url}/laser/control"  # Standard laser control endpoint
            })
        else:
            print("NGROK_URL not provided or invalid, laser server will not be configured")
    except Exception as e:
        print(f"Error configuring laser server from NGROK_URL: {e}")

    # Set the MCP servers configuration as an environment variable
    os.environ['MCP_SERVERS'] = json.dumps(mcp_servers_config)
    os.environ['MCP_ENABLED'] = 'true'

    print(f"MCP Configuration: {os.environ['MCP_SERVERS']}")

    # Import and return the FastAPI app after setting up environment
    # This ensures the configuration is loaded with the proper MCP settings
    from app.main import app

    # Re-initialize config to pick up new environment variables
    from app.config.settings import Config
    import app.config.settings as settings_module
    settings_module.config = Config.from_env()
    settings_module.config.validate()

    return app