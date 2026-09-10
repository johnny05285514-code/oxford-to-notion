from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
import gui
from app_version import CURRENT_VERSION
from settings_store import StoredNotionSettings
from update_checker import UpdateCheckError, UpdateInfo, RELEASES_BASE


class Pool:
    def __init__(self, *args): self.jobs = []
    def setMaxThreadCount(self, n): pass
    def start(self, worker): self.jobs.append(worker)


@pytest.fixture
def window(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui, 'read_notion_settings', lambda: StoredNotionSettings('token','db'))
    monkeypatch.setattr(gui, 'read_app_language', lambda: 'en')
    monkeypatch.setattr(gui, 'save_app_language', lambda _: None)
    monkeypatch.setattr(gui, 'QThreadPool', Pool)
    w = gui.OxfordToNotionWindow(start_update_check=False, history_reader=lambda: [])
    yield w
    w._update_running = False
    w._download_running = False
    w.close()
    app.processEvents()


def info():
    name = 'Oxford-to-Notion-Setup-2.0.0.exe'
    return UpdateInfo('2.0.0', RELEASES_BASE+'/tag/v2.0.0',
                      RELEASES_BASE+'/download/v2.0.0/'+name,
                      RELEASES_BASE+'/download/v2.0.0/'+name+'.sha256', name, 100)


def test_settings_version_and_manual_offline_check(window):
    window.show_settings_page()
    assert CURRENT_VERSION in window.version_label.text()
    def offline(*, force=False):
        assert force
        raise UpdateCheckError()
    window.update_func = offline
    window.check_update_button.click()
    window.update_thread_pool.jobs[-1].run()
    assert 'could not' in window.update_status_label.text().lower()
    assert window.check_update_button.isEnabled()


def test_download_is_click_only_and_shared_with_banner(window, tmp_path, monkeypatch):
    monkeypatch.setattr(gui.sys, 'platform', 'win32')
    window.show_update(info())
    assert not window.update_thread_pool.jobs
    def download(value, **kwargs):
        assert value == info()
        kwargs['progress'](50, 100)
        return tmp_path/info().filename
    window.download_func = download
    window.update_button.click()
    assert window.update_state == 'downloading'
    assert not window.check_update_button.isEnabled()
    window.update_thread_pool.jobs[-1].run()
    assert window.update_state == 'verified'
    assert window.update_button.text() == window.settings_update_button.text() == 'Install now'


def test_launch_failure_does_not_quit_and_can_retry(window, tmp_path):
    window.show_update(info())
    window.finish_update_download(tmp_path/info().filename)
    def fail(*_): raise OSError('cannot launch')
    window.launch_update_func = fail
    window.install_downloaded_update()
    assert window.update_state == 'error'
    assert window.downloaded_update_path is not None
    assert 'installer' in window.update_status_label.text().lower()


def test_successful_windows_launch_precedes_quit(window, monkeypatch, tmp_path):
    monkeypatch.setattr(gui.sys, 'platform', 'win32')
    events = []
    window.show_update(info())
    window.finish_update_download(tmp_path/info().filename)
    window.launch_update_func = lambda path: events.append(('launch', path))
    monkeypatch.setattr(QApplication, 'quit', lambda: events.append(('quit', None)))
    window.install_downloaded_update()
    assert [e[0] for e in events] == ['launch', 'quit']


def test_active_import_blocks_install(window, tmp_path):
    window.show_update(info())
    window.finish_update_download(tmp_path/info().filename)
    window.set_busy(True)
    assert not window.settings_update_button.isEnabled()
    window.launch_update_func = lambda _: pytest.fail('must wait for import')
    window.install_downloaded_update()
    window.set_busy(False)
    assert window.settings_update_button.isEnabled()


def test_language_switch_preserves_size_and_translates_updates(window):
    app = QApplication.instance()
    window.show_update(info())
    window.show_settings_page()
    window.show()
    window.resize(window.minimumSize())
    app.processEvents()
    size = window.size()
    window.set_language('zh-CN')
    app.processEvents()
    assert window.size() == size
    assert '当前版本' in window.version_label.text()
    assert window.toolbar_title.text() == '设置'
    assert window.settings_update_button.text() == '下载更新'
    window.settings_scroll.ensureWidgetVisible(window.version_label)
    app.processEvents()
    assert window.version_label.visibleRegion().boundingRect().height() > 0


def test_close_during_download_requests_cancellation(window):
    window.show_update(info())
    window.start_update_download()
    window.close()
    assert window._download_cancel.is_set()


def test_mac_opens_dmg_without_quitting(window, monkeypatch, tmp_path):
    monkeypatch.setattr(gui.sys, 'platform', 'darwin')
    window.show_update(info())
    window.finish_update_download(tmp_path/'Oxford-to-Notion-macOS-arm64.dmg')
    opened = []
    window.launch_update_func = opened.append
    monkeypatch.setattr(QApplication, 'quit', lambda: pytest.fail('Mac must not quit automatically'))
    window.install_downloaded_update()
    assert len(opened) == 1
    assert window.settings_update_button.text() == 'Open installer'
    assert 'Applications' in window.update_help_label.text()


def test_frozen_windows_launch_resets_environment_and_restores_dll_path(monkeypatch, tmp_path):
    import ctypes
    from types import SimpleNamespace
    path = tmp_path/'installer.exe'
    path.write_bytes(b'test')
    monkeypatch.setattr(gui.sys, 'platform', 'win32')
    monkeypatch.setattr(gui.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(gui.sys, '_MEIPASS', str(tmp_path/'bundle'), raising=False)
    monkeypatch.setenv('QT_QPA_PLATFORM_PLUGIN_PATH', str(tmp_path/'bundle'))
    events = []
    monkeypatch.setattr(ctypes, 'windll', SimpleNamespace(kernel32=SimpleNamespace(
        SetDllDirectoryW=lambda value: events.append(('dll', value)) or 1)), raising=False)
    def popen(args, **kwargs):
        assert kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'] == '1'
        assert 'QT_QPA_PLATFORM_PLUGIN_PATH' not in kwargs['env']
        events.append(('launch', args))
        raise OSError('launch failed')
    monkeypatch.setattr(gui.subprocess, 'Popen', popen)
    with pytest.raises(OSError):
        gui.launch_update_package(path)
    assert events == [('dll', None), ('launch', [str(path)]), ('dll', str(tmp_path/'bundle'))]


def test_real_worker_close_cancels_without_destroying_running_pool(window):
    from PySide6.QtCore import QThreadPool
    from PySide6.QtTest import QTest
    from update_downloader import UpdateDownloadError
    import time
    window.update_thread_pool = QThreadPool(window)
    def download(_info, *, cancelled, progress):
        while not cancelled():
            time.sleep(0.005)
        raise UpdateDownloadError('cancelled')
    window.download_func = download
    window.show_update(info())
    window.show()
    window.start_update_download()
    window.close()
    for _ in range(100):
        QTest.qWait(10)
        if not window._download_running and not window.isVisible():
            break
    assert not window._download_running
    assert not window.isVisible()
    assert window.update_thread_pool.waitForDone(1000)
