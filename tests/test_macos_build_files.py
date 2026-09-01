from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_macos_build_is_arm64_safe_and_smoke_tested():
    script = (ROOT / "scripts" / "build_macos_app.sh").read_text(encoding="utf-8")

    assert "iconutil -c icns" in script
    assert "PyInstaller" in script
    assert '--add-data "assets/app-icon.png:assets"' in script
    assert '"$APP_EXECUTABLE" --smoke-test' in script
    assert "codesign --force --deep --sign -" in script
    assert ".env" not in script


def test_dmg_script_contains_applications_shortcut_and_hash():
    script = (ROOT / "scripts" / "package_macos_dmg.sh").read_text(
        encoding="utf-8"
    )

    assert 'ln -s /Applications "$STAGE_DIR/Applications"' in script
    assert "hdiutil create" in script
    assert "shasum -a 256" in script


def test_macos_build_dependencies_are_pinned():
    requirements = (ROOT / "requirements-macos-build.txt").read_text(
        encoding="utf-8"
    )

    assert "PySide6-Essentials==" in requirements
    assert "shiboken6==" in requirements
    assert "pyinstaller==" in requirements


def test_macos_workflow_is_manual_arm64_and_private_artifact_only():
    workflow = (
        ROOT / ".github" / "workflows" / "macos-arm64-build.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "runs-on: macos-15" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "actions/setup-python@v5" in workflow
    assert "python-version: '3.13'" in workflow
    assert "pytest" in workflow
    assert "scripts/build_macos_app.sh" in workflow
    assert "scripts/package_macos_dmg.sh" in workflow
    assert "lipo -info" in workflow
    assert "hdiutil attach" in workflow
    assert "--smoke-test" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "retention-days: 14" in workflow
    assert "softprops/action-gh-release" not in workflow
