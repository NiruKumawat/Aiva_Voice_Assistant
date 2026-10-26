import time
import re
from typing import Optional
from computer.controller import ComputerController
from computer.actions import ActionStep, ActionType
from utils.logger import logger


class ActionExecutor:
    """Executes validated ActionSteps using the ComputerController."""

    def __init__(self, controller: Optional[ComputerController] = None):
        self.controller = controller or ComputerController()

    def execute_step(self, step: ActionStep) -> bool:
        """Executes a single validated step."""
        logger.info(f"Executor -> Executing: {step.action} (target: {step.target.description if step.target else 'None'})")

        if step.action == ActionType.CLICK:
            if step.target and step.target.abs_x is not None and step.target.abs_y is not None:
                self.controller.click(step.target.abs_x, step.target.abs_y, button="left")
            else:
                self.controller.click(button="left")

        elif step.action == ActionType.DOUBLE_CLICK:
            if step.target and step.target.abs_x is not None and step.target.abs_y is not None:
                self.controller.double_click(step.target.abs_x, step.target.abs_y)
            else:
                self.controller.double_click()

        elif step.action == ActionType.RIGHT_CLICK:
            if step.target and step.target.abs_x is not None and step.target.abs_y is not None:
                self.controller.right_click(step.target.abs_x, step.target.abs_y)
            else:
                self.controller.right_click()

        elif step.action == ActionType.MOVE:
            if step.target and step.target.abs_x is not None and step.target.abs_y is not None:
                self.controller.move(step.target.abs_x, step.target.abs_y)

        elif step.action == ActionType.TYPE:
            # If target provided, click field first to focus
            if step.target and step.target.abs_x is not None and step.target.abs_y is not None:
                self.controller.click(step.target.abs_x, step.target.abs_y)
                time.sleep(0.15)
            if step.text:
                self.controller.type_text(step.text, is_sensitive=step.sensitive)

        elif step.action == ActionType.PRESS_KEY:
            if step.keys:
                for k in step.keys:
                    self.controller.press(k)

        elif step.action == ActionType.HOTKEY:
            if step.keys:
                self.controller.hotkey(step.keys)

        elif step.action == ActionType.SCROLL:
            sx = step.target.abs_x if step.target else None
            sy = step.target.abs_y if step.target else None
            self.controller.scroll(direction=step.direction, amount=step.amount, x=sx, y=sy)

        elif step.action == ActionType.WAIT:
            self.controller.wait(step.duration)

        elif step.action == ActionType.LAUNCH:
            if step.text:
                import subprocess
                import webbrowser
                clean_target = step.text.strip()
                logger.info(f"Executor -> Launch: {clean_target}")

                # 1. Browser + URL launch: "chrome https://..." or "msedge https://..."
                if clean_target.startswith("chrome ") or clean_target.startswith("msedge ") or clean_target.startswith("firefox "):
                    b_cmd, url = clean_target.split(" ", 1)
                    try:
                        subprocess.Popen(["cmd", "/c", "start", "", b_cmd, url], shell=False)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to launch {b_cmd} with {url}: {e}")
                        webbrowser.open(url)
                        return True

                # 2. Plain URLs
                if clean_target.startswith("http://") or clean_target.startswith("https://"):
                    webbrowser.open(clean_target)
                    return True

                # 3. Special shell folders
                if clean_target.startswith("shell:"):
                    try:
                        subprocess.Popen(["cmd", "/c", "start", "", f"explorer.exe {clean_target}"], shell=False)
                    except Exception as e:
                        logger.error(f"Executor -> Failed to launch shell folder {clean_target}: {e}")
                    return True

                # 4. Defensive check for phrases like "X in chrome browser" or "X in chrome"
                in_browser_match = re.search(r"^(.*?)\s+(?:in|on|using|with)\s+(?:the\s+)?(chrome(?:\s+browser)?|google\s+chrome|edge|firefox|browser|web\s+browser)$", clean_target, re.I)
                if in_browser_match:
                    dest = in_browser_match.group(1).strip()
                    br_type = in_browser_match.group(2).lower()
                    br_cmd = "chrome" if "chrome" in br_type else ("msedge" if "edge" in br_type else "start")
                    common_urls = {
                        "youtube": "https://www.youtube.com",
                        "google": "https://www.google.com",
                        "reddit": "https://www.reddit.com",
                        "github": "https://www.github.com",
                    }
                    dest_url = common_urls.get(dest.lower(), dest if dest.startswith("http") else f"https://{dest}")
                    try:
                        subprocess.Popen(["cmd", "/c", "start", "", br_cmd, dest_url], shell=False)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to launch {br_cmd} with {dest_url}: {e}")

                # 5. Windows application launcher with common user-friendly aliases
                aliases = {
                    "calculator": "calc",
                    "calc": "calc",
                    "chrome": "chrome",
                    "google chrome": "chrome",
                    "browser": "start",
                    "web browser": "start",
                    "edge": "msedge",
                    "microsoft edge": "msedge",
                    "notepad": "notepad",
                    "text editor": "notepad",
                    "code": "code",
                    "vscode": "code",
                    "vs code": "code",
                    "visual studio code": "code",
                    "terminal": "wt",
                    "cmd": "cmd",
                    "command prompt": "cmd",
                    "powershell": "powershell",
                    "paint": "mspaint",
                    "ms paint": "mspaint",
                    "excel": "excel",
                    "word": "winword",
                    "powerpoint": "powerpnt",
                    "control panel": "control",
                    "task manager": "taskmgr",
                }
                cmd_to_run = aliases.get(clean_target.lower(), clean_target)
                try:
                    subprocess.Popen(["cmd", "/c", "start", "", cmd_to_run], shell=False)
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Executor -> Failed to launch {clean_target} ({cmd_to_run}): {e}")

        elif step.action in [ActionType.FINISH, ActionType.ASK_CONFIRMATION, ActionType.SCREENSHOT]:
            pass

        return True
