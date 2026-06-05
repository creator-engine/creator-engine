"""Unit tests for the v3 G-2.0 thin orchestrator + approved-plan ratification gate.

The orchestrator is pure glue: it gate-checks an ``ApprovedPlan``, resolves an
isolation backend (injected for tests, else by the runtime-policy's
``isolation_backend``), wraps it in the ``AuditOverlayBackend``, and drives
``provision -> run -> collect -> teardown``, returning the collected
hash-chained evidence. The ratification gate refuses BEFORE any provision. These
tests run against the inert ``LocalNoopBackend`` with ZERO live subprocess and
write nothing to disk, and confirm the orchestrator registers no validator check
and no backend (``--list-checks`` and ``available_backends()`` unchanged).
"""

import socket
import subprocess

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.orchestrator import (
    ApprovedPlan,
    CredentialNotPermitted,
    MintedCredential,
    PlanNotRatified,
    run_plan,
)
from creator_engine_validator.forge import open_change
from creator_engine_validator.runner import (
    BackendUnavailable,
    CollectedEvidence,
    PolicyRejected,
    ProvisionedHandle,
    ProvisionRequest,
    RunChangeSet,
    RunnerBackend,
    RunRequest,
    RunResult,
    TeardownResult,
    UnknownBackend,
    available_backends,
)
from creator_engine_validator.runner.audit_overlay import CounterClock
from creator_engine_validator.runner.noop_backend import LocalNoopBackend
from creator_engine_validator.runtime_evidence_spine import verify_chain

