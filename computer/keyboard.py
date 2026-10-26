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
        """
        Types the specified text.
        For multiline text (code, paragraphs) or long text (>30 chars), uses fast clipboard pasting
        to avoid indentation distortion, special character misfires, and multi-second typing lag.
        """
        if not text:
            return

        display_text = "********" if is_sensitive else (text if len(text) <= 50 else text[:47] + "...")
        logger.info(f"Keyboard -> Type: '{display_text}' (len={len(text)})")

        # Fast clipboard injection for multiline, code, or longer text (unless sensitive)
        if not is_sensitive and ("\n" in text or len(text) > 30):
            try:
                import pyperclip
                pyperclip.copy(text)
                time.sleep(0.05)
                self.hotkey(["ctrl", "v"])
                time.sleep(0.05)
                return
            except Exception as e:
                logger.warning(f"Clipboard paste fallback to typing: {e}")

        if HAS_PYAUTOGUI:
            pyautogui.write(text, interval=interval)
        elif HAS_KEYBOARD:
            keyboard.write(text, delay=interval)
        else:
            logger.error("No keyboard driver available for type_text")

    def paste_text(self, text: str):
        """Directly copies text to clipboard and issues Ctrl+V paste."""
        if not text:
            return
        try:
            import pyperclip
            pyperclip.copy(text)
            time.sleep(0.05)
            self.hotkey(["ctrl", "v"])
            time.sleep(0.05)
        except Exception as e:
            logger.error(f"Keyboard -> paste_text failed: {e}")

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
