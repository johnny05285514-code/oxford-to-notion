import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui import SuccessIcon, build_ui_font


def test_ui_font_has_explicit_latin_and_chinese_families():
    font = build_ui_font()

    assert font.families()[:2] == ["Segoe UI", "Microsoft YaHei UI"]
    assert font.pointSize() == 10
    assert font.hintingPreference() == font.HintingPreference.PreferVerticalHinting


def test_success_icon_is_a_fixed_vector_widget():
    app = QApplication.instance() or QApplication([])
    icon = SuccessIcon()

    assert icon.sizeHint().width() == 20
    assert icon.sizeHint().height() == 20
    assert icon.width() == 20
    assert icon.height() == 20

    icon.close()
    assert app is not None
