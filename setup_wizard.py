from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from exceptions import AppError
from i18n import Translator, localize_error
from language_menu import LanguageMenuButton
from notion_connection import ConnectionResult, check_notion_connection


TEMPLATE_URL = (
    "https://impartial-chicken-d5f.notion.site/"
    "39362946376780deb3d2f6986fef3c4a"
    "?v=39362946376780878dde000c78112f24&source=copy_link"
)
INTEGRATIONS_URL = "https://www.notion.so/profile/integrations"
NOTION_HELP_URL = "https://developers.notion.com/guides/get-started/internal-connections"


@dataclass(slots=True)
class SetupWizardState:
    current_step: int = 0
    total_steps: int = 5

    def advance(self) -> int:
        self.current_step = min(self.current_step + 1, self.total_steps - 1)
        return self.current_step

    def back(self) -> int:
        self.current_step = max(self.current_step - 1, 0)
        return self.current_step


class ConnectionSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)


class ConnectionWorker(QRunnable):
    def __init__(
        self,
        token: str,
        database: str,
        connection_func: Callable[[str, str], ConnectionResult] = check_notion_connection,
    ) -> None:
        super().__init__()
        self.token = token
        self.database = database
        self.connection_func = connection_func
        self.signals = ConnectionSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.connection_func(self.token, self.database)
        except AppError as exc:
            self.signals.failed.emit(str(exc))
        except Exception:
            self.signals.failed.emit("测试连接时发生意外错误，请稍后重试。")
        else:
            self.signals.succeeded.emit(result)


