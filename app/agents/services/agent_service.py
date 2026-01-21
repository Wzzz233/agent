
from typing import List, Dict, Any, Optional

class AgentService:
    """Mock Service class to manage the THz agent instance"""

    def __init__(self):
        pass

    async def process_message_async(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        return f"Echo: {message}"

    def get_available_tools(self) -> List[Dict[str, Any]]:
        return []

# Global agent service instance
_agent_service_instance = None

def get_agent_service():
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance