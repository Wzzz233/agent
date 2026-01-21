# THz Agent - MCP Modal Deployment Guide

## Overview
This guide describes the process for deploying the THz Agent with MCP Server integration to Modal.

## Prerequisites

### 1. Environment Configuration & Credential Preparation

Before any code deployment, secure credentials must be hosted in Modal Console. Never embed keys directly in code files.

#### Create Modal Secret:
```bash
modal secret create agent-secrets \
  LLM_MODEL_SERVER="<your_model_server_url>" \
  LLM_API_KEY="<your_api_key>" \
  NGROK_URL="<your_ngrok_url>"
```

#### Confirm Configuration:
| Key | Expected Value Example | Validation Method |
| --- | --- | --- |
| LLM_MODEL_SERVER | https://wzzz233--qwen3-openai-api-serve.modal.run/v1 | Browser access should return {"detail":"Not Found"} rather than connection timeout |
| LLM_API_KEY | sk-qyqpyojdysuvzmkjrsxjkzwbpgfjferenzhgmokairbwgkps | Should match the key set when deploying inference model in Phase 2 |
| NGROK_URL | https://xxxx.ngrok-free.app | Ensure local laser service is mapped through Ngrok and online (placeholder for now) |

## Deployment Process

### 2. Script Writing - deploy_agent.py

The deployment script is located in the project root and follows these structural guidelines:

#### Image Definition:
- Uses `modal.Image.debian_slim().pip_install(...)` to pre-install fastapi, uvicorn, mcp, httpx, qwen-agent and other core libraries
- Must include `qwen-agent[all]` to ensure tool call logic completeness

#### Code Mounting:
- Uses `.add_local_dir("app", remote_path="/root/app")` to mount business logic
- Uses `.add_local_dir("servers", remote_path="/root/servers")` to mount local tool code

#### Function Declaration:
- Uses `@app.function(secrets=[modal.Secret.from_name("agent-secrets")], keep_warm=1)`
- Uses `@modal.asgi_app()` decorator to wrap function returning FastAPI instance

### 3. Deploy Command Execution

During execution, maintain stable terminal connection and record generated key information.

#### Permission Verification:
```bash
modal token new  # Refresh login state to ensure deployment permissions are not expired
```

#### Deployment Execution:
```bash
modal deploy deploy_agent.py
```

#### Terminal Output Record:
- Record the URL following "Created ..." ending with .modal.run
- Access Modal Dashboard to confirm that agent-secrets is correctly bound to the deployed function

### 4. Cloud Service Multi-Dimensional Verification

After successful deployment, conduct deep infrastructure-to-business-logic checks in sequence:

#### Interface Liveliness Detection:
Access https://<Agent-address>/docs - if Swagger page doesn't open, check that FastAPI import paths in deploy_agent.py are correct.

#### Model End-to-End Testing:
Call `/api/v1/chat` via Swagger sending "Ping" and observe if response contains Qwen model's characteristic replies.

#### Log Monitoring:
Run `modal volume ls` in terminal or monitor inference connections in Dashboard's Logs page. If 401 errors appear, immediately check if LLM_API_KEY is configured incorrectly.

### 5. MCP Tool Chain Configuration

Pre-configure for Phase 5 hardware integration - the key step to achieve "cloud brain" control of "local laser":

#### Environment Variable Injection:
Set MCP_SERVERS variable in deploy_agent.py or Dashboard.

#### JSON Format Specification:
- Laser Server: `{"name": "laser", "transport_type": "sse", "url": "${NGROK_URL}/sse"}`
- Search Server: `{"name": "search", "transport_type": "stdio", "command": "python", "args": ["/root/servers/search_server.py"]}`

## Risk Management

### Path Offset Risk:
In Modal containers, `__file__` paths change. When referencing tools or configuration files in business code, always use absolute paths based on `/root/`, never relative paths `./`.

### Cold Start & Timeout Risk:
Although `keep_warm=1` is set, 5-10 second delays may still occur during high concurrency or auto-scaling. Consider adding retry mechanisms in the frontend, or set `timeout=300` in `app.function` to prevent connection interruption during complex tool calls.

### Tool Call Parsing Failure:
Qwen models in vLLM environments may output non-standard JSON format. If Agent cannot trigger tools, check that `qwen_adapter.py` correctly handles the `tool_calls` field. If necessary, force specify `--tool-call-parser qwen` parameter on the inference side.

## Files Structure
- `deploy_agent.py` - Main deployment script
- `app/` - Application logic (mounted to /root/app)
- `servers/` - MCP server implementations (mounted to /root/servers)