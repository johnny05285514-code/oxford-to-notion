import sys
from collections.abc import Callable

from PySide6.QtCore import QObject, QPointF, QRunnable, QSize, QThreadPool, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app_paths import resource_path
from exceptions import AppError
from import_service import ImportResult, import_word
from setup_wizard import ConnectionWorker, SetupWizard
from settings_store import read_notion_settings, save_notion_settings


APP_STYLE = """
QWidget#root {
    background: #f3f6fb;
    color: #172033;
}
QFrame#card {
    background: #ffffff;
    border: 1px solid #e3e8f0;
    border-radius: 18px;
}
QLabel#title {
    font-size: 26px;
    font-weight: 700;
    color: #111827;
}
QLabel#subtitle, QLabel#muted {
    color: #64748b;
}
QLineEdit {
    min-height: 46px;
    padding: 0 14px;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    background: #ffffff;
    font-size: 16px;
    selection-background-color: #2563eb;
}
QLineEdit:focus {
    border: 2px solid #2563eb;
}
QPushButton {
    min-height: 44px;
    border-radius: 10px;
    padding: 0 16px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#primary {
    background: #2563eb;
    color: #ffffff;
    border: none;
}
QPushButton#primary:hover {
    background: #1d4ed8;
}
QPushButton#primary:disabled {
    background: #93b4ee;
}
QPushButton#secondary {
    background: transparent;
    color: #334155;
    border: 1px solid #cbd5e1;
}
QPushButton#secondary:hover {
    background: #f8fafc;
}
QCheckBox {
    color: #475569;
    spacing: 8px;
}
QProgressBar {
    min-height: 7px;
    max-height: 7px;
    border: none;
    border-radius: 3px;
    background: #e2e8f0;
}
QProgressBar::chunk {
    border-radius: 3px;
    background: #2563eb;
}
"""


