import math
import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QFrame, 
    QHBoxLayout, QScrollArea, QStackedWidget, QPushButton, 
    QApplication, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, Slot, QPoint, QPointF, QTimer, QPropertyAnimation, 
    QRect, QRectF, QEasingCurve, QSize
)
from PySide6.QtGui import (
    QFont, QColor, QPalette, QMouseEvent, QPainter, QRadialGradient, 
    QLinearGradient, QBrush, QPen, QPainterPath, QCursor
)

# --- Glassmorphic Stylesheets ---
GLASS_CARD_STYLE = """
    QFrame#GlassCard {
        background-color: qlineargradient(x1:0, y1:0, x2:0.2, y2:1, 
                                          stop:0 rgba(22, 28, 54, 235), 
                                          stop:0.4 rgba(16, 20, 42, 240), 
                                          stop:1 rgba(28, 18, 50, 235));
        border-radius: 22px;
        border: 1px solid rgba(255, 255, 255, 45);
    }
"""

MENU_ITEM_STYLE = """
    QPushButton {
        background-color: rgba(255, 255, 255, 14);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 20);
    }
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 26);
        border: 1px solid rgba(255, 255, 255, 45);
    }
    QPushButton:pressed {
        background-color: rgba(255, 255, 255, 16);
    }
"""

ACTION_BTN_STYLE = """
    QPushButton {
        background-color: rgba(255, 255, 255, 18);
        border-radius: 14px;
        padding: 8px 18px;
        color: white;
        font-family: "Segoe UI", sans-serif;
        font-size: 13px;
        font-weight: 500;
        border: 1px solid rgba(255, 255, 255, 30);
    }
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 30);
        border: 1px solid rgba(255, 255, 255, 55);
    }
    QPushButton:pressed {
        background-color: rgba(255, 255, 255, 20);
    }
"""


