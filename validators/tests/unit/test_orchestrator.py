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
from pathlib import Path
from types import SimpleNamespace

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.evidence_sink import EvidencePersistRefused
from creator_engine_validator.orchestrator import (
    ApprovedPlan,
    CredentialNotPermitted,
    MintedCredential,
    PlanNotRatified,
    RatificationBindingRefused,
    merge_change,
    run_plan,
)
from creator_engine_validator.forge import open_change
from creator_engine_validator.runner import (
    BackendUnavailable,
    CollectedEvidence,
    OsNativeCapability,
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
from creator_engine_validator.runtime_evidence_spine import compute_binding_ref, verify_chain

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

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
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
    # A genuinely-unregistered selector keeps the UnknownBackend teeth live.
    # (``openshell`` is now registered as of v3.5-A.2a, so it is no longer the
    # negative case — the positive resolution is asserted below.)
    with pytest.raises(UnknownBackend):
        run_plan(valid_policy("no-such-backend"), "run-1", ("echo", "hi"), approved())


def test_omitted_isolation_backend_resolves_default_not_keyerror(monkeypatch):
    # ce-ops#71 round 2 REGRESSION: round-1 dropped ``isolation_backend`` from the
    # schema ``required`` set (back-compat) and the validator does NOT materialize the
    # schema default — so a clean policy may OMIT the field. ``run_plan`` must resolve
    # the fail-closed default (``gvisor-proxy``) through ``resolve_isolation_backend``
    # instead of ``KeyError``-ing on the old raw ``runtime_policy["isolation_backend"]``
    # index. (A present-but-unregistered key still raises ``UnknownBackend``, above.)
    captured: dict[str, str] = {}

    def fake_get_backend(key: str):
        captured["key"] = key
        return _SpyBackend()

    monkeypatch.setattr("creator_engine_validator.orchestrator.get_backend", fake_get_backend)
    policy = valid_policy()
    del policy["isolation_backend"]
    evidence = run_plan(policy, "run-1", ("echo", "hi"), approved())
    assert captured["key"] == "gvisor-proxy"  # the fail-closed default, not a KeyError
    assert isinstance(evidence, CollectedEvidence)


def test_openshell_isolation_backend_resolves_then_refuses_unwired():
    # ``openshell`` is registered (v3.5-A.2a): run_plan resolves it by the policy
    # selector with ZERO orchestrator changes, then the default (unwired) client
    # refuses at provision with ``BackendUnavailable`` — proving the registry path
    # works end-to-end without a live OpenShell gateway (the live run is A.2b).
    with pytest.raises(BackendUnavailable):
        run_plan(valid_policy("openshell"), "run-1", ("echo", "hi"), approved())


def test_gvisor_backend_unavailable_raises_backend_unavailable(monkeypatch):
    # ``gvisor-proxy`` is registered but availability-gated. Monkeypatch the runsc
    # discovery probe to deterministic absence so the refusal CONTRACT is asserted
    # on EVERY host (runsc installed or not) — no per-host tolerated failure, and
    # still no live subprocess spawned.
    from creator_engine_validator.runner import gvisor_proxy_backend

    monkeypatch.setattr(gvisor_proxy_backend.shutil, "which", lambda _binary: None)
    with pytest.raises(BackendUnavailable):
        run_plan(valid_policy("gvisor-proxy"), "run-1", ("echo", "hi"), approved())


def test_os_native_selected_then_fails_closed_without_required_primitives(monkeypatch):
    from creator_engine_validator.runner import os_native_backend

    monkeypatch.setattr(
        os_native_backend,
        "probe_os_native_capability",
        lambda: OsNativeCapability(
            platform_name="Linux",
            bwrap_path=None,
            landlock_abi=None,
            seccomp_available=True,
            proxy_path="/usr/bin/proxy",
            missing=("bwrap", "landlock"),
        ),
    )

    policy = valid_policy("os-native")
    policy["egress_allowlist"] = []
    with pytest.raises(BackendUnavailable) as exc:
        run_plan(policy, "run-1", ("echo", "hi"), approved())
    message = str(exc.value)
    assert "required Linux primitives" in message
    assert "missing: bwrap, landlock" in message
    assert "gvisor-proxy" in message  # only named as a forbidden silent fallback


def test_os_native_selected_with_primitives_available_still_fails_closed_without_contract(monkeypatch):
    from creator_engine_validator.runner import os_native_backend

    monkeypatch.setattr(
        os_native_backend,
        "probe_os_native_capability",
        lambda: OsNativeCapability(
            platform_name="Linux",
            bwrap_path="/usr/bin/bwrap",
            landlock_abi=4,
            seccomp_available=True,
            proxy_path="/usr/bin/proxy",
            missing=(),
        ),
    )

    policy = valid_policy("os-native")
    policy["egress_allowlist"] = []
    with pytest.raises(BackendUnavailable) as exc:
        run_plan(policy, "run-1", ("echo", "hi"), approved())
    message = str(exc.value)
    assert "capability probe passed" in message
    assert "no concrete deny-by-default host-proxy enforcement contract" in message
    assert "restrictive seccomp policy" in message


def test_gvisor_subprocess_runner_available_when_registered_runtime_present(monkeypatch, tmp_path):
    # Hermetic positive branch of the same discovery seam: Docker on PATH is not
    # enough. The required DGX runsc runtime must also be registered.
    from creator_engine_validator.runner.gvisor_proxy_backend import (
        SubprocessContainerRunner,
    )

    stub = tmp_path / "docker"
    stub.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setattr(
        "subprocess.run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"runc": {"path": "runc"}, "runsc-gvproxy-ptrace": {"path": "runsc"}}',
            stderr="",
        ),
    )

    runner = SubprocessContainerRunner(binary=str(stub))

    assert runner.available() is True


