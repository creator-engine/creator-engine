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
