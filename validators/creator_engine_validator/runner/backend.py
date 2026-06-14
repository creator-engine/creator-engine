"""CE v3 runner-backend adapter interface (G-1.1, plane C).

The thin runner abstraction the (future, thin) orchestrator calls to run an
agent seat inside an isolation backend: ``provision -> run -> collect ->
teardown``. Per the secure-runtime architect report, CE *rents* the enforcer —
it keeps only this adapter (plus the advisory classifier/audit overlay and the
hash-chained evidence spine). Two first-class backends land behind this one
abstraction — a hardened gVisor container + capability-separation egress proxy
(G-1.2, ships now) and an OpenShell sandbox (fast-follow) — selected by the
``isolation_backend`` field of a runtime-policy record
(``schemas/runtime-policy.schema.yaml``, the G-1.0 contract).

Design invariants (deliberate, load-bearing):

* **Not a validator check.** Nothing here is ``@register``-ed; importing this
  package registers no check and leaves ``--list-checks`` byte-identical. The
  validator's check path stays offline; a backend is the only place that will
  ever touch a live runtime.
* **G-1.1 is a PURE INTERFACE.** This module defines the ABC, the
  provision/run/collect/teardown data model, the error hierarchy, and the
  backend registry. It allocates no container, opens no socket, and runs no
  subprocess. The only shipped backend is the inert ``LocalNoopBackend``
  (``runner/noop_backend.py``); the live gVisor+proxy backend is G-1.2.
* **Defensive.** The adapter hardens our own agent runtime; it is never an
  offensive capability.

This adapter may later be EXTRACTED into a standalone ``ce_orchestrator``
package on the architect's pre-committed trigger; until then it lives in the
installable validator package so the existing CI pytest job covers it.
"""

from __future__ import annotations

import abc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class RunnerError(Exception):
    """Base class for runner-adapter errors."""


class BackendUnavailable(RunnerError):
    """A backend exists but cannot service the request in this environment."""


class PolicyRejected(RunnerError):
    """A runtime-policy record failed validation and MUST NOT be provisioned."""


class UnknownBackend(RunnerError):
    """No backend is registered under the requested key."""


class BackendAlreadyRegistered(RunnerError):
    """A backend is already registered under the requested key."""


# ---------------------------------------------------------------------------
# Data model — pure, frozen dataclasses. Nothing crosses a process or
# persistence boundary in G-1.1, so these need no schema; the
# ``CollectedEvidence`` record gets a schema when it enters the hash-chained
# evidence spine at G-1.3.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProvisionRequest:
    """A request to provision an isolated runtime for one agent seat.

    ``runtime_policy`` is a runtime-policy record (the G-1.0 contract); a
    backend MUST refuse to provision one that does not validate clean.
    """

    runtime_policy: dict[str, Any]
    run_id: str


@dataclass(frozen=True)
class ProvisionedHandle:
    """An opaque handle to a provisioned runtime, bound to the exact policy."""

    backend_key: str
    run_id: str
    policy_sha: str
    ref: str


@dataclass(frozen=True)
class RunRequest:
    """A command to run inside a provisioned runtime."""

    command: tuple[str, ...]


@dataclass(frozen=True)
class RunChangeSet:
    """The agent's in-manifest work as DATA crossing the runner seam — value-free.

    Desired-state POINTERS only: the head ``branch`` the run authored, the ``base``
    it targets, the authorized ``manifest_paths`` the change carries, and the produced
    ``head_sha``. It holds NO diff blob and NO secret — the live diff capture is the
    gVisor backend's job (later). The inert ``LocalNoopBackend`` produces none (an inert
    run authors nothing, so :class:`RunResult`/:class:`CollectedEvidence` default
    ``change_set`` to ``None``); a test/fake backend or the real gVisor backend populates
    it so the work crosses the seam as a value, not a side effect.
    """

    branch: str
    base: str
    manifest_paths: tuple[str, ...]
    head_sha: str


@dataclass(frozen=True)
class RunResult:
    """The outcome of a single run inside a provisioned runtime."""

    exit_code: int
    stdout: str
    stderr: str
    started_ref: str
    #: The run's value-free change-set pointers (``None`` for an inert/no-author run).
    change_set: RunChangeSet | None = None


@dataclass(frozen=True)
class CollectedEvidence:
    """Evidence collected from a provisioned runtime (the evidence-spine seed)."""

    handle_ref: str
    records: tuple[dict[str, Any], ...]
    note: str
    #: Surfaced when the orchestrated lifecycle ends at "PR opened" (G-3.1); else ``None``.
    change_set: RunChangeSet | None = None


@dataclass(frozen=True)
class TeardownResult:
    """The outcome of tearing down a provisioned runtime."""

    handle_ref: str
    released: bool


