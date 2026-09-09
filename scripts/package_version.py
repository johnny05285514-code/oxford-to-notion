"""Write platform version metadata before packaging/signing."""
import plistlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_version import CURRENT_VERSION


def write_windows_version(path: Path) -> None:
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringTable, StringStruct,
        VarFileInfo, VarStruct, VSVersionInfo,
    )
    numbers = (*map(int, CURRENT_VERSION.split('.')), 0)
    info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, mask=0x3f,
                         flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable('040904B0', [
            StringStruct('ProductName', 'Oxford to Notion'),
            StringStruct('FileDescription', 'Oxford to Notion'),
            StringStruct('FileVersion', CURRENT_VERSION),
            StringStruct('ProductVersion', CURRENT_VERSION),
        ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(info), encoding='utf-8')


def write_macos_version(path: Path) -> None:
    with path.open('rb') as stream:
        info = plistlib.load(stream)
    info['CFBundleShortVersionString'] = CURRENT_VERSION
    info['CFBundleVersion'] = CURRENT_VERSION
    with path.open('wb') as stream:
        plistlib.dump(info, stream)


if __name__ == '__main__':
    if sys.argv[1] == 'windows':
        write_windows_version(Path(sys.argv[2]))
    elif sys.argv[1] == 'macos':
        write_macos_version(Path(sys.argv[2]))
    else:
        raise SystemExit('Expected windows or macos')
