import sys
from collections.abc import Callable

from PySide6.QtCore import QObject, QPointF, QRunnable, QSize, QThreadPool, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
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
from i18n import (
    Translator,
    detect_system_language,
    localize_error,
)
from import_service import ImportResult, import_word
from history_store import ImportHistoryItem, add_history_item, read_history
from language_menu import LanguageMenuButton
from oxford_client import build_oxford_search_url
from setup_wizard import ConnectionWorker, SetupWizard
from settings_store import (
    HISTORY_LINK_TARGET_NOTION,
    HISTORY_LINK_TARGET_OXFORD,
    read_app_language,
    read_history_link_target,
    read_notion_settings,
    save_app_language,
    save_history_link_target,
    save_notion_settings,
)
from update_checker import UpdateInfo, check_for_update


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
QToolButton#language {
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
}
QToolButton#language:hover {
    background: #f8fafc;
}
QToolButton#language::menu-indicator {
    image: none;
}
QFrame#updateBanner {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
}
QLabel#updateText {
    color: #1e40af;
}
QPushButton#updateAction {
    min-height: 32px;
    padding: 0 8px;
    border: none;
    color: #2563eb;
    background: transparent;
}
QPushButton#historyItem {
    min-height: 34px;
    padding: 0 11px;
    border: 1px solid #dbe3ed;
    border-radius: 8px;
    background: #f8fafc;
    color: #334155;
    font-weight: 500;
}
QPushButton#historyItem:hover {
    background: #eff6ff;
    border-color: #bfdbfe;
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


class UpdateSignals(QObject):
    completed = Signal(object)


class UpdateWorker(QRunnable):
    def __init__(self, update_func: Callable[[], UpdateInfo | None]) -> None:
        super().__init__()
        self.update_func = update_func
        self.signals = UpdateSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.update_func()
        except Exception:
            result = None
        self.signals.completed.emit(result)


