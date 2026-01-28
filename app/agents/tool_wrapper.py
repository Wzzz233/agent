"""
Tool Layer - Dual View Wrapper for MCP Tool Results

Wraps MCP tool returns to provide:
1. Machine-readable status/error information
2. Human-readable natural language summaries
3. System instructions for the model
"""

from typing import Any, Dict, Optional
from enum import Enum
import json


class ToolStatus(Enum):
    """Standardized tool execution status"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    ERROR = "error"


class ToolResult:
    """Structured wrapper for tool results"""

    def __init__(
        self,
        status: ToolStatus,
        summary: str,
        data: Optional[Dict[str, Any]] = None,
        instruction: Optional[str] = None,
        raw_result: Optional[Any] = None
    ):
        self.status = status
        self.summary = summary
        self.data = data or {}
        self.instruction = instruction
        self.raw_result = raw_result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "status": self.status.value,
            "summary": self.summary
        }

        if self.data:
            result["data"] = self.data

        if self.instruction:
            result["instruction"] = self.instruction

        if self.raw_result is not None:
            result["raw_result"] = self.raw_result

        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_user_message(self) -> str:
        """
        Generate user-facing message (natural language only).
        This prevents JSON leakage.
        """
        parts = [self.summary]

        if self.instruction:
            parts.append(f"\n\n{self.instruction}")

        return "\n".join(parts)

    def to_model_message(self) -> str:
        """
        Generate model-facing message with system instructions.
        This can include directives for the model.
        """
        parts = [self.summary]

        if self.instruction:
            parts.append(f"\n\n{self.instruction}")

        return "\n".join(parts)


def wrap_tool_result(
    tool_name: str,
    raw_result: Any,
    context: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """
    Wrap a raw tool result into structured format.

    Args:
        tool_name: Name of the tool that was called
        raw_result: Raw result from MCP tool
        context: Optional context (arguments, design_uri, etc.)

    Returns:
        ToolResult with structured fields
    """
    # Try to parse if it's already a JSON string
    if isinstance(raw_result, str):
        try:
            parsed = json.loads(raw_result)
            if isinstance(parsed, dict):
                raw_result = parsed
        except json.JSONDecodeError:
            pass

    # Special handling for specific tools
    if tool_name == "add_components_from_plan":
        return _wrap_add_components_result(raw_result, context)

    elif tool_name == "execute_circuit_plan":
        return _wrap_execute_plan_result(raw_result, context)

    elif tool_name == "plan_circuit":
        return _wrap_plan_circuit_result(raw_result, context)

    elif tool_name == "add_component":
        return _wrap_add_component_result(raw_result, context)

    elif tool_name == "check_cell_exists":
        return _wrap_check_cell_exists_result(raw_result, context)

    elif tool_name == "get_project_structure":
        return _wrap_get_project_structure_result(raw_result, context)

    elif tool_name == "get_current_design":
        return _wrap_get_current_design_result(raw_result, context)

    # Default wrapping
    return _wrap_generic_result(raw_result, context)


def _wrap_add_components_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Wrap add_components_from_plan result"""
    if isinstance(raw_result, dict):
        success = raw_result.get("success", True)
        status = ToolStatus.SUCCESS if success else ToolStatus.FAILED

        # Extract summary
        if success:
            design_uri = raw_result.get("design_uri", "")
            component_count = len(context.get("components", [])) if context else 0
            summary = f"✅ Successfully added {component_count} components to design."

            instruction = (
                f"Design saved to: {design_uri}\n\n"
                f"CRITICAL: Task completed. All components have been added. "
                f"DO NOT call any more tools unless the user provides new instructions."
            )

            return ToolResult(
                status=status,
                summary=summary,
                data={"design_uri": design_uri, "component_count": component_count},
                instruction=instruction,
                raw_result=raw_result
            )
        else:
            error = raw_result.get("error", "Unknown error")
            summary = f"❌ Failed to add components: {error}"
            return ToolResult(
                status=status,
                summary=summary,
                raw_result=raw_result
            )

    # Fallback for non-dict results
    return ToolResult(
        status=ToolStatus.SUCCESS,
        summary="Components added to design.",
        raw_result=raw_result
    )


