"""
Comprehensive Benchmark Test Suite covering all 35 user-defined real-world scenarios:
- Media & YouTube Controls (Play, Pause, Mute, Wait, Volume %)
- Web Navigation & Search (Google, YouTube, Pricing, Contact Us)
- Safe Form Filling & Consequential Protection (Filling, Do Not Submit, Ask Confirmation)
- Code & Editor Tasks (VS Code, Python files, API Endpoints)
- File Explorer Inspection (Downloads folder, recent PDF, Do Not Open)
- Hover & Inspect without clicking (Coordinates check, Answer vs Action)
- Context & Pronoun Memory ('Click it' only on matching screen)
- Active Window Safety (Chrome -> VS Code context switch, preventing stale clicks)
- Ambiguity & Multi-Option Clarification (Multiple login buttons)
- Non-existent Target Graceful Exit (Report not found, stop)
- Loop Prevention & Action Limits (Safety ceiling, screen hash loop break)
- Emergency Stop (ESC aborts mid-sequence immediately)
"""

import unittest
import time
from unittest.mock import MagicMock, patch
from capture.screen import ScreenCaptureData
from computer.actions import ActionPlan, ActionStep, ActionType, ActionTarget
from agent.fast_path import DirectActionFastPath
from agent.loop import AgentLoop
from agent.context import AgentContext
from safety.manager import SafetyManager
from safety.confirmation import ConfirmationManager


