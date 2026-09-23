import threading
import keyboard
from config import EMERGENCY_STOP_KEY
from utils.logger import logger


class EmergencyStopManager:
    """Listens for the emergency stop key (default: ESC) to immediately halt execution."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._hooked = False
        self._setup_hook()

    def _setup_hook(self):
        try:
            keyboard.on_press_key(EMERGENCY_STOP_KEY, self._on_key_press, suppress=False)
            self._hooked = True
            logger.info(f"Emergency stop listener registered on key: '{EMERGENCY_STOP_KEY}'")
        except Exception as e:
            logger.warning(f"Could not hook emergency stop key {EMERGENCY_STOP_KEY}: {e}")

    def _on_key_press(self, event):
        if not self._stop_event.is_set():
            logger.warning(f"EMERGENCY STOP TRIGGERED via {EMERGENCY_STOP_KEY.upper()}!")
            self.request_stop()

    def request_stop(self):
        """Immediately signals stop to all running action loops."""
        self._stop_event.set()

    def is_stop_requested(self) -> bool:
        """Returns whether a stop has been requested."""
        return self._stop_event.is_set()

    def reset(self):
        """Resets the stop event for a new request."""
        self._stop_event.clear()