_POLICY_SHA = "a" * 64
_OTHER_SHA = "c" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy(isolation_backend: str = "gvisor-proxy") -> dict:
    """A fully schema-clean runtime-policy record (the inner backend validates it)."""
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "gvisor-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": isolation_backend,
        "image_ref": {"name": "registry.example/creator-engine/implementer", "sha": _IMAGE_SHA},
        "mount_manifest": [
            {"path": "/runtime/worktree", "mode": "rw", "write_justification": "allocated worktree"},
            {"path": "governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "protocol": "https", "assurance": ["l4"]},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


def approved(run_id: str = "run-1", policy_sha: str = _POLICY_SHA) -> ApprovedPlan:
    return ApprovedPlan(
        run_id=run_id,
        policy_sha=policy_sha,
        approved_by="operator",
        approval_ref="forge-issue#42",
    )


class _SpyBackend(RunnerBackend):
    """Records the lifecycle call order; delegates to an inert ``LocalNoopBackend``."""

    backend_key = "spy"

    def __init__(self) -> None:
        self._inner = LocalNoopBackend()
        self.calls: list[str] = []

    def provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        self.calls.append("provision")
        return self._inner.provision(request)

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        self.calls.append("run")
        return self._inner.run(handle, request)

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        self.calls.append("collect")
        return self._inner.collect(handle)

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        self.calls.append("teardown")
        return self._inner.teardown(handle)


# ---------------------------------------------------------------------------
# The ratification gate — refuse BEFORE any provision (no side effect on refusal)
# ---------------------------------------------------------------------------
def test_gate_refuses_when_no_approved_plan():
    spy = _SpyBackend()
    with pytest.raises(PlanNotRatified):
        run_plan(valid_policy(), "run-1", ("echo", "hi"), None, backend=spy)
    assert spy.calls == []  # nothing was provisioned


def test_gate_refuses_on_policy_sha_mismatch():
    spy = _SpyBackend()
    with pytest.raises(PlanNotRatified):
        run_plan(valid_policy(), "run-1", ("echo", "hi"), approved(policy_sha=_OTHER_SHA), backend=spy)
    assert spy.calls == []


def test_gate_refuses_on_run_id_mismatch():
    spy = _SpyBackend()
    with pytest.raises(PlanNotRatified):
        run_plan(valid_policy(), "run-1", ("echo", "hi"), approved(run_id="other-run"), backend=spy)
    assert spy.calls == []


def test_gate_refuses_on_non_hex_policy_sha():
    spy = _SpyBackend()
    policy = valid_policy()
    policy["policy_sha"] = "not-a-64-hex-digest"
    bad = ApprovedPlan(run_id="run-1", policy_sha="not-a-64-hex-digest", approved_by="op", approval_ref="r")
    with pytest.raises(PlanNotRatified):
        run_plan(policy, "run-1", ("echo", "hi"), bad, backend=spy)
    assert spy.calls == []


def test_gate_refuses_on_missing_attestation():
    spy = _SpyBackend()
    unattributed = ApprovedPlan(run_id="run-1", policy_sha=_POLICY_SHA, approved_by="", approval_ref="")
    with pytest.raises(PlanNotRatified):
        run_plan(valid_policy(), "run-1", ("echo", "hi"), unattributed, backend=spy)
    assert spy.calls == []


# ---------------------------------------------------------------------------
# Thin lifecycle glue — happy path against the injected inert backend
# ---------------------------------------------------------------------------
def test_run_plan_drives_lifecycle_and_returns_verifiable_evidence():
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=LocalNoopBackend(), clock=CounterClock(),
    )
    assert isinstance(evidence, CollectedEvidence)
    # collect() folds the spine snapshot at collect-time: provision, run, collect.
    phases = [r["lifecycle_phase"] for r in evidence.records]
    assert phases == ["provision", "run", "collect"]
    assert verify_chain(list(evidence.records)) == []  # content-addressed + hash-chained, clean
    assert all(r["policy_sha"] == _POLICY_SHA for r in evidence.records)  # bound to the policy in force


def test_run_plan_invokes_full_lifecycle_in_order():
    spy = _SpyBackend()
    run_plan(valid_policy(), "run-1", ("echo", "hi"), approved(), backend=spy, clock=CounterClock())
    assert spy.calls == ["provision", "run", "collect", "teardown"]


def test_run_plan_propagates_backend_policy_rejection():
    # The gate passes (policy_sha + run_id bind), then the inner backend refuses an
    # unclean record (image not digest-pinned) at provision — a SECOND refusal surface.
    policy = valid_policy()
    policy["image_ref"] = {"name": "registry.example/x", "sha": "not-a-digest"}
    with pytest.raises(PolicyRejected):
        run_plan(policy, "run-1", ("echo", "hi"), approved(), backend=LocalNoopBackend())


# ---------------------------------------------------------------------------
# Backend resolution path (no injection) — deterministic, no live work
# ---------------------------------------------------------------------------
def test_unknown_isolation_backend_raises_unknown_backend():
    # ``openshell`` is a schema-valid selector but not registered yet → UnknownBackend.
    with pytest.raises(UnknownBackend):
        run_plan(valid_policy("openshell"), "run-1", ("echo", "hi"), approved())


def test_gvisor_backend_unavailable_raises_backend_unavailable():
    # ``gvisor-proxy`` is registered but availability-gated; with no runsc in this
    # environment the backend refuses at provision (no live subprocess spawned).
    with pytest.raises(BackendUnavailable):
        run_plan(valid_policy("gvisor-proxy"), "run-1", ("echo", "hi"), approved())


# ---------------------------------------------------------------------------
# Invariants — registers no check / no backend; zero live surface
# ---------------------------------------------------------------------------
def test_orchestrator_registers_no_check_and_no_backend():
    import creator_engine_validator.orchestrator  # noqa: F401  (import = the side-effect surface)

    assert not any("orchestrat" in n for n in registered_checks())
    assert available_backends() == ("gvisor-proxy", "local-noop")  # no isolation_backend added


def test_run_plan_no_live_subprocess_or_socket(monkeypatch):
    # The orchestrator (and the inert inner backend) must run a full lifecycle
    # without ever shelling out or opening a socket. (Schema validation reads files
    # via the validator's own loader — a read, not a live runtime call.)
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the orchestrator must not touch a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)

    evidence = run_plan(valid_policy(), "run-1", ("echo", "hi"), approved(), backend=LocalNoopBackend())
    assert isinstance(evidence, CollectedEvidence)


