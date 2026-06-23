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
# Herdr backend (ce-ops#217 U3) — live inspectable surface over herdr socket.
# ---------------------------------------------------------------------------
from creator_engine_validator.runner.herdr_session import HerdrPane  # noqa: E402


class FakeHerdrSession:
    def __init__(self, *, socket_path, herdr_binary="herdr"):
        self.socket_path = str(socket_path)
        self.herdr_binary = herdr_binary
        self.spawn_calls: list[dict] = []
        self.observed: list[str] = []
        self.waited: list[tuple[str, str]] = []

    def spawn_pane(self, *, command, cwd=None, env=None, label=None):
        self.spawn_calls.append({
            "command": list(command),
            "cwd": cwd,
            "env": dict(env) if env else None,
            "label": label,
        })
        return HerdrPane(
            pane_id="pane-1",
            surface_ref=self.socket_path,
            pid=4242,
            workspace_id="workspace-1",
        )

    def observe(self, pane):
        self.observed.append(pane.pane_id)
        return b"recent output"

    def wait_agent_status(self, pane, *, status="ready"):
        self.waited.append((pane.pane_id, status))
        return {"pane_id": pane.pane_id, "status": status}


def test_herdr_backend_is_registered_by_default():
    assert vb.HERDR_TERMINAL_KIND in vb.available_visibility_kinds()
    backend = vb.get_visibility_backend(vb.HERDR_TERMINAL_KIND)
    assert isinstance(backend, vb.HerdrVisibilityBackend)
    assert backend.terminal_kind == "herdr"
    assert backend.visibility_class == vb.OPERATOR_INSPECTABLE


def test_headless_pty_backend_is_retired_from_registry():
    assert vb.HEADLESS_TERMINAL_KIND not in vb.available_visibility_kinds()
    with pytest.raises(vb.UnknownVisibilityBackend):
        vb.get_visibility_backend(vb.HEADLESS_TERMINAL_KIND)


def test_herdr_backend_availability_uses_injected_session_factory():
    assert vb.HerdrVisibilityBackend(lambda **kw: FakeHerdrSession(**kw)).is_available() is True


def test_headless_backend_inspectable_class_satisfies_the_contract():
    assert vb.OPERATOR_INSPECTABLE in vb.SATISFYING_VISIBILITY_CLASSES
    assert vb.OPERATOR_VISIBLE in vb.SATISFYING_VISIBILITY_CLASSES


def test_herdr_backend_builds_terminal_record_and_keeps_socket_controller_owned(tmp_path):
    sessions: list[FakeHerdrSession] = []

    def factory(**kwargs):
        session = FakeHerdrSession(**kwargs)
        sessions.append(session)
        return session

    backend = vb.HerdrVisibilityBackend(
        factory,
        substrate_socket_dir="/run/ce/herdr",
    )
    handle = backend.ensure_surface(
        session="ce-lane",
        window="gate3-lane",
        command=["/bin/sh", "wrapper.sh"],
        cwd=str(tmp_path),
        env={"CE_LEDGER_ROOT": "/abs/ledger"},
        seat_dir=str(tmp_path),
    )
    assert handle.visibility_class == vb.OPERATOR_INSPECTABLE
    # The terminal record is the herdr surface: the controller-owned socket ref,
    # herdr pane id, and seat pid. No tmux identity is present.
    assert handle.terminal == {
        "kind": "herdr",
        "surface_ref": "/run/ce/herdr/control.sock",
        "pane_id": "pane-1",
        "pid": 4242,
    }
    assert isinstance(handle.native, HerdrPane)
    # The socket is held by the controller-side session, not passed to the seat env.
    assert sessions[0].socket_path == "/run/ce/herdr/control.sock"
    assert sessions[0].spawn_calls == [{
        "command": ["/bin/sh", "wrapper.sh"],
        "cwd": str(tmp_path),
        "env": {"CE_LEDGER_ROOT": "/abs/ledger"},
        "label": "gate3-lane",
    }]
    assert "HERDR_SOCKET" not in sessions[0].spawn_calls[0]["env"]


def test_herdr_backend_observe_and_wait_delegate_to_controller_session(tmp_path):
    session = FakeHerdrSession(socket_path="/run/ce/herdr/control.sock")
    backend = vb.HerdrVisibilityBackend(lambda **_kw: session)
    handle = backend.ensure_surface(
        session="s", window="w", command=["true"], seat_dir=str(tmp_path)
    )
    assert backend.observe(handle.native) == b"recent output"
    assert backend.wait_agent_status(handle.native) == {
        "pane_id": "pane-1",
        "status": "ready",
    }


def test_herdr_backend_requires_seat_dir():
    backend = vb.HerdrVisibilityBackend(lambda **kw: FakeHerdrSession(**kw))
    with pytest.raises(vb.VisibilityBackendError):
        backend.ensure_surface(
            session="s", window="w", command=["true"], seat_dir=None
        )


def test_herdr_backend_honors_u2_socket_overlap_refusal(tmp_path):
    """§7 invariant: the governed seat cannot reach the herdr control socket."""
    backend = vb.HerdrVisibilityBackend(
        lambda **kw: FakeHerdrSession(**kw),
        substrate_socket_dir=str(tmp_path),
    )
    with pytest.raises(vb.VisibilityBackendError) as exc:
        backend.ensure_surface(
            session="s",
            window="w",
            command=["true"],
            seat_dir=str(tmp_path),
        )
    assert "overlaps" in str(exc.value)
