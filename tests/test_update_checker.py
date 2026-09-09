import json
from datetime import datetime, timedelta, timezone
import pytest
import requests
import update_checker as checker

NOW = datetime(2026, 9, 9, tzinfo=timezone.utc)
BASE = 'https://github.com/johnny05285514-code/oxford-to-notion/releases'
NEW = '.'.join(map(str, (int(checker.CURRENT_VERSION.split('.')[0]) + 1, 0, 0)))


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.calls = payload, error, []
    def get(self, url, **kwargs):
        self.calls.append(url)
        if self.error:
            raise self.error
        return FakeResponse(self.payload)


def release(version=NEW):
    names = [f'Oxford-to-Notion-Setup-{version}.exe', 'Oxford-to-Notion-macOS-arm64.dmg']
    return dict(tag_name='v'+version, html_url=f'{BASE}/tag/v{version}', draft=False, prerelease=False,
                assets=[dict(name=n+s, browser_download_url=f'{BASE}/download/v{version}/{n+s}', size=100)
                        for n in names for s in ('', '.sha256')])


def check(tmp_path, payload=None, **kwargs):
    return checker.check_for_update(session=FakeSession(payload or release()),
        state_path=tmp_path/'state.json', now=lambda: NOW, **kwargs)


@pytest.mark.parametrize('system,machine,filename', [
    ('win32', 'AMD64', f'Oxford-to-Notion-Setup-{NEW}.exe'),
    ('darwin', 'arm64', 'Oxford-to-Notion-macOS-arm64.dmg'),
    ('darwin', 'x86_64', None), ('linux', 'x86_64', None), ('win32', 'ARM64', None)])
def test_platform_asset_selection(tmp_path, system, machine, filename):
    info = check(tmp_path, system=system, machine=machine)
    assert info.version == NEW
    assert info.filename == filename
    assert bool(info.package_url) == bool(filename)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'foreign', 'huge', 'bool', 'port'])
def test_bad_assets_only_allow_release_page(tmp_path, mutation):
    payload = release()
    if mutation == 'missing':
        payload['assets'].pop(1)
    elif mutation == 'duplicate':
        payload['assets'].append(payload['assets'][0])
    elif mutation == 'foreign':
        payload['assets'][0]['browser_download_url'] = 'https://example.com/setup.exe'
    elif mutation == 'port':
        payload['assets'][0]['browser_download_url'] = payload['assets'][0]['browser_download_url'].replace('github.com', 'github.com:444')
    else:
        payload['assets'][0]['size'] = True if mutation == 'bool' else 200_000_001
    info = check(tmp_path, payload, system='win32', machine='AMD64')
    assert info.package_url is None
    assert info.release_url == f'{BASE}/tag/v{NEW}'


def test_manual_check_bypasses_cache_and_upgrade_hides_cached_update(tmp_path, monkeypatch):
    path = tmp_path/'state.json'
    first = check(tmp_path, system='win32', machine='AMD64')
    offline = FakeSession(error=requests.Timeout())
    args = dict(session=offline, state_path=path, now=lambda: NOW, system='win32', machine='AMD64')
    assert checker.check_for_update(**args) == first
    assert not offline.calls
    with pytest.raises(checker.UpdateCheckError):
        checker.check_for_update(**args, force=True)
    monkeypatch.setattr(checker, 'CURRENT_VERSION', NEW)
    assert checker.check_for_update(**args) is None


def test_network_failure_is_not_up_to_date(tmp_path):
    with pytest.raises(checker.UpdateCheckError):
        checker.check_for_update(session=FakeSession(error=requests.ConnectionError()), state_path=tmp_path/'state.json')


@pytest.mark.parametrize('field', ['draft', 'prerelease'])
def test_nonstable_releases_are_ignored(tmp_path, field):
    payload = release()
    payload[field] = True
    assert check(tmp_path, payload) is None


def test_malformed_release_is_failed_check(tmp_path):
    payload = release()
    payload['html_url'] = 'https://github.com/another/repo/releases/tag/v'+NEW
    with pytest.raises(checker.UpdateCheckError):
        check(tmp_path, payload)


def test_equal_and_older_versions_are_hidden(tmp_path):
    assert check(tmp_path, release(checker.CURRENT_VERSION), force=True) is None
    assert check(tmp_path, release('0.1.0'), force=True) is None


def test_cache_write_failure_does_not_discard_success(tmp_path):
    parent = tmp_path/'file'
    parent.write_text('not a directory')
    info = checker.check_for_update(session=FakeSession(release()), state_path=parent/'state')
    assert info.version == NEW


@pytest.mark.parametrize('age', [timedelta(days=2), timedelta(days=-2)])
def test_expired_or_future_cache_refetches(tmp_path, age):
    check(tmp_path)
    path = tmp_path/'state.json'
    payload = json.loads(path.read_text())
    payload['checked_at'] = (NOW-age).isoformat()
    path.write_text(json.dumps(payload))
    with pytest.raises(checker.UpdateCheckError):
        checker.check_for_update(session=FakeSession(error=requests.Timeout()), state_path=path, now=lambda: NOW)