# ---------------------------------------------------------------------------
# Invariants — registers no check / no backend; zero live surface
# ---------------------------------------------------------------------------
def test_orchestrator_registers_no_check_and_no_backend():
    import creator_engine_validator.orchestrator  # noqa: F401  (import = the side-effect surface)

    assert not any("orchestrat" in n for n in registered_checks())
    assert available_backends() == ("docker", "gvisor-proxy", "local-noop", "openshell", "os-native")  # +docker; orchestrator still adds none


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

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
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


# ---------------------------------------------------------------------------
# G-3.6b — the run_plan(evidence_sink=...) seam: an injected sink persists the
# run's FINAL evidence (with the terminal run-outcome record) AFTER teardown, on
# the success path; the default None persists nothing; a sink's refusal
# propagates (non-conforming evidence is surfaced, not swallowed). The sink is
# the lone persistence seam — run_plan stays pure (default None = no I/O).
# ---------------------------------------------------------------------------
def test_run_plan_persists_final_evidence_via_injected_sink(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("zero live transport")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)

    def change_opener(change_set, plan_ref):
        return open_change(
            "creator-engine/creator-engine", change_set.branch, change_set.base,
            change_set.manifest_paths, plan_ref, apply=False, gh_runner=_fake_gh_runner,
        )

    backend = _ChangeSetBackend()
    persisted: list = []
    calls_at_sink: list = []

    def sink(evidence):
        calls_at_sink.append(list(backend.calls))
        persisted.append(evidence)

    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=backend, clock=CounterClock(), change_opener=change_opener, evidence_sink=sink,
    )
    # The sink received EXACTLY the returned evidence — the FINAL chain with the outcome record.
    assert len(persisted) == 1
    assert persisted[0] is evidence
    assert persisted[0].records[-1]["record_type"] == "runtime_run_outcome"
    # ...and it ran AFTER teardown (the runtime is released before the run's evidence persists).
    assert "teardown" in calls_at_sink[0]


def test_run_plan_without_sink_does_no_io(monkeypatch):
    # The default evidence_sink=None persists nothing — no filesystem write is even attempted.
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("no sink -> no write / no live transport")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(Path, "write_text", explode)

    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),
        backend=_ChangeSetBackend(), clock=CounterClock(),
    )
    assert [r["lifecycle_phase"] for r in evidence.records] == ["provision", "run", "collect"]


def test_run_plan_evidence_sink_refusal_propagates(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("zero live transport")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)

    backend = _ChangeSetBackend()

    def refusing_sink(evidence):
        raise EvidencePersistRefused("non-conforming evidence")

    with pytest.raises(EvidencePersistRefused):
        run_plan(
            valid_policy(), "run-1", ("echo", "hi"), approved(),
            backend=backend, clock=CounterClock(), evidence_sink=refusing_sink,
        )
    # teardown still ran — the runtime is released even when persistence refuses.
    assert "teardown" in backend.calls


# ---------------------------------------------------------------------------
# G-3.7.2b — the runtime head-SHA assertion gate (refuse BEFORE the change-open;
# append the ratification record; INERT for the existing unbound ApprovedPlan).
# ---------------------------------------------------------------------------
_REPO = "creator-engine/creator-engine"
_INSTALL = 42
_PERMS = {"contents": "read", "pull_requests": "write"}
_RATIFIED_HEAD = "d" * 40  # == _RUN_CHANGE_SET.head_sha (the produced change head)


