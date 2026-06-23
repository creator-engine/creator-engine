"""Unit tests for the visibility-backend registry + tmux backend (ce-ops#207 W1).

W1 is a pure structural seam: it introduces the ``VisibilityBackend`` registry
(mirroring ``runner/backend.py``) and a thin ``TmuxVisibilityBackend`` that
reproduces today's tmux spawn behaviour exactly. These tests prove the registry
ergonomics and that the tmux backend returns the *same* terminal record the
launcher built before the seam existed.
"""
from __future__ import annotations

import pytest

from creator_engine_validator import visibility_backend as vb
from creator_engine_validator.tmux_adapter import TmuxPane, TmuxUnavailable


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------
class FakeAdapter:
    """In-memory tmux adapter double — mirrors the lane_runtime test double."""

    kind = "tmux"

    def __init__(self, *, available: bool = True, pane: TmuxPane | None = None):
        self._available = available
        self._pane = pane
        self.spawned: list[tuple[str, str, list[str]]] = []
        self.last_cwd = None
        self.last_env = None

    def is_available(self) -> bool:
        return self._available

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append((session, window, list(command)))
        self.last_cwd = cwd
        self.last_env = dict(env) if env else None
        if self._pane is not None:
            return self._pane
        return TmuxPane(
            session_id="$1",
            window_id="@2",
            pane_id="%3",
            pane_tty="/dev/pts/9",
            pane_pid=4242,
            pane_cwd=(str(cwd) if cwd else None),
        )


# ---------------------------------------------------------------------------
# Registry ergonomics (mirror of the runner-backend registry tests)
# ---------------------------------------------------------------------------
def test_tmux_backend_is_registered_by_default():
    assert vb.TMUX_TERMINAL_KIND in vb.available_visibility_kinds()
    backend = vb.get_visibility_backend(vb.TMUX_TERMINAL_KIND)
    assert isinstance(backend, vb.TmuxVisibilityBackend)
    assert backend.terminal_kind == "tmux"
    assert backend.visibility_class == vb.OPERATOR_VISIBLE


def test_get_unknown_kind_fails_closed():
    with pytest.raises(vb.UnknownVisibilityBackend) as exc:
        vb.get_visibility_backend("does-not-exist")
    # The error names the unknown kind and lists the available ones (fail-closed).
    assert "does-not-exist" in str(exc.value)
    assert "tmux" in str(exc.value)


def test_register_is_fresh_instance_per_get():
    a = vb.get_visibility_backend(vb.TMUX_TERMINAL_KIND)
    b = vb.get_visibility_backend(vb.TMUX_TERMINAL_KIND)
    assert a is not b  # factory returns a fresh instance, like runner/backend.py


def test_double_register_refuses():
    sentinel_kind = "test-double-register-kind"
    vb.register_visibility_backend(sentinel_kind, vb.TmuxVisibilityBackend)
    try:
        with pytest.raises(vb.VisibilityBackendAlreadyRegistered):
            vb.register_visibility_backend(sentinel_kind, vb.TmuxVisibilityBackend)
    finally:
        vb._REGISTRY.pop(sentinel_kind, None)


def test_available_kinds_is_sorted_tuple():
    kinds = vb.available_visibility_kinds()
    assert isinstance(kinds, tuple)
    assert list(kinds) == sorted(kinds)


# ---------------------------------------------------------------------------
# Tmux backend reproduces the pre-seam terminal record EXACTLY (zero regression)
# ---------------------------------------------------------------------------
def test_tmux_backend_returns_existing_terminal_record():
    adapter = FakeAdapter()
    backend = vb.TmuxVisibilityBackend(adapter)
    handle = backend.ensure_surface(
        session="ce-lane",
        window="gate3-lane",
        command=["/bin/sh", "wrapper.sh"],
        cwd="/worktrees/lane",
        env={"CE_LEDGER_ROOT": "/abs/ledger"},
    )
    # visibility_class is the record-level value the launcher stamps.
    assert handle.visibility_class == vb.OPERATOR_VISIBLE
    # The terminal mapping reproduces lane_runtime.py:980-992 byte-for-byte.
    assert handle.terminal == {
        "kind": "tmux",
        "session_id": "$1",
        "window_id": "@2",
        "pane_id": "%3",
        "pane_tty": "/dev/pts/9",
        "pane_pid": 4242,
    }
    # The native TmuxPane is preserved so the launcher's LaunchResult.pane is
    # byte-identical to the pre-seam behaviour (zero regression).
    assert isinstance(handle.native, TmuxPane)
    assert handle.native.pane_id == "%3"
    # The spawn was delegated to the injected adapter with the same kwargs.
    assert adapter.spawned == [("ce-lane", "gate3-lane", ["/bin/sh", "wrapper.sh"])]
    assert adapter.last_cwd == "/worktrees/lane"
    assert adapter.last_env == {"CE_LEDGER_ROOT": "/abs/ledger"}


def test_tmux_backend_omits_optional_pane_fields_when_absent():
    """When the adapter reports no tty/pid, the record omits them — as before."""
    pane = TmuxPane(session_id="$9", window_id="@9", pane_id="%9")
    backend = vb.TmuxVisibilityBackend(FakeAdapter(pane=pane))
    handle = backend.ensure_surface(
        session="s", window="w", command=["true"], cwd=None, env=None
    )
    assert handle.terminal == {
        "kind": "tmux",
        "session_id": "$9",
        "window_id": "@9",
        "pane_id": "%9",
    }


