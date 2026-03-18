from __future__ import annotations

import time

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QCursor, QPainter, QPen, QRadialGradient
from PyQt5.QtWidgets import QWidget


class MouseHighlightOverlay(QWidget):
    """Transparent overlay that renders a soft cursor halo."""

    def __init__(
        self,
        diameter: int = 84,
        ring_thickness: int = 4,
        opacity: int = 70,
        color: str = "#F6C445",
    ) -> None:
        super().__init__(None)
        self._diameter = 84
        self._ring_thickness = 4
        self._opacity = 70
        self._color = QColor("#F6C445")
        self._click_effects_enabled = True
        self._pulse_duration = 0.32
        self._pulses: list[tuple[float, str]] = []
        self.apply_style(
            diameter=diameter,
            ring_thickness=ring_thickness,
            opacity=opacity,
            color=color,
        )

        flags = (
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.BypassWindowManagerHint
        )
        # Ensure overlay never captures input from underlying windows.
        if hasattr(Qt, "WindowDoesNotAcceptFocus"):
            flags |= Qt.WindowDoesNotAcceptFocus
        if hasattr(Qt, "WindowTransparentForInput"):
            flags |= Qt.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        if hasattr(Qt, "WA_X11DoNotAcceptFocus"):
            self.setAttribute(Qt.WA_X11DoNotAcceptFocus, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._sync_position)

    def apply_style(
        self,
        diameter: int,
        ring_thickness: int,
        opacity: int,
        color: str,
    ) -> None:
        self._diameter = max(40, min(200, int(diameter)))
        self._ring_thickness = max(2, min(16, int(ring_thickness)))
        self._opacity = max(10, min(100, int(opacity)))
        parsed = QColor(color)
        self._color = parsed if parsed.isValid() else QColor("#F6C445")
        self.resize(self._diameter, self._diameter)
        if self.isVisible():
            self._sync_position()
            self.update()

    def set_click_effects_enabled(self, enabled: bool) -> None:
        self._click_effects_enabled = bool(enabled)
        if not self._click_effects_enabled:
            self._pulses.clear()
            self.update()

    def trigger_click_effect(self, button: str = "left") -> None:
        if not self._click_effects_enabled:
            return
        self._pulses.append((time.monotonic(), button))
        if len(self._pulses) > 8:
            self._pulses = self._pulses[-8:]
        self.update()

    def start(self) -> None:
        self._sync_position()
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._pulses.clear()
        self.hide()

    def _sync_position(self) -> None:
        if self._pulses:
            now = time.monotonic()
            self._pulses = [
                (started_at, button)
                for started_at, button in self._pulses
                if now - started_at <= self._pulse_duration
            ]
        cursor_pos = QCursor.pos()
        self.move(cursor_pos.x() - self.width() // 2, cursor_pos.y() - self.height() // 2)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 2 - 3

        glow = QColor(self._color)
        glow.setAlpha(max(25, int(self._opacity * 1.5)))
        transparent = QColor(glow)
        transparent.setAlpha(0)
        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0.0, glow)
        gradient.setColorAt(0.65, transparent)
        gradient.setColorAt(1.0, transparent)
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(int(center_x - radius), int(center_y - radius), int(radius * 2), int(radius * 2))

        ring_color = QColor(self._color)
        ring_color.setAlpha(int(255 * (self._opacity / 100)))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(ring_color, self._ring_thickness))
        inset = 4 + self._ring_thickness / 2
        ring_size = min(self.width(), self.height()) - inset * 2
        painter.drawEllipse(int(inset), int(inset), int(ring_size), int(ring_size))

        dot_color = QColor("#FFFFFF")
        dot_color.setAlpha(min(255, int(170 + self._opacity * 0.8)))
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot_color)
        painter.drawEllipse(int(center_x - 2), int(center_y - 2), 4, 4)

        if self._click_effects_enabled and self._pulses:
            now = time.monotonic()
            min_pulse_radius = 6.0
            max_pulse_radius = max(
                min_pulse_radius + 1.0,
                radius - (self._ring_thickness / 2) - 3.0,
            )
            for started_at, button in self._pulses:
                progress = (now - started_at) / self._pulse_duration
                if progress < 0 or progress > 1:
                    continue
                pulse_color = QColor(self._color)
                if button == "right":
                    pulse_color = QColor("#FFFFFF")
                pulse_color.setAlpha(max(0, int((1.0 - progress) * 220)))
                pulse_radius = min_pulse_radius + progress * (max_pulse_radius - min_pulse_radius)
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(pulse_color, max(1, self._ring_thickness - 1)))
                painter.drawEllipse(
                    int(center_x - pulse_radius),
                    int(center_y - pulse_radius),
                    int(pulse_radius * 2),
                    int(pulse_radius * 2),
                )