class VectorIconButton(QPushButton):
    """Resolution-independent, antialiased vector icon button with smooth hover effect."""
    def __init__(self, icon_type, size=34, parent=None, tooltip="", has_hover_bg=True):
        super().__init__(parent)
        self.icon_type = icon_type  # 'mic', 'chat', 'settings', 'close', 'pin', 'eye', 'waves', 'stop', 'screen', 'doc', 'cursor', 'keyboard'
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.has_hover_bg = has_hover_bg
        if tooltip:
            self.setToolTip(tooltip)
        self.is_hovered = False

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Hover circular highlight
        if self.has_hover_bg and self.is_hovered and self.icon_type != 'stop':
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 38))
            r_bg = min(self.width(), self.height()) / 2.0 - 2
            painter.drawRoundedRect(QRectF(cx - r_bg, cy - r_bg, 2 * r_bg, 2 * r_bg), r_bg, r_bg)

        # Draw crisp outline icon
        pen_color = QColor(255, 255, 255, 255 if self.is_hovered else 225)
        pen = QPen(pen_color, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self.icon_type == 'mic':
            # Capsule mic
            painter.drawRoundedRect(QRectF(cx - 3.5, cy - 8, 7, 11), 3.5, 3.5)
            # Cradle arc
            cradle = QPainterPath()
            cradle.arcMoveTo(QRectF(cx - 6.5, cy - 5, 13, 11), 0)
            cradle.arcTo(QRectF(cx - 6.5, cy - 5, 13, 11), 0, -180)
            painter.drawPath(cradle)
            # Stem and base
            painter.drawLine(QPointF(cx, cy + 6), QPointF(cx, cy + 9.5))
            painter.drawLine(QPointF(cx - 4.5, cy + 9.5), QPointF(cx + 4.5, cy + 9.5))

        elif self.icon_type == 'chat':
            # Speech bubble
            bubble = QPainterPath()
            bubble.addRoundedRect(QRectF(cx - 7.5, cy - 7, 15, 11), 3, 3)
            tail = QPainterPath()
            tail.moveTo(cx - 3, cy + 4)
            tail.lineTo(cx - 6, cy + 8)
            tail.lineTo(cx, cy + 4)
            bubble = bubble.united(tail)
            painter.drawPath(bubble)

        elif self.icon_type == 'settings':
            # 6-toothed cogwheel
            painter.drawEllipse(QPointF(cx, cy), 3.2, 3.2)
            for i in range(6):
                angle = i * (360.0 / 6)
                rad = math.radians(angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)
                p1 = QPointF(cx + 5.5 * cos_a, cy + 5.5 * sin_a)
                p2 = QPointF(cx + 7.5 * cos_a, cy + 7.5 * sin_a)
                painter.drawLine(p1, p2)
            painter.drawEllipse(QPointF(cx, cy), 5.5, 5.5)

        elif self.icon_type == 'close':
            s = 5.0
            painter.drawLine(QPointF(cx - s, cy - s), QPointF(cx + s, cy + s))
            painter.drawLine(QPointF(cx + s, cy - s), QPointF(cx - s, cy + s))

        elif self.icon_type == 'pin':
            painter.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy - 4))
            painter.drawLine(QPointF(cx, cy - 4), QPointF(cx, cy + 3))
            painter.drawLine(QPointF(cx - 2, cy + 3), QPointF(cx + 2, cy + 3))
            painter.drawLine(QPointF(cx, cy + 3), QPointF(cx, cy + 8))

        elif self.icon_type == 'eye':
            eye = QPainterPath()
            eye.moveTo(cx - 8, cy)
            eye.quadTo(cx, cy - 5.5, cx + 8, cy)
            eye.quadTo(cx, cy + 5.5, cx - 8, cy)
            painter.drawPath(eye)
            painter.drawEllipse(QPointF(cx, cy), 2.2, 2.2)

        elif self.icon_type == 'waves':
            painter.drawLine(QPointF(cx - 6, cy - 3), QPointF(cx - 6, cy + 3))
            painter.drawLine(QPointF(cx - 2, cy - 7), QPointF(cx - 2, cy + 7))
            painter.drawLine(QPointF(cx + 2, cy - 5), QPointF(cx + 2, cy + 5))
            painter.drawLine(QPointF(cx + 6, cy - 2), QPointF(cx + 6, cy + 2))

        elif self.icon_type == 'screen':
            painter.drawRoundedRect(QRectF(cx - 7, cy - 6, 14, 9), 2, 2)
            painter.drawLine(QPointF(cx, cy + 3), QPointF(cx, cy + 6))
            painter.drawLine(QPointF(cx - 4, cy + 6), QPointF(cx + 4, cy + 6))

        elif self.icon_type == 'doc':
            painter.drawRoundedRect(QRectF(cx - 5.5, cy - 7.5, 11, 15), 1.5, 1.5)
            painter.drawLine(QPointF(cx - 3, cy - 3), QPointF(cx + 3, cy - 3))
            painter.drawLine(QPointF(cx - 3, cy + 0.5), QPointF(cx + 3, cy + 0.5))
            painter.drawLine(QPointF(cx - 3, cy + 4), QPointF(cx + 1, cy + 4))

        elif self.icon_type == 'cursor':
            cur = QPainterPath()
            cur.moveTo(cx - 4, cy - 7)
            cur.lineTo(cx - 4, cy + 5)
            cur.lineTo(cx - 0.5, cy + 2)
            cur.lineTo(cx + 3.5, cy + 7)
            cur.lineTo(cx + 5.5, cy + 5.5)
            cur.lineTo(cx + 1.5, cy + 0.5)
            cur.lineTo(cx + 5, cy + 0.5)
            cur.closeSubpath()
            painter.drawPath(cur)

        elif self.icon_type == 'keyboard':
            painter.drawRoundedRect(QRectF(cx - 7.5, cy - 5, 15, 10), 2, 2)
            painter.drawLine(QPointF(cx - 4.5, cy - 2), QPointF(cx - 3.5, cy - 2))
            painter.drawLine(QPointF(cx - 0.5, cy - 2), QPointF(cx + 0.5, cy - 2))
            painter.drawLine(QPointF(cx + 3.5, cy - 2), QPointF(cx + 4.5, cy - 2))
            painter.drawLine(QPointF(cx - 3.5, cy + 2), QPointF(cx + 3.5, cy + 2))

        elif self.icon_type == 'stop':
            # Circular red glowing stop button
            r_circle = min(self.width(), self.height()) / 2.0 - 2
            grad = QRadialGradient(cx, cy, r_circle)
            if self.is_hovered:
                grad.setColorAt(0.0, QColor(248, 113, 113, 245))
                grad.setColorAt(1.0, QColor(220, 38, 38, 255))
            else:
                grad.setColorAt(0.0, QColor(239, 68, 68, 230))
                grad.setColorAt(1.0, QColor(185, 28, 28, 245))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(255, 180, 180, 140), 1.2))
            painter.drawEllipse(QPointF(cx, cy), r_circle, r_circle)

            # Center white square stop symbol
            painter.setBrush(QColor(255, 255, 255, 250))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(cx - 5, cy - 5, 10, 10), 2, 2)

        painter.end()


