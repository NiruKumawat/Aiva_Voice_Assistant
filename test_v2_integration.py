import unittest
from unittest.mock import MagicMock, patch
from capture.screen import ScreenCaptureData
from computer.actions import ActionPlan, ActionStep, ActionType, ActionTarget
from agent.loop import AgentLoop


class TestV2Integration(unittest.TestCase):

    def setUp(self):
        self.mock_screen = ScreenCaptureData(
            image_b64="test_img_b64",
            window_title="Test Application - Window",
            bbox={"left": 100, "top": 100, "width": 800, "height": 600},
            original_size=(800, 600),
            scaled_size=(800, 600)
        )

    @patch("agent.loop.capture_screen_detailed")
    def test_informational_query_no_actions(self, mock_capture):
        mock_capture.return_value = self.mock_screen
        agent = AgentLoop()

        # Mock the planner to return a pure informational answer
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="answer",
            thought="Informational query about screen contents",
            answer="You have Test Application open."
        ))

        # Mock executor to verify it is NEVER called
        agent.executor.execute_step = MagicMock()

        result = agent.run_cycle("What is open right now?")

        self.assertEqual(result, "You have Test Application open.")
        agent.executor.execute_step.assert_not_called()
        self.assertIsNone(agent.pending_confirmation)

    @patch("agent.loop.ENABLE_ACTION_VERIFICATION", True)
    @patch("agent.loop.capture_screen_detailed")
    def test_safe_action_execution_and_verification(self, mock_capture):
        mock_capture.return_value = self.mock_screen
        agent = AgentLoop()

        # Step to click a safe button
        step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=300, abs_y=250, description="Next Page Button")
        )

        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            thought="Click next page button",
            actions=[step],
            requires_confirmation=False
        ))

        agent.executor.execute_step = MagicMock()
        agent.verifier.verify = MagicMock(return_value=(True, "Page changed successfully."))

        result = agent.run_cycle("Click next page")

        self.assertEqual(result, "Page changed successfully.")
        agent.executor.execute_step.assert_called_once_with(step)
        agent.verifier.verify.assert_called_once()
        self.assertIsNone(agent.pending_confirmation)

    @patch("agent.loop.ENABLE_ACTION_VERIFICATION", False)
    @patch("agent.loop.capture_screen_detailed")
    def test_fast_execution_skips_verification(self, mock_capture):
        mock_capture.return_value = self.mock_screen
        agent = AgentLoop()

        step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=300, abs_y=250, description="Next Page Button")
        )

        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            thought="Click next page button",
            answer="Clicked next page button.",
            actions=[step],
            requires_confirmation=False
        ))

        agent.executor.execute_step = MagicMock()
        agent.verifier.verify = MagicMock()

        result = agent.run_cycle("Click next page")

        self.assertEqual(result, "Clicked next page button.")
        agent.executor.execute_step.assert_called_once_with(step)
        # Verifier must NOT be called when verification is disabled (saving 20s)
        agent.verifier.verify.assert_not_called()

    @patch("agent.loop.ENABLE_ACTION_VERIFICATION", True)
    @patch("agent.loop.capture_screen_detailed")
    def test_sensitive_action_requires_confirmation_flow(self, mock_capture):
        mock_capture.return_value = self.mock_screen
        agent = AgentLoop()

        # Sensitive submit step
        step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=400, abs_y=500, description="Submit Payment")
        )

        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            thought="User wants to submit payment",
            actions=[step],
            requires_confirmation=True,
            confirmation_prompt="Are you sure you want to submit the payment?"
        ))

        agent.executor.execute_step = MagicMock()
        agent.verifier.verify = MagicMock(return_value=(True, "Payment submitted."))

        # 1. First cycle should NOT execute, but require confirmation
        prompt = agent.run_cycle("Submit payment now")
        self.assertEqual(prompt, "Are you sure you want to submit the payment?")
        agent.executor.execute_step.assert_not_called()
        self.assertIsNotNone(agent.pending_confirmation)

        # 2. User confirms -> executes confirmed plan
        result = agent.execute_confirmed_plan()
        self.assertEqual(result, "Payment submitted.")
        agent.executor.execute_step.assert_called_once_with(step)
        self.assertIsNone(agent.pending_confirmation)

    @patch("agent.loop.capture_screen_detailed")
    def test_sensitive_action_cancellation(self, mock_capture):
        mock_capture.return_value = self.mock_screen
        agent = AgentLoop()

        step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=400, abs_y=500, description="Delete Database")
        )

        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[step],
            requires_confirmation=True,
            confirmation_prompt="Do you really want to delete the database?"
        ))

        agent.executor.execute_step = MagicMock()

        prompt = agent.run_cycle("Delete the database")
        self.assertIsNotNone(agent.pending_confirmation)

        cancel_msg = agent.cancel_pending_confirmation()
        self.assertEqual(cancel_msg, "Action cancelled.")
        self.assertIsNone(agent.pending_confirmation)
        agent.executor.execute_step.assert_not_called()

    @patch("agent.loop.capture_screen_detailed")
    def test_emergency_stop_aborts_execution(self, mock_capture):
        mock_capture.return_value = self.mock_screen
        agent = AgentLoop()

        steps = [
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=200, abs_y=200, description="Step 1")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=250, abs_y=250, description="Step 2"))
        ]

        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=steps
        ))

        # Simulate emergency stop triggered during the first step execution
        executed_steps = []
        def mock_execute(step):
            executed_steps.append(step)
            agent.stop()  # Triggers emergency stop mid-sequence

        agent.executor.execute_step = MagicMock(side_effect=mock_execute)
        agent.verifier.verify = MagicMock(return_value=(True, "Step 1 done"))

        result = agent.run_cycle("Run multi-step action")
        self.assertIn("stopped", result.lower())
        # Step 1 ran, but Step 2 was blocked by emergency stop!
        self.assertEqual(len(executed_steps), 1)

    @patch("agent.loop.ENABLE_FAST_PATH", False)
    @patch("agent.loop.capture_screen_detailed")
    def test_multistep_reasoning_launch_and_type_success(self, mock_capture):
        """Verifies multi-step workflow handles app launch window transition without aborting."""
        mock_capture.return_value = self.mock_screen
        agent = AgentLoop()

        steps = [
            ActionStep(action=ActionType.LAUNCH, text="notepad", reason="Launch Notepad"),
            ActionStep(action=ActionType.WAIT, duration=0.1, reason="Wait for window"),
            ActionStep(action=ActionType.HOTKEY, keys=["ctrl", "n"], reason="New file"),
            ActionStep(action=ActionType.WAIT, duration=0.1, reason="Wait for tab"),
            ActionStep(action=ActionType.TYPE, text="def is_palindrome(s): return s == s[::-1]", reason="Write palindrome code")
        ]

        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            thought="Open Notepad and write palindrome code",
            answer="Opening Notepad, creating a new file, and writing palindrome code.",
            actions=steps
        ))

        executed_actions = []
        agent.executor.execute_step = MagicMock(side_effect=lambda s: executed_actions.append(s.action))

        result = agent.run_cycle("open notepad take new file and write palindrome code")
        self.assertIn("palindrome", result.lower())
        self.assertEqual(len(executed_actions), 5)
        self.assertEqual(executed_actions, [ActionType.LAUNCH, ActionType.WAIT, ActionType.HOTKEY, ActionType.WAIT, ActionType.TYPE])


if __name__ == "__main__":
    unittest.main()
