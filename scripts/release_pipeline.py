"""Draft-first publishing. Failures never promote an incomplete release."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_version import CURRENT_VERSION
from scripts.verify_release import expected_assets, verify_docs, verify_release_directory

REPO = 'johnny05285514-code/oxford-to-notion'


def run_gh(*args):
    return subprocess.run(['gh', *map(str, args)], check=True, capture_output=True,
                          text=True, encoding='utf-8').stdout


def preflight(version, *, gh=run_gh):
    tag = 'v'+version
    refs = json.loads(gh('api', f'repos/{REPO}/git/matching-refs/tags/{tag}'))
    if any(ref['ref'] == 'refs/tags/'+tag for ref in refs):
        raise ValueError('Version tag already exists; choose a new version')
    releases = json.loads(gh('release', 'list', '--repo', REPO, '--limit', '1000', '--json', 'tagName'))
    if any(release['tagName'] == tag for release in releases):
        raise ValueError('Release or draft already exists; review it before retrying')


def publish_release(directory, version, commit, notes, *, gh=run_gh):
    verify_release_directory(directory, version)
    tag = 'v'+version
    gh('release', 'create', tag, '--repo', REPO, '--draft', '--target', commit,
       '--title', 'Oxford to Notion '+tag+' (Windows and macOS)', '--notes-file', str(notes))
    gh('release', 'upload', tag, '--repo', REPO,
       *[str(directory/name) for name in sorted(expected_assets(version))])
    release = json.loads(gh('release', 'view', tag, '--repo', REPO, '--json', 'assets,isDraft'))
    if not release['isDraft'] or {a['name'] for a in release['assets']} != expected_assets(version):
        raise ValueError('Draft asset list does not match')
    if len(release['assets']) != 4:
        raise ValueError('Duplicate release assets')
    with tempfile.TemporaryDirectory(prefix='oton-release-verify-') as folder:
        gh('release', 'download', tag, '--repo', REPO, '--dir', folder)
        verify_release_directory(Path(folder), version)
        for asset in release['assets']:
            if asset['size'] != (directory/asset['name']).stat().st_size:
                raise ValueError('Uploaded size mismatch')
        # Also compare every uploaded byte to the build output, not only its paired checksum.
        for name in expected_assets(version):
            if (Path(folder)/name).read_bytes() != (directory/name).read_bytes():
                raise ValueError('Uploaded artifact differs from build output')
    gh('release', 'edit', tag, '--repo', REPO, '--draft=false', '--latest')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    if os.environ.get('GITHUB_REPOSITORY', REPO) != REPO:
        raise SystemExit('Official releases must run in the product repository')
    verify_docs(root, CURRENT_VERSION)
    preflight(CURRENT_VERSION)
    if sys.argv[1] == 'publish':
        publish_release(root/'release', CURRENT_VERSION, os.environ['GITHUB_SHA'],
                        root/'docs'/'releases'/(CURRENT_VERSION+'.md'))
    elif sys.argv[1] != 'preflight':
        raise SystemExit('Expected preflight or publish')
