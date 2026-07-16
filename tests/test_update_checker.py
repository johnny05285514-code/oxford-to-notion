import json
from datetime import datetime, timedelta, timezone

import requests

from update_checker import CURRENT_VERSION, UpdateInfo, check_for_update, parse_version


NOW = datetime(2026, 7, 12, 2, 0, 0, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def release(version="v1.5.0", **overrides):
    payload = {
        "tag_name": version,
        "html_url": "https://github.com/johnny/repo/releases/tag/v1.5.0",
        "draft": False,
        "prerelease": False,
    }
    payload.update(overrides)
    return payload


def test_version_parser_accepts_v_prefix_and_rejects_invalid_values():
    assert CURRENT_VERSION == "1.4.3"
    assert parse_version("v1.4.2") == (1, 4, 2)
    assert parse_version("1.5") == (1, 5, 0)
    assert parse_version("latest") is None
    assert parse_version("1.2.3.4") is None


def test_newer_stable_release_returns_update_and_writes_cache(tmp_path):
    path = tmp_path / "update-state.json"
    session = FakeSession(FakeResponse(release()))

    result = check_for_update(session=session, state_path=path, now=lambda: NOW)

    assert result == UpdateInfo("1.5.0", release()["html_url"])
    assert session.calls[0][1]["timeout"] <= 10
    assert "Oxford-to-Notion" in session.calls[0][1]["headers"]["User-Agent"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["checked_at"] == NOW.isoformat()
    assert payload["update"]["version"] == "1.5.0"


def test_fresh_cache_is_reused_without_network(tmp_path):
    path = tmp_path / "update-state.json"
    path.write_text(
        json.dumps(
            {
                "checked_at": (NOW - timedelta(hours=2)).isoformat(),
                "update": {
                    "version": "1.5.0",
                    "release_url": "https://github.com/johnny/repo/releases/tag/v1.5.0",
                },
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(error=AssertionError("network must not be called"))

    result = check_for_update(session=session, state_path=path, now=lambda: NOW)

    assert result == UpdateInfo(
        "1.5.0", "https://github.com/johnny/repo/releases/tag/v1.5.0"
    )
    assert session.calls == []


def test_stale_cache_refreshes_and_hides_older_release(tmp_path):
    path = tmp_path / "update-state.json"
    path.write_text(
        json.dumps({"checked_at": (NOW - timedelta(days=2)).isoformat(), "update": None}),
        encoding="utf-8",
    )
    session = FakeSession(FakeResponse(release("v1.3.0")))

    assert check_for_update(session=session, state_path=path, now=lambda: NOW) is None
    assert len(session.calls) == 1


def test_draft_prerelease_malformed_or_unsafe_release_is_ignored(tmp_path):
    payloads = [
        release(draft=True),
        release(prerelease=True),
        release(version="not-a-version"),
        release(html_url="javascript:alert(1)"),
        {"tag_name": "v2.0.0"},
    ]
    for index, payload in enumerate(payloads):
        path = tmp_path / f"state-{index}.json"
        assert check_for_update(
            session=FakeSession(FakeResponse(payload)),
            state_path=path,
            now=lambda: NOW,
        ) is None


def test_network_and_json_failures_are_silent(tmp_path):
    sessions = [
        FakeSession(error=requests.Timeout("slow")),
        FakeSession(FakeResponse(ValueError("bad json"))),
        FakeSession(FakeResponse({}, status_code=500)),
    ]
    for index, session in enumerate(sessions):
        assert check_for_update(
            session=session,
            state_path=tmp_path / f"state-{index}.json",
            now=lambda: NOW,
        ) is None
