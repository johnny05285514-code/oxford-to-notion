import hashlib
import pytest


def assets(folder):
    for name in ('Oxford-to-Notion-Setup-2.0.0.exe', 'Oxford-to-Notion-macOS-arm64.dmg'):
        (folder/name).write_bytes(b'package')
        (folder/(name+'.sha256')).write_text(hashlib.sha256(b'package').hexdigest()+'  '+name+'\n')


def test_release_requires_both_packages_and_hashes(tmp_path):
    from scripts.verify_release import verify_release_directory
    with pytest.raises(ValueError):
        verify_release_directory(tmp_path, '2.0.0')
    assets(tmp_path)
    verify_release_directory(tmp_path, '2.0.0')
    (tmp_path/'Oxford-to-Notion-macOS-arm64.dmg').unlink()
    with pytest.raises(ValueError):
        verify_release_directory(tmp_path, '2.0.0')


def test_corrupt_or_extra_assets_cannot_publish(tmp_path):
    from scripts.verify_release import verify_release_directory
    assets(tmp_path)
    (tmp_path/'Oxford-to-Notion-macOS-arm64.dmg').write_bytes(b'corrupt')
    with pytest.raises(ValueError):
        verify_release_directory(tmp_path, '2.0.0')
    assets(tmp_path)
    (tmp_path/'.env').write_text('fake-secret')
    with pytest.raises(ValueError):
        verify_release_directory(tmp_path, '2.0.0')


def test_failed_upload_never_publishes(tmp_path):
    from scripts.release_pipeline import publish_release
    assets(tmp_path)
    commands = []
    def gh(*args):
        commands.append(args)
        if args[:2] == ('release', 'upload'):
            raise RuntimeError('upload failed')
        return ''
    with pytest.raises(RuntimeError):
        publish_release(tmp_path, '2.0.0', 'a'*40, tmp_path/'notes.md', gh=gh)
    assert not any(c[:2] == ('release', 'edit') for c in commands)
