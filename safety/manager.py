from typing import List, Optional, Tuple
from config import (
    MAX_ACTIONS_PER_REQUEST,
    REQUIRE_CONFIRMATION_FOR_SENSITIVE_ACTIONS,
    MAX_IDENTICAL_SCREEN_STATES
)
from computer.actions import ActionStep, ActionPlan, ActionType
from safety.validators import validate_coordinates, validate_active_window, clamp_coordinates
from safety.confirmation import ConfirmationManager
from safety.emergency_stop import EmergencyStopManager
from utils.logger import logger


class SafetyManager:
    """Central safety policy enforcer for computer-controlled actions."""

    def __init__(self):
        self.confirmation = ConfirmationManager()
        self.emergency_stop = EmergencyStopManager()
        self.action_count = 0
        self.recent_screen_hashes: List[int] = []

    def reset(self):
        """Resets state for a new user instruction sequence."""
        self.action_count = 0
        self.recent_screen_hashes.clear()
        self.emergency_stop.reset()

    def record_screen_hash(self, img_hash: int) -> bool:
        """
        Records the screen hash and checks for repeated identical screen states (loop detection).
        Returns True if a loop is detected, False otherwise.
        """
        self.recent_screen_hashes.append(img_hash)
        if len(self.recent_screen_hashes) > 6:
            self.recent_screen_hashes.pop(0)

        # Count consecutive identical states
        if len(self.recent_screen_hashes) >= MAX_IDENTICAL_SCREEN_STATES:
            tail = self.recent_screen_hashes[-MAX_IDENTICAL_SCREEN_STATES:]
            if len(set(tail)) == 1:
                logger.warning(f"Loop detected: screen remained identical for {MAX_IDENTICAL_SCREEN_STATES} steps.")
                return True
        return False

    def validate_step(self, step: ActionStep, expected_window: str) -> Tuple[bool, Optional[str]]:
        """
        Validates an action step before execution.
        Returns: (is_valid, error_reason)
        """
        # 1. Emergency stop check
        if self.emergency_stop.is_stop_requested():
            return False, "Emergency stop requested."

        # 2. Action limit check
        if self.action_count >= MAX_ACTIONS_PER_REQUEST:
            return False, f"Maximum action limit ({MAX_ACTIONS_PER_REQUEST}) reached."

        # 3. Active window consistency check
        if not validate_active_window(expected_window):
            return False, f"Active window changed. Stopped to prevent acting on wrong application."

        # 4. Target coordinate validation
        if step.action in [ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK, ActionType.MOVE]:
            if step.target and step.target.abs_x is not None and step.target.abs_y is not None:
                # Safely clamp boundary edge coordinates (e.g. taskbar or edge buttons) to valid pixels
                step.target.abs_x, step.target.abs_y = clamp_coordinates(step.target.abs_x, step.target.abs_y)
                if not validate_coordinates(step.target.abs_x, step.target.abs_y):
                    return False, f"Coordinates ({step.target.abs_x}, {step.target.abs_y}) are outside screen bounds."

        # 5. Sensitive action confirmation check
        if REQUIRE_CONFIRMATION_FOR_SENSITIVE_ACTIONS:
            if self.confirmation.is_action_sensitive(step):
                step.sensitive = True

        self.action_count += 1
        return True, None
