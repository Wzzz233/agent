"""
ADS Agent Workflow State Machine

This module manages the workflow state for the ADS MCP Agent.
It provides:
- State definition and transitions
- Context persistence (plan, design_uri, etc.)
- Dynamic tool visibility based on state
- Dynamic Prompt injection based on state

State Machine:
    IDLE -> PLANNING -> SCHEMATIC_CREATED -> WAITING_USER -> COMPONENT_ADDING -> COMPLETED
                                                                      |
                                                                      v
                                                                   (reset) -> IDLE
"""

import os
import json
import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("ads-workflow-manager")

# ===================== Constants =====================

STATE_FILE = os.path.join(os.path.dirname(__file__), ".workflow_state.json")


# ===================== State Definitions =====================

class WorkflowState(str, Enum):
    """
    Workflow States for the ADS Agent.
    
    State Transitions:
    - IDLE: Initial state, no active workflow
    - PLANNING: Agent is creating a circuit plan (plan_circuit called)
    - SCHEMATIC_CREATED: Schematic file created, waiting for user to open in ADS
    - WAITING_USER: System is waiting for user confirmation
    - COMPONENT_ADDING: Design is open, Agent can add components
    - COMPLETED: Workflow finished successfully
    """
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    SCHEMATIC_CREATED = "SCHEMATIC_CREATED"
    WAITING_USER = "WAITING_USER"
    COMPONENT_ADDING = "COMPONENT_ADDING"
    COMPLETED = "COMPLETED"


# ===================== Tool Registry =====================

# Define which tools are available in each state
# This is the CORE of dynamic tool visibility
TOOLS_BY_STATE: Dict[WorkflowState, Set[str]] = {
    WorkflowState.IDLE: {
        "check_connection",
        "get_project_structure",
        "list_cells",
        "check_cell_exists",
        "get_current_design",
        "get_workflow_status",
        "plan_circuit",  # Start a new design workflow
        "open_existing_design",  # Open existing design for editing
    },
    WorkflowState.PLANNING: {
        "check_connection",
        "get_workflow_status",
        "plan_circuit",  # Allow re-planning
        "reset_workflow",  # Escape hatch
    },
    WorkflowState.SCHEMATIC_CREATED: {
        "check_connection",
        "get_workflow_status",
        "get_current_design",  # Read-only, safe to allow
        "execute_circuit_plan",
        "reset_workflow",
    },
    WorkflowState.WAITING_USER: {
        "check_connection",
        "get_workflow_status",
        "get_current_design",  # To verify user opened the design
        "confirm_design_open",  # New tool to confirm user action
        "reset_workflow",
    },
    WorkflowState.COMPONENT_ADDING: {
        "check_connection",
        "get_workflow_status",
        "get_current_design",
        "add_component",
        "add_wire",
        "add_components_from_plan",
        "save_current_design",
        "finish_design",  # Complete the workflow
        "reset_workflow",
    },
    WorkflowState.COMPLETED: {
        "check_connection",
        "get_workflow_status",
        "get_project_structure",
        "plan_circuit",  # Start a new design
        "reset_workflow",
    },
}

# Tools that are ALWAYS available regardless of state (global read-only tools)
GLOBAL_TOOLS: Set[str] = {
    "reset_workflow",       # Escape hatch (except IDLE)
    "get_workflow_status",  # Always show current state
    "check_connection",     # Always allow connection check
}


# ===================== System Prompts by State =====================

