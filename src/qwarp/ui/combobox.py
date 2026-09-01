from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QComboBox

from qwarp.ui.styles import ACCENT_GRADIENT_COLOR


class AccentComboBox(QComboBox):
    """A combo box with a clean, palette-independent dropdown chevron."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        color = "#909090" if not self.isEnabled() else "#c7c7c7"
        if self.isEnabled() and (self.hasFocus() or self.underMouse()):
            color = ACCENT_GRADIENT_COLOR

        center_x = float(self.width() - 14)
        center_y = float(self.height()) / 2.0
        chevron = QPolygonF(
            [
                QPointF(center_x - 4.0, center_y - 2.0),
                QPointF(center_x, center_y + 2.0),
                QPointF(center_x + 4.0, center_y - 2.0),
            ]
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(chevron)
