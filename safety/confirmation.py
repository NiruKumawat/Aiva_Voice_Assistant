import re
from typing import Optional, List
from computer.actions import ActionStep, ActionType
from utils.logger import logger

# Keywords indicating consequential / sensitive actions
SENSITIVE_KEYWORDS = [
    "submit", "delete", "remove", "erase", "trash", "discard",
    "pay", "purchase", "order", "buy", "checkout", "transfer", "subscribe",
    "publish", "post", "send message", "send email", "send",
    "password", "security", "credential", "reset password", "two-factor",
    "sign", "contract", "accept terms", "agree", "confirm booking"
]

AFFIRMATIVE_TERMS = [
    "yes", "yeah", "yep", "sure", "ok", "okay", "confirm", "proceed",
    "go ahead", "do it", "please do", "submit", "continue", "accept"
]

NEGATIVE_TERMS = [
    "no", "nope", "cancel", "stop", "don't", "dont", "wait", "abort",
    "never mind", "nevermind", "not yet", "hold on", "maybe"
]


class ConfirmationManager:
    """Manages sensitive action detection and user confirmation processing."""

    def is_action_sensitive(self, step: ActionStep) -> bool:
        """
        Determines whether an action has external consequences requiring confirmation.
        Only checks target description and typed text — NOT the AI's internal reasoning.
        """
        if step.sensitive:
            return True

        # PRESS_KEY, SCROLL, MOVE, WAIT, SCREENSHOT, LAUNCH, FINISH are never destructive on their own
        if step.action in (ActionType.PRESS_KEY, ActionType.SCROLL, ActionType.MOVE,
                           ActionType.WAIT, ActionType.SCREENSHOT, ActionType.FINISH, ActionType.LAUNCH):
            return False

        # 1. Target description check (Buttons / Links like "Delete Account", "Submit Payment")
        if step.target and step.target.description:
            target_desc = step.target.description.lower()
            for kw in SENSITIVE_KEYWORDS:
                if re.search(r'\b' + re.escape(kw) + r'\b', target_desc):
                    logger.info(f"Action flagged as sensitive due to keyword: '{kw}'")
                    return True

        # 2. Typed text check (passwords, credentials, destructive shell commands)
        if step.text:
            text_lower = step.text.lower()
            # Explicit credential keywords always require confirmation / masking
            cred_keywords = ["password", "secret_key", "credential", "private_key", "credit card", "two-factor", "api_key"]
            for kw in cred_keywords:
                if kw in text_lower:
                    logger.info(f"Action flagged as sensitive due to keyword: '{kw}'")
                    return True

            # Destructive terminal/database command keywords
            destructive_cmds = [r"\brm\s+-rf\b", r"\bdrop\s+database\b", r"\bdrop\s+table\b", r"\bformat\s+[a-z]:\b", r"\bdel\s+/[fsq]\b"]
            for cmd_pat in destructive_cmds:
                if re.search(cmd_pat, text_lower):
                    logger.info(f"Action flagged as sensitive due to destructive command: '{cmd_pat}'")
                    return True

            # For short phrases (< 60 chars) that are not multiline code: check general sensitive keywords
            if "\n" not in step.text and len(step.text.strip()) < 60:
                for kw in SENSITIVE_KEYWORDS:
                    if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                        logger.info(f"Action flagged as sensitive due to keyword: '{kw}'")
                        return True

        return False

    def build_confirmation_prompt(self, step: ActionStep) -> str:
        """Generates a natural confirmation question for text-to-speech."""
        target_name = step.target.description if step.target and step.target.description else "this action"
        return f"This action involves {target_name}. Should I proceed?"

    def classify_confirmation_intent(self, text: str) -> Optional[bool]:
        """
        Returns True if user unambiguously confirmed, False if rejected,
        and None if the input is unclear or unrelated.
        """
        clean = text.lower().strip()

        for neg in NEGATIVE_TERMS:
            if re.search(r'\b' + re.escape(neg) + r'\b', clean):
                logger.info(f"User rejected confirmation with: '{clean}'")
                return False

        for aff in AFFIRMATIVE_TERMS:
            if re.search(r'\b' + re.escape(aff) + r'\b', clean):
                logger.info(f"User accepted confirmation with: '{clean}'")
                return True

        logger.warning(f"Ambiguous confirmation response: '{clean}'")
        return None

    def parse_confirmation_response(self, text: str) -> Optional[bool]:
        """Convenience alias for classify_confirmation_intent."""
        return self.classify_confirmation_intent(text)

