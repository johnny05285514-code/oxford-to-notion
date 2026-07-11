import os
import sys
from pathlib import Path


def app_directory() -> Path:
    """Return the folder that should hold user-editable app files."""
    if getattr(sys, "frozen", False):
        app_data = os.getenv("APPDATA")
        base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return base / "Oxford to Notion"
    return Path(__file__).resolve().parent


def env_path() -> Path:
    return app_directory() / ".env"


def resource_path(relative_path: str) -> Path:
    """Locate bundled read-only assets in source and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parent
    return base / relative_path
