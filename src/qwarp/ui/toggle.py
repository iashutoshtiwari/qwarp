from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QRectF, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QBrush, QPainterPath

class AnimatedToggle(QCheckBox):
    def hitButton(self, pos):
        # Forces Qt to register clicks across the entire 100x50 custom widget
        return self.rect().contains(pos)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Colors
        self._bg_color_checked = QColor("#F46654") # Cloudflare Orange
        self._bg_color_unchecked = QColor("#D3D3D3") # Inactive Gray
        self._thumb_color = QColor("#FFFFFF")

        # Geometry for drawing
        self._thumb_radius = 21
        self._track_radius = 25.0
        self._margin = 4.0
        self._thumb_position = float(self._margin)

        # The Animation Engine
        self.animation = QPropertyAnimation(self, b"thumb_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(200) # 200ms slide duration

        self.stateChanged.connect(self._start_animation)

    def setChecked(self, checked: bool):
        """Overrides programmatic state changes to instantly snap visual geometry without relying on signals."""
        super().setChecked(checked)
        end_pos = float(self.width()) - (self._thumb_radius * 2.0) - self._margin if checked else float(self._margin)
        self.thumb_position = end_pos

    @pyqtProperty(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update() # Force repaint on every animation frame

    def _start_animation(self, state):
        self.animation.stop()
        if state == Qt.CheckState.Checked.value:
            end_pos = float(self.width()) - (self._thumb_radius * 2.0) - self._margin
        else:
            end_pos = self._margin

        self.animation.setEndValue(end_pos)
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = self._bg_color_checked if self.isChecked() else self._bg_color_unchecked

        # Draw the Track (The Pill) using QRectF for floating-point precision
        track_rect = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        path = QPainterPath()
        path.addRoundedRect(track_rect, self._track_radius, self._track_radius)
        painter.fillPath(path, QBrush(bg_color))

        # Draw the Thumb (The Circle) using QRectF
        thumb_rect = QRectF(
            self._thumb_position,
            self._margin,
            float(self._thumb_radius * 2),
            float(self._thumb_radius * 2)
        )
        painter.setBrush(QBrush(self._thumb_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(thumb_rect)

        painter.end()