def test_tmux_backend_availability_delegates_to_adapter():
    assert vb.TmuxVisibilityBackend(FakeAdapter(available=True)).is_available() is True
    assert vb.TmuxVisibilityBackend(FakeAdapter(available=False)).is_available() is False


def test_tmux_backend_propagates_tmux_unavailable():
    class Boom(FakeAdapter):
        def ensure_pane(self, **kwargs):
            raise TmuxUnavailable("no tmux server")

    backend = vb.TmuxVisibilityBackend(Boom())
    with pytest.raises(TmuxUnavailable):
        backend.ensure_surface(session="s", window="w", command=["true"])


def test_default_constructed_tmux_backend_uses_real_adapter():
    """No injected adapter → a real TmuxAdapter is built (no spawn here)."""
    from creator_engine_validator.tmux_adapter import TmuxAdapter

    backend = vb.TmuxVisibilityBackend()
    assert isinstance(backend._adapter, TmuxAdapter)


# ---------------------------------------------------------------------------
# Headless backend (ce-ops#207 W2′) — CE owns the seat under its own PTY.
# ---------------------------------------------------------------------------
from creator_engine_validator.seat_pty_session import SeatPtySession  # noqa: E402


class FakePtySpawn:
    """In-memory PTY spawner double — records the spawn, never forks."""

    def __init__(self, *, pid: int = 9191):
        self._pid = pid
        self.calls: list[dict] = []

    def __call__(self, *, command, seat_dir, cwd=None, env=None):
        from pathlib import Path

        self.calls.append(
            {"command": list(command), "seat_dir": str(seat_dir), "cwd": cwd,
             "env": dict(env) if env else None}
        )
        return SeatPtySession(
            pid=self._pid,
            master_fd=7,
            surface_ref=str(Path(seat_dir) / "attach.sock"),
        )


def test_headless_backend_is_registered_by_default():
    assert vb.HEADLESS_TERMINAL_KIND in vb.available_visibility_kinds()
    backend = vb.get_visibility_backend(vb.HEADLESS_TERMINAL_KIND)
    assert isinstance(backend, vb.HeadlessVisibilityBackend)
    assert backend.terminal_kind == "headless"
    assert backend.visibility_class == vb.OPERATOR_INSPECTABLE


def test_headless_backend_is_always_available():
    # The no-tmux fallback: a writable seat dir + pty.fork are the only needs.
    assert vb.HeadlessVisibilityBackend(FakePtySpawn()).is_available() is True


def test_headless_backend_inspectable_class_satisfies_the_contract():
    assert vb.OPERATOR_INSPECTABLE in vb.SATISFYING_VISIBILITY_CLASSES
    assert vb.OPERATOR_VISIBLE in vb.SATISFYING_VISIBILITY_CLASSES


def test_headless_backend_builds_headless_terminal_record(tmp_path):
    spawn = FakePtySpawn(pid=4242)
    backend = vb.HeadlessVisibilityBackend(spawn)
    handle = backend.ensure_surface(
        session="ce-lane",
        window="gate3-lane",
        command=["/bin/sh", "wrapper.sh"],
        cwd=str(tmp_path),
        env={"CE_LEDGER_ROOT": "/abs/ledger"},
        seat_dir=str(tmp_path),
    )
    assert handle.visibility_class == vb.OPERATOR_INSPECTABLE
    # The terminal record is the headless surface: a control-socket ref + pid,
    # NOT session/window/pane ids.
    assert handle.terminal == {
        "kind": "headless",
        "surface_ref": str(tmp_path / "attach.sock"),
        "pid": 4242,
    }
    # The native handle is the live CE-owned PTY session (master fd held by CE).
    assert isinstance(handle.native, SeatPtySession)
    assert handle.native.master_fd == 7
    # The spawn received the sentinel-wrapped argv + the seat env (pinned, not echoed).
    assert spawn.calls == [{
        "command": ["/bin/sh", "wrapper.sh"],
        "seat_dir": str(tmp_path),
        "cwd": str(tmp_path),
        "env": {"CE_LEDGER_ROOT": "/abs/ledger"},
    }]


def test_headless_backend_requires_seat_dir():
    backend = vb.HeadlessVisibilityBackend(FakePtySpawn())
    with pytest.raises(vb.VisibilityBackendError):
        backend.ensure_surface(
            session="s", window="w", command=["true"], seat_dir=None
        )


def test_headless_backend_does_not_persist_pty_bytes(tmp_path):
    """W2′ invariant: owning the master fd != streaming it. No new byte surface.

    The raw PTY stream is gated behind W2-sec/T1; this unit must NOT write the
    seat's stdout/stderr (which can carry secrets) to any log/file. The headless
    spawn must leave no captured-output artifact in the seat dir.
    """
    backend = vb.HeadlessVisibilityBackend(FakePtySpawn())
    before = set(p.name for p in tmp_path.iterdir())
    backend.ensure_surface(
        session="s", window="w", command=["true"],
        env={"CE_LEDGER_ROOT": "/secret/ledger"}, seat_dir=str(tmp_path),
    )
    after = set(p.name for p in tmp_path.iterdir())
    # No headless.log / captured-output file was created by the surface.
    assert not any("log" in name.lower() for name in (after - before))
