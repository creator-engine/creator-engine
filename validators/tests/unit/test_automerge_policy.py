"""Unit tests for forge.automerge_policy — CEO-mode auto-merge policy engine.

Covers:
- AutoMergePolicyState shipped default (dev mode, all flags false).
- decide_automerge: AUTO requires all guards; GESTURE on any failure.
- Kill-switch halts everything.
- GESTURE classes never auto-merge even when their flag is set.
- Fail-closed: unknown paths, missing checks, CHANGES_REQUESTED.
- Dry-run over representative PR shapes (docs-only green → AUTO in CEO mode;
  privileged paths → GESTURE regardless of mode).
- Schema: default state serializes/deserializes correctly.
"""
from __future__ import annotations

import json
import socket
import subprocess

import pytest

from creator_engine_validator.forge.automerge_policy import (
    AUTOMERGE_DECISION_AUTO,
    AUTOMERGE_DECISION_GESTURE,
    AutoMergeClassPolicy,
    AutoMergePolicyState,
    AutoMergePolicyStateError,
    decide_automerge,
    load_automerge_policy_state,
    save_automerge_policy_state,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ceo_state(
    *,
    mutation_class: str = "docs",
    auto_merge_flag: bool = True,
    kill_switch: bool = False,
    enabling_ref: str | None = "ce-ops#291-enabling-decision",
) -> AutoMergePolicyState:
    """Build a CEO-mode state with one class flag on (for positive tests)."""
    classes = {
        c: AutoMergeClassPolicy(auto_merge=False)
        for c in [
            "none", "docs", "code", "schema", "deploy",
            "governance", "identity", "security", "attestation", "redaction",
        ]
    }
    classes[mutation_class] = AutoMergeClassPolicy(auto_merge=auto_merge_flag)
    return AutoMergePolicyState(
        run_mode="ceo",
        kill_switch=kill_switch,
        classes=classes,
        enabling_decision_ref=enabling_ref,
    )


_DOCS_PATHS = ["README.md", "docs/getting-started.md", "CHANGELOG.md"]
_CODE_PATHS = ["validators/creator_engine_validator/work_sizing.py"]
_SCHEMA_PATHS = ["schemas/work-sizing.schema.yaml"]
_DEPLOY_PATHS = [".github/workflows/ci.yml"]
_GOVERNANCE_PATHS = ["playbooks/controller/briefs/dispatch.md"]
_IDENTITY_PATHS = ["validators/creator_engine_validator/secret_identity.py"]
_SECURITY_PATHS = ["validators/creator_engine_validator/forge/cred_injection_proxy.py"]
_ATTESTATION_PATHS = ["validators/creator_engine_validator/forge/approval_capability.py"]
_REDACTION_PATHS = ["validators/creator_engine_validator/forge/_redact.py"]

_GREEN_CHECKS = {"validate": "success", "test": "success"}
_MIXED_CHECKS = {"validate": "success", "test": "failure"}


# ── Shipped default state ─────────────────────────────────────────────────────

def test_default_state_is_dev_mode():
    state = AutoMergePolicyState.default()
    assert state.run_mode == "dev"


def test_default_state_kill_switch_is_false():
    state = AutoMergePolicyState.default()
    assert state.kill_switch is False


def test_default_state_all_flags_false():
    state = AutoMergePolicyState.default()
    for cls_name, cls_policy in state.classes.items():
        assert cls_policy.auto_merge is False, (
            f"Default state has auto_merge=True for class {cls_name!r} — "
            "all flags must ship as False"
        )


def test_default_state_enabling_decision_ref_is_none():
    state = AutoMergePolicyState.default()
    assert state.enabling_decision_ref is None


def test_default_state_all_known_classes_present():
    state = AutoMergePolicyState.default()
    expected = {
        "none", "docs", "code", "schema", "deploy",
        "governance", "identity", "security", "attestation", "redaction",
    }
    assert set(state.classes.keys()) == expected


# ── State serialization ───────────────────────────────────────────────────────

def test_default_state_round_trips():
    state = AutoMergePolicyState.default()
    payload = state.to_payload()
    restored = AutoMergePolicyState.from_payload(payload)
    assert restored.run_mode == "dev"
    assert restored.kill_switch is False
    assert restored.enabling_decision_ref is None
    for cls_name, cls_policy in restored.classes.items():
        assert cls_policy.auto_merge is False


def test_state_with_ceo_mode_round_trips():
    state = _ceo_state()
    payload = state.to_payload()
    restored = AutoMergePolicyState.from_payload(payload)
    assert restored.run_mode == "ceo"
    assert restored.class_flag("docs") is True
    assert restored.class_flag("code") is False


def test_state_json_serializes_cleanly():
    state = AutoMergePolicyState.default()
    raw = json.dumps(state.to_payload(), sort_keys=True)
    loaded = json.loads(raw)
    assert loaded["run_mode"] == "dev"
    assert loaded["kill_switch"] is False
    assert loaded["enabling_decision_ref"] is None
    for cls_policy in loaded["classes"].values():
        assert cls_policy["auto_merge"] is False


def test_from_payload_rejects_non_bool_kill_switch():
    with pytest.raises(AutoMergePolicyStateError):
        AutoMergePolicyState.from_payload({
            "run_mode": "dev",
            "kill_switch": "no",
            "classes": {},
        })


def test_from_payload_rejects_non_bool_auto_merge():
    with pytest.raises(AutoMergePolicyStateError):
        AutoMergePolicyState.from_payload({
            "run_mode": "dev",
            "kill_switch": False,
            "classes": {"docs": {"auto_merge": "yes"}},
        })


def test_save_and_load_round_trip(tmp_path):
    state = _ceo_state()
    path = tmp_path / ".ce/state/automerge/policy.json"
    save_automerge_policy_state(path, state)
    loaded = load_automerge_policy_state(path)
    assert loaded.run_mode == "ceo"
    assert loaded.class_flag("docs") is True
    assert loaded.kill_switch is False


def test_load_absent_file_returns_default(tmp_path):
    path = tmp_path / "nonexistent.json"
    state = load_automerge_policy_state(path)
    assert state.run_mode == "dev"
    assert state.kill_switch is False


def test_save_is_atomic_write(tmp_path):
    """Save must not leave a partial file on disk (uses tmp+replace)."""
    state = AutoMergePolicyState.default()
    path = tmp_path / "policy.json"
    save_automerge_policy_state(path, state)
    # tmp file must be gone
    tmp = path.with_name(f".{path.name}.tmp")
    assert not tmp.exists()
    assert path.exists()


# ── decide_automerge: GESTURE_REQUIRED (default / dev mode) ──────────────────

def test_dev_mode_always_gesture_for_docs():
    """Dev mode → GESTURE even for docs paths with green checks."""
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=AutoMergePolicyState.default(),
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.run_mode == "dev"
    assert any("CEO mode" in r for r in decision.rationale)


def test_none_policy_state_is_dev_mode_gesture():
    """None policy_state → shipped default → GESTURE_REQUIRED."""
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=None,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE


def test_kill_switch_halts_everything():
    """kill_switch=True → GESTURE regardless of class or run_mode."""
    state = _ceo_state(kill_switch=True)
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert any("kill_switch" in r for r in decision.rationale)


def test_class_flag_false_blocks_auto():
    """CEO mode but class flag=False → GESTURE."""
    state = _ceo_state(auto_merge_flag=False)
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert any("class_flag" in r for r in decision.rationale)


def test_no_enabling_decision_ref_blocks_auto():
    """CEO mode, flag on, but enabling_decision_ref=None → GESTURE."""
    state = _ceo_state(enabling_ref=None)
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert any("enabling_decision_ref" in r for r in decision.rationale)


def test_failing_checks_blocks_auto():
    """CEO mode + class enabled but failing checks → GESTURE."""
    state = _ceo_state()
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_MIXED_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.checks_green is False


def test_none_checks_blocks_auto():
    """No checks provided → fail-closed → GESTURE."""
    state = _ceo_state()
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=None,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.checks_green is False


def test_changes_requested_blocks_auto():
    """CHANGES_REQUESTED → GESTURE."""
    state = _ceo_state()
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="CHANGES_REQUESTED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.review_decision_blocked is True


def test_split_required_size_band_blocks_auto(tmp_path):
    """size_band=split_required → GESTURE even in CEO mode."""
    from creator_engine_validator.checks.work_sizing_floor import ChangeStat

    # Manufacture >1000 lines to trigger split_required
    big_stats = [
        ChangeStat(path="docs/huge.md", additions=600, deletions=600, binary=False)
    ]
    state = _ceo_state()
    decision = decide_automerge(
        changed_paths=["docs/huge.md"],
        change_stats=big_stats,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.size_band == "split_required"


# ── decide_automerge: AUTO (CEO mode, docs, all guards pass) ─────────────────

def test_ceo_mode_docs_green_auto():
    """CEO mode + docs paths + green checks + APPROVED → AUTO."""
    state = _ceo_state(mutation_class="docs")
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert decision.mutation_class == "docs"
    assert decision.checks_green is True
    assert decision.review_decision_blocked is False


def test_ceo_mode_docs_null_review_decision_auto():
    """CEO mode + docs + green checks + no reviewDecision → AUTO."""
    state = _ceo_state(mutation_class="docs")
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision=None,
    )
    assert decision.decision == AUTOMERGE_DECISION_AUTO


def test_auto_decision_carries_pr_metadata():
    """AUTO decision record should include pr_number and head_sha."""
    state = _ceo_state(mutation_class="docs")
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
        pr_number=291,
        head_sha="abc123" * 6 + "ab",
    )
    assert decision.pr_number == 291
    assert decision.head_sha is not None