STATE_PROMPTS: Dict[WorkflowState, str] = {
    WorkflowState.IDLE: """
### Current Status: IDLE
You are ready to start a new design workflow. 
Available actions:
- Check ADS connection status
- View project structure and available libraries
- Start a new circuit design with `plan_circuit`
""",
    WorkflowState.PLANNING: """
### Current Status: PLANNING
You are creating a circuit plan. 
- Use `plan_circuit` to define components
- Once satisfied, the plan will be ready for execution
- Use `reset_workflow` to cancel and start over
""",
    WorkflowState.SCHEMATIC_CREATED: """
### Current Status: SCHEMATIC_CREATED
A circuit plan has been created and is ready for execution.
- Use `execute_circuit_plan` to create the schematic in ADS
- Use `reset_workflow` to cancel
""",
    WorkflowState.WAITING_USER: """
### Current Status: WAITING FOR USER
⚠️ **IMPORTANT**: The schematic has been created in ADS.

You CANNOT execute any design actions until the user confirms they have opened the design.

Please ask the user to:
1. Open ADS
2. Navigate to the created schematic
3. Confirm by saying "已打开" or "I have opened it"

Then use `confirm_design_open` to proceed, or `reset_workflow` to start over.
""",
    WorkflowState.COMPONENT_ADDING: """
### Current Status: COMPONENT_ADDING
The design is open and ready for editing.
Available actions:
- `add_component` - Add individual components
- `add_wire` - Connect components with wires
- `add_components_from_plan` - Add all planned components at once
- `save_current_design` - Save the design
- `finish_design` - Complete the workflow
- `reset_workflow` - Cancel and start over
""",
    WorkflowState.COMPLETED: """
### Current Status: COMPLETED
The design workflow has been completed successfully.
You can:
- Start a new design with `plan_circuit`
- Check project structure
- Reset to idle state
""",
}


# ===================== Workflow Context =====================

@dataclass
class WorkflowContext:
    """
    Stores all context data for the current workflow session.
    This is persisted to disk for resumption.
    """
    state: WorkflowState = WorkflowState.IDLE
    plan_id: Optional[str] = None
    plan_data: Optional[Dict[str, Any]] = None
    design_uri: Optional[str] = None
    library_name: Optional[str] = None
    cell_name: Optional[str] = None
    components_added: int = 0
    total_components: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["state"] = self.state.value  # Convert enum to string
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowContext":
        """Create from dictionary."""
        if "state" in data:
            data["state"] = WorkflowState(data["state"])
        return cls(**data)


# ===================== Workflow Manager =====================

