# Contract: Thin Orchestrator + Approved-Plan Ratification Gate

Gate: v3 **G-2.0** — the thin orchestrator + the approved-plan ratification
gate (the first slice of G-2; opens the second MVP milestone after G-1 /
plane C is complete). **G-2.1** hardens it: the gate is wired to a forge-native
approval source-of-truth (`forge.plan_approved`) through an injected resolver
seam, and a no-self-approval guardrail (`approved_by` != the running
`seat_identity`) is enforced. **G-2.2** adds a JIT, least-privilege, time-boxed
per-run credential: an injected `token_minter` seam (`forge.mint_scoped_token` /
`revoke_scoped_token`) minted for the provisioned sandbox, gated on the policy
`secret_allowlist`, and attested to the evidence spine.
Validator check: **none** — the orchestrator is pure in-process glue behind the
G-1.1 runner adapter, and the G-2.1 resolver + the G-2.2 minter are pure behind
the G-iii forge `GhRunner` seam. Neither registers a `@register` check
(`--list-checks` stays **43**) nor an `isolation_backend` (`available_backends()`
stays `('gvisor-proxy', 'local-noop')`).
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
| not self-approved | `PlanNotRatified` when a `seat_identity` is supplied and `approved_by == seat_identity` |
| backend resolvable | propagates `UnknownBackend` (e.g. `openshell`, not yet registered) |
| backend available | propagates `BackendUnavailable` (e.g. `gvisor-proxy` with no runsc) |
| policy clean | propagates the inner backend's `PolicyRejected` |

## Forge-native approval resolution (G-2.1)

In G-2.0 the `ApprovedPlan` was a caller-supplied literal. G-2.1 makes the
**forge the source-of-truth** for it without coupling the orchestrator to the
forge: `run_plan` takes two keyword-only seams — `approval_resolver` and
`seat_identity`. When no `approved_plan` is supplied and a resolver is injected,
`run_plan` calls `approval_resolver(runtime_policy, run_id)` and gate-checks the
result. The production resolver is a thin closure over
`forge.plan_approved(query, *, seat_identity, gh_runner)`; injecting it (rather
than importing the forge here) keeps the orchestrator pure and forge-free.

`forge.plan_approved` resolves an `ApprovedPlan` from a plan-PR and returns it
only when **all** of the following hold (else it returns `None`; a transport
failure raises `ForgeConfigError`):

| axis | rule |
| --- | --- |
| run + policy bound | the PR body carries `ce-run-id:` / `ce-policy-sha:` markers equal to the requested `run_id` / `policy_sha` |
| commit-pinned | the `APPROVED` review's `commit_id` equals the PR head SHA (re-asserts GitHub's stale-on-commit-change behaviour) |
| independent | the approver is neither the PR author nor the running `seat_identity` (no self-approval) |
| state | only an `APPROVED` review counts (`COMMENTED` / `CHANGES_REQUESTED` do not) |

The resolved `approval_ref` is `{repo}#{pr}@{head_sha}`. Defence-in-depth: even a
caller-supplied or resolved plan is re-checked by the gate's `approved_by` !=
`seat_identity` guardrail, so the seat can never approve its own run on any path.
Like the rest of `forge/`, the resolver performs **zero** live network in
tests (the `GhRunner` is injected) and registers no check.

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
(`provision`, `run`, `collect`, plus the credential issuance/revocation records
when a `token_minter` is injected — see G-2.2), content-addressed and
hash-chained and bound to the run's `policy_sha`; a clean run satisfies
`verify_chain(records) == []`. `teardown` is still executed to release the
runtime.

## Per-run scoped credential (G-2.2)

Once a run is ratified, G-2.2 gives it a **just-in-time, least-privilege,
time-boxed, audited per-run credential** rather than a long-lived ambient token.
`run_plan` takes a third keyword-only seam — `token_minter` — and runs the
credential lifecycle *inside* the provisioned sandbox's lifecycle:

```
provision  ->  [mint + gate + attest]  ->  run  ->  [attest revocation]  ->  collect  ->  teardown
```

- **Ordering — provision first, then mint.** The sandbox is provisioned **without
  credentials**; the credential is minted JIT for that handle and (in production)
  injected at runtime via the backend/proxy. This matches the secure-runtime model
  ("the agent holds no network/secrets; the proxy holds both") and gives clean
  failure semantics — a provision failure mints nothing, and a refused/failed mint
  still tears the sandbox down (the mint runs under a `try` whose `finally` tears
  down). It refines the earlier "between the gate and provision" sketch.
- **Policy-gated issuance (the local permission ceiling).** When `token_minter`
  returns a `MintedCredential`, `run_plan` classifies a `SecretEvent(name=…)` for
  the credential's `secret_name` against the runtime-policy `secret_allowlist` via
  the G-1.3b classifier. `allowed` → the issuance is attested and the run proceeds;
  anything else → `CredentialNotPermitted` (after provision, before run/collect;
  the runtime is still torn down). A run can only mint a credential the policy
  already permits.
