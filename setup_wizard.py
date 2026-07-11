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
    ) -> None:
        super().__init__()
        self.state = SetupWizardState()
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.connection_func = connection_func
        self.thread_pool = thread_pool or QThreadPool(self)
        self.connection_passed = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(0)
        outer.addWidget(card)

        header = QHBoxLayout()
        header.addWidget(QLabel("首次配置 Notion", objectName="title"))
        header.addStretch()
        cancel_button = QPushButton("退出向导", objectName="secondary")
        cancel_button.setFixedWidth(90)
        cancel_button.setEnabled(on_cancel is not None)
        if on_cancel is not None:
            cancel_button.clicked.connect(on_cancel)
        header.addWidget(cancel_button)
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
        self.update_step()

    def _base_step(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 19px; font-weight: 600;")
        layout.addWidget(title_label)
        layout.addSpacing(8)
        description_label = QLabel(description, objectName="subtitle")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        layout.addSpacing(18)
        return page, layout

    def _template_step(self) -> QWidget:
        page, layout = self._base_step(
            "复制 Notion 数据库模板",
            "模板已经包含程序需要的全部字段。打开模板后，点击右上角 Duplicate，复制到你自己的 workspace。",
        )
        button = QPushButton("打开 Notion 模板", objectName="primary")
        button.clicked.connect(lambda: self.open_link(TEMPLATE_URL))
        layout.addWidget(button)
        layout.addStretch()
        return page

    def _integration_step(self) -> QWidget:
        page, layout = self._base_step(
            "创建并连接 Notion Integration",
            "创建 Internal Integration，复制它的 Token，然后在 Notion 中把这个 Integration 连接到刚才复制的数据库。",
        )
        open_button = QPushButton("打开 Notion Integrations", objectName="primary")
        open_button.clicked.connect(lambda: self.open_link(INTEGRATIONS_URL))
        help_button = QPushButton("查看 Notion 官方说明", objectName="secondary")
        help_button.clicked.connect(lambda: self.open_link(NOTION_HELP_URL))
        layout.addWidget(open_button)
        layout.addSpacing(10)
        layout.addWidget(help_button)
        layout.addStretch()
        return page

    def _token_step(self, token: str) -> QWidget:
        page, layout = self._base_step(
            "粘贴 Integration Token",
            "Token 只会保存在你的电脑中。不要把它发送给别人，也不要上传到 GitHub。",
        )
        self.token_entry = QLineEdit()
        self.token_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_entry.setPlaceholderText("粘贴 Notion Integration Token")
        self.token_entry.setText(token)
        layout.addWidget(self.token_entry)
        layout.addSpacing(8)
        show_token = QCheckBox("显示 Token")
        show_token.toggled.connect(
            lambda visible: self.token_entry.setEchoMode(
                QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
            )
        )
        layout.addWidget(show_token)
        layout.addStretch()
        return page

    def _database_step(self, database: str) -> QWidget:
        page, layout = self._base_step(
            "粘贴 Notion 数据库链接",
            "打开刚才复制的数据库，复制完整页面 URL。程序会自动从 URL 中识别 Database ID。",
        )
        self.database_entry = QLineEdit()
        self.database_entry.setPlaceholderText("https://www.notion.so/...")
        self.database_entry.setText(database)
        layout.addWidget(self.database_entry)
        layout.addStretch()
        return page

    def _test_step(self) -> QWidget:
        page, layout = self._base_step(
            "测试 Notion 连接",
            "测试不会写入单词。它只检查 Token、数据库权限和字段结构是否正确。",
        )
        self.test_button = QPushButton("测试连接", objectName="primary")
        self.test_button.clicked.connect(self.start_connection_test)
        self.finish_button = QPushButton("保存并开始使用", objectName="secondary")
        self.finish_button.setEnabled(False)
        self.finish_button.clicked.connect(self.finish_setup)
        layout.addWidget(self.test_button)
        layout.addSpacing(10)
        layout.addWidget(self.finish_button)
        layout.addStretch()
        return page

    @Slot()
    def go_next(self) -> None:
        if self.state.current_step == 2 and not self.token_entry.text().strip():
            self.show_error("请先填写 Notion Integration Token。")
            return
        if self.state.current_step == 3 and not self.database_entry.text().strip():
            self.show_error("请先填写 Notion 数据库 URL。")
            return
        self.page_status.clear()
        self.state.advance()
        self.update_step()

    @Slot()
    def go_back(self) -> None:
        self.page_status.clear()
        self.state.back()
        self.update_step()

    def update_step(self) -> None:
        index = self.state.current_step
        self.pages.setCurrentIndex(index)
        self.progress.setValue(index + 1)
        self.step_label.setText(f"第 {index + 1} / {self.state.total_steps} 步")
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
        self.set_values(token, database)
        self.test_button.setEnabled(True)
        self.test_button.setText("测试连接")
        self.update_step()

    @Slot()
    def start_connection_test(self) -> None:
        token = self.token_entry.text().strip()
        database = self.database_entry.text().strip()
        if not token or not database:
            self.show_error("请返回上一步，填写完整的 Token 和数据库链接。")
            return

        self.connection_passed = False
        self.finish_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.test_button.setText("正在测试…")
        self.page_status.setText("正在检查 Token、数据库权限和字段结构…")
        self.page_status.setStyleSheet("color: #64748b;")

        worker = ConnectionWorker(token, database, self.connection_func)
        worker.signals.succeeded.connect(self.finish_connection)
        worker.signals.failed.connect(self.fail_connection)
        self.thread_pool.start(worker)

    @Slot(object)
    def finish_connection(self, _result: ConnectionResult) -> None:
        self.connection_passed = True
        self.test_button.setEnabled(True)
        self.test_button.setText("重新测试")
        self.finish_button.setEnabled(True)
        self.page_status.setText("连接成功：Token、数据库权限和字段结构都正确。")
        self.page_status.setStyleSheet("color: #15803d;")

    @Slot(str)
    def fail_connection(self, message: str) -> None:
        self.connection_passed = False
        self.test_button.setEnabled(True)
        self.test_button.setText("重新测试")
        self.finish_button.setEnabled(False)
        self.show_error(message)

    @Slot()
    def invalidate_connection(self) -> None:
        if self.connection_passed:
            self.page_status.setText("配置已经更改，请重新测试连接。")
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
        self.page_status.setText(message)
        self.page_status.setStyleSheet("color: #b91c1c;")

    @staticmethod
    def open_link(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))