class GlowingOrb(QWidget):
    """Iridescent multi-layer luminous AI gem/orb with live shimmer and breathing animation."""
    def __init__(self, size=32, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.color_theme = "ai"  # 'ai', 'listening', 'processing', 'speaking', 'ready'
        self.color = QColor(0, 150, 255)
        self.shimmer_phase = 0.0

        # Continuous smooth shimmer animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(30)
        self.anim_timer.timeout.connect(self._tick_anim)
        self.anim_timer.start()

    def _tick_anim(self):
        self.shimmer_phase += 0.05
        self.update()

    def set_theme(self, theme):
        self.color_theme = theme
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        r = min(w, h) / 2.0 - 2.5

        # 1. Outer ambient glow halo
        halo_grad = QRadialGradient(cx, cy, r + 4)
        halo_alpha = int(95 + math.sin(self.shimmer_phase * 1.5) * 30)

        if self.color_theme == "listening":
            halo_grad.setColorAt(0.0, QColor(244, 63, 94, halo_alpha + 30))
            halo_grad.setColorAt(0.7, QColor(236, 72, 153, 50))
        elif self.color_theme == "processing":
            halo_grad.setColorAt(0.0, QColor(6, 182, 212, halo_alpha + 30))
            halo_grad.setColorAt(0.7, QColor(59, 130, 246, 50))
        elif self.color_theme == "speaking":
            halo_grad.setColorAt(0.0, QColor(168, 85, 247, halo_alpha + 30))
            halo_grad.setColorAt(0.7, QColor(139, 92, 246, 50))
        elif self.color_theme == "executing":
            halo_grad.setColorAt(0.0, QColor(16, 185, 129, halo_alpha + 35))
            halo_grad.setColorAt(0.7, QColor(5, 150, 105, 55))
        elif self.color_theme == "verifying":
            halo_grad.setColorAt(0.0, QColor(14, 165, 233, halo_alpha + 30))
            halo_grad.setColorAt(0.7, QColor(6, 182, 212, 50))
        elif self.color_theme == "confirmation":
            halo_grad.setColorAt(0.0, QColor(245, 158, 11, halo_alpha + 40))
            halo_grad.setColorAt(0.7, QColor(217, 119, 6, 60))
        elif self.color_theme == "stopped":
            halo_grad.setColorAt(0.0, QColor(239, 68, 68, halo_alpha + 30))
            halo_grad.setColorAt(0.7, QColor(185, 28, 28, 50))
        else:  # AI Multi-color / ready
            halo_grad.setColorAt(0.0, QColor(168, 85, 247, halo_alpha))
            halo_grad.setColorAt(0.6, QColor(56, 189, 248, 60))
        halo_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(halo_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), r + 3, r + 3)

        # 2. Main sphere gradient with live shimmering focal center
        shift_x = math.cos(self.shimmer_phase) * (r * 0.12)
        shift_y = math.sin(self.shimmer_phase) * (r * 0.12)
        sphere_grad = QRadialGradient(cx - r * 0.25 + shift_x, cy - r * 0.25 + shift_y, r * 1.3)

        if self.color_theme == "listening":
            sphere_grad.setColorAt(0.0, QColor(254, 205, 211))
            sphere_grad.setColorAt(0.4, QColor(244, 63, 94))
            sphere_grad.setColorAt(0.8, QColor(190, 18, 60))
            sphere_grad.setColorAt(1.0, QColor(88, 28, 135))
        elif self.color_theme == "processing":
            sphere_grad.setColorAt(0.0, QColor(207, 250, 254))
            sphere_grad.setColorAt(0.4, QColor(6, 182, 212))
            sphere_grad.setColorAt(0.8, QColor(37, 99, 235))
            sphere_grad.setColorAt(1.0, QColor(30, 27, 75))
        elif self.color_theme == "speaking":
            sphere_grad.setColorAt(0.0, QColor(243, 232, 255))
            sphere_grad.setColorAt(0.4, QColor(168, 85, 247))
            sphere_grad.setColorAt(0.8, QColor(109, 40, 217))
            sphere_grad.setColorAt(1.0, QColor(30, 27, 75))
        elif self.color_theme == "executing":
            sphere_grad.setColorAt(0.0, QColor(209, 250, 229))
            sphere_grad.setColorAt(0.4, QColor(16, 185, 129))
            sphere_grad.setColorAt(0.8, QColor(4, 120, 87))
            sphere_grad.setColorAt(1.0, QColor(6, 78, 59))
        elif self.color_theme == "verifying":
            sphere_grad.setColorAt(0.0, QColor(224, 242, 254))
            sphere_grad.setColorAt(0.4, QColor(14, 165, 233))
            sphere_grad.setColorAt(0.8, QColor(3, 105, 161))
            sphere_grad.setColorAt(1.0, QColor(12, 74, 110))
        elif self.color_theme == "confirmation":
            sphere_grad.setColorAt(0.0, QColor(254, 243, 199))
            sphere_grad.setColorAt(0.4, QColor(245, 158, 11))
            sphere_grad.setColorAt(0.8, QColor(180, 83, 9))
            sphere_grad.setColorAt(1.0, QColor(120, 53, 15))
        elif self.color_theme == "stopped":
            sphere_grad.setColorAt(0.0, QColor(254, 226, 226))
            sphere_grad.setColorAt(0.4, QColor(239, 68, 68))
            sphere_grad.setColorAt(0.8, QColor(185, 28, 28))
            sphere_grad.setColorAt(1.0, QColor(127, 29, 29))
        else:  # Ethereal AI Galaxy/Gemini iridescent gradient
            sphere_grad.setColorAt(0.0, QColor(224, 242, 254))
            sphere_grad.setColorAt(0.25, QColor(56, 189, 248))
            sphere_grad.setColorAt(0.65, QColor(147, 51, 234))
            sphere_grad.setColorAt(0.88, QColor(219, 39, 119))
            sphere_grad.setColorAt(1.0, QColor(30, 27, 75))

        painter.setBrush(QBrush(sphere_grad))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 3. Outer rim glass shine
        painter.setPen(QPen(QColor(255, 255, 255, 150), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 4. Top specular highlight
        hl_x = cx - r * 0.35 + shift_x * 0.5
        hl_y = cy - r * 0.35 + shift_y * 0.5
        highlight = QRadialGradient(hl_x, hl_y, r * 0.55)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 240))
        highlight.setColorAt(0.6, QColor(255, 255, 255, 90))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(hl_x, hl_y), r * 0.45, r * 0.35)

        painter.end()


