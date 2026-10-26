import re
from typing import Optional
from computer.actions import ActionPlan, ActionStep, ActionType
from utils.logger import logger


class DirectActionFastPath:
    """
    High-speed intent matcher for direct, non-visual OS actions (scrolling, keypresses, hotkeys).
    Bypasses screenshot capture and Vision LLM reasoning (saving 1.5 - 20 seconds of latency)
    while smoothly understanding natural, conversational human phrasing:
      - 'Can you scroll up please?'
      - 'Could you please roll down a bit?'
      - 'Please hit enter'
      - 'Can you copy that for me?'

    Returns None for any command requiring visual grounding (clicks, visual searches, reading screen).
    """

    # Stop words / fillers stripped from beginning of sentence
    PREFIX_FILLERS = [
        r"^listening\s*[\.\,\:\-]*\s+",
        r"^listen\s*[\.\,\:\-]*\s+",
        r"^can you please\s+",
        r"^could you please\s+",
        r"^would you please\s+",
        r"^will you please\s+",
        r"^can you kindly\s+",
        r"^could you kindly\s+",
        r"^can you\s+",
        r"^could you\s+",
        r"^would you\s+",
        r"^will you\s+",
        r"^can we\s+",
        r"^please\s+",
        r"^kindly\s+",
        r"^hey assistant\s+",
        r"^assistant\s+",
        r"^hey\s+",
        r"^just\s+",
        r"^now\s+",
        r"^go ahead and\s+",
        r"^i want you to\s+",
        r"^try to\s+",
        r"^help me\s+",
    ]

    # Stop words / fillers stripped from end of sentence
    SUFFIX_FILLERS = [
        r"\s+please$",
        r"\s+for me$",
        r"\s+kindly$",
        r"\s+now$",
        r"\s+thanks$",
        r"\s+thank you$",
        r"\s+ok$",
        r"\s+okay$",
    ]

    # Visual / complex action words that MUST be handled by Vision AI / Planner
    VISUAL_KEYWORDS = {
        "click", "tap", "double click", "right click", "press on",
        "search", "find", "look", "where", "what", "read", "explain",
        "open", "launch", "type", "write", "check", "inspect", "see",
        "tell me", "summarize", "describe", "who", "why", "how"
    }

    # Built-in code and text templates for instant typing
    PALINDROME_CODE = (
        "def is_palindrome(s):\n"
        "    # Check if a string is a palindrome\n"
        "    cleaned = ''.join(c.lower() for c in str(s) if c.isalnum())\n"
        "    return cleaned == cleaned[::-1]\n\n"
        "# Test cases\n"
        "test_cases = ['radar', 'level', 'Python', 'A man, a plan, a canal: Panama']\n"
        "for text in test_cases:\n"
        "    print(f\"{text!r:35} -> {is_palindrome(text)}\")\n"
    )

    HELLO_WORLD_CODE = (
        "def main():\n"
        "    print(\"Hello, World!\")\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )

    FIBONACCI_CODE = (
        "def fibonacci(n):\n"
        "    # Return first n Fibonacci numbers\n"
        "    series = [0, 1]\n"
        "    while len(series) < n:\n"
        "        series.append(series[-1] + series[-2])\n"
        "    return series[:n]\n\n"
        "print('Fibonacci series (first 10):', fibonacci(10))\n"
    )

    FACTORIAL_CODE = (
        "def factorial(n):\n"
        "    # Compute factorial recursively\n"
        "    return 1 if n <= 1 else n * factorial(n - 1)\n\n"
        "print('Factorial of 5:', factorial(5))\n"
    )

    SAMPLE_NOTE = (
        "# Notes\n"
        "AIVA Voice Assistant Workspace\n"
        "Ready for code, ideas, and notes.\n"
    )

    def _resolve_snippet(self, topic: str) -> tuple:
        """Returns (code_or_text, topic_description)"""
        t = topic.lower().strip()
        if any(k in t for k in ["palindrome", "palindrom"]):
            return self.PALINDROME_CODE, "palindrome code"
        if any(k in t for k in ["hello world", "helloworld", "hello-world"]):
            return self.HELLO_WORLD_CODE, "hello world code"
        if any(k in t for k in ["fibonacci", "fibonaci"]):
            return self.FIBONACCI_CODE, "fibonacci code"
        if any(k in t for k in ["factorial"]):
            return self.FACTORIAL_CODE, "factorial code"
        if any(k in t for k in ["something", "anything", "some text", "a note", "sample note", "notes"]):
            return self.SAMPLE_NOTE, "sample notes"

        clean_text = re.sub(r"^(a\s+)?(note|message|memo|text|sentence|comment)\s+(saying|that\s+says)?\s*", "", topic, flags=re.I).strip()
        if clean_text:
            clean_text = clean_text[0].upper() + clean_text[1:]
            return clean_text, "your text"
        return self.SAMPLE_NOTE, "notes"

    def _match_compound_multistep(self, raw_lower: str, user_instruction: str) -> Optional[ActionPlan]:
        """
        Matches multi-step compound desktop workflows that do not require visual grounding:
        e.g.
          - 'open notepad take new file and write palindrome code'
          - 'open notepad and write palindrome code'
          - 'open notepad create new file and write hello world'
          - 'take new file and write palindrome code'
          - 'write palindrome code'
        """
        norm = self.normalize_text(user_instruction)
        cleaned = norm.replace("note pad", "notepad").replace("notebook", "notepad")

        # 1. Pattern: Open [App] + [Take New File] + Write [Topic]
        compound_app_match = re.search(
            r"^(?:open|launch|start)\s+(notepad|code|vscode|vs\s*code|text\s*editor|word)\s*"
            r"(?:and|,|then)?\s*(?:take|create|make|open)?\s*(?:a\s+)?(?:new\s+)?(file|document|doc|note|pile|tab)?\s*"
            r"(?:and|,|then|to)?\s*(?:write|type|insert|put|generate)\s+(?:something\s+into\s+that|something\s+in\s+it|something|.+?)$",
            cleaned,
            re.I
        )
        if not compound_app_match:
            compound_app_match = re.search(
                r"^(?:open|launch|start)\s+(notepad|code|vscode|vs\s*code|text\s*editor|word)\b.*?\b(?:write|type|put)\s+(.+)$",
                cleaned,
                re.I
            )

        if compound_app_match:
            app_raw = compound_app_match.group(1).lower()
            app_cmd = "notepad" if ("not" in app_raw or "text" in app_raw) else ("code" if "code" in app_raw else app_raw)
            app_name = "Notepad" if app_cmd == "notepad" else app_cmd.title()

            full_match_text = compound_app_match.group(0)
            write_part_match = re.search(r"\b(?:write|type|put|insert|generate)\s+(.+)$", full_match_text, re.I)
            topic_str = write_part_match.group(1) if write_part_match else "something"
            topic_str = re.sub(r"\b(into\s+that|in\s+it|in\s+that|into\s+it|there)\b", "", topic_str, flags=re.I).strip()

            snippet, desc = self._resolve_snippet(topic_str)
            wants_new_file = bool(re.search(r"\b(new\s+(file|document|doc|note|pile|tab)|take\s+(a\s+)?(new\s+)?file)\b", cleaned, re.I))

            actions = [
                ActionStep(action=ActionType.LAUNCH, text=app_cmd, reason=f"Launch {app_name}"),
                ActionStep(action=ActionType.WAIT, duration=1.0, reason=f"Wait for {app_name} to open and take focus")
            ]

            if wants_new_file:
                actions.append(ActionStep(action=ActionType.HOTKEY, keys=["ctrl", "n"], reason=f"Create new file in {app_name}"))
                actions.append(ActionStep(action=ActionType.WAIT, duration=0.4, reason="Wait for new file editor tab"))

            actions.append(ActionStep(action=ActionType.TYPE, text=snippet, reason=f"Write {desc} into {app_name}"))

            if wants_new_file:
                answer = f"Opening {app_name}, creating a new file, and writing {desc}."
            else:
                answer = f"Opening {app_name} and writing {desc}."

            logger.info(f"DirectActionFastPath -> Matched compound app workflow: {answer} ({len(actions)} steps)")
            return ActionPlan(
                type="action",
                thought=f"Compound workflow: Launch {app_name}, optional new file, and write {desc}.",
                answer=answer,
                actions=actions
            )

        # 2. Pattern: In current editor: "take new file and write [topic]" / "create new file and write [topic]"
        editor_new_write = re.search(
            r"^(?:take|create|make|open)?\s*(?:a\s+)?new\s+(?:file|document|doc|note|pile|tab)\s*(?:and|,|then|to)?\s*(?:write|type|insert|put|generate)\s+(.+)$",
            cleaned,
            re.I
        )
        if editor_new_write:
            topic_str = editor_new_write.group(1).strip()
            topic_str = re.sub(r"\b(into\s+that|in\s+it|in\s+that|into\s+it|there)\b", "", topic_str, flags=re.I).strip()
            snippet, desc = self._resolve_snippet(topic_str)
            actions = [
                ActionStep(action=ActionType.HOTKEY, keys=["ctrl", "n"], reason="Create new file"),
                ActionStep(action=ActionType.WAIT, duration=0.4, reason="Wait for new file editor tab"),
                ActionStep(action=ActionType.TYPE, text=snippet, reason=f"Write {desc}")
            ]
            answer = f"Creating a new file and writing {desc}."
            logger.info(f"DirectActionFastPath -> Matched new file & write: {answer}")
            return ActionPlan(
                type="action",
                thought=f"New file and write {desc}.",
                answer=answer,
                actions=actions
            )

        # 3. Pattern: Direct write into current focus: "write palindrome code" / "write hello world"
        direct_write = re.search(
            r"^(?:write|type|insert|generate)\s+(palindrome\s+code|palindrome\s+program|palindrome\s+function|palindrome|hello\s+world\s+code|hello\s+world|fibonacci\s+code|fibonacci|factorial\s+code|factorial)$",
            cleaned,
            re.I
        )
        if direct_write:
            topic_str = direct_write.group(1).strip()
            snippet, desc = self._resolve_snippet(topic_str)
            actions = [
                ActionStep(action=ActionType.TYPE, text=snippet, reason=f"Write {desc}")
            ]
            answer = f"Writing {desc}."
            logger.info(f"DirectActionFastPath -> Matched direct code write: {answer}")
            return ActionPlan(
                type="action",
                thought=f"Write {desc} into active document.",
                answer=answer,
                actions=actions
            )

        return None

    def normalize_text(self, text: str) -> str:
        """Strips punctuation and polite conversational fillers to isolate core command."""
        cleaned = text.lower().strip()
        # Remove trailing punctuation and delimiters, preserving domain dots like github.com
        cleaned = re.sub(r"[?!,;:]+", " ", cleaned)
        cleaned = re.sub(r"(?<!\w)\.|\.(?!\w)", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Phonetic cleanups for common desktop voice commands
        cleaned = re.sub(r"\bnot\s*paid\b", "notepad", cleaned)
        cleaned = re.sub(r"\bnot\s*prid\b", "notepad", cleaned)
        cleaned = re.sub(r"\bnotebook\b", "notepad", cleaned)
        cleaned = re.sub(r"\bsomhing\b", "something", cleaned)
        cleaned = re.sub(r"\bnew\s*pile\b", "new file", cleaned)
        cleaned = re.sub(r"\btake\s*a\s*new\s*pile\b", "take a new file", cleaned)

        # Iteratively strip polite prefixes
        changed = True
        while changed:
            changed = False
            for pattern in self.PREFIX_FILLERS:
                new_text = re.sub(pattern, "", cleaned).strip()
                if new_text != cleaned:
                    cleaned = new_text
                    changed = True

        # Iteratively strip polite suffixes
        changed = True
        while changed:
            changed = False
            for pattern in self.SUFFIX_FILLERS:
                new_text = re.sub(pattern, "", cleaned).strip()
                if new_text != cleaned:
                    cleaned = new_text
                    changed = True

        return cleaned

    def match(self, user_instruction: str) -> Optional[ActionPlan]:
        """
        Attempts to match a direct OS action.
        Returns an ActionPlan if matched, or None if visual reasoning is required.
        """
        if not user_instruction or not user_instruction.strip():
            return None

        raw_lower = user_instruction.lower().strip()

        # 0. Check compound multi-step non-visual workflows (e.g. open notepad take new file and write palindrome code)
        compound_plan = self._match_compound_multistep(raw_lower, user_instruction)
        if compound_plan:
            return compound_plan

        # 1. Negative check: if visual keywords exist, immediately fall through to Vision Planner
        # e.g., "click search bar", "find the first video", "type python in search"
        tokens = set(re.findall(r"\b\w+\b", raw_lower))
        for vk in self.VISUAL_KEYWORDS:
            if vk in ["open", "launch"]:
                if re.search(r"\b(open|launch)\s+(a\s+)?(new\s+)?tab\b", raw_lower):
                    continue  # Allow direct hotkey "open a new tab" (Ctrl+T)
                if re.search(r"\b(open|launch|create|make|take)?\s*(a\s+)?new\s+(file|document|doc|note|pile)\b", raw_lower):
                    continue  # Allow direct hotkey "create a new file" (Ctrl+N)
                if re.search(r"\b(open|launch)\s+(the\s+)?(file\s*manager|file\s*explorer|pile\s*explorer|explorer|my\s*computer|files)\b", raw_lower):
                    continue  # Allow direct Windows hotkey Win+E
                if re.search(r"\b(open|launch|start|go\s*to)\b", raw_lower) and not any(k in raw_lower for k in ["search", "find", "click", "look", "type", "play", "video", "menu", "dropdown", "link", "icon", "button", "first", "second", "third", "result", "dialog", "drawer"]):
                    continue  # Allow generalized universal app & website launcher
            if " " in vk:
                if vk in raw_lower:
                    return None
            else:
                if vk in tokens:
                    return None

        # 2. Normalize conversational phrasing
        cmd = self.normalize_text(user_instruction)
        if not cmd:
            return None

        logger.debug(f"DirectActionFastPath -> Normalized '{user_instruction}' to '{cmd}'")

        # 3. Detect modifiers for scroll amount
        scroll_amount = 500
        if any(w in cmd for w in ["a bit", "a little", "slightly", "slowly"]):
            scroll_amount = 250
            cmd = re.sub(r"\b(a bit|a little|slightly|slowly)\b", "", cmd).strip()
            cmd = re.sub(r"\s+", " ", cmd).strip()
        elif any(w in cmd for w in ["a lot", "more", "faster"]):
            scroll_amount = 1000
            cmd = re.sub(r"\b(a lot|more|faster)\b", "", cmd).strip()
            cmd = re.sub(r"\s+", " ", cmd).strip()

        # 4. Check Direct Match Patterns

        # --- SCROLL DOWN ---
        if re.match(r"^(scroll\s*down|scrolldown|roll\s*down|move\s*down|down)$", cmd):
            step = ActionStep(
                action=ActionType.SCROLL,
                direction="down",
                amount=scroll_amount,
                reason=f"Fast-path scroll down ({scroll_amount}px)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct scroll down",
                answer="Scrolled down.",
                actions=[step]
            )

        # --- SCROLL UP ---
        if re.match(r"^(scroll\s*up|scrollup|roll\s*up|move\s*up|up)$", cmd):
            step = ActionStep(
                action=ActionType.SCROLL,
                direction="up",
                amount=scroll_amount,
                reason=f"Fast-path scroll up ({scroll_amount}px)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct scroll up",
                answer="Scrolled up.",
                actions=[step]
            )

        # --- SCROLL TO TOP ---
        if re.match(r"^(scroll\s*(all\s*the\s*way\s*)?(to\s*)?(the\s*)?top|go\s*to\s*(the\s*)?top|jump\s*to\s*(the\s*)?top|top)(\s*of\s*(the\s*)?page)?$", cmd):
            step = ActionStep(
                action=ActionType.SCROLL,
                direction="up",
                amount=5000,
                reason="Fast-path scroll to top of page"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct scroll to top",
                answer="Scrolled to the top.",
                actions=[step]
            )

        # --- SCROLL TO BOTTOM ---
        if re.match(r"^(scroll\s*(all\s*the\s*way\s*)?(to\s*)?(the\s*)?bottom|go\s*to\s*(the\s*)?bottom|jump\s*to\s*(the\s*)?bottom|bottom)(\s*of\s*(the\s*)?page)?$", cmd):
            step = ActionStep(
                action=ActionType.SCROLL,
                direction="down",
                amount=5000,
                reason="Fast-path scroll to bottom of page"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct scroll to bottom",
                answer="Scrolled to the bottom.",
                actions=[step]
            )

        # --- PAGE DOWN / UP ---
        if re.match(r"^(page\s*down|pagedown)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["pagedown"],
                reason="Fast-path page down key"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path page down",
                answer="Paged down.",
                actions=[step]
            )

        if re.match(r"^(page\s*up|pageup)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["pageup"],
                reason="Fast-path page up key"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path page up",
                answer="Paged up.",
                actions=[step]
            )

        # --- ENTER KEY ---
        if re.match(r"^(hit\s*enter|press\s*enter|enter\s*key|press\s*the\s*enter\s*key|hit\s*the\s*enter\s*key|enter|submit)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["enter"],
                reason="Fast-path press Enter"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Enter keypress",
                answer="Pressed Enter.",
                actions=[step]
            )

        # --- ESCAPE KEY ---
        if re.match(r"^(hit\s*escape|press\s*escape|hit\s*esc|press\s*esc|escape|esc)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["escape"],
                reason="Fast-path press Escape"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Escape keypress",
                answer="Pressed Escape.",
                actions=[step]
            )

        # --- TAB KEY ---
        if re.match(r"^(hit\s*tab|press\s*tab|tab\s*key|tab)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["tab"],
                reason="Fast-path press Tab"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Tab keypress",
                answer="Pressed Tab.",
                actions=[step]
            )

        # --- SPACE KEY ---
        if re.match(r"^(hit\s*space|press\s*space|hit\s*spacebar|press\s*spacebar|spacebar|space)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["space"],
                reason="Fast-path press Space"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Space keypress",
                answer="Pressed Space.",
                actions=[step]
            )

        # --- BACKSPACE KEY ---
        if re.match(r"^(hit\s*backspace|press\s*backspace|backspace)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["backspace"],
                reason="Fast-path press Backspace"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Backspace keypress",
                answer="Pressed Backspace.",
                actions=[step]
            )

        # --- MEDIA CONTROL: PAUSE / PLAY / RESUME ---
        if re.match(r"^(pause(\s*(the|this))?\s*video|pause)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["k"],
                reason="Fast-path pause video (K key)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Pause video",
                answer="Paused the video.",
                actions=[step]
            )

        if re.match(r"^(play(\s*(the|this))?\s*video(\s*again)?|resume(\s*(the|this))?\s*video|play\s*again)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["k"],
                reason="Fast-path play/resume video (K key)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Play video",
                answer="Playing the video.",
                actions=[step]
            )

        # --- MEDIA CONTROL: MUTE WITH DURATION WAIT & UNMUTE ---
        m_wait = re.match(r"^mute(\s*(the|this))?\s*video\s*(and\s*)?wait\s*(\d+)\s*seconds?\s*(and\s*)?unmute(\s*(it|the\s*video))?$", cmd)
        if m_wait:
            sec = float(m_wait.group(4))
            steps = [
                ActionStep(action=ActionType.PRESS_KEY, keys=["m"], reason="Fast-path mute (M key)"),
                ActionStep(action=ActionType.WAIT, duration=sec, reason=f"Wait {sec} seconds"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["m"], reason="Fast-path unmute (M key)")
            ]
            return ActionPlan(
                type="action",
                thought=f"Fast-path mute for {sec}s and unmute",
                answer=f"Muted for {int(sec)} seconds and unmuted.",
                actions=steps
            )

        # --- MEDIA CONTROL: MUTE / UNMUTE ---
        if re.match(r"^(mute(\s*(the|this))?\s*video|mute)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["m"],
                reason="Fast-path mute video (M key)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Mute",
                answer="Muted the video.",
                actions=[step]
            )

        if re.match(r"^(unmute(\s*(the|this))?\s*video|unmute)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["m"],
                reason="Fast-path unmute video (M key)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Unmute",
                answer="Unmuted the video.",
                actions=[step]
            )

        # --- MEDIA CONTROL: SET VOLUME (PERCENTAGE) ---
        m_vol = re.match(r"^(set|lower|change|turn)?\s*(the\s*)?(video\s*)?volume\s*(to\s*)?(\d{1,3})%?$", cmd)
        if m_vol:
            pct = int(m_vol.group(5))
            digit = str(min(9, max(0, pct // 10)))
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=[digit],
                reason=f"Fast-path set volume to {pct}% (key {digit})"
            )
            return ActionPlan(
                type="action",
                thought=f"Fast-path direct volume adjustment to {pct}%",
                answer=f"Set video volume to {pct}%.",
                actions=[step]
            )

        # --- HOTKEYS: COPY ---
        if re.match(r"^(copy|copy\s*that|copy\s*this|copy\s*text)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "c"],
                reason="Fast-path copy to clipboard (Ctrl+C)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Copy hotkey",
                answer="Copied to clipboard.",
                actions=[step]
            )

        # --- HOTKEYS: PASTE ---
        if re.match(r"^(paste|paste\s*that|paste\s*this|paste\s*here)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "v"],
                reason="Fast-path paste from clipboard (Ctrl+V)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Paste hotkey",
                answer="Pasted from clipboard.",
                actions=[step]
            )

        # --- HOTKEYS: CUT ---
        if re.match(r"^(cut|cut\s*that|cut\s*this)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "x"],
                reason="Fast-path cut to clipboard (Ctrl+X)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Cut hotkey",
                answer="Cut to clipboard.",
                actions=[step]
            )

        # --- HOTKEYS: NEW FILE / DOCUMENT (Ctrl+N) ---
        if re.search(r"^(create|open|take|make|start)?\s*(a\s+)?new\s+(file|document|doc|note|pile)(\s+in\s+[a-zA-Z0-9\s]+)?$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "n"],
                reason="Fast-path create new file (Ctrl+N)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct New File hotkey",
                answer="Created a new file.",
                actions=[step]
            )

        # --- HOTKEYS: CLEAR ALL / BLANK FILE (Ctrl+A -> Delete) ---
        if re.search(r"^(clear|blank|empty|wipe|erase)\s+(?:(?:all|the|this|complete|entire|current)\s*)*(?:file|document|doc|text|content|notepad)?(\s*text)?(\s*from\s*.*)?$", cmd):
            steps = [
                ActionStep(action=ActionType.HOTKEY, keys=["ctrl", "a"], reason="Select all (Ctrl+A)"),
                ActionStep(action=ActionType.WAIT, duration=0.05, reason="Wait for selection"),
                ActionStep(action=ActionType.PRESS_KEY, keys=["delete"], reason="Delete selected text")
            ]
            return ActionPlan(
                type="action",
                thought="Fast-path clear all text in active document",
                answer="Cleared all text.",
                actions=steps
            )

        # --- HOTKEYS: COPY ALL TEXT / WEBPAGE (Ctrl+A -> Ctrl+C) ---
        if re.search(r"^copy\s+(?:all|complete|entire|whole|the\s+complete|this\s+complete)?\s*(?:text|content)?(\s*from\s*.*)?$", cmd):
            steps = [
                ActionStep(action=ActionType.HOTKEY, keys=["ctrl", "a"], reason="Select all (Ctrl+A)"),
                ActionStep(action=ActionType.WAIT, duration=0.05, reason="Wait for selection"),
                ActionStep(action=ActionType.HOTKEY, keys=["ctrl", "c"], reason="Copy to clipboard (Ctrl+C)")
            ]
            return ActionPlan(
                type="action",
                thought="Fast-path copy all text to clipboard",
                answer="Copied all text to clipboard.",
                actions=steps
            )

        # --- HOTKEYS: SELECT ALL (Ctrl+A) ---
        if re.search(r"^(select|highlight)\s*(?:all|everything|complete|entire|whole|the\s+current|the\s+complete)?\s*(?:text|content)?(\s*from\s*.*)?$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "a"],
                reason="Fast-path select all (Ctrl+A)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Select All hotkey",
                answer="Selected all text.",
                actions=[step]
            )

        # --- HOTKEYS: SAVE FILE (Ctrl+S) ---
        if re.search(r"^save\s*(the|this)?\s*(file|document|doc|changes|page)?$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "s"],
                reason="Fast-path save file (Ctrl+S)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Save file hotkey",
                answer="Saved.",
                actions=[step]
            )

        # --- HOTKEYS: UNDO ---
        if re.match(r"^(undo|undo\s*that|revert)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "z"],
                reason="Fast-path undo (Ctrl+Z)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Undo hotkey",
                answer="Undone.",
                actions=[step]
            )

        # --- HOTKEYS: REDO ---
        if re.match(r"^(redo|redo\s*that)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "y"],
                reason="Fast-path redo (Ctrl+Y)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Redo hotkey",
                answer="Redone.",
                actions=[step]
            )

        # --- HOTKEYS: ZOOM IN / OUT ---
        if re.match(r"^(zoom\s*in)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "plus"],
                reason="Fast-path zoom in (Ctrl++)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Zoom In hotkey",
                answer="Zoomed in.",
                actions=[step]
            )

        if re.match(r"^(zoom\s*out)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "minus"],
                reason="Fast-path zoom out (Ctrl+-)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Zoom Out hotkey",
                answer="Zoomed out.",
                actions=[step]
            )

        # --- BROWSER / SYSTEM NAVIGATION: GO BACK ---
        if re.match(r"^(go\s*back|back|navigate\s*back|previous\s*page|go\s*to\s*(the\s*)?previous\s*page)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["alt", "left"],
                reason="Fast-path navigate back (Alt+Left)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Navigate Back hotkey",
                answer="Going back to the previous page.",
                actions=[step]
            )

        # --- BROWSER / SYSTEM NAVIGATION: GO FORWARD ---
        if re.match(r"^(go\s*forward|forward|navigate\s*forward|next\s*page|go\s*to\s*(the\s*)?next\s*page)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["alt", "right"],
                reason="Fast-path navigate forward (Alt+Right)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Navigate Forward hotkey",
                answer="Going forward to the next page.",
                actions=[step]
            )

        # --- BROWSER / SYSTEM NAVIGATION: REFRESH / RELOAD ---
        if re.match(r"^(refresh|reload|refresh\s*(the\s*)?page|reload\s*(the\s*)?page)$", cmd):
            step = ActionStep(
                action=ActionType.PRESS_KEY,
                keys=["f5"],
                reason="Fast-path refresh page (F5)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Refresh key",
                answer="Page refreshed.",
                actions=[step]
            )

        # --- BROWSER / SYSTEM NAVIGATION: NEW TAB ---
        if re.match(r"^(new\s*tab|open\s*(a\s*)?new\s*tab)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "t"],
                reason="Fast-path open new tab (Ctrl+T)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct New Tab hotkey",
                answer="Opened a new tab.",
                actions=[step]
            )

        # --- BROWSER / SYSTEM NAVIGATION: CLOSE TAB ---
        if re.match(r"^(close\s*tab|close\s*this\s*tab|close\s*current\s*tab)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "w"],
                reason="Fast-path close tab (Ctrl+W)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct Close Tab hotkey",
                answer="Closed tab.",
                actions=[step]
            )

        # --- WINDOW / APP NAVIGATION: CLOSE WINDOW (Alt + F4) ---
        if re.match(r"^(close|quit|exit)((\s*(the|this))?\s*(window|application|app|file\s*explorer|pile\s*explorer|explorer|folder|chrome|browser)|(\s+(this|it)))?$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["alt", "f4"],
                reason="Fast-path close window (Alt+F4)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct close window hotkey",
                answer="Closing window.",
                actions=[step]
            )

        # --- OS SYSTEM NAVIGATION: FOLDERS ---
        if re.match(r"^(open|go\s*to)\s*(the\s*)?downloads(\s*folder)?$", cmd):
            step = ActionStep(
                action=ActionType.LAUNCH,
                text="shell:Downloads",
                reason="Fast-path open Downloads folder"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct open Downloads folder",
                answer="Opening Downloads folder.",
                actions=[step]
            )

        if re.match(r"^(open|go\s*to)\s*(the\s*)?documents(\s*folder)?$", cmd):
            step = ActionStep(
                action=ActionType.LAUNCH,
                text="shell:Personal",
                reason="Fast-path open Documents folder"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct open Documents folder",
                answer="Opening Documents folder.",
                actions=[step]
            )

        if re.match(r"^(open|go\s*to)\s*(the\s*)?desktop(\s*folder)?$", cmd):
            step = ActionStep(
                action=ActionType.LAUNCH,
                text="shell:Desktop",
                reason="Fast-path open Desktop folder"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct open Desktop folder",
                answer="Opening Desktop folder.",
                actions=[step]
            )

        # --- OS SYSTEM NAVIGATION: FILE EXPLORER (Win + E) ---
        if re.match(r"^(open\s*(the\s*)?)?(file\s*manager|file\s*explorer|pile\s*explorer|explorer|my\s*computer|files)$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["win", "e"],
                reason="Fast-path open File Explorer (Win+E)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct open File Explorer hotkey",
                answer="Opening File Explorer.",
                actions=[step]
            )

        # --- OS SYSTEM NAVIGATION: SETTINGS (Win + I) ---
        if re.match(r"^(open\s*(the\s*)?)?(windows\s*)?settings$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["win", "i"],
                reason="Fast-path open Windows Settings (Win+I)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct open Settings hotkey",
                answer="Opening Settings.",
                actions=[step]
            )

        # --- OS SYSTEM NAVIGATION: TASK MANAGER (Ctrl + Shift + Esc) ---
        if re.match(r"^(open\s*(the\s*)?)?task\s*manager$", cmd):
            step = ActionStep(
                action=ActionType.HOTKEY,
                keys=["ctrl", "shift", "escape"],
                reason="Fast-path open Task Manager (Ctrl+Shift+Esc)"
            )
            return ActionPlan(
                type="action",
                thought="Fast-path direct open Task Manager hotkey",
                answer="Opening Task Manager.",
                actions=[step]
            )

        # --- GENERALIZED APPS & WEBSITES LAUNCHER ---
        app_match = re.match(r"^(?:open|launch|start|go\s*to)\s+(?:the\s+)?(.+)$", cmd)
        if app_match:
            raw_target = app_match.group(1).strip()

            # Check if a browser was specified (e.g. "open youtube in chrome browser", "open github on edge")
            browser_spec = None
            browser_match = re.search(r"\s+(?:in|on|with|using)\s+(?:the\s+)?(chrome(?:\s+browser)?|google\s+chrome|edge|microsoft\s+edge|firefox|browser|web\s+browser)$", raw_target)
            if browser_match:
                b_str = browser_match.group(1).lower()
                if "chrome" in b_str:
                    browser_spec = "chrome"
                elif "edge" in b_str:
                    browser_spec = "msedge"
                elif "firefox" in b_str:
                    browser_spec = "firefox"
                else:
                    browser_spec = "default"
                target = raw_target[:browser_match.start()].strip()
            else:
                target = raw_target

            # Visual nouns and compound phrasing indicating screen interaction rather than external app launch
            ui_nouns = {
                "video", "menu", "link", "icon", "button", "dropdown", "dialog",
                "first", "second", "third", "result", "sidebar", "panel", "drawer",
                "checkbox", "item", "option", "task", "step", "press", "while", "and", "then"
            }
            target_tokens = set(re.findall(r"\b\w+\b", target))
            if not (target_tokens & ui_nouns) and len(target.split()) <= 4:
                web_tlds = [".com", ".org", ".net", ".io", ".ai", ".co", ".gov", ".edu", ".app", ".dev", ".in", ".us", ".uk", ".de"]
                is_explicit_url = target.startswith("http://") or target.startswith("https://") or target.startswith("www.") or any(tld in target for tld in web_tlds)

                # Popular web services without explicit domain
                common_web = {
                    "youtube": "https://www.youtube.com",
                    "google": "https://www.google.com",
                    "reddit": "https://www.reddit.com",
                    "github": "https://www.github.com",
                    "twitter": "https://twitter.com",
                    "x": "https://x.com",
                    "facebook": "https://www.facebook.com",
                    "instagram": "https://www.instagram.com",
                    "linkedin": "https://www.linkedin.com",
                    "netflix": "https://www.netflix.com",
                    "wikipedia": "https://www.wikipedia.org",
                    "amazon": "https://www.amazon.com",
                    "chatgpt": "https://chatgpt.com",
                }

                if target in common_web or is_explicit_url:
                    url = common_web.get(target, target if target.startswith("http") else f"https://{target}")
                    launch_payload = f"{browser_spec} {url}" if (browser_spec and browser_spec != "default") else url
                    spoken_target = target.title()
                    spoken_browser = f" in {browser_spec.title()}" if (browser_spec and browser_spec != "default") else ""
                    step = ActionStep(
                        action=ActionType.LAUNCH,
                        text=launch_payload,
                        reason=f"Universal launcher: open {target} ({launch_payload})"
                    )
                    return ActionPlan(
                        type="action",
                        thought=f"Universal launcher opening {target}",
                        answer=f"Opening {spoken_target}{spoken_browser}.",
                        actions=[step]
                    )
                else:
                    # Generalized desktop application or tool (e.g. spotify, vlc, vscode, calc, settings)
                    app_aliases = {
                        "calculator": "calc",
                        "google chrome": "chrome",
                        "browser": "chrome",
                        "web browser": "chrome",
                        "visual studio code": "code",
                        "vscode": "code",
                        "vs code": "code",
                        "text editor": "notepad",
                    }
                    target_exec = app_aliases.get(target.lower(), target)
                    friendly_name = target.title()
                    step = ActionStep(
                        action=ActionType.LAUNCH,
                        text=target_exec,
                        reason=f"Universal launcher: open application ({target_exec})"
                    )
                    return ActionPlan(
                        type="action",
                        thought=f"Universal launcher opening app {target_exec}",
                        answer=f"Opening {friendly_name}.",
                        actions=[step]
                    )

        # No direct action match -> delegate to full Vision AI Planner
        return None
