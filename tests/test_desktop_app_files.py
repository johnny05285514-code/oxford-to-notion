from pathlib import Path


def test_build_script_creates_windowed_executable_without_bundling_env():
    script = Path("build_app.bat")

    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "--windowed" in content
    assert "--add-data .env" not in content
    assert "--add-data \".env" not in content


def test_build_script_isolates_path_before_pyinstaller_runs():
    content = Path("build_app.bat").read_text(encoding="utf-8")

    path_guard = 'set "PATH=%SystemRoot%\\System32;%SystemRoot%;%~dp0.venv\\Scripts"'
    assert path_guard in content
    assert content.index(path_guard) < content.index("-m PyInstaller")


def test_build_script_smoke_tests_the_packaged_executable():
    content = Path("build_app.bat").read_text(encoding="utf-8")

    invocation = '"dist\\Oxford to Notion.exe" --smoke-test'
    assert invocation in content
    assert "if errorlevel 1" in content[content.index(invocation) :]


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
