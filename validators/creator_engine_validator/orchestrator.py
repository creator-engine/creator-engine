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
existing CI pytest job covers it. **G-2.1 hardening** wires the gate to a
forge-native approval source-of-truth via an injected ``approval_resolver`` seam
(the production resolver is a thin closure over ``forge.plan_approved``; the
orchestrator itself stays forge-free) and adds the no-self-approval guardrail
(``approved_by`` != the running ``seat_identity``). **G-2.2 hardening** wires a
per-run credential: an injected ``token_minter`` seam mints a JIT, least-privilege,
time-boxed credential for the provisioned sandbox (the production minter is a thin
closure over ``forge.mint_scoped_token`` mapping to a value-free ``MintedCredential``
port type — the live secret never crosses into the orchestrator), gates its issuance
on the runtime-policy ``secret_allowlist`` via the G-1.3b classifier, and attests the
issuance + revocation to the evidence spine. **G-3.1 wiring** threads the audited run's
in-manifest work (the value-free ``RunChangeSet`` pointers on the ``RunResult``) into the
merged ``forge.open_change`` via an injected ``change_opener`` seam: after ``collect`` the
lifecycle's terminal step opens/claims the PR plan-by-default (the production closure
captures the repo + a ``gh_runner`` factory — the orchestrator passes a factory, never a
raw token) and attests a typed terminal **run-outcome** record (G-3.6a: ``outcome:
pr_opened`` + a value-free ``change_set`` pointer, on the disposition axis ORTHOGONAL
to ``lifecycle_phase``) on the hash chain, so the lifecycle ends at "PR opened". See
``docs/contracts/orchestrator.md``.

Defensive only — authorization + accountability for our own agent runtime;
never offensive.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from .runner import (
    ALLOWED,
    AuditOverlayBackend,
    Clock,
    CollectedEvidence,
    CounterClock,
    ProvisionRequest,
    RunChangeSet,
    RunnerBackend,
    RunnerError,
    RunRequest,
    SecretEvent,
    get_backend,
)
from .runtime_evidence_spine import (
    RATIFICATION_RECORD_KIND,
    RATIFICATION_RECORD_TYPE,
    RUN_OUTCOME_RECORD_KIND,
    RUN_OUTCOME_RECORD_TYPE,
    append,
    compute_binding_ref,
    is_policy_sha,
)

if TYPE_CHECKING:  # type-only: the orchestrator imports ZERO from ``forge`` at runtime
    from .evidence_sink import EvidenceSink
    from .forge.change import ChangeRef
    from .forge.merge import MergeResult


class PlanNotRatified(RunnerError):
    """The approved-plan ratification gate refused: no provision may proceed.

    Raised BEFORE any backend side effect when the run is not bound to a valid,
    human-ratified plan anchored to the exact runtime-policy (``policy_sha``).
    """


class RatificationBindingRefused(RunnerError):
    """The runtime head-SHA assertion refused: the runtime drifted from what was ratified.

    Raised BEFORE the change-open (the point a live drive promotes to ``apply=True``)
    when the SHA-pinned ratification is ENGAGED (``ApprovedPlan.ratified_head_sha`` set)
    but the change's ``head_sha`` differs from the ratified head, or the recomputed
    ``binding_ref`` over the in-force ``{repo, installation_id, permissions,
    ratified_head_sha}`` tuple differs from the ratified one. Value-free: the message
    names the run + that the binding drifted, never an account / secret / host.
    """


@dataclass(frozen=True)
class ApprovedPlan:
    """A human-ratified plan attestation that authorizes one orchestrated run.

    The gate requires this record to be present and bound to the exact run:
    ``policy_sha`` anchors the approval to the runtime-policy version in force and
    ``run_id`` to the specific run. ``approved_by`` is the ratifier identity (NOT
    the agent seat being run — the agent never self-approves) and ``approval_ref``
    points at the ratifying artifact (e.g. the forge issue / plan-PR). These may
    be caller-supplied, or (G-2.1) resolved from the forge by an injected
    ``approval_resolver`` (``forge.plan_approved``); ``run_plan`` enforces
    ``approved_by`` != the running ``seat_identity`` either way.

    **G-3.7.2b SHA-pinned binding (optional, value-free).** When ``ratified_head_sha``
    is set the run is bound to a SHA-pinned ratification: ``run_plan`` asserts the
    change being opened is at exactly that head (+ the recomputed ``binding_ref``
    matches the in-force ``{repo, installation_id, permissions, ratified_head_sha}``
    tuple) BEFORE the change-open, REFUSING drift, and appends a value-free
    ``runtime_ratification_record`` (the opaque ``approver_ref`` / ``ratified_prompt_sha``
    / ``binding_ref`` + the pinned ``ratified_head_sha``) to the evidence chain. These
    fields are opaque digests the CALLER supplies (the orchestrator never derives an
    identity); they default empty, so an unbound plan leaves the gate inert and the
    run byte-for-byte unchanged.
    """

    run_id: str
    policy_sha: str
    approved_by: str
    approval_ref: str
    ratified_head_sha: str = ""
    binding_ref: str = ""
    approver_ref: str = ""
    ratified_prompt_sha: str = ""


