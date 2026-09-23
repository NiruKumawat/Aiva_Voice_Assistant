import time
from typing import List
from utils.logger import logger

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


class KeyboardController:
    """Safe keyboard controller for typing text and executing hotkeys."""

    def type_text(self, text: str, interval: float = 0.03, is_sensitive: bool = False):
        """Types the specified text character-by-character."""
        if not text:
            return

        display_text = "********" if is_sensitive else (text if len(text) <= 50 else text[:47] + "...")
        logger.info(f"Keyboard -> Type: '{display_text}'")

        if HAS_PYAUTOGUI:
            pyautogui.write(text, interval=interval)
        elif HAS_KEYBOARD:
            keyboard.write(text, delay=interval)
        else:
            logger.error("No keyboard driver available for type_text")

    def press_key(self, key: str):
        """Presses a single key (e.g. enter, tab, escape, backspace)."""
        clean_key = key.lower().strip()
        logger.info(f"Keyboard -> Press key: '{clean_key}'")

        if HAS_PYAUTOGUI:
            pyautogui.press(clean_key)
        elif HAS_KEYBOARD:
            keyboard.send(clean_key)
        else:
            logger.error("No keyboard driver available for press_key")

    def hotkey(self, keys: List[str]):
        """Executes a key combination (e.g. ['ctrl', 'c'])."""
        clean_keys = [k.lower().strip() for k in keys]
        logger.info(f"Keyboard -> Hotkey: {'+'.join(clean_keys)}")

        if HAS_PYAUTOGUI:
            pyautogui.hotkey(*clean_keys)
        elif HAS_KEYBOARD:
            keyboard.send("+".join(clean_keys))
        else:
            logger.error("No keyboard driver available for hotkey")
