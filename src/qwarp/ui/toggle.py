from PyQt6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRectF, Qt, pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import QCheckBox

from qwarp.utils.system import is_dark_mode


class AnimatedToggle(QCheckBox):
    def hitButton(self, pos):
        # Forces Qt to register clicks across the entire 100x50 custom widget
        return self.rect().contains(pos)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Geometry for drawing
        self._thumb_radius = 21.0
        self._track_radius = 25.0
        self._margin = 4.0
        self._thumb_position = float(self._margin)

        # The Animation Engine
        self.animation = QPropertyAnimation(self, b"thumb_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(200)  # 200ms slide duration

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
        self.update()  # Force repaint on every animation frame

    def _start_animation(self, state):
        self.animation.stop()
        if state == Qt.CheckState.Checked.value:
            end_pos = float(self.width()) - (self._thumb_radius * 2.0) - self._margin
        else:
            end_pos = self._margin

        self.animation.setEndValue(end_pos)
        self.animation.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.update()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.EnabledChange,
        ):
            self.update()

    def _get_track_color(self) -> QColor:
        palette = self.palette()
        dark = is_dark_mode(palette)
        if self.isChecked():
            if self.isEnabled():
                color = palette.color(QPalette.ColorRole.Highlight)
                if self.underMouse():
                    color = color.lighter(108)
                return color
            return palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight)
        if self.isEnabled():
            color = palette.color(QPalette.ColorRole.Mid)
            if self.underMouse():
                color = color.lighter(112) if dark else color.darker(108)
            return color
        return palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Mid)

    def _get_thumb_color(self) -> QColor:
        palette = self.palette()
        group = QPalette.ColorGroup.Normal if self.isEnabled() else QPalette.ColorGroup.Disabled
        if self.isChecked():
            return palette.color(group, QPalette.ColorRole.HighlightedText)
        if is_dark_mode(palette):
            candidate = palette.color(group, QPalette.ColorRole.BrightText)
            if candidate.lightness() < 128:
                candidate = palette.color(group, QPalette.ColorRole.WindowText)
            return candidate
        candidate = palette.color(group, QPalette.ColorRole.Base)
        if candidate.lightness() < 128:
            candidate = palette.color(group, QPalette.ColorRole.Window)
        return candidate

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_color = self._get_track_color()
        thumb_color = self._get_thumb_color()

        # Draw the Track (The Pill) using QRectF for floating-point precision
        track_rect = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        path = QPainterPath()
        path.addRoundedRect(track_rect, self._track_radius, self._track_radius)
        painter.fillPath(path, QBrush(track_color))

        # Focus indicator
        if self.hasFocus():
            focus_pen = QPen(self.palette().color(QPalette.ColorRole.Highlight), 2.0, Qt.PenStyle.DashLine)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                track_rect.adjusted(1.0, 1.0, -1.0, -1.0),
                self._track_radius - 1.0,
                self._track_radius - 1.0,
            )

        # Draw the Thumb (The Circle) using QRectF
        thumb_rect = QRectF(
            self._thumb_position,
            self._margin,
            float(self._thumb_radius * 2.0),
            float(self._thumb_radius * 2.0),
        )
        border_color = QColor(0, 0, 0, 45) if is_dark_mode(self.palette()) else QColor(0, 0, 0, 30)
        painter.setPen(QPen(border_color, 1.0))
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(thumb_rect)

        painter.end()