# A resolver maps (runtime_policy, run_id) -> the ApprovedPlan to gate-check, or
# None when the forge holds no valid ratification. The production resolver is a
# thin closure over ``forge.plan_approved``; injecting it (rather than importing
# the forge here) keeps the orchestrator pure and forge-free.
ApprovalResolver = Callable[[dict[str, Any], str], "ApprovedPlan | None"]


class CredentialNotPermitted(RunnerError):
    """The runtime-policy does not permit the per-run credential the run requested.

    Raised AFTER provision (the issuance is attested to the spine first) when the
    classifier denies the credential's ``secret_name`` against the runtime-policy
    ``secret_allowlist`` — the local least-privilege "permission ceiling" check. The
    provisioned runtime is still torn down (the mint is gated, not leaked).
    """


@dataclass(frozen=True)
class MintedCredential:
    """A JIT per-run credential's *attestable metadata* — deliberately value-free.

    The orchestrator gates and attests a minted credential through this port type and
    NEVER holds the live secret value (a type-level guarantee: there is no ``value``
    field). The secret lives only in the forge ``ScopedToken`` (redacted from its repr);
    the production ``token_minter`` closure mints via ``forge.mint_scoped_token``, maps the
    result to this value-free record, and arranges ``forge.revoke_scoped_token`` at
    completion. ``secret_name`` is the logical secret the credential satisfies (gated
    against the policy ``secret_allowlist``); ``permissions`` the least-privilege subset
    granted; ``expires_at`` the forge-granted expiry; ``credential_ref`` a non-secret
    correlation pointer.
    """

    run_id: str
    policy_sha: str
    secret_name: str
    permissions: tuple[tuple[str, str], ...]
    expires_at: str
    credential_ref: str


# A minter maps (runtime_policy, run_id) -> the MintedCredential for the run, or None
# when no per-run credential is needed. The production minter is a thin closure over
# ``forge.mint_scoped_token`` that maps the (value-bearing) ScopedToken to the value-free
# MintedCredential port type and arranges ``forge.revoke_scoped_token`` at completion;
# injecting it (rather than importing the forge here) keeps the orchestrator pure and
# forge-free, and keeps the live secret value out of the orchestrator entirely.
TokenMinter = Callable[[dict[str, Any], str], "MintedCredential | None"]


# A change-opener maps (the run's RunChangeSet, the 64-hex plan_ref) -> the value-free
# ChangeRef for the opened/claimed PR, or None when no change is to be opened. The
# production change_opener is a thin closure capturing the repo + a ``gh_runner`` FACTORY
# (a ``Callable[[], GhRunner]``) that calls ``forge.open_change(..., apply=False)`` and
# never a raw token; auth stays in the runner's env, never in argv, never here. Injecting
# it (rather than importing the forge) keeps the orchestrator pure and forge-free, and the
# credential value-injection into the runner env is a later, deferred seam (G-3.4). For
#   def make_change_opener(repo, gh_runner_factory):
#       def change_opener(change_set, plan_ref):
#           return open_change(repo, change_set.branch, change_set.base,
#                              change_set.manifest_paths, plan_ref,
#                              apply=False, gh_runner=gh_runner_factory())
#       return change_opener
ChangeOpener = Callable[["RunChangeSet", str], "ChangeRef | None"]


