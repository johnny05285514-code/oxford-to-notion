from pathlib import Path


def test_build_script_creates_windowed_executable_without_bundling_env():
    script = Path("build_app.bat")

    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "--windowed" in content
    assert "--add-data .env" not in content
    assert "--add-data \".env" not in content


def test_gui_dependencies_are_declared():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "PySide6-Essentials" in requirements
    assert "pyinstaller" in requirements


def test_install_script_uses_user_app_folders_and_creates_shortcut():
    content = Path("install_app.bat").read_text(encoding="utf-8")

    assert "%LOCALAPPDATA%\\Programs\\Oxford to Notion" in content
    assert "%APPDATA%\\Oxford to Notion" in content
    assert "CreateShortcut" in content
    assert "NOTION_TOKEN=" not in content
