"""Fail closed unless both platform packages and exact checksums are present."""
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_version import CURRENT_VERSION


def expected_assets(version: str) -> set[str]:
    packages = {f'Oxford-to-Notion-Setup-{version}.exe', 'Oxford-to-Notion-macOS-arm64.dmg'}
    return packages | {name+'.sha256' for name in packages}


def verify_release_directory(directory: Path, version: str) -> None:
    if {p.name for p in directory.iterdir()} != expected_assets(version):
        raise ValueError('Release must contain exactly both packages and both checksums')
    for name in sorted(expected_assets(version)):
        path = directory/name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Invalid release file')
        if name.endswith('.sha256'):
            continue
        if not 0 < path.stat().st_size <= 200_000_000:
            raise ValueError('Invalid package size')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        text = (directory/(name+'.sha256')).read_text(encoding='ascii')
        if not re.fullmatch(re.escape(digest)+r' [ *]'+re.escape(name)+r'\r?\n?', text):
            raise ValueError('Package checksum or filename mismatch: '+name)


def verify_docs(root: Path, version: str) -> None:
    filename = f'Oxford-to-Notion-Setup-{version}.exe'
    for name in ('README.md', 'README.en.md'):
        text = (root/name).read_text(encoding='utf-8')
        if filename not in text:
            raise ValueError('Update installer example in '+name)
    notes = (root/'docs'/'releases'/(version+'.md')).read_text(encoding='utf-8')
    if 'v'+version not in notes or 'English' not in notes or '中文' not in notes:
        raise ValueError('Missing bilingual version-specific notes')


if __name__ == '__main__':
    verify_release_directory(Path(sys.argv[1]), CURRENT_VERSION)
    print('Both platform packages and checksums verified.')
