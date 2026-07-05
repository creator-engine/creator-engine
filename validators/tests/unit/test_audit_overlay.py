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
    AgentActionEvent,
    AuditOverlayBackend,
    BUILTIN_DENY_CELLS,
    CounterClock,
    DENIED,
    Decision,
    ESCALATE,
    EgressEvent,
    LifecycleEvent,
    MountEvent,
    SecretEvent,
    classify,
    decide,
)
from creator_engine_validator.runner.backend import (
    CollectedEvidence,
    ProvisionRequest,
    RunRequest,
)
from creator_engine_validator.runner.noop_backend import LocalNoopBackend
from creator_engine_validator.runtime_evidence_spine import (
    RECORD_KIND,
    RUNTIME_AGENT_ACTION_RECORD_KIND,
    RUNTIME_AGENT_ACTION_RECORD_TYPE,
    verify_chain,
)

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
    assert available_backends() == ("docker", "gvisor-proxy", "local-noop", "openshell", "os-native")  # +docker; overlay still adds none


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


# ---------------------------------------------------------------------------
# v3 G-4 — AgentActionEvent classifier, the decide() control-point, and the
# per-action emit path
# ---------------------------------------------------------------------------
def action_policy() -> dict:
    """A valid runtime policy carrying the G-4 action allowlist + gate-mode ladder."""
    policy = valid_policy()
    policy["action_class_allowlist"] = [
        {"op": "write", "mutation_class": "docs"},
        {"op": "write", "mutation_class": "code"},
    ]
    policy["gate_mode_ladder"] = {
        "default_mode": "allowlist",
        "cells": [{"op": "write", "mutation_class": "code", "mode": "auto"}],
        "rules": [
            {"effect": "always_deny", "op": "vcs", "mutation_class": "deploy"},
            {"effect": "always_allow", "op": "exec", "mutation_class": "none"},
        ],
    }
    return policy


def test_classify_agent_action_read_is_observe_only():
    assert classify(AgentActionEvent("read", "code"), action_policy()) == ALLOWED


def test_classify_agent_action_faithful_mutation_allowlist():
    policy = action_policy()
    assert classify(AgentActionEvent("write", "docs", fidelity="faithful"), policy) == ALLOWED
    # not on the allowlist -> deny-by-default
    assert classify(AgentActionEvent("write", "schema", fidelity="faithful"), policy) == DENIED


def test_classify_agent_action_non_faithful_mutation_escalates():
    policy = action_policy()
    # even an allowlisted cell escalates when observed below faithful fidelity (Fork-1)
    assert classify(AgentActionEvent("write", "docs", fidelity="best_effort"), policy) == ESCALATE
    assert classify(AgentActionEvent("write", "docs", fidelity="inferred"), policy) == ESCALATE


def test_classify_agent_action_deny_by_default_on_absent_cell():
    # an empty/absent allowlist denies a faithful mutating op (deny-by-default)
    assert classify(AgentActionEvent("write", "docs", fidelity="faithful"), valid_policy()) == DENIED


def test_classify_agent_action_unknown_op_escalates():
    assert classify(AgentActionEvent("frobnicate", "docs"), action_policy()) == ESCALATE


def test_classify_agent_action_is_pure(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("classify must not touch a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    assert classify(AgentActionEvent("write", "docs"), action_policy()) in (ALLOWED, DENIED, ESCALATE)


def test_decide_allowlist_mode_tracks_base_verdict():
    policy = action_policy()
    d = decide(AgentActionEvent("write", "docs", fidelity="faithful"), policy)
    assert isinstance(d, Decision)
    assert (d.verdict, d.mode, d.remember) == (ALLOWED, "allowlist", "none")
    assert d.escalation_id is None
    # an escalate verdict carries a deterministic escalation_id
    esc = decide(AgentActionEvent("write", "docs", fidelity="best_effort"), valid_policy())
    assert esc.verdict == ESCALATE and esc.escalation_id is not None


def test_decide_auto_is_advisory_only():
    policy = action_policy()  # write/code cell is mode=auto
    # base ESCALATE (best_effort) -> auto may downgrade to allow
    assert decide(AgentActionEvent("write", "code", fidelity="best_effort"), policy).verdict == ALLOWED
    # base DENIED -> auto NEVER authorizes a deny-class action
    nolist = valid_policy()
    nolist["gate_mode_ladder"] = {"default_mode": "auto"}
    assert decide(AgentActionEvent("write", "schema", fidelity="faithful"), nolist).verdict == DENIED


def test_decide_zed_precedence_deny_beats_allow():
    policy = valid_policy()
    policy["gate_mode_ladder"] = {
        "default_mode": "full",
        "rules": [
            {"effect": "always_allow", "op": "write", "mutation_class": "code"},
            {"effect": "always_deny", "op": "write", "mutation_class": "code"},
        ],
    }
    assert decide(AgentActionEvent("write", "code", fidelity="faithful"), policy).verdict == DENIED


def test_decide_builtin_deny_survives_full():
    policy = valid_policy()
    policy["gate_mode_ladder"] = {"default_mode": "full"}
    for op, mutation_class in BUILTIN_DENY_CELLS:
        assert decide(AgentActionEvent(op, mutation_class), policy).verdict == DENIED
    # full otherwise allows
    assert decide(AgentActionEvent("write", "docs"), policy).verdict == ALLOWED


def test_decide_always_deny_rule_fires():
    policy = action_policy()  # has an always_deny vcs/deploy rule
    assert decide(AgentActionEvent("vcs", "deploy"), policy).verdict == DENIED


def test_decide_is_deterministic_and_pure(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("decide must not touch a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    policy = action_policy()
    event = AgentActionEvent("write", "docs", target="docs/x.md", tool="Edit")
    first = decide(event, policy)
    second = decide(event, policy)
    assert first == second  # same input -> identical Decision


def test_observe_action_appends_runtime_agent_action_record():
    overlay = _overlay()
    handle = overlay.provision(ProvisionRequest(runtime_policy=action_policy(), run_id="run-1"))
    rec = overlay.observe_action(
        handle, AgentActionEvent("write", "docs", target="docs/x.md", tool="Edit", fidelity="faithful")
    )
    assert rec["kind"] == RUNTIME_AGENT_ACTION_RECORD_KIND
    assert rec["record_type"] == RUNTIME_AGENT_ACTION_RECORD_TYPE
    assert (rec["op"], rec["mutation_class"], rec["fidelity"]) == ("write", "docs", "faithful")
    assert rec["classification"] == ALLOWED
    assert rec["policy_sha"] == _POLICY_SHA
    # the chain stays clean across lifecycle + action records
    assert verify_chain(list(overlay.chain(handle))) == []


def test_observe_action_records_escalation_id_on_escalate():
    overlay = _overlay()
    handle = overlay.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    rec = overlay.observe_action(handle, AgentActionEvent("write", "docs", fidelity="best_effort"))
    assert rec["classification"] == ESCALATE
    assert "escalation_id" in rec and len(rec["escalation_id"]) == 64
    assert verify_chain(list(overlay.chain(handle))) == []
