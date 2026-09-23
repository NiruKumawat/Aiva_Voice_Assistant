import sys
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QLinearGradient


class LiveTestHUD(QWidget):
    """
    Prominent glowing On-Screen Heads-Up Display (HUD) banner.
    Floats at the top center of the screen during live test execution
    so the user can clearly see which test step is executing in real time.
    """
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        screen = QApplication.primaryScreen().availableGeometry()
        w = 580
        h = 74
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + 24
        self.setGeometry(x, y, w, h)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(2)

        self.step_label = QLabel("LIVE TEST INITIALIZING...")
        self.step_label.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold; font-family: 'Segoe UI'; letter-spacing: 1px;")
        self.step_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.step_label)

        self.desc_label = QLabel("Preparing test environment...")
        self.desc_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; font-family: 'Segoe UI';")
        self.desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.desc_label)

        self._apply_display_affinity()

    def _apply_display_affinity(self):
        try:
            import ctypes
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x00000011)
        except Exception:
            pass

    def set_step(self, step_title: str, description: str):
        self.step_label.setText(step_title.upper())
        self.desc_label.setText(description)
        self.show()
        self.raise_()
        QApplication.processEvents()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            w = self.width()
            h = self.height()

            # Glass background with gradient
            bg_grad = QLinearGradient(0, 0, w, h)
            bg_grad.setColorAt(0.0, QColor(15, 23, 42, 245))
            bg_grad.setColorAt(1.0, QColor(30, 27, 75, 245))
            painter.setBrush(QBrush(bg_grad))

            # Glowing neon border
            border_pen = QPen(QColor(56, 189, 248, 220), 1.8)
            painter.setPen(border_pen)
            painter.drawRoundedRect(1, 1, w - 2, h - 2, 14, 14)

            # Top accent highlight line
            accent_pen = QPen(QColor(168, 85, 247, 230), 2.2)
            painter.setPen(accent_pen)
            painter.drawLine(30, 2, w - 30, 2)
        finally:
            painter.end()


_hud_instance = None


def get_live_hud() -> LiveTestHUD:
    global _hud_instance
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    if _hud_instance is None:
        _hud_instance = LiveTestHUD()
    return _hud_instance