# ---------------------------------------------------------------------------
# The adapter ABC
# ---------------------------------------------------------------------------
class RunnerBackend(abc.ABC):
    """The runner-backend lifecycle: provision -> run -> collect -> teardown.

    Consumes a validated runtime-policy record (the G-1.0 contract). A concrete
    backend MUST refuse to provision a record that does not validate clean
    (raise :class:`PolicyRejected`) so the G-1.0 deny surface — image digest
    pin, forbidden mounts, names-only secrets, deny-by-default egress — stays
    load-bearing at the adapter boundary.
    """

    #: The ``isolation_backend`` key this backend services (e.g. ``local-noop``).
    backend_key: str

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Structurally enforce the validate-at-provision invariant (ce-ops#71 req-3).

        :meth:`provision` is the CONCRETE template method that runs the G-1.0 deny
        surface FIRST and only then delegates to :meth:`_provision`. A subclass that
        overrides ``provision`` itself could skip that validation — so this guard
        FORBIDS it at class-creation time: a subclass may override ``_provision``
        (the backend-specific hook) but NEVER ``provision`` (the template). This
        promotes the moat's "every backend re-runs the policy validation" residual
        from a registry-test discipline to an import-time structural assertion no
        backend can bypass. The registry test still proves today's backends comply.
        """
        super().__init_subclass__(**kwargs)
        if "provision" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must not override RunnerBackend.provision (the "
                "validate-at-provision template method); override _provision instead "
                "— the G-1.0 deny surface must run before any backend-specific work"
            )

    def provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        """Provision an isolated runtime for the policy in ``request``.

        **Enforced invariant (ce-ops#71 req-3): validate-at-provision.** This is
        a CONCRETE template method — it runs the G-1.0 deny surface FIRST (the
        record must be a mapping AND ``validate_runtime_policy`` must return no
        errors, else :class:`PolicyRejected`) and only then delegates the
        backend-specific work to :meth:`_provision`. Because #71 *adds* a backend
        (``os-native``), the moat's "every backend re-runs the policy validation"
        residual is promoted from a per-backend discipline to an ABC-level
        assertion here: a subclass CANNOT skip it (the validation is not in the
        overridable method). The registry-level test asserts every registered
        backend rejects a dirty record through this path.
        """
        record = request.runtime_policy
        if not isinstance(record, dict):
            raise PolicyRejected("runtime_policy must be a mapping")
        # Lazy import keeps this module's import side-effect-free (the G-1.1
        # "zero I/O on import" invariant); the schema read happens at call time.
        from ..checks.ce_runtime_policy import validate_runtime_policy

        errors = validate_runtime_policy(record, Path(f"<provision:{request.run_id}>"))
        if errors:
            rendered = "; ".join(error.format() for error in errors)
            raise PolicyRejected(
                f"runtime-policy did not validate clean; refusing to provision: {rendered}"
            )
        return self._provision(request)

    @abc.abstractmethod
    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        """Backend-specific provisioning, called by :meth:`provision` ONLY after
        the policy has validated clean (the deny surface is already enforced)."""
        raise NotImplementedError

    @abc.abstractmethod
    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        """Run a command inside the provisioned runtime."""
        raise NotImplementedError

    @abc.abstractmethod
    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        """Collect evidence from the provisioned runtime."""
        raise NotImplementedError

    @abc.abstractmethod
    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        """Tear down the provisioned runtime, releasing its resources."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Registry — keyed by the runtime-policy ``isolation_backend`` value.
# G-1.1 registers only the inert ``local-noop`` backend; ``gvisor-proxy`` and
# ``openshell`` are registered by later slices and raise ``UnknownBackend``
# until then.
# ---------------------------------------------------------------------------
BackendFactory = Callable[[], "RunnerBackend"]

_REGISTRY: dict[str, BackendFactory] = {}


def register_backend(key: str, factory: BackendFactory) -> None:
    """Register a backend ``factory`` under ``key``.

    Raises :class:`BackendAlreadyRegistered` if ``key`` is already taken.
    """
    if key in _REGISTRY:
        raise BackendAlreadyRegistered(f"a runner backend is already registered under {key!r}")
    _REGISTRY[key] = factory


def get_backend(key: str) -> RunnerBackend:
    """Return a fresh backend instance for ``key``.

    Raises :class:`UnknownBackend` when no backend is registered under ``key``.
    """
    try:
        factory = _REGISTRY[key]
    except KeyError:
        available = ", ".join(available_backends()) or "(none)"
        raise UnknownBackend(
            f"no runner backend registered under {key!r}; available: {available}"
        ) from None
    return factory()


def available_backends() -> tuple[str, ...]:
    """Return the sorted tuple of registered backend keys."""
    return tuple(sorted(_REGISTRY))