class WorkflowManager:
    """
    Manages the workflow state machine for ADS Agent.
    
    Responsibilities:
    - State transitions with validation
    - Context persistence
    - Dynamic tool filtering
    - Dynamic prompt generation
    """
    
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.context = self._load_state()
        logger.info(f"WorkflowManager initialized. Current state: {self.context.state}")
    
    # ==================== Persistence ====================
    
    def _load_state(self) -> WorkflowContext:
        """Load state from file, or return default."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded workflow state from file: {data.get('state')}")
                    return WorkflowContext.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load workflow state: {e}")
        return WorkflowContext()
    
    def _save_state(self):
        """Persist state to file."""
        try:
            self.context.last_updated = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.context.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved workflow state: {self.context.state}")
        except Exception as e:
            logger.error(f"Failed to save workflow state: {e}")
    
    # ==================== State Access ====================
    
    @property
    def state(self) -> WorkflowState:
        """Get current state."""
        return self.context.state
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get full state information for API responses."""
        return {
            "state": self.context.state.value,
            "plan_id": self.context.plan_id,
            "design_uri": self.context.design_uri,
            "components_added": self.context.components_added,
            "total_components": self.context.total_components,
            "last_updated": self.context.last_updated,
        }
    
    # ==================== State Transitions ====================
    
    def transition_to(self, new_state: WorkflowState, **kwargs) -> bool:
        """
        Transition to a new state with optional context updates.
        
        Args:
            new_state: Target state
            **kwargs: Context fields to update (plan_id, design_uri, etc.)
            
        Returns:
            True if transition was successful
        """
        old_state = self.context.state
        
        # Validate transition (basic check - allow any transition for flexibility)
        valid_transitions = self._get_valid_transitions(old_state)
        if new_state not in valid_transitions and new_state != WorkflowState.IDLE:
            logger.warning(f"Invalid transition: {old_state} -> {new_state}")
            # Allow anyway with warning for flexibility
        
        # Update state
        self.context.state = new_state
        
        # Update context fields
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        
        self._save_state()
        logger.info(f"State transition: {old_state} -> {new_state}")
        return True
    
    def _get_valid_transitions(self, from_state: WorkflowState) -> Set[WorkflowState]:
        """Get valid target states from current state."""
        transitions = {
            WorkflowState.IDLE: {WorkflowState.PLANNING},
            WorkflowState.PLANNING: {WorkflowState.SCHEMATIC_CREATED, WorkflowState.IDLE},
            WorkflowState.SCHEMATIC_CREATED: {WorkflowState.WAITING_USER, WorkflowState.IDLE},
            WorkflowState.WAITING_USER: {WorkflowState.COMPONENT_ADDING, WorkflowState.IDLE},
            WorkflowState.COMPONENT_ADDING: {WorkflowState.COMPLETED, WorkflowState.IDLE},
            WorkflowState.COMPLETED: {WorkflowState.IDLE, WorkflowState.PLANNING},
        }
        return transitions.get(from_state, {WorkflowState.IDLE})
    
    def reset(self) -> Dict[str, Any]:
        """Reset workflow to IDLE state."""
        old_state = self.context.state
        self.context = WorkflowContext()  # Fresh context
        self._save_state()
        logger.info(f"Workflow reset from {old_state} to IDLE")
        return {
            "status": "success",
            "message": f"工作流已重置。从 {old_state.value} 返回到 IDLE 状态。",
            "previous_state": old_state.value,
            "current_state": WorkflowState.IDLE.value
        }
    
    # ==================== Plan Management ====================
    
    def set_plan(self, plan_id: str, plan_data: Dict[str, Any]):
        """Store a circuit plan and transition to PLANNING -> SCHEMATIC_CREATED."""
        self.context.plan_id = plan_id
        self.context.plan_data = plan_data
        self.context.total_components = len(plan_data.get("components", []))
        
        circuit = plan_data.get("circuit", {})
        self.context.library_name = circuit.get("library")
        self.context.cell_name = circuit.get("name")
        self.context.design_uri = circuit.get("design_uri")
        
        self.transition_to(WorkflowState.SCHEMATIC_CREATED)
    
    def get_plan(self) -> Optional[Dict[str, Any]]:
        """Get the current plan data."""
        return self.context.plan_data
    
    def set_design_uri(self, design_uri: str):
        """Update design URI after schematic creation."""
        self.context.design_uri = design_uri
        self._save_state()
    
    def increment_components_added(self, count: int = 1):
        """Track component addition progress."""
        self.context.components_added += count
        self._save_state()
    
    # ==================== Tool Visibility ====================
    
    def get_allowed_tools(self) -> Set[str]:
        """
        Get the set of tool names allowed in the current state.
        This is the CORE function for dynamic tool visibility.
        """
        state_tools = TOOLS_BY_STATE.get(self.context.state, set())
        
        # Add global tools (except in IDLE where reset is not needed)
        if self.context.state != WorkflowState.IDLE:
            state_tools = state_tools | GLOBAL_TOOLS
        
        return state_tools
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a specific tool is allowed in current state."""
        return tool_name in self.get_allowed_tools()
    
    # ==================== Dynamic Prompt Injection ====================
    
    def get_state_prompt(self) -> str:
        """
        Get the system prompt for the current state.
        This should be injected into the LLM context.
        """
        base_prompt = STATE_PROMPTS.get(self.context.state, "")
        
        # Add context-specific information
        context_info = []
        if self.context.plan_id:
            context_info.append(f"- Active Plan ID: `{self.context.plan_id}`")
        if self.context.design_uri:
            context_info.append(f"- Design URI: `{self.context.design_uri}`")
        if self.context.total_components > 0:
            context_info.append(f"- Progress: {self.context.components_added}/{self.context.total_components} components")
        
        if context_info:
            base_prompt += "\n\n**Current Context:**\n" + "\n".join(context_info)
        
        return base_prompt
    
    def get_full_system_context(self) -> Dict[str, Any]:
        """
        Get full context for MCP prompts/list response.
        """
        return {
            "state": self.context.state.value,
            "prompt": self.get_state_prompt(),
            "allowed_tools": list(self.get_allowed_tools()),
            "context": {
                "plan_id": self.context.plan_id,
                "design_uri": self.context.design_uri,
                "library": self.context.library_name,
                "cell": self.context.cell_name,
            }
        }


# ===================== Singleton Instance =====================

# Global instance for use across the MCP server
_workflow_manager: Optional[WorkflowManager] = None

def get_workflow_manager() -> WorkflowManager:
    """Get or create the global WorkflowManager instance."""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager

def reset_workflow_manager():
    """Reset the global WorkflowManager instance (for testing)."""
    global _workflow_manager
    _workflow_manager = None
