import time
import ctypes
import win32api
import win32con
from typing import Tuple
from utils.logger import logger

# Ensure Per-Monitor DPI awareness is active so cursor positioning matches physical pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Managed by EmergencyStopManager (ESC key / Stop UI button)
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


try:
    from ui.action_indicator import show_click_indicator
except ImportError:
    def show_click_indicator(x, y, color_theme="cyan"): pass


class MouseController:
    """Safe mouse controller with boundary validation, smooth visual glide, and PyAutoGUI / win32 fallback."""
    def __init__(self):
        v_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        v_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        v_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        v_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

        self.screen_left = v_left if v_width > 0 else 0
        self.screen_top = v_top if v_height > 0 else 0
        self.screen_width = v_width if v_width > 0 else win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        self.screen_height = v_height if v_height > 0 else win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

    def validate_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Clamps and validates coordinates within virtual screen dimensions."""
        clamped_x = max(self.screen_left, min(int(x), self.screen_left + self.screen_width - 1))
        clamped_y = max(self.screen_top, min(int(y), self.screen_top + self.screen_height - 1))
        if clamped_x != x or clamped_y != y:
            logger.warning(f"Coordinates ({x}, {y}) clamped to screen bounds ({clamped_x}, {clamped_y})")
        return clamped_x, clamped_y

    def move(self, x: int, y: int, duration: float = 0.1):
        """Moves cursor smoothly to the specified coordinates so the user can see it."""
        cx, cy = self.validate_coordinates(x, y)
        logger.info(f"Mouse -> Move to ({cx}, {cy})")
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(cx, cy, duration=duration)
        else:
            win32api.SetCursorPos((cx, cy))

    def click(self, x: int = None, y: int = None, button: str = "left"):
        """Clicks at coordinates or at current position with visual indicator and smooth glide."""
        if x is not None and y is not None:
            cx, cy = self.validate_coordinates(x, y)
            logger.info(f"Mouse -> Click ({button}) at ({cx}, {cy})")
            try:
                show_click_indicator(cx, cy, color_theme="cyan" if button == "left" else "green")
            except Exception:
                pass
            if HAS_PYAUTOGUI:
                pyautogui.moveTo(cx, cy, duration=0.1)
                time.sleep(0.02)
                pyautogui.click(button=button)
            else:
                win32api.SetCursorPos((cx, cy))
                time.sleep(0.02)
                if button == "left":
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                elif button == "right":
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            logger.info(f"Mouse -> Click ({button}) at current position")
            if HAS_PYAUTOGUI:
                pyautogui.click(button=button)
            else:
                if button == "left":
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                elif button == "right":
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def double_click(self, x: int = None, y: int = None):
        """Double clicks at coordinates with visual indicator and reliable 80ms interval."""
        if x is not None and y is not None:
            cx, cy = self.validate_coordinates(x, y)
            logger.info(f"Mouse -> Double Click at ({cx}, {cy})")
            try:
                show_click_indicator(cx, cy, color_theme="magenta")
            except Exception:
                pass
            if HAS_PYAUTOGUI:
                pyautogui.moveTo(cx, cy, duration=0.1)
                time.sleep(0.04)
                pyautogui.doubleClick(interval=0.08)
            else:
                win32api.SetCursorPos((cx, cy))
                time.sleep(0.04)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.08)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            logger.info("Mouse -> Double Click at current position")
            if HAS_PYAUTOGUI:
                pyautogui.doubleClick(interval=0.08)
            else:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.08)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def right_click(self, x: int = None, y: int = None):
        """Right clicks at coordinates."""
        self.click(x, y, button="right")
