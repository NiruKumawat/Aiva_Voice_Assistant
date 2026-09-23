import platform
import os
from typing import Optional, Dict, Any
from utils.logger import logger

_LAST_NON_ASSISTANT_WINDOW = None


def get_active_window_info() -> Optional[Dict[str, Any]]:
    """
    Returns a dictionary with 'title' and 'bbox' (left, top, right, bottom).
    Excludes the assistant's own window so it never captures itself.
    """
    global _LAST_NON_ASSISTANT_WINDOW

    if platform.system() != "Windows":
        return None

    try:
        import win32gui
        import win32process
        import win32con

        our_pid = os.getpid()
        hwnd = win32gui.GetForegroundWindow()

        # 1. Check if the foreground window is an actual application (not our assistant)
        if hwnd:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            title = win32gui.GetWindowText(hwnd).strip()
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]

            if pid != our_pid and title and title.lower() not in ["python", "voice assistant", "program manager", "windows input experience"]:
                if w > 150 and h > 150:
                    info = {"title": title, "bbox": rect, "hwnd": hwnd}
                    _LAST_NON_ASSISTANT_WINDOW = info
                    return info

        # 2. If foreground window is our assistant or empty, walk Z-order to find the underlying app
        h_cur = hwnd if hwnd else None
        while h_cur:
            h_cur = win32gui.GetWindow(h_cur, win32con.GW_HWNDNEXT)
            if not h_cur:
                break
            if not win32gui.IsWindowVisible(h_cur) or win32gui.IsIconic(h_cur):
                continue

            _, h_pid = win32process.GetWindowThreadProcessId(h_cur)
            if h_pid == our_pid:
                continue

            h_title = win32gui.GetWindowText(h_cur).strip()
            if not h_title or h_title.lower() in ["python", "program manager", "windows input experience", "settings", "taskbar"]:
                continue

            rect = win32gui.GetWindowRect(h_cur)
            w = rect[2] - rect[0]
            h_len = rect[3] - rect[1]
            if w > 200 and h_len > 200:
                info = {"title": h_title, "bbox": rect, "hwnd": h_cur}
                _LAST_NON_ASSISTANT_WINDOW = info
                return info

        # 3. Fallback to the last known target application window
        if _LAST_NON_ASSISTANT_WINDOW:
            return _LAST_NON_ASSISTANT_WINDOW

    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Error getting active window: {e}")

    return None