class ClickableFrame(QFrame):
    """Frame that emits a signal on click."""
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AudioWaveformWidget(QWidget):
    """Animated glowing audio waveform visualizer for active listening."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _tick(self):
        self.phase += 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        bars = 16
        spacing = 5.0
        total_w = bars * spacing
        start_x = cx - total_w / 2.0

        for i in range(bars):
            val = math.sin(self.phase + i * 0.5)
            h = 4.0 + abs(val) * 13.0
            x = start_x + i * spacing
            alpha = int(120 + abs(val) * 135)
            painter.setPen(QPen(QColor(56, 189, 248, alpha), 2.2, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(x, cy - h / 2.0), QPointF(x, cy + h / 2.0))

        painter.end()


class SidebarCollapsedView(QWidget):
    """Exact collapsed floating pill sidebar with Frosted Glass effect and Live Sonar Wave Animations."""
    def __init__(self, parent_window):
        super().__init__()
        self.main_win = parent_window
        self.setFixedSize(116, 254)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self.anim_time = 0.0

        # Live animation loop (35 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(28)
        self.anim_timer.timeout.connect(self._tick_anim)
        self.anim_timer.start()

        # Floating Pill Container with Frosted Glass styling
        self.pill = ClickableFrame(self)
        self.pill.setGeometry(54, 12, 50, 230)
        self.pill.setObjectName("EdgePill")
        self.pill.setCursor(Qt.PointingHandCursor)
        self.pill.clicked.connect(self.main_win.show_menu)
        self.pill.setStyleSheet("""
            QFrame#EdgePill {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 rgba(28, 36, 70, 215),
                                                  stop:0.5 rgba(18, 22, 46, 225),
                                                  stop:1 rgba(34, 22, 58, 215));
                border-radius: 25px;
                border: 1px solid rgba(255, 255, 255, 55);
            }
        """)

        layout = QVBoxLayout(self.pill)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Glowing Orb
        self.orb = GlowingOrb(28)
        layout.addWidget(self.orb, alignment=Qt.AlignCenter)

        # 2. "AI" Text Label
        lbl_ai = QLabel("AI")
        lbl_ai.setStyleSheet("color: #ffffff; font-family: 'Segoe UI', sans-serif; font-weight: 700; font-size: 13px; letter-spacing: 1px;")
        lbl_ai.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_ai)

        # 3. Horizontal Divider
        div = QFrame()
        div.setFixedSize(18, 2)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 80); border-radius: 1px;")
        layout.addWidget(div, alignment=Qt.AlignCenter)

        # 4. Action Buttons
        self.btn_mic = VectorIconButton('mic', 34, tooltip="Voice Assistant (Click to Speak)")
        self.btn_mic.clicked.connect(self.main_win._btn_start)

        self.btn_chat = VectorIconButton('chat', 34, tooltip="AI Assistant Menu")
        self.btn_chat.clicked.connect(self.main_win.show_menu)

        self.btn_settings = VectorIconButton('settings', 34, tooltip="Settings")
        self.btn_settings.clicked.connect(self.main_win._btn_settings)

        layout.addWidget(self.btn_mic, alignment=Qt.AlignCenter)
        layout.addWidget(self.btn_chat, alignment=Qt.AlignCenter)
        layout.addWidget(self.btn_settings, alignment=Qt.AlignCenter)

    def _tick_anim(self):
        self.anim_time += 0.04
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.main_win.show_menu()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Center of the pill capsule
        pcx = 54.0 + 25.0
        pcy = 12.0 + 115.0

        # 1. Ambient aura glow directly behind the pill with living breathing pulse
        breath = math.sin(self.anim_time * 1.2) * 0.15

        # Top-left cyan aura
        cyan_r = 65 * (1.0 + breath)
        cyan_glow = QRadialGradient(pcx - 10, pcy - 40, cyan_r)
        cyan_glow.setColorAt(0.0, QColor(56, 189, 248, int(75 + breath * 30)))
        cyan_glow.setColorAt(0.5, QColor(14, 165, 233, 25))
        cyan_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(cyan_glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(pcx - 10, pcy - 40), cyan_r, cyan_r)

        # Bottom-right magenta aura
        magenta_r = 70 * (1.0 - breath)
        magenta_glow = QRadialGradient(pcx + 10, pcy + 45, magenta_r)
        magenta_glow.setColorAt(0.0, QColor(217, 70, 239, int(80 - breath * 30)))
        magenta_glow.setColorAt(0.5, QColor(168, 85, 247, 30))
        magenta_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(magenta_glow))
        painter.drawEllipse(QPointF(pcx + 10, pcy + 45), magenta_r, magenta_r)

        # 2. Live animated concentric sonar ripple waves radiating outward to the left
        num_waves = 3
        for i in range(num_waves):
            phase = (self.anim_time * 0.75 + i * (1.0 / num_waves)) % 1.0
            r = 44.0 + phase * 54.0
            
            fade = math.sin(phase * math.pi)
            alpha = int(fade * 85)
            pen_w = 2.0 - phase * 0.8

            pen_arc = QPen(QColor(56, 189, 248, alpha), pen_w)
            pen_arc.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_arc)
            painter.setBrush(Qt.NoBrush)

            start_angle = int((115 + phase * 6) * 16)
            span_angle = int((130 - phase * 14) * 16)
            painter.drawArc(QRectF(pcx - r, pcy - r, 2 * r, 2 * r), start_angle, span_angle)

        # 3. Frosted Glass Diagonal Sheen across the top of the pill
        glass_shine = QLinearGradient(54, 12, 54 + 50, 12 + 80)
        glass_shine.setColorAt(0.0, QColor(255, 255, 255, 40))
        glass_shine.setColorAt(0.4, QColor(255, 255, 255, 12))
        glass_shine.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glass_shine))
        painter.setPen(Qt.NoPen)

        shine_path = QPainterPath()
        shine_path.addRoundedRect(QRectF(54, 12, 50, 80), 25, 25)
        painter.drawPath(shine_path)

        painter.end()


class MainWindow(QMainWindow):
    # Main App Signals
    update_status_signal = Signal(str)
    update_window_signal = Signal(str)
    update_question_signal = Signal(str)
    update_answer_signal = Signal(str)

    # Audio Signals
    play_audio_signal = Signal(str)
    tts_play_signal = Signal()
    play_ui_sound_signal = Signal(str)

    # Input Signals
    start_listening_signal = Signal()
    hotkey_signal = Signal()
    hotkey_vision_signal = Signal()
    open_settings_signal = Signal()

    # V2 Computer Control Signals
    show_confirmation_signal = Signal(str)
    hide_confirmation_signal = Signal()
    confirm_action_signal = Signal()
    cancel_action_signal = Signal()
    emergency_stop_signal = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self.current_state = "COLLAPSED"  # COLLAPSED, MENU, ACTIVE

        # Auto-hide timer for active card
        self.hide_timer = QTimer(self)
        self.hide_timer.setInterval(10000)
        self.hide_timer.timeout.connect(self.show_collapsed)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(280)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        self.init_ui()
        self.connect_signals()

        # Place immediately at the right screen edge in collapsed state
        screen = QApplication.primaryScreen().availableGeometry()
        init_x = screen.x() + screen.width() - 116
        init_y = screen.y() + (screen.height() - 254) // 2
        self.setGeometry(init_x, init_y, 116, 254)
        self.show_collapsed()

        # Ensure assistant window is excluded from all screen captures via Windows DWM
        self._apply_display_affinity()

    def _apply_display_affinity(self):
        try:
            import ctypes
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x00000011)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_display_affinity()

    def init_ui(self):
        self.central = QWidget()
        self.central.setObjectName("CentralWidget")
        self.central.setStyleSheet("QWidget#CentralWidget { background: transparent; }")
        self.setCentralWidget(self.central)

        main_layout = QVBoxLayout(self.central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # --- View 0: Exact Collapsed Edge Pill ---
        self.view_collapsed = SidebarCollapsedView(self)
        self.mini_orb = self.view_collapsed.orb

        # --- View 1: Main Menu Card ---
        self.view_menu = QFrame()
        self.view_menu.setObjectName("GlassCard")
        self.view_menu.setStyleSheet(GLASS_CARD_STYLE)

        m_layout = QVBoxLayout(self.view_menu)
        m_layout.setContentsMargins(18, 16, 18, 18)
        m_layout.setSpacing(8)

        # Top Bar (Pin + Close)
        m_topbar = QHBoxLayout()
        btn_pin = VectorIconButton('pin', 28, tooltip="Pin")
        btn_close_menu = VectorIconButton('close', 28, tooltip="Hide to Edge")
        btn_close_menu.clicked.connect(self.show_collapsed)
        m_topbar.addWidget(btn_pin)
        m_topbar.addStretch()
        m_topbar.addWidget(btn_close_menu)
        m_layout.addLayout(m_topbar)

        # Header with Glowing Orb
        m_header = QHBoxLayout()
        self.menu_orb = GlowingOrb(42)
        m_header.addWidget(self.menu_orb)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("AI Assistant")
        title_lbl.setStyleSheet("color: white; font-size: 17px; font-weight: bold; font-family: 'Segoe UI';")
        sub_lbl = QLabel("Listen • Understand • Assist")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'Segoe UI';")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        m_header.addLayout(title_box)
        m_header.addStretch()
        m_layout.addLayout(m_header)

        # Divider
        div_m = QFrame()
        div_m.setFixedHeight(1)
        div_m.setStyleSheet("background-color: rgba(255, 255, 255, 30); border: none;")
        m_layout.addWidget(div_m)

        # Menu Action Buttons with Vector Icons & Protected Label Height
        self._add_menu_btn(m_layout, 'mic', "Start", "Begin voice assistant", self._btn_start)
        self._add_menu_btn(m_layout, 'stop', "Stop", "Emergency stop (ESC)", self._btn_stop)
        self._add_menu_btn(m_layout, 'eye', "Hide", "Minimize to edge", self.show_collapsed)
        self._add_menu_btn(m_layout, 'screen', "Ask About Screen", "Understand what's on screen", self._btn_vision)
        self._add_menu_btn(m_layout, 'doc', "Summarize Page", "Get instant summary", self._btn_vision)
        self._add_menu_btn(m_layout, 'cursor', "Click & Navigate", "Control mouse and screen", self._btn_vision)
        self._add_menu_btn(m_layout, 'keyboard', "Type & Shortcut", "Type text and hotkeys", self._btn_vision)
        self._add_menu_btn(m_layout, 'settings', "Settings", "Customize your assistant", self._btn_settings)

        # Footer Quote
        quote_lbl = QLabel("“Smarter days start with a simple voice.”")
        quote_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic; font-family: 'Segoe UI';")
        quote_lbl.setAlignment(Qt.AlignCenter)
        m_layout.addWidget(quote_lbl)

        # --- View 2: Active Chat / Listening Card ---
        self.view_active = QFrame()
        self.view_active.setObjectName("GlassCard")
        self.view_active.setStyleSheet(GLASS_CARD_STYLE)

        a_layout = QVBoxLayout(self.view_active)
        a_layout.setContentsMargins(18, 16, 18, 18)
        a_layout.setSpacing(10)

        # Top Bar
        a_topbar = QHBoxLayout()
        btn_waves = VectorIconButton('waves', 28, tooltip="Listening indicator")
        btn_close_active = VectorIconButton('close', 28, tooltip="Hide to Edge")
        btn_close_active.clicked.connect(self.show_collapsed)
        a_topbar.addWidget(btn_waves)
        a_topbar.addStretch()
        a_topbar.addWidget(btn_close_active)
        a_layout.addLayout(a_topbar)

        # Center Orb
        orb_container = QHBoxLayout()
        self.active_orb = GlowingOrb(84)
        orb_container.addStretch()
        orb_container.addWidget(self.active_orb)
        orb_container.addStretch()
        a_layout.addLayout(orb_container)

        # Status & Subtitle
        self.status_label = QLabel("Listening...")
        self.status_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold; font-family: 'Segoe UI';")
        self.status_label.setAlignment(Qt.AlignCenter)
        a_layout.addWidget(self.status_label)

        self.window_label = QLabel("Speak now")
        self.window_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-family: 'Segoe UI';")
        self.window_label.setAlignment(Qt.AlignCenter)
        a_layout.addWidget(self.window_label)

        # Waveform Visualizer
        self.waveform = AudioWaveformWidget()
        a_layout.addWidget(self.waveform)

        # Scroll Area for Questions and Answers
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(8)

        self.question_text = QLabel('“What can I help you with?”')
        self.question_text.setWordWrap(True)
        self.question_text.setStyleSheet("color: rgba(186, 230, 253, 0.95); font-size: 14px; font-style: italic; font-family: 'Segoe UI';")
        self.question_text.setAlignment(Qt.AlignCenter)

        self.answer_text = QLabel("")
        self.answer_text.setWordWrap(True)
        self.answer_text.setStyleSheet("color: #ffffff; font-size: 14px; line-height: 1.4; font-family: 'Segoe UI';")
        self.answer_text.setAlignment(Qt.AlignCenter)

        scroll_layout.addWidget(self.question_text)
        scroll_layout.addWidget(self.answer_text)
        scroll_layout.addStretch()

        self.scroll_area.setWidget(scroll_content)
        a_layout.addWidget(self.scroll_area)

        # Confirmation Card (Hidden by default, shown during sensitive action confirmation)
        self.confirm_frame = QFrame()
        self.confirm_frame.setObjectName("ConfirmCard")
        self.confirm_frame.setStyleSheet("""
            QFrame#ConfirmCard {
                background-color: rgba(245, 158, 11, 0.18);
                border: 1px solid rgba(245, 158, 11, 0.65);
                border-radius: 14px;
            }
        """)
        cf_layout = QVBoxLayout(self.confirm_frame)
        cf_layout.setContentsMargins(12, 10, 12, 10)
        cf_layout.setSpacing(8)

        cf_badge = QLabel("⚠️ SENSITIVE ACTION CONFIRMATION")
        cf_badge.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: 700; font-family: 'Segoe UI';")
        cf_badge.setAlignment(Qt.AlignCenter)
        cf_layout.addWidget(cf_badge)

        self.confirm_prompt = QLabel("")
        self.confirm_prompt.setWordWrap(True)
        self.confirm_prompt.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; font-family: 'Segoe UI';")
        self.confirm_prompt.setAlignment(Qt.AlignCenter)
        cf_layout.addWidget(self.confirm_prompt)

        cf_btn_box = QHBoxLayout()
        cf_btn_box.setSpacing(10)
        cf_btn_box.setAlignment(Qt.AlignCenter)

        btn_confirm = QPushButton("Confirm (Yes)")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.35);
                border: 1px solid rgba(16, 185, 129, 0.8);
                color: #ecfdf5;
                font-weight: 600;
                font-size: 12px;
                border-radius: 10px;
                padding: 6px 14px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.55);
                color: white;
            }
        """)
        btn_confirm.clicked.connect(self.confirm_action_signal.emit)

        btn_cancel = QPushButton("Cancel (No)")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                border: 1px solid rgba(239, 68, 68, 0.8);
                color: #fef2f2;
                font-weight: 600;
                font-size: 12px;
                border-radius: 10px;
                padding: 6px 14px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        btn_cancel.clicked.connect(self.cancel_action_signal.emit)

        cf_btn_box.addWidget(btn_confirm)
        cf_btn_box.addWidget(btn_cancel)
        cf_layout.addLayout(cf_btn_box)

        self.confirm_frame.setVisible(False)
        a_layout.addWidget(self.confirm_frame)

        # Suggestion Pill
        self.suggestion_pill = QPushButton('Try: "Summarize this page"')
        self.suggestion_pill.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 14);
                border-radius: 12px;
                padding: 6px 14px;
                color: #e2e8f0;
                font-family: 'Segoe UI';
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 28);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 28);
                color: white;
            }
        """)
        self.suggestion_pill.setCursor(Qt.PointingHandCursor)
        self.suggestion_pill.clicked.connect(self._btn_vision)
        a_layout.addWidget(self.suggestion_pill, alignment=Qt.AlignCenter)

        # Action Buttons (Hide, Stop, Settings)
        a_actions = QHBoxLayout()
        a_actions.setSpacing(14)
        a_actions.setAlignment(Qt.AlignCenter)

        btn_act_hide = QPushButton("Hide")
        btn_act_hide.setStyleSheet(ACTION_BTN_STYLE)
        btn_act_hide.clicked.connect(self.show_collapsed)

        btn_act_stop = VectorIconButton('stop', 44, tooltip="Emergency Stop (ESC)", has_hover_bg=False)
        btn_act_stop.clicked.connect(self._btn_stop)

        btn_act_settings = QPushButton("Settings")
        btn_act_settings.setStyleSheet(ACTION_BTN_STYLE)
        btn_act_settings.clicked.connect(self._btn_settings)

        a_actions.addWidget(btn_act_hide)
        a_actions.addWidget(btn_act_stop)
        a_actions.addWidget(btn_act_settings)
        a_layout.addLayout(a_actions)

        # Footer Quote
        quote_act = QLabel("“Your voice makes it happen.”")
        quote_act.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic; font-family: 'Segoe UI';")
        quote_act.setAlignment(Qt.AlignCenter)
        a_layout.addWidget(quote_act)

        # Add Views to Stack
        self.stack.addWidget(self.view_collapsed)
        self.stack.addWidget(self.view_menu)
        self.stack.addWidget(self.view_active)

        main_layout.addWidget(self.stack)

    def _add_menu_btn(self, layout, icon_type, title, desc, callback):
        btn = QPushButton()
        btn.setStyleSheet(MENU_ITEM_STYLE)
        btn.setFixedHeight(48)
        btn.setCursor(Qt.PointingHandCursor)

        b_layout = QHBoxLayout(btn)
        b_layout.setContentsMargins(12, 4, 12, 4)
        b_layout.setSpacing(10)

        # Vector Icon
        icon_w = VectorIconButton(icon_type, 26, has_hover_bg=False)
        icon_w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        b_layout.addWidget(icon_w)

        # Text Box with safe descender heights
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        t_lbl = QLabel(title)
        t_lbl.setFixedHeight(18)
        t_lbl.setStyleSheet("color: white; font-weight: 600; font-size: 13px; background: transparent; font-family: 'Segoe UI';")
        d_lbl = QLabel(desc)
        d_lbl.setFixedHeight(16)
        d_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent; font-family: 'Segoe UI';")
        text_box.addWidget(t_lbl)
        text_box.addWidget(d_lbl)
        b_layout.addLayout(text_box)
        b_layout.addStretch()

        if callback:
            btn.clicked.connect(callback)
        layout.addWidget(btn)

    def connect_signals(self):
        self.update_status_signal.connect(self.set_status)
        self.update_window_signal.connect(self.set_window)
        self.update_question_signal.connect(self.set_question)
        self.update_answer_signal.connect(self.set_answer)
        self.show_confirmation_signal.connect(self.show_confirmation)
        self.hide_confirmation_signal.connect(self.hide_confirmation)
        self.hotkey_signal.connect(self.show_active)
        self.hotkey_vision_signal.connect(self.show_active)

    # --- Actions ---
    def _btn_start(self):
        self.hotkey_signal.emit()

    def _btn_vision(self):
        self.hotkey_vision_signal.emit()

    def _btn_stop(self):
        self.emergency_stop_signal.emit()

    def _btn_settings(self):
        self.open_settings_signal.emit()

    # --- Confirmation UI Slots ---
    @Slot(str)
    def show_confirmation(self, prompt_text: str):
        self.confirm_prompt.setText(prompt_text)
        self.confirm_frame.setVisible(True)
        self.show_active()

    @Slot()
    def hide_confirmation(self):
        self.confirm_frame.setVisible(False)

    # --- View Transitions ---
    def _animate_to(self, width, height, idx):
        # 1. Update size policies so inactive views do not restrict or force larger window bounds
        views = [self.view_collapsed, self.view_menu, self.view_active]
        for i, view in enumerate(views):
            if i == idx:
                view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                view.setMaximumSize(width, height)
            else:
                view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                view.setMaximumSize(0, 0)

        self.stack.setCurrentIndex(idx)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        screen = QApplication.primaryScreen().availableGeometry()

        if idx == 0:
            target_x = screen.x() + screen.width() - width
            target_y = screen.y() + (screen.height() - height) // 2
        else:
            target_x = screen.x() + screen.width() - width - 16
            target_y = screen.y() + (screen.height() - height) // 2

        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(QRect(target_x, target_y, width, height))
        self.animation.start()

    @Slot()
    def show_collapsed(self):
        self.current_state = "COLLAPSED"
        self._animate_to(116, 254, 0)
        self.hide_timer.stop()

    @Slot()
    def show_menu(self):
        self.current_state = "MENU"
        self._animate_to(330, 580, 1)
        self.hide_timer.stop()

    @Slot()
    def show_active(self):
        self.current_state = "ACTIVE"
        self._animate_to(350, 640, 2)

    # --- Data Updates ---
    @Slot(str)
    def set_status(self, status):
        self.status_label.setText(status)
        status_lower = status.lower()

        if any(k in status_lower for k in ["executing", "action", "typing", "clicking", "scroll", "navigat"]):
            theme = "executing"
            self.hide_timer.stop()
        elif "verifying" in status_lower:
            theme = "verifying"
            self.hide_timer.stop()
        elif "confirm" in status_lower:
            theme = "confirmation"
            self.hide_timer.stop()
        elif "stop" in status_lower:
            theme = "stopped"
            if self.current_state == "ACTIVE":
                self.hide_timer.start()
        elif "ready" in status_lower:
            theme = "ready"
            if self.current_state == "ACTIVE":
                self.hide_timer.start()
        elif "listening" in status_lower:
            theme = "listening"
            self.hide_timer.stop()
        elif any(k in status_lower for k in ["processing", "thinking", "transcribing", "planning", "observing"]):
            theme = "processing"
            self.hide_timer.stop()
        elif "speaking" in status_lower:
            theme = "speaking"
            self.hide_timer.stop()
        else:
            theme = "ai"

        self.mini_orb.set_theme(theme)
        self.menu_orb.set_theme(theme)
        self.active_orb.set_theme(theme)

    @Slot(str)
    def set_window(self, window_name):
        max_len = 35
        if len(window_name) > max_len:
            window_name = window_name[:max_len] + "..."
        self.window_label.setText(window_name)

    @Slot(str)
    def set_question(self, question):
        self.question_text.setText(f'“{question}”' if question else '“What can I help you with?”')

    @Slot(str)
    def set_answer(self, answer):
        self.answer_text.setText(answer if answer else "")
