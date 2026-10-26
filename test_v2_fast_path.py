import unittest
import time
from unittest.mock import MagicMock, patch
from computer.actions import ActionType
from agent.fast_path import DirectActionFastPath
from agent.loop import AgentLoop


class TestDirectActionFastPath(unittest.TestCase):

    def setUp(self):
        self.fast_path = DirectActionFastPath()

    def test_conversational_scroll_up(self):
        plan = self.fast_path.match("Can you scroll up please?")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action, ActionType.SCROLL)
        self.assertEqual(plan.actions[0].direction, "up")
        self.assertEqual(plan.actions[0].amount, 500)
        self.assertIn("Scrolled up", plan.answer)

    def test_conversational_scroll_down_a_bit(self):
        plan = self.fast_path.match("Could you please scroll down a bit?")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action, ActionType.SCROLL)
        self.assertEqual(plan.actions[0].direction, "down")
        self.assertEqual(plan.actions[0].amount, 250)

    def test_conversational_roll_down(self):
        plan = self.fast_path.match("Hey assistant, can you roll down for me?")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].action, ActionType.SCROLL)
        self.assertEqual(plan.actions[0].direction, "down")

    def test_scroll_to_top_and_bottom(self):
        plan_top = self.fast_path.match("Scroll to the top of the page please")
        self.assertIsNotNone(plan_top)
        self.assertEqual(plan_top.actions[0].action, ActionType.SCROLL)
        self.assertEqual(plan_top.actions[0].direction, "up")
        self.assertEqual(plan_top.actions[0].amount, 5000)

        plan_bot = self.fast_path.match("Jump to the bottom")
        self.assertIsNotNone(plan_bot)
        self.assertEqual(plan_bot.actions[0].action, ActionType.SCROLL)
        self.assertEqual(plan_bot.actions[0].direction, "down")
        self.assertEqual(plan_bot.actions[0].amount, 5000)

    def test_conversational_enter_key(self):
        plan1 = self.fast_path.match("Please hit enter")
        self.assertIsNotNone(plan1)
        self.assertEqual(plan1.actions[0].action, ActionType.PRESS_KEY)
        self.assertEqual(plan1.actions[0].keys, ["enter"])

        plan2 = self.fast_path.match("Can you press the enter key for me?")
        self.assertIsNotNone(plan2)
        self.assertEqual(plan2.actions[0].action, ActionType.PRESS_KEY)
        self.assertEqual(plan2.actions[0].keys, ["enter"])

    def test_escape_tab_space(self):
        plan_esc = self.fast_path.match("Press escape please")
        self.assertIsNotNone(plan_esc)
        self.assertEqual(plan_esc.actions[0].keys, ["escape"])

        plan_tab = self.fast_path.match("Hit tab")
        self.assertIsNotNone(plan_tab)
        self.assertEqual(plan_tab.actions[0].keys, ["tab"])

        plan_space = self.fast_path.match("Hit spacebar please")
        self.assertIsNotNone(plan_space)
        self.assertEqual(plan_space.actions[0].keys, ["space"])

    def test_hotkeys_copy_paste_undo(self):
        plan_copy = self.fast_path.match("Can you copy that for me?")
        self.assertIsNotNone(plan_copy)
        self.assertEqual(plan_copy.actions[0].action, ActionType.HOTKEY)
        self.assertEqual(plan_copy.actions[0].keys, ["ctrl", "c"])

        plan_paste = self.fast_path.match("Paste here please")
        self.assertIsNotNone(plan_paste)
        self.assertEqual(plan_paste.actions[0].action, ActionType.HOTKEY)
        self.assertEqual(plan_paste.actions[0].keys, ["ctrl", "v"])

        plan_undo = self.fast_path.match("Undo that")
        self.assertIsNotNone(plan_undo)
        self.assertEqual(plan_undo.actions[0].keys, ["ctrl", "z"])

        plan_select = self.fast_path.match("Select all")
        self.assertIsNotNone(plan_select)
        self.assertEqual(plan_select.actions[0].keys, ["ctrl", "a"])

    def test_browser_navigation(self):
        plan_back1 = self.fast_path.match("Go back")
        self.assertIsNotNone(plan_back1)
        self.assertEqual(plan_back1.actions[0].action, ActionType.HOTKEY)
        self.assertEqual(plan_back1.actions[0].keys, ["alt", "left"])

        plan_back2 = self.fast_path.match("Can you go back please?")
        self.assertIsNotNone(plan_back2)
        self.assertEqual(plan_back2.actions[0].keys, ["alt", "left"])

        plan_fwd = self.fast_path.match("Go forward")
        self.assertIsNotNone(plan_fwd)
        self.assertEqual(plan_fwd.actions[0].keys, ["alt", "right"])

        plan_ref = self.fast_path.match("Refresh the page")
        self.assertIsNotNone(plan_ref)
        self.assertEqual(plan_ref.actions[0].keys, ["f5"])

        plan_tab = self.fast_path.match("Open a new tab")
        self.assertIsNotNone(plan_tab)
        self.assertEqual(plan_tab.actions[0].keys, ["ctrl", "t"])

        plan_close = self.fast_path.match("Close this tab please")
        self.assertIsNotNone(plan_close)
        self.assertEqual(plan_close.actions[0].keys, ["ctrl", "w"])

        plan_files = self.fast_path.match("Open file manager")
        self.assertIsNotNone(plan_files)
        self.assertEqual(plan_files.actions[0].keys, ["win", "e"])

        plan_exp = self.fast_path.match("Please open file explorer")
        self.assertIsNotNone(plan_exp)
        self.assertEqual(plan_exp.actions[0].keys, ["win", "e"])

        # Phonetic Whisper variation: "Pile Explorer"
        plan_pile = self.fast_path.match("Open pile explorer")
        self.assertIsNotNone(plan_pile)
        self.assertEqual(plan_pile.actions[0].keys, ["win", "e"])

        plan_yt = self.fast_path.match("Open YouTube")
        self.assertIsNotNone(plan_yt)
        self.assertEqual(plan_yt.actions[0].action, ActionType.LAUNCH)
        self.assertEqual(plan_yt.actions[0].text, "https://www.youtube.com")

        plan_chrome = self.fast_path.match("Please open Chrome")
        self.assertIsNotNone(plan_chrome)
        self.assertEqual(plan_chrome.actions[0].action, ActionType.LAUNCH)
        self.assertEqual(plan_chrome.actions[0].text, "chrome")

        plan_calc = self.fast_path.match("Open calculator")
        self.assertIsNotNone(plan_calc)
        self.assertEqual(plan_calc.actions[0].action, ActionType.LAUNCH)
        self.assertEqual(plan_calc.actions[0].text, "calc")

        plan_sett = self.fast_path.match("Open settings")
        self.assertIsNotNone(plan_sett)
        self.assertEqual(plan_sett.actions[0].keys, ["win", "i"])

        # Close File Explorer / close window
        plan_close_fe = self.fast_path.match("Close File Explorer")
        self.assertIsNotNone(plan_close_fe)
        self.assertEqual(plan_close_fe.actions[0].action, ActionType.HOTKEY)
        self.assertEqual(plan_close_fe.actions[0].keys, ["alt", "f4"])

        plan_close_win = self.fast_path.match("Please close this window")
        self.assertIsNotNone(plan_close_win)
        self.assertEqual(plan_close_win.actions[0].keys, ["alt", "f4"])

        # Open Downloads
        plan_dl = self.fast_path.match("Open Downloads")
        self.assertIsNotNone(plan_dl)
        self.assertEqual(plan_dl.actions[0].action, ActionType.LAUNCH)
        self.assertEqual(plan_dl.actions[0].text, "shell:Downloads")

    def test_visual_queries_fall_through_to_vision_ai(self):
        """Visual queries must return None so Vision AI Planner locates coordinates accurately."""
        visual_queries = [
            "Can you click on the search bar please?",
            "Click on the first video",
            "Search for python tutorials on youtube",
            "What is on my screen right now?",
            "Find the login button",
            "Type hello world into the text box",
            "Where is the save button?",
            "Explain what is open right now",
        ]
        for query in visual_queries:
            plan = self.fast_path.match(query)
            self.assertIsNone(plan, f"Query '{query}' should fall through to Vision AI, but matched fast path!")

    def test_latency_is_sub_millisecond(self):
        """Matching benchmark: must complete in <1ms."""
        start = time.perf_counter()
        for _ in range(100):
            self.fast_path.match("Could you please scroll down a bit?")
        elapsed = (time.perf_counter() - start) / 100
        self.assertLess(elapsed, 0.001, f"Fast-path matching took {elapsed*1000:.3f}ms (expected <1ms)")

    def test_multistep_open_notepad_and_write_palindrome(self):
        plan = self.fast_path.match("open notepad take new file and write palindrome code")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.type, "action")
        self.assertIn("Notepad", plan.answer)
        self.assertIn("palindrome", plan.answer)
        # Should have 5 steps: LAUNCH, WAIT, HOTKEY, WAIT, TYPE
        actions = [s.action for s in plan.actions]
        self.assertEqual(actions, [ActionType.LAUNCH, ActionType.WAIT, ActionType.HOTKEY, ActionType.WAIT, ActionType.TYPE])
        self.assertEqual(plan.actions[0].text, "notepad")
        self.assertEqual(plan.actions[2].keys, ["ctrl", "n"])
        self.assertIn("is_palindrome", plan.actions[4].text)

    def test_multistep_open_notepad_and_write_simple(self):
        plan = self.fast_path.match("open notepad and write palindrome code")
        self.assertIsNotNone(plan)
        actions = [s.action for s in plan.actions]
        self.assertEqual(actions, [ActionType.LAUNCH, ActionType.WAIT, ActionType.TYPE])
        self.assertEqual(plan.actions[0].text, "notepad")
        self.assertIn("is_palindrome", plan.actions[2].text)

    def test_multistep_open_notebook_and_write_something(self):
        plan = self.fast_path.match("open notebook and write somhing into that")
        self.assertIsNotNone(plan)
        actions = [s.action for s in plan.actions]
        self.assertEqual(actions, [ActionType.LAUNCH, ActionType.WAIT, ActionType.TYPE])
        self.assertEqual(plan.actions[0].text, "notepad")
        self.assertIsNotNone(plan.actions[2].text)

    def test_multistep_direct_write_palindrome(self):
        plan = self.fast_path.match("write palindrome code")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action, ActionType.TYPE)
        self.assertIn("is_palindrome", plan.actions[0].text)

    @patch("agent.loop.ENABLE_FAST_PATH", True)
    @patch("agent.loop.ENABLE_COMPUTER_CONTROL", True)
    def test_agent_loop_fast_path_integration(self):
        """Verify AgentLoop dispatches direct actions instantly without calling capture or planner."""
        loop = AgentLoop()
        loop.executor = MagicMock()
        loop.planner = MagicMock()

        answer = loop.run_cycle("Can you scroll up please?")
        self.assertIn("Scrolled up", answer)
        # Executor must have received the scroll step
        loop.executor.execute_step.assert_called_once()
        # Planner must NOT have been called (saving 1.5s - 20s)
        loop.planner.generate_plan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
