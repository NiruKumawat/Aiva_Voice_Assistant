import time
from typing import List, Optional
from computer.mouse import MouseController
from computer.keyboard import KeyboardController
from computer.scrolling import ScrollController
from utils.logger import logger


class ComputerController:
    """Unified facade for desktop automation: mouse, keyboard, and scrolling."""

    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.scrolling = ScrollController()

    def move(self, x: int, y: int, duration: float = 0.2):
        self.mouse.move(x, y, duration=duration)

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left"):
        self.mouse.click(x, y, button=button)

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self.mouse.double_click(x, y)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self.mouse.right_click(x, y)

    def type_text(self, text: str, interval: float = 0.03, is_sensitive: bool = False):
        self.keyboard.type_text(text, interval=interval, is_sensitive=is_sensitive)

    def press(self, key: str):
        self.keyboard.press_key(key)

    def hotkey(self, keys: List[str]):
        self.keyboard.hotkey(keys)

    def scroll(self, direction: str = "down", amount: int = 500, x: Optional[int] = None, y: Optional[int] = None):
        self.scrolling.scroll(direction=direction, amount=amount, x=x, y=y)

    def wait(self, seconds: float = 1.0):
        logger.info(f"Controller -> Wait {seconds}s")
        time.sleep(seconds)
