import hashlib
import os
import time
from dataclasses import replace
import pytest
import requests
from update_checker import UpdateInfo, RELEASES_BASE

DATA = b'example installer content'
NAME = 'Oxford-to-Notion-Setup-2.0.0.exe'
INFO = UpdateInfo('2.0.0', f'{RELEASES_BASE}/tag/v2.0.0',
                  f'{RELEASES_BASE}/download/v2.0.0/{NAME}',
                  f'{RELEASES_BASE}/download/v2.0.0/{NAME}.sha256', NAME, len(DATA))


class Response:
    def __init__(self, data, status=200, headers=None):
        self.data, self.status_code, self.headers = data, status, headers or {}
        self.closed = False
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()
    def iter_content(self, chunk_size):
        if isinstance(self.data, Exception):
            raise self.data
        yield self.data[:3]
        yield self.data[3:]
    def close(self):
        self.closed = True


class Session:
    def __init__(self, data=DATA, checksum=None):
        self.calls = []
        self.responses = [Response(checksum if checksum is not None else
            (hashlib.sha256(DATA).hexdigest()+'  '+NAME+'\n').encode()), Response(data)]
    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.responses.pop(0)


def test_verified_download_and_reuse(tmp_path):
    from update_downloader import download_update
    events = []
    path = download_update(INFO, session=Session(), cache_dir=tmp_path, progress=lambda n,t: events.append((n,t)))
    assert path.read_bytes() == DATA
    assert path.parent.name == '2.0.0'
    assert events[-1] == (len(DATA), len(DATA))
    session = Session()
    assert download_update(INFO, session=session, cache_dir=tmp_path) == path
    assert session.calls == [INFO.checksum_url]


@pytest.mark.parametrize('data,checksum,code', [
    (b'x'*len(DATA), None, 'integrity'), (DATA[:-1], None, 'integrity'),
    (DATA+b'x', None, 'size'), (requests.Timeout(), None, 'network'),
    (DATA, b'invalid', 'integrity'),
    (DATA, ('a'*64+'  wrong.exe').encode(), 'integrity'),
    (DATA, b'x'*16385, 'integrity')])
def test_failure_never_leaves_installable_file(tmp_path, data, checksum, code):
    from update_downloader import download_update, UpdateDownloadError
    with pytest.raises(UpdateDownloadError) as exc:
        download_update(INFO, session=Session(data, checksum), cache_dir=tmp_path)
    assert exc.value.code == code
    assert not list(tmp_path.rglob('*.exe'))
    assert not list(tmp_path.rglob('*.part'))


def test_checksum_requires_single_exact_entry():
    from update_downloader import parse_checksum, UpdateDownloadError
    good = hashlib.sha256(DATA).hexdigest()+'  '+NAME
    assert parse_checksum(good, NAME) == hashlib.sha256(DATA).hexdigest()
    for text in (good+'\n'+good, good+'x', 'garbage\n'+good):
        with pytest.raises(UpdateDownloadError):
            parse_checksum(text, NAME)


def test_unsafe_info_cannot_write_outside_cache(tmp_path):
    from update_downloader import download_update, UpdateDownloadError
    with pytest.raises(UpdateDownloadError):
        download_update(replace(INFO, filename='../evil.exe'), session=Session(), cache_dir=tmp_path)
    assert not list(tmp_path.iterdir())


def test_bad_redirect_is_rejected(tmp_path):
    from update_downloader import download_update, UpdateDownloadError
    session = Session()
    session.responses = [Response(b'', 302, {'Location':'https://example.com/evil'})]
    with pytest.raises(UpdateDownloadError):
        download_update(INFO, session=session, cache_dir=tmp_path)
    assert len(session.calls) == 1


def test_allowed_cdn_redirect(tmp_path):
    from update_downloader import download_update
    session = Session()
    session.responses.insert(0, Response(b'', 302, {'Location':'https://release-assets.githubusercontent.com/example?sig=abc'}))
    assert download_update(INFO, session=session, cache_dir=tmp_path).read_bytes() == DATA


def test_cancel_and_storage_failure(tmp_path):
    from update_downloader import download_update, UpdateDownloadError
    with pytest.raises(UpdateDownloadError) as exc:
        download_update(INFO, session=Session(), cache_dir=tmp_path, cancelled=lambda: True)
    assert exc.value.code == 'cancelled'
    blocked = tmp_path/'blocked'
    blocked.write_text('file')
    with pytest.raises(UpdateDownloadError) as exc:
        download_update(INFO, session=Session(), cache_dir=blocked)
    assert exc.value.code == 'storage'


def test_cleanup_keeps_recent_partial_and_verified_package(tmp_path):
    from update_downloader import cleanup_partial_downloads
    folder = tmp_path/'2.0.0'
    folder.mkdir()
    old, recent, complete = folder/'oton-old.part', folder/'oton-new.part', folder/NAME
    for path in (old, recent, complete):
        path.write_bytes(DATA)
    os.utime(old, (time.time()-172800, time.time()-172800))
    cleanup_partial_downloads(tmp_path)
    assert not old.exists()
    assert recent.exists() and complete.exists()


def test_declared_length_mismatch_rejected(tmp_path):
    from update_downloader import download_update, UpdateDownloadError
    session = Session()
    session.responses[1].headers['Content-Length'] = '900'
    with pytest.raises(UpdateDownloadError):
        download_update(INFO, session=session, cache_dir=tmp_path)
