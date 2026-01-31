"""
Session Manager - Per-session state management for the agent

Provides:
1. Session creation and lifecycle management
2. Per-session message history
3. Per-session ControlLayer state
4. Session cleanup and expiration

No more global singleton - each session is independent.
"""
import uuid
import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.agents.control_layer import ControlLayer, ControlLayerConfig


@dataclass
class Session:
    """
    Represents a single conversation session.
    
    Each session maintains its own:
    - Message history
    - ControlLayer instance
    - Metadata
    """
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    # Per-session message history (OpenAI format)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Per-session control layer
    control_layer: ControlLayer = field(default_factory=lambda: ControlLayer(ControlLayerConfig()))
    
    # Optional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the session history."""
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self.messages.append(msg)
        self.last_activity = time.time()
    
    def add_tool_call_message(self, message: Any) -> None:
        """Add an assistant message with tool calls."""
        self.messages.append(message)
        self.last_activity = time.time()
    
    def add_tool_result(self, tool_call_id: str, name: str, content: str) -> None:
        """Add a tool result message."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })
        self.last_activity = time.time()
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in the session."""
        return self.messages.copy()
    
    def clear_messages(self) -> None:
        """Clear message history but keep the session."""
        self.messages.clear()
        self.control_layer = ControlLayer(ControlLayerConfig())
        self.last_activity = time.time()
    
    def get_age_seconds(self) -> float:
        """Get session age in seconds."""
        return time.time() - self.created_at
    
    def get_idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self.last_activity
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dict (for API responses)."""
        return {
            "session_id": self.session_id,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_activity": datetime.fromtimestamp(self.last_activity).isoformat(),
            "message_count": len(self.messages),
            "age_seconds": self.get_age_seconds(),
            "idle_seconds": self.get_idle_seconds(),
            "metadata": self.metadata
        }


class SessionManager:
    """
    Manages multiple conversation sessions.
    
    Thread-safe session creation, retrieval, and cleanup.
    """
    
    # Default session expiration: 30 minutes
    DEFAULT_EXPIRATION_SECONDS = 30 * 60
    
    # Maximum sessions to prevent memory issues
    MAX_SESSIONS = 100
    
    def __init__(self, expiration_seconds: Optional[float] = None):
        """
        Initialize the session manager.
        
        Args:
            expiration_seconds: Session expiration time (default 30 min)
        """
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        self._expiration = expiration_seconds or self.DEFAULT_EXPIRATION_SECONDS
    
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """
        Create a new session.
        
        Args:
            metadata: Optional metadata for the session
            
        Returns:
            The new Session instance
        """
        with self._lock:
            # Cleanup expired sessions first
            self._cleanup_expired()
            
            # Check max sessions
            if len(self._sessions) >= self.MAX_SESSIONS:
                # Remove oldest session
                oldest_id = min(self._sessions.keys(), 
                               key=lambda k: self._sessions[k].last_activity)
                del self._sessions[oldest_id]
            
            # Generate unique session ID
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            # Create session
            session = Session(
                session_id=session_id,
                metadata=metadata or {}
            )
            
            self._sessions[session_id] = session
            print(f"[SessionManager] Created session: {session_id}")
            
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            Session if found and not expired, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                return None
            
            # Check if expired
            if session.get_idle_seconds() > self._expiration:
                print(f"[SessionManager] Session expired: {session_id}")
                del self._sessions[session_id]
                return None
            
            return session
    
    def get_or_create_session(
        self, 
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Get existing session or create a new one.
        
        Args:
            session_id: Optional session ID to retrieve
            metadata: Metadata for new session if created
            
        Returns:
            Session instance
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        return self.create_session(metadata)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                print(f"[SessionManager] Deleted session: {session_id}")
                return True
            return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions.
        
        Returns:
            List of session info dicts
        """
        with self._lock:
            self._cleanup_expired()
            return [s.to_dict() for s in self._sessions.values()]
    
    def _cleanup_expired(self) -> int:
        """
        Remove expired sessions.
        
        Returns:
            Number of sessions removed
        """
        expired = [
            sid for sid, session in self._sessions.items()
            if session.get_idle_seconds() > self._expiration
        ]
        
        for sid in expired:
            del self._sessions[sid]
        
        if expired:
            print(f"[SessionManager] Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def get_session_count(self) -> int:
        """Get number of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