# ---------------------------------------------------------------------------
# G-2.1 — forge-native approval resolver seam + no-self-approval guardrail
# ---------------------------------------------------------------------------
def test_run_plan_resolves_approval_via_injected_resolver():
    # With no explicit approved_plan, run_plan consults the injected resolver
    # (the production path wires this to forge.plan_approved) and drives the run.
    spy = _SpyBackend()
    calls: list[tuple] = []

    def resolver(runtime_policy, run_id):
        calls.append((runtime_policy["policy_sha"], run_id))
        return approved(run_id=run_id)

    run_plan(
        valid_policy(), "run-1", ("echo", "hi"), None,
        backend=spy, clock=CounterClock(), approval_resolver=resolver,
    )
    assert spy.calls == ["provision", "run", "collect", "teardown"]
    assert calls == [(_POLICY_SHA, "run-1")]  # resolver consulted with the policy + run in force


def test_run_plan_refuses_when_resolver_returns_no_approval():
    spy = _SpyBackend()
    with pytest.raises(PlanNotRatified):
        run_plan(
            valid_policy(), "run-1", ("echo", "hi"), None,
            backend=spy, approval_resolver=lambda rp, rid: None,
        )
    assert spy.calls == []  # refused before any provision


def test_gate_refuses_self_approval_by_seat():
    # The seat may not approve its own run, even with an otherwise-valid plan.
    spy = _SpyBackend()
    self_plan = ApprovedPlan(
        run_id="run-1", policy_sha=_POLICY_SHA, approved_by="seat-agent", approval_ref="ref",
    )
    with pytest.raises(PlanNotRatified):
        run_plan(valid_policy(), "run-1", ("echo", "hi"), self_plan, backend=spy, seat_identity="seat-agent")
    assert spy.calls == []  # refused before any provision


def test_seat_identity_allows_independent_approver():
    # An independent approver (approved_by="operator" != seat) passes the guardrail.
    spy = _SpyBackend()
    run_plan(valid_policy(), "run-1", ("echo", "hi"), approved(), backend=spy, seat_identity="seat-agent")
    assert spy.calls == ["provision", "run", "collect", "teardown"]


# ---------------------------------------------------------------------------
# G-2.2 — JIT scoped-credential minter seam (provision -> mint -> gate+attest
# -> run -> attest revocation -> collect -> teardown)
# ---------------------------------------------------------------------------
def _credential(secret_name: str = "model-provider-key") -> MintedCredential:
    return MintedCredential(
        run_id="run-1",
        policy_sha=_POLICY_SHA,
        secret_name=secret_name,
        permissions=(("contents", "read"),),
        expires_at="2026-06-03T15:00:00Z",
        credential_ref="creator-engine/creator-engine@2026-06-03T15:00:00Z",
    )


def test_token_minter_issues_and_revokes_attesting_to_the_spine():
    # The minted credential's secret_name IS in the policy secret_allowlist → allowed;
    # issuance + revocation are attested to the spine around the run, bound to the policy.
    minter_calls: list[tuple] = []

    def minter(runtime_policy, run_id):
        minter_calls.append((runtime_policy["policy_sha"], run_id))
        return _credential()

    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=LocalNoopBackend(), clock=CounterClock(), token_minter=minter,
    )
    assert minter_calls == [(_POLICY_SHA, "run-1")]  # consulted with the policy + run in force
    phases = [r["lifecycle_phase"] for r in evidence.records]
    assert phases == ["provision", "run", "run", "teardown", "collect"]  # issuance(run)+revocation(teardown)
    assert verify_chain(list(evidence.records)) == []
    assert all(r["policy_sha"] == _POLICY_SHA for r in evidence.records)
    assert all("value" not in r for r in evidence.records)  # no secret value on the spine


