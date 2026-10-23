from update_downloader import cleanup_old_packages


def test_cleanup_keeps_current_latest_old_future_and_unrelated_files(tmp_path):
    for version in ["1.5.5", "1.5.6", "1.5.7", "1.5.8"]:
        folder = tmp_path / version
        folder.mkdir()
        (folder / f"Oxford-to-Notion-Setup-{version}.exe").write_bytes(b"package")
        (folder / "notes.txt").write_text("keep")
    cleanup_old_packages(tmp_path, "1.5.7")
    assert not (tmp_path / "1.5.5" / "Oxford-to-Notion-Setup-1.5.5.exe").exists()
    assert (tmp_path / "1.5.5" / "notes.txt").exists()
    for version in ["1.5.6", "1.5.7", "1.5.8"]:
        assert (tmp_path / version / f"Oxford-to-Notion-Setup-{version}.exe").exists()


def test_empty_version_folder_does_not_replace_backup(tmp_path):
    (tmp_path / "1.5.6").mkdir()
    backup = tmp_path / "1.5.5"
    backup.mkdir()
    installer = backup / "Oxford-to-Notion-Setup-1.5.5.exe"
    installer.write_bytes(b"keep")
    cleanup_old_packages(tmp_path, "1.5.7")
    assert installer.exists()
