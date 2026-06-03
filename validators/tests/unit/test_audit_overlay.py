"""Unit tests for the v3 G-1.3b classifier + audit overlay.

The classifier is a PURE policy decision point; the overlay is a decorator over
any RunnerBackend that attests each lifecycle step to the merged G-1.3a
hash-chained spine. These tests perform ZERO live subprocess and write nothing
to disk, and confirm the overlay registers no validator check and no backend
(``--list-checks`` and ``available_backends()`` unchanged).
"""

import socket
import subprocess

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.runner import available_backends, get_backend
from creator_engine_validator.runner.audit_overlay import (
    ALLOWED,
    AuditOverlayBackend,
    CounterClock,
    DENIED,
    ESCALATE,
    EgressEvent,
    LifecycleEvent,
    MountEvent,
    SecretEvent,
    classify,
)
from creator_engine_validator.runner.backend import (
    CollectedEvidence,
    ProvisionRequest,
    RunRequest,
)
from creator_engine_validator.runner.noop_backend import LocalNoopBackend
from creator_engine_validator.runtime_evidence_spine import RECORD_KIND, verify_chain

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy() -> dict:
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "gvisor-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": "gvisor-proxy",
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


def _overlay() -> AuditOverlayBackend:
    return AuditOverlayBackend(LocalNoopBackend(), clock=CounterClock())


# ---------------------------------------------------------------------------
# Classifier — the pure policy decision point
# ---------------------------------------------------------------------------
def test_classify_lifecycle_allowed():
    assert classify(LifecycleEvent("provision"), valid_policy()) == ALLOWED


def test_classify_egress_allowed_and_denied():
    policy = valid_policy()
    assert classify(EgressEvent("model-provider.example", 443), policy) == ALLOWED
    assert classify(EgressEvent("evil.example", 443), policy) == DENIED


def test_classify_egress_empty_allowlist_denies_all():
    policy = valid_policy()
    policy["egress_allowlist"] = []
    assert classify(EgressEvent("anything.example"), policy) == DENIED


def test_classify_mount_allowed_denied_escalate():
    policy = valid_policy()
    assert classify(MountEvent("governance", "ro"), policy) == ALLOWED
    assert classify(MountEvent("/runtime/worktree", "rw"), policy) == ALLOWED
    assert classify(MountEvent("/not/in/manifest", "ro"), policy) == DENIED
    assert classify(MountEvent("governance", "rw"), policy) == ESCALATE  # rw on a ro-granted mount


def test_classify_secret_allowed_and_denied():
    policy = valid_policy()
    assert classify(SecretEvent("model-provider-key"), policy) == ALLOWED
    assert classify(SecretEvent("unknown-key"), policy) == DENIED


def test_classify_unknown_event_and_bad_policy_escalate():
    assert classify(object(), valid_policy()) == ESCALATE
    assert classify(LifecycleEvent("run"), None) == ESCALATE


def test_classify_returns_only_valid_verdicts():
    from creator_engine_validator.runtime_evidence_spine import CLASSIFICATIONS

    for verdict in (ALLOWED, DENIED, ESCALATE):
        assert verdict in CLASSIFICATIONS


# ---------------------------------------------------------------------------
# Overlay — decorator over a RunnerBackend
# ---------------------------------------------------------------------------
def test_overlay_lifecycle_emits_clean_verifiable_chain():
    overlay = _overlay()
    handle = overlay.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    overlay.run(handle, RunRequest(command=("echo", "hi")))
    evidence = overlay.collect(handle)
    overlay.teardown(handle)

    chain = list(overlay.chain(handle))
    assert [r["lifecycle_phase"] for r in chain] == ["provision", "run", "collect", "teardown"]
    assert verify_chain(chain) == []  # content-addressed + hash-chained, clean
    assert all(r["policy_sha"] == _POLICY_SHA for r in chain)
    assert all(r["kind"] == RECORD_KIND and r["classification"] == ALLOWED for r in chain)
    # collect() folded the spine-at-collect-time (provision, run, collect) into evidence.
    assert isinstance(evidence, CollectedEvidence)
    assert [r["lifecycle_phase"] for r in evidence.records] == ["provision", "run", "collect"]


def test_overlay_observe_classifies_and_attests():
    overlay = _overlay()
    handle = overlay.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    allowed = overlay.observe(handle, EgressEvent("model-provider.example", 443))
    denied = overlay.observe(handle, EgressEvent("evil.example", 443))
    escalate = overlay.observe(handle, MountEvent("governance", "rw"))
    assert allowed["classification"] == ALLOWED
    assert denied["classification"] == DENIED
    assert escalate["classification"] == ESCALATE
    assert verify_chain(list(overlay.chain(handle))) == []  # chain stays intact across mixed verdicts


def test_overlay_binds_each_record_to_policy_sha():
    overlay = _overlay()
    handle = overlay.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    overlay.observe(handle, SecretEvent("model-provider-key"))
    assert all(r["policy_sha"] == handle.policy_sha == _POLICY_SHA for r in overlay.chain(handle))


def test_overlay_registers_no_check_and_no_backend():
    AuditOverlayBackend(LocalNoopBackend())  # constructing/using registers nothing
    names = set(registered_checks())
    assert not any("audit" in n or "overlay" in n for n in names)
    assert available_backends() == ("gvisor-proxy", "local-noop")  # no isolation_backend added


def test_overlay_leaves_inner_backend_untouched():
    inner = LocalNoopBackend()
    overlay = AuditOverlayBackend(inner)
    assert overlay._inner is inner
    assert isinstance(get_backend("local-noop"), LocalNoopBackend)  # registry unchanged


def test_counter_clock_is_deterministic_and_pure():
    clock = CounterClock()
    assert [clock(), clock(), clock()] == ["t1", "t2", "t3"]


def test_overlay_no_live_subprocess_or_socket(monkeypatch):
    # The overlay (and the inert inner backend) must run a full lifecycle without
    # ever shelling out or opening a socket. (Schema validation reads files via
    # the validator's own loader — a read, not a live runtime call.)
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the audit overlay must not touch a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)

    overlay = _overlay()
    handle = overlay.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    overlay.run(handle, RunRequest(command=("x",)))
    overlay.collect(handle)
    overlay.teardown(handle)
    assert verify_chain(list(overlay.chain(handle))) == []
