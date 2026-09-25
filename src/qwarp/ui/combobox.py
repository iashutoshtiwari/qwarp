from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QPainter, QPalette, QPen, QPolygonF
from PyQt6.QtWidgets import QComboBox


class AccentComboBox(QComboBox):
    """A combo box with a clean dropdown chevron derived from the desktop palette."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox::down-arrow {
                image: none;
            }
        """)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.EnabledChange,
        ):
            self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        palette = self.palette()
        if not self.isEnabled():
            color = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
        elif self.hasFocus() or self.underMouse():
            color = palette.color(QPalette.ColorRole.Highlight)
        else:
            color = palette.color(QPalette.ColorRole.Text)

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
        pen = QPen(color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(chevron)
        painter.end()