class OxfordToNotionWindow(QMainWindow):
    def __init__(
        self,
        *,
        import_func: Callable[[str], ImportResult] = import_word,
        history_reader: Callable[[], list[ImportHistoryItem]] = read_history,
        history_adder: Callable[[str, str], list[ImportHistoryItem]] = add_history_item,
        update_func: Callable[[], UpdateInfo | None] = check_for_update,
        start_update_check: bool = True,
    ) -> None:
        super().__init__()
        self.import_func = import_func
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self.update_thread_pool = QThreadPool(self)
        self.update_thread_pool.setMaxThreadCount(1)
        self.current_page_url = ""
        self.history_reader = history_reader
        self.history_adder = history_adder
        self.update_func = update_func
        self.update_info: UpdateInfo | None = None
        self._settings_test_values: tuple[str, str] | None = None
        self.language = read_app_language() or detect_system_language()
        self.translator = Translator(self.language)
        self.history_link_target = read_history_link_target()

        self.setWindowTitle("Oxford to Notion")
        self.setWindowIcon(QIcon(str(resource_path("assets/app-icon.png"))))
        self.resize(720, 600)
        self.setMinimumSize(640, 600)
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
            translator=self.translator,
            on_language_changed=self.set_language,
        )
        self.stack.addWidget(self.main_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.wizard_page)
        self.retranslate_ui()
        self.refresh_history()
        self.show_update(None)

        if stored.is_complete:
            self.show_main_page()
        else:
            self.stack.setCurrentWidget(self.wizard_page)
        if start_update_check:
            self.start_update_check()

    def _new_card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 30, 34, 28)
        layout.setSpacing(0)
        return card, layout

    def _create_language_button(self, *, main: bool = False) -> LanguageMenuButton:
        button = LanguageMenuButton(self.set_language)
        if main:
            self.language_button = button
            self.language_menu = button.language_menu
            self.language_action_group = button.action_group
        return button

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        card, layout = self._new_card()
        page_layout.addWidget(card)

        header = QHBoxLayout()
        self.main_title_label = QLabel("Oxford to Notion", objectName="title")
        self.settings_button = QPushButton(objectName="secondary")
        self.settings_button.setFixedWidth(92)
        self.settings_button.clicked.connect(self.show_settings_page)
        header.addWidget(self.main_title_label)
        header.addStretch()
        header.addWidget(self._create_language_button(main=True))
        header.addSpacing(8)
        header.addWidget(self.settings_button)
        layout.addLayout(header)

        self.subtitle_label = QLabel(objectName="subtitle")
        self.subtitle_label.setContentsMargins(0, 10, 0, 26)
        layout.addWidget(self.subtitle_label)

        self.word_entry = QLineEdit()
        self.word_entry.returnPressed.connect(self.start_import)
        layout.addWidget(self.word_entry)

        self.import_button = QPushButton(objectName="primary")
        self.import_button.setContentsMargins(0, 16, 0, 0)
        self.import_button.clicked.connect(self.start_import)
        layout.addSpacing(16)
        layout.addWidget(self.import_button)

        self.status_label = QLabel(objectName="muted")
        self._status_key = "ready"
        self._status_values: dict[str, object] = {}
        self._status_error_source: str | None = None
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

        self.open_button = QPushButton(objectName="secondary")
        self.open_button.setFixedWidth(176)
        self.open_button.clicked.connect(self.open_notion_page)
        self.open_button.hide()
        open_row = QHBoxLayout()
        open_row.addStretch()
        open_row.addWidget(self.open_button)
        open_row.addStretch()
        self.open_spacing = QWidget()
        self.open_spacing.setFixedHeight(10)
        self.open_spacing.hide()
        layout.addWidget(self.open_spacing)
        layout.addLayout(open_row)

        self.update_banner = QFrame(objectName="updateBanner")
        update_layout = QHBoxLayout(self.update_banner)
        update_layout.setContentsMargins(12, 5, 8, 5)
        self.update_label = QLabel(objectName="updateText")
        self.update_label.setWordWrap(True)
        self.update_button = QPushButton(objectName="updateAction")
        self.update_button.clicked.connect(self.open_update_page)
        update_layout.addWidget(self.update_label, 1)
        update_layout.addWidget(self.update_button)
        self.update_spacing = QWidget()
        self.update_spacing.setFixedHeight(12)
        self.update_spacing.hide()
        layout.addWidget(self.update_spacing)
        layout.addWidget(self.update_banner)
        self.update_banner.hide()

        self.history_section = QWidget()
        history_layout = QVBoxLayout(self.history_section)
        history_layout.setContentsMargins(0, 0, 0, 8)
        history_layout.setSpacing(8)
        self.history_title = QLabel(objectName="subtitle")
        self.history_title.setStyleSheet("font-weight: 600;")
        history_layout.addWidget(self.history_title)
        self.history_grid = QGridLayout()
        self.history_grid.setContentsMargins(0, 0, 0, 0)
        self.history_grid.setHorizontalSpacing(8)
        self.history_grid.setVerticalSpacing(8)
        history_layout.addLayout(self.history_grid)
        self.history_buttons: list[QPushButton] = []
        self.history_spacing = QWidget()
        self.history_spacing.setFixedHeight(8)
        self.history_spacing.hide()
        layout.addWidget(self.history_spacing)
        layout.addWidget(self.history_section)
        self.history_section.hide()

        layout.addStretch()
        self.footer_label = QLabel(objectName="muted")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.footer_label)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        card, layout = self._new_card()
        page_layout.addWidget(card)

        settings_header = QHBoxLayout()
        self.settings_title_label = QLabel(objectName="title")
        settings_header.addWidget(self.settings_title_label)
        settings_header.addStretch()
        self.settings_language_button = self._create_language_button()
        settings_header.addWidget(self.settings_language_button)
        layout.addLayout(settings_header)

        self.settings_note_label = QLabel(objectName="subtitle")
        self.settings_note_label.setWordWrap(True)
        self.settings_note_label.setContentsMargins(0, 8, 0, 22)
        layout.addWidget(self.settings_note_label)

        self.token_label = QLabel()
        layout.addWidget(self.token_label)
        layout.addSpacing(6)
        self.token_entry = QLineEdit()
        self.token_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_entry.textChanged.connect(self.invalidate_settings_connection)
        layout.addWidget(self.token_entry)

        self.show_token_checkbox = QCheckBox()
        self.show_token_checkbox.toggled.connect(self.toggle_token_visibility)
        layout.addSpacing(8)
        layout.addWidget(self.show_token_checkbox)

        layout.addSpacing(18)
        self.database_label = QLabel()
        layout.addWidget(self.database_label)
        layout.addSpacing(6)
        self.database_entry = QLineEdit()
        self.database_entry.textChanged.connect(self.invalidate_settings_connection)
        layout.addWidget(self.database_entry)

        layout.addSpacing(18)
        self.history_target_label = QLabel()
        layout.addWidget(self.history_target_label)
        layout.addSpacing(6)
        self.history_target_combo = QComboBox()
        self.history_target_combo.addItem("", HISTORY_LINK_TARGET_NOTION)
        self.history_target_combo.addItem("", HISTORY_LINK_TARGET_OXFORD)
        layout.addWidget(self.history_target_combo)

        layout.addSpacing(12)
        self.wizard_button = QPushButton(objectName="secondary")
        self.wizard_button.clicked.connect(self.show_wizard_page)
        layout.addWidget(self.wizard_button)

        self.settings_status = QLabel("")
        self._settings_status_key: str | None = None
        self._settings_error_source: str | None = None
        self.settings_status.setWordWrap(True)
        self.settings_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(12)
        layout.addWidget(self.settings_status)

        layout.addStretch()
        buttons = QHBoxLayout()
        self.settings_back_button = QPushButton(objectName="secondary")
        self.settings_back_button.clicked.connect(self.show_main_page)
        self.settings_test_button = QPushButton(objectName="secondary")
        self.settings_test_button.clicked.connect(self.start_settings_connection_test)
        self.settings_save_button = QPushButton(objectName="primary")
        self.settings_save_button.clicked.connect(self.save_settings)
        buttons.addWidget(self.settings_back_button)
        buttons.addSpacing(8)
        buttons.addWidget(self.settings_test_button)
        buttons.addSpacing(8)
        buttons.addWidget(self.settings_save_button)
        layout.addLayout(buttons)
        return page

    @Slot(str)
    def set_language(self, code: str) -> None:
        self.language = Translator(code).language
        self.translator = Translator(self.language)
        self.retranslate_ui()
        try:
            save_app_language(self.language)
        except AppError:
            self.set_status(self.translator.text("language_save_warning"), "#b45309")

    def retranslate_ui(self) -> None:
        text = self.translator.text
        self.settings_button.setText(text("settings"))
        self.subtitle_label.setText(text("subtitle"))
        self.word_entry.setPlaceholderText(text("word_placeholder"))
        self.import_button.setText(text("import"))
        self.open_button.setText(text("open_notion"))
        self.footer_label.setText(text("footer"))
        self.settings_title_label.setText(text("settings_title"))
        self.settings_note_label.setText(text("settings_note"))
        self.token_label.setText(text("token_label"))
        self.show_token_checkbox.setText(text("show_token"))
        self.database_label.setText(text("database_label"))
        self.history_target_label.setText(text("history_target_label"))
        self.history_target_combo.setItemText(0, text("history_target_notion"))
        self.history_target_combo.setItemText(1, text("history_target_oxford"))
        self.wizard_button.setText(text("open_wizard"))
        self.settings_back_button.setText(text("back"))
        self.settings_test_button.setText(text("test_connection"))
        self.settings_save_button.setText(text("save_settings"))
        self.history_title.setText(text("recently_imported"))
        self.update_button.setText(text("view_update"))
        if self.update_info is not None:
            self.update_label.setText(
                text("update_available", version=self.update_info.version)
            )
        for button in self.history_buttons:
            button.setToolTip(
                text(self.history_tooltip_key(), word=button.property("word"))
            )
        tooltip = text("language_tooltip")
        self.language_button.set_language_state(self.language, tooltip)
        self.settings_language_button.set_language_state(self.language, tooltip)
        if self._status_key:
            self.status_label.setText(text(self._status_key, **self._status_values))
        elif self._status_error_source:
            self.status_label.setText(localize_error(self._status_error_source, self.translator))
        if self._settings_status_key:
            self.settings_status.setText(text(self._settings_status_key))
        elif self._settings_error_source:
            self.settings_status.setText(
                localize_error(self._settings_error_source, self.translator)
            )
        if hasattr(self, "wizard_page"):
            self.wizard_page.apply_translator(self.translator)

    @Slot()
    def show_main_page(self) -> None:
        self.stack.setCurrentWidget(self.main_page)
        self.word_entry.setFocus()

    @Slot()
    def show_settings_page(self) -> None:
        stored = read_notion_settings()
        self.token_entry.setText(stored.notion_token)
        self.database_entry.setText(stored.notion_database_value)
        target_index = self.history_target_combo.findData(self.history_link_target)
        self.history_target_combo.setCurrentIndex(max(0, target_index))
        self.settings_status.clear()
        self._settings_status_key = None
        self._settings_error_source = None
        self._settings_test_values = None
        self.settings_test_button.setEnabled(True)
        self.settings_test_button.setText(self.translator.text("test_connection"))
        self.stack.setCurrentWidget(self.settings_page)
        self.token_entry.setFocus()
        self.schedule_content_fit()

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
            self.wizard_page.show_error_source(str(exc))
            return
        self.show_main_page()
        self.set_status_key("setup_complete", "#15803d", success=True)

    @Slot()
    def start_import(self) -> None:
        word = self.word_entry.text().strip()
        if not word:
            self.set_status_key("enter_word", "#b91c1c")
            return

        self.current_page_url = ""
        self.open_button.hide()
        self.open_spacing.hide()
        self.word_entry.setEnabled(False)
        self.import_button.setEnabled(False)
        self.import_button.setText(self.translator.text("importing"))
        self.set_status_key("querying", "#64748b", word=word)

        worker = ImportWorker(word, self.import_func)
        worker.signals.succeeded.connect(self.finish_success)
        worker.signals.failed.connect(self.finish_error)
        self.thread_pool.start(worker)

    @Slot(object)
    def finish_success(self, result: ImportResult) -> None:
        self.set_ready()
        self.current_page_url = result.page_url
        self.set_status_key("import_success", "#15803d", success=True, word=result.word)
        self.open_spacing.show()
        self.open_button.show()
        items = self.history_adder(result.word, result.page_url)
        self.refresh_history(items)
        self.word_entry.clear()
        self.word_entry.setFocus()
        self.schedule_content_fit()

    @Slot(str)
    def finish_error(self, message: str) -> None:
        self.set_ready()
        self.set_error_status(message)
        self.word_entry.setFocus()

    def set_ready(self) -> None:
        self.word_entry.setEnabled(True)
        self.import_button.setEnabled(True)
        self.import_button.setText(self.translator.text("import"))

    def set_status_key(
        self,
        key: str,
        color: str,
        *,
        success: bool = False,
        **values: object,
    ) -> None:
        self._status_key = key
        self._status_values = values
        self._status_error_source = None
        self.set_status(self.translator.text(key, **values), color, success=success)

    def set_error_status(self, message: str) -> None:
        self._status_key = None
        self._status_values = {}
        self._status_error_source = message
        self.set_status(localize_error(message, self.translator), "#b91c1c")

    def set_status(self, message: str, color: str, *, success: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
        self.success_icon.setVisible(success)

    @Slot()
    def open_notion_page(self) -> None:
        if self.current_page_url:
            QDesktopServices.openUrl(QUrl(self.current_page_url))

    def history_url(self, item: ImportHistoryItem) -> str:
        if self.history_link_target == HISTORY_LINK_TARGET_OXFORD:
            return build_oxford_search_url(item.word)
        return item.page_url

    def history_tooltip_key(self) -> str:
        if self.history_link_target == HISTORY_LINK_TARGET_OXFORD:
            return "open_history_item_oxford"
        return "open_history_item_notion"

    def refresh_history(self, items: list[ImportHistoryItem] | None = None) -> None:
        for button in self.history_buttons:
            self.history_grid.removeWidget(button)
            button.deleteLater()
        self.history_buttons.clear()

        history = (items if items is not None else self.history_reader())[:5]
        for index, item in enumerate(history):
            button = QPushButton(f"{item.word} ↗", objectName="historyItem")
            button.setProperty("word", item.word)
            button.setToolTip(
                self.translator.text(self.history_tooltip_key(), word=item.word)
            )
            target_url = self.history_url(item)
            button.clicked.connect(
                lambda _checked=False, url=target_url: self.open_external_url(url)
            )
            self.history_grid.addWidget(button, index // 3, index % 3)
            self.history_buttons.append(button)
        has_history = bool(self.history_buttons)
        self.history_spacing.setVisible(has_history)
        self.history_section.setVisible(has_history)

    def schedule_content_fit(self) -> None:
        QTimer.singleShot(0, self.grow_window_to_fit_content)

    def grow_window_to_fit_content(self) -> None:
        required_height = self.sizeHint().height()
        if required_height > self.height():
            self.resize(self.width(), required_height)

    @Slot()
    def start_update_check(self) -> None:
        worker = UpdateWorker(self.update_func)
        worker.signals.completed.connect(self.show_update)
        self.update_thread_pool.start(worker)

    @Slot(object)
    def show_update(self, info: UpdateInfo | None) -> None:
        self.update_info = info
        if info is None:
            self.update_spacing.hide()
            self.update_banner.hide()
            return
        self.update_label.setText(
            self.translator.text("update_available", version=info.version)
        )
        self.update_button.setText(self.translator.text("view_update"))
        self.update_spacing.show()
        self.update_banner.show()
        self.schedule_content_fit()

    @Slot()
    def open_update_page(self) -> None:
        if self.update_info is not None:
            self.open_external_url(self.update_info.release_url)

    @staticmethod
    def open_external_url(url: str) -> None:
        target = QUrl(url)
        if target.isValid() and target.scheme().lower() in {"http", "https"}:
            QDesktopServices.openUrl(target)

    @Slot(bool)
    def toggle_token_visibility(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.token_entry.setEchoMode(mode)

    @Slot()
    def start_settings_connection_test(self) -> None:
        token = self.token_entry.text().strip()
        database = self.database_entry.text().strip()
        if not token or not database:
            self.set_settings_status_key("settings_incomplete", "#b91c1c")
            return

        self.settings_test_button.setEnabled(False)
        self.settings_test_button.setText(self.translator.text("testing"))
        self._settings_test_values = (token, database)
        self.set_settings_status_key("checking_connection", "#64748b")
        worker = ConnectionWorker(token, database)
        worker.signals.succeeded.connect(self.finish_settings_connection_test)
        worker.signals.failed.connect(self.fail_settings_connection_test)
        self.thread_pool.start(worker)

    @Slot(object)
    def finish_settings_connection_test(self, _result) -> None:
        self.settings_test_button.setEnabled(True)
        self.settings_test_button.setText(self.translator.text("retest"))
        submitted = self._settings_test_values
        current = (
            self.token_entry.text().strip(),
            self.database_entry.text().strip(),
        )
        self._settings_test_values = None
        if submitted is not None and current != submitted:
            self.set_settings_status_key("connection_changed", "#b45309")
            return
        self.set_settings_status_key("connection_success", "#15803d")

    @Slot(str)
    def fail_settings_connection_test(self, message: str) -> None:
        self._settings_test_values = None
        self.settings_test_button.setEnabled(True)
        self.settings_test_button.setText(self.translator.text("retest"))
        self._settings_status_key = None
        self._settings_error_source = message
        self.settings_status.setText(localize_error(message, self.translator))
        self.settings_status.setStyleSheet("color: #b91c1c;")

    @Slot()
    def invalidate_settings_connection(self) -> None:
        if self._settings_status_key == "connection_success":
            self.set_settings_status_key("connection_changed", "#b45309")

    def set_settings_status_key(self, key: str, color: str) -> None:
        self._settings_status_key = key
        self._settings_error_source = None
        self.settings_status.setText(self.translator.text(key))
        self.settings_status.setStyleSheet(f"color: {color};")

    @Slot()
    def save_settings(self) -> None:
        selected_target = self.history_target_combo.currentData()
        try:
            save_notion_settings(self.token_entry.text(), self.database_entry.text())
            save_history_link_target(selected_target)
        except AppError as exc:
            self._settings_status_key = None
            self._settings_error_source = str(exc)
            self.settings_status.setText(localize_error(str(exc), self.translator))
            self.settings_status.setStyleSheet("color: #b91c1c;")
            return

        self.history_link_target = selected_target
        self.refresh_history()
        self.show_main_page()
        self.set_status_key("settings_saved", "#15803d", success=True)


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