- **Attested to the spine.** Both the issuance (at the run phase) and the
  revocation (at the teardown phase, recorded *before* collect so it lands in the
  snapshot) are hash-chained evidence records bound to `policy_sha` — **without**
  the secret name's value, the token value, or the token ref. Revocation is
  defense-in-depth: release the credential the instant the run no longer needs it,
  not after its ≤1h ttl elapses (a 2-minute run must not hold a 60-minute token).
- **Secret hygiene — the orchestrator never holds the value.** The `MintedCredential`
  port type is deliberately **value-free** (it has no `value` field); the live secret
  lives only in the forge `ScopedToken` (redacted from its repr) and never enters the
  orchestrator or the evidence spine.

`forge.mint_scoped_token(request, *, gh_runner)` / `forge.revoke_scoped_token(token,
*, gh_runner)` do the actual minting/revocation behind the injectable `GhRunner`
(`POST app/installations/{id}/access_tokens` scoped to one repo + an explicit
least-privilege `permissions` subset; `DELETE installation/token`). They **refuse
before any forge call** (`TokenMintRefused`) an empty / `admin` / forbidden permission
set, a ttl outside `0 < t <= 3600`, a non-64-hex `policy_sha`, a malformed repo, or a
non-positive installation id. The production `token_minter` is a thin caller-side
closure that mints via `forge.mint_scoped_token`, maps the result to the value-free
`MintedCredential`, and arranges `forge.revoke_scoped_token` at completion — so the
orchestrator stays pure and forge-free, registering no check (`--list-checks` stays
**43**) and no backend, with **zero** live mint in tests (the `GhRunner` is injected).

## Evidence persistence + the composition root (G-3.6b)

The lifecycle's terminal disposition (G-3.1 / G-3.6a) opens/claims the PR for the
run's `RunChangeSet` through an injected `change_opener` and attests a typed
`runtime_run_outcome` record (`outcome: pr_opened` + a value-free `change_set`
pointer; on the disposition axis, never a `lifecycle_phase`). G-3.6b makes that
run's evidence **durable** and wires the production composition root:

- **The `evidence_sink` seam.** `run_plan` takes a keyword-only `evidence_sink`
  (the production wiring is the G-3.5 `evidence_sink.file_evidence_sink`). When
  injected, the run's **final** evidence — the full hash chain *including* the
  terminal run-outcome record — is persisted **after `teardown`, on the success
  path**. The sink is an injectable seam: the default `None` persists nothing and
  performs zero I/O (the orchestrator stays pure — it writes no file itself), and
  a non-conforming chain's `EvidencePersistRefused` **propagates** (it is a defect
  to surface, not swallow). The sink never re-hashes a record, so the persisted
  chain re-reads to `verify_chain() == []` and validates against
  `schemas/runtime-evidence.schema.yaml`.
- **The composition root — `run_assembly.make_run_driver(repo, root, …)`.** The
  first production `run` driver. It is the one place that imports `forge` and
  holds the live `ScopedToken.value` (the opposite of the pure orchestrator),
  assembling the seams into one `run_plan(...)` drive: the production
  `token_minter` (over `forge.mint_scoped_token` / `revoke_scoped_token` → the
  value-free `MintedCredential`), the **minter→runner bridge** (a closure cell
  sharing the one live `ScopedToken` from the minter to the `change_opener`'s
  authenticated `gh` runner via `forge.authenticated_gh_runner`, so the
  change-opener authenticates AS the same minted token while the orchestrator
  never sees the value), the production `change_opener` (over
  `forge.open_change(..., apply=False)`), and the `file_evidence_sink`. It revokes
  the credential at completion (success **or** failure). The live `value` lives
  only in the closure cell and, at call time, only in the child `gh` env — never
  the orchestrator, the evidence, argv, input, a log, disk, or the parent
  environment. The driver runs entirely offline against an injected backend +
  fake `gh_runner` / `spawn` / `write` (CI monkeypatches `subprocess` / `socket` /
  `Path.write_text` to explode); it is the exact entry G-3.7 promotes to live
  (`apply=True` + a real installation, outside the CI-purity envelope).

## Deferred (NOT in this slice)

- **The live spike (G-3.7)** — promoting the composition root to a real drive
  (`apply=True`, a real GitHub App installation, a real container) OUTSIDE the
  CI-purity envelope; the human-created App key never enters the task container.
- **`merge()` in the drive** — the gated squash-merge (`forge.merge`) is deferred
  to G-3.7; G-3.6b opens + persists only.
- **OpenShell** as a registered backend behind the same `RunnerBackend` adapter
  (the research-gated G-2.3).

This module is the seed for the architect's pre-committed `ce_orchestrator`
extraction; until then it lives in the installable validator package so the
existing CI pytest job covers it.
