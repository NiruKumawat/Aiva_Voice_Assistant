from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union


class ActionType(str, Enum):
    MOVE = "MOVE"
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    SCROLL = "SCROLL"
    TYPE = "TYPE"
    PRESS_KEY = "PRESS_KEY"
    HOTKEY = "HOTKEY"
    SELECT = "SELECT"
    WAIT = "WAIT"
    LAUNCH = "LAUNCH"
    SCREENSHOT = "SCREENSHOT"
    ASK_CONFIRMATION = "ASK_CONFIRMATION"
    FINISH = "FINISH"


@dataclass
class ActionTarget:
    description: str = ""
    # Normalized coords [0, 1000]
    norm_x: Optional[float] = None
    norm_y: Optional[float] = None
    # Normalized bounding box [xmin, ymin, xmax, ymax] (0-1000 scale)
    box_2d: Optional[List[float]] = None
    # Absolute screen coordinates (computed by local coordinate mapper)
    abs_x: Optional[int] = None
    abs_y: Optional[int] = None


@dataclass
class ActionStep:
    action: ActionType
    target: Optional[ActionTarget] = None
    text: Optional[str] = None
    keys: Optional[List[str]] = None
    direction: str = "down"  # "down" or "up"
    amount: int = 500
    duration: float = 0.5
    sensitive: bool = False
    reason: str = ""
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionStep":
        act_raw = str(data.get("action", "WAIT")).upper()
        try:
            act_type = ActionType(act_raw)
        except ValueError:
            act_type = ActionType.WAIT

        target_data = data.get("target")
        target_obj = None
        if isinstance(target_data, dict):
            # 1. Parse point: {"x": ..., "y": ...} or [x, y]
            point_data = target_data.get("point")
            norm_x = None
            norm_y = None
            if isinstance(point_data, dict):
                norm_x = float(point_data.get("x")) if point_data.get("x") is not None else None
                norm_y = float(point_data.get("y")) if point_data.get("y") is not None else None
            elif isinstance(point_data, (list, tuple)) and len(point_data) == 2:
                norm_x = float(point_data[0]) if point_data[0] is not None else None
                norm_y = float(point_data[1]) if point_data[1] is not None else None

            # 2. Fallback to direct x / y fields
            if norm_x is None:
                raw_x = target_data.get("x") if target_data.get("x") is not None else target_data.get("norm_x")
                norm_x = float(raw_x) if raw_x is not None else None
            if norm_y is None:
                raw_y = target_data.get("y") if target_data.get("y") is not None else target_data.get("norm_y")
                norm_y = float(raw_y) if raw_y is not None else None

            # 3. Parse box_2d [xmin, ymin, xmax, ymax]
            raw_box = target_data.get("box_2d") or target_data.get("bbox_2d")
            box_2d = None
            if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
                try:
                    box_2d = [float(v) for v in raw_box if v is not None]
                    if len(box_2d) != 4:
                        box_2d = None
                except (ValueError, TypeError):
                    box_2d = None

            # If norm_x/norm_y still None but box_2d is present: compute center from box_2d [xmin, ymin, xmax, ymax]
            if (norm_x is None or norm_y is None) and box_2d:
                xmin, ymin, xmax, ymax = box_2d
                if xmin > xmax:
                    xmin, xmax = xmax, xmin
                if ymin > ymax:
                    ymin, ymax = ymax, ymin
                norm_x = (xmin + xmax) / 2.0
                norm_y = (ymin + ymax) / 2.0

            target_obj = ActionTarget(
                description=str(target_data.get("description") or ""),
                norm_x=norm_x,
                norm_y=norm_y,
                box_2d=box_2d,
                abs_x=target_data.get("abs_x"),
                abs_y=target_data.get("abs_y")
            )
        elif isinstance(target_data, str):
            target_obj = ActionTarget(description=target_data)

        keys_val = data.get("keys")
        if isinstance(keys_val, str):
            keys_val = [k.strip() for k in keys_val.split("+")]

        # Safe numeric parsing
        amount_raw = data.get("amount")
        try:
            amount = int(amount_raw) if amount_raw is not None else 500
        except (ValueError, TypeError):
            amount = 500

        duration_raw = data.get("duration")
        try:
            duration = float(duration_raw) if duration_raw is not None else 0.5
        except (ValueError, TypeError):
            duration = 0.5

        conf_raw = data.get("confidence")
        try:
            confidence = float(conf_raw) if conf_raw is not None else 1.0
        except (ValueError, TypeError):
            confidence = 1.0

        return cls(
            action=act_type,
            target=target_obj,
            text=data.get("text"),
            keys=keys_val,
            direction=str(data.get("direction") or "down"),
            amount=amount,
            duration=duration,
            sensitive=bool(data.get("sensitive", False)),
            reason=str(data.get("reason") or ""),
            confidence=confidence
        )


@dataclass
class ActionPlan:
    type: str  # "action", "answer", or "clarify"
    thought: str = ""
    answer: Optional[str] = None
    actions: List[ActionStep] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    question: Optional[str] = None
    options: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionPlan":
        plan_type = data.get("type", "answer")
        thought = data.get("thought", "")
        answer = data.get("answer")
        question = data.get("question") or answer
        actions_list = []
        raw_actions = data.get("actions", [])
        if isinstance(raw_actions, list):
            for a in raw_actions:
                if isinstance(a, dict):
                    actions_list.append(ActionStep.from_dict(a))

        raw_options = data.get("options", [])
        options_list = []
        if isinstance(raw_options, list):
            for opt in raw_options:
                if isinstance(opt, dict):
                    t_data = opt.get("target")
                    if isinstance(t_data, dict):
                        dummy_step = ActionStep.from_dict({"action": "CLICK", "target": t_data})
                        opt_copy = dict(opt)
                        opt_copy["target"] = dummy_step.target
                        options_list.append(opt_copy)
                    else:
                        options_list.append(opt)

        return cls(
            type=plan_type,
            thought=thought,
            answer=answer,
            actions=actions_list,
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            confirmation_prompt=data.get("confirmation_prompt"),
            question=question,
            options=options_list
        )
