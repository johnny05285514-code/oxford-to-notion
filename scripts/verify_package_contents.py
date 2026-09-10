"""Inspect packaged inputs for private runtime files and the shared version."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_version import CURRENT_VERSION


def verify_package(path: Path):
    if path.is_dir():
        names = [p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()]
        versions = [p for p in path.rglob('version.json') if p.is_file()]
        if not versions or any(json.loads(p.read_text()) != {'version': CURRENT_VERSION} for p in versions):
            raise ValueError('Missing or mismatched bundled version')
    else:
        from PyInstaller.archive.readers import CArchiveReader
        archive = CArchiveReader(str(path))
        names = list(archive.toc)
        if json.loads(archive.extract('version.json')) != {'version': CURRENT_VERSION}:
            raise ValueError('Bundled version mismatch')
    for name in names:
        basename = name.replace('\\', '/').split('/')[-1].lower()
        if basename in {'.env', 'history.json', 'update-state.json'} or basename.startswith('.env.'):
            raise ValueError('Private runtime file in package')
    print('Bundled version and private-file exclusion verified.')


if __name__ == '__main__':
    verify_package(Path(sys.argv[1]))
