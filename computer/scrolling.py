import time
import win32api
import win32con
from typing import Optional
from utils.logger import logger

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class ScrollController:
    """Safe scrolling controller for desktop and active windows."""

    def __init__(self):
        self.screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        self.screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

    def scroll(self, direction: str = "down", amount: int = 500, x: Optional[int] = None, y: Optional[int] = None):
        """
        Scrolls the screen in the given direction.
        Moves cursor to (x, y) or screen center first so wheel events reach the active application.
        """
        dir_clean = direction.lower().strip()

        # If coordinates not specified, target screen center (prevents scrolling over sidebars)
        target_x = x if x is not None else (self.screen_width // 2)
        target_y = y if y is not None else (self.screen_height // 2)

        logger.info(f"Scroll -> {dir_clean} by {amount} at ({target_x}, {target_y})")

        clicks = amount // 100
        if clicks == 0:
            clicks = 1

        delta = -clicks if dir_clean == "down" else clicks

        # Position cursor over the scroll target window
        if HAS_PYAUTOGUI:
            try:
                pyautogui.moveTo(target_x, target_y, duration=0.1)
                time.sleep(0.05)
                # PyAutoGUI: negative is down on Windows, positive is up
                pyautogui.scroll(delta * 120, x=target_x, y=target_y)
            except Exception as e:
                logger.warning(f"PyAutoGUI scroll failed: {e}. Falling back to win32api.")
                win32api.SetCursorPos((target_x, target_y))
                time.sleep(0.05)
                win32_delta = delta * win32con.WHEEL_DELTA
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, win32_delta, 0)
        else:
            win32api.SetCursorPos((target_x, target_y))
            time.sleep(0.05)
            win32_delta = delta * win32con.WHEEL_DELTA
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, win32_delta, 0)
