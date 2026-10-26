import json
import re
from typing import Optional, List, Dict, Any
from groq import Groq
from config import AI_API_KEY, AI_MODEL
from capture.screen import ScreenCaptureData
from computer.actions import ActionPlan, ActionStep, ActionType, ActionTarget
from computer.grounding import UniversalTargetGrounder
from ai.prompts import ACTION_PLANNER_SYSTEM_PROMPT
from utils.logger import logger


class ActionPlanner:
    """Uses Vision AI to analyze the screen and generate structured ActionPlans."""

    def __init__(self):
        if not AI_API_KEY:
            raise ValueError("AI_API_KEY is not configured in environment.")
        self.client = Groq(api_key=AI_API_KEY)

    def generate_plan(self,
                      user_instruction: str,
                      screen_data: ScreenCaptureData,
                      history: Optional[List[Dict[str, str]]] = None) -> ActionPlan:
        """
        Sends the screenshot and user instruction to the vision model and generates a structured plan.
        """
        logger.info(f"ActionPlanner -> Planning for: '{user_instruction}' on window: '{screen_data.window_title}'")

        # Format recent history as user context rather than raw chat turns to prevent
        # the model from mimicking plain-text assistant responses
        history_context = ""
        if history:
            recent_turns = history[-4:]
            turns_text = []
            for h in recent_turns:
                role = "User" if h.get("role") == "user" else "Assistant"
                content = h.get("content", "")
                turns_text.append(f"{role}: {content}")
            if turns_text:
                history_context = "\nRecent Conversation:\n" + "\n".join(turns_text) + "\n"

        w = screen_data.bbox.get('width', screen_data.scaled_size[0])
        h = screen_data.bbox.get('height', screen_data.scaled_size[1])

        prompt_text = (
            f"Active window: {screen_data.window_title}\n"
            f"Screen Resolution: {w}x{h} px\n"
            f"Coordinate System: Standard normalized [0, 1000] scale for both width and height (X: 0=left, 1000=right; Y: 0=top, 1000=bottom edge of the captured window).\n"
            f"{history_context}\n"
            f"User instruction: {user_instruction}\n\n"
            "REMINDER: You MUST return a single JSON object. Do not include any conversational prose outside the JSON."
        )

        messages = [
            {
                "role": "system",
                "content": ACTION_PLANNER_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screen_data.image_b64}"
                        }
                    }
                ]
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"},
                timeout=20.0
            )

            raw_text = completion.choices[0].message.content.strip()
            logger.info(f"ActionPlanner -> Raw response: {raw_text}")
            return self._parse_and_map_plan(raw_text, screen_data)

        except Exception as e:
            err_msg = str(e)
            logger.error(f"ActionPlanner failed: {err_msg}")

            # If rate limited (HTTP 429), avoid useless immediate retry and report clearly
            if "429" in err_msg or "rate_limit" in err_msg.lower():
                return ActionPlan(
                    type="answer",
                    thought="Daily API token limit reached",
                    answer="The daily token limit for the AI model has been reached on the Groq free tier. Please wait about 15 minutes for the quota to reset, or update the GROQ_API_KEY in your env file."
                )

            # Check if Groq returned failed_generation in error response
            failed_text = None
            err_dict = getattr(e, 'body', None)
            if isinstance(err_dict, dict):
                failed_text = err_dict.get('error', {}).get('failed_generation')
            if not failed_text and hasattr(e, 'response'):
                try:
                    res_json = e.response.json()
                    failed_text = res_json.get('error', {}).get('failed_generation')
                except Exception:
                    pass

            if failed_text:
                logger.info(f"ActionPlanner -> Recovered failed_generation: {failed_text[:150]}")
                if "{" in failed_text and "}" in failed_text:
                    return self._parse_and_map_plan(failed_text, screen_data)
                return ActionPlan(
                    type="answer",
                    thought="Model emitted direct explanation",
                    answer=failed_text.strip()
                )

            # Retry once without response_format if json_validate_failed occurred
            try:
                logger.info("ActionPlanner -> Retrying without response_format constraint...")
                completion = self.client.chat.completions.create(
                    model=AI_MODEL,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2048
                )
                raw_text = completion.choices[0].message.content.strip()
                return self._parse_and_map_plan(raw_text, screen_data)
            except Exception as retry_err:
                logger.error(f"ActionPlanner retry also failed: {retry_err}")

            # Fallback to pure conversational answer
            return ActionPlan(
                type="answer",
                thought="Model query error",
                answer="I encountered an issue planning that action. Please try again."
            )

    def _parse_and_map_plan(self, raw_text: str, screen_data: ScreenCaptureData) -> ActionPlan:
        """Cleans, parses JSON, and maps normalized coordinates to absolute screen pixels."""
        # Clean markdown codeblocks if present
        clean_json = raw_text.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()

        # If still not starting with '{', attempt regex search for JSON object
        if not clean_json.startswith("{"):
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match:
                clean_json = match.group(0)

        try:
            data = json.loads(clean_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON plan: {e}. Fallback to plain answer.")
            return ActionPlan(type="answer", answer=raw_text)

        plan = ActionPlan.from_dict(data)

        # Map coordinates for all steps targeting screen elements using vision isotropic mapping
        for step in plan.actions:
            if step.target:
                pred_x, pred_y = None, None
                box_center_x, box_center_y = None, None

                if step.target.box_2d and len(step.target.box_2d) == 4:
                    box_center_x, box_center_y = screen_data.map_box_center(step.target.box_2d, mode="standard")

                if step.target.norm_x is not None and step.target.norm_y is not None:
                    pred_x, pred_y = screen_data.map_normalized_coords(step.target.norm_x, step.target.norm_y, mode="standard")

                # Refine coordinates using UniversalTargetGrounder (UIA exact -> Box Centroid -> Point)
                final_x, final_y, method = UniversalTargetGrounder.refine_target_coordinates(
                    target_description=step.target.description or "",
                    active_hwnd=screen_data.hwnd,
                    predicted_x=pred_x,
                    predicted_y=pred_y,
                    box_center_x=box_center_x,
                    box_center_y=box_center_y
                )
                step.target.abs_x = final_x
                step.target.abs_y = final_y
                logger.info(f"Refined target '{step.target.description}' via [{method}] -> screen ({final_x}, {final_y})")

        # Map coordinates for candidate options if type is 'clarify'
        for opt in plan.options:
            target = opt.get("target")
            if target:
                pred_x, pred_y = None, None
                box_center_x, box_center_y = None, None

                if target.box_2d and len(target.box_2d) == 4:
                    box_center_x, box_center_y = screen_data.map_box_center(target.box_2d, mode="standard")

                if target.norm_x is not None and target.norm_y is not None:
                    pred_x, pred_y = screen_data.map_normalized_coords(target.norm_x, target.norm_y, mode="standard")

                final_x, final_y, method = UniversalTargetGrounder.refine_target_coordinates(
                    target_description=opt.get("description") or target.description or "",
                    active_hwnd=screen_data.hwnd,
                    predicted_x=pred_x,
                    predicted_y=pred_y,
                    box_center_x=box_center_x,
                    box_center_y=box_center_y
                )
                target.abs_x = final_x
                target.abs_y = final_y
                logger.info(f"Refined option '{opt.get('description')}' via [{method}] -> screen ({final_x}, {final_y})")

        return plan
