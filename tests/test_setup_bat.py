from pathlib import Path


def test_setup_bat_guides_windows_installation():
    script = Path("setup.bat")

    assert script.exists()

    content = script.read_text(encoding="utf-8")
    assert "Oxford to Notion setup" in content
    assert "python --version" in content
    assert "python -m venv .venv" in content
    assert ".venv\\Scripts\\python.exe" in content
    assert "requirements.txt" in content
    assert ".env.example" in content
    assert "notepad .env" in content
