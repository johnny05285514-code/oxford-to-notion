from pathlib import Path

from PySide6.QtGui import QImage


PNG = Path("assets/app-icon.png")
ICO = Path("assets/app-icon.ico")


def test_icon_assets_are_valid_and_high_resolution():
    assert PNG.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert ICO.read_bytes()[:4] == b"\x00\x00\x01\x00"

    image = QImage(str(PNG))
    assert image.width() == 1024
    assert image.height() == 1024
    assert image.hasAlphaChannel()


def test_desktop_build_embeds_icon_and_runtime_asset():
    script = Path("build_app.bat").read_text(encoding="utf-8")

    assert '--icon "assets\\app-icon.ico"' in script
    assert '--add-data "assets\\app-icon.png;assets"' in script


def test_installer_and_readme_use_product_icon():
    installer = Path("installer.nsi").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    english_readme = Path("README.en.md").read_text(encoding="utf-8")

    assert 'Icon "assets\\app-icon.ico"' in installer
    assert 'UninstallIcon "assets\\app-icon.ico"' in installer
    assert 'assets/app-icon.png' in readme
    assert 'assets/app-icon.png' in english_readme