class SuccessIcon(QWidget):
    """A resolution-independent success icon drawn by Qt instead of a font glyph."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def sizeHint(self) -> QSize:
        return QSize(20, 20)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.scale(self.width() / 20.0, self.height() / 20.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#16a34a"))
        painter.drawEllipse(QPointF(10, 10), 9, 9)

        pen = QPen(QColor("#ffffff"), 1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        check = QPainterPath(QPointF(5.4, 10.1))
        check.lineTo(QPointF(8.6, 13.1))
        check.lineTo(QPointF(14.7, 6.9))
        painter.drawPath(check)


def build_ui_font() -> QFont:
    """Use Segoe UI for Latin text and Microsoft YaHei UI for Chinese text."""
    font = QFont()
    font.setFamilies(["Segoe UI", "Microsoft YaHei UI"])
    font.setPointSize(10)
    font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


class ImportSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)


class ImportWorker(QRunnable):
    def __init__(self, word: str, import_func: Callable[[str], ImportResult]) -> None:
        super().__init__()
        self.word = word
        self.import_func = import_func
        self.signals = ImportSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.import_func(self.word)
        except (AppError, ValueError) as exc:
            self.signals.failed.emit(str(exc))
        except Exception:
            self.signals.failed.emit("发生了意外错误，请稍后重试。")
        else:
            self.signals.succeeded.emit(result)


class OxfordToNotionWindow(QMainWindow):
    def __init__(
        self,
        *,
        import_func: Callable[[str], ImportResult] = import_word,
    ) -> None:
        super().__init__()
        self.import_func = import_func
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self.current_page_url = ""

        self.setWindowTitle("Oxford to Notion")
        self.setWindowIcon(QIcon(str(resource_path("assets/app-icon.png"))))
        self.resize(720, 540)
        self.setMinimumSize(640, 500)
        self.setStyleSheet(APP_STYLE)

        root = QWidget(objectName="root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(52, 42, 52, 42)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)
        self.setCentralWidget(root)

        stored = read_notion_settings()
        self.main_page = self._build_main_page()
        self.settings_page = self._build_settings_page()
        self.wizard_page = SetupWizard(
            on_complete=self.complete_setup,
            on_cancel=self.show_settings_page,
            token=stored.notion_token,
            database=stored.notion_database_value,
            thread_pool=self.thread_pool,
        )
        self.stack.addWidget(self.main_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.wizard_page)

        if stored.is_complete:
            self.show_main_page()
        else:
            self.stack.setCurrentWidget(self.wizard_page)

    def _new_card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 30, 34, 28)
        layout.setSpacing(0)
        return card, layout

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        card, layout = self._new_card()
        page_layout.addWidget(card)

        header = QHBoxLayout()
        title = QLabel("Oxford to Notion", objectName="title")
        settings_button = QPushButton("设置", objectName="secondary")
        settings_button.setFixedWidth(76)
        settings_button.clicked.connect(self.show_settings_page)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(settings_button)
        layout.addLayout(header)

        subtitle = QLabel(
            "输入一个英文单词，自动保存到你的 Notion 单词库",
            objectName="subtitle",
        )
        subtitle.setContentsMargins(0, 10, 0, 26)
        layout.addWidget(subtitle)

        self.word_entry = QLineEdit()
        self.word_entry.setPlaceholderText("例如：brutality")
        self.word_entry.returnPressed.connect(self.start_import)
        layout.addWidget(self.word_entry)

        self.import_button = QPushButton("导入到 Notion", objectName="primary")
        self.import_button.setContentsMargins(0, 16, 0, 0)
        self.import_button.clicked.connect(self.start_import)
        layout.addSpacing(16)
        layout.addWidget(self.import_button)

        self.status_label = QLabel("准备就绪", objectName="muted")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.success_icon = SuccessIcon()
        self.success_icon.hide()
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addStretch()
        status_row.addWidget(self.success_icon)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addSpacing(24)
        layout.addLayout(status_row)

        self.open_button = QPushButton("在 Notion 中打开", objectName="secondary")
        self.open_button.setFixedWidth(176)
        self.open_button.clicked.connect(self.open_notion_page)
        self.open_button.hide()
        open_row = QHBoxLayout()
        open_row.addStretch()
        open_row.addWidget(self.open_button)
        open_row.addStretch()
        layout.addSpacing(10)
        layout.addLayout(open_row)

        layout.addStretch()
        footer = QLabel("Personal, low-frequency learning use", objectName="muted")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("font-size: 11px;")
        layout.addWidget(footer)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        card, layout = self._new_card()
        page_layout.addWidget(card)

        title = QLabel("Notion 设置", objectName="title")
        layout.addWidget(title)

        note = QLabel(
            "配置只保存在这台电脑的 .env 文件中，不会上传到 GitHub。",
            objectName="subtitle",
        )
        note.setWordWrap(True)
        note.setContentsMargins(0, 8, 0, 22)
        layout.addWidget(note)

        layout.addWidget(QLabel("Notion Integration Token"))
        layout.addSpacing(6)
        self.token_entry = QLineEdit()
        self.token_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.token_entry)

        self.show_token_checkbox = QCheckBox("显示 Token")
        self.show_token_checkbox.toggled.connect(self.toggle_token_visibility)
        layout.addSpacing(8)
        layout.addWidget(self.show_token_checkbox)

        layout.addSpacing(18)
        layout.addWidget(QLabel("Notion 数据库 URL 或 Database ID"))
        layout.addSpacing(6)
        self.database_entry = QLineEdit()
        layout.addWidget(self.database_entry)

        layout.addSpacing(12)
        wizard_button = QPushButton("打开分步配置向导", objectName="secondary")
        wizard_button.clicked.connect(self.show_wizard_page)
        layout.addWidget(wizard_button)

        self.settings_status = QLabel("")
        self.settings_status.setWordWrap(True)
        self.settings_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(12)
        layout.addWidget(self.settings_status)

        layout.addStretch()
        buttons = QHBoxLayout()
        back_button = QPushButton("返回", objectName="secondary")
        back_button.clicked.connect(self.show_main_page)
        self.settings_test_button = QPushButton("测试连接", objectName="secondary")
        self.settings_test_button.clicked.connect(self.start_settings_connection_test)
        save_button = QPushButton("保存设置", objectName="primary")
        save_button.clicked.connect(self.save_settings)
        buttons.addWidget(back_button)
        buttons.addSpacing(8)
        buttons.addWidget(self.settings_test_button)
        buttons.addSpacing(8)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)
        return page

    @Slot()
    def show_main_page(self) -> None:
        self.stack.setCurrentWidget(self.main_page)
        self.word_entry.setFocus()

    @Slot()
    def show_settings_page(self) -> None:
        stored = read_notion_settings()
        self.token_entry.setText(stored.notion_token)
        self.database_entry.setText(stored.notion_database_value)
        self.settings_status.clear()
        self.settings_test_button.setEnabled(True)
        self.settings_test_button.setText("测试连接")
        self.stack.setCurrentWidget(self.settings_page)
        self.token_entry.setFocus()

    @Slot()
    def show_wizard_page(self) -> None:
        stored = read_notion_settings()
        self.wizard_page.reset(stored.notion_token, stored.notion_database_value)
        self.stack.setCurrentWidget(self.wizard_page)

    @Slot(str, str)
    def complete_setup(self, token: str, database: str) -> None:
        try:
            save_notion_settings(token, database)
        except AppError as exc:
            self.wizard_page.show_error(str(exc))
            return
        self.show_main_page()
        self.set_status("配置完成，可以开始导入单词。", "#15803d", success=True)

    @Slot()
    def start_import(self) -> None:
        word = self.word_entry.text().strip()
        if not word:
            self.set_status("请输入一个英文单词。", "#b91c1c")
            return

        self.current_page_url = ""
        self.open_button.hide()
        self.word_entry.setEnabled(False)
        self.import_button.setEnabled(False)
        self.import_button.setText("正在导入…")
        self.set_status(f"正在查询 {word}…", "#64748b")

        worker = ImportWorker(word, self.import_func)
        worker.signals.succeeded.connect(self.finish_success)
        worker.signals.failed.connect(self.finish_error)
        self.thread_pool.start(worker)

    @Slot(object)
    def finish_success(self, result: ImportResult) -> None:
        self.set_ready()
        self.current_page_url = result.page_url
        self.set_status(f"{result.word} 已成功导入", "#15803d", success=True)
        self.open_button.show()
        self.word_entry.clear()
        self.word_entry.setFocus()

    @Slot(str)
    def finish_error(self, message: str) -> None:
        self.set_ready()
        self.set_status(message, "#b91c1c")
        self.word_entry.setFocus()

    def set_ready(self) -> None:
        self.word_entry.setEnabled(True)
        self.import_button.setEnabled(True)
        self.import_button.setText("导入到 Notion")

    def set_status(self, message: str, color: str, *, success: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
        self.success_icon.setVisible(success)

    @Slot()
    def open_notion_page(self) -> None:
        if self.current_page_url:
            QDesktopServices.openUrl(QUrl(self.current_page_url))

    @Slot(bool)
    def toggle_token_visibility(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.token_entry.setEchoMode(mode)

    @Slot()
    def start_settings_connection_test(self) -> None:
        token = self.token_entry.text().strip()
        database = self.database_entry.text().strip()
        if not token or not database:
            self.settings_status.setText("请先填写完整的 Token 和数据库链接。")
            self.settings_status.setStyleSheet("color: #b91c1c;")
            return

        self.settings_test_button.setEnabled(False)
        self.settings_test_button.setText("正在测试…")
        self.settings_status.setText("正在检查 Token、数据库权限和字段结构…")
        self.settings_status.setStyleSheet("color: #64748b;")
        worker = ConnectionWorker(token, database)
        worker.signals.succeeded.connect(self.finish_settings_connection_test)
        worker.signals.failed.connect(self.fail_settings_connection_test)
        self.thread_pool.start(worker)

    @Slot(object)
    def finish_settings_connection_test(self, _result) -> None:
        self.settings_test_button.setEnabled(True)
        self.settings_test_button.setText("重新测试")
        self.settings_status.setText("连接成功：Token、数据库权限和字段结构都正确。")
        self.settings_status.setStyleSheet("color: #15803d;")

    @Slot(str)
    def fail_settings_connection_test(self, message: str) -> None:
        self.settings_test_button.setEnabled(True)
        self.settings_test_button.setText("重新测试")
        self.settings_status.setText(message)
        self.settings_status.setStyleSheet("color: #b91c1c;")

    @Slot()
    def save_settings(self) -> None:
        try:
            save_notion_settings(self.token_entry.text(), self.database_entry.text())
        except AppError as exc:
            self.settings_status.setText(str(exc))
            self.settings_status.setStyleSheet("color: #b91c1c;")
            return

        self.show_main_page()
        self.set_status("设置已保存，可以开始导入单词。", "#15803d", success=True)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Oxford to Notion")
    app.setFont(build_ui_font())
    app.setWindowIcon(QIcon(str(resource_path("assets/app-icon.png"))))
    window = OxfordToNotionWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
