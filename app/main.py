from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from app.config.settings import config
from app.agents.services.agent_service import get_agent_service
import asyncio


# Define Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = []



class ChatResponse(BaseModel):
    success: bool
    response: str
    message: str
    thoughts: Optional[List[Dict[str, Any]]] = []


class SessionResponse(BaseModel):
    success: bool
    session_id: str


class ToolsResponse(BaseModel):
    success: bool
    tools: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    service: str


class IndexResponse(BaseModel):
    message: str
    version: str
    endpoints: Dict[str, str]


# Create FastAPI app
app = FastAPI(title="THz Agent API", version="1.0.0")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/agent/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint for chat interaction with the agent"""
    try:
        # Validate history format if provided
        if request.history:
            for msg in request.history:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    raise HTTPException(status_code=400,
                                      detail='Each message in history must have role and content fields')

        # Process the message
        agent_service = get_agent_service()
        result = await agent_service.process_message_async(request.message, request.history)
        
        return ChatResponse(
            success=True,
            response=result["response"],
            message=request.message,
            thoughts=result["thoughts"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.post("/api/v1/sessions/create", response_model=SessionResponse)
async def create_session():
    """Endpoint to create a new conversation session"""
    try:
        import uuid
        session_id = 'session_' + str(uuid.uuid4())
        return SessionResponse(success=True, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.get("/api/v1/tools/list", response_model=ToolsResponse)
async def list_tools():
    """Endpoint to list available tools"""
    try:
        agent_service = get_agent_service()
        tools = agent_service.get_available_tools()
        return ToolsResponse(success=True, tools=tools)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(status="healthy", service="THz Agent")


@app.get("/", response_model=IndexResponse)
async def index():
    """Root endpoint"""
    return IndexResponse(
        message="THz Agent API",
        version="1.0.0",
        endpoints={
            "chat": "/api/v1/agent/chat",
            "tools": "/api/v1/tools/list",
            "mcp": "/mcp/v1/call"  # Keep MCP endpoint reference
        }
    )


def main():
    """Main entry point for the application"""
    import uvicorn

    print(f"Starting THz Agent API on {config.server.host}:{config.server.port}")

    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug
    )


if __name__ == '__main__':
    main()