def test_token_minter_credential_not_in_allowlist_is_refused_after_provision():
    # The classifier (policy secret_allowlist) is the local permission-ceiling check.
    spy = _SpyBackend()
    with pytest.raises(CredentialNotPermitted):
        run_plan(
            valid_policy(), "run-1", ("echo", "hi"), approved(),
            backend=spy, clock=CounterClock(),
            token_minter=lambda rp, rid: _credential(secret_name="unlisted-secret"),
        )
    assert spy.calls == ["provision", "teardown"]  # gated after provision; run/collect skipped; still torn down


def test_token_minter_returning_none_drives_normal_lifecycle():
    spy = _SpyBackend()
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=spy, clock=CounterClock(), token_minter=lambda rp, rid: None,
    )
    assert spy.calls == ["provision", "run", "collect", "teardown"]
    assert [r["lifecycle_phase"] for r in evidence.records] == ["provision", "run", "collect"]


def test_no_token_minter_is_backward_compatible():
    # Identical to the G-2.0/2.1 behaviour: provision, run, collect (+ teardown after).
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=LocalNoopBackend(), clock=CounterClock(),
    )
    assert [r["lifecycle_phase"] for r in evidence.records] == ["provision", "run", "collect"]


def test_minted_credential_carries_no_secret_value():
    from dataclasses import fields

    cred = _credential()
    assert not hasattr(cred, "value")
    assert "value" not in {f.name for f in fields(cred)}


# ---------------------------------------------------------------------------
# G-3.1 — change-opener seam: the lifecycle ends at "PR opened" (a ChangeRef).
# The audited run's in-manifest work crosses the runner seam as DATA
# (RunChangeSet pointers); after collect the orchestrator opens the change
# plan-by-default through a FAKE GhRunner and attests the value-free ChangeRef
# as the terminal "change-opened" step. Zero-live: the fake runner is the sole
# transport (subprocess/socket monkeypatched to explode).
# ---------------------------------------------------------------------------
_RUN_CHANGE_SET = RunChangeSet(
    branch="ce/run-1",
    base="main",
    manifest_paths=(
        "validators/creator_engine_validator/orchestrator.py",
        "validators/tests/unit/test_orchestrator.py",
    ),
    head_sha="d" * 40,
)


class _ChangeSetBackend(RunnerBackend):
    """Fake backend whose run() reports a deterministic change-set (the agent's work as DATA)."""

    backend_key = "changeset"

    def __init__(self) -> None:
        self._inner = LocalNoopBackend()
        self.calls: list[str] = []

    def provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        self.calls.append("provision")
        return self._inner.provision(request)

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        self.calls.append("run")
        return RunResult(
            exit_code=0,
            stdout="noop",
            stderr="",
            started_ref=handle.ref,
            change_set=_RUN_CHANGE_SET,
        )

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        self.calls.append("collect")
        return self._inner.collect(handle)

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        self.calls.append("teardown")
        return self._inner.teardown(handle)


def _fake_gh_runner(argv, input_text=None):
    # A canned empty open-PR list -> no existing PR -> plan-by-default ChangeRef(changed=True).
    return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout="[]", stderr="")