def _wrap_execute_plan_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Wrap execute_circuit_plan result"""
    if isinstance(raw_result, dict):
        success = raw_result.get("success", True)
        status = ToolStatus.SUCCESS if success else ToolStatus.FAILED

        if success:
            design_uri = raw_result.get("design_uri", "")
            summary = f"✅ Schematic created successfully."

            instruction = (
                f"Design URI: {design_uri}\n\n"
                f"⏸️ STOP and wait for user to open the design in ADS. "
                f"DO NOT call add_components_from_plan until user confirms they have opened the design.\n\n"
                f"Next step: When user replies '已打开' or 'continue', call add_components_from_plan to add components."
            )

            return ToolResult(
                status=status,
                summary=summary,
                data={"design_uri": design_uri},
                instruction=instruction,
                raw_result=raw_result
            )
        else:
            error = raw_result.get("error", "Unknown error")
            summary = f"❌ Failed to create schematic: {error}"
            return ToolResult(
                status=status,
                summary=summary,
                raw_result=raw_result
            )

    return ToolResult(
        status=ToolStatus.SUCCESS,
        summary="Schematic created.",
        raw_result=raw_result
    )


def _wrap_plan_circuit_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Wrap plan_circuit result"""
    # Extract plan_id
    plan_id = None
    if isinstance(raw_result, str) and raw_result.startswith("PLAN_ID:"):
        plan_id = raw_result.split("\n")[0].split(": ")[1]
    elif isinstance(raw_result, dict):
        plan_id = raw_result.get("plan_id")

    summary = f"✅ Circuit plan generated."

    instruction = (
        f"Plan ID: {plan_id}\n\n"
        f"⏸️ PAUSED: Awaiting user confirmation to execute this plan.\n\n"
        f"DO NOT call execute_circuit_plan or any other tools until user confirms.\n"
        f"Wait for user to reply with '确认' or 'confirm' before proceeding."
    )

    return ToolResult(
        status=ToolStatus.REQUIRES_CONFIRMATION,
        summary=summary,
        data={"plan_id": plan_id},
        instruction=instruction,
        raw_result=raw_result
    )


def _wrap_add_component_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Wrap add_component result"""
    if isinstance(raw_result, dict):
        success = raw_result.get("status") == "success"
        status = ToolStatus.SUCCESS if success else ToolStatus.FAILED

        if success:
            instance_name = context.get("instance_name", "") if context else ""
            component_type = context.get("component_type", "") if context else ""
            summary = f"✅ Added component {component_type} ({instance_name})."

            return ToolResult(
                status=status,
                summary=summary,
                raw_result=raw_result
            )
        else:
            error = raw_result.get("message", "Unknown error")
            summary = f"❌ Failed to add component: {error}"
            return ToolResult(
                status=status,
                summary=summary,
                raw_result=raw_result
            )

    return ToolResult(
        status=ToolStatus.SUCCESS,
        summary="Component added.",
        raw_result=raw_result
    )


def _wrap_check_cell_exists_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Wrap check_cell_exists result"""
    if isinstance(raw_result, dict):
        # Check for nested error in data field
        if 'data' in raw_result and isinstance(raw_result['data'], dict):
            data = raw_result['data']
            if data.get("status") == "error":
                error_msg = data.get('error', 'Unknown error')
                library_name = context.get("arguments", {}).get("library_name", "unknown") if context else "unknown"

                # Parse library not open error
                if "library" in error_msg.lower() and "not open" in error_msg.lower():
                    summary = f"❌ Library '{library_name}' is not open or does not exist."
                    instruction = (
                        f"⚠️ The library '{library_name}' is not available in the current ADS project.\n\n"
                        f"IMPORTANT: Before calling any cell-related tools again, you MUST:\n"
                        f"1. Call 'get_project_structure' to see all available libraries and cells\n"
                        f"2. Choose an existing library from the project structure\n"
                        f"3. OR use 'create_schematic' to create a new design in the default workspace\n\n"
                        f"Do NOT repeatedly call check_cell_exists with the same non-existent library."
                    )
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        summary=summary,
                        instruction=instruction,
                        raw_result=raw_result
                    )

                # Other errors
                summary = f"❌ Error checking cell: {error_msg}"
                return ToolResult(
                    status=ToolStatus.ERROR,
                    summary=summary,
                    raw_result=raw_result
                )

        # Check for cell exists result
        if raw_result.get("status") == "success":
            exists = raw_result.get("data", {}).get("exists", False)
            cell_name = context.get("arguments", {}).get("cell_name", "") if context else ""
            library_name = context.get("arguments", {}).get("library_name", "") if context else ""

            if exists:
                summary = f"✅ Cell '{cell_name}' exists in library '{library_name}'."
            else:
                summary = f"ℹ️ Cell '{cell_name}' does not exist in library '{library_name}'."
                instruction = (
                    f"Cell '{cell_name}' not found in '{library_name}'.\n\n"
                    f"Next steps:\n"
                    f"1. Call 'list_cells' to see all available cells in this library\n"
                    f"2. OR call 'create_schematic' to create a new cell"
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                summary=summary,
                instruction=instruction if not exists else None,
                raw_result=raw_result
            )

    # Fallback
    return ToolResult(
        status=ToolStatus.SUCCESS,
        summary="Cell existence check completed.",
        raw_result=raw_result
    )


