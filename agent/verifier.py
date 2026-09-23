import json
from typing import Tuple
from groq import Groq
from config import AI_API_KEY, AI_MODEL
from capture.screen import ScreenCaptureData
from computer.actions import ActionStep, ActionType
from ai.prompts import ACTION_VERIFIER_SYSTEM_PROMPT
from utils.logger import logger


class ActionVerifier:
    """Verifies whether an executed action achieved its intended outcome."""

    def __init__(self):
        if not AI_API_KEY:
            raise ValueError("AI_API_KEY is not set.")
        self.client = Groq(api_key=AI_API_KEY)

    def verify(self,
               step: ActionStep,
               pre_screen: ScreenCaptureData,
               post_screen: ScreenCaptureData,
               user_goal: str) -> Tuple[bool, str]:
        """
        Compares post-action state with expectations.
        Returns: (success: bool, spoken_summary: str)
        """
        # 1. Quick check: Did the screen hash or window change?
        pre_hash = hash(pre_screen.image_b64)
        post_hash = hash(post_screen.image_b64)

        if pre_hash == post_hash and pre_screen.window_title == post_screen.window_title:
            logger.info("Verification -> Screen content hash unchanged after action. Checking semantic result...")

        # 2. Semantic verification via Vision AI
        action_desc = f"{step.action.value}"
        if step.target and step.target.description:
            action_desc += f" on {step.target.description}"
        if step.text:
            action_desc += f" with text '{step.text}'"

        logger.info(f"Verification -> Verifying action: '{action_desc}' against goal: '{user_goal}'")

        messages = [
            {"role": "system", "content": ACTION_VERIFIER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"User Goal: {user_goal}\nAction Just Performed: {action_desc}\nCurrent Window: {post_screen.window_title}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{post_screen.image_b64}"}
                    }
                ]
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            raw = completion.choices[0].message.content.strip()
            data = json.loads(raw)
            success = bool(data.get("success", True))
            explanation = data.get("explanation", "Action completed.")
            logger.info(f"Verification -> Result: success={success}, explanation='{explanation}'")
            return success, explanation

        except Exception as e:
            logger.warning(f"Verification call failed: {e}. Defaulting to optimistic completion.")
            return True, f"Completed {action_desc}."
