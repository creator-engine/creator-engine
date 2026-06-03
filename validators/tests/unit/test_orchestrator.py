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
    PlanNotRatified,
    run_plan,
)
from creator_engine_validator.runner import (
    BackendUnavailable,
    CollectedEvidence,
    PolicyRejected,
    ProvisionedHandle,
    ProvisionRequest,
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