def _wrap_get_project_structure_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Wrap get_project_structure result"""
    if isinstance(raw_result, dict):
        # Check for error
        if 'data' in raw_result and isinstance(raw_result['data'], dict):
            data = raw_result['data']
            if data.get("status") == "error":
                error_msg = data.get('error', 'Unknown error')
                return ToolResult(
                    status=ToolStatus.ERROR,
                    summary=f"❌ Failed to get project structure: {error_msg}",
                    raw_result=raw_result
                )

        # Successfully retrieved project structure
        if raw_result.get("status") == "success":
            libraries = raw_result.get("data", {}).get("libraries", [])
            lib_count = len(libraries) if isinstance(libraries, list) else 0

            summary = f"✅ Retrieved project structure with {lib_count} libraries."

            if lib_count > 0:
                # List available libraries
                lib_names = [lib.get("name", "unknown") for lib in libraries] if isinstance(libraries, list) else []
                lib_list = ", ".join(lib_names[:5])  # Show first 5
                if len(lib_names) > 5:
                    lib_list += f" ... and {len(lib_names) - 5} more"

                instruction = (
                    f"Available libraries: {lib_list}\n\n"
                    f"You can now:\n"
                    f"1. Use 'list_cells' with a library name to see cells\n"
                    f"2. Use 'check_cell_exists' to verify specific cells\n"
                    f"3. Use 'create_schematic' to create new designs"
                )
            else:
                instruction = "No libraries found. You may need to create a new schematic."

            return ToolResult(
                status=ToolStatus.SUCCESS,
                summary=summary,
                instruction=instruction,
                raw_result=raw_result
            )

    return ToolResult(
        status=ToolStatus.SUCCESS,
        summary="Project structure retrieved.",
        raw_result=raw_result
    )


def _wrap_get_current_design_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Wrap get_current_design result - CRITICAL for workflow decision"""
    if isinstance(raw_result, dict):
        # Check for error
        if 'data' in raw_result and isinstance(raw_result['data'], dict):
            data = raw_result['data']
            if data.get("status") == "error":
                error_msg = data.get('error', 'Unknown error')
                return ToolResult(
                    status=ToolStatus.ERROR,
                    summary=f"❌ Failed to get current design: {error_msg}",
                    raw_result=raw_result
                )

        # Check if design is open
        design_uri = raw_result.get("data", {}).get("design_uri")
        cell_name = raw_result.get("data", {}).get("cell_name")
        library_name = raw_result.get("data", {}).get("library_name")

        if design_uri and design_uri != "None":
            # SCENARIO 2: User has a design open
            summary = f"✅ User has a schematic open: {design_uri}"
            instruction = (
                f"WORKFLOW DECISION: User already has '{library_name}:{cell_name}' open in ADS.\n\n"
                f"IMPORTANT:\n"
                f"✓ DO NOT call plan_circuit or execute_circuit_plan\n"
                f"✓ DO NOT create a new cell\n"
                f"✓ Design the circuit directly using the user's open schematic\n"
                f"✓ Ask user for design requirements (circuit type, parameters, etc.)\n"
                f"✓ Then call add_component or other design tools directly\n\n"
                f"This is SCENARIO 2: User has existing schematic - design directly."
            )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                summary=summary,
                instruction=instruction,
                data={"scenario": "existing_design", "design_uri": design_uri},
                raw_result=raw_result
            )
        else:
            # SCENARIO 1: No design is open
            summary = "ℹ️ No schematic is currently open in ADS."
            instruction = (
                f"WORKFLOW DECISION: No design is open in ADS.\n\n"
                f"IMPORTANT - Ask user to clarify:\n"
                f"1. Do you want to CREATE a new cell/schematic?\n"
                f"   → If yes: Call plan_circuit to generate design plan\n"
                f"   → Then call execute_circuit_plan to create schematic\n"
                f"   → Wait for user to open it in ADS\n"
                f"   → Then add components\n\n"
                f"2. Do you have an EXISTING cell/schematic you want to use?\n"
                f"   → If yes: Ask user for library and cell names\n"
                f"   → Call get_project_structure to see available cells\n"
                f"   → User should open the schematic in ADS first\n"
                f"   → Then design and add components\n\n"
                f"This is SCENARIO 1: Need to create or open a schematic first."
            )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                summary=summary,
                instruction=instruction,
                data={"scenario": "no_design"},
                raw_result=raw_result
            )

    # Fallback
    return ToolResult(
        status=ToolStatus.SUCCESS,
        summary="Checked current design status.",
        raw_result=raw_result
    )


