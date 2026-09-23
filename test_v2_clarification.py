import unittest
from computer.actions import ActionPlan, ActionStep, ActionType, ActionTarget
from agent.context import AgentContext
from ai.action_planner import ActionPlanner
from capture.screen import ScreenCaptureData


class TestClarification(unittest.TestCase):

    def setUp(self):
        self.screen_data = ScreenCaptureData(
            image_b64="fake_b64",
            window_title="YouTube - Google Chrome",
            bbox={"left": 0, "top": 0, "width": 1366, "height": 768},
            original_size=(1366, 768),
            scaled_size=(1366, 768)
        )

    def test_parse_clarify_plan(self):
        data = {
            "type": "clarify",
            "thought": "Found two search bars on the screen.",
            "question": "I see two search bars: the YouTube search at the top, and the Windows Taskbar search at the bottom. Which one would you like me to click?",
            "options": [
                {
                    "id": 1,
                    "description": "YouTube search at the top",
                    "target": {
                        "point": {"x": 480, "y": 70},
                        "box_2d": [250, 50, 710, 90]
                    }
                },
                {
                    "id": 2,
                    "description": "Windows Taskbar search at the bottom",
                    "target": {
                        "point": {"x": 410, "y": 540},
                        "box_2d": [340, 530, 480, 555]
                    }
                }
            ]
        }

        plan = ActionPlan.from_dict(data)
        self.assertEqual(plan.type, "clarify")
        self.assertIn("two search bars", plan.question)
        self.assertEqual(len(plan.options), 2)
        self.assertIsInstance(plan.options[0]["target"], ActionTarget)
        self.assertEqual(plan.options[0]["target"].norm_x, 480)
        self.assertEqual(plan.options[0]["target"].norm_y, 70)

    def test_planner_maps_option_coordinates(self):
        planner = ActionPlanner.__new__(ActionPlanner)
        raw_json = """{
            "type": "clarify",
            "thought": "Two search bars found",
            "question": "Which search bar?",
            "options": [
                {
                    "id": 1,
                    "description": "YouTube search at the top",
                    "target": {"point": {"x": 480, "y": 70}}
                },
                {
                    "id": 2,
                    "description": "Windows Taskbar search at the bottom",
                    "target": {"point": {"x": 410, "y": 540}}
                }
            ]
        }"""

        plan = planner._parse_and_map_plan(raw_json, self.screen_data)
        self.assertEqual(plan.type, "clarify")
        opt1_target = plan.options[0]["target"]
        opt2_target = plan.options[1]["target"]

        # 480/1000 * 1366 = 655
        self.assertEqual(opt1_target.abs_x, 655)
        # 70/1000 * 1366 = 95 (isotropic)
        self.assertEqual(opt1_target.abs_y, 95)

        # 410/1000 * 1366 = 560
        self.assertEqual(opt2_target.abs_x, 560)
        # 540/1000 * 1366 = 737 (isotropic, clamped to 768)
        self.assertEqual(opt2_target.abs_y, 737)

    def test_context_resolve_by_keyword(self):
        ctx = AgentContext()
        target_yt = ActionTarget(abs_x=655, abs_y=95, description="YouTube search at the top")
        target_tb = ActionTarget(abs_x=560, abs_y=737, description="Windows Taskbar search at the bottom")

        options = [
            {"id": 1, "description": "YouTube search at the top", "target": target_yt},
            {"id": 2, "description": "Windows Taskbar search at the bottom", "target": target_tb}
        ]

        ctx.set_pending_clarification("Which search bar?", options)
        self.assertTrue(ctx.has_pending_clarification())

        # Match "YouTube"
        res = ctx.resolve_clarification("the YouTube one please")
        self.assertIsNotNone(res)
        self.assertEqual(res.description, "YouTube search at the top")
        self.assertFalse(ctx.has_pending_clarification())

        # Reset and match "Taskbar"
        ctx.set_pending_clarification("Which search bar?", options)
        res = ctx.resolve_clarification("click taskbar")
        self.assertIsNotNone(res)
        self.assertEqual(res.description, "Windows Taskbar search at the bottom")

    def test_context_resolve_by_ordinal(self):
        ctx = AgentContext()
        target_1 = ActionTarget(abs_x=100, abs_y=100, description="Option 1")
        target_2 = ActionTarget(abs_x=200, abs_y=200, description="Option 2")

        options = [
            {"id": 1, "description": "Option 1", "target": target_1},
            {"id": 2, "description": "Option 2", "target": target_2}
        ]

        # "First one"
        ctx.set_pending_clarification("Which one?", options)
        res = ctx.resolve_clarification("first one")
        self.assertEqual(res, target_1)

        # "Second"
        ctx.set_pending_clarification("Which one?", options)
        res = ctx.resolve_clarification("the second option")
        self.assertEqual(res, target_2)

    def test_context_cancellation(self):
        ctx = AgentContext()
        ctx.set_pending_clarification("Which one?", [{"id": 1, "description": "Test", "target": None}])
        self.assertTrue(ctx.has_pending_clarification())

        res = ctx.resolve_clarification("cancel that")
        self.assertIsNone(res)
        self.assertFalse(ctx.has_pending_clarification())

    def test_action_command_does_not_hijack_clarification(self):
        """Action commands like 'Close File Explorer' must never false-match options containing generic words like 'file'."""
        ctx = AgentContext()
        target_ppt = ActionTarget(abs_x=450, abs_y=471, description="AI_Safety_PPT file")
        options = [
            {"id": 1, "description": "final folder", "target": None},
            {"id": 2, "description": "project folder", "target": None},
            {"id": 3, "description": "AI_Safety_PPT file", "target": target_ppt}
        ]
        ctx.set_pending_clarification("Which item would you like me to click on?", options)

        # "Close File Explorer" contains the word "file", but it's an action command and "file" is a generic word.
        res = ctx.resolve_clarification("Close File Explorer")
        self.assertIsNone(res, "'Close File Explorer' should NOT match 'AI_Safety_PPT file'")
        self.assertFalse(ctx.has_pending_clarification(), "Clarification should be cleared on new action command")


if __name__ == "__main__":
    unittest.main()
