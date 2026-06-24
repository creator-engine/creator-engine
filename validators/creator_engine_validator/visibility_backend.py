"""Visibility-backend registry — the witnessability/surface seam (ce-ops#207, W1).

`ce lane launch` must, for a visibility-required role, spawn an
operator-inspectable surface or fail closed. Historically that surface was a
hard-wired tmux pane. This module introduces a **visibility-backend
abstraction** — modelled on the runner-backend registry
(``runner/backend.py``: an ABC + ``register_*`` / ``get_*`` / ``_REGISTRY``
keyed by a string) — so the spawn seam routes through a named backend keyed by
``terminal.kind`` instead of calling tmux directly.

Design invariants (deliberate, load-bearing):

* **Separate from ``RunnerBackend``.** ``RunnerBackend`` is the *sandbox /
  runtime* tier (``os-native`` / ``openshell`` / ``gvisor`` — *where* the process
  runs). A visibility backend is the *witnessability / surface* tier (*how* the
  lane is observed and recorded). They compose orthogonally (a gVisor-sandboxed
  seat with a headless surface), so they get distinct registries. This module
  deliberately copies the proven ``RunnerBackend`` ergonomics (string key,
  factory, fail-closed ``get_*``).
* **Substrate-specific implementations.** ``TmuxVisibilityBackend`` remains a
  THIN wrapper over ``tmux_adapter.TmuxAdapter``. ``HeadlessVisibilityBackend``
  is a logged/streamed ``operator_inspectable`` implementation for autonomous
  seats with no watched pane. ``HerdrVisibilityBackend`` drives herdr as a
  separate process over the substrate-owned control socket.
* **No validator check.** Nothing here is ``@register``-ed; importing this
  module registers no validator check and runs no I/O on import.
"""
from __future__ import annotations

import abc
import json
import os
import shutil
import subprocess
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .runner.herdr_containment import (
    DEFAULT_HERDR_BINARY,
    DEFAULT_HERDR_SOCKET_NAME,
    DEFAULT_SUBSTRATE_SOCKET_DIR,
    HerdrContainmentInvariantViolation,
    plan_herdr_containment,
)
from .runner.herdr_session import (
    HERDR_TERMINAL_KIND,
    HerdrCommandError,
    HerdrPane,
    HerdrSession,
)
from .tmux_adapter import TmuxAdapter, TmuxUnavailable

# The terminal kind / visibility class vocabulary. ``operator_visible`` is the
# tmux class (a human can attach a live pane); ``operator_inspectable`` is the
# non-tmux class (a recorded surface, no live pane). Both satisfy the visibility
# *contract*.
TMUX_TERMINAL_KIND = "tmux"
HEADLESS_TERMINAL_KIND = "headless"
OPERATOR_VISIBLE = "operator_visible"
OPERATOR_INSPECTABLE = "operator_inspectable"

# The visibility classes that SATISFY the visibility contract (the C1 gate).
# A visibility-required role may launch onto any backend whose class is here;
# an unknown / non-satisfying surface is still refused (the load-bearing
# refusal). ``operator_inspectable`` = a non-tmux surface with an inspectable
# evidence spine.
SATISFYING_VISIBILITY_CLASSES = frozenset({OPERATOR_VISIBLE, OPERATOR_INSPECTABLE})


# ---------------------------------------------------------------------------
# Errors — mirror the runner-backend error hierarchy.
# ---------------------------------------------------------------------------
class VisibilityBackendError(Exception):
    """Base class for visibility-backend registry errors."""


class UnknownVisibilityBackend(VisibilityBackendError):
    """No visibility backend is registered under the requested terminal kind."""


class VisibilityBackendAlreadyRegistered(VisibilityBackendError):
    """A visibility backend is already registered under the requested kind."""


# ---------------------------------------------------------------------------
# Surface handle — the terminal record the Pane Registry writes.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SurfaceHandle:
    """The result of ensuring a visibility surface for a launched lane.

    ``terminal`` is the exact ``terminal`` mapping the caller stamps onto the
    Pane Registry record (``{"kind": ..., ...}``); ``visibility_class`` is the
    record-level ``visibility`` value. Carrying the whole mapping keeps the
    spawn seam backend-agnostic — the caller never special-cases tmux ids.
    """

    visibility_class: str
    terminal: dict[str, Any]
    #: The backend's native surface handle (e.g. the ``TmuxPane`` for the tmux
    #: backend). Carried so the launcher can preserve the exact ``LaunchResult``
    #: shape it returned before this seam existed (zero behaviour change in W1).
    #: ``None`` for backends with no native object surface.
    native: Any = None


