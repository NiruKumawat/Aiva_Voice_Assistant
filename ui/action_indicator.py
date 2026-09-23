import math
from typing import Optional
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QRectF, QPoint, QObject, Signal, Slot
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush
from config import SHOW_ACTION_INDICATOR
from utils.logger import logger


class ActionIndicatorBridge(QObject):
    """Thread-safe signal bridge for triggering click indicator ripples from any worker thread."""
    pulse_signal = Signal(int, int, str)


# Global bridge singleton
_bridge = ActionIndicatorBridge()
_global_indicator: Optional["ActionIndicatorWidget"] = None


class ActionIndicatorWidget(QWidget):
    """
    Ultra-sleek luminous ripple ring overlay that displays at click coordinates
    so the user can visually see where the AI assistant is interacting.
    Fully click-through (WA_TransparentForMouseEvents) and excluded from screen captures.
    """
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background: transparent;")

        self.size_box = 80
        self.setFixedSize(self.size_box, self.size_box)

        self.radius = 12.0
        self.max_radius = 34.0
        self.alpha = 240
        self.color_base = QColor(56, 189, 248)  # Glowing cyan

        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self._step_animation)

        # Exclude from DWM screen capture
        self._apply_display_affinity()

        # Connect to thread-safe bridge with QueuedConnection to guarantee execution on main GUI thread
        _bridge.pulse_signal.connect(self.pulse_at, Qt.QueuedConnection)

    def _apply_display_affinity(self):
        try:
            import ctypes
            # 1. Exclude from screen capture
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x00000011)
        except Exception:
            pass

        try:
            import win32gui, win32con
            # 2. Set Win32 transparent extended style so clicks pass 100% through to underlying desktop / apps
            hwnd = int(self.winId())
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd,
                win32con.GWL_EXSTYLE,
                ex_style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED | win32con.WS_EX_NOACTIVATE
            )
        except Exception as e:
            logger.debug(f"Action indicator Win32 transparency error: {e}")

    @Slot(int, int, str)
    def pulse_at(self, x: int, y: int, color_theme: str = "cyan"):
        if not SHOW_ACTION_INDICATOR:
            return

        try:
            if color_theme == "magenta":
                self.color_base = QColor(217, 70, 239)
            elif color_theme == "green":
                self.color_base = QColor(16, 185, 129)
            else:
                self.color_base = QColor(56, 189, 248)

            self.radius = 10.0
            self.alpha = 240

            # Center on target coordinate
            half = self.size_box // 2
            self.move(x - half, y - half)
            self.show()
            self.raise_()
            self.timer.start()
        except Exception as e:
            logger.debug(f"Action indicator pulse error: {e}")

    def _step_animation(self):
        try:
            self.radius += 2.2
            self.alpha = max(0, int(self.alpha - 18))
            if self.radius >= self.max_radius or self.alpha <= 0:
                self.timer.stop()
                self.hide()
            self.update()
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            cx = self.width() / 2.0
            cy = self.height() / 2.0

            # Outer expanding glowing ripple ring
            pen_color = QColor(self.color_base.red(), self.color_base.green(), self.color_base.blue(), self.alpha)
            pen = QPen(pen_color, 2.5, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(cx - self.radius, cy - self.radius, 2 * self.radius, 2 * self.radius))

            # Inner subtle burst
            if self.radius < 24:
                inner_r = max(2.0, self.radius * 0.45)
                inner_alpha = min(255, int(self.alpha * 0.8))
                inner_color = QColor(255, 255, 255, inner_alpha)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(inner_color))
                painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, 2 * inner_r, 2 * inner_r))
        finally:
            painter.end()


def init_action_indicator() -> Optional[ActionIndicatorWidget]:
    """
    Initializes the ActionIndicatorWidget on the main GUI thread.
    Must be called during application startup when QApplication is active.
    """
    global _global_indicator
    if not SHOW_ACTION_INDICATOR:
        return None
    if _global_indicator is None:
        try:
            app = QApplication.instance()
            if app:
                _global_indicator = ActionIndicatorWidget()
        except Exception as e:
            logger.debug(f"Could not create ActionIndicatorWidget: {e}")
    return _global_indicator


def show_click_indicator(x: int, y: int, color_theme: str = "cyan"):
    """
    Thread-safe click indicator dispatcher.
    Can be safely called from ANY thread (worker threads, executor, or main GUI thread).
    Emits a queued Qt signal to ensure the ripple is rendered on the main thread without crashing.
    """
    if not SHOW_ACTION_INDICATOR:
        return
    try:
        # If widget has not been initialized yet and we are on the main thread, initialize it
        app = QApplication.instance()
        if app and _global_indicator is None:
            import threading
            if threading.current_thread() is threading.main_thread():
                init_action_indicator()

        # Emit across threads safely
        _bridge.pulse_signal.emit(int(x), int(y), str(color_theme))
    except Exception as e:
        logger.debug(f"Action indicator emit error: {e}")
