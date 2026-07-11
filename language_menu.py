from collections.abc import Callable

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QActionGroup, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QToolButton, QWidget

from i18n import SUPPORTED_LANGUAGES


def build_language_icon() -> QIcon:
    """Draw a crisp, familiar globe icon without relying on emoji fonts."""
    pixmap = QPixmap(40, 40)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor("#475569"), 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(5.5, 5.5, 29, 29))
    painter.drawEllipse(QRectF(12.5, 5.5, 15, 29))
    painter.drawEllipse(QRectF(5.5, 12.5, 29, 15))
    painter.end()
    return QIcon(pixmap)


class LanguageMenuButton(QToolButton):
    def __init__(
        self,
        on_selected: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("language")
        self.setFixedSize(46, 44)
        self.setIcon(build_language_icon())
        self.setIconSize(QSize(21, 21))
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.language_menu = QMenu(self)
        self.action_group = QActionGroup(self.language_menu)
        self.action_group.setExclusive(True)
        for language in SUPPORTED_LANGUAGES:
            action = self.language_menu.addAction(language.native_name)
            action.setCheckable(True)
            action.setData(language.code)
            action.triggered.connect(
                lambda _checked=False, code=language.code: on_selected(code)
            )
            self.action_group.addAction(action)
        self.setMenu(self.language_menu)

    def set_language_state(self, language: str, tooltip: str) -> None:
        self.setToolTip(tooltip)
        for action in self.language_menu.actions():
            action.setChecked(action.data() == language)