# ---------------------------------------------------------------------------
# The abstraction
# ---------------------------------------------------------------------------
class VisibilityBackend(abc.ABC):
    """The witnessability-surface lifecycle: ``ensure_surface``.

    A concrete backend declares the ``terminal_kind`` it services and the
    ``visibility_class`` it satisfies, reports ``is_available()`` for the host,
    and ``ensure_surface(...)`` spawns/attaches the surface and returns a
    :class:`SurfaceHandle` carrying the terminal record.
    """

    #: The ``terminal.kind`` key this backend services (e.g. ``"tmux"``).
    terminal_kind: str
    #: The record-level ``visibility`` class this backend satisfies.
    visibility_class: str

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True when this backend can spawn a surface on this host."""
        raise NotImplementedError

    @abc.abstractmethod
    def ensure_surface(
        self,
        *,
        session: str,
        window: str,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        seat_dir: str | None = None,
    ) -> SurfaceHandle:
        """Spawn/attach the visibility surface running ``command``; return its handle.

        ``seat_dir`` is the per-seat state directory (where ``events.jsonl`` and
        the sentinel wrapper live). The tmux backend ignores it; the headless
        backend reserves the control-socket ref under it. Optional so the W1
        signature stays source-compatible.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# The tmux backend — a THIN wrapper over the existing TmuxAdapter.
# ---------------------------------------------------------------------------
class TmuxVisibilityBackend(VisibilityBackend):
    """An ``operator_visible`` backend that wraps the existing ``TmuxAdapter``.

    Zero behaviour change: ``ensure_surface`` delegates to ``adapter.ensure_pane``
    and reproduces the exact tmux terminal record the launcher built before this
    seam existed (``{kind, session_id, window_id, pane_id, pane_tty?, pane_pid?}``).
    The adapter is injectable so existing tests that pass a fake tmux adapter into
    ``lane_runtime.launch`` keep working unchanged.
    """

    terminal_kind = TMUX_TERMINAL_KIND
    visibility_class = OPERATOR_VISIBLE

    def __init__(self, adapter: Any | None = None):
        self._adapter = adapter if adapter is not None else TmuxAdapter()

    def is_available(self) -> bool:
        return bool(self._adapter.is_available())

    def ensure_surface(
        self,
        *,
        session: str,
        window: str,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        seat_dir: str | None = None,  # noqa: ARG002 — tmux ignores the seat dir
    ) -> SurfaceHandle:
        pane_kwargs: dict[str, Any] = {
            "session": session,
            "window": window,
            "command": command,
        }
        if cwd is not None:
            pane_kwargs["cwd"] = cwd
        if env is not None:
            pane_kwargs["env"] = env
        try:
            pane = self._adapter.ensure_pane(**pane_kwargs)
        except TmuxUnavailable:
            # Preserve the existing exception type so the caller's translation to
            # TmuxUnavailableError is byte-identical.
            raise
        terminal: dict[str, Any] = {
            "kind": TMUX_TERMINAL_KIND,
            "session_id": pane.session_id,
            "window_id": pane.window_id,
            "pane_id": pane.pane_id,
        }
        if pane.pane_tty:
            terminal["pane_tty"] = pane.pane_tty
        if pane.pane_pid is not None:
            terminal["pane_pid"] = pane.pane_pid
        return SurfaceHandle(
            visibility_class=self.visibility_class, terminal=terminal, native=pane
        )


