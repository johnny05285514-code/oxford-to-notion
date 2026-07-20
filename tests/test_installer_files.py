from pathlib import Path


def test_nsis_installer_is_per_user_and_has_uninstall_support():
    script = Path("installer.nsi").read_text(encoding="utf-8")

    assert 'RequestExecutionLevel user' in script
    assert '$LOCALAPPDATA\\Programs\\Oxford to Notion' in script
    assert 'WriteUninstaller' in script
    assert 'UninstallString' in script
    assert '$\\"$INSTDIR\\Uninstall.exe$\\"' in script
    assert '$SMPROGRAMS\\Oxford to Notion.lnk' in script
    assert '$DESKTOP\\Oxford to Notion.lnk' in script
    assert 'File /oname=Oxford-to-Notion-v1.4.6.ico "assets\\app-icon.ico"' in script
    assert '"$INSTDIR\\Oxford-to-Notion-v1.4.6.ico" 0' in script
    assert 'Delete "$INSTDIR\\Oxford-to-Notion-v1.4.5.ico"' in script


def test_installer_never_bundles_or_deletes_private_settings():
    script = Path("installer.nsi").read_text(encoding="utf-8")

    assert 'File ".env"' not in script
    assert 'NOTION_TOKEN=' not in script
    assert 'RMDir /r "$APPDATA\\Oxford to Notion"' not in script
    assert 'preserve $APPDATA\\Oxford to Notion' in script


def test_installer_build_script_builds_app_and_checksum():
    script = Path("build_installer.bat").read_text(encoding="utf-8")

    assert 'build_app.bat --no-pause' in script
    assert 'MAKENSIS' in script
    assert 'scoop\\apps\\nsis' in script
    assert 'Get-FileHash' in script
    assert '.sha256' in script
    assert '--no-pause' in script
