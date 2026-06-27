"""Unit tests for the Gate 3 tmux adapter (RV1-030 visible-lane terminal seam).

The adapter is the only place that talks to the tmux binary. Tests inject a
fake runner so no real tmux process is required here; the live-tmux path is
exercised by the integration suite.
"""
from __future__ import annotations

import subprocess

import pytest

from creator_engine_validator.tmux_adapter import (
    TmuxAdapter,
    TmuxCwdMismatch,
    TmuxError,
    TmuxPane,
    TmuxUnavailable,
)


class FakeTmux:
    """Records tmux invocations and replays a canned identity line."""

    IDENTITY = "$3\t@7\t%9\t/dev/pts/4\t2222\n"

    def __init__(self, *, available: bool = True, existing_sessions=()):
        self.available = available
        self.existing = set(existing_sessions)
        self.calls: list[list[str]] = []

    def __call__(self, argv, check: bool = True):
        argv = list(argv)
        self.calls.append(argv)
        sub = argv[1] if len(argv) > 1 else ""
        if sub == "-V":
            if not self.available:
                raise FileNotFoundError("tmux")
            return subprocess.CompletedProcess(argv, 0, "tmux 3.6\n", "")
        if sub == "has-session":
            target = argv[-1]
            rc = 0 if target in self.existing else 1
            if rc and check:
                raise subprocess.CalledProcessError(rc, argv)
            return subprocess.CompletedProcess(argv, rc, "", "")
        if sub in ("new-session", "new-window"):
            return subprocess.CompletedProcess(argv, 0, self.IDENTITY, "")
        return subprocess.CompletedProcess(argv, 0, "", "")


def test_is_available_true_with_working_tmux():
    adapter = TmuxAdapter(runner=FakeTmux(available=True))
    assert adapter.is_available() is True


def test_is_available_false_when_tmux_missing():
    adapter = TmuxAdapter(runner=FakeTmux(available=False))
    assert adapter.is_available() is False


def test_ensure_pane_returns_full_tmux_identity():
    fake = FakeTmux(available=True)
    adapter = TmuxAdapter(runner=fake)
    pane = adapter.ensure_pane(session="ce-lane", window="lane-x", command=["sh", "-c", "true"])
    assert isinstance(pane, TmuxPane)
    assert pane.session_id == "$3"
    assert pane.window_id == "@7"
    assert pane.pane_id == "%9"
    assert pane.pane_tty == "/dev/pts/4"
    assert pane.pane_pid == 2222


def test_ensure_pane_creates_session_when_absent():
    fake = FakeTmux(available=True, existing_sessions=())
    adapter = TmuxAdapter(runner=fake)
    adapter.ensure_pane(session="ce-lane", window="lane-x", command=["sh", "-c", "true"])
    assert any(c[1] == "new-session" for c in fake.calls)
    assert not any(c[1] == "new-window" for c in fake.calls)


def test_ensure_pane_adds_window_when_session_exists():
    fake = FakeTmux(available=True, existing_sessions={"ce-lane"})
    adapter = TmuxAdapter(runner=fake)
    adapter.ensure_pane(session="ce-lane", window="lane-x", command=["sh", "-c", "true"])
    assert any(c[1] == "new-window" for c in fake.calls)
    assert not any(c[1] == "new-session" for c in fake.calls)


def test_ensure_pane_refuses_when_tmux_unavailable():
    adapter = TmuxAdapter(runner=FakeTmux(available=False))
    with pytest.raises(TmuxUnavailable):
        adapter.ensure_pane(session="ce-lane", window="lane-x", command=["sh", "-c", "true"])


def test_command_passed_through_after_separator():
    fake = FakeTmux(available=True)
    adapter = TmuxAdapter(runner=fake)
    adapter.ensure_pane(session="ce-lane", window="lane-x", command=["sh", "-c", "echo hi"])
    create = next(c for c in fake.calls if c[1] in ("new-session", "new-window"))
    assert create[-3:] == ["sh", "-c", "echo hi"]


@pytest.mark.parametrize(
    "identity",
    [
        # tmux build that PRESERVES the literal TAB delimiter (our dev box).
        "$0\t@0\t%0\t/dev/pts/1\t17075\n",
        # tmux build that SANITIZES the TAB to '_' in -F output (pilot Ubuntu
        # 24.04 / tmux 3.4) — the ce-ops#332 crash input.
        "$0_@0_%0_/dev/pts/1_17075\n",
    ],
    ids=["tab-separated", "underscore-sanitized"],
)
def test_parse_identity_tolerates_tab_and_underscore_separators(identity):
    pane = TmuxAdapter._parse_identity(identity)
    assert pane.session_id == "$0"
    assert pane.window_id == "@0"
    assert pane.pane_id == "%0"
    assert pane.pane_tty == "/dev/pts/1"
    assert pane.pane_pid == 17075


def test_parse_identity_raises_on_unparseable_output():
    # A single empty/garbage token must still raise (regression guard: the
    # underscore-tolerant split must not silently accept a non-identity line).
    with pytest.raises(TmuxError):
        TmuxAdapter._parse_identity("\n")