def _binding_inputs() -> dict:
    return {"repo": _REPO, "installation_id": _INSTALL, "permissions": dict(_PERMS)}


def approved_bound(
    *, head: str = _RATIFIED_HEAD, binding_ref: str | None = None,
    approver_ref: str = "2" * 64, prompt_sha: str = "3" * 64,
) -> ApprovedPlan:
    bref = binding_ref if binding_ref is not None else compute_binding_ref(_REPO, _INSTALL, _PERMS, head)
    return ApprovedPlan(
        run_id="run-1", policy_sha=_POLICY_SHA, approved_by="operator", approval_ref="forge-issue#42",
        ratified_head_sha=head, binding_ref=bref, approver_ref=approver_ref, ratified_prompt_sha=prompt_sha,
    )


def _recording_opener(calls: list):
    def change_opener(change_set, plan_ref):
        calls.append((change_set, plan_ref))
        return open_change(
            _REPO, change_set.branch, change_set.base, change_set.manifest_paths,
            plan_ref, apply=False, gh_runner=_fake_gh_runner,
        )
    return change_opener


def test_head_sha_drift_refuses_before_change_open(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    opener_calls: list = []
    # ratified head "e"*40 != the produced change head "d"*40; binding_ref matches the ratified head.
    plan = approved_bound(head="e" * 40)
    with pytest.raises(RatificationBindingRefused):
        run_plan(
            valid_policy(), "run-1", ("echo", "hi"), plan,
            backend=_ChangeSetBackend(), clock=CounterClock(),
            change_opener=_recording_opener(opener_calls), binding_inputs=_binding_inputs(),
        )
    assert opener_calls == []  # refused BEFORE the change-open side effect


def test_binding_ref_mismatch_refuses(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    opener_calls: list = []
    # head matches the produced change, but the binding_ref is wrong (tuple drift).
    plan = approved_bound(head=_RATIFIED_HEAD, binding_ref="f" * 64)
    with pytest.raises(RatificationBindingRefused):
        run_plan(
            valid_policy(), "run-1", ("echo", "hi"), plan,
            backend=_ChangeSetBackend(), clock=CounterClock(),
            change_opener=_recording_opener(opener_calls), binding_inputs=_binding_inputs(),
        )
    assert opener_calls == []


def test_engaged_matching_appends_ratification_record(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    opener_calls: list = []
    plan = approved_bound()  # head + binding_ref both match
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), plan,
        backend=_ChangeSetBackend(), clock=CounterClock(),
        change_opener=_recording_opener(opener_calls), binding_inputs=_binding_inputs(),
    )
    assert len(opener_calls) == 1  # gate passed -> the change WAS opened
    rats = [r for r in evidence.records if r["record_type"] == "runtime_ratification"]
    assert len(rats) == 1
    rec = rats[0]
    assert rec["ratified_head_sha"] == _RATIFIED_HEAD
    assert rec["approver_ref"] == "2" * 64 and rec["ratified_prompt_sha"] == "3" * 64
    assert rec["binding_ref"] == compute_binding_ref(_REPO, _INSTALL, _PERMS, _RATIFIED_HEAD)
    assert rec["policy_sha"] == _POLICY_SHA and "lifecycle_phase" not in rec
    assert "operator" not in repr(rec)  # value-free: the raw ratifier never lands in the record
    # chain still clean + still carries the run-outcome record.
    assert verify_chain(list(evidence.records)) == []
    assert any(r["record_type"] == "runtime_run_outcome" for r in evidence.records)


def test_inert_when_unbound_appends_no_ratification_record(monkeypatch):
    # The existing unbound ApprovedPlan (no ratified_head_sha) => gate inert: no assertion,
    # no ratification record, the chain is the pre-3.7.2b run-outcome shape.
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    opener_calls: list = []
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), approved(),  # unbound
        backend=_ChangeSetBackend(), clock=CounterClock(),
        change_opener=_recording_opener(opener_calls), binding_inputs=_binding_inputs(),
    )
    assert len(opener_calls) == 1
    assert not any(r["record_type"] == "runtime_ratification" for r in evidence.records)
    assert evidence.records[-1]["record_type"] == "runtime_run_outcome"


def test_compute_binding_ref_deterministic_and_order_independent():
    a = compute_binding_ref(_REPO, _INSTALL, {"contents": "read", "pull_requests": "write"}, _RATIFIED_HEAD)
    b = compute_binding_ref(_REPO, _INSTALL, {"pull_requests": "write", "contents": "read"}, _RATIFIED_HEAD)
    assert a == b  # permission order-independent
    assert len(a) == 64 and all(c in "0123456789abcdef" for c in a)
    assert a != compute_binding_ref(_REPO, _INSTALL, _PERMS, "e" * 40)  # head differs
    assert a != compute_binding_ref(_REPO, 99, _PERMS, _RATIFIED_HEAD)  # installation differs