def _wrap_generic_result(
    raw_result: Any,
    context: Optional[Dict[str, Any]]
) -> ToolResult:
    """Default wrapper for generic tools"""
    status = ToolStatus.SUCCESS
    summary = "Tool executed successfully."
    instruction = None

    if isinstance(raw_result, dict):
        # Check for errors at multiple levels
        error_msg = None

        # Level 1: Check top-level status
        if raw_result.get("status") == "error":
            error_msg = raw_result.get('message') or raw_result.get('error', 'Unknown error')
            status = ToolStatus.ERROR
        elif raw_result.get("success") == False:
            error_msg = raw_result.get('error', 'Unknown error')
            status = ToolStatus.FAILED

        # Level 2: Check nested data field
        elif 'data' in raw_result and isinstance(raw_result['data'], dict):
            data = raw_result['data']
            if data.get("status") == "error":
                error_msg = data.get('error', data.get('message', 'Unknown error'))
                status = ToolStatus.ERROR
            elif data.get("error"):
                error_msg = data.get('error')
                status = ToolStatus.ERROR

        # Build summary and instruction based on error
        if error_msg:
            # Parse common ADS errors and provide helpful guidance
            if "library" in error_msg.lower() and "not open" in error_msg.lower():
                library_name = context.get("arguments", {}).get("library_name", "unknown") if context else "unknown"
                summary = f"❌ Library '{library_name}' is not open in ADS."
                instruction = (
                    f"⚠️ ISSUE: The specified library is not available.\n\n"
                    f"Next steps:\n"
                    f"1. Call 'get_project_structure' to see available libraries\n"
                    f"2. Use an open library from the project structure\n"
                    f"3. OR call 'create_schematic' to create a new design in the default workspace"
                )
            elif "cell" in error_msg.lower() and "not found" in error_msg.lower():
                cell_name = context.get("arguments", {}).get("cell_name", "unknown") if context else "unknown"
                summary = f"❌ Cell '{cell_name}' does not exist."
                instruction = (
                    f"⚠️ ISSUE: The specified cell was not found.\n\n"
                    f"Next steps:\n"
                    f"1. Call 'get_project_structure' to see available cells\n"
                    f"2. Call 'list_cells' with a library name to see all cells in a library\n"
                    f"3. OR call 'create_schematic' to create a new cell"
                )
            else:
                summary = f"❌ Error: {error_msg}"
                instruction = "Please review the error and try a different approach."

        elif raw_result.get("status") == "success" and 'data' in raw_result:
            # Successful result with data
            data = raw_result.get('data', {})
            if isinstance(data, dict):
                # Extract meaningful info from success data
                if 'uri' in data:
                    summary = f"✅ Operation completed. URI: {data['uri']}"
                elif 'design_uri' in data:
                    summary = f"✅ Design created: {data['design_uri']}"
                else:
                    summary = "✅ Operation completed successfully."
            else:
                summary = "✅ Operation completed successfully."

    elif isinstance(raw_result, str):
        if "error" in raw_result.lower():
            status = ToolStatus.ERROR
            # Check for common error patterns
            if "library" in raw_result.lower() and "not open" in raw_result.lower():
                summary = "❌ Library is not open in ADS."
                instruction = "Call 'get_project_structure' to see available libraries."
            elif "cell" in raw_result.lower() and "not found" in raw_result.lower():
                summary = "❌ Cell does not exist."
                instruction = "Call 'list_cells' to see available cells."
            else:
                summary = raw_result
        else:
            summary = raw_result

    return ToolResult(
        status=status,
        summary=summary,
        instruction=instruction,
        raw_result=raw_result
    )
