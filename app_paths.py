import os
import sys
from pathlib import Path


def app_directory() -> Path:
    """Return the folder that should hold user-editable app files."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Oxford to Notion"
        app_data = os.getenv("APPDATA")
        base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return base / "Oxford to Notion"
    return Path(__file__).resolve().parent


def env_path() -> Path:
    return app_directory() / ".env"


def history_path() -> Path:
    return app_directory() / "history.json"


def update_state_path() -> Path:
    return app_directory() / "update-state.json"


def updates_directory() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "Oxford to Notion" / "Updates"
    base = os.getenv("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / "AppData" / "Local") / "Oxford to Notion" / "Updates"


def resource_path(relative_path: str) -> Path:
    """Locate bundled read-only assets in source and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parent
    return base / relative_path
