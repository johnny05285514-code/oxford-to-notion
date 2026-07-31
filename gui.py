import sys
from collections.abc import Callable

from PySide6.QtCore import QObject, QPointF, QRunnable, QSize, QThreadPool, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPen
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
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app_paths import resource_path
from exceptions import AppError
from history_store import ImportHistoryItem, add_history_item, read_history
from i18n import Translator, detect_system_language, localize_error
from import_service import ImportResult, import_word
from language_menu import LanguageMenuButton
from oxford_client import build_oxford_search_url
from settings_store import (
    HISTORY_LINK_TARGET_NOTION,
    HISTORY_LINK_TARGET_OXFORD,
    read_app_language,
    read_history_link_target,
    read_notion_settings,
    read_performance_diagnostics,
    save_app_language,
    save_history_link_target,
    save_notion_settings,
    save_performance_diagnostics,
)
from setup_wizard import ConnectionWorker, SetupWizard
from update_checker import UpdateInfo, check_for_update


SUMMARY_HISTORY_ITEMS = 5

APP_STYLE = """
QWidget#root {
    background: #f7f8fb;
    color: #172033;
}
QFrame#sidebar {
    background: #f1f4f9;
    border-right: 1px solid #e0e5ec;
}
QFrame#toolbar {
    background: #ffffff;
    border-bottom: 1px solid #e6eaf0;
}
QLabel#toolbarTitle {
    color: #16213b;
    font-size: 18px;
    font-weight: 700;
}
QPushButton#brand {
    min-height: 54px;
    padding: 8px 10px;
    text-align: left;
    border: none;
    border-radius: 12px;
    color: #172033;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#brand:hover { background: #e7edf7; }
QPushButton#navigation {
    min-height: 42px;
    padding: 0 14px;
    text-align: left;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: #334155;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#navigation:hover { background: #e7edf7; }
QPushButton#navigation[active="true"] {
    background: #e1edff;
    color: #1769e8;
}
QWidget#page { background: #ffffff; }
QLabel#pageTitle {
    color: #101b35;
    font-size: 30px;
    font-weight: 700;
}
QLabel#pageSubtitle, QLabel#muted { color: #6b7280; }
QLabel#sectionTitle {
    color: #16213b;
    font-size: 17px;
    font-weight: 700;
}
QLineEdit {
    min-height: 48px;
    padding: 0 15px;
    border: 1px solid #d5dce6;
    border-radius: 10px;
    background: #ffffff;
    font-size: 16px;
    selection-background-color: #1769e8;
}
QLineEdit:focus { border: 2px solid #1769e8; }
QPushButton {
    min-height: 42px;
    border-radius: 10px;
    padding: 0 16px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#primary {
    background: #1769e8;
    color: white;
    border: none;
}
QPushButton#primary:hover { background: #0f5fd8; }
QPushButton#primary:disabled { background: #99beeF; }
QPushButton#secondary {
    background: #ffffff;
    color: #23324c;
    border: 1px solid #cfd8e5;
}
QPushButton#secondary:hover { background: #f6f8fb; }
QPushButton#historyItem, QPushButton#recentItem {
    min-height: 38px;
    padding: 0 14px;
    text-align: left;
    background: #ffffff;
    color: #26344d;
    border: 1px solid #e0e6ee;
    border-radius: 9px;
    font-weight: 500;
}
QPushButton#historyItem:hover, QPushButton#recentItem:hover {
    background: #eef5ff;
    border-color: #bdd6fb;
}
QPushButton#recentItem { border-radius: 0; border-top: none; }
QPushButton#recentItem[firstItem="true"] {
    border-top: 1px solid #e0e6ee;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
QFrame#settingsGroup, QFrame#updateBanner {
    background: #ffffff;
    border: 1px solid #e0e6ee;
    border-radius: 12px;
}
QCheckBox { color: #334155; spacing: 8px; }
QComboBox {
    min-height: 40px;
    padding: 0 12px;
    border: 1px solid #d5dce6;
    border-radius: 9px;
    background: #ffffff;
}
QToolButton#language {
    background: #ffffff;
    border: 1px solid #d5dce6;
    border-radius: 10px;
}
QToolButton#language:hover { background: #f6f8fb; }
QToolButton#language::menu-indicator { image: none; }
QLabel#updateText { color: #1d4f91; }
QPushButton#updateAction {
    min-height: 30px;
    padding: 0 8px;
    border: none;
    color: #1769e8;
    background: transparent;
}
QScrollArea { border: none; background: transparent; }
"""