# ---------------------------------------------------------------------------
# G-3.7.3a — the observed-base-head assertion. When run_assembly supplies a LIVE
# observed head (live mode), the gate binds the INDEPENDENTLY-OBSERVED repo head
# too — refusing BEFORE the change-open if it drifted from the ratified head, even
# when the agent-claimed change head matches (closing the agent-trust/TOCTOU gap).
# Absent observed_head_sha => byte-for-byte the 3.7.2b behavior.
# ---------------------------------------------------------------------------
def _binding_inputs_observed(observed: str) -> dict:
    bi = _binding_inputs()
    bi["observed_head_sha"] = observed
    return bi


def test_observed_head_drift_refuses_before_change_open(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    opener_calls: list = []
    # The agent-claimed change head MATCHES the ratified head ("d"*40), but the
    # independently-observed live head ("e"*40) does NOT -> refuse before any apply.
    plan = approved_bound(head=_RATIFIED_HEAD)
    with pytest.raises(RatificationBindingRefused):
        run_plan(
            valid_policy(), "run-1", ("echo", "hi"), plan,
            backend=_ChangeSetBackend(), clock=CounterClock(),
            change_opener=_recording_opener(opener_calls),
            binding_inputs=_binding_inputs_observed("e" * 40),
        )
    assert opener_calls == []  # refused BEFORE the change-open side effect


def test_observed_head_match_proceeds_and_appends_ratification(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    opener_calls: list = []
    plan = approved_bound(head=_RATIFIED_HEAD)
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), plan,
        backend=_ChangeSetBackend(), clock=CounterClock(),
        change_opener=_recording_opener(opener_calls),
        binding_inputs=_binding_inputs_observed(_RATIFIED_HEAD),  # observed == ratified
    )
    assert len(opener_calls) == 1  # observed head matches -> the change WAS opened
    rats = [r for r in evidence.records if r["record_type"] == "runtime_ratification"]
    assert len(rats) == 1 and rats[0]["ratified_head_sha"] == _RATIFIED_HEAD
    assert verify_chain(list(evidence.records)) == []


def test_observed_head_absent_is_unchanged_3_7_2b_behavior(monkeypatch):
    # No observed_head_sha key => ONLY the agent-claimed head + binding_ref checks run (the
    # 3.7.2b path), byte-for-byte. The change opens; the ratification record still appends.
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no live")))
    opener_calls: list = []
    plan = approved_bound(head=_RATIFIED_HEAD)
    evidence = run_plan(
        valid_policy(), "run-1", ("echo", "hi"), plan,
        backend=_ChangeSetBackend(), clock=CounterClock(),
        change_opener=_recording_opener(opener_calls),
        binding_inputs=_binding_inputs(),  # NO observed_head_sha
    )
    assert len(opener_calls) == 1
    assert any(r["record_type"] == "runtime_ratification" for r in evidence.records)


# ---------------------------------------------------------------------------
# G-3.7b.1 — the merge-driving producer: merge_change drives a gated merge of an
# ALREADY-OPEN, reviewed PR (a disposition distinct from an agent run) through an
# injected forge-free change_merger (the production closure wraps forge.merge), and
# on an ACTUAL merge attests a typed pr_merged run-outcome on the SAME hash chain.
# Forge-free: the change_merger is injected; the orchestrator imports zero forge at
# runtime. An ineligible / non-mutating (plan-mode would_merge) merge attests NOTHING.
# ---------------------------------------------------------------------------
def _pr_opened_prior(run_id: str = "run-1"):
    """A realistic prior chain from the open drive (ends at a pr_opened outcome + change_set)."""
    return run_plan(
        valid_policy(), run_id, ("echo", "hi"), approved(run_id),
        backend=_ChangeSetBackend(), clock=CounterClock(),
        change_opener=lambda change_set, plan_ref: SimpleNamespace(pr_number=43),
    )