# A change-merger drives the gated merge of an ALREADY-OPEN, reviewed PR and returns the
# value-free MergeResult (whether it ``merged`` / ``would_merge`` + the gate snapshot; it holds
# NO token). The production closure (see ``run_assembly.make_merge_driver``) wraps
# ``forge.merge(change, apply=live, gh_runner=<the DISTINCT merge identity — NEVER the per-run
# token>)``; injecting it (rather than importing the forge here) keeps the orchestrator pure and
# forge-free, and keeps the merge credential out of the orchestrator entirely. Zero-arg: the
# closure captures the already-open change to merge.
ChangeMerger = Callable[[], "MergeResult"]


def _ratify_or_refuse(
    runtime_policy: dict[str, Any],
    run_id: str,
    approved_plan: ApprovedPlan | None,
    seat_identity: str | None = None,
) -> None:
    """Raise :class:`PlanNotRatified` unless ``approved_plan`` authorizes the run.

    Enforced BEFORE any provision. The approval must be present, bound to the
    exact ``run_id``, anchored to the runtime-policy's ``policy_sha`` (a 64-hex
    digest), carry a non-empty ratifier identity + approval reference, and — when
    a ``seat_identity`` is supplied — NOT be approved by the running seat itself
    (the agent never self-approves; the guardrail holds for both caller-supplied
    and forge-resolved plans).
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
    if seat_identity is not None and approved_plan.approved_by == seat_identity:
        raise PlanNotRatified(
            f"approved plan approved_by {approved_plan.approved_by!r} is the running seat "
            "(a seat may not approve its own run)"
        )


def run_plan(
    runtime_policy: dict[str, Any],
    run_id: str,
    command: Sequence[str],
    approved_plan: ApprovedPlan | None,
    *,
    backend: RunnerBackend | None = None,
    clock: Clock | None = None,
    approval_resolver: ApprovalResolver | None = None,
    seat_identity: str | None = None,
    token_minter: TokenMinter | None = None,
    change_opener: ChangeOpener | None = None,
    evidence_sink: "EvidenceSink | None" = None,
    binding_inputs: dict[str, Any] | None = None,
) -> CollectedEvidence:
    """Drive one ratified, audited agent-seat run and return its collected evidence.

    Thin glue, in order:

    0. **resolve approval** — if no ``approved_plan`` is supplied and an
       ``approval_resolver`` is injected (production wires it to
       ``forge.plan_approved``), resolve the plan from the forge source-of-truth;
    1. **gate-check** — :func:`_ratify_or_refuse` raises :class:`PlanNotRatified`
       BEFORE any side effect if the run is not ratified + bound to this policy,
       or if ``seat_identity`` approved its own run;
    2. **resolve** the inner isolation backend — the injected ``backend`` else
       ``get_backend(runtime_policy["isolation_backend"])``;
    3. **wrap** it in :class:`AuditOverlayBackend` so every lifecycle step is
       attested to the hash-chained evidence spine, bound to the policy;
    4. **drive** ``provision -> [mint] -> run -> [revoke] -> collect -> [open
       change] -> teardown`` and return the collected evidence (the audit
       overlay's collect-time spine snapshot; teardown is still executed to
       release the runtime). When a ``token_minter`` is injected, a JIT per-run
       credential is minted for the provisioned sandbox, its issuance gated on
       the policy ``secret_allowlist`` and attested, and its revocation attested
       before collect (:class:`CredentialNotPermitted` if the policy forbids it).

    **G-3.1 wiring.** The run's in-manifest work crosses the runner seam as DATA
    (the value-free :class:`~.runner.RunChangeSet` pointers on the ``RunResult``).
    When a ``change_opener`` is injected and the run produced a change-set, the
    lifecycle's terminal step (after ``collect``) opens/claims the PR for that
    change plan-by-default (the production closure captures the repo + a
    ``gh_runner`` factory and calls ``forge.open_change(..., apply=False)`` — the
    orchestrator passes a factory, never a raw token), attests a typed terminal
    run-outcome record (G-3.6a — ``outcome: pr_opened`` + a value-free ``change_set``
    pointer; a distinct ``runtime_run_outcome`` record type on the disposition axis,
    NEVER a ``lifecycle_phase``) on the hash chain, and surfaces the change-set on the
    returned evidence — so the lifecycle ends at "PR opened," not "evidence collected."
    A ``None`` ``change_opener`` (or a run with no change-set) is the existing
    G-2.x behavior, byte-for-byte unchanged.

    **G-3.6b wiring.** When an ``evidence_sink`` is injected (production wires the
    G-3.5 :func:`~.evidence_sink.file_evidence_sink`), the run's FINAL evidence —
    the full hash chain INCLUDING the terminal run-outcome record — is persisted
    AFTER ``teardown``, on the success path. The sink is an injectable seam
    (default ``None`` = no persistence, zero I/O — the orchestrator stays pure and
    performs no I/O itself); a non-conforming chain's
    :class:`~.evidence_sink.EvidencePersistRefused` PROPAGATES (it is a defect to
    surface, not swallow). The value-bearing per-run credential is the
    composition root's concern (see ``run_assembly``); it never reaches here.

    Allocates no container and runs no subprocess itself; in CI it is exercised
    against the inert ``LocalNoopBackend`` with zero live subprocess. Propagates
    the backend's own refusals unchanged: ``PolicyRejected`` on an unclean
    runtime-policy, ``BackendUnavailable`` / ``UnknownBackend`` on resolution.
    """
    # 0) Resolve the approval from the forge if not supplied (injected resolver).
    if approved_plan is None and approval_resolver is not None:
        approved_plan = approval_resolver(runtime_policy, run_id)

    # 1) Ratification gate — refuse BEFORE any side effect (the locked guardrail).
    _ratify_or_refuse(runtime_policy, run_id, approved_plan, seat_identity)

    # 2) Resolve the inner backend (injected for tests, else by the policy selector).
    inner = backend if backend is not None else get_backend(runtime_policy["isolation_backend"])

    # 3) Wrap in the audit overlay so every lifecycle step is attested. Resolve the
    #    clock HERE (not only inside the overlay) so the terminal run-outcome record
    #    (G-3.6a) shares the SAME monotonic clock instance as the lifecycle records.
    clock = clock if clock is not None else CounterClock()
    overlay = AuditOverlayBackend(inner, clock=clock)

    # 4) Drive the lifecycle. The inner backend's provision() re-applies the G-1.0
    #    deny surface (PolicyRejected on an unclean record) — not duplicated here.
    handle = overlay.provision(ProvisionRequest(runtime_policy=runtime_policy, run_id=run_id))
    try:
        # 4.5) G-2.2: mint a JIT, least-privilege, time-boxed per-run credential for the
        #      provisioned sandbox (sandbox up FIRST, no creds; the credential is injected
        #      at runtime — a deferred backend seam). The live secret stays in the forge
        #      minter; only the value-free MintedCredential crosses into the orchestrator.
        credential = token_minter(runtime_policy, run_id) if token_minter is not None else None
        if credential is not None:
            # Gate the issuance on the runtime-policy secret_allowlist via the G-1.3b
            # classifier (the local permission-ceiling check) AND attest it to the spine.
            issuance = overlay.observe(handle, SecretEvent(name=credential.secret_name))
            if issuance.get("classification") != ALLOWED:
                raise CredentialNotPermitted(
                    f"runtime-policy does not permit credential {credential.secret_name!r} "
                    f"for run {run_id!r}; refusing (secret not in the policy secret_allowlist)"
                )
        run_result = overlay.run(handle, RunRequest(command=tuple(command)))
        if credential is not None:
            # The run no longer needs the credential → attest its revocation BEFORE collect
            # (so it lands in the collect snapshot). The live forge DELETE is the injected
            # minter seam's job; here we record the release, bound to the policy.
            overlay.observe(handle, SecretEvent(name=credential.secret_name, phase="teardown"))
        evidence = overlay.collect(handle)
        # 4.6) G-3.1 + G-3.6a: the lifecycle's terminal disposition. The run's in-manifest
        #      work crosses the seam as DATA (run_result.change_set). When a change_opener is
        #      injected and the run produced a change-set, open/claim the PR plan-by-default
        #      (the closure calls forge.open_change(apply=False) through a gh_runner factory —
        #      value-free, no raw token here), then attest a TYPED run-outcome record AFTER
        #      collect. The outcome is its OWN record type on the disposition axis (NOT a
        #      lifecycle_phase; outcomes are plural — pr_opened here), appended to the SAME
        #      hash chain via the spine `append` so it is itself tamper-evident, carrying a
        #      value-free change_set pointer (+ pr_number when the ChangeRef has one). A None
        #      change_opener (or a run with no change-set) ends at the clean lifecycle.
        if change_opener is not None and run_result.change_set is not None:
            # 4.6a) G-3.7.2b: the runtime head-SHA assertion. When the ratification is
            #       SHA-pinned (ratified_head_sha set), REFUSE — BEFORE the change-open (the
            #       point a live drive promotes to apply=True) — unless the change is at the
            #       ratified head AND the recomputed binding_ref matches the in-force
            #       {repo, installation_id, permissions, ratified_head_sha} tuple. The agent
            #       seat cannot bypass this; an unbound plan (ratified_head_sha == "") is inert.
            if approved_plan.ratified_head_sha:
                if run_result.change_set.head_sha != approved_plan.ratified_head_sha:
                    raise RatificationBindingRefused(
                        f"run {run_id!r} change head_sha drifted from the ratified head "
                        "(refusing to open a change not bound to the ratified head)"
                    )
                if binding_inputs is not None:
                    # 4.6b) G-3.7.3a: when run_assembly supplies a LIVE observed-base-head
                    #       (live mode reads the real repo head and passes it as DATA), the
                    #       ratification ALSO binds the INDEPENDENTLY-OBSERVED head — not just the
                    #       agent-claimed change head — so a compromised/buggy seat that merely
                    #       CLAIMS the ratified head cannot drive a live apply against a different
                    #       real head. Absent observed_head_sha (the CI-pure / pre-3.7.3a path)
                    #       this is a no-op (byte-for-byte the 3.7.2b assertions).
                    observed_head_sha = binding_inputs.get("observed_head_sha")
                    if (
                        observed_head_sha is not None
                        and observed_head_sha != approved_plan.ratified_head_sha
                    ):
                        raise RatificationBindingRefused(
                            f"run {run_id!r} observed head_sha drifted from the ratified head "
                            "(the live-observed repo head is not the ratified head)"
                        )
                    recomputed = compute_binding_ref(
                        binding_inputs["repo"],
                        binding_inputs["installation_id"],
                        binding_inputs["permissions"],
                        approved_plan.ratified_head_sha,
                    )
                    if recomputed != approved_plan.binding_ref:
                        raise RatificationBindingRefused(
                            f"run {run_id!r} ratification binding_ref mismatch "
                            "(the in-force repo/installation/permissions tuple drifted from "
                            "the ratified binding)"
                        )
            ref = change_opener(run_result.change_set, approved_plan.policy_sha)
            cs = run_result.change_set
            change_set_ptr: dict[str, Any] = {
                "branch": cs.branch,
                "base": cs.base,
                "manifest_paths": list(cs.manifest_paths),
                "head_sha": cs.head_sha,
            }
            pr_number = getattr(ref, "pr_number", None)
            if pr_number is not None:
                change_set_ptr["pr_number"] = pr_number
            opened = append(
                list(evidence.records),
                {
                    "kind": RUN_OUTCOME_RECORD_KIND,
                    "record_type": RUN_OUTCOME_RECORD_TYPE,
                    "schema_version": "1",
                    "policy_sha": approved_plan.policy_sha,
                    "run_id": handle.run_id,
                    "recorded_at": clock(),
                    "outcome": "pr_opened",
                    "change_set": change_set_ptr,
                },
            )
            evidence = replace(
                evidence,
                records=tuple(evidence.records) + (opened,),
                change_set=run_result.change_set,
                note=f"{evidence.note}; run-outcome: pr_opened",
            )
            # 4.6b) G-3.7.2b: when the run was SHA-pinned-ratified (and the assertion above
            #       passed), attest the ratification itself as a typed, value-free record on the
            #       SAME hash chain — the opaque approver/prompt/binding digests + the pinned
            #       head SHA — so the authorization that admitted the change is auditable. The
            #       orchestrator copies the caller-supplied opaque digests verbatim (it never
            #       derives an identity). An unbound plan appends nothing (byte-for-byte the
            #       pre-3.7.2b chain).
            if approved_plan.ratified_head_sha:
                ratified = append(
                    list(evidence.records),
                    {
                        "kind": RATIFICATION_RECORD_KIND,
                        "record_type": RATIFICATION_RECORD_TYPE,
                        "schema_version": "1",
                        "policy_sha": approved_plan.policy_sha,
                        "run_id": handle.run_id,
                        "recorded_at": clock(),
                        "ratified_prompt_sha": approved_plan.ratified_prompt_sha,
                        "approver_ref": approved_plan.approver_ref,
                        "ratified_head_sha": approved_plan.ratified_head_sha,
                        "binding_ref": approved_plan.binding_ref,
                    },
                )
                evidence = replace(
                    evidence,
                    records=tuple(evidence.records) + (ratified,),
                    note=f"{evidence.note}; ratified",
                )
    finally:
        overlay.teardown(handle)
    # G-3.6b: persist the run's FINAL evidence (with the terminal run-outcome record) via the
    # injected G-3.5 sink, AFTER teardown, on the success path. The sink is an injectable seam
    # (default None = today's behavior, zero I/O — the orchestrator stays pure); a malformed
    # chain's EvidencePersistRefused PROPAGATES (non-conforming evidence is a defect to surface).
    if evidence_sink is not None:
        evidence_sink(evidence)
    return evidence


def merge_change(
    prior_evidence: CollectedEvidence,
    *,
    run_id: str,
    policy_sha: str,
    change_merger: ChangeMerger,
    evidence_sink: "EvidenceSink | None" = None,
    clock: Clock | None = None,
) -> CollectedEvidence:
    """Drive a gated merge of an already-open, reviewed PR; attest a typed ``pr_merged`` outcome.

    The disposition AFTER review (G-3.7b.1) — a merge acts on an ALREADY-OPEN, gate-eligible PR,
    so it is its OWN entry, distinct from the agent-run :func:`run_plan`. Thin, forge-free glue:

    1. **drive the merge** via the injected ``change_merger`` (the production closure wraps
       ``forge.merge`` through a DISTINCT merge identity — NEVER the per-run token; see
       ``run_assembly.make_merge_driver``). It returns the value-free :class:`~.forge.merge.MergeResult`
       (duck-typed here — the orchestrator imports ZERO from ``forge`` at runtime);
    2. **attest only an ACTUAL merge** — when ``result.merged`` is True (the ``apply``/live path),
       append a TYPED ``runtime_run_outcome`` record (``outcome: pr_merged`` + the value-free
       ``change_set`` pointer carried from the open drive — branch / base / manifest_paths / head_sha
       + the PR number; NO secret, and NO ``merge_commit_sha`` slot under the v1 schema) onto the
       SAME hash chain via the spine :func:`~.runtime_evidence_spine.append`, so the merge
       disposition is itself tamper-evident; then persist via the injected sink. A NON-mutating
       plan-mode preview (``would_merge`` but not ``merged``) or a gate-ineligible result attests
       NOTHING (``pr_merged`` means the PR was ACTUALLY merged, never a dry run); a
       ``change_merger`` that RAISES (e.g. ``forge.merge(apply=True)`` refused an ineligible PR)
       PROPAGATES, leaving no partial record.

    Holds no credential, allocates nothing, runs no subprocess; in CI it is exercised against a
    fake ``change_merger`` with zero live I/O. The merge identity is the composition root's
    concern (``run_assembly``); it never reaches here.
    """
    clock = clock if clock is not None else CounterClock()
    result = change_merger()
    if not bool(getattr(result, "merged", False)):
        # Not actually merged (a plan-mode would-merge preview, or a gate-ineligible result):
        # attest nothing and persist nothing; the caller surfaces the MergeResult disposition.
        return prior_evidence
    change_set = prior_evidence.change_set
    if change_set is None:
        raise ValueError(
            f"merge_change for run {run_id!r} requires the open drive's change_set "
            "(the value-free pointer to the merged change) to attest the pr_merged outcome"
        )
    change_set_ptr: dict[str, Any] = {
        "branch": change_set.branch,
        "base": change_set.base,
        "manifest_paths": list(change_set.manifest_paths),
        "head_sha": change_set.head_sha,
    }
    pr_number = getattr(result, "pr_number", None)
    if pr_number is not None:
        change_set_ptr["pr_number"] = pr_number
    merged_record = append(
        list(prior_evidence.records),
        {
            "kind": RUN_OUTCOME_RECORD_KIND,
            "record_type": RUN_OUTCOME_RECORD_TYPE,
            "schema_version": "1",
            "policy_sha": policy_sha,
            "run_id": run_id,
            "recorded_at": clock(),
            "outcome": "pr_merged",
            "change_set": change_set_ptr,
        },
    )
    evidence = replace(
        prior_evidence,
        records=tuple(prior_evidence.records) + (merged_record,),
        note=f"{prior_evidence.note}; run-outcome: pr_merged",
    )
    if evidence_sink is not None:
        evidence_sink(evidence)
    return evidence
