import json
import pytest


def test_load_valid_version(tmp_path):
    from app_version import load_version
    path = tmp_path / 'version.json'
    path.write_text('{"version":"2.10.3"}', encoding='utf-8')
    assert load_version(path) == '2.10.3'


@pytest.mark.parametrize('value', [None, [], {}, {'version': True}, {'version': 'v1.2.3'},
                                 {'version': '1.2'}, {'version': '01.2.3'},
                                 {'version': '65536.0.0'}, {'version': '1.2.-1'}])
def test_reject_invalid_version(tmp_path, value):
    from app_version import load_version
    path = tmp_path / 'version.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError):
        load_version(path)


def test_missing_or_broken_version_fails(tmp_path):
    from app_version import load_version
    with pytest.raises(FileNotFoundError):
        load_version(tmp_path/'missing')
    path = tmp_path/'bad'
    path.write_text('{', encoding='utf-8')
    with pytest.raises(ValueError):
        load_version(path)