# ---------------------------------------------------------------------------
# The herdr backend — CE owns the socket; herdr owns the live pane/PTY.
# ---------------------------------------------------------------------------
class HerdrVisibilityBackend(VisibilityBackend):
    """An ``operator_inspectable`` backend over herdr's controller-owned socket.

    CE creates a herdr workspace/pane and runs the sentinel-wrapped seat command
    through :class:`~creator_engine_validator.runner.herdr_session.HerdrSession`.
    The governed seat receives only its normal launch environment; the herdr
    socket path is held by the controller-side subprocess environment only. The
    Pane Registry ``surface_ref`` is an opaque controller-owned surface id, not
    the socket path.
    """

    terminal_kind = HERDR_TERMINAL_KIND
    visibility_class = OPERATOR_INSPECTABLE

    def __init__(
        self,
        session_factory: Callable[..., HerdrSession] | None = None,
        *,
        herdr_binary: str = DEFAULT_HERDR_BINARY,
        substrate_socket_dir: str = DEFAULT_SUBSTRATE_SOCKET_DIR,
        socket_name: str = DEFAULT_HERDR_SOCKET_NAME,
        available: bool | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._herdr_binary = herdr_binary
        self._substrate_socket_dir = substrate_socket_dir
        self._socket_name = socket_name
        self._available_override = available
        self._last_session: HerdrSession | None = None

    def is_available(self) -> bool:
        if self._available_override is not None:
            return self._available_override
        if self._session_factory is not None:
            return True
        binary = Path(self._herdr_binary)
        if binary.is_absolute() or binary.parent != Path("."):
            return binary.is_file()
        return shutil.which(self._herdr_binary) is not None

    def _session(self, *, socket_path: str) -> HerdrSession:
        if self._session_factory is not None:
            return self._session_factory(
                socket_path=socket_path,
                herdr_binary=self._herdr_binary,
            )
        return HerdrSession(socket_path=socket_path, herdr_binary=self._herdr_binary)

    def ensure_surface(
        self,
        *,
        session: str,
        window: str,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        seat_dir: str | None = None,
    ) -> SurfaceHandle:
        if not seat_dir:
            raise VisibilityBackendError(
                "the herdr visibility backend requires a seat_dir so the U2 "
                "containment overlap invariant can be checked"
            )
        runtime_policy = {
            "mount_manifest": [{"path": str(seat_dir), "mode": "rw"}],
            "egress_allowlist": [],
        }
        try:
            plan = plan_herdr_containment(
                runtime_policy,
                run_id=f"{session}-{window}",
                seat_command=command,
                herdr_binary=self._herdr_binary,
                substrate_socket_dir=self._substrate_socket_dir,
                socket_name=self._socket_name,
            )
        except HerdrContainmentInvariantViolation as exc:
            raise VisibilityBackendError(str(exc)) from exc
        if not self.is_available():
            raise VisibilityBackendError(
                f"herdr binary {self._herdr_binary!r} is unavailable; "
                "refusing herdr visibility launch"
            )
        session_client = self._session(socket_path=plan.socket_path)
        try:
            pane = session_client.spawn_pane(
                command=command,
                cwd=cwd,
                env=env,
                label=window or session,
            )
        except HerdrCommandError as exc:
            raise VisibilityBackendError(str(exc)) from exc
        self._last_session = session_client
        terminal: dict[str, Any] = {
            "kind": HERDR_TERMINAL_KIND,
            "surface_ref": pane.surface_ref,
            "pane_id": pane.pane_id,
        }
        if pane.pid is not None:
            terminal["pid"] = pane.pid
        return SurfaceHandle(
            visibility_class=self.visibility_class, terminal=terminal, native=pane
        )

    def observe(self, pane: HerdrPane) -> bytes:
        """Read recent pane output through the controller-held herdr session."""
        if self._last_session is None:
            raise VisibilityBackendError("herdr pane has no live controller session")
        return self._last_session.observe(pane)

    def wait_agent_status(self, pane: HerdrPane, *, status: str = "ready") -> dict[str, Any]:
        """Wait for herdr agent-status through the controller-held session."""
        if self._last_session is None:
            raise VisibilityBackendError("herdr pane has no live controller session")
        return self._last_session.wait_agent_status(pane, status=status)


def _headless_surface_slug(value: str) -> str:
    slug = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in value)
    return slug.strip(".-") or "surface"


