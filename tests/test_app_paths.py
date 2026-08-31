from pathlib import Path

import app_paths


def test_frozen_macos_uses_application_support(monkeypatch, tmp_path):
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "platform", "darwin")
    monkeypatch.setattr(app_paths.Path, "home", classmethod(lambda cls: tmp_path))

    assert app_paths.app_directory() == (
        tmp_path / "Library" / "Application Support" / "Oxford to Notion"
    )


def test_frozen_windows_still_prefers_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert app_paths.app_directory() == tmp_path / "Oxford to Notion"


def test_source_execution_still_uses_project_directory(monkeypatch):
    monkeypatch.setattr(app_paths.sys, "frozen", False, raising=False)

    assert app_paths.app_directory() == Path(app_paths.__file__).resolve().parent
