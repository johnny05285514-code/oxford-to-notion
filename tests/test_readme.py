from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_chinese_readme_explains_macos_release_install_and_sync():
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "macOS Apple 芯片版（M1、M2、M3、M4）" in content
    assert "GitHub Actions" in content
    assert "GitHub Releases" in content
    assert "M3 MacBook" in content
    assert "拖到“应用程序”" in content
    assert "右键" in content and "打开" in content
    assert "隐私与安全性" in content and "仍要打开" in content
    assert "Developer ID" in content
    assert "Token 和数据库链接需要在 Mac 上单独填写" in content
    assert "通过 Notion 同步" in content
    assert "本地缓存" in content


def test_english_readme_explains_macos_release_install_and_sync():
    content = (ROOT / "README.en.md").read_text(encoding="utf-8")

    assert "Apple silicon (M1, M2, M3, and M4)" in content
    assert "GitHub Actions" in content
    assert "GitHub Releases" in content
    assert "M3 MacBook" in content
    assert "drag `oxford to notion` into `applications`" in content.lower()
    assert "right-click" in content and "Open" in content
    assert "Privacy & Security" in content and "Open Anyway" in content
    assert "ad-hoc" in content
    assert "entered separately on the Mac" in content
    assert "synced through Notion" in content
    assert "local cache" in content


def test_changelog_has_unreleased_macos_and_recent_sync_entry():
    content = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Unreleased" in content
    assert "macOS ARM64" in content
    assert "Recent" in content