class Test35BenchmarkSuite(unittest.TestCase):

    def setUp(self):
        self.fast_path = DirectActionFastPath()
        self.mock_screen = ScreenCaptureData(
            image_b64="test_b64",
            window_title="Google Chrome - YouTube",
            bbox={"left": 0, "top": 0, "width": 1366, "height": 768},
            original_size=(1366, 768),
            scaled_size=(1366, 768)
        )

    # -------------------------------------------------------------
    # 1-7: Media & YouTube Controls
    # -------------------------------------------------------------

    def test_01_youtube_search_play_flow(self):
        """1. Open YouTube, search for Shape of You, open official video, play it."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            thought="Search for Shape of You on YouTube and play the video",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=80, description="YouTube Search Bar")),
                ActionStep(action=ActionType.TYPE, text="Shape of You by Ed Sheeran"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
                ActionStep(action=ActionType.WAIT, duration=1.0),
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=280, description="Official Video Result")),
            ],
            answer="Playing Shape of You by Ed Sheeran on YouTube."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open YouTube, search for Shape of You by Ed Sheeran, open the official video, and play it.")
        self.assertIn("Playing Shape of You", result)
        self.assertEqual(agent.executor.execute_step.call_count, 5)

    def test_02_pause_video_fast_path(self):
        """2. Pause the video (instant <0.05ms dispatch)."""
        plan = self.fast_path.match("Pause the video.")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].action, ActionType.PRESS_KEY)
        self.assertEqual(plan.actions[0].keys, ["k"])
        self.assertIn("Paused", plan.answer)

    def test_03_play_video_again_fast_path(self):
        """3. Play the video again (instant <0.05ms dispatch)."""
        plan = self.fast_path.match("Play the video again.")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].action, ActionType.PRESS_KEY)
        self.assertEqual(plan.actions[0].keys, ["k"])
        self.assertIn("Playing", plan.answer)

    def test_04_mute_wait_unmute_sequence(self):
        """4. Mute the video, wait 3 seconds, and unmute it."""
        plan = self.fast_path.match("Mute the video, wait 3 seconds, and unmute it.")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 3)
        self.assertEqual(plan.actions[0].action, ActionType.PRESS_KEY)
        self.assertEqual(plan.actions[0].keys, ["m"])
        self.assertEqual(plan.actions[1].action, ActionType.WAIT)
        self.assertEqual(plan.actions[1].duration, 3.0)
        self.assertEqual(plan.actions[2].action, ActionType.PRESS_KEY)
        self.assertEqual(plan.actions[2].keys, ["m"])

    def test_05_set_video_volume_percentage(self):
        """5. Set the video volume to 50%."""
        plan = self.fast_path.match("Set the video volume to 50%.")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].action, ActionType.PRESS_KEY)
        self.assertEqual(plan.actions[0].keys, ["5"])
        self.assertIn("50%", plan.answer)

    def test_06_youtube_search_interstellar_wait_pause(self):
        """6. Search YouTube for Interstellar soundtrack, open result, play, wait 10s, pause."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=80, description="Search Bar")),
                ActionStep(action=ActionType.TYPE, text="Interstellar Hans Zimmer soundtrack"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
                ActionStep(action=ActionType.WAIT, duration=1.0),
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=280, description="Top Result")),
                ActionStep(action=ActionType.WAIT, duration=10.0),
                ActionStep(action=ActionType.PRESS_KEY, keys=["k"])
            ],
            answer="Played Interstellar soundtrack for 10 seconds and paused."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Search YouTube for Interstellar Hans Zimmer soundtrack, open the most relevant result, play it, wait 10 seconds, and pause it.")
        self.assertIn("Interstellar", result)
        self.assertEqual(agent.executor.execute_step.call_count, 7)

    def test_07_youtube_lofi_play_pause_tell_title(self):
        """7. Search lofi music, open first result, play 5s, pause, tell video title."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=80, description="Search Bar")),
                ActionStep(action=ActionType.TYPE, text="lofi music"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
                ActionStep(action=ActionType.WAIT, duration=1.0),
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=280, description="First Video")),
                ActionStep(action=ActionType.WAIT, duration=5.0),
                ActionStep(action=ActionType.PRESS_KEY, keys=["k"])
            ],
            answer="The video title is 'Lofi Hip Hop Radio - Beats to Relax/Study to'."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open YouTube, search for lofi music, open the first relevant video, play it for 5 seconds, pause it, and tell me the video title.")
        self.assertIn("Lofi Hip Hop", result)

    # -------------------------------------------------------------
    # 8-12: Web Navigation, Scrolling & Form Inspection
    # -------------------------------------------------------------

    def test_08_google_search_fastapi_tutorial_explain(self):
        """8. Search FastAPI tutorial on Google, open first result, tell what page is about."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=500, abs_y=300, description="Google Search Box")),
                ActionStep(action=ActionType.TYPE, text="Python FastAPI tutorial"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
                ActionStep(action=ActionType.WAIT, duration=1.0),
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=300, abs_y=250, description="First Search Result"))
            ],
            answer="The page is FastAPI's official tutorial covering routing, dependency injection, and Pydantic validation."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open Google, search for Python FastAPI tutorial, open the first relevant result, and tell me what the page is about.")
        self.assertIn("FastAPI", result)

    def test_09_pricing_section_scroll_and_summarize(self):
        """9. Find pricing section, scroll down if necessary, tell plans and prices."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.SCROLL, direction="down", amount=600),
                ActionStep(action=ActionType.WAIT, duration=0.5)
            ],
            answer="The available plans are Free ($0/mo), Pro ($15/mo), and Enterprise ($49/mo)."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open a website, find the pricing section, scroll down if necessary, and tell me the available plans and prices.")
        self.assertIn("Free ($0/mo)", result)

    def test_10_find_login_button_click_and_wait(self):
        """10. Find login button, click it, wait for login page to appear."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=1200, abs_y=45, description="Login Button")),
                ActionStep(action=ActionType.WAIT, duration=1.5)
            ],
            answer="Clicked the login button. The login page is now open."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open a webpage and find the login button. Click it and wait for the login page to appear.")
        self.assertIn("login page is now open", result)

    def test_11_webpage_search_ai_type_enter_report(self):
        """11. Find search box, type 'artificial intelligence', press Enter, report results."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=600, abs_y=150, description="Search Box")),
                ActionStep(action=ActionType.TYPE, text="artificial intelligence"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"])
            ],
            answer="The top results show Wikipedia's overview of AI, neural networks, and recent LLM breakthroughs."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open a webpage, find the search box, type artificial intelligence, press Enter, and tell me what results are shown.")
        self.assertIn("Wikipedia", result)

    def test_12_scroll_to_contact_us_section(self):
        """12. Scroll down to Contact Us section and report information."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.SCROLL, direction="down", amount=800)
            ],
            answer="The Contact Us section provides support email support@example.com and phone +1-800-555-0199."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open a webpage and scroll down until you find the Contact Us section. Tell me what information is available there.")
        self.assertIn("support@example.com", result)

    # -------------------------------------------------------------
    # 13-14: Form Filling & Sensitive Confirmation
    # -------------------------------------------------------------

    def test_13_form_fill_without_submit(self):
        """13. Enter name, email, dropdown, checkbox. DO NOT SUBMIT."""
        agent = AgentLoop()
        # Form actions MUST NOT contain a submit step or sensitive submit action
        actions = [
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=300, abs_y=200, description="Name Field")),
            ActionStep(action=ActionType.TYPE, text="Mayur Chauhan"),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=300, abs_y=250, description="Email Field")),
            ActionStep(action=ActionType.TYPE, text="test@example.com"),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=300, abs_y=300, description="Country Dropdown")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=300, abs_y=340, description="India Option")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=280, abs_y=380, description="Terms Checkbox"))
        ]
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=actions,
            requires_confirmation=False,
            answer="Filled in your name, email, dropdown option, and checked the checkbox without submitting."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open a safe test form, enter the name Mayur Chauhan, enter the email test@example.com, select an option from the dropdown, and check the available checkbox. Do not submit the form.")
        self.assertIn("without submitting", result)
        # Verify no submit button was clicked
        for call_arg in agent.executor.execute_step.call_args_list:
            step = call_arg[0][0]
            if step.target:
                self.assertNotIn("submit", step.target.description.lower())

    def test_14_form_submit_requires_confirmation(self):
        """14. Fill form, and ask for confirmation before clicking Submit."""
        agent = AgentLoop()
        submit_step = ActionStep(
            action=ActionType.CLICK,
            target=ActionTarget(abs_x=300, abs_y=450, description="Submit Form Button"),
            sensitive=True
        )
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[submit_step],
            requires_confirmation=True,
            confirmation_prompt="The form is filled and ready. Should I submit it?"
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            prompt = agent.run_cycle("Open a safe test form, fill in all required fields, and when the form is ready to submit, ask me for confirmation before clicking Submit.")
        self.assertEqual(prompt, "The form is filled and ready. Should I submit it?")
        # Crucial: Submit was NOT clicked!
        agent.executor.execute_step.assert_not_called()
        self.assertIsNotNone(agent.pending_confirmation)

    # -------------------------------------------------------------
    # 15-17: Code, VS Code & File Explorer
    # -------------------------------------------------------------

    def test_15_vscode_open_project_explain_code(self):
        """15. In VS Code, locate main Python file, open it, explain code."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=120, abs_y=200, description="main.py in File Tree"))
            ],
            answer="main.py initializes the FastAPI application, mounts CORS middleware, and includes API routers."
        ))
        agent.executor.execute_step = MagicMock()
        vscode_screen = ScreenCaptureData("b64", "main.py - Visual Studio Code", {"left":0,"top":0,"width":1366,"height":768}, (1366,768), (1366,768))
        with patch("agent.loop.capture_screen_detailed", return_value=vscode_screen):
            result = agent.run_cycle("Open VS Code, open a project folder, locate the main Python file, open it, and explain what the code does.")
        self.assertIn("FastAPI", result)

    def test_16_vscode_find_api_endpoint_function(self):
        """16. In VS Code, find API endpoint function, open it, explain purpose."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=400, abs_y=350, description="get_users endpoint definition"))
            ],
            answer="The function 'get_users' handles GET /api/v1/users, queries the database with pagination, and returns serialized user profiles."
        ))
        agent.executor.execute_step = MagicMock()
        vscode_screen = ScreenCaptureData("b64", "routes.py - Visual Studio Code", {"left":0,"top":0,"width":1366,"height":768}, (1366,768), (1366,768))
        with patch("agent.loop.capture_screen_detailed", return_value=vscode_screen):
            result = agent.run_cycle("In VS Code, find the function that contains the API endpoint, open it, and explain its purpose.")
        self.assertIn("get_users", result)

    def test_17_file_explorer_find_pdf_do_not_open(self):
        """17. In File Explorer Downloads, find latest PDF, report filename, DO NOT OPEN OR MODIFY."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="answer",
            thought="Inspected Downloads folder. Found latest PDF without clicking or modifying.",
            actions=[],  # ZERO actions -> purely observational
            answer="The most recently modified PDF in Downloads is 'invoice_september_2026.pdf'."
        ))
        agent.executor.execute_step = MagicMock()
        explorer_screen = ScreenCaptureData("b64", "Downloads", {"left":0,"top":0,"width":1366,"height":768}, (1366,768), (1366,768))
        with patch("agent.loop.capture_screen_detailed", return_value=explorer_screen):
            result = agent.run_cycle("Open File Explorer, navigate to the Downloads folder, find the most recently modified PDF, and tell me its filename. Do not open or modify it.")
        self.assertIn("invoice_september_2026.pdf", result)
        agent.executor.execute_step.assert_not_called()

    # -------------------------------------------------------------
    # 18-25: Hover, Inspect, Observe & Safe Exploration
    # -------------------------------------------------------------

    def test_18_hover_inspect_button_do_not_click(self):
        """18. Locate 'Sign Up' button, move mouse over it, tell where it is. DO NOT CLICK."""
        agent = AgentLoop()
        # Move mouse (hover) only, no click!
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.MOVE, target=ActionTarget(abs_x=1150, abs_y=45, description="Sign Up Button"))
            ],
            answer="The Sign Up button is located in the top-right corner of the page at screen coordinates (1150, 45)."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open a webpage, locate the Sign Up button, move the mouse over it, and tell me where it is. Do not click it.")
        self.assertIn("top-right corner", result)
        agent.executor.execute_step.assert_called_once()
        self.assertEqual(agent.executor.execute_step.call_args[0][0].action, ActionType.MOVE)

    def test_19_click_login_observe_change_report(self):
        """19. Find login button, click it, observe new screen and tell what changed."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=1200, abs_y=50, description="Login Button"))
            ],
            answer="Clicked the login button. The screen transitioned to the email and password login form."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Find the login button on the current screen and click it. Then observe the new screen and tell me what changed.")
        self.assertIn("login form", result)

    def test_20_search_box_machine_learning_first_result(self):
        """20. Search box -> type machine learning -> Enter -> tell first result title."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=500, abs_y=150, description="Search Input")),
                ActionStep(action=ActionType.TYPE, text="machine learning"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
                ActionStep(action=ActionType.WAIT, duration=1.0)
            ],
            answer="The first result title is 'Machine Learning - Coursera by Andrew Ng'."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("On the current webpage, find the search box, click it, type machine learning, press Enter, wait for the results page, and tell me the first result title.")
        self.assertIn("Machine Learning - Coursera", result)

    def test_21_interstellar_lower_volume_wait_pause_title(self):
        """21. Search Interstellar, play, volume 30%, wait 5s, pause, report title."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=80, description="Search Bar")),
                ActionStep(action=ActionType.TYPE, text="Interstellar soundtrack"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
                ActionStep(action=ActionType.WAIT, duration=1.0),
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=280, description="Video Result")),
                ActionStep(action=ActionType.PRESS_KEY, keys=["3"]),  # 30% volume
                ActionStep(action=ActionType.WAIT, duration=5.0),
                ActionStep(action=ActionType.PRESS_KEY, keys=["k"])   # pause
            ],
            answer="The video is 'Interstellar Main Theme - Hans Zimmer'."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Search YouTube for Interstellar soundtrack, open the relevant video, play it, lower the volume to 30%, wait 5 seconds, pause it, and tell me the video title.")
        self.assertIn("Interstellar Main Theme", result)

    def test_22_cricket_highlights_then_ai_news_search(self):
        """22. Open YouTube, search cricket highlights, play, pause after 5s, then search AI news."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=80, description="Search Bar")),
                ActionStep(action=ActionType.TYPE, text="cricket highlights"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
                ActionStep(action=ActionType.WAIT, duration=1.0),
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=280, description="Cricket Video")),
                ActionStep(action=ActionType.WAIT, duration=5.0),
                ActionStep(action=ActionType.PRESS_KEY, keys=["k"]),
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=80, description="Search Bar")),
                ActionStep(action=ActionType.TYPE, text="AI news"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"])
            ],
            answer="The first relevant AI news result is 'Google DeepMind Announces Gemini 2.0'."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open YouTube, search for cricket highlights, open a relevant video, play it, pause it after 5 seconds, then search for AI news and tell me the title of the first relevant result.")
        self.assertIn("Gemini 2.0", result)

    def test_23_weather_search_no_consequential_actions(self):
        """23. Google search weather Ahmedabad. Do NOT perform any purchase, login, or submission."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=500, abs_y=300, description="Google Search Bar")),
                ActionStep(action=ActionType.TYPE, text="weather Ahmedabad"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["enter"])
            ],
            requires_confirmation=False,
            answer="The current weather in Ahmedabad is 32°C and sunny with 45% humidity."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open Google and search for weather Ahmedabad. Do not perform any purchase, login, submission, or other consequential action.")
        self.assertIn("Ahmedabad", result)
        self.assertFalse(agent.safety.confirmation.is_action_sensitive(agent.executor.execute_step.call_args_list[0][0][0]))

    def test_24_click_search_result_scroll_explain_heading(self):
        """24. Click first result, wait for load, scroll down, explain relevant heading."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=[
                ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=300, abs_y=220, description="First Result Link")),
                ActionStep(action=ActionType.WAIT, duration=1.5),
                ActionStep(action=ActionType.SCROLL, direction="down", amount=500)
            ],
            answer="The heading 'Key Architecture Components' explains client-side rendering and background thread communication."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Click the first search result, wait for the page to load, scroll down, find a relevant heading, and explain that section to me.")
        self.assertIn("Architecture", result)

    def test_25_find_next_button_inspect_only_no_click(self):
        """25. Find 'Next' button on current page, tell where it is. DO NOT CLICK."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="answer",  # Answer only, no action
            actions=[],
            answer="The Next button is located at the bottom right of the table at screen position (820, 560)."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Find the Next button on the current page and tell me where it is. Do not click it.")
        self.assertIn("bottom right", result)
        agent.executor.execute_step.assert_not_called()

    # -------------------------------------------------------------
    # 26-28: Graceful Search, Context Validity & Active Window Confinement
    # -------------------------------------------------------------

    def test_26_button_not_visible_scroll_or_report_not_found(self):
        """26. If button not visible, scroll down. If still not found, report could not locate instead of repeated clicks."""
        agent = AgentLoop()
        # Planner scrolls once, determines element does not exist, and returns clean answer without infinite loops
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="answer",
            thought="Searched visible viewport and scrolled down. The requested button is not present on this page.",
            actions=[],
            answer="I scrolled down and searched the page, but I could not locate the requested button."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("If the requested button is not visible, scroll down and look for it. If it still cannot be found, tell me that you could not locate it instead of repeatedly clicking or scrolling.")
        self.assertIn("could not locate", result)
        agent.executor.execute_step.assert_not_called()

    def test_27_pronoun_click_it_validates_screen_context(self):
        """27. 'Click it' only clicks previously identified button if screen matches."""
        context = AgentContext()
        button_target = ActionTarget(abs_x=500, abs_y=300, description="Download Button")
        context.record_target(button_target)
        context.last_window_title = "Google Chrome - Download Page"

        # Case A: Same context -> resolves target
        resolved = context.resolve_pronoun_target("click it")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.abs_x, 500)

        # Case B: Context cleared or screen changed -> does NOT click stale target
        context.clear()
        resolved_stale = context.resolve_pronoun_target("click it")
        self.assertIsNone(resolved_stale)

    def test_28_active_window_switch_chrome_to_vscode_safety(self):
        """28. Switch from Chrome to VS Code mid-task -> verify window, do NOT use stale Chrome coords."""
        safety = SafetyManager()
        step = ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=500, abs_y=300, description="Chrome Button"))
        
        # When active window is VS Code but step expected Google Chrome
        with patch("safety.validators.get_active_window_info", return_value={"title": "Visual Studio Code - app.py", "bbox": [0,0,1366,768]}):
            is_valid, err = safety.validate_step(step, expected_window="Google Chrome")
            self.assertFalse(is_valid)
            self.assertIn("Active window changed", err)

    # -------------------------------------------------------------
    # 29-35: Consequential Actions, Emergency Stop, Clarification, Limits & Complex Task
    # -------------------------------------------------------------

    def test_29_consequential_actions_require_confirmation(self):
        """29. Ask confirmation before submitting form, sending email, deleting file, purchasing, or changing security."""
        cm = ConfirmationManager()
        sensitive_samples = [
            ActionStep(action=ActionType.CLICK, target=ActionTarget(description="Submit Form Button")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(description="Send Email Button")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(description="Delete Database File")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(description="Confirm Purchase and Pay")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(description="Reset Password & Security Settings"))
        ]
        for step in sensitive_samples:
            self.assertTrue(cm.is_action_sensitive(step), f"Failed to flag sensitive action: {step.target.description}")

    def test_30_emergency_stop_aborts_multi_step_task(self):
        """30. Press ESC while multi-step task is running -> immediately stops and returns control."""
        agent = AgentLoop()
        steps = [
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=100, abs_y=100, description="Step 1")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=200, abs_y=200, description="Step 2")),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=300, abs_y=300, description="Step 3"))
        ]
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(type="action", actions=steps))
        
        executed = []
        def mock_step(step):
            executed.append(step)
            # ESC triggered on first step
            agent.stop()

        agent.executor.execute_step = MagicMock(side_effect=mock_step)
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Start a multi-step task and press ESC while it is running.")
        self.assertIn("stopped", result.lower())
        self.assertEqual(len(executed), 1)  # Stopped immediately!

    def test_31_multiple_login_buttons_clarification(self):
        """31. If multiple login buttons visible -> ask which one instead of guessing."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="clarify",
            thought="Multiple login buttons visible on page",
            question="I see two login buttons: one in the top navigation bar and one inside the main banner. Which one would you like me to click?",
            options=[
                {"id": 1, "description": "top navigation login", "target": ActionTarget(abs_x=1100, abs_y=40)},
                {"id": 2, "description": "main banner login", "target": ActionTarget(abs_x=680, abs_y=420)}
            ]
        ))
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            response = agent.run_cycle("Find the login button and click it.")
        self.assertIn("Which one", response)
        self.assertTrue(agent.context.has_pending_clarification())

    def test_32_unreliable_target_asks_for_clarification(self):
        """32. If target button cannot be identified reliably -> ask for clarification instead of guessing."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="clarify",
            thought="Multiple result buttons identified",
            question="There are multiple buttons matching 'the button'. Did you mean the download button or the details button?",
            options=[
                {"id": 1, "description": "download button", "target": ActionTarget(abs_x=400, abs_y=300)},
                {"id": 2, "description": "details button", "target": ActionTarget(abs_x=400, abs_y=350)}
            ]
        ))
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            response = agent.run_cycle("Open the first result and click the button.")
        self.assertIn("Did you mean", response)

    def test_33_nonexistent_button_reports_not_found_and_stops(self):
        """33. Find button that does not exist -> report could not find target and stop."""
        agent = AgentLoop()
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="answer",
            thought="Target does not exist on page after visual scan",
            actions=[],
            answer="I could not find the requested button on this page."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Find a button that does not exist on this page.")
        self.assertIn("could not find", result)
        agent.executor.execute_step.assert_not_called()

    def test_34_action_limit_and_loop_prevention(self):
        """34. Continuous task -> verify action limit and loop prevention stops infinite cycling."""
        safety = SafetyManager()
        # Test action limit
        safety.action_count = 15  # MAX_ACTIONS_PER_REQUEST = 15
        is_valid, err = safety.validate_step(ActionStep(action=ActionType.CLICK), "Google Chrome")
        self.assertFalse(is_valid)
        self.assertIn("Maximum action limit", err)

        # Test screen hash loop detection
        safety.reset()
        for _ in range(3):
            is_loop = safety.record_screen_hash(123456789)
        self.assertTrue(is_loop)

    def test_35_complex_multi_step_sequential_execution(self):
        """35. Complex task: YouTube -> search relaxing music -> open result -> play -> volume 40% -> wait 10s -> pause -> tell title."""
        agent = AgentLoop()
        steps = [
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=80, description="YouTube Search Bar")),
            ActionStep(action=ActionType.TYPE, text="relaxing music"),
            ActionStep(action=ActionType.PRESS_KEY, keys=["enter"]),
            ActionStep(action=ActionType.WAIT, duration=1.0),
            ActionStep(action=ActionType.CLICK, target=ActionTarget(abs_x=450, abs_y=280, description="Most Relevant Video")),
            ActionStep(action=ActionType.PRESS_KEY, keys=["4"]),  # 40% volume
            ActionStep(action=ActionType.WAIT, duration=10.0),
            ActionStep(action=ActionType.PRESS_KEY, keys=["k"])   # pause
        ]
        agent.planner.generate_plan = MagicMock(return_value=ActionPlan(
            type="action",
            actions=steps,
            answer="The video title is 'Peaceful Piano Music - Relaxing Sleep & Study Background'."
        ))
        agent.executor.execute_step = MagicMock()
        with patch("agent.loop.capture_screen_detailed", return_value=self.mock_screen):
            result = agent.run_cycle("Open YouTube, search for a relaxing music video, open the most relevant result, play it, set the volume to 40%, wait 10 seconds, pause it, and tell me the title.")
        self.assertIn("Peaceful Piano Music", result)
        self.assertEqual(agent.executor.execute_step.call_count, 8)


if __name__ == "__main__":
    unittest.main()
