import time
from typing import Optional, Callable, Dict, Any, List
from config import (
    ENABLE_COMPUTER_CONTROL,
    MAX_ACTIONS_PER_REQUEST,
    ENABLE_FAST_PATH,
    ENABLE_ACTION_VERIFICATION,
)
from capture.screen import capture_screen_detailed, ScreenCaptureData
from computer.actions import ActionPlan, ActionStep, ActionType
from computer.controller import ComputerController
from safety.manager import SafetyManager
from ai.action_planner import ActionPlanner
from agent.context import AgentContext
from agent.executor import ActionExecutor
from agent.verifier import ActionVerifier
from agent.fast_path import DirectActionFastPath
from utils.logger import logger


class AgentLoop:
    """Orchestrates the Observe -> Plan -> Safety Check -> Act -> Observe -> Verify agent cycle."""

    def __init__(self,
                 status_callback: Optional[Callable[[str], None]] = None,
                 tts_callback: Optional[Callable[[str], None]] = None,
                 confirm_callback: Optional[Callable[[str, Callable[[], None], Callable[[], None]], None]] = None):
        self.status_cb = status_callback or (lambda s: None)
        self.tts_cb = tts_callback or (lambda t: None)
        self.confirm_cb = confirm_callback

        self.planner = ActionPlanner()
        self.safety = SafetyManager()
        self.controller = ComputerController()
        self.executor = ActionExecutor(self.controller)
        self.verifier = ActionVerifier()
        self.context = AgentContext()
        self.fast_path = DirectActionFastPath()

        self.is_running = False
        self.pending_confirmation = None

    def stop(self):
        """Immediately aborts any running action execution."""
        logger.warning("AgentLoop -> Stop requested!")
        self.safety.emergency_stop.request_stop()
        self.is_running = False
        self.status_cb("Stopped")

    def run_cycle(self, user_instruction: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Executes the full agent loop for a user instruction.
        Returns the final spoken response text.
        """
        self.is_running = True
        self.safety.reset()

        logger.info(f"AgentLoop -> Starting cycle for: '{user_instruction}'")

        # 0a. FAST PATH FOR DIRECT ACTIONS (scroll, enter, keys, hotkeys in <0.3s)
        if ENABLE_FAST_PATH and ENABLE_COMPUTER_CONTROL and self.fast_path:
            fast_plan = self.fast_path.match(user_instruction)
            if fast_plan:
                # If there was a pending clarification, user moved on with a direct action
                self.context.clear_clarification()
                logger.info(f"AgentLoop -> Fast-path matched direct action: {fast_plan.actions[0].action}")
                self.status_cb(f"Executing: {fast_plan.actions[0].action.value}...")
                for step in fast_plan.actions:
                    self.executor.execute_step(step)
                    self.context.record_action(step, "")
                self.is_running = False
                self.status_cb("Ready")
                return fast_plan.answer or "Done."

        # 0b. CHECK PENDING CLARIFICATION (Multi-choice disambiguation from previous turn)
        if self.context.has_pending_clarification():
            resolved_target = self.context.resolve_clarification(user_instruction)
            if resolved_target:
                desc = resolved_target.description or "selected option"
                logger.info(f"AgentLoop -> Resolved ambiguous choice to: '{desc}'")
                self.status_cb(f"Clicking {desc}...")
                step = ActionStep(
                    action=ActionType.CLICK,
                    target=resolved_target,
                    reason=f"Selected {desc} based on user clarification"
                )
                single_plan = ActionPlan(
                    type="action",
                    thought=f"Executing chosen option: {desc}",
                    answer=f"Clicking on the {desc}.",
                    actions=[step]
                )
                screen_data = capture_screen_detailed()
                final_answer = self._execute_plan_sequence(single_plan, screen_data, user_instruction)
                self.is_running = False
                self.status_cb("Ready")
                return final_answer
            elif any(w in user_instruction.lower() for w in ["cancel", "stop", "nevermind", "neither"]):
                self.context.clear_clarification()
                self.is_running = False
                self.status_cb("Ready")
                return "Cancelled. What else would you like me to do?"
            else:
                # User did not answer the clarification (they moved on with a new instruction).
                # Clarifications are single-turn; clear it so it never hijacks subsequent actions.
                logger.info(f"AgentLoop -> User did not select a clarification candidate; clearing pending clarification.")
                self.context.clear_clarification()

        # 1. OBSERVE (Assistant window is auto-excluded from capture via SetWindowDisplayAffinity)
        self.status_cb("Observing Screen...")
        screen_data = capture_screen_detailed()
        initial_window = screen_data.window_title

        # Check pronoun context (e.g. "click it")
        resolved_target = self.context.resolve_pronoun_target(user_instruction)
        if resolved_target:
            logger.info(f"AgentLoop -> Resolved pronoun target: '{resolved_target.description}'")

        # 2. UNDERSTAND & PLAN
        self.status_cb("Planning Action...")
        plan = self.planner.generate_plan(user_instruction, screen_data, history)

        # Check if stop was requested while planning was running
        if self.safety.emergency_stop.is_stop_requested():
            logger.warning("AgentLoop -> Stop requested during planning; aborting cycle.")
            self.status_cb("Stopped")
            self.is_running = False
            return "Action stopped by user."

        # Check if plan asks for clarification among multiple candidates
        if plan.type == "clarify":
            self.is_running = False
            self.context.set_pending_clarification(plan.question or "Which one do you mean?", plan.options)
            logger.info(f"AgentLoop -> Clarification required: '{plan.question}' with {len(plan.options)} options")
            self.status_cb("Clarification Required")
            return plan.question or "There are multiple matching options on the screen. Which one would you like me to click?"

        # If pure informational query or computer control disabled, return answer directly
        if plan.type == "answer" or not ENABLE_COMPUTER_CONTROL or not plan.actions:
            self.is_running = False
            response = plan.answer or "I found the requested information on your screen."
            self.status_cb("Ready")
            return response

        # 3. SAFETY CHECK & SENSITIVE ACTION CONFIRMATION
        has_sensitive = any(self.safety.confirmation.is_action_sensitive(s) for s in plan.actions)
        if has_sensitive or plan.requires_confirmation:
            prompt = plan.confirmation_prompt or "This action has significant consequences. Do you want me to proceed?"
            logger.info(f"AgentLoop -> Confirmation required: '{prompt}'")
            self.status_cb("Confirmation Required")
            
            # Save pending execution state so voice or UI confirmation can resume
            self.pending_confirmation = {
                "plan": plan,
                "screen_data": screen_data,
                "user_instruction": user_instruction
            }
            self.is_running = False
            return prompt

        # 4. EXECUTE & VERIFY
        final_answer = self._execute_plan_sequence(plan, screen_data, user_instruction)
        self.is_running = False
        self.status_cb("Ready")
        return final_answer

    def execute_confirmed_plan(self) -> str:
        """Called when user confirms a sensitive action."""
        if not self.pending_confirmation:
            return "No pending action to confirm."

        data = self.pending_confirmation
        self.pending_confirmation = None
        self.is_running = True

        plan = data["plan"]
        screen_data = data["screen_data"]
        user_instruction = data["user_instruction"]

        # Mark all steps as confirmed
        for step in plan.actions:
            step.sensitive = False

        result = self._execute_plan_sequence(plan, screen_data, user_instruction)
        self.is_running = False
        self.status_cb("Ready")
        return result

    def cancel_pending_confirmation(self) -> str:
        """Called when user rejects a sensitive action."""
        self.pending_confirmation = None
        self.is_running = False
        self.status_cb("Ready")
        return "Action cancelled."

    def _execute_plan_sequence(self, plan: ActionPlan, initial_screen: ScreenCaptureData, user_instruction: str) -> str:
        """Iterates through action steps, validating and verifying each step."""
        current_screen = initial_screen
        last_explanation = ""

        for step_idx, step in enumerate(plan.actions):
            if self.safety.emergency_stop.is_stop_requested():
                self.status_cb("Stopped")
                return "Action stopped by user."

            # Safety validation
            is_valid, err_msg = self.safety.validate_step(step, initial_screen.window_title)
            if not is_valid:
                logger.warning(f"AgentLoop -> Step {step_idx} rejected: {err_msg}")
                self.status_cb("Stopped")
                return f"I stopped the action: {err_msg}"

            # ACT
            desc = step.target.description if step.target and step.target.description else step.action.value
            self.status_cb(f"Executing: {desc}")
            self.executor.execute_step(step)
            self.context.record_action(step, current_screen.window_title)

            # Skip redundant 20s secondary Groq verification call if disabled
            if not ENABLE_ACTION_VERIFICATION:
                continue

            # Brief pause for UI reaction / navigation
            time.sleep(0.8)

            # OBSERVE AGAIN (Assistant window is auto-excluded via SetWindowDisplayAffinity)
            self.status_cb("Verifying Action...")
            new_screen = capture_screen_detailed()

            # Loop detection
            img_hash = hash(new_screen.image_b64)
            if self.safety.record_screen_hash(img_hash):
                self.status_cb("Stopped")
                return "The screen stopped responding after the attempted actions, so I stopped."

            # VERIFY
            success, explanation = self.verifier.verify(step, current_screen, new_screen, user_instruction)
            current_screen = new_screen
            last_explanation = explanation

            if not success:
                logger.warning(f"AgentLoop -> Verification failed for step {step_idx}: {explanation}")
                # If this was the final action (e.g. clicking a link or shortcut to navigate),
                # web pages or apps frequently take a couple seconds to complete loading.
                if step_idx == len(plan.actions) - 1 and step.action in [ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.HOTKEY, ActionType.PRESS_KEY]:
                    logger.info("AgentLoop -> Final navigation step executed; completing gracefully.")
                    return plan.answer or f"I clicked {desc}. It may take a moment to load."
                return f"I attempted to {desc}, but {explanation}"

        return plan.answer or last_explanation or "Action completed successfully."
