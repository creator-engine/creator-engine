"""CE v3 plane-C audit overlay: classifier + AuditOverlayBackend (G-1.3b).

The backend-agnostic audit layer that makes the rented runtime *accountable*.
Two pieces, both behind the G-1.1 ``RunnerBackend`` adapter:

* a PURE **classifier** — the policy decision point: ``classify(event,
  runtime_policy)`` evaluates an observed runtime/lifecycle event against the
  G-1.0 runtime-policy record and returns ``allowed`` / ``denied`` / ``escalate``;
* a **decorator** — ``AuditOverlayBackend`` wraps any ``RunnerBackend`` so every
  ``provision -> run -> collect -> teardown`` step (and every observed runtime
  event) emits a tamper-evident, hash-chained evidence record via the merged
  G-1.3a ``runtime_evidence_spine``, bound to the ``policy_sha`` it attests.

Per the secure-runtime architect report this is the "logical-governance" layer
the rented runtime does not provide, and the audit trail that turns each runtime
decision into cryptographic evidence on top of kernel enforcement.

Design invariants (deliberate, load-bearing):

* **PURE classifier.** ``classify`` is a pure function — no live tap, no
  subprocess, no socket, no disk, no wall-clock read. It mirrors the G-1.2
  translate-vs-execute split: the live event *source* is a later seam; this
  module only decides + attests.
* **DECORATOR overlay.** ``AuditOverlayBackend`` wraps an inner backend; it does
  NOT edit the concrete backends and registers NO ``isolation_backend``. The
  inner backend does the real work; the overlay observes + attests. So
  ``gvisor-proxy`` (and the future ``openshell``) get audit for free.
* **REUSE, don't reinvent.** The hash chain is the merged G-1.3a
  ``runtime_evidence_spine`` (``append`` / ``verify_chain``); a record the
  overlay emits is exactly what the ``ce_runtime_evidence`` check accepts.
* **Not a check, not a registered backend.** Importing this module registers no
  validator check and no backend; it leaves ``--list-checks`` (43) and
  ``available_backends()`` byte-identical, and performs no I/O.
* **Pure clock seam.** Timestamps are inputs, never read from the wall clock
  here; the default ``clock`` is a deterministic counter (a real-clock
  implementation is an injected seam, a later concern).

Defensive only — accountability for our own agent runtime; never offensive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..runtime_evidence_spine import (
    CLASSIFICATIONS,
    RECORD_KIND,
    append,
    verify_chain,
)
from .backend import (
    CollectedEvidence,
    ProvisionedHandle,
    ProvisionRequest,
    RunnerBackend,
    RunRequest,
    RunResult,
    TeardownResult,
)

#: The three classifier verdicts (reuse the spine's source of truth).
ALLOWED, DENIED, ESCALATE = CLASSIFICATIONS  # ("allowed", "denied", "escalate")


# ---------------------------------------------------------------------------
# Event model — frozen, pure inputs to the classifier. The live event *source*
# (a tap on the running container) is a deferred seam; here events are values.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LifecycleEvent:
    """A RunnerBackend lifecycle transition (provision/run/collect/teardown)."""

    phase: str


@dataclass(frozen=True)
class EgressEvent:
    """An outbound connection attempt observed inside the runtime."""

    host: str
    port: int | None = None
    phase: str = "run"


@dataclass(frozen=True)
class MountEvent:
    """A filesystem mount/access observed inside the runtime."""

    path: str
    mode: str = "ro"  # "ro" | "rw"
    phase: str = "run"


@dataclass(frozen=True)
class SecretEvent:
    """A secret-injection request observed inside the runtime."""

    name: str
    phase: str = "run"


# ---------------------------------------------------------------------------
# The classifier — the pure policy decision point
# ---------------------------------------------------------------------------
def classify(event: Any, runtime_policy: dict[str, Any]) -> str:
    """Classify ``event`` against a runtime-policy record (PURE).

    Returns one of ``allowed`` / ``denied`` / ``escalate`` (the
    :data:`CLASSIFICATIONS` set), evaluated against the G-1.0 ``ce_runtime_policy``
    record's ``egress_allowlist`` / ``mount_manifest`` / ``secret_allowlist``:

    * a lifecycle transition is ``allowed`` (the policy validated clean at
      provision, else the inner backend would have refused);
    * an egress to an allowlisted host is ``allowed``, otherwise ``denied``
      (deny-by-default — an empty allowlist denies all egress);
    * a mount whose path is in the manifest is ``allowed``, unless it requests
      ``rw`` on a path granted ``ro`` (that needs a grant → ``escalate``); a path
      not in the manifest is ``denied`` (default-deny);
    * a secret whose name is in the allowlist is ``allowed``, otherwise
      ``denied``;
    * any unrecognized event type fails safe to ``escalate`` (human review).

    No I/O, no subprocess, no clock read.
    """
    if not isinstance(runtime_policy, dict):
        return ESCALATE
    if isinstance(event, LifecycleEvent):
        return ALLOWED
    if isinstance(event, EgressEvent):
        hosts = {
            rule.get("host")
            for rule in (runtime_policy.get("egress_allowlist") or [])
            if isinstance(rule, dict)
        }
        return ALLOWED if event.host in hosts else DENIED
    if isinstance(event, MountEvent):
        for entry in runtime_policy.get("mount_manifest") or []:
            if isinstance(entry, dict) and entry.get("path") == event.path:
                if event.mode == "rw" and entry.get("mode") != "rw":
                    return ESCALATE  # rw on a ro-granted mount — needs a grant
                return ALLOWED
        return DENIED  # default-deny: path not in the manifest
    if isinstance(event, SecretEvent):
        names = set(runtime_policy.get("secret_allowlist") or [])
        return ALLOWED if event.name in names else DENIED
    return ESCALATE  # unknown event type — fail safe to human review


# ---------------------------------------------------------------------------
# The pure clock seam (deterministic default; real-clock impl is injected later)
# ---------------------------------------------------------------------------
Clock = Callable[[], str]


class CounterClock:
    """A deterministic, pure default clock — never reads the wall clock."""

    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> str:
        self._n += 1
        return f"t{self._n}"


# ---------------------------------------------------------------------------
# The overlay — a decorator over any RunnerBackend
# ---------------------------------------------------------------------------
class AuditOverlayBackend(RunnerBackend):
    """Wrap an inner :class:`RunnerBackend`; attest each step to a hash-chained spine.

    The inner backend does the real provision/run/collect/teardown work; this
    overlay classifies each step and ``append``s an evidence record (bound to the
    handle's ``policy_sha``) to a per-handle in-memory chain via the merged G-1.3a
    substrate. ``collect`` folds the spine chain into the returned
    :class:`CollectedEvidence`. A clean run satisfies ``verify_chain(chain) == []``.

    Registers no ``isolation_backend`` and no validator check; it is composed
    around an existing backend (e.g. ``AuditOverlayBackend(GvisorProxyBackend())``).
    """

    def __init__(self, inner: RunnerBackend, clock: Clock | None = None) -> None:
        self._inner = inner
        self._clock: Clock = clock if clock is not None else CounterClock()
        self._chains: dict[str, list[dict[str, Any]]] = {}
        self._policies: dict[str, dict[str, Any]] = {}
        #: A composed key; the overlay itself is not registered under it.
        self.backend_key = f"audit-overlay[{getattr(inner, 'backend_key', '?')}]"

    # -- attestation helpers -------------------------------------------------
    def _emit(self, handle: ProvisionedHandle, phase: str, classification: str) -> dict[str, Any]:
        chain = self._chains.setdefault(handle.ref, [])
        body: dict[str, Any] = {
            "kind": RECORD_KIND,
            "record_type": "runtime_evidence",
            "schema_version": "1",
            "policy_sha": handle.policy_sha,
            "run_id": handle.run_id,
            "lifecycle_phase": phase,
            "classification": classification,
            "recorded_at": self._clock(),
        }
        inner_key = getattr(self._inner, "backend_key", "")
        if isinstance(inner_key, str) and inner_key:
            body["backend_key"] = inner_key
        record = append(chain, body)
        chain.append(record)
        return record

    def chain(self, handle: ProvisionedHandle) -> tuple[dict[str, Any], ...]:
        """Return the (ordered) evidence chain attested for ``handle``."""
        return tuple(self._chains.get(handle.ref, ()))

    def observe(self, handle: ProvisionedHandle, event: Any) -> dict[str, Any]:
        """Classify a concrete runtime ``event`` against the attested policy + record it.

        This is how a (future, deferred) live event tap feeds the overlay: the
        event is classified against the exact policy provisioned for ``handle``,
        and the verdict is attested into the hash chain.
        """
        policy = self._policies.get(handle.ref, {})
        classification = classify(event, policy)
        phase = getattr(event, "phase", "run")
        return self._emit(handle, str(phase), classification)

    # -- the wrapped RunnerBackend lifecycle ---------------------------------
    def provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        handle = self._inner.provision(request)
        # The inner backend's provision() applies the G-1.0 deny guard and would
        # have raised PolicyRejected on an unclean record, so a returned handle
        # means the policy validated clean → the provision is allowed.
        if isinstance(request.runtime_policy, dict):
            self._policies[handle.ref] = request.runtime_policy
        self._emit(handle, "provision", ALLOWED)
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        result = self._inner.run(handle, request)
        self._emit(handle, "run", ALLOWED)
        return result

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        inner_evidence = self._inner.collect(handle)
        self._emit(handle, "collect", ALLOWED)
        spine = self.chain(handle)
        return CollectedEvidence(
            handle_ref=inner_evidence.handle_ref,
            records=tuple(inner_evidence.records) + spine,
            note=f"audit-overlay attested {len(spine)} spine record(s); inner: {inner_evidence.note}",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        self._emit(handle, "teardown", ALLOWED)
        result = self._inner.teardown(handle)
        self._policies.pop(handle.ref, None)
        return result
