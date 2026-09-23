import time
import threading
from typing import Optional, Callable, Tuple
from PIL import Image
import mss

from capture.screen import ScreenCaptureData, capture_screen_detailed
from capture.window import get_active_window_info
from config import SCREEN_WATCHER_INTERVAL, ENABLE_CONTINUOUS_SCREEN_WATCHER
from utils.logger import logger


def compute_dhash(image: Image.Image, hash_size: int = 8) -> int:
    """
    Computes a fast 64-bit difference hash (dHash) for an image.
    Ultra-low CPU cost (< 0.2ms).
    """
    # Resize to (hash_size + 1, hash_size) in grayscale
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BOX)
    pixels = list(resized.getdata())
    
    # Compare adjacent pixels row by row
    diff = []
    width = hash_size + 1
    for row in range(hash_size):
        row_start = row * width
        for col in range(hash_size):
            left = pixels[row_start + col]
            right = pixels[row_start + col + 1]
            diff.append(left > right)
            
    # Convert bool list to integer
    decimal_val = 0
    for bit in diff:
        decimal_val = (decimal_val << 1) | bit
    return decimal_val


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculates bitwise difference between two 64-bit hashes."""
    return bin(hash1 ^ hash2).count("1")


class ScreenWatcher:
    """
    Ultra-lightweight background thread that monitors screen and active window changes,
    maintaining an always-ready in-memory ScreenCaptureData buffer.
    CPU usage is typically < 0.2% and consumes ZERO AI API tokens when idle.
    """

    def __init__(self,
                 interval: float = SCREEN_WATCHER_INTERVAL,
                 change_threshold: int = 4,
                 on_change_callback: Optional[Callable[[ScreenCaptureData], None]] = None):
        self.interval = max(0.5, float(interval))
        self.change_threshold = change_threshold  # Bits different in 64-bit dHash (ignores cursor blinks)
        self.on_change_callback = on_change_callback

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._latest_screen_data: Optional[ScreenCaptureData] = None
        self._last_hash: Optional[int] = None
        self._last_window_title: str = ""
        self._last_capture_time: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        """Starts the background watcher thread."""
        if not ENABLE_CONTINUOUS_SCREEN_WATCHER:
            logger.info("ScreenWatcher is disabled in config.")
            return

        if self.is_running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._watch_loop, name="ScreenWatcherThread", daemon=True)
        self._thread.start()
        logger.info(f"ScreenWatcher started (interval: {self.interval}s, threshold: {self.change_threshold} bits)")

    def stop(self, timeout: float = 2.0):
        """Stops the background watcher thread cleanly."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None
        logger.info("ScreenWatcher stopped.")

    def get_latest_screen(self) -> ScreenCaptureData:
        """
        Instantly returns the latest cached ScreenCaptureData from memory (0ms latency).
        Falls back to synchronous capture if cache is not yet warm.
        """
        with self._lock:
            if self._latest_screen_data is not None:
                return self._latest_screen_data

        # Fallback if accessed immediately upon startup before first background cycle
        logger.info("ScreenWatcher cache cold, capturing immediately on demand...")
        screen_data = capture_screen_detailed()
        with self._lock:
            self._latest_screen_data = screen_data
            self._last_window_title = screen_data.window_title
            self._last_capture_time = time.time()
        return screen_data

    def _watch_loop(self):
        """Main loop executed on background daemon thread."""
        # Initial capture on startup to warm the buffer immediately
        try:
            initial_data = capture_screen_detailed()
            with self._lock:
                self._latest_screen_data = initial_data
                self._last_window_title = initial_data.window_title
                self._last_capture_time = time.time()
        except Exception as e:
            logger.warning(f"ScreenWatcher initial capture error: {e}")

        while not self._stop_event.is_set():
            try:
                self._check_screen_change()
            except Exception as e:
                logger.debug(f"ScreenWatcher error in check: {e}")

            # Sleep in small increments for responsive stop
            self._stop_event.wait(self.interval)

    def _check_screen_change(self):
        """
        Checks active window and micro-dHash.
        Only updates high-res buffer when real changes occur.
        """
        # 1. Zero-CPU active window check via Win32
        win_info = get_active_window_info()
        current_title = win_info.get("title", "") if win_info else ""
        window_changed = (current_title != self._last_window_title and current_title != "")

        # 2. Micro-thumbnail grab for dHash comparison
        screen_changed = False
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            # Micro-thumbnail downscale: 160x90 takes < 1ms
            raw_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            thumb = raw_img.resize((160, 90), Image.Resampling.BOX)
            current_hash = compute_dhash(thumb)

        if self._last_hash is None:
            self._last_hash = current_hash
            screen_changed = True
        else:
            diff_bits = hamming_distance(self._last_hash, current_hash)
            if diff_bits >= self.change_threshold:
                screen_changed = True
                self._last_hash = current_hash

        # 3. If either window or screen content meaningfully changed, update high-res buffer
        if window_changed or screen_changed:
            new_screen_data = capture_screen_detailed()
            with self._lock:
                self._latest_screen_data = new_screen_data
                self._last_window_title = current_title
                self._last_capture_time = time.time()

            logger.debug(f"ScreenWatcher -> Screen updated. Window: '{current_title}', changed: {screen_changed}")

            if self.on_change_callback:
                try:
                    self.on_change_callback(new_screen_data)
                except Exception as cb_err:
                    logger.warning(f"ScreenWatcher on_change_callback error: {cb_err}")
