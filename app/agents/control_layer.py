"""
Control Layer - Physical Circuit Breaker for Agent Execution

Provides:
1. Declarative termination action whitelist
2. Semantic termination detection
3. Loop state management
4. Backward compatibility with existing checks
"""

from typing import Set, Dict, Any, Optional
from enum import Enum
import json


class TerminationReason(Enum):
    """Reasons for agent termination"""
    TERMINATION_ACTION_CALLED = "termination_action"
    USER_CONFIRMATION_REQUIRED = "user_confirmation_required"
    TOOL_CALL_LIMIT_REACHED = "tool_call_limit"
    INFINITE_LOOP_DETECTED = "infinite_loop"
    TASK_COMPLETED = "task_completed"
    ERROR_OCCURRED = "error"


class ControlLayerConfig:
    """Configuration for control layer behavior"""

    # Tools that trigger immediate termination
    TERMINATION_ACTIONS: Set[str] = {
        "add_components_from_plan",
        "execute_circuit_plan",
        "save_current_design",
        # Add more as needed
    }

    # Tools that require user confirmation (stop and wait)
    CONFIRMATION_REQUIRED_ACTIONS: Set[str] = {
        "plan_circuit",
        # Add more as needed
    }

    # Maximum tools per session (global fallback)
    MAX_TOOL_CALLS_TOTAL = 15
    MAX_TOOL_CALLS_PER_TOOL = 5

    # Loop detection threshold
    MAX_SAME_TOOL_CALLS = 3


class LoopState:
    """Track execution state for loop detection"""

    def __init__(self):
        self.turn_count = 0
        self.tools_called_in_session = []
        self.tool_call_signatures = []
        self.last_tool_call_signature = ""
        self.consecutive_same_tool_calls = 0

    def record_tool_call(self, tool_name: str, tool_args: Dict[str, Any]):
        """Record a tool call for loop detection"""
        signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"

        if signature == self.last_tool_call_signature:
            self.consecutive_same_tool_calls += 1
        else:
            self.consecutive_same_tool_calls = 0

        self.last_tool_call_signature = signature
        self.tool_call_signatures.append(signature)
        self.tools_called_in_session.append(tool_name)


class ControlLayer:
    """Main control layer for agent execution"""

    def __init__(self, config: Optional[ControlLayerConfig] = None):
        self.config = config or ControlLayerConfig()
        self.state = LoopState()

    def should_terminate_after_tool(
        self,
        tool_name: str,
        tool_result: Any
    ) -> tuple[bool, Optional[TerminationReason], str]:
        """
        Check if execution should terminate after a tool call.

        Args:
            tool_name: Name of the tool just called
            tool_result: Result returned by the tool

        Returns:
            (should_terminate, reason, message)
        """
        # Check 1: Termination action
        if tool_name in self.config.TERMINATION_ACTIONS:
            # Only terminate if successful
            if self._is_successful_result(tool_result):
                return True, TerminationReason.TERMINATION_ACTION_CALLED, (
                    f"✓ Task completed by '{tool_name}'. "
                    f"Execution stopped to prevent redundant actions."
                )

        # Check 2: User confirmation required
        if tool_name in self.config.CONFIRMATION_REQUIRED_ACTIONS:
            return True, TerminationReason.USER_CONFIRMATION_REQUIRED, (
                f"⏸️ Tool '{tool_name}' requires user confirmation. "
                f"Waiting for user input before proceeding."
            )

        # Check 3: Infinite loop detection
        if self.state.consecutive_same_tool_calls >= self.config.MAX_SAME_TOOL_CALLS:
            return True, TerminationReason.INFINITE_LOOP_DETECTED, (
                f"⚠️ Detected infinite loop on '{tool_name}'. "
                f"Execution stopped after {self.state.consecutive_same_tool_calls} identical calls."
            )

        # Check 4: Tool call limit
        if len(self.state.tools_called_in_session) >= self.config.MAX_TOOL_CALLS_TOTAL:
            return True, TerminationReason.TOOL_CALL_LIMIT_REACHED, (
                f"⚠️ Reached maximum tool calls ({self.config.MAX_TOOL_CALLS_TOTAL}). "
                f"Please confirm before continuing."
            )

        return False, None, ""

    def _is_successful_result(self, result: Any) -> bool:
        """Check if tool result indicates success"""
        if isinstance(result, str):
            # Check for wrapped result format
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict):
                    return parsed.get("status") == "success"
            except json.JSONDecodeError:
                pass
            # Check for success indicators in string
            return "success" in result.lower() or "✓" in result or "✅" in result

        if isinstance(result, dict):
            return result.get("status") == "success"

        return False

    def record_tool_call(self, tool_name: str, tool_args: Dict[str, Any]):
        """Record a tool call in the loop state"""
        self.state.record_tool_call(tool_name, tool_args)
        self.state.turn_count += 1

    def get_termination_message(
        self,
        reason: TerminationReason,
        tool_result: Any
    ) -> str:
        """
        Generate user-friendly termination message.

        This wraps tool results into natural language for display.
        """
        # Extract summary from wrapped result if available
        summary = ""
        if isinstance(tool_result, str):
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict):
                    summary = parsed.get("summary", "")
                    instruction = parsed.get("instruction", "")
                    if instruction:
                        summary = f"{summary}\n\n{instruction}" if summary else instruction
            except json.JSONDecodeError:
                pass

        # Build message
        messages = {
            TerminationReason.TERMINATION_ACTION_CALLED: (
                f"{summary or 'Task completed successfully.'}\n\n"
                f"ℹ️ Execution terminated automatically to prevent redundant actions."
            ),
            TerminationReason.USER_CONFIRMATION_REQUIRED: (
                f"{summary or tool_result}\n\n"
                f"⏸️ Paused for user confirmation. Reply '继续执行' to proceed."
            ),
            TerminationReason.INFINITE_LOOP_DETECTED: (
                f"⚠️ {summary or 'Detected repetitive tool calling pattern.'}\n\n"
                f"ℹ️ Execution stopped to prevent infinite loop. "
                f"Please provide clearer instructions or try a different approach."
            ),
            TerminationReason.TOOL_CALL_LIMIT_REACHED: (
                f"⚠️ {summary or 'Reached tool call limit.'}\n\n"
                f"ℹ️ Reply '继续执行' to continue with a new session."
            ),
        }

        return messages.get(reason, str(tool_result))
