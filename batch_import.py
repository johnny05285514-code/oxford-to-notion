"""Small sequential import queue with per-word retry results."""
import re

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QPlainTextEdit, QPushButton,
                              QLabel, QTableWidget, QTableWidgetItem, QHeaderView)

from i18n import localize_error


def parse_batch(text):
    words = list(dict.fromkeys(word.strip().lower() for word in re.split(r'[\n\r,;，；]+', text) if word.strip()))
    if not words or len(words) > 20:
        raise ValueError("batch_limit")
    return words


class BatchImportDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.text = owner.translator.text
        self.busy = False
        self.queue = []
        self.words = []
        self.stage = "stage_oxford"
        self.setWindowTitle(self.text("batch_import"))
        self.resize(680, 540)
        self.setMinimumSize(540, 420)
        layout = QVBoxLayout(self)
        self.hint = QLabel(self.text("batch_hint"))
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.entry = QPlainTextEdit()
        self.entry.setMaximumHeight(130)
        layout.addWidget(self.entry)
        self.start_button = QPushButton(self.text("batch_start"))
        self.start_button.clicked.connect(self.start_batch)
        layout.addWidget(self.start_button)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([self.text(k) for k in ("batch_word", "batch_status", "batch_action")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def start_batch(self):
        if self.busy or self.owner._import_busy:
            return
        try:
            self.words = parse_batch(self.entry.toPlainText())
        except ValueError:
            self.hint.setText(self.text("batch_limit"))
            return
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.words))
        for row, word in enumerate(self.words):
            self.table.setItem(row, 0, QTableWidgetItem(word))
            self.table.setItem(row, 1, QTableWidgetItem(self.text("batch_waiting")))
        self.queue = list(range(len(self.words)))
        self.begin()

    def begin(self):
        self.busy = True
        self.owner.set_busy(True)
        self.entry.setEnabled(False)
        self.start_button.setEnabled(False)
        self.advance()

    def advance(self):
        if not self.queue or self.owner._close_pending:
            self.queue.clear()
            self.busy = False
            self.owner.set_busy(False)
            self.entry.setEnabled(True)
            self.start_button.setEnabled(True)
            self.owner.start_recent_sync(force=True)
            return
        self.row = self.queue.pop(0)
        self.stage = "stage_oxford"
        self.table.removeCellWidget(self.row, 2)
        self.progress(self.stage, {})
        from gui import ImportWorker
        worker = ImportWorker(self.words[self.row], self.owner.import_func)
        worker.signals.progress.connect(self.progress)
        worker.signals.succeeded.connect(self.success)
        worker.signals.failed.connect(self.failure)
        self.owner.thread_pool.start(worker)

    def progress(self, stage, values):
        self.stage = "stage_oxford" if stage == "stage_retry" else stage
        self.table.setItem(self.row, 1, QTableWidgetItem(self.text(stage, **values)))

    def success(self, result):
        try:
            items = self.owner.history_adder(result.word, result.page_url, result.oxford_url)
            self.owner.refresh_history(items)
            message = self.text("batch_success")
        except OSError:
            message = self.text("recent_cache_failed")
        if result.cleanup_retry:
            message = self.text("saved_cleanup_failed")
            self.action(self.row, "retry_cleanup", result.cleanup_retry)
        self.table.setItem(self.row, 1, QTableWidgetItem(message))
        self.table.resizeRowToContents(self.row)
        self.advance()

    def failure(self, message):
        self.table.setItem(self.row, 1, QTableWidgetItem(
            self.text(self.stage) + ": " + localize_error(message, self.owner.translator)))
        self.table.resizeRowToContents(self.row)
        self.action(self.row, "retry_import")
        self.advance()

    def action(self, row, key, cleanup=None):
        button = QPushButton(self.text(key))
        button.clicked.connect(lambda: self.retry(row, cleanup))
        self.table.setCellWidget(row, 2, button)

    def retry(self, row, cleanup=None):
        if self.busy or self.owner._import_busy:
            return
        if cleanup is None:
            self.queue = [row]
            self.begin()
            return
        from gui import ImportWorker
        self.busy = True
        self.owner.set_busy(True)
        self.row = row
        self.stage = "stage_cleanup"
        self.table.removeCellWidget(row, 2)
        worker = ImportWorker("", lambda _word: cleanup())
        worker.signals.succeeded.connect(self.success)
        def failed(message):
            self.table.setItem(row, 1, QTableWidgetItem(localize_error(message, self.owner.translator)))
            self.action(row, "retry_cleanup", cleanup)
            self.advance()
        worker.signals.failed.connect(failed)
        self.owner.thread_pool.start(worker)

    def closeEvent(self, event):
        if self.busy:
            self.hint.setText(self.text("closing_wait"))
            event.ignore()
        else:
            super().closeEvent(event)

    def reject(self):
        if self.busy:
            self.hint.setText(self.text("closing_wait"))
            return
        super().reject()
