from pathlib import Path

import pytest
import requests

from exceptions import OxfordBlockedError, OxfordNetworkError, WordNotFoundError
from oxford_client import OxfordClient


HTML = (Path(__file__).parent / "fixtures" / "brutality_excerpt.html").read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, status_code=200, text=HTML, url="https://example.test/final"):
        self.status_code = status_code
        self.text = text
        self.url = url


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.headers = {}

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_lookup_builds_safe_url_and_sets_user_agent():
    session = FakeSession([FakeResponse()])
    client = OxfordClient(session=session, sleep=lambda _: None)

    entry = client.lookup("Brutality")

    assert session.calls[0][0].endswith("/definition/english/brutality")
    assert "Oxford-to-Notion/1.4.4" in session.headers["User-Agent"]
    assert entry.word == "brutality"


def test_lookup_rejects_invalid_word_before_request():
    session = FakeSession([])

    with pytest.raises(ValueError, match="English word"):
        OxfordClient(session=session).lookup("two words")

    assert session.calls == []


def test_lookup_reports_not_found():
    client = OxfordClient(session=FakeSession([FakeResponse(status_code=404)]), sleep=lambda _: None)

    with pytest.raises(WordNotFoundError):
        client.lookup("nonexistentword")


def test_lookup_detects_access_challenge():
    response = FakeResponse(text="<html>Enable JavaScript and cookies to continue</html>")
    client = OxfordClient(session=FakeSession([response]), sleep=lambda _: None)

    with pytest.raises(OxfordBlockedError):
        client.lookup("brutality")


def test_lookup_retries_transient_network_error():
    session = FakeSession([requests.ConnectionError("offline"), FakeResponse()])
    client = OxfordClient(session=session, max_attempts=2, sleep=lambda _: None)

    assert client.lookup("brutality").word == "brutality"
    assert len(session.calls) == 2


def test_lookup_wraps_network_error_without_leaking_details():
    session = FakeSession([requests.Timeout("secret endpoint details")])
    client = OxfordClient(session=session, max_attempts=1, sleep=lambda _: None)

    with pytest.raises(OxfordNetworkError, match="Oxford") as error:
        client.lookup("brutality")

    assert "secret endpoint" not in str(error.value)
