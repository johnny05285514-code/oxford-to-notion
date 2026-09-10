"""Keep GUI tests away from the developer's configuration and caches."""
import pytest
import history_store
import settings_store
import update_checker


@pytest.fixture(autouse=True)
def isolated_runtime_files(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_store, 'default_env_path', lambda: tmp_path/'.env')
    monkeypatch.setattr(history_store, 'default_history_path', lambda: tmp_path/'history.json')
    monkeypatch.setattr(update_checker, 'default_update_state_path', lambda: tmp_path/'update-state.json')
