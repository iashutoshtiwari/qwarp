from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QLabel

from qwarp.ui.styles import ACCENT_COLOR, ACCENT_GRADIENT_COLOR


class GradientLabel(QLabel):
    """A label whose text is painted with QWarp's accent gradient."""

    gradient_start = QColor(ACCENT_COLOR)
    gradient_end = QColor(ACCENT_GRADIENT_COLOR)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.contentsRect()
        gradient = QLinearGradient(float(rect.left()), 0.0, float(rect.right()), 0.0)
        gradient.setColorAt(0.0, self.gradient_start)
        gradient.setColorAt(1.0, self.gradient_end)
        painter.setPen(QPen(QBrush(gradient), 0))
        painter.setFont(self.font())
        painter.drawText(rect, self.alignment(), self.text())
