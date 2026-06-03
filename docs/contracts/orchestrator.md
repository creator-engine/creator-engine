# Contract: Thin Orchestrator + Approved-Plan Ratification Gate

Gate: v3 **G-2.0** — the thin orchestrator + the approved-plan ratification
gate (the first slice of G-2; opens the second MVP milestone after G-1 /
plane C is complete).
Validator check: **none** — the orchestrator is pure in-process glue behind the
G-1.1 runner adapter. It registers no `@register` check (`--list-checks` stays
**43**) and no `isolation_backend` (`available_backends()` stays
`('gvisor-proxy', 'local-noop')`).
Module: `validators/creator_engine_validator/orchestrator.py`
Reuses: the G-1.1 adapter (`runner.get_backend` / `RunnerBackend` /
`ProvisionRequest` / `RunRequest`), the G-1.3b `AuditOverlayBackend`, and the
G-1.3a hash-chained `runtime_evidence_spine`.

## Purpose

The orchestrator is the thin glue that composes the merged plane-C parts into
one ratified, audited run of an agent seat. Its authored surface is *glue* — per
the v3-spec architect report, "check approval (one query), provision/teardown a
runner, collect results … not a coordination engine". The single entry point
`run_plan(...)`:

1. **gate-checks** an `ApprovedPlan` and refuses (`PlanNotRatified`) BEFORE any
   side effect if the run is not ratified and bound to the exact policy;
2. **resolves** the inner isolation backend — an injected backend (CI / tests)
   else `get_backend(runtime_policy["isolation_backend"])`;
3. **wraps** it in the `AuditOverlayBackend` so every lifecycle step is attested
   to the hash-chained evidence spine, bound to the policy's `policy_sha`;
4. **drives** `provision -> run -> collect -> teardown` and returns the
   collected, content-addressed, hash-chained evidence.

A reader with only a fresh clone must be able to answer: *was this run
authorized by a human-ratified plan, bound to the exact runtime-policy, before
the sandbox started?* — and verify the answer from the returned evidence chain.

This contract is **defensive**: it adds authorization + accountability to the
Creator Engine's own agent runtime. It is never an offensive capability.

## The ratification gate — the locked guardrail

The orchestrator **will not provision a runtime unless an approved plan is
present and valid.** A human (the Operator) ratifies the plan *before* the
sandbox starts; the agent never self-approves. The boundary lives **outside and
below the agent** — the orchestrator refuses, and the seat it runs cannot bypass
that refusal.

The gate consumes an `ApprovedPlan` record:

| field | meaning |
| --- | --- |
| `run_id` | the run this approval authorizes; MUST equal the requested `run_id` |
| `policy_sha` | a 64-hex digest binding the approval to the exact runtime-policy version in force; MUST equal the record's `policy_sha` |
| `approved_by` | the ratifier identity (NOT the agent seat being run); MUST be non-empty |
| `approval_ref` | a pointer to the ratifying artifact (e.g. the forge issue / plan-PR); MUST be non-empty |

`run_plan` raises `PlanNotRatified` (a subclass of `runner.RunnerError`) BEFORE
the inner backend's `provision` is ever called when the approval is absent,
mis-bound (`run_id` / `policy_sha` mismatch), carries a non-hex `policy_sha`, or
is unattributed. This mirrors the G-1.0 `PolicyRejected` and the G-1.2
availability-gate "refuse before side effect" discipline. The inner backend's
own `provision` then re-applies the G-1.0 deny surface (`PolicyRejected` on an
unclean record) — a second, independent refusal surface the orchestrator does
not duplicate.

## Predicate summary

| predicate | refusal |
| --- | --- |
| approved plan present | `PlanNotRatified` when `approved_plan is None` |
| run bound | `PlanNotRatified` when `approved_plan.run_id != run_id` |
| policy bound | `PlanNotRatified` when `approved_plan.policy_sha` is not a 64-hex digest, or `!= runtime_policy["policy_sha"]` |
| attested | `PlanNotRatified` when `approved_by` or `approval_ref` is empty |
| backend resolvable | propagates `UnknownBackend` (e.g. `openshell`, not yet registered) |
| backend available | propagates `BackendUnavailable` (e.g. `gvisor-proxy` with no runsc) |
| policy clean | propagates the inner backend's `PolicyRejected` |

## Purity and the injectable backend seam

`run_plan` allocates no container, opens no socket, and runs no subprocess
itself. All live work stays behind the G-1.1 adapter and the G-1.2 injectable
seam: the backend is an injectable parameter, so CI exercises the full lifecycle
against the inert `LocalNoopBackend` with **zero live subprocess**. Because the
schema's `isolation_backend` enum is `[gvisor-proxy, openshell]` (it does not
include `local-noop`), a clean policy selects `gvisor-proxy` (availability-gated)
or `openshell` (a fast-follow, not yet registered) in production; tests inject
the inert backend directly. Importing the module performs zero I/O.

The returned evidence is the audit overlay's collect-time spine snapshot
(`provision`, `run`, `collect`), content-addressed and hash-chained and bound to
the run's `policy_sha`; a clean run satisfies `verify_chain(records) == []`.
`teardown` is still executed to release the runtime.

## Deferred (later G-2 hardening — NOT in G-2.0)

- **Forge-native approval source.** Populating `approved_by` / `approval_ref`
  from the architect's `forge.plan_approved(plan_ref)` query over an approved
  forge issue / plan-PR, and enforcing `approved_by` != the seat identity.
- **`mint_scoped_token`.** The least-privilege, short-TTL token minted per task
  between the approval gate and provision.
- **OpenShell** as a registered backend behind the same `RunnerBackend` adapter.
- **Real-clock + evidence persistence** behind the existing injectable seams.

This module is the seed for the architect's pre-committed `ce_orchestrator`
extraction; until then it lives in the installable validator package so the
existing CI pytest job covers it.
