import gui


def test_main_smoke_mode_initializes_without_showing(monkeypatch):
    events = []

    class FakeApp:
        @staticmethod
        def instance():
            return None

        def __init__(self, argv):
            events.append(("app", argv))

        def setApplicationName(self, _name):
            pass

        def setFont(self, _font):
            pass

        def setWindowIcon(self, _icon):
            pass

        def exec(self):
            events.append(("exec", None))
            return 0

    class FakeWindow:
        def __init__(self, **kwargs):
            events.append(("window", kwargs))

        def show(self):
            events.append(("show", None))

    monkeypatch.setattr(gui, "QApplication", FakeApp)
    monkeypatch.setattr(gui, "OxfordToNotionWindow", FakeWindow)
    monkeypatch.setattr(gui, "build_ui_font", lambda: object())
    monkeypatch.setattr(gui, "QIcon", lambda _path: object())

    assert gui.main(["gui.py", "--smoke-test"]) == 0
    assert events == [
        ("app", ["gui.py", "--smoke-test"]),
        (
            "window",
            {"start_update_check": False, "enable_recent_sync": False},
        ),
    ]