def test_ensure_pane_parses_underscore_sanitized_identity():
    """End-to-end ensure_pane on a tmux build that sanitizes the TAB to '_'."""

    class FakeUnderscoreTmux(FakeTmux):
        IDENTITY = "$0_@0_%0_/dev/pts/1_17075\n"

    fake = FakeUnderscoreTmux(available=True)
    adapter = TmuxAdapter(runner=fake)
    pane = adapter.ensure_pane(session="ce-lane", window="lane-x", command=["sh", "-c", "true"])
    assert pane.session_id == "$0"
    assert pane.window_id == "@0"
    assert pane.pane_id == "%0"
    assert pane.pane_tty == "/dev/pts/1"
    assert pane.pane_pid == 17075


_NOOP_SLEEP = lambda *_: None


class FakeTmuxCwd:
    """Fake runner modelling tmux honoring ``-c`` with a *delayed* cwd settle.

    Identity is returned at creation (no ``pane_current_path``); the cwd is
    reported only via post-spawn ``display-message``. ``force_cwd`` makes the pane
    never settle to the request (mismatch path); ``settle_after`` reports the
    server cwd for the first N polls, then the requested cwd.
    """

    def __init__(self, *, force_cwd=None, settle_after=0):
        self.force_cwd = force_cwd
        self.settle_after = settle_after
        self.calls: list[list[str]] = []
        self.spawn_cwd = None
        self._dm = 0

    def __call__(self, argv, check: bool = True):
        argv = list(argv)
        self.calls.append(argv)
        sub = argv[1] if len(argv) > 1 else ""
        if sub == "-V":
            return subprocess.CompletedProcess(argv, 0, "tmux 3.6\n", "")
        if sub == "has-session":
            return subprocess.CompletedProcess(argv, 1, "", "")
        if sub in ("new-session", "new-window"):
            if "-c" in argv:
                self.spawn_cwd = argv[argv.index("-c") + 1]
            return subprocess.CompletedProcess(argv, 0, "$1\t@2\t%3\t/dev/pts/0\t1234\n", "")
        if sub == "display-message":
            self._dm += 1
            if self.force_cwd is not None:
                return subprocess.CompletedProcess(argv, 0, self.force_cwd + "\n", "")
            if self._dm <= self.settle_after:
                return subprocess.CompletedProcess(argv, 0, "/home/nefarious/projects\n", "")
            return subprocess.CompletedProcess(argv, 0, (self.spawn_cwd or "") + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")


def test_ensure_pane_enforces_and_verifies_cwd(tmp_path):
    fake = FakeTmuxCwd()
    adapter = TmuxAdapter(runner=fake, sleeper=_NOOP_SLEEP)
    pane = adapter.ensure_pane(
        session="ce-lane", window="lane-x", command=["sh", "-c", "true"], cwd=str(tmp_path)
    )
    create = next(c for c in fake.calls if c[1] in ("new-session", "new-window"))
    assert "-c" in create and create[create.index("-c") + 1] == str(tmp_path)
    # cwd must be verified via display-message, not the creation-time identity format
    fmt = create[create.index("-F") + 1]
    assert "pane_current_path" not in fmt
    assert any(c[1] == "display-message" for c in fake.calls)
    assert pane.pane_cwd == str(tmp_path)


def test_ensure_pane_tolerates_delayed_cwd_settle(tmp_path):
    fake = FakeTmuxCwd(settle_after=2)  # wrong cwd for first 2 polls, then correct
    adapter = TmuxAdapter(runner=fake, sleeper=_NOOP_SLEEP, cwd_poll_attempts=5)
    pane = adapter.ensure_pane(
        session="ce-lane", window="lane-x", command=["sh", "-c", "true"], cwd=str(tmp_path)
    )
    assert pane.pane_cwd == str(tmp_path)


def test_ensure_pane_raises_and_kills_pane_when_cwd_never_settles(tmp_path):
    fake = FakeTmuxCwd(force_cwd="/somewhere/else")
    adapter = TmuxAdapter(runner=fake, sleeper=_NOOP_SLEEP, cwd_poll_attempts=3)
    with pytest.raises(TmuxCwdMismatch):
        adapter.ensure_pane(
            session="ce-lane", window="lane-x", command=["sh", "-c", "true"], cwd=str(tmp_path)
        )
    assert any(c[1] == "kill-pane" for c in fake.calls)


def test_ensure_pane_without_cwd_omits_dash_c_and_does_not_poll():
    fake = FakeTmuxCwd()
    adapter = TmuxAdapter(runner=fake, sleeper=_NOOP_SLEEP)
    # Command intentionally has no "-c" so the only possible "-c" would be the
    # tmux start-directory flag, which must be absent when cwd is not given.
    adapter.ensure_pane(session="ce-lane", window="lane-x", command=["true"])
    create = next(c for c in fake.calls if c[1] in ("new-session", "new-window"))
    flags = create[: create.index("true")]
    assert "-c" not in flags
    assert not any(c[1] == "display-message" for c in fake.calls)
