"""
Adapter Layer - Dynamic Prompt Injection for MCP Tools

Injects negative constraints and guidance into tool descriptions
to prevent intent drift and guide model behavior.
"""

from typing import Dict, Any


class AdapterLayerConfig:
    """Configuration for adapter layer behavior"""

    # Tools that should NOT be called multiple times
    SINGLE_USE_TOOLS = {
        "plan_circuit": "Only call this ONCE per design. CRITICAL: Call get_current_design FIRST - if user already has a design open, DO NOT call this tool. Only use when creating a NEW schematic.",
        "execute_circuit_plan": "Only call this ONCE per plan. CRITICAL: Call get_current_design FIRST - if user already has a design open, DO NOT call this tool. Only use when creating a NEW schematic.",
        "add_components_from_plan": "Only call this ONCE per plan. After components added, task is complete.",
    }

    # Tools that require specific preconditions
    PRECONDITION_TOOLS = {
        "add_component": "ONLY use when user explicitly asks to add a single component. For batch adding, use add_components_from_plan.",
        "add_components_from_plan": "ONLY use after execute_circuit_plan has completed AND user has confirmed design is open in ADS.",
        "check_cell_exists": "ONLY call AFTER get_project_structure has been called to verify available libraries. DO NOT guess library names.",
    }

    # Tools that signal task completion
    COMPLETION_TOOLS = {
        "add_components_from_plan": "This completes the circuit design task. STOP after calling this tool.",
        "save_current_design": "This completes the save operation. STOP after calling this tool.",
    }

    # Tools that should be called first (discovery tools)
    DISCOVERY_TOOLS = {
        "get_project_structure": "RECOMMENDED FIRST STEP: Call this before any design operations to understand available libraries and cells.",
        "get_current_design": "CRITICAL: Call this to check if user already has a schematic open. If open, you can design directly WITHOUT creating new cells.",
        "list_cells": "Call AFTER get_project_structure to see all cells in a specific library.",
    }

    # Decision tree guidance for model
    DECISION_GUIDANCE = {
        "workflow_selection": "WORKFLOW DECISION: 1) Call get_current_design first. 2) If design is open → design directly. 3) If no design open → ask user if they want to create new cell or use existing one.",
        "check_cell_exists": "ONLY use when explicitly verifying a cell exists. Do NOT use for workflow decision - use get_current_design instead.",
    }


class AdapterLayer:
    """Manages dynamic prompt injection for tools"""

    def __init__(self, config: AdapterLayerConfig = None):
        self.config = config or AdapterLayerConfig()

    def inject_constraints(
        self,
        tool_name: str,
        original_description: str
    ) -> str:
        """
        Inject negative constraints into tool description.

        Args:
            tool_name: Name of the tool
            original_description: Original tool description

        Returns:
            Enhanced description with constraints
        """
        constraints = []

        # CRITICAL: Workflow decision guidance for ALL tools
        if tool_name in ["plan_circuit", "execute_circuit_plan", "add_component"]:
            constraints.append(f"🎯 {self.config.DECISION_GUIDANCE['workflow_selection']}")

        # Add discovery tool recommendation
        if tool_name in self.config.DISCOVERY_TOOLS:
            constraints.append(f"💡 RECOMMENDATION: {self.config.DISCOVERY_TOOLS[tool_name]}")

        # Add single-use warning
        if tool_name in self.config.SINGLE_USE_TOOLS:
            constraints.append(f"⚠️ WARNING: {self.config.SINGLE_USE_TOOLS[tool_name]}")

        # Add precondition warning
        if tool_name in self.config.PRECONDITION_TOOLS:
            constraints.append(f"⚠️ PRECONDITION: {self.config.PRECONDITION_TOOLS[tool_name]}")

        # Add completion signal
        if tool_name in self.config.COMPLETION_TOOLS:
            constraints.append(f"✅ COMPLETION: {self.config.COMPLETION_TOOLS[tool_name]}")

        if not constraints:
            return original_description

        # Build enhanced description
        enhanced = f"{original_description}\n\n"
        enhanced += "│ ⚠️ IMPORTANT CONSTRAINTS:\n"
        for constraint in constraints:
            enhanced += f"│ • {constraint}\n"

        return enhanced

    def inject_system_instruction(
        self,
        tool_name: str,
        tool_result: Dict[str, Any]
    ) -> str:
        """
        Generate system instruction based on tool call result.
        This is added to the conversation to guide model behavior.

        Args:
            tool_name: Name of the tool called
            tool_result: Result from the tool

        Returns:
            System instruction string (or empty if not needed)
        """
        # Single-use tool was called
        if tool_name in self.config.SINGLE_USE_TOOLS:
            return (
                f"CRITICAL: Tool '{tool_name}' has been called. "
                f"Do NOT call this tool again in this session."
            )

        # Completion tool was called
        if tool_name in self.config.COMPLETION_TOOLS:
            return (
                f"TASK COMPLETED: '{tool_name}' has finished the current task. "
                f"Wait for user's next instruction before calling more tools."
            )

        return ""
