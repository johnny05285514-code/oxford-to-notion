from pathlib import Path
import struct

from PySide6.QtGui import QImage


PNG = Path("assets/app-icon.png")
ICO = Path("assets/app-icon.ico")
DEMO = Path("assets/demo.gif")


def test_icon_assets_are_valid_and_high_resolution():
    assert PNG.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert ICO.read_bytes()[:4] == b"\x00\x00\x01\x00"

    image = QImage(str(PNG))
    assert image.width() == 1024
    assert image.height() == 1024
    assert image.hasAlphaChannel()


def test_windows_icon_uses_bitmap_frames_for_shell_compatibility():
    data = ICO.read_bytes()
    _reserved, icon_type, count = struct.unpack_from("<HHH", data)
    assert icon_type == 1
    assert count >= 4

    sizes = set()
    for index in range(count):
        width, height, _colors, _reserved, _planes, _bits, length, offset = (
            struct.unpack_from("<BBBBHHII", data, 6 + index * 16)
        )
        sizes.add((width or 256, height or 256))
        assert data[offset : offset + 8] != b"\x89PNG\r\n\x1a\n"
        assert length > 0

    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= sizes


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


def test_readmes_embed_valid_demo_gif():
    assert DEMO.read_bytes()[:6] in {b"GIF87a", b"GIF89a"}
    assert DEMO.stat().st_size < 2_000_000
    assert 'assets/demo.gif' in Path("README.md").read_text(encoding="utf-8")
    assert 'assets/demo.gif' in Path("README.en.md").read_text(encoding="utf-8")
