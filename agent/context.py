from typing import Optional, Dict, Any, List
from computer.actions import ActionTarget, ActionStep


class AgentContext:
    """Maintains short-term target and pronoun resolution context."""

    def __init__(self):
        self.last_target: Optional[ActionTarget] = None
        self.last_action: Optional[ActionStep] = None
        self.last_window_title: str = ""
        self.recent_targets: List[ActionTarget] = []
        self.pending_clarification: Optional[Dict[str, Any]] = None

    def set_pending_clarification(self, question: str, options: List[Dict[str, Any]]):
        """Stores pending clarification options awaiting user choice."""
        self.pending_clarification = {
            "question": question,
            "options": options
        }

    def has_pending_clarification(self) -> bool:
        """Returns True if there are unresolved ambiguous candidate options."""
        return bool(self.pending_clarification and self.pending_clarification.get("options"))

    def clear_clarification(self):
        """Clears pending clarification."""
        self.pending_clarification = None

    def resolve_clarification(self, user_response: str) -> Optional[ActionTarget]:
        """
        Matches user's voice reply to one of the candidate options.
        Supports:
        - Ordinal numbers ("first", "second", "1st", "2nd", "one", "two")
        - Positional hints ("top", "bottom", "left", "right")
        - Semantic keyword matching against option descriptions ("youtube", "taskbar")
        """
        if not self.has_pending_clarification():
            return None

        text = user_response.lower().strip()
        options = self.pending_clarification.get("options", [])

        # Check cancellation
        cancel_words = ["cancel", "nevermind", "stop", "neither", "none", "no"]
        if any(w in text for w in cancel_words) and len(text.split()) <= 3:
            self.clear_clarification()
            return None

        # Check if user instruction is an independent action command (e.g. "close file explorer", "open chrome", "scroll down")
        # rather than an answer to the clarification question.
        first_word = text.split()[0] if text.split() else ""
        action_verbs = {"close", "open", "launch", "scroll", "type", "press", "write", "search", "mute", "unmute", "play", "pause"}
        ordinals_all = ["first", "1st", "second", "2nd", "third", "3rd", "fourth", "4th", "one", "two", "three", "four", "option"]
        if first_word in action_verbs and not any(k in text for k in ordinals_all):
            self.clear_clarification()
            return None

        # 1. Check direct ordinal index matching
        ordinals = [
            (["first", "1st", "number one", "option 1", "one"], 0),
            (["second", "2nd", "number two", "option 2", "two"], 1),
            (["third", "3rd", "number three", "option 3", "three"], 2),
            (["fourth", "4th", "number four", "option 4", "four"], 3)
        ]

        for keywords, idx in ordinals:
            if idx < len(options) and any(k in text for k in keywords):
                target = options[idx].get("target")
                self.clear_clarification()
                return target

        # 2. Score by token overlap with option descriptions
        user_tokens = set(text.replace(".", " ").replace(",", " ").split())
        # Filter stop words AND generic UI structural nouns (e.g. "file", "folder", "item")
        # to ensure only distinctive semantic terms match.
        stop_words = {
            "the", "a", "an", "on", "in", "to", "at", "of", "for", "with",
            "one", "click", "use", "select", "please",
            "file", "files", "folder", "folders", "item", "items", "icon", "icons",
            "button", "buttons", "link", "links", "window", "windows", "tab", "tabs",
            "app", "application", "document", "documents"
        }
        content_tokens = user_tokens - stop_words

        best_score = 0
        best_option = None

        for opt in options:
            desc = opt.get("description", "").lower()
            desc_tokens = set(desc.replace(".", " ").replace(",", " ").split()) - stop_words
            score = len(content_tokens & desc_tokens)
            if score > best_score:
                best_score = score
                best_option = opt

        if best_option and best_score > 0:
            target = best_option.get("target")
            self.clear_clarification()
            return target

        # User response did not match any options; clear single-turn clarification
        self.clear_clarification()
        return None

    def record_target(self, target: ActionTarget):
        """Records a referenced or interacted target."""
        if target:
            self.last_target = target
            self.recent_targets.append(target)
            if len(self.recent_targets) > 5:
                self.recent_targets.pop(0)

    def record_action(self, step: ActionStep, window_title: str = ""):
        """Records executed action step."""
        self.last_action = step
        if step.target:
            self.record_target(step.target)
        if window_title:
            self.last_window_title = window_title

    def resolve_pronoun_target(self, text: str) -> Optional[ActionTarget]:
        """
        If text contains references like 'click it', 'type in it', returns the most recent target.
        """
        lower = text.lower().strip()
        pronouns = [" it", " that", " this", " there", " the button", " the field"]
        if any(p in lower for p in pronouns) and self.last_target:
            return self.last_target
        return None

    def clear(self):
        """Clears context."""
        self.last_target = None
        self.last_action = None
        self.recent_targets.clear()
        self.clear_clarification()