class SuccessIcon(QWidget):
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
            self.signals.failed.emit("Something unexpected happened. Please try again.")
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
        try:
            self.signals.completed.emit(result)
        except RuntimeError:
            pass


class OxfordToNotionWindow(QMainWindow):
    def __init__(
        self,
        *,
        import_func: Callable[[str], ImportResult] = import_word,
        history_reader: Callable[[], list[ImportHistoryItem]] = read_history,
        history_adder: Callable[[str, str, str], list[ImportHistoryItem]] = add_history_item,
        update_func: Callable[[], UpdateInfo | None] = check_for_update,
        start_update_check: bool = True,
    ) -> None:
        super().__init__()
        self.import_func = import_func
        self.history_reader = history_reader
        self.history_adder = history_adder
        self.update_func = update_func
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self.update_thread_pool = QThreadPool(self)
        self.update_thread_pool.setMaxThreadCount(1)
        self.current_page_url = ""
        self.update_info: UpdateInfo | None = None
        self._settings_test_values: tuple[str, str] | None = None
        self._status_key = "ready"
        self._status_values: dict[str, object] = {}
        self._status_error_source: str | None = None
        self._settings_status_key: str | None = None
        self._settings_error_source: str | None = None
        self.language = read_app_language() or detect_system_language()
        self.translator = Translator(self.language)
        self.history_link_target = read_history_link_target()
        self.performance_diagnostics_enabled = read_performance_diagnostics()

        self.setWindowTitle("Oxford to Notion")
        self.setWindowIcon(QIcon(str(resource_path("assets/app-icon.png"))))
        self.resize(1060, 700)
        self.setMinimumSize(840, 620)
        self.setStyleSheet(APP_STYLE)

        root = QWidget(objectName="root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self._build_toolbar())
        self.stack = QStackedWidget()
        workspace_layout.addWidget(self.stack, 1)
        root_layout.addWidget(workspace, 1)
        self.setCentralWidget(root)

        stored = read_notion_settings()
        self.main_page = self._build_main_page()
        self.recent_page = self._build_recent_page()
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
        self.stack.addWidget(self.recent_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.wizard_page)
        self.retranslate_ui()
        self.refresh_history()
        self.show_update(None)
        if stored.is_complete:
            self.show_main_page()
        else:
            self.show_wizard_page()
        if start_update_check:
            self.start_update_check()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(238)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 18)
        layout.setSpacing(8)
        self.brand_button = QPushButton(objectName="brand")
        self.brand_button.setIcon(QIcon(str(resource_path("assets/app-icon.png"))))
        self.brand_button.setIconSize(QSize(36, 36))
        self.brand_button.clicked.connect(self.show_main_page)
        layout.addWidget(self.brand_button)
        layout.addSpacing(20)
        self.nav_import_button = self._nav_button(self.show_main_page)
        self.nav_recent_button = self._nav_button(self.show_recent_page)
        self.nav_settings_button = self._nav_button(self.show_settings_page)
        self.settings_button = self.nav_settings_button
        layout.addWidget(self.nav_import_button)
        layout.addWidget(self.nav_recent_button)
        layout.addWidget(self.nav_settings_button)
        layout.addStretch(1)
        self.footer_label = QLabel(objectName="muted")
        self.footer_label.setWordWrap(True)
        self.footer_label.setStyleSheet("font-size: 11px; padding: 0 8px;")
        layout.addWidget(self.footer_label)
        return sidebar

    def _nav_button(self, handler: Callable[[], None]) -> QPushButton:
        button = QPushButton(objectName="navigation")
        button.setProperty("active", False)
        button.clicked.connect(handler)
        return button

    def _build_toolbar(self) -> QFrame:
        toolbar = QFrame(objectName="toolbar")
        toolbar.setFixedHeight(64)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(30, 0, 24, 0)
        self.toolbar_title = QLabel(objectName="toolbarTitle")
        layout.addWidget(self.toolbar_title)
        layout.addStretch(1)
        self.language_button = LanguageMenuButton(self.set_language)
        self.language_menu = self.language_button.language_menu
        self.language_action_group = self.language_button.action_group
        self.settings_language_button = self.language_button
        layout.addWidget(self.language_button)
        return toolbar

    def _page_layout(self, page: QWidget) -> QVBoxLayout:
        layout = QVBoxLayout(page)
        layout.setContentsMargins(64, 48, 64, 38)
        layout.setSpacing(0)
        return layout

    def _build_main_page(self) -> QWidget:
        page = QWidget(objectName="page")
        layout = self._page_layout(page)
        self.main_title_label = QLabel(objectName="pageTitle")
        self.main_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_title_label.setWordWrap(True)
        layout.addWidget(self.main_title_label)
        self.subtitle_label = QLabel(objectName="pageSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        layout.addSpacing(10)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(32)

        form = QWidget()
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(14)
        self.word_entry = QLineEdit()
        self.word_entry.returnPressed.connect(self.start_import)
        form_layout.addWidget(self.word_entry)
        self.import_button = QPushButton(objectName="primary")
        self.import_button.clicked.connect(self.start_import)
        form_layout.addWidget(self.import_button)
        layout.addWidget(form)

        self.status_label = QLabel(objectName="muted")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumWidth(440)
        self.success_icon = SuccessIcon()
        self.success_icon.hide()
        status_row = QHBoxLayout()
        status_row.addStretch(1)
        status_row.addWidget(self.success_icon)
        status_row.addSpacing(8)
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        layout.addSpacing(24)
        layout.addLayout(status_row)

        self.open_button = QPushButton(objectName="secondary")
        self.open_button.setFixedWidth(164)
        self.open_button.clicked.connect(self.open_notion_page)
        self.open_button.hide()
        self.open_spacing = QWidget()
        self.open_spacing.setFixedHeight(10)
        self.open_spacing.hide()
        open_row = QHBoxLayout()
        open_row.addStretch(1)
        open_row.addWidget(self.open_button)
        open_row.addStretch(1)
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
        self.update_spacing.setFixedHeight(14)
        self.update_spacing.hide()
        self.update_banner.hide()
        layout.addWidget(self.update_spacing)
        layout.addWidget(self.update_banner)

        self.history_section = QWidget()
        history_layout = QVBoxLayout(self.history_section)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(10)
        self.history_title = QLabel(objectName="sectionTitle")
        history_layout.addWidget(self.history_title)
        self.history_grid = QGridLayout()
        self.history_grid.setContentsMargins(0, 0, 0, 0)
        self.history_grid.setHorizontalSpacing(10)
        self.history_grid.setVerticalSpacing(10)
        history_layout.addLayout(self.history_grid)
        history_layout.addSpacing(10)
        self.history_buttons: list[QPushButton] = []
        self.history_spacing = QWidget()
        self.history_spacing.setFixedHeight(26)
        self.history_spacing.hide()
        layout.addWidget(self.history_spacing)
        layout.addWidget(self.history_section)
        self.history_section.hide()
        layout.addStretch(1)
        return page

    def _build_recent_page(self) -> QWidget:
        page = QWidget(objectName="page")
        layout = self._page_layout(page)
        self.recent_title_label = QLabel(objectName="pageTitle")
        layout.addWidget(self.recent_title_label)
        self.recent_subtitle_label = QLabel(objectName="pageSubtitle")
        self.recent_subtitle_label.setWordWrap(True)
        layout.addSpacing(8)
        layout.addWidget(self.recent_subtitle_label)
        layout.addSpacing(28)
        self.recent_scroll = QScrollArea()
        self.recent_scroll.setWidgetResizable(True)
        self.recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_content = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_content)
        self.recent_layout.setContentsMargins(0, 0, 16, 0)
        self.recent_layout.setSpacing(0)
        self.recent_empty_label = QLabel(objectName="muted")
        self.recent_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_layout.addWidget(self.recent_empty_label)
        self.recent_layout.addStretch(1)
        self.recent_scroll.setWidget(self.recent_content)
        self.recent_buttons: list[QPushButton] = []
        layout.addWidget(self.recent_scroll, 1)
        return page

    def _settings_group(self) -> tuple[QFrame, QVBoxLayout]:
        group = QFrame(objectName="settingsGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)
        return group, layout

    def _build_settings_page(self) -> QWidget:
        page = QScrollArea(objectName="page")
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll = page
        self.settings_content = QWidget(objectName="page")
        layout = self._page_layout(self.settings_content)
        layout.setContentsMargins(44, 48, 44, 38)
        self.settings_title_label = QLabel(objectName="pageTitle")
        self.settings_title_label.setWordWrap(True)
        layout.addWidget(self.settings_title_label)
        self.settings_note_label = QLabel(objectName="pageSubtitle")
        self.settings_note_label.setWordWrap(True)
        layout.addSpacing(8)
        layout.addWidget(self.settings_note_label)
        layout.addSpacing(26)

        connection_group, connection = self._settings_group()
        self.connection_heading = QLabel(objectName="sectionTitle")
        connection.addWidget(self.connection_heading)
        connection.addSpacing(4)
        self.token_label = QLabel()
        connection.addWidget(self.token_label)
        token_row = QHBoxLayout()
        self.token_entry = QLineEdit()
        self.token_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_entry.textChanged.connect(self.invalidate_settings_connection)
        self.show_token_checkbox = QCheckBox()
        self.show_token_checkbox.toggled.connect(self.toggle_token_visibility)
        token_row.addWidget(self.token_entry, 1)
        token_row.addWidget(self.show_token_checkbox)
        connection.addLayout(token_row)
        connection.addSpacing(8)
        self.database_label = QLabel()
        connection.addWidget(self.database_label)
        self.database_entry = QLineEdit()
        self.database_entry.textChanged.connect(self.invalidate_settings_connection)
        connection.addWidget(self.database_entry)
        connection.addSpacing(8)
        connection_actions = QHBoxLayout()
        self.settings_test_button = QPushButton(objectName="secondary")
        self.settings_test_button.clicked.connect(self.start_settings_connection_test)
        connection_actions.addWidget(self.settings_test_button)
        connection_actions.addStretch(1)
        connection.addLayout(connection_actions)
        self.settings_status = QLabel("")
        self.settings_status.setWordWrap(True)
        connection.addWidget(self.settings_status)
        layout.addWidget(connection_group)

        preferences_group, preferences = self._settings_group()
        self.preferences_heading = QLabel(objectName="sectionTitle")
        preferences.addWidget(self.preferences_heading)
        preferences.addSpacing(4)
        self.history_target_label = QLabel()
        preferences.addWidget(self.history_target_label)
        self.history_target_combo = QComboBox()
        self.history_target_combo.addItem("", HISTORY_LINK_TARGET_NOTION)
        self.history_target_combo.addItem("", HISTORY_LINK_TARGET_OXFORD)
        preferences.addWidget(self.history_target_combo)
        preferences.addSpacing(10)
        self.performance_diagnostics_checkbox = QCheckBox()
        preferences.addWidget(self.performance_diagnostics_checkbox)
        self.performance_note_label = QLabel(objectName="muted")
        self.performance_note_label.setWordWrap(True)
        preferences.addWidget(self.performance_note_label)
        layout.addSpacing(12)
        layout.addWidget(preferences_group)

        help_group, help_layout = self._settings_group()
        self.help_heading = QLabel(objectName="sectionTitle")
        help_layout.addWidget(self.help_heading)
        self.wizard_button = QPushButton(objectName="secondary")
        self.wizard_button.clicked.connect(self.show_wizard_page)
        help_layout.addSpacing(4)
        help_layout.addWidget(self.wizard_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(12)
        layout.addWidget(help_group)
        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.settings_back_button = QPushButton(objectName="secondary")
        self.settings_back_button.clicked.connect(self.show_main_page)
        self.settings_save_button = QPushButton(objectName="primary")
        self.settings_save_button.clicked.connect(self.save_settings)
        actions.addWidget(self.settings_back_button)
        actions.addSpacing(10)
        actions.addWidget(self.settings_save_button)
        layout.addSpacing(20)
        layout.addLayout(actions)
        self.settings_content.setMinimumHeight(layout.sizeHint().height())
        page.setWidget(self.settings_content)
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
        self.brand_button.setText("Oxford to Notion")
        self.brand_button.setToolTip(text("nav_import"))
        self.nav_import_button.setText(text("nav_import"))
        self.nav_recent_button.setText(text("nav_recent"))
        self.nav_settings_button.setText(text("settings"))
        self.footer_label.setText(text("footer"))
        self.main_title_label.setText(text("import_heading"))
        self.subtitle_label.setText(text("subtitle"))
        self.word_entry.setPlaceholderText(text("word_placeholder"))
        self.import_button.setText(text("import"))
        self.open_button.setText(text("open_notion"))
        self.history_title.setText(text("recently_imported"))
        self.recent_title_label.setText(text("recently_imported"))
        self.recent_subtitle_label.setText(text("recent_subtitle"))
        self.recent_empty_label.setText(text("recent_empty"))
        self.settings_title_label.setText(text("settings_title"))
        self.settings_note_label.setText(text("settings_note"))
        self.connection_heading.setText(text("connection_heading"))
        self.preferences_heading.setText(text("preferences_heading"))
        self.help_heading.setText(text("help_heading"))
        self.token_label.setText(text("token_label"))
        self.show_token_checkbox.setText(text("show_token"))
        self.database_label.setText(text("database_label"))
        self.history_target_label.setText(text("history_target_label"))
        self.history_target_combo.setItemText(0, text("history_target_notion"))
        self.history_target_combo.setItemText(1, text("history_target_oxford"))
        self.performance_diagnostics_checkbox.setText(text("performance_diagnostics"))
        self.performance_note_label.setText(text("performance_note"))
        self.wizard_button.setText(text("open_wizard"))
        self.settings_back_button.setText(text("cancel"))
        self.settings_test_button.setText(text("test_connection"))
        self.settings_save_button.setText(text("save_settings"))
        self.update_button.setText(text("view_update"))
        tooltip = text("language_tooltip")
        self.language_button.set_language_state(self.language, tooltip)
        for button in [*self.history_buttons, *self.recent_buttons]:
            button.setToolTip(text(self.history_tooltip_key(), word=button.property("word")))
        if self.update_info is not None:
            self.update_label.setText(text("update_available", version=self.update_info.version))
        if self._status_key:
            self.status_label.setText(text(self._status_key, **self._status_values))
        elif self._status_error_source:
            self.status_label.setText(localize_error(self._status_error_source, self.translator))
        if self._settings_status_key:
            self.settings_status.setText(text(self._settings_status_key))
        elif self._settings_error_source:
            self.settings_status.setText(localize_error(self._settings_error_source, self.translator))
        if hasattr(self, "wizard_page"):
            self.wizard_page.apply_translator(self.translator)

    def _set_active_nav(self, active: QPushButton | None) -> None:
        for button in (self.nav_import_button, self.nav_recent_button, self.nav_settings_button):
            button.setProperty("active", button is active)
            button.style().unpolish(button)
            button.style().polish(button)

    def _set_toolbar_title(self, key: str) -> None:
        self.toolbar_title.setText(self.translator.text(key))

    @Slot()
    def show_main_page(self) -> None:
        self.stack.setCurrentWidget(self.main_page)
        self._set_active_nav(self.nav_import_button)
        self._set_toolbar_title("page_import")
        self.word_entry.setFocus()

    @Slot()
    def show_recent_page(self) -> None:
        self.refresh_history()
        self.stack.setCurrentWidget(self.recent_page)
        self._set_active_nav(self.nav_recent_button)
        self._set_toolbar_title("nav_recent")

    @Slot()
    def show_settings_page(self) -> None:
        stored = read_notion_settings()
        self.token_entry.setText(stored.notion_token)
        self.database_entry.setText(stored.notion_database_value)
        target_index = self.history_target_combo.findData(self.history_link_target)
        self.history_target_combo.setCurrentIndex(max(0, target_index))
        self.performance_diagnostics_checkbox.setChecked(self.performance_diagnostics_enabled)
        self.settings_status.clear()
        self._settings_status_key = None
        self._settings_error_source = None
        self._settings_test_values = None
        self.settings_test_button.setEnabled(True)
        self.settings_test_button.setText(self.translator.text("test_connection"))
        self.stack.setCurrentWidget(self.settings_page)
        self._set_active_nav(self.nav_settings_button)
        self._set_toolbar_title("settings")
        self.token_entry.setFocus()

    @Slot()
    def show_wizard_page(self) -> None:
        stored = read_notion_settings()
        self.wizard_page.reset(stored.notion_token, stored.notion_database_value)
        self.stack.setCurrentWidget(self.wizard_page)
        self._set_active_nav(None)
        self._set_toolbar_title("wizard_title")

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
        if self.performance_diagnostics_enabled and result.timing is not None:
            self.set_status_key(
                "import_success_with_timing", "#15803d", success=True, word=result.word,
                oxford=result.timing.oxford_seconds, check=result.timing.notion_check_seconds,
                save=result.timing.notion_write_seconds, total=result.timing.total_seconds,
            )
        else:
            self.set_status_key("import_success", "#15803d", success=True, word=result.word)
        self.open_spacing.show()
        self.open_button.show()
        self.refresh_history(self.history_adder(result.word, result.page_url, result.oxford_url))
        self.word_entry.clear()
        self.word_entry.setFocus()

    @Slot(str)
    def finish_error(self, message: str) -> None:
        self.set_ready()
        self.set_error_status(message)
        self.word_entry.setFocus()

    def set_ready(self) -> None:
        self.word_entry.setEnabled(True)
        self.import_button.setEnabled(True)
        self.import_button.setText(self.translator.text("import"))

    def set_status_key(self, key: str, color: str, *, success: bool = False, **values: object) -> None:
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
            self.open_external_url(self.current_page_url)

    def history_url(self, item: ImportHistoryItem) -> str:
        if self.history_link_target == HISTORY_LINK_TARGET_OXFORD:
            return item.oxford_url or build_oxford_search_url(item.word)
        return item.page_url

    def history_tooltip_key(self) -> str:
        return "open_history_item_oxford" if self.history_link_target == HISTORY_LINK_TARGET_OXFORD else "open_history_item_notion"

    def _history_button(self, item: ImportHistoryItem, object_name: str) -> QPushButton:
        button = QPushButton(f"{item.word}  ↗", objectName=object_name)
        button.setProperty("word", item.word)
        button.setText(f"{item.word} " + chr(0x2197))
        button.setToolTip(self.translator.text(self.history_tooltip_key(), word=item.word))
        button.clicked.connect(lambda _checked=False, url=self.history_url(item): self.open_external_url(url))
        return button

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

    def refresh_history(self, items: list[ImportHistoryItem] | None = None) -> None:
        for button in self.history_buttons:
            self.history_grid.removeWidget(button)
            button.deleteLater()
        self.history_buttons.clear()
        self._clear_layout(self.recent_layout)
        self.recent_buttons.clear()
        history = items if items is not None else self.history_reader()
        for index, item in enumerate(history[:SUMMARY_HISTORY_ITEMS]):
            button = self._history_button(item, "historyItem")
            self.history_grid.addWidget(button, index // 3, index % 3)
            self.history_buttons.append(button)
        for index, item in enumerate(history):
            button = self._history_button(item, "recentItem")
            button.setProperty("firstItem", index == 0)
            self.recent_layout.addWidget(button)
            self.recent_buttons.append(button)
        self.recent_empty_label = QLabel(self.translator.text("recent_empty"), objectName="muted")
        self.recent_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_empty_label.setVisible(not self.recent_buttons)
        self.recent_layout.addWidget(self.recent_empty_label)
        self.recent_layout.addStretch(1)
        self.history_section.setVisible(bool(self.history_buttons))
        self.history_spacing.setVisible(bool(self.history_buttons))

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
        self.update_label.setText(self.translator.text("update_available", version=info.version))
        self.update_button.setText(self.translator.text("view_update"))
        self.update_spacing.show()
        self.update_banner.show()

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
        self.token_entry.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)

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
        current = (self.token_entry.text().strip(), self.database_entry.text().strip())
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
        diagnostics_enabled = self.performance_diagnostics_checkbox.isChecked()
        try:
            save_notion_settings(self.token_entry.text(), self.database_entry.text())
            save_history_link_target(selected_target)
            save_performance_diagnostics(diagnostics_enabled)
        except AppError as exc:
            self._settings_status_key = None
            self._settings_error_source = str(exc)
            self.settings_status.setText(localize_error(str(exc), self.translator))
            self.settings_status.setStyleSheet("color: #b91c1c;")
            return
        self.history_link_target = selected_target
        self.performance_diagnostics_enabled = diagnostics_enabled
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
