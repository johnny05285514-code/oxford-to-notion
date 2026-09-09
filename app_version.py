"""The version shared by the application and both packaging tools."""
import json
import re
from pathlib import Path

from app_paths import resource_path


def load_version(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
        raise ValueError("Invalid application version")
    if any(int(part) > 65535 for part in value.split(".")):
        raise ValueError("Application version exceeds Windows metadata limits")
    return value


CURRENT_VERSION = load_version(resource_path("version.json"))


if __name__ == "__main__":
    print(CURRENT_VERSION)