class HeadlessVisibilityBackend(VisibilityBackend):
    """Logged/streamed ``operator_inspectable`` backend with no tmux pane.

    The surface contract is a seat-owned evidence directory under ``seat_dir``:
    ``stream.log`` receives combined stdout/stderr from the launched command and
    ``surface.json`` records the surface ref, child pid, and log path. Operators
    can inspect the manifest/log through normal filesystem access without a live
    tmux pane. This intentionally uses ``subprocess.Popen`` with file-backed
    streams rather than the retired hand-rolled PTY byte tap.
    """

    terminal_kind = HEADLESS_TERMINAL_KIND
    visibility_class = OPERATOR_INSPECTABLE

    def is_available(self) -> bool:
        return True

    def ensure_surface(
        self,
        *,
        session: str,
        window: str,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        seat_dir: str | None = None,
    ) -> SurfaceHandle:
        if not seat_dir:
            raise VisibilityBackendError(
                "the headless visibility backend requires a seat_dir for its "
                "operator-inspectable log surface"
            )
        root = (
            Path(seat_dir)
            / "headless"
            / (
                f"{_headless_surface_slug(session)}-"
                f"{_headless_surface_slug(window)}-{uuid.uuid4().hex[:8]}"
            )
        )
        root.mkdir(parents=True, exist_ok=True)
        log_path = root / "stream.log"
        manifest_path = root / "surface.json"
        surface_ref = str(manifest_path)
        merged_env = os.environ.copy()
        if env:
            merged_env.update(dict(env))
        try:
            stream = log_path.open("ab")
            try:
                process = subprocess.Popen(
                    list(command),
                    cwd=cwd,
                    env=merged_env,
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    close_fds=True,
                )
            finally:
                stream.close()
        except OSError as exc:
            raise VisibilityBackendError(
                f"headless visibility launch failed: {exc}"
            ) from exc
        manifest = {
            "kind": HEADLESS_TERMINAL_KIND,
            "visibility": self.visibility_class,
            "surface_ref": surface_ref,
            "pid": process.pid,
            "stream_ref": str(log_path),
            "started_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        terminal: dict[str, Any] = {
            "kind": HEADLESS_TERMINAL_KIND,
            "surface_ref": surface_ref,
            "pid": process.pid,
        }
        return SurfaceHandle(
            visibility_class=self.visibility_class,
            terminal=terminal,
            native=process,
        )


# ---------------------------------------------------------------------------
# Registry — keyed by ``terminal.kind``; mirrors runner/backend.py:244-274.
# ---------------------------------------------------------------------------
VisibilityBackendFactory = Callable[[], "VisibilityBackend"]

_REGISTRY: dict[str, VisibilityBackendFactory] = {}


def register_visibility_backend(kind: str, factory: VisibilityBackendFactory) -> None:
    """Register a visibility-backend ``factory`` under terminal ``kind``.

    Raises :class:`VisibilityBackendAlreadyRegistered` if ``kind`` is taken.
    """
    if kind in _REGISTRY:
        raise VisibilityBackendAlreadyRegistered(
            f"a visibility backend is already registered under {kind!r}"
        )
    _REGISTRY[kind] = factory


def get_visibility_backend(kind: str) -> VisibilityBackend:
    """Return a fresh visibility-backend instance for terminal ``kind``.

    Raises :class:`UnknownVisibilityBackend` when no backend is registered.
    """
    try:
        factory = _REGISTRY[kind]
    except KeyError:
        available = ", ".join(available_visibility_kinds()) or "(none)"
        raise UnknownVisibilityBackend(
            f"no visibility backend registered under {kind!r}; available: {available}"
        ) from None
    return factory()


def available_visibility_kinds() -> tuple[str, ...]:
    """Return the sorted tuple of registered visibility-backend kinds."""
    return tuple(sorted(_REGISTRY))


# The tmux backend is the default registered surface (W1). The factory builds a
# fresh adapter-backed instance; when the caller injects a tmux adapter (the
# existing test seam), the launcher constructs the backend directly instead.
register_visibility_backend(TMUX_TERMINAL_KIND, TmuxVisibilityBackend)
# The headless backend is the logged/streamed operator_inspectable surface for
# autonomous contained seats with no tmux pane.
register_visibility_backend(HEADLESS_TERMINAL_KIND, HeadlessVisibilityBackend)
# The herdr backend (ce-ops#217 U3): the live operator_inspectable surface over
# a controller-owned herdr control socket.
register_visibility_backend(HERDR_TERMINAL_KIND, HerdrVisibilityBackend)