def test_merge_change_attests_pr_merged_on_actual_merge():
    prior = _pr_opened_prior()
    assert prior.records[-1]["outcome"] == "pr_opened"  # the open-drive terminal
    merger_calls: list = []
    # An ACTUAL merge (apply path): merged=True + the value-free gate snapshot.
    result = SimpleNamespace(
        merged=True, would_merge=True, eligible=True,
        pr_number=43, head_sha="d" * 40, merge_commit_sha="f" * 40,
    )

    def change_merger():
        merger_calls.append(1)
        return result

    evidence = merge_change(
        prior, run_id="run-1", policy_sha=_POLICY_SHA, change_merger=change_merger,
        clock=CounterClock(),
    )
    assert len(merger_calls) == 1
    # The TERMINAL record is a TYPED pr_merged run-outcome on the disposition axis (no phase).
    outcome = evidence.records[-1]
    assert outcome["kind"] == "runtime-run-outcome"
    assert outcome["record_type"] == "runtime_run_outcome"
    assert outcome["outcome"] == "pr_merged"
    assert "lifecycle_phase" not in outcome  # an outcome is NOT a container phase
    # The pr_merged record carries the SAME value-free change_set pointer shape as pr_opened
    # (branch / base / manifest_paths / head_sha / pr_number) — NO merge_commit_sha slot
    # (no schema bump in this slice; the commit sha lives only on the returned MergeResult).
    assert outcome["change_set"]["branch"] == "ce/run-1"
    assert outcome["change_set"]["pr_number"] == 43
    assert "merge_commit_sha" not in outcome
    assert "merge_commit_sha" not in outcome["change_set"]
    # Appended onto the SAME chain (open -> merged): exactly one pr_merged, prior tail preserved.
    outcomes = [r.get("outcome") for r in evidence.records]
    assert outcomes.count("pr_merged") == 1
    assert evidence.records[-2]["outcome"] == "pr_opened"
    # Chain-linked + policy-bound + value-free; verifies clean.
    assert verify_chain(list(evidence.records)) == []
    assert all(r["policy_sha"] == _POLICY_SHA for r in evidence.records)
    assert all("value" not in r for r in evidence.records)


def test_merge_change_ineligible_attests_no_pr_merged():
    # A gate-ineligible merge (the change_merger reports not merged / not would-merge) attests
    # NOTHING — the gate is load-bearing: no pr_merged record, the chain is unchanged.
    prior = _pr_opened_prior()
    result = SimpleNamespace(
        merged=False, would_merge=False, eligible=False, pr_number=43, head_sha="d" * 40,
    )
    evidence = merge_change(
        prior, run_id="run-1", policy_sha=_POLICY_SHA, change_merger=lambda: result,
    )
    assert all(r.get("outcome") != "pr_merged" for r in evidence.records)
    assert evidence.records[-1]["outcome"] == "pr_opened"
    assert verify_chain(list(evidence.records)) == []


def test_merge_change_plan_mode_would_merge_attests_no_pr_merged():
    # A NON-mutating plan-mode preview (would_merge True but merged False) attests NOTHING —
    # pr_merged means the PR was ACTUALLY merged, never a dry-run preview.
    prior = _pr_opened_prior()
    result = SimpleNamespace(
        merged=False, would_merge=True, eligible=True, pr_number=43, head_sha="d" * 40,
    )
    evidence = merge_change(
        prior, run_id="run-1", policy_sha=_POLICY_SHA, change_merger=lambda: result,
    )
    assert all(r.get("outcome") != "pr_merged" for r in evidence.records)
    assert evidence.records[-1]["outcome"] == "pr_opened"


def test_merge_change_persists_only_on_actual_merge():
    # The injected sink fires (once) on an actual merge, and NOT at all when nothing merged.
    prior = _pr_opened_prior()
    written: list = []
    merged_result = SimpleNamespace(merged=True, would_merge=True, pr_number=43, head_sha="d" * 40)
    merge_change(
        prior, run_id="run-1", policy_sha=_POLICY_SHA, change_merger=lambda: merged_result,
        evidence_sink=lambda ev: written.append(ev), clock=CounterClock(),
    )
    assert len(written) == 1 and written[0].records[-1]["outcome"] == "pr_merged"

    written.clear()
    not_merged = SimpleNamespace(merged=False, would_merge=False, pr_number=43, head_sha="d" * 40)
    merge_change(
        prior, run_id="run-1", policy_sha=_POLICY_SHA, change_merger=lambda: not_merged,
        evidence_sink=lambda ev: written.append(ev),
    )
    assert written == []  # nothing merged -> nothing persisted


def test_merge_change_propagates_merger_refusal_without_attesting():
    # If the change_merger raises (e.g. forge.merge(apply=True) raised MergeRefused on an
    # ineligible PR), merge_change does not swallow it and attests NO partial pr_merged record.
    prior = _pr_opened_prior()

    class _Refused(RuntimeError):
        pass

    def change_merger():
        raise _Refused("merge gate not satisfied")

    with pytest.raises(_Refused):
        merge_change(prior, run_id="run-1", policy_sha=_POLICY_SHA, change_merger=change_merger)