def test_auto_decision_to_dict_is_json_serializable():
    """AUTO decision.to_dict() must be JSON-serializable."""
    state = _ceo_state(mutation_class="docs")
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    raw = json.dumps(decision.to_dict(), sort_keys=True)
    loaded = json.loads(raw)
    assert loaded["decision"] == "AUTO"


# ── GESTURE classes NEVER auto-merge even when flag is on ────────────────────

_GESTURE_CLASS_PATHS = {
    "code": _CODE_PATHS,
    "schema": _SCHEMA_PATHS,
    "deploy": _DEPLOY_PATHS,
    "governance": _GOVERNANCE_PATHS,
    "identity": _IDENTITY_PATHS,
    "security": _SECURITY_PATHS,
    "attestation": _ATTESTATION_PATHS,
    "redaction": _REDACTION_PATHS,
}


@pytest.mark.parametrize("mutation_class,paths", list(_GESTURE_CLASS_PATHS.items()))
def test_gesture_class_never_auto_even_when_flag_on(mutation_class, paths):
    """GESTURE classes must never produce AUTO even in CEO mode with flag=True."""
    state = _ceo_state(mutation_class=mutation_class, auto_merge_flag=True)
    decision = decide_automerge(
        changed_paths=paths,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE, (
        f"mutation_class={mutation_class!r} produced AUTO — "
        "GESTURE classes must NEVER auto-merge even with the class flag on!"
    )


def test_privileged_path_among_docs_forces_gesture():
    """A single privileged path mixed with docs paths → GESTURE."""
    # This is the zero-false-AUTO-on-privileged-paths requirement.
    paths = _DOCS_PATHS + _ATTESTATION_PATHS
    state = _ceo_state(mutation_class="docs")  # docs flag on, but attestation path present
    decision = decide_automerge(
        changed_paths=paths,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE, (
        "A privileged path among docs should escalate to GESTURE — zero-false-AUTO violated!"
    )
    assert decision.mutation_class == "attestation"


def test_github_workflow_among_docs_forces_gesture():
    """.github/workflows/ path mixed with docs → GESTURE (deploy class)."""
    paths = _DOCS_PATHS + _DEPLOY_PATHS
    state = _ceo_state(mutation_class="docs")
    decision = decide_automerge(
        changed_paths=paths,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.mutation_class == "deploy"


def test_schema_among_docs_forces_gesture():
    """A schema file among docs → GESTURE."""
    paths = _DOCS_PATHS + _SCHEMA_PATHS
    state = _ceo_state(mutation_class="docs")
    decision = decide_automerge(
        changed_paths=paths,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.mutation_class == "schema"


# ── Dry-run over example PR shapes ───────────────────────────────────────────

@pytest.mark.parametrize("scenario,changed_paths,expected_decision,expected_mutation_class", [
    # Docs-only: README + changelog → AUTO in CEO mode
    (
        "docs_only_green",
        ["README.md", "CHANGELOG.md", "docs/guide.md"],
        AUTOMERGE_DECISION_AUTO,
        "docs",
    ),
    # Code PR: source change → GESTURE
    (
        "code_pr",
        ["validators/creator_engine_validator/work_sizing.py", "README.md"],
        AUTOMERGE_DECISION_GESTURE,
        "code",
    ),
    # Schema PR → GESTURE
    (
        "schema_pr",
        ["schemas/automerge-policy.schema.yaml"],
        AUTOMERGE_DECISION_GESTURE,
        "schema",
    ),
    # Deploy PR (.github/workflows) → GESTURE
    (
        "deploy_pr",
        [".github/workflows/ci.yml", "README.md"],
        AUTOMERGE_DECISION_GESTURE,
        "deploy",
    ),
    # Governance PR (playbooks/) → GESTURE (privileged)
    (
        "governance_pr",
        ["playbooks/governance/policy.md", "README.md"],
        AUTOMERGE_DECISION_GESTURE,
        "governance",
    ),
    # Identity PR → GESTURE (privileged)
    (
        "identity_pr",
        ["validators/creator_engine_validator/secret_identity.py"],
        AUTOMERGE_DECISION_GESTURE,
        "identity",
    ),
    # Security PR (egress-broker) → GESTURE (privileged)
    (
        "security_pr",
        ["tools/egress-broker/main.py", "docs/guide.md"],
        AUTOMERGE_DECISION_GESTURE,
        "security",
    ),
    # Attestation PR (approval_capability) → GESTURE (privileged)
    (
        "attestation_pr",
        ["validators/creator_engine_validator/forge/approval_capability.py"],
        AUTOMERGE_DECISION_GESTURE,
        "attestation",
    ),
    # Mixed: new classifier + docs → code → GESTURE
    (
        "automerge_classifier_self_pr",
        [
            "validators/creator_engine_validator/forge/mutation_classifier.py",
            "validators/creator_engine_validator/forge/automerge_policy.py",
            "schemas/automerge-policy.schema.yaml",
            "schemas/automerge-decision.schema.yaml",
            "README.md",
        ],
        AUTOMERGE_DECISION_GESTURE,
        "schema",  # schema dominates over code
    ),
])
def test_dryrun_pr_shapes(
    scenario, changed_paths, expected_decision, expected_mutation_class
):
    """Dry-run over representative PR shapes.

    CEO-mode state with docs flag enabled; green checks; APPROVED review.
    Validates zero-false-AUTO on privileged paths.
    """
    state = _ceo_state(mutation_class="docs")  # only docs flag on
    decision = decide_automerge(
        changed_paths=changed_paths,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == expected_decision, (
        f"Scenario {scenario!r}: expected {expected_decision!r}, "
        f"got {decision.decision!r}. Rationale: {decision.rationale}"
    )
    assert decision.mutation_class == expected_mutation_class, (
        f"Scenario {scenario!r}: expected mutation_class={expected_mutation_class!r}, "
        f"got {decision.mutation_class!r}"
    )


def test_zero_false_auto_on_all_privileged_paths():
    """Exhaustive check: no privileged path produces AUTO in any mode."""
    privileged_paths = [
        "validators/creator_engine_validator/forge/approval_capability.py",
        "validators/creator_engine_validator/forge/cred_injection_proxy.py",
        "validators/creator_engine_validator/forge/_redact.py",
        "validators/creator_engine_validator/secret_identity.py",
        "tools/egress-broker/main.py",
        "playbooks/controller/briefs/dispatch.md",
        ".ce/contracts/approval-policy.md",
    ]
    # Even with ALL flags on and CEO mode
    all_on_state = AutoMergePolicyState(
        run_mode="ceo",
        kill_switch=False,
        classes={
            c: AutoMergeClassPolicy(auto_merge=True)
            for c in [
                "none", "docs", "code", "schema", "deploy",
                "governance", "identity", "security", "attestation", "redaction",
            ]
        },
        enabling_decision_ref="hypothetical-ref",
    )
    for path in privileged_paths:
        decision = decide_automerge(
            changed_paths=[path],
            policy_state=all_on_state,
            checks=_GREEN_CHECKS,
            review_decision="APPROVED",
        )
        assert decision.decision == AUTOMERGE_DECISION_GESTURE, (
            f"CRITICAL: Privileged path {path!r} produced AUTO — "
            f"mutation_class={decision.mutation_class!r}, rationale={decision.rationale}"
        )


def test_zero_live_network(monkeypatch):
    """decide_automerge must never touch the network."""
    def explode(*a, **k):  # pragma: no cover
        raise AssertionError("automerge_policy must not perform network I/O")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)

    state = _ceo_state()
    decision = decide_automerge(
        changed_paths=_DOCS_PATHS,
        policy_state=state,
        checks=_GREEN_CHECKS,
        review_decision="APPROVED",
    )
    assert decision.decision == AUTOMERGE_DECISION_AUTO
