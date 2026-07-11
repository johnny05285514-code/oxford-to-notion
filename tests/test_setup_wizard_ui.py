import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from notion_connection import ConnectionResult
from setup_wizard import SetupWizard


def make_wizard(completed):
    app = QApplication.instance() or QApplication([])
    wizard = SetupWizard(on_complete=lambda token, database: completed.append((token, database)))
    return app, wizard


def test_wizard_renders_five_steps_and_progress():
    _app, wizard = make_wizard([])

    assert wizard.pages.count() == 5
    assert wizard.progress.maximum() == 5
    assert wizard.progress.value() == 1
    assert "1 / 5" in wizard.step_label.text()

    wizard.close()


def test_wizard_requires_token_and_database_before_test_step():
    _app, wizard = make_wizard([])

    wizard.go_next()
    wizard.go_next()
    assert wizard.state.current_step == 2

    wizard.go_next()
    assert wizard.state.current_step == 2
    assert "Token" in wizard.page_status.text()

    wizard.token_entry.setText("test-token")
    wizard.go_next()
    assert wizard.state.current_step == 3

    wizard.go_next()
    assert wizard.state.current_step == 3
    assert "数据库" in wizard.page_status.text()

    wizard.close()


def test_wizard_only_completes_after_successful_connection_test():
    completed = []
    _app, wizard = make_wizard(completed)
    wizard.token_entry.setText("test-token")
    wizard.database_entry.setText("test-database")

    for _ in range(4):
        wizard.go_next()

    assert wizard.state.current_step == 4
    assert not wizard.finish_button.isEnabled()

    wizard.finish_setup()
    assert completed == []

    wizard.finish_connection(ConnectionResult("test-database", "data-source"))
    assert wizard.finish_button.isEnabled()
    wizard.finish_setup()

    assert completed == [("test-token", "test-database")]
    wizard.close()
