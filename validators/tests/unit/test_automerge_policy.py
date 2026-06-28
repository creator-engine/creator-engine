from __future__ import annotations

import json
import socket
import subprocess

import pytest

from creator_engine_validator.checks.work_sizing_floor import ChangeStat
from creator_engine_validator.forge.automerge_policy import (
    AUTOMERGE_DECISION_AUTO,
    AUTOMERGE_DECISION_GESTURE,
    AutoMergeClassPolicy,
    AutoMergePolicyState,
    AutoMergePolicyStateError,
    automerge_policy_state_path,
    decide_automerge,
    emit_automerge_dry_run_decision,
    load_automerge_policy_state,
    save_automerge_policy_state,
)
from creator_engine_validator.work_sizing import size_ceremony


ALL_CLASSES = (
    "none",
    "docs",
    "code",
    "schema",
    "deploy",
    "governance",
    "identity",
    "security",
    "attestation",
    "redaction",
)

GREEN_CHECKS = {
    "validate": "success",
    "unit": "success",
    "reviewDecision": "APPROVED",
}


def state_with_flags(*enabled: str, run_mode: str = "ceo", kill_switch: bool = False) -> AutoMergePolicyState:
    return AutoMergePolicyState(
        run_mode=run_mode,
        kill_switch=kill_switch,
        classes={
            class_name: AutoMergeClassPolicy(auto_merge=class_name in enabled)
            for class_name in ALL_CLASSES
        },
        enabling_decision_ref="ce-ops#291-test-enable",
    )


def numstat_for(paths: list[str], additions: int = 1, deletions: int = 0) -> list[ChangeStat]:
    return [
        ChangeStat(path=path, additions=additions, deletions=deletions, binary=False)
        for path in paths
    ]


def test_default_state_is_secret_free_armed_off() -> None:
    state = AutoMergePolicyState.default()
    assert state.run_mode == "dev"
    assert state.kill_switch is False
    assert state.enabling_decision_ref is None
    assert all(not policy.auto_merge for policy in state.classes.values())


def test_policy_state_round_trip(tmp_path) -> None:
    path = tmp_path / "policy.json"
    state = state_with_flags("docs")
    save_automerge_policy_state(path, state)
    loaded = load_automerge_policy_state(path)
    assert loaded.run_mode == "ceo"
    assert loaded.class_flag("docs") is True
    assert loaded.class_flag("code") is False
    assert not path.with_name(".policy.json.tmp").exists()


def test_absent_policy_state_loads_default(tmp_path) -> None:
    assert load_automerge_policy_state(tmp_path / "missing.json").run_mode == "dev"


def test_state_rejects_invalid_payload() -> None:
    with pytest.raises(AutoMergePolicyStateError):
        AutoMergePolicyState.from_payload({"run_mode": "dev", "kill_switch": "false"})
    with pytest.raises(AutoMergePolicyStateError):
        AutoMergePolicyState.from_payload(
            {"run_mode": "dev", "classes": {"docs": {"auto_merge": "yes"}}}
        )


def test_policy_state_path_uses_configured_default() -> None:
    assert str(automerge_policy_state_path()).endswith(".ce/state/automerge/policy.json")


def test_composes_classifier_with_size_ceremony_for_docs_auto() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
    )
    assert decision.mutation_class == "docs"
    assert decision.gates == tuple(size_ceremony("tiny", "docs")["ratification_gates"])
    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert decision.to_payload()["class"] == "tiny"
    assert len(decision.policy_sha) == 64


def test_composes_classifier_with_size_ceremony_for_schema_gesture() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["schemas/automerge-policy.schema.yaml"]),
        paths=["schemas/automerge-policy.schema.yaml"],
        declared_work_class="story",
        policy_state=state_with_flags("schema"),
        checks=GREEN_CHECKS,
    )
    assert decision.mutation_class == "schema"
    assert decision.gates == tuple(size_ceremony("story", "schema")["ratification_gates"])
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "gesture_class" in decision.rationale


