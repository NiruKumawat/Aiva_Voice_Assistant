import win32api
import win32con
from capture.window import get_active_window_info
from utils.logger import logger


def validate_coordinates(x: int, y: int, max_w: int = None, max_h: int = None) -> bool:
    """Verifies coordinates are within valid virtual screen bounds."""
    screen_w = max_w if max_w is not None else win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    screen_h = max_h if max_h is not None else win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    return 0 <= x < screen_w and 0 <= y < screen_h


def clamp_coordinates(x: int, y: int, max_w: int = None, max_h: int = None) -> tuple:
    """
    Clamps coordinates to valid virtual screen bounds [0, screen_w - 1] and [0, screen_h - 1].
    Ensures boundary clicks (e.g. taskbar or edge buttons) are safe without failing validation.
    """
    try:
        screen_w = max_w if max_w is not None else win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_h = max_h if max_h is not None else win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    except Exception:
        screen_w = max_w if max_w is not None else 1920
        screen_h = max_h if max_h is not None else 1080
    cx = max(0, min(int(x), max(0, screen_w - 1)))
    cy = max(0, min(int(y), max(0, screen_h - 1)))
    return cx, cy


def validate_active_window(expected_title: str, current_title: str = None) -> bool:
    """
    Checks if the expected window is still the foreground active window.
    Prevents executing stale coordinates if the user switched windows mid-task.
    """
    if not expected_title or expected_title in ["Full Screen", "Unknown"]:
        return True

    if current_title is None:
        current_info = get_active_window_info()
        if not current_info:
            logger.warning("Could not determine current active window during safety check.")
            return True
        current_title = current_info.get("title", "")

    # Check if either contains the core title (handles dynamic browser title changes)
    if expected_title in current_title or current_title in expected_title:
        return True

    # Check first segment before separator (e.g. "Google Chrome", "Visual Studio Code")
    exp_prefix = expected_title.split(" - ")[-1].strip()
    curr_prefix = current_title.split(" - ")[-1].strip()
    if exp_prefix and curr_prefix and exp_prefix == curr_prefix:
        return True

    logger.warning(f"Active window safety violation: expected '{expected_title}', found '{current_title}'")
    return False
