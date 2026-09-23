import sys
import unittest
from capture.screen import ScreenCaptureData
from computer.actions import ActionPlan, ActionStep, ActionType, ActionTarget
from safety.validators import validate_coordinates, validate_active_window, clamp_coordinates
from safety.confirmation import ConfirmationManager
from safety.emergency_stop import EmergencyStopManager
from safety.manager import SafetyManager
from agent.context import AgentContext
from ai.action_planner import ActionPlanner


class TestV2Core(unittest.TestCase):

    def setUp(self):
        # Sample screen data for a 1920x1080 screen with a window at (100, 100, 800, 600)
        self.screen_data = ScreenCaptureData(
            image_b64="fake_b64",
            window_title="Google Chrome - Dashboard",
            bbox={"left": 100, "top": 100, "width": 800, "height": 600},
            original_size=(800, 600),
            scaled_size=(800, 600)
        )

    def test_coordinate_mapping(self):
        # (500, 500) normalized should map to center of bbox: 100 + 400 = 500, 100 + 300 = 400
        abs_x, abs_y = self.screen_data.map_normalized_coords(500, 500)
        self.assertEqual(abs_x, 500)
        self.assertEqual(abs_y, 400)

        # (0, 0) normalized should map to top-left of bbox: (100, 100)
        abs_x, abs_y = self.screen_data.map_normalized_coords(0, 0)
        self.assertEqual(abs_x, 100)
        self.assertEqual(abs_y, 100)

        # (1000, 1000) normalized should map to bottom-right of bbox: (900, 700)
        abs_x, abs_y = self.screen_data.map_normalized_coords(1000, 1000)
        self.assertEqual(abs_x, 900)
        self.assertEqual(abs_y, 700)

        # Bounding box center [xmin, ymin, xmax, ymax] -> [400, 200, 600, 400]
        # Center is (500 norm_x, 300 norm_y) -> abs_x = 100 + 0.5*800 = 500, abs_y = 100 + 0.3*600 = 280
        abs_x, abs_y = self.screen_data.map_box_center([400, 200, 600, 400])
        self.assertEqual(abs_x, 500)
        self.assertEqual(abs_y, 280)

    def test_vision_isotropic_coordinate_mapping(self):
        # 1366x768 Full screen data
        screen_1366 = ScreenCaptureData(
            image_b64="fake_b64",
            window_title="Full Screen",
            bbox={"left": 0, "top": 0, "width": 1366, "height": 768},
            original_size=(1366, 768),
            scaled_size=(1366, 768)
        )

        # Google Search Bar: model emits point (490, 300)
        # Isotropic: both X and Y map via longest_dim = 1366
        abs_x, abs_y = screen_1366.map_normalized_coords(490, 300, mode="vision")
        # abs_x = int(0.490 * 1366) = 669, abs_y = int(0.300 * 1366) = 409
        self.assertEqual(abs_x, 669)
        self.assertEqual(abs_y, 409)

        # GitHub shortcut icon: model emits point (252, 363)
        abs_x, abs_y = screen_1366.map_normalized_coords(252, 363, mode="vision")
        # abs_x = int(0.252 * 1366) = 344, abs_y = int(0.363 * 1366) = 495
        self.assertEqual(abs_x, 344)
        self.assertEqual(abs_y, 495)

        # Box center for search bar: [230, 280, 770, 320]
        # cx = 500, cy = 300 -> abs_x = int(0.500 * 1366) = 683, abs_y = int(0.300 * 1366) = 409
        abs_x, abs_y = screen_1366.map_box_center([230, 280, 770, 320], mode="vision")
        self.assertEqual(abs_x, 683)
        self.assertEqual(abs_y, 409)

        # Taskbar Chrome icon: model emits point (126, 555) - isotropic Y for bottom of screen
        # 555/1000 * 1366 = 758 -> clamped to 768
        abs_x, abs_y = screen_1366.map_normalized_coords(126, 555, mode="vision")
        self.assertEqual(abs_x, 172)
        self.assertEqual(abs_y, 758)

        # Taskbar File Explorer icon: model emits point (541, 556)
        abs_x, abs_y = screen_1366.map_normalized_coords(541, 556, mode="vision")
        self.assertEqual(abs_x, 739)
        self.assertEqual(abs_y, 759)

    def test_safety_coordinate_validation(self):
        # Valid coordinate
        self.assertTrue(validate_coordinates(500, 400, 1920, 1080))
        # Negative coordinate
        self.assertFalse(validate_coordinates(-10, 400, 1920, 1080))
        # Out of screen bounds
        self.assertFalse(validate_coordinates(2000, 500, 1920, 1080))
        self.assertFalse(validate_coordinates(500, 1200, 1920, 1080))

        # Clamp boundary coordinates
        cx, cy = clamp_coordinates(172, 768, 1366, 768)
        self.assertEqual((cx, cy), (172, 767))
        self.assertTrue(validate_coordinates(cx, cy, 1366, 768))

        cx, cy = clamp_coordinates(1366, 500, 1366, 768)
        self.assertEqual((cx, cy), (1365, 500))
        self.assertTrue(validate_coordinates(cx, cy, 1366, 768))

    def test_safety_window_validation(self):
        # Same window
        self.assertTrue(validate_active_window("Google Chrome - Dashboard", "Google Chrome - Dashboard"))
        # Partial match
        self.assertTrue(validate_active_window("Google Chrome", "Google Chrome - Settings"))
        # Completely different window
        self.assertFalse(validate_active_window("Google Chrome", "Calculator"))
        # Empty title allows fallback
        self.assertTrue(validate_active_window("", "Google Chrome"))

    def test_sensitive_action_confirmation(self):
        cm = ConfirmationManager()
        
        # Safe step
        safe_step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=100, abs_y=100, description="Read more link")
        )
        self.assertFalse(cm.is_action_sensitive(safe_step))

        # Sensitive submit step
        submit_step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=100, abs_y=100, description="Submit Payment Button")
        )
        self.assertTrue(cm.is_action_sensitive(submit_step))

        # Sensitive delete step
        del_step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=100, abs_y=100, description="Delete Account")
        )
        self.assertTrue(cm.is_action_sensitive(del_step))

        # Sensitive text typing (password)
        type_step = ActionStep(
            action=ActionType.TYPE,
            text="SecretPassword123"
        )
        self.assertTrue(cm.is_action_sensitive(type_step))

    def test_confirmation_response_parsing(self):
        cm = ConfirmationManager()

        # Affirmative responses
        self.assertTrue(cm.parse_confirmation_response("yes please"))
        self.assertTrue(cm.parse_confirmation_response("confirm and proceed"))
        self.assertTrue(cm.parse_confirmation_response("go ahead"))
        self.assertTrue(cm.parse_confirmation_response("do it"))
        self.assertTrue(cm.parse_confirmation_response("sure"))

        # Negative responses
        self.assertFalse(cm.parse_confirmation_response("no don't"))
        self.assertFalse(cm.parse_confirmation_response("cancel that"))
        self.assertFalse(cm.parse_confirmation_response("stop"))
        self.assertFalse(cm.parse_confirmation_response("nevermind"))

        # Neutral / Ambiguous
        self.assertIsNone(cm.parse_confirmation_response("what time is it?"))

    def test_emergency_stop(self):
        esm = EmergencyStopManager()
        self.assertFalse(esm.is_stop_requested())
        esm.request_stop()
        self.assertTrue(esm.is_stop_requested())
        esm.reset()
        self.assertFalse(esm.is_stop_requested())

    def test_safety_loop_detection(self):
        sm = SafetyManager()
        test_hash = 123456789

        # Recording identical hash up to threshold
        self.assertFalse(sm.record_screen_hash(test_hash))
        self.assertFalse(sm.record_screen_hash(test_hash))
        # 3rd identical state triggers loop abort
        self.assertTrue(sm.record_screen_hash(test_hash))

    def test_agent_context_pronoun_resolution(self):
        ctx = AgentContext()

        # Record action on a button
        step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=450, abs_y=300, description="Blue Submit Button")
        )
        ctx.record_action(step, "Chrome")

        # "Click it again" should resolve to "Blue Submit Button"
        target = ctx.resolve_pronoun_target("click it again")
        self.assertIsNotNone(target)
        self.assertEqual(target.description, "Blue Submit Button")
        self.assertEqual(target.abs_x, 450)

    def test_action_planner_parsing(self):
        planner = ActionPlanner.__new__(ActionPlanner)  # instantiate without calling __init__
        
        json_sample = """```json
        {
            "type": "action",
            "thought": "User wants to click login",
            "actions": [
                {
                    "action": "click",
                    "target": {
                        "point": {"x": 300, "y": 200},
                        "box_2d": [200, 100, 400, 300],
                        "description": "Login button"
                    }
                }
            ],
            "requires_confirmation": false
        }
        ```"""

        plan = planner._parse_and_map_plan(json_sample, self.screen_data)
        self.assertEqual(plan.type, "action")
        self.assertEqual(len(plan.actions), 1)
        step = plan.actions[0]
        self.assertEqual(step.action, ActionType.CLICK)
        self.assertIsNotNone(step.target.abs_x)
        self.assertIsNotNone(step.target.abs_y)
        self.assertEqual(step.target.description, "Login button")


if __name__ == "__main__":
    unittest.main()
