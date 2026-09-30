from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import import_service
import gui


def test_dependencies_reused_and_replaced_on_configuration_change(monkeypatch):
    settings = SimpleNamespace(notion_token="first", notion_database_id="database")
    monkeypatch.setattr(import_service.Settings, "from_env", lambda: settings)
    clients = []
    class Client:
        def __init__(self, **kwargs):
            self.closed = False
            clients.append(self)
        def close(self):
            self.closed = True
    monkeypatch.setattr(import_service, "Client", Client)
    def probe():
        cache = import_service.DependencyCache()
        with cache.acquire() as a:
            pass
        with cache.acquire() as again:
            assert again is a
        settings.notion_token = "second"
        with cache.acquire() as b:
            assert b != a
        assert clients[0].closed
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(probe).result()


def test_mac_font_does_not_request_windows_fonts(monkeypatch):
    monkeypatch.setattr(gui.sys, "platform", "darwin")
    assert "Segoe UI" not in gui.build_ui_font().families()


def test_qt_callbacks_reuse_owned_connections(monkeypatch):
    from threading import Event
    from PySide6.QtCore import QThreadPool, QRunnable
    settings = SimpleNamespace(notion_token="token", notion_database_id="db")
    monkeypatch.setattr(import_service.Settings, "from_env", lambda: settings)
    clients = []
    monkeypatch.setattr(import_service, "Client", lambda **kw: clients.append(object()) or clients[-1])
    cache = import_service.DependencyCache()
    done = Event()
    pairs = []
    class Worker(QRunnable):
        def run(self):
            with cache.acquire() as pair:
                pairs.append(pair)
            done.set()
    pool = QThreadPool()
    pool.setMaxThreadCount(1)
    pool.start(Worker())
    assert done.wait(5)
    done.clear()
    pool.start(Worker())
    assert done.wait(5)
    pool.waitForDone()
    assert pairs[0] is pairs[1]
    assert len(clients) == 1

