"""
End-to-end simulation test reproducing the exact scenario from terminal 7088:
1. Clarification with 3 items (including a PPT file).
2. User says: "Click on Downloads".
3. User says: "In the sidebar double click on downloads".
4. User says: "Close File Explorer".
"""
import unittest
from agent.context import AgentContext
from agent.fast_path import DirectActionFastPath
from computer.actions import ActionTarget, ActionType


class TestUserLogScenario(unittest.TestCase):

    def setUp(self):
        self.context = AgentContext()
        self.fast_path = DirectActionFastPath()

    def test_reproduce_and_verify_fix(self):
        # Step 1: Clarification was asked in terminal 7088
        target_final = ActionTarget(abs_x=402, abs_y=605, description="final folder")
        target_project = ActionTarget(abs_x=402, abs_y=570, description="project folder")
        target_ppt = ActionTarget(abs_x=450, abs_y=471, description="AI_Based_Child_Safety_Monitoring_System_PPT_OS file")

        options = [
            {"id": 1, "description": "final folder", "target": target_final},
            {"id": 2, "description": "project folder", "target": target_project},
            {"id": 3, "description": "AI_Based_Child_Safety_Monitoring_System_PPT_OS file", "target": target_ppt}
        ]

        self.context.set_pending_clarification(
            "Which item would you like me to click on? For example, a folder like 'final', 'project', or a file like 'AI_Based_Child_Safety_Monitoring_System_PPT_OS'.",
            options
        )
        self.assertTrue(self.context.has_pending_clarification())

        # Step 2: User says "Click on Downloads"
        # In the fixed code:
        # A) Fast path returns None (requires vision or visual grounding if "click" is spoken)
        fp_res = self.fast_path.match("Click on Downloads")
        self.assertIsNone(fp_res)

        # B) Context resolve_clarification is called
        # "Click on Downloads" contains "click" (an action verb) and does not match "final", "project", or "ppt".
        # It must NOT match Option 3! It must clear clarification!
        resolved = self.context.resolve_clarification("Click on Downloads")
        self.assertIsNone(resolved, "'Click on Downloads' must not resolve to any clarification option")
        self.assertFalse(self.context.has_pending_clarification(), "Pending clarification must be cleared")

        # Step 3: User says "In the sidebar double click on downloads"
        # Context has no pending clarification
        self.assertFalse(self.context.has_pending_clarification())

        # Step 4: User says "Close File Explorer"
        # Fast path must directly intercept this and produce Alt+F4 hotkey in <0.01s!
        plan = self.fast_path.match("Close File Explorer")
        self.assertIsNotNone(plan, "Fast-path must intercept 'Close File Explorer'")
        self.assertEqual(plan.actions[0].action, ActionType.HOTKEY)
        self.assertEqual(plan.actions[0].keys, ["alt", "f4"])

        # Even if context resolve_clarification was hypothetically called with "Close File Explorer":
        self.context.set_pending_clarification("stale question", options)
        resolved_close = self.context.resolve_clarification("Close File Explorer")
        self.assertIsNone(resolved_close, "'Close File Explorer' must NEVER match the PPT file!")
        self.assertFalse(self.context.has_pending_clarification())

    def test_fast_path_close_variations(self):
        variations = [
            "Close File Explorer",
            "close the file explorer",
            "close window",
            "close this window",
            "close the window",
            "close folder",
            "close this folder",
            "close this",
            "close it",
            "quit",
            "exit"
        ]
        for phrase in variations:
            plan = self.fast_path.match(phrase)
            self.assertIsNotNone(plan, f"Failed to match fast path for: {phrase}")
            self.assertEqual(plan.actions[0].action, ActionType.HOTKEY)
            self.assertEqual(plan.actions[0].keys, ["alt", "f4"])

    def test_fast_path_folder_openings(self):
        folders = [
            ("Open Downloads", "shell:Downloads"),
            ("open the downloads folder", "shell:Downloads"),
            ("Go to Downloads", "shell:Downloads"),
            ("Open Documents", "shell:Personal"),
            ("open documents folder", "shell:Personal"),
            ("Open Desktop", "shell:Desktop")
        ]
        for phrase, target in folders:
            plan = self.fast_path.match(phrase)
            self.assertIsNotNone(plan, f"Failed to match fast path for: {phrase}")
            self.assertEqual(plan.actions[0].action, ActionType.LAUNCH)
            self.assertEqual(plan.actions[0].text, target)


if __name__ == "__main__":
    unittest.main()
