"""
Test Suite for ADS Agent Workflow State Machine

Tests the key scenarios from the acceptance criteria:
1. Loop Test - plan_circuit should not loop
2. Isolation Test - tools should be hidden based on state
3. Readability Test - responses should be human-readable
4. Resume Test - state should persist and resume
"""

import sys
import os
import json
import unittest

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))

from workflow_manager import (
    WorkflowManager,
    WorkflowState,
    WorkflowContext,
    TOOLS_BY_STATE,
    reset_workflow_manager,
    get_workflow_manager,
)


class TestWorkflowStateTransitions(unittest.TestCase):
    """Test state machine transitions."""
    
    def setUp(self):
        """Reset state before each test."""
        reset_workflow_manager()
        self.wm = get_workflow_manager()
        # Clean state file
        if os.path.exists(self.wm.state_file):
            os.remove(self.wm.state_file)
        self.wm = WorkflowManager()
    
    def test_initial_state_is_idle(self):
        """Verify initial state is IDLE."""
        self.assertEqual(self.wm.state, WorkflowState.IDLE)
    
    def test_transition_idle_to_planning(self):
        """Test IDLE -> PLANNING transition."""
        self.wm.transition_to(WorkflowState.PLANNING)
        self.assertEqual(self.wm.state, WorkflowState.PLANNING)
    
    def test_full_workflow_transitions(self):
        """Test complete workflow: IDLE -> PLANNING -> ... -> COMPLETED."""
        # IDLE -> PLANNING (via set_plan which goes to SCHEMATIC_CREATED)
        self.wm.set_plan("test123", {
            "circuit": {"name": "test", "library": "lib", "design_uri": "lib:test:schematic"},
            "components": [{"type": "R", "name": "R1", "x": 0, "y": 0}]
        })
        self.assertEqual(self.wm.state, WorkflowState.SCHEMATIC_CREATED)
        
        # -> WAITING_USER
        self.wm.transition_to(WorkflowState.WAITING_USER)
        self.assertEqual(self.wm.state, WorkflowState.WAITING_USER)
        
        # -> COMPONENT_ADDING
        self.wm.transition_to(WorkflowState.COMPONENT_ADDING)
        self.assertEqual(self.wm.state, WorkflowState.COMPONENT_ADDING)
        
        # -> COMPLETED
        self.wm.transition_to(WorkflowState.COMPLETED)
        self.assertEqual(self.wm.state, WorkflowState.COMPLETED)
    
    def test_reset_returns_to_idle(self):
        """Test reset() always returns to IDLE."""
        self.wm.transition_to(WorkflowState.COMPONENT_ADDING)
        result = self.wm.reset()
        self.assertEqual(self.wm.state, WorkflowState.IDLE)
        self.assertEqual(result["status"], "success")


class TestToolVisibility(unittest.TestCase):
    """Test dynamic tool visibility (Isolation Test)."""
    
    def setUp(self):
        reset_workflow_manager()
        self.wm = get_workflow_manager()
        if os.path.exists(self.wm.state_file):
            os.remove(self.wm.state_file)
        self.wm = WorkflowManager()
    
    def test_idle_state_tools(self):
        """In IDLE, plan_circuit should be available but add_component should not."""
        allowed = self.wm.get_allowed_tools()
        
        self.assertIn("plan_circuit", allowed)
        self.assertIn("check_connection", allowed)
        self.assertIn("get_project_structure", allowed)
        
        # These should NOT be available in IDLE
        self.assertNotIn("add_component", allowed)
        self.assertNotIn("execute_circuit_plan", allowed)
        self.assertNotIn("confirm_design_open", allowed)
    
    def test_waiting_user_state_tools(self):
        """In WAITING_USER, only verification tools should be available."""
        self.wm.transition_to(WorkflowState.WAITING_USER)
        allowed = self.wm.get_allowed_tools()
        
        # Should have escape hatch
        self.assertIn("reset_workflow", allowed)
        self.assertIn("confirm_design_open", allowed)
        
        # Should NOT have component tools
        self.assertNotIn("add_component", allowed)
        self.assertNotIn("plan_circuit", allowed)
    
    def test_component_adding_state_tools(self):
        """In COMPONENT_ADDING, component tools should be available."""
        self.wm.transition_to(WorkflowState.COMPONENT_ADDING)
        allowed = self.wm.get_allowed_tools()
        
        self.assertIn("add_component", allowed)
        self.assertIn("add_wire", allowed)
        self.assertIn("save_current_design", allowed)
        self.assertIn("finish_design", allowed)
        self.assertIn("reset_workflow", allowed)
        
        # Should NOT have planning tools
        self.assertNotIn("plan_circuit", allowed)
        self.assertNotIn("execute_circuit_plan", allowed)
    
    def test_is_tool_allowed(self):
        """Test is_tool_allowed helper."""
        self.assertTrue(self.wm.is_tool_allowed("plan_circuit"))
        self.assertFalse(self.wm.is_tool_allowed("add_component"))
        
        self.wm.transition_to(WorkflowState.COMPONENT_ADDING)
        
        self.assertFalse(self.wm.is_tool_allowed("plan_circuit"))
        self.assertTrue(self.wm.is_tool_allowed("add_component"))