def test_run_plan_opens_change_on_completion(monkeypatch):
    # The lifecycle ends at "PR opened": after collect, run_plan consults the injected
    # change_opener with the run's change-set + the 64-hex plan_ref (the policy_sha), opens
    # the change plan-by-default through the FAKE GhRunner, and attests the value-free
    # ChangeRef as the terminal "change-opened" step. The fake runner is the SOLE transport.
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("open_change must use the injected fake gh_runner, not a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)

    opener_calls: list[tuple] = []
    refs: list = []

    # The production change_opener captures the repo + a gh_runner FACTORY (credential
    # value-injection is G-3.4) and calls forge.open_change(..., apply=False); run_plan
    # only ever sees the ChangeOpener callable.
    def gh_runner_factory():
        return _fake_gh_runner

    def change_opener(change_set, plan_ref):
        opener_calls.append((change_set, plan_ref))
        ref = open_change(
            "creator-engine/creator-engine",
            change_set.branch,
            change_set.base,
            change_set.manifest_paths,
            plan_ref,
            apply=False,
            gh_runner=gh_runner_factory(),
        )
        refs.append(ref)
        return ref

    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=_ChangeSetBackend(), clock=CounterClock(), change_opener=change_opener,
    )

    # The opener was consulted once, with the run's change-set + the policy_sha as plan_ref.
    assert len(opener_calls) == 1
    consulted_change_set, consulted_plan_ref = opener_calls[0]
    assert consulted_change_set.branch == "ce/run-1"
    assert consulted_change_set.manifest_paths == _RUN_CHANGE_SET.manifest_paths
    assert consulted_plan_ref == _POLICY_SHA

    # The returned ChangeRef is value-free (no token) and plan-by-default (no existing PR).
    from dataclasses import fields

    assert len(refs) == 1
    ref = refs[0]
    assert not hasattr(ref, "value")
    assert "value" not in {f.name for f in fields(ref)}
    assert ref.changed is True and ref.applied is False

    # The TERMINAL attested step (AFTER collect) is a TYPED run-outcome record on the
    # SAME hash chain — orthogonal to the container lifecycle axis: it carries no
    # lifecycle_phase, but the plural ``outcome`` + a value-free ``change_set`` pointer.
    lifecycle = list(evidence.records[:-1])
    outcome = evidence.records[-1]
    assert [r["lifecycle_phase"] for r in lifecycle] == ["provision", "run", "collect"]
    assert outcome["kind"] == "runtime-run-outcome"
    assert outcome["record_type"] == "runtime_run_outcome"
    assert outcome["outcome"] == "pr_opened"
    assert "lifecycle_phase" not in outcome  # an outcome is NOT a container phase
    assert outcome["change_set"]["branch"] == "ce/run-1"
    assert outcome["change_set"]["manifest_paths"] == list(_RUN_CHANGE_SET.manifest_paths)
    # The outcome record is chain-linked + policy-bound like every record; chain clean.
    assert verify_chain(list(evidence.records)) == []
    assert all(r["policy_sha"] == _POLICY_SHA for r in evidence.records)
    assert all("value" not in r for r in evidence.records)  # no secret value on the spine

    # The run's change-set is surfaced on the returned evidence (value-free pointers).
    assert evidence.change_set is not None
    assert evidence.change_set.branch == "ce/run-1"


def test_no_change_opener_is_backward_compatible():
    # A run that produces a change-set but with NO change_opener still ends at collect
    # (the seam defaults to None -> the existing G-2.x lifecycle, byte-for-byte unchanged).
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=_ChangeSetBackend(), clock=CounterClock(),
    )
    assert [r["lifecycle_phase"] for r in evidence.records] == ["provision", "run", "collect"]
    assert evidence.change_set is None


def test_change_opener_without_change_set_is_noop():
    # The inert LocalNoopBackend produces no change-set; even with a change_opener injected,
    # run_plan opens nothing (the run authored no in-manifest work) and ends at collect.
    opener_calls: list[tuple] = []

    def change_opener(change_set, plan_ref):
        opener_calls.append((change_set, plan_ref))  # pragma: no cover - must never run
        raise AssertionError("change_opener must not be called when the run produced no change-set")

    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=LocalNoopBackend(), clock=CounterClock(), change_opener=change_opener,
    )
    assert opener_calls == []
    assert [r["lifecycle_phase"] for r in evidence.records] == ["provision", "run", "collect"]
    assert evidence.change_set is None


def test_change_set_carries_no_secret():
    from dataclasses import fields

    cs = RunChangeSet(branch="b", base="main", manifest_paths=("a.py",), head_sha="abc")
    assert not hasattr(cs, "value")
    assert {f.name for f in fields(cs)} == {"branch", "base", "manifest_paths", "head_sha"}