def test_dev_mode_returns_gesture_even_for_docs_with_flag_on() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs", run_mode="dev"),
        checks=GREEN_CHECKS,
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "run_mode_dev" in decision.rationale


def test_kill_switch_returns_gesture() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs", kill_switch=True),
        checks=GREEN_CHECKS,
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "kill_switch" in decision.rationale


def test_class_flag_false_blocks_auto() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags(),
        checks=GREEN_CHECKS,
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "class_auto_merge_false" in decision.rationale


def test_changes_requested_blocks_auto() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks={**GREEN_CHECKS, "reviewDecision": "CHANGES_REQUESTED"},
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "reviewDecision_CHANGES_REQUESTED" in decision.rationale


def test_legacy_review_decision_keyword_blocks_and_exposes_compat_property() -> None:
    decision = decide_automerge(
        changed_paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks={"validate": "success"},
        review_decision="CHANGES_REQUESTED",
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.review_decision == "CHANGES_REQUESTED"
    assert decision.review_decision_blocked is True
    assert "reviewDecision_CHANGES_REQUESTED" in decision.rationale


def test_failing_check_blocks_auto() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks={"validate": "failure", "reviewDecision": "APPROVED"},
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "required_checks_not_green" in decision.rationale


def test_check_run_conclusion_failure_overrides_completed_status() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks={
            "check_runs": [
                {"name": "validate", "status": "completed", "conclusion": "failure"}
            ],
            "reviewDecision": "APPROVED",
        },
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.checks_green is False
    assert "required_checks_not_green" in decision.rationale


def test_split_required_blocks_auto() -> None:
    decision = decide_automerge(
        numstat=[ChangeStat(path="docs/huge.md", additions=1001, deletions=0, binary=False)],
        paths=["docs/huge.md"],
        declared_work_class="epic",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
    )
    assert decision.size_band == "split_required"
    assert decision.decision == AUTOMERGE_DECISION_GESTURE


def test_fail_closed_unknown_path_gesture() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["unknown/blob.bin"]),
        paths=["unknown/blob.bin"],
        declared_work_class="tiny",
        policy_state=state_with_flags("redaction"),
        checks=GREEN_CHECKS,
    )
    assert decision.mutation_class == "redaction"
    assert decision.decision == AUTOMERGE_DECISION_GESTURE


@pytest.mark.parametrize(
    ("mutation_class", "path"),
    [
        ("code", "validators/creator_engine_validator/work_sizing.py"),
        ("schema", "schemas/automerge-policy.schema.yaml"),
        ("deploy", ".github/workflows/ci.yml"),
        ("governance", "docs/contracts/ratification-flow.md"),
        ("identity", "validators/creator_engine_validator/secret_identity.py"),
        ("security", "validators/creator_engine_validator/forge/cred_injection_proxy.py"),
        ("attestation", "validators/creator_engine_validator/forge/approval_capability.py"),
        ("redaction", "validators/creator_engine_validator/forge/_redact.py"),
    ],
)
def test_gesture_class_never_returns_auto_even_if_flag_is_on(mutation_class: str, path: str) -> None:
    decision = decide_automerge(
        numstat=numstat_for([path]),
        paths=[path],
        declared_work_class="story",
        policy_state=state_with_flags(mutation_class),
        checks=GREEN_CHECKS,
    )
    assert decision.mutation_class == mutation_class
    assert decision.class_flag is True
    assert decision.decision == AUTOMERGE_DECISION_GESTURE


def test_dry_run_writes_decision_and_merges_nothing(tmp_path, monkeypatch) -> None:
    def explode(*args, **kwargs):  # pragma: no cover
        raise AssertionError("dry-run policy must not perform live actions")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)

    decision = emit_automerge_dry_run_decision(
        pr_number=291,
        head_sha="abc123",
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        output_dir=tmp_path,
    )

    assert decision.decision == AUTOMERGE_DECISION_AUTO
    written = tmp_path / "291-abc123.json"
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["decision"] == "AUTO"
    assert payload["mutation_class"] == "docs"
    assert payload["checks_snapshot"]["validate"] == "success"
