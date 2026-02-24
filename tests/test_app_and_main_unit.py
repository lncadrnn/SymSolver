from gui.app import SymSolverApp
import gui.app as app_module
import main as entry


class _FakeLoading:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


class _FakeEntry:
    def __init__(self):
        self.focused = False

    def focus_set(self):
        self.focused = True


class _FakeContainer:
    pass


class _FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.packed = False

    def pack(self, *args, **kwargs):
        self.packed = True


class _FakeTk:
    X = "x"
    LEFT = "left"

    Frame = _FakeWidget
    Label = _FakeWidget


def test_friendly_error_for_parse_and_generic() -> None:
    msg_parse = SymSolverApp._friendly_error("2x +", ValueError("Could not parse expression"))
    assert "Could not understand" in msg_parse

    msg_generic = SymSolverApp._friendly_error("2x+1=0", RuntimeError("boom"))
    assert "could not process" in msg_generic.lower()
    assert "Details: boom" in msg_generic


def test_show_error_ui_path_does_not_crash(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "tk", _FakeTk)

    class _FakeApp:
        def __init__(self):
            self._chat_frame = _FakeContainer()
            self._bold = object()
            self._default = object()
            self._entry = _FakeEntry()
            self._PHASE_PAUSE = 0
            self._TYPING_SPEED = 0
            self.input_state = None

        def _set_input_state(self, enabled: bool) -> None:
            self.input_state = enabled

        def _scroll_to_bottom(self) -> None:
            self.scrolled = True

    fake_app = _FakeApp()
    loading = _FakeLoading()

    SymSolverApp._show_error(fake_app, "Invalid equation", loading)

    assert loading.destroyed is True
    assert fake_app.input_state is True
    assert fake_app._entry.focused is True


def test_main_entry_runs_app(monkeypatch) -> None:
    called = {"mainloop": False}

    class DummyApp:
        def mainloop(self):
            called["mainloop"] = True

    monkeypatch.setattr(entry, "SymSolverApp", DummyApp)
    entry.main()
    assert called["mainloop"] is True
