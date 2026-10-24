import mss
from PIL import Image
import io
import base64
import ctypes
from typing import Tuple, Dict, Any, Optional
from config import CAPTURE_MODE, MAX_IMAGE_SIZE
from capture.window import get_active_window_info
from utils.logger import logger

# Ensure Per-Monitor DPI awareness is active so capture bounding boxes match physical screen pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ScreenCaptureData:
    """Detailed screen capture data with coordinate mapping context."""
    def __init__(self, 
                 image_b64: str, 
                 window_title: str, 
                 bbox: Dict[str, int], 
                 original_size: Tuple[int, int], 
                 scaled_size: Tuple[int, int],
                 hwnd: Optional[int] = None):
        self.image_b64 = image_b64
        self.window_title = window_title
        self.bbox = bbox  # {'left': l, 'top': t, 'width': w, 'height': h}
        self.original_size = original_size  # (width, height)
        self.scaled_size = scaled_size  # (width, height)
        self.hwnd = hwnd

    def map_normalized_coords(self, norm_x: float, norm_y: float, mode: str = "standard") -> Tuple[int, int]:
        """
        Maps normalized coordinates to absolute Windows screen coordinates.

        In 'vision' mode (default for all AI planner outputs):
          Uses isotropic scaling where the longest screen dimension maps to 1000.
          On a 1366x768 landscape display: X ranges [0, 1000], Y ranges [0, ~562].
          Both X and Y are converted by: abs = left/top + int((norm / 1000.0) * longest_dim)

        In 'standard' mode:
          Independent 0-1000 normalization for width and height separately.
        """
        if norm_x is None or norm_y is None:
            return self.bbox.get('left', 0), self.bbox.get('top', 0)

        w = self.bbox.get('width', 1366)
        h = self.bbox.get('height', 768)
        left = self.bbox.get('left', 0)
        top = self.bbox.get('top', 0)

        fx = float(norm_x)
        fy = float(norm_y)

        if mode == "vision":
            # Isotropic: longest dimension of the capture area maps to 1000.
            longest_dim = max(w, h)
            max_iso_y = (1000.0 * h / longest_dim) if longest_dim > 0 else 1000
            # If fy exceeds isotropic max_y + 20, the AI outputted standard 0-1000 coordinates (1000=bottom)
            if fy > (max_iso_y + 20):
                abs_x = left + int((fx / 1000.0) * w)
                abs_y = top + int((fy / 1000.0) * h)
            else:
                abs_x = left + int((fx / 1000.0) * longest_dim)
                abs_y = top + int((fy / 1000.0) * longest_dim)
        else:
            # Standard: independent 0-1000 for width and height
            abs_x = left + int((fx / 1000.0) * w)
            abs_y = top + int((fy / 1000.0) * h)

        # Strictly clamp within bounding box
        abs_x = max(left, min(abs_x, left + w))
        abs_y = max(top, min(abs_y, top + h))
        return abs_x, abs_y

    def map_box_center(self, box_2d: list, mode: str = "standard") -> Tuple[int, int]:
        """
        Maps a normalized bounding box [xmin, ymin, xmax, ymax] (0-1000 scale)
        to absolute screen coordinates of its center.
        """
        if not box_2d or len(box_2d) != 4 or any(v is None for v in box_2d):
            return self.bbox.get('left', 0), self.bbox.get('top', 0)
        try:
            xmin, ymin, xmax, ymax = [float(v) for v in box_2d]
            if xmin > xmax:
                xmin, xmax = xmax, xmin
            if ymin > ymax:
                ymin, ymax = ymax, ymin
            cx = (xmin + xmax) / 2.0
            cy = (ymin + ymax) / 2.0
            return self.map_normalized_coords(cx, cy, mode=mode)
        except Exception:
            return self.bbox.get('left', 0), self.bbox.get('top', 0)


def resize_image(image: Image.Image, max_size: tuple) -> Image.Image:
    """Resizes the image maintaining aspect ratio so it fits within max_size."""
    copy_img = image.copy()
    copy_img.thumbnail(max_size, Image.Resampling.LANCZOS)
    return copy_img


def encode_image_to_base64(image: Image.Image) -> str:
    """Converts a PIL Image to base64 string for API calls."""
    buffer = io.BytesIO()
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def capture_screen_detailed() -> ScreenCaptureData:
    """
    Captures the active window or screen with rich coordinate metadata.
    """
    import win32api
    import win32con

    screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

    with mss.mss() as sct:
        bbox = None
        window_title = "Full Screen"

        if CAPTURE_MODE == "ACTIVE_WINDOW":
            win_info = get_active_window_info()
            if win_info and win_info.get('bbox'):
                l, t, r, b = win_info['bbox']
                # Clamp to primary screen bounds to eliminate negative margins
                cl = max(0, l)
                ct = max(0, t)
                cr = min(screen_w, r)
                cb = min(screen_h, b)
                if cr > cl and cb > ct:
                    bbox = {"left": cl, "top": ct, "width": cr - cl, "height": cb - ct}
                    window_title = win_info.get('title', 'Active Window')
                else:
                    logger.warning("Invalid bounding box for active window, falling back to full screen")
            else:
                logger.warning("Could not detect active window, falling back to full screen")

        if not bbox:
            bbox = {"left": 0, "top": 0, "width": screen_w, "height": screen_h}

        logger.debug(f"Capturing: {window_title} with bounds {bbox}")
        sct_img = sct.grab(bbox)

        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        orig_size = img.size

        # Resize for AI token efficiency
        scaled_img = resize_image(img, MAX_IMAGE_SIZE)
        scaled_size = scaled_img.size

        extrema = scaled_img.getextrema()
        if extrema == ((0, 0), (0, 0), (0, 0)):
            logger.warning("Screen capture warning: All pixels are black (0,0,0). Display may be asleep, locked, or GDI DC disconnected.")

        encoded = encode_image_to_base64(scaled_img)

        # Retrieve active window HWND if available for accurate UI control matching
        active_hwnd = None
        try:
            cur_win = get_active_window_info()
            if cur_win:
                active_hwnd = cur_win.get('hwnd')
        except Exception:
            pass

        return ScreenCaptureData(
            image_b64=encoded,
            window_title=window_title,
            bbox=bbox,
            original_size=orig_size,
            scaled_size=scaled_size,
            hwnd=active_hwnd
        )


def capture_screen() -> Tuple[str, str]:
    """
    V1 Backward-Compatible wrapper.
    Returns: (base64_image, window_title)
    """
    detailed = capture_screen_detailed()
    return detailed.image_b64, detailed.window_title
