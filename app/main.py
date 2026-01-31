"""
THz Agent API - FastAPI Application

Provides REST endpoints for:
1. Session-based chat (recommended)
2. Legacy stateless chat
3. Session management
4. Tool listing
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

from app.config.settings import config
from app.agents.services.agent_service import get_agent_service
from app.agents.services.session_manager import get_session_manager


# ==================== Pydantic Models ====================

class ChatRequest(BaseModel):
    """Legacy chat request (stateless)."""
    message: str
    history: Optional[List[Dict[str, Any]]] = []


class SessionChatRequest(BaseModel):
    """Session-based chat request."""
    message: str
    session_id: Optional[str] = None  # If None, creates new session


class ChatResponse(BaseModel):
    """Chat response model."""
    success: bool
    response: str
    message: str
    thoughts: Optional[List[Dict[str, Any]]] = []
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Session creation/info response."""
    success: bool
    session_id: str
    message_count: Optional[int] = 0
    created_at: Optional[str] = None
    last_activity: Optional[str] = None


class SessionListResponse(BaseModel):
    """List of sessions response."""
    success: bool
    sessions: List[Dict[str, Any]]
    count: int


class ToolsResponse(BaseModel):
    """Tools list response."""
    success: bool
    tools: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str


class IndexResponse(BaseModel):
    """Root endpoint response."""
    message: str
    version: str
    endpoints: Dict[str, str]


# ==================== FastAPI App ====================

app = FastAPI(
    title="THz Agent API",
    version="2.0.0",
    description="AI Agent with session-based state management"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Session-Based Chat (Recommended) ====================

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_with_session(request: SessionChatRequest):
    """
    Chat with the agent using session-based state.
    
    If session_id is provided, continues that conversation.
    If session_id is None, creates a new session.
    
    Session maintains conversation history automatically.
    """
    try:
        agent_service = get_agent_service()
        session_manager = get_session_manager()
        
        # Get or create session
        if request.session_id:
            session = session_manager.get_session(request.session_id)
            if not session:
                # Session expired or not found, create new one
                session = session_manager.create_session()
        else:
            session = session_manager.create_session()
        
        # Process message with session
        result = await agent_service.chat_with_session(
            session_id=session.session_id,
            message=request.message
        )
        
        return ChatResponse(
            success=True,
            response=result["response"],
            message=request.message,
            thoughts=result.get("thoughts", []),
            session_id=result.get("session_id", session.session_id)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


# ==================== Session Management ====================

@app.post("/api/v1/sessions/create", response_model=SessionResponse)
async def create_session():
    """Create a new conversation session."""
    try:
        session_manager = get_session_manager()
        session = session_manager.create_session()
        
        return SessionResponse(
            success=True,
            session_id=session.session_id,
            message_count=0,
            created_at=session.to_dict()["created_at"],
            last_activity=session.to_dict()["last_activity"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.get("/api/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session_info(session_id: str):
    """Get information about a specific session."""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f'Session {session_id} not found or expired')
        
        info = session.to_dict()
        return SessionResponse(
            success=True,
            session_id=session.session_id,
            message_count=info["message_count"],
            created_at=info["created_at"],
            last_activity=info["last_activity"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its history."""
    try:
        session_manager = get_session_manager()
        deleted = session_manager.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f'Session {session_id} not found')
        
        return {"success": True, "message": f"Session {session_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.post("/api/v1/sessions/{session_id}/clear")
async def clear_session_history(session_id: str):
    """Clear a session's message history but keep the session."""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f'Session {session_id} not found or expired')
        
        session.clear_messages()
        
        return {"success": True, "message": f"Session {session_id} history cleared"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.get("/api/v1/sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all active sessions."""
    try:
        session_manager = get_session_manager()
        sessions = session_manager.list_sessions()
        
        return SessionListResponse(
            success=True,
            sessions=sessions,
            count=len(sessions)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


# ==================== Legacy API (Stateless) ====================

@app.post("/api/v1/agent/chat", response_model=ChatResponse)
async def chat_legacy(request: ChatRequest):
    """
    Legacy chat endpoint (stateless).
    
    DEPRECATED: Use /api/v1/chat with session_id for persistent conversations.
    """
    try:
        if request.history:
            for msg in request.history:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    raise HTTPException(
                        status_code=400,
                        detail='Each message in history must have role and content fields'
                    )

        agent_service = get_agent_service()
        result = await agent_service.process_message_async(request.message, request.history)
        
        return ChatResponse(
            success=True,
            response=result["response"],
            message=request.message,
            thoughts=result.get("thoughts", [])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


# ==================== Tools & Health ====================

@app.get("/api/v1/tools/list", response_model=ToolsResponse)
async def list_tools():
    """List available tools."""
    try:
        agent_service = get_agent_service()
        tools = agent_service.get_available_tools()
        return ToolsResponse(success=True, tools=tools)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="healthy", service="THz Agent")


@app.get("/", response_model=IndexResponse)
async def index():
    """Root endpoint with API information."""
    return IndexResponse(
        message="THz Agent API",
        version="2.0.0",
        endpoints={
            "chat": "/api/v1/chat (session-based, recommended)",
            "chat_legacy": "/api/v1/agent/chat (stateless, deprecated)",
            "sessions": "/api/v1/sessions",
            "tools": "/api/v1/tools/list",
            "health": "/health"
        }
    )


# ==================== Main Entry ====================

def main():
    """Main entry point for the application."""
    import uvicorn

    print(f"Starting THz Agent API v2.0 on {config.server.host}:{config.server.port}")
    print("Session-based state management enabled")

    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug
    )


if __name__ == '__main__':
    main()