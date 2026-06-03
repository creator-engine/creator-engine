"""CE v3 thin orchestrator + approved-plan ratification gate (G-2.0, plane C).

The thin glue that opens the G-2 milestone. :func:`run_plan` composes the merged
plane-C parts — it resolves an isolation backend by the runtime-policy's
``isolation_backend`` (or uses an injected backend), wraps it in the G-1.3b
``AuditOverlayBackend``, and drives ``provision -> run -> collect -> teardown`` —
but ONLY after the **approved-plan ratification gate** passes.

Per the v3-spec architect report the orchestrator's authored surface is *glue*:
"check approval (one query), provision/teardown a runner, collect results … not
a coordination engine". The locked guardrail: the orchestrator "will not call
``runner.provision()`` until ``plan_approved()`` is true" — a human ratifies the
plan BEFORE the sandbox starts; the agent never self-approves. The boundary
lives **outside and below the agent**: the orchestrator refuses, and the seat it
runs cannot bypass that refusal.

Design invariants (deliberate, load-bearing):

* **Refuse before any side effect.** :func:`run_plan` evaluates the ratification
  gate FIRST and raises :class:`PlanNotRatified` BEFORE the inner backend's
  ``provision`` is ever called — mirroring the G-1.0 ``PolicyRejected`` / G-1.2
  availability "refuse before side effect" discipline. A refused run touches no
  backend.
* **Gate binds to ``policy_sha``.** The approval is anchored to the exact
  runtime-policy version in force: ``ApprovedPlan.policy_sha`` MUST equal the
  record's ``policy_sha`` (a 64-hex digest) and ``ApprovedPlan.run_id`` the
  requested ``run_id``.
* **Thin pure glue.** :func:`run_plan` allocates no container, opens no socket,
  runs no subprocess. All live work stays behind the G-1.1 adapter / G-1.2
  injectable seam, so CI runs it against the inert ``LocalNoopBackend`` with ZERO
  live subprocess. Importing this module performs zero I/O and registers no
  validator check and no backend — ``--list-checks`` (43) and
  ``available_backends()`` stay byte-identical.
* **REUSE the merged seams.** ``get_backend`` / ``AuditOverlayBackend`` /
  ``ProvisionRequest`` / ``RunRequest`` / the evidence spine — never reinvented.
  The inner backend's own ``provision`` re-applies the G-1.0 deny surface
  (``PolicyRejected`` on an unclean record): a second, independent refusal
  surface the orchestrator does not duplicate.

This module is the seed for the architect's pre-committed ``ce_orchestrator``
extraction; until then it lives in the installable validator package so the
existing CI pytest job covers it. The forge-native approval source
(``plan_approved()``) and the per-task ``mint_scoped_token`` are deferred G-2
hardening. See ``docs/contracts/orchestrator.md``.

Defensive only — authorization + accountability for our own agent runtime;
never offensive.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .runner import (
    AuditOverlayBackend,
    Clock,
    CollectedEvidence,
    ProvisionRequest,
    RunnerBackend,
    RunnerError,
    RunRequest,
    get_backend,
)
from .runtime_evidence_spine import is_policy_sha


class PlanNotRatified(RunnerError):
    """The approved-plan ratification gate refused: no provision may proceed.

    Raised BEFORE any backend side effect when the run is not bound to a valid,
    human-ratified plan anchored to the exact runtime-policy (``policy_sha``).
    """


@dataclass(frozen=True)
class ApprovedPlan:
    """A human-ratified plan attestation that authorizes one orchestrated run.

    The gate requires this record to be present and bound to the exact run:
    ``policy_sha`` anchors the approval to the runtime-policy version in force and
    ``run_id`` to the specific run. ``approved_by`` is the ratifier identity (NOT
    the agent seat being run — the agent never self-approves) and ``approval_ref``
    points at the ratifying artifact (e.g. the forge issue / plan-PR). In G-2.0
    these are caller-supplied; wiring them to the forge-native ``plan_approved()``
    query (and enforcing ``approved_by`` != the seat identity) is deferred G-2
    hardening.
    """

    run_id: str
    policy_sha: str
    approved_by: str
    approval_ref: str


def _ratify_or_refuse(
    runtime_policy: dict[str, Any],
    run_id: str,
    approved_plan: ApprovedPlan | None,
) -> None:
    """Raise :class:`PlanNotRatified` unless ``approved_plan`` authorizes the run.

    Enforced BEFORE any provision. The approval must be present, bound to the
    exact ``run_id``, anchored to the runtime-policy's ``policy_sha`` (a 64-hex
    digest), and carry a non-empty ratifier identity + approval reference.
    """
    if approved_plan is None:
        raise PlanNotRatified(
            f"no approved plan for run {run_id!r}; refusing to provision "
            "(the plan must be ratified before the sandbox starts)"
        )
    if approved_plan.run_id != run_id:
        raise PlanNotRatified(
            f"approved plan run_id {approved_plan.run_id!r} != requested {run_id!r}"
        )
    policy_sha = runtime_policy.get("policy_sha") if isinstance(runtime_policy, dict) else None
    if not is_policy_sha(approved_plan.policy_sha):
        raise PlanNotRatified(
            f"approved plan policy_sha {approved_plan.policy_sha!r} is not a 64-hex digest"
        )
    if approved_plan.policy_sha != policy_sha:
        raise PlanNotRatified(
            f"approved plan policy_sha {approved_plan.policy_sha!r} != runtime-policy "
            f"policy_sha {policy_sha!r} (approval not bound to the policy in force)"
        )
    if not (approved_plan.approved_by and approved_plan.approval_ref):
        raise PlanNotRatified(
            "approved plan is missing approved_by / approval_ref "
            "(an unattributed approval is not a ratification)"
        )


def run_plan(
    runtime_policy: dict[str, Any],
    run_id: str,
    command: Sequence[str],
    approved_plan: ApprovedPlan | None,
    *,
    backend: RunnerBackend | None = None,
    clock: Clock | None = None,
) -> CollectedEvidence:
    """Drive one ratified, audited agent-seat run and return its collected evidence.

    Thin glue, in order:

    1. **gate-check** — :func:`_ratify_or_refuse` raises :class:`PlanNotRatified`
       BEFORE any side effect if the run is not ratified + bound to this policy;
    2. **resolve** the inner isolation backend — the injected ``backend`` else
       ``get_backend(runtime_policy["isolation_backend"])``;
    3. **wrap** it in :class:`AuditOverlayBackend` so every lifecycle step is
       attested to the hash-chained evidence spine, bound to the policy;
    4. **drive** ``provision -> run -> collect -> teardown`` and return the
       collected evidence (the audit overlay's collect-time spine snapshot;
       teardown is still executed to release the runtime).

    Allocates no container and runs no subprocess itself; in CI it is exercised
    against the inert ``LocalNoopBackend`` with zero live subprocess. Propagates
    the backend's own refusals unchanged: ``PolicyRejected`` on an unclean
    runtime-policy, ``BackendUnavailable`` / ``UnknownBackend`` on resolution.
    """
    # 1) Ratification gate — refuse BEFORE any side effect (the locked guardrail).
    _ratify_or_refuse(runtime_policy, run_id, approved_plan)

    # 2) Resolve the inner backend (injected for tests, else by the policy selector).
    inner = backend if backend is not None else get_backend(runtime_policy["isolation_backend"])

    # 3) Wrap in the audit overlay so every lifecycle step is attested.
    overlay = AuditOverlayBackend(inner, clock=clock)

    # 4) Drive the lifecycle. The inner backend's provision() re-applies the G-1.0
    #    deny surface (PolicyRejected on an unclean record) — not duplicated here.
    handle = overlay.provision(ProvisionRequest(runtime_policy=runtime_policy, run_id=run_id))
    overlay.run(handle, RunRequest(command=tuple(command)))
    evidence = overlay.collect(handle)
    overlay.teardown(handle)
    return evidence
