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
* **Zero behaviour change in W1.** This slice ships only the registry plus a
  :class:`TmuxVisibilityBackend` that is a THIN wrapper over the existing
  ``tmux_adapter.TmuxAdapter`` (untouched). The headless backend and any gate
  relaxation are later slices (#207 W2+).
* **No validator check.** Nothing here is ``@register``-ed; importing this
  module registers no validator check and runs no I/O on import.
"""
from __future__ import annotations

import abc
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .tmux_adapter import TmuxAdapter, TmuxUnavailable

# The terminal kind / visibility class vocabulary. ``operator_visible`` is the
# tmux class (a human can attach a live pane); ``operator_inspectable`` is the
# headless class (a recorded surface, no live pane) reserved for W2. Both satisfy
# the visibility *contract* — see the C1 gate (W2).
TMUX_TERMINAL_KIND = "tmux"
OPERATOR_VISIBLE = "operator_visible"
OPERATOR_INSPECTABLE = "operator_inspectable"


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
    ) -> SurfaceHandle:
        """Spawn/attach the visibility surface running ``command``; return its handle."""
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
    ) -> SurfaceHandle:
        try:
            pane = self._adapter.ensure_pane(
                session=session,
                window=window,
                command=command,
                cwd=cwd,
                env=env,
            )
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