class SetupWizard(QWidget):
    def __init__(
        self,
        *,
        on_complete: Callable[[str, str], None],
        on_cancel: Callable[[], None] | None = None,
        token: str = "",
        database: str = "",
        connection_func: Callable[[str, str], ConnectionResult] = check_notion_connection,
        thread_pool: QThreadPool | None = None,
        translator: Translator | None = None,
        on_language_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.state = SetupWizardState()
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.connection_func = connection_func
        self.thread_pool = thread_pool or QThreadPool(self)
        self.connection_passed = False
        self._status_key: str | None = None
        self._status_error_source: str | None = None
        self.translator = translator or Translator("zh-CN")
        self.on_language_changed = on_language_changed
        self.step_text_labels: list[tuple[QLabel, QLabel, str, str]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(0)
        outer.addWidget(card)

        header = QHBoxLayout()
        self.title_label = QLabel(objectName="title")
        header.addWidget(self.title_label)
        header.addStretch()
        self.language_button = LanguageMenuButton(self.set_language)
        self.language_menu = self.language_button.language_menu
        self.language_action_group = self.language_button.action_group
        header.addWidget(self.language_button)
        header.addSpacing(8)
        self.cancel_button = QPushButton(objectName="secondary")
        self.cancel_button.setFixedWidth(100)
        self.cancel_button.setEnabled(on_cancel is not None)
        if on_cancel is not None:
            self.cancel_button.clicked.connect(on_cancel)
        header.addWidget(self.cancel_button)
        layout.addLayout(header)

        self.step_label = QLabel("第 1 / 5 步", objectName="subtitle")
        self.step_label.setContentsMargins(0, 10, 0, 6)
        layout.addWidget(self.step_label)

        self.progress = QProgressBar()
        self.progress.setRange(1, self.state.total_steps)
        self.progress.setTextVisible(False)
        self.progress.setValue(1)
        layout.addWidget(self.progress)
        layout.addSpacing(18)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._template_step())
        self.pages.addWidget(self._integration_step())
        self.pages.addWidget(self._token_step(token))
        self.pages.addWidget(self._database_step(database))
        self.pages.addWidget(self._test_step())
        layout.addWidget(self.pages, 1)

        self.page_status = QLabel("")
        self.page_status.setWordWrap(True)
        self.page_status.setStyleSheet("color: #b91c1c;")
        layout.addSpacing(10)
        layout.addWidget(self.page_status)

        navigation = QHBoxLayout()
        self.back_button = QPushButton("上一步", objectName="secondary")
        self.back_button.clicked.connect(self.go_back)
        self.next_button = QPushButton("下一步", objectName="primary")
        self.next_button.clicked.connect(self.go_next)
        navigation.addWidget(self.back_button)
        navigation.addStretch()
        navigation.addWidget(self.next_button)
        layout.addSpacing(16)
        layout.addLayout(navigation)

        self.token_entry.textChanged.connect(self.invalidate_connection)
        self.database_entry.textChanged.connect(self.invalidate_connection)
        self.retranslate_ui()
        self.update_step()

    def _base_step(
        self, title_key: str, description_key: str
    ) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel()
        title_label.setStyleSheet("font-size: 19px; font-weight: 600;")
        layout.addWidget(title_label)
        layout.addSpacing(8)
        description_label = QLabel(objectName="subtitle")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        layout.addSpacing(18)
        self.step_text_labels.append(
            (title_label, description_label, title_key, description_key)
        )
        return page, layout

    def _template_step(self) -> QWidget:
        page, layout = self._base_step(
            "template_title",
            "template_description",
        )
        self.template_button = QPushButton(objectName="primary")
        self.template_button.clicked.connect(lambda: self.open_link(TEMPLATE_URL))
        layout.addWidget(self.template_button)
        layout.addStretch()
        return page

    def _integration_step(self) -> QWidget:
        page, layout = self._base_step(
            "integration_title",
            "integration_description",
        )
        self.integrations_button = QPushButton(objectName="primary")
        self.integrations_button.clicked.connect(lambda: self.open_link(INTEGRATIONS_URL))
        self.help_button = QPushButton(objectName="secondary")
        self.help_button.clicked.connect(lambda: self.open_link(NOTION_HELP_URL))
        layout.addWidget(self.integrations_button)
        layout.addSpacing(10)
        layout.addWidget(self.help_button)
        layout.addStretch()
        return page

    def _token_step(self, token: str) -> QWidget:
        page, layout = self._base_step(
            "token_title",
            "token_description",
        )
        self.token_entry = QLineEdit()
        self.token_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_entry.setText(token)
        layout.addWidget(self.token_entry)
        layout.addSpacing(8)
        self.show_token_checkbox = QCheckBox()
        self.show_token_checkbox.toggled.connect(
            lambda visible: self.token_entry.setEchoMode(
                QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
            )
        )
        layout.addWidget(self.show_token_checkbox)
        layout.addStretch()
        return page

    def _database_step(self, database: str) -> QWidget:
        page, layout = self._base_step(
            "database_title",
            "database_description",
        )
        self.database_entry = QLineEdit()
        self.database_entry.setPlaceholderText("https://www.notion.so/...")
        self.database_entry.setText(database)
        layout.addWidget(self.database_entry)
        layout.addStretch()
        return page

    def _test_step(self) -> QWidget:
        page, layout = self._base_step(
            "connection_title",
            "connection_description",
        )
        self.test_button = QPushButton(objectName="primary")
        self.test_button.clicked.connect(self.start_connection_test)
        self.finish_button = QPushButton(objectName="secondary")
        self.finish_button.setEnabled(False)
        self.finish_button.clicked.connect(self.finish_setup)
        layout.addWidget(self.test_button)
        layout.addSpacing(10)
        layout.addWidget(self.finish_button)
        layout.addStretch()
        return page

    @Slot(str)
    def set_language(self, code: str) -> None:
        self.translator = Translator(code)
        self.retranslate_ui()
        if self.on_language_changed is not None:
            self.on_language_changed(self.translator.language)

    def apply_translator(self, translator: Translator) -> None:
        self.translator = translator
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        text = self.translator.text
        self.title_label.setText(text("wizard_title"))
        self.cancel_button.setText(text("exit_wizard"))
        self.language_button.set_language_state(
            self.translator.language, text("language_tooltip")
        )
        self.back_button.setText(text("previous"))
        self.next_button.setText(text("next"))
        for title, description, title_key, description_key in self.step_text_labels:
            title.setText(text(title_key))
            description.setText(text(description_key))
        self.template_button.setText(text("open_template"))
        self.integrations_button.setText(text("open_integrations"))
        self.help_button.setText(text("open_notion_help"))
        self.token_entry.setPlaceholderText(text("token_placeholder"))
        self.show_token_checkbox.setText(text("show_token"))
        self.test_button.setText(text("test_connection"))
        self.finish_button.setText(text("save_and_start"))
        self.update_step()
        if self._status_key:
            self.page_status.setText(text(self._status_key))
        elif self._status_error_source:
            self.page_status.setText(
                localize_error(self._status_error_source, self.translator)
            )

    @Slot()
    def go_next(self) -> None:
        if self.state.current_step == 2 and not self.token_entry.text().strip():
            self.show_error_key("token_required")
            return
        if self.state.current_step == 3 and not self.database_entry.text().strip():
            self.show_error_key("database_required")
            return
        self.page_status.clear()
        self._status_key = None
        self._status_error_source = None
        self.state.advance()
        self.update_step()

    @Slot()
    def go_back(self) -> None:
        self.page_status.clear()
        self._status_key = None
        self._status_error_source = None
        self.state.back()
        self.update_step()

    def update_step(self) -> None:
        index = self.state.current_step
        self.pages.setCurrentIndex(index)
        self.progress.setValue(index + 1)
        self.step_label.setText(
            self.translator.text(
                "step_progress", current=index + 1, total=self.state.total_steps
            )
        )
        self.back_button.setEnabled(index > 0)
        self.next_button.setVisible(index < self.state.total_steps - 1)

    def set_values(self, token: str, database: str) -> None:
        self.token_entry.setText(token)
        self.database_entry.setText(database)
        self.connection_passed = False
        self.finish_button.setEnabled(False)

    def reset(self, token: str, database: str) -> None:
        self.state.current_step = 0
        self.page_status.clear()
        self._status_key = None
        self._status_error_source = None
        self.set_values(token, database)
        self.test_button.setEnabled(True)
        self.test_button.setText(self.translator.text("test_connection"))
        self.update_step()

    @Slot()
    def start_connection_test(self) -> None:
        token = self.token_entry.text().strip()
        database = self.database_entry.text().strip()
        if not token or not database:
            self.show_error_key("complete_previous_steps")
            return

        self.connection_passed = False
        self.finish_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.test_button.setText(self.translator.text("testing"))
        self._status_key = "checking_connection"
        self._status_error_source = None
        self.page_status.setText(self.translator.text(self._status_key))
        self.page_status.setStyleSheet("color: #64748b;")

        worker = ConnectionWorker(token, database, self.connection_func)
        worker.signals.succeeded.connect(self.finish_connection)
        worker.signals.failed.connect(self.fail_connection)
        self.thread_pool.start(worker)

    @Slot(object)
    def finish_connection(self, _result: ConnectionResult) -> None:
        self.connection_passed = True
        self.test_button.setEnabled(True)
        self.test_button.setText(self.translator.text("retest"))
        self.finish_button.setEnabled(True)
        self._status_key = "connection_success"
        self._status_error_source = None
        self.page_status.setText(self.translator.text(self._status_key))
        self.page_status.setStyleSheet("color: #15803d;")

    @Slot(str)
    def fail_connection(self, message: str) -> None:
        self.connection_passed = False
        self.test_button.setEnabled(True)
        self.test_button.setText(self.translator.text("retest"))
        self.finish_button.setEnabled(False)
        self.show_error_source(message)

    @Slot()
    def invalidate_connection(self) -> None:
        if self.connection_passed:
            self._status_key = "connection_changed"
            self._status_error_source = None
            self.page_status.setText(self.translator.text(self._status_key))
            self.page_status.setStyleSheet("color: #b45309;")
        self.connection_passed = False
        if hasattr(self, "finish_button"):
            self.finish_button.setEnabled(False)

    @Slot()
    def finish_setup(self) -> None:
        if not self.connection_passed:
            return
        self.on_complete(self.token_entry.text().strip(), self.database_entry.text().strip())

    def show_error(self, message: str) -> None:
        self._status_key = None
        self._status_error_source = None
        self.page_status.setText(message)
        self.page_status.setStyleSheet("color: #b91c1c;")

    def show_error_key(self, key: str) -> None:
        self._status_key = key
        self._status_error_source = None
        self.page_status.setText(self.translator.text(key))
        self.page_status.setStyleSheet("color: #b91c1c;")

    def show_error_source(self, message: str) -> None:
        self._status_key = None
        self._status_error_source = message
        self.page_status.setText(localize_error(message, self.translator))
        self.page_status.setStyleSheet("color: #b91c1c;")

    @staticmethod
    def open_link(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))
