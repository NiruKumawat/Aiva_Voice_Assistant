"""
Universal Target Grounder.
Combines Windows UI Automation (100% exact OS bounding boxes) with Vision AI
bounding-box centroid refinement for pixel-perfect mouse targeting on low-end hardware.
Runs in <20ms with near-zero CPU/RAM overhead.
"""

import re
import math
from typing import Optional, Tuple, List, Dict, Any
from utils.logger import logger

# Lazy-loaded COM/UIA objects to prevent import latency
_UIA_CLIENT = None
_UIA_INITIALIZED = False

# Generic UI words that should never trigger a false-positive match on their own
GENERIC_UI_WORDS = {
    "icon", "button", "shortcut", "bar", "box", "link", "field", "input",
    "item", "menu", "dropdown", "tab", "label", "text", "element", "control",
    "image", "tile", "card", "view", "window", "pane", "group"
}


def _get_uia_client():
    """Lazily initializes and caches the Windows UI Automation client."""
    global _UIA_CLIENT, _UIA_INITIALIZED
    if _UIA_INITIALIZED:
        return _UIA_CLIENT

    _UIA_INITIALIZED = True
    try:
        import pythoncom
        pythoncom.CoInitialize()
        import comtypes.client
        try:
            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation
        except Exception:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation
        _UIA_CLIENT = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
        logger.info("UniversalGrounder -> Windows UIAutomation client initialized successfully.")
    except Exception as e:
        logger.warning(f"UniversalGrounder -> Could not initialize Windows UIAutomation: {e}")
        _UIA_CLIENT = None

    return _UIA_CLIENT


class UniversalTargetGrounder:
    """
    High-accuracy, lightweight coordinate refiner for mouse clicks.
    
    1. First tries Windows UI Automation for the active window (<15ms, exact pixels)
       with strict keyword filtering and visual proximity validation.
    2. Falls back to Vision Bounding Box Centroid (geometric center of detected element).
    3. Falls back to Vision Point.
    """

    @staticmethod
    def _normalize_name(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower()).strip()

    @classmethod
    def find_uia_control(cls,
                          hwnd: int,
                          target_description: str,
                          ref_x: Optional[int] = None,
                          ref_y: Optional[int] = None,
                          max_distance: float = 120.0) -> Optional[Tuple[int, int]]:
        """
        Scans the controls in the specified window for a match to the target description.
        Only matches if:
          1. Meaningful (non-generic) keywords match.
          2. The element is spatially consistent with the visual prediction (within max_distance).
        Returns (center_x, center_y) if a confident match is found, else None.
        """
        if not hwnd or hwnd <= 0 or not target_description:
            return None

        uia = _get_uia_client()
        if not uia:
            return None

        try:
            import pythoncom
            pythoncom.CoInitialize()
            from comtypes.gen.UIAutomationClient import TreeScope_Descendants

            window_element = uia.ElementFromHandle(hwnd)
            if not window_element:
                return None

            clean_target = cls._normalize_name(target_description)
            target_tokens = set(clean_target.split())
            if not target_tokens:
                return None

            # Isolate meaningful keywords (strip generic words like "icon", "button")
            meaningful_target_tokens = target_tokens - GENERIC_UI_WORDS
            if not meaningful_target_tokens:
                meaningful_target_tokens = target_tokens

            cond = uia.CreateTrueCondition()
            elements = window_element.FindAll(TreeScope_Descendants, cond)
            total = elements.Length

            best_match = None
            best_score = 0

            # Scan up to 150 elements for speed (<20ms)
            max_scan = min(total, 150)
            for i in range(max_scan):
                el = elements.GetElement(i)
                try:
                    name = el.CurrentName
                    if not name:
                        continue

                    rect = el.CurrentBoundingRectangle
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top

                    # Ignore zero-sized or invisible controls
                    if width <= 2 or height <= 2:
                        continue

                    clean_name = cls._normalize_name(name)
                    if not clean_name:
                        continue

                    name_tokens = set(clean_name.split())

                    # CRITICAL GUARD: Element must share at least one MEANINGFUL token
                    meaningful_overlap = meaningful_target_tokens & name_tokens
                    if not meaningful_overlap and clean_target != clean_name:
                        continue

                    # CRITICAL GUARD 2: In web browsers, the outer address bar is named "Address and search bar".
                    # Never let it hijack an in-page search bar unless the user explicitly said "address" or "url".
                    if "address" in clean_name and "address" not in clean_target and "url" not in clean_target:
                        continue

                    # Calculate spatial distance to vision prediction if available
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2

                    if ref_x is not None and ref_y is not None:
                        dist = math.hypot(cx - ref_x, cy - ref_y)
                        # For exact or high-confidence name matches, allow broader snap radius (up to 300px)
                        is_strong_match = (clean_target == clean_name or clean_target in clean_name or clean_name in clean_target)
                        allowed_distance = 300.0 if is_strong_match else max_distance
                        if dist > allowed_distance:
                            # Too far from where the Vision AI saw it (e.g. toolbar vs page body)
                            continue

                    # Scoring
                    if clean_target == clean_name:
                        score = 100
                    elif clean_target in clean_name:
                        score = 85
                    else:
                        score = 60 + (len(meaningful_overlap) * 15)

                    if score > best_score:
                        best_score = score
                        best_match = (cx, cy)

                        if score == 100:
                            break

                except Exception:
                    continue

            if best_match and best_score >= 75:
                logger.info(f"UniversalGrounder -> UIA matched '{target_description}' with score {best_score} at {best_match}")
                return best_match

        except Exception as e:
            logger.debug(f"UniversalGrounder -> UIA scan exception: {e}")

        return None

    @classmethod
    def refine_target_coordinates(cls,
                                  target_description: str,
                                  active_hwnd: Optional[int],
                                  predicted_x: Optional[int],
                                  predicted_y: Optional[int],
                                  box_center_x: Optional[int] = None,
                                  box_center_y: Optional[int] = None) -> Tuple[Optional[int], Optional[int], str]:
        """
        Returns (final_x, final_y, method_used).
        Prioritizes Vision Bounding Box centroid for screen elements,
        verifying with UIA only if spatially and semantically consistent.
        """
        ref_x = box_center_x if box_center_x is not None else predicted_x
        ref_y = box_center_y if box_center_y is not None else predicted_y

        # 1. Try Windows UIA only with proximity and keyword validation
        if active_hwnd and ref_x is not None and ref_y is not None:
            uia_coords = cls.find_uia_control(active_hwnd, target_description, ref_x=ref_x, ref_y=ref_y)
            if uia_coords:
                return uia_coords[0], uia_coords[1], "uia_exact"

        # 2. Prioritize Vision Bounding Box center (very high accuracy on web/desktop)
        if box_center_x is not None and box_center_y is not None:
            return box_center_x, box_center_y, "vision_box_center"

        # 3. Fallback to Vision predicted point
        if predicted_x is not None and predicted_y is not None:
            return predicted_x, predicted_y, "vision_point"

        return None, None, "unresolved"