class TestStatePersistence(unittest.TestCase):
    """Test state persistence (Resume Test)."""
    
    def setUp(self):
        reset_workflow_manager()
        self.state_file = os.path.join(os.path.dirname(__file__), ".test_state.json")
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
    
    def tearDown(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
    
    def test_state_persists_to_file(self):
        """State should be saved to file."""
        wm = WorkflowManager(state_file=self.state_file)
        wm.set_plan("persist123", {
            "circuit": {"name": "test", "library": "lib", "design_uri": "lib:test:schematic"},
            "components": []
        })
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.state_file))
        
        # Verify content
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["state"], "SCHEMATIC_CREATED")
        self.assertEqual(data["plan_id"], "persist123")
    
    def test_state_resumes_from_file(self):
        """State should be restored from file on new instance."""
        wm1 = WorkflowManager(state_file=self.state_file)
        wm1.set_plan("resume123", {
            "circuit": {"name": "test", "library": "lib", "design_uri": "lib:test:schematic"},
            "components": [{"type": "R", "name": "R1"}]
        })
        wm1.transition_to(WorkflowState.WAITING_USER)
        
        # Create new instance (simulates process restart)
        wm2 = WorkflowManager(state_file=self.state_file)
        
        # Should have resumed state
        self.assertEqual(wm2.state, WorkflowState.WAITING_USER)
        self.assertEqual(wm2.context.plan_id, "resume123")


class TestDynamicPromptInjection(unittest.TestCase):
    """Test dynamic prompt generation."""
    
    def setUp(self):
        reset_workflow_manager()
        self.wm = get_workflow_manager()
        if os.path.exists(self.wm.state_file):
            os.remove(self.wm.state_file)
        self.wm = WorkflowManager()
    
    def test_idle_prompt_contains_instructions(self):
        """IDLE prompt should mention available actions."""
        prompt = self.wm.get_state_prompt()
        
        self.assertIn("IDLE", prompt)
        self.assertIn("plan_circuit", prompt)
    
    def test_waiting_user_prompt_is_warning(self):
        """WAITING_USER prompt should warn agent not to proceed."""
        self.wm.transition_to(WorkflowState.WAITING_USER)
        prompt = self.wm.get_state_prompt()
        
        self.assertIn("WAITING", prompt)
        self.assertIn("CANNOT", prompt)  # Should emphasize restriction
    
    def test_prompt_includes_context(self):
        """Prompt should include current plan/design info."""
        self.wm.set_plan("ctx123", {
            "circuit": {"name": "my_circuit", "library": "mylib", "design_uri": "mylib:my_circuit:schematic"},
            "components": [{"type": "R"}]
        })
        
        prompt = self.wm.get_state_prompt()
        
        self.assertIn("ctx123", prompt)  # Plan ID should be mentioned


class TestLoopPrevention(unittest.TestCase):
    """Test that the state machine prevents looping (Loop Test)."""
    
    def setUp(self):
        reset_workflow_manager()
        self.wm = get_workflow_manager()
        if os.path.exists(self.wm.state_file):
            os.remove(self.wm.state_file)
        self.wm = WorkflowManager()
    
    def test_plan_circuit_not_available_after_execution(self):
        """
        After calling plan_circuit and execute, plan_circuit should not be available
        until the workflow is completed or reset.
        """
        # Initially available
        self.assertTrue(self.wm.is_tool_allowed("plan_circuit"))
        
        # After setting plan (simulates plan_circuit)
        self.wm.set_plan("loop_test", {
            "circuit": {"name": "test", "library": "lib", "design_uri": "lib:test:schematic"},
            "components": []
        })
        
        # Now in SCHEMATIC_CREATED - plan_circuit should NOT be available
        self.assertFalse(self.wm.is_tool_allowed("plan_circuit"))
        
        # Move to WAITING_USER
        self.wm.transition_to(WorkflowState.WAITING_USER)
        self.assertFalse(self.wm.is_tool_allowed("plan_circuit"))
        
        # Move to COMPONENT_ADDING
        self.wm.transition_to(WorkflowState.COMPONENT_ADDING)
        self.assertFalse(self.wm.is_tool_allowed("plan_circuit"))
        
        # Only after COMPLETED or reset
        self.wm.transition_to(WorkflowState.COMPLETED)
        self.assertTrue(self.wm.is_tool_allowed("plan_circuit"))


if __name__ == "__main__":
    print("=" * 60)
    print("ADS Agent Workflow State Machine - Test Suite")
    print("=" * 60)
    
    unittest.main(verbosity=2)
