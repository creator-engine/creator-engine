"""The unprivileged OS-native runner backend — a FAIL-CLOSED scaffold (ce-ops#71 T1).

This is the neutral-keyed (``os-native``) realization of #71's headline direction:
a daemonless, rootless backend (bubblewrap user-ns + a host deny-by-default proxy
on Linux; Seatbelt on macOS) that lets ``onboard --apply`` succeed with **no root**
— the lowest-privilege tier of the RunnerBackend menu, the existence-proof posture
Claude Code and Codex both ship.

**Scope (deliberate, load-bearing): this slice ships the STRUCTURE + SELECTION + a
FAIL-CLOSED posture, NOT a functional sandbox mechanism.** The mechanism choice —
Anthropic's ``@anthropic-ai/sandbox-runtime`` (srt) vs a CE-native jail — is an open
Operator call (the install-architecture research §9 OQ-1), so this backend does not
pin the default install path to a Node/research-preview dependency. Until that
decision lands and the adapter is built (Tranche 2), :meth:`_provision` refuses to
provision a live runtime with :class:`BackendUnavailable`, naming exactly what is
missing. This preserves CE's existing fail-closed posture: a selected-but-unbuilt
backend never silently downgrades to an unsandboxed run.

What this backend DOES enforce today, fully:

* **The G-1.0 deny surface stays load-bearing.** Provisioning runs through the
  :class:`RunnerBackend.provision` template method, which validates the
  runtime-policy record FIRST (``validate_runtime_policy`` → :class:`PolicyRejected`
  on a dirty record) before :meth:`_provision` is ever called. Because #71 ADDS this
  backend, that validate-at-provision invariant is what keeps the grader-outside moat
  intact for the new lighter tier — and it is enforced at the ABC, not here.
* **Registration + selection.** It registers under the ``os-native`` key
  (``schemas/runtime-policy.schema.yaml`` enum) so a policy/profile can SELECT it and
  audit predicates can attest the selection — even while the live mechanism is held.

Design invariants (shared with the other backends):

* **Not a validator check.** ``register_backend`` is the BACKEND registry, not the
  ``@register`` check registry — importing this module adds no check and leaves
  ``--list-checks`` byte-identical.
* **Zero I/O on import / no live side effect.** Importing allocates nothing; the
  fail-closed refusal is the only behavior, and it raises before any side effect.
* **Defensive.** This hardens CE's own agent runtime; it is never an offensive
  capability.
"""

from __future__ import annotations

from .backend import (
    BackendUnavailable,
    CollectedEvidence,
    ProvisionRequest,
    ProvisionedHandle,
    RunnerBackend,
    RunRequest,
    RunResult,
    TeardownResult,
    register_backend,
)

BACKEND_KEY = "os-native"

#: The unprivileged sandbox primitives the (future) functional ``os-native``
#: backend will require on Linux. Named here so the FAIL-CLOSED refusal can
#: enumerate exactly what a live provision would need — preserving CE's
#: "fail-closed with a named missing-dep list" posture (the #71 fallback-semantics
#: default; the policy choice between fail-closed / noop-ladder / one-time-fix is
#: the Operator's, research §9 OQ-2). The mechanism that consumes these (srt vs a
#: CE-native jail, OQ-1) is HELD — so they are documented prerequisites, never
#: auto-installed (that is what keeps this tier zero-root).
LINUX_SANDBOX_PRIMITIVES: tuple[str, ...] = ("bwrap", "proxy")

#: Why a live provision is refused today. The structure is in place; the mechanism
#: adapter is the held Tranche-2 / Operator decision.
_HELD_REASON = (
    "the 'os-native' backend is a fail-closed scaffold (ce-ops#71 Tranche 1): its "
    "structure, selection and deny-surface enforcement are live, but the unprivileged "
    "sandbox MECHANISM (srt vs a CE-native jail — research §9 OQ-1) is HELD pending an "
    "Operator decision, so it refuses to provision a live runtime rather than silently "
    "run unsandboxed. Required-but-unwired primitives: "
    + ", ".join(LINUX_SANDBOX_PRIMITIVES)
    + ". Select 'gvisor-proxy' for a privileged single-host runtime today."
)


class OsNativeBackend(RunnerBackend):
    """The unprivileged OS-native backend — registered, deny-surface-enforcing,
    fail-closed until its sandbox mechanism is chosen and built (Tranche 2)."""

    backend_key = BACKEND_KEY

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        # The deny surface (mapping + validate_runtime_policy → PolicyRejected) is
        # enforced by the RunnerBackend.provision template method before we get
        # here — so a dirty record is already rejected. A clean record reaches
        # this point and is refused FAIL-CLOSED: the mechanism is held.
        raise BackendUnavailable(_HELD_REASON)

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:  # pragma: no cover - unreachable until a live mechanism lands
        raise BackendUnavailable(_HELD_REASON)

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:  # pragma: no cover - unreachable until a live mechanism lands
        raise BackendUnavailable(_HELD_REASON)

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:  # pragma: no cover - unreachable until a live mechanism lands
        raise BackendUnavailable(_HELD_REASON)


register_backend(BACKEND_KEY, OsNativeBackend)
