"""CE v3 runner-backend adapter — the thin runner abstraction (G-1.1, plane C).

This sub-package is the second slice of the v3 plane-C runtime: the small
lifecycle seam the (future, thin) orchestrator calls to run an agent seat inside
an isolation backend — ``provision -> run -> collect -> teardown`` — consuming a
runtime-policy record (the G-1.0 contract). See
``docs/contracts/runtime-policy.md`` and the secure-runtime architect report.

Design invariants (deliberate, load-bearing):

* **Not a validator check.** Nothing here is ``@register``-ed; importing this
  package registers no check and leaves ``--list-checks`` byte-identical.
* **Pure interface in G-1.1.** This slice ships the ABC, the
  provision/run/collect/teardown data model, the error hierarchy, the backend
  registry, and a single INERT backend (``LocalNoopBackend``). It allocates no
  container, opens no socket, runs no subprocess, and performs no network I/O on
  import. The live gVisor + capability-separation-proxy backend is G-1.2; an
  OpenShell backend is a fast-follow behind this same adapter.
* **Deny surface stays load-bearing.** ``LocalNoopBackend.provision`` refuses a
  runtime-policy record that does not validate clean against the G-1.0
  ``ce_runtime_policy`` predicates (raises ``PolicyRejected``).

This adapter may later be EXTRACTED into a standalone ``ce_orchestrator``
package on the architect's pre-committed trigger; until then it lives in the
installable validator package so the existing CI pytest job covers it.
"""

from __future__ import annotations

from .backend import (
    BackendAlreadyRegistered,
    BackendUnavailable,
    CollectedEvidence,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunnerBackend,
    RunnerError,
    RunRequest,
    RunResult,
    TeardownResult,
    UnknownBackend,
    available_backends,
    get_backend,
    register_backend,
)
from .noop_backend import BACKEND_KEY as LOCAL_NOOP_BACKEND_KEY
from .noop_backend import LocalNoopBackend

__all__ = [
    "BackendAlreadyRegistered",
    "BackendUnavailable",
    "CollectedEvidence",
    "LOCAL_NOOP_BACKEND_KEY",
    "LocalNoopBackend",
    "PolicyRejected",
    "ProvisionRequest",
    "ProvisionedHandle",
    "RunRequest",
    "RunResult",
    "RunnerBackend",
    "RunnerError",
    "TeardownResult",
    "UnknownBackend",
    "available_backends",
    "get_backend",
    "register_backend",
]
