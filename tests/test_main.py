from types import SimpleNamespace

import main
from exceptions import ConfigurationError, OxfordNetworkError


class FakeOxford:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def lookup(self, word):
        if self.error:
            raise self.error
        return self.result


class FakeNotion:
    def upsert(self, entry):
        return "https://notion.test/page"


def test_run_reports_success(capsys):
    entry = SimpleNamespace(word="brutality")

    code = main.run(["brutality"], oxford=FakeOxford(entry), notion=FakeNotion())

    assert code == 0
    assert "https://notion.test/page" in capsys.readouterr().out


def test_run_rejects_invalid_word(capsys):
    code = main.run(["two words"], oxford=FakeOxford(), notion=FakeNotion())

    assert code == 2
    assert "English word" in capsys.readouterr().err


def test_run_reports_operational_error_without_traceback(capsys):
    code = main.run(
        ["brutality"],
        oxford=FakeOxford(error=OxfordNetworkError("Oxford request failed.")),
        notion=FakeNotion(),
    )

    assert code == 1
    assert "Oxford request failed" in capsys.readouterr().err


def test_run_reports_configuration_error(monkeypatch, capsys):
    def fail_dependencies():
        raise ConfigurationError("Missing NOTION_TOKEN")

    monkeypatch.setattr(main, "build_dependencies", fail_dependencies)

    assert main.run(["brutality"]) == 1
    assert "NOTION_TOKEN" in capsys.readouterr().err


def test_run_hides_unexpected_dependency_details(capsys):
    class BrokenNotion:
        def upsert(self, entry):
            raise RuntimeError("secret transport details")

    code = main.run(
        ["brutality"],
        oxford=FakeOxford(SimpleNamespace(word="brutality")),
        notion=BrokenNotion(),
    )

    error = capsys.readouterr().err
    assert code == 1
    assert "Unexpected failure" in error
    assert "secret transport" not in error
