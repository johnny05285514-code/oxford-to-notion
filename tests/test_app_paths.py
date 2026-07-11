from pathlib import Path

import app_paths


def test_source_app_uses_project_directory():
    assert app_paths.app_directory() == Path(app_paths.__file__).resolve().parent


def test_frozen_app_uses_windows_appdata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert app_paths.app_directory() == tmp_path / "Oxford to Notion"


def test_source_resource_path_uses_project_directory():
    assert app_paths.resource_path("assets/app-icon.png") == (
        Path(app_paths.__file__).resolve().parent / "assets" / "app-icon.png"
    )


def test_local_state_paths_share_the_application_directory():
    assert app_paths.history_path() == app_paths.app_directory() / "history.json"
    assert app_paths.update_state_path() == app_paths.app_directory() / "update-state.json"
