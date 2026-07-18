from __future__ import annotations

import json
import os
import socket
import subprocess
import copy
import tempfile
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks.work_sizing_floor import ChangeStat
from creator_engine_validator import brain_runtime
from creator_engine_validator.forge.automerge_actuate_cli import actuate_decision
from creator_engine_validator.forge.automerge_policy import (
    AUTOMERGE_DECISION_AUTO,
    AUTOMERGE_DECISION_GESTURE,
    AUTOMERGE_TIER_BRAIN_SUPERSEDE,
    AUTOMERGE_TIER_BRAIN_SUPERSEDE_PATH_ENVELOPE,
    AUTOMERGE_TIER_CARRIER_CHANGELOG,
    AUTOMERGE_TIER_CARRIER_CHANGELOG_PATH_ENVELOPE,
    AUTOMERGE_TIER_DOCS_ENVELOPE,
    AUTOMERGE_TIER_DOCS_ENVELOPE_PATH_ENVELOPE,
    AutoMergeClassPolicy,
    AutoMergePolicyState,
    AutoMergePolicyStateError,
    AutoMergeTierPolicy,
    automerge_policy_state_path,
    brain_supersede_tier_evidence,
    brain_supersede_path_envelope_matches,
    carrier_changelog_tier_matches,
    docs_envelope_tier_matches,
    decide_automerge,
    emit_automerge_dry_run_decision,
    load_automerge_policy_state,
    materialize_automerge_policy_state_from_variables,
    save_automerge_policy_state,
)
from creator_engine_validator.work_sizing import size_ceremony
from creator_engine_validator.runner import work_unit_cap
from creator_engine_validator import side_effect_ledger_runtime as ledger_runtime
import creator_engine_validator.forge.automerge_policy as automerge_policy


REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_CHECK = "Validate governance artifacts"
HEAD_SHA = "d" * 40


def valid_work_unit_receipt(tmp_path: Path | None = None):
    if tmp_path is None:
        tmp_path = Path(tempfile.mkdtemp(prefix="ce603-verified-ledger-"))
    awl_root = tmp_path / ".hermes" / "active-work-ledger"
    claim_path = awl_root / "claims" / "controller" / "lane.yaml"
    claim_path.parent.mkdir(parents=True)
    claim_path.write_text(yaml.safe_dump({
        "kind": "active-work-ledger-record", "record_type": "claim", "schema_version": "1",
        "controller_id": "controller", "lane_id": "lane",
        "record_timestamp": "source-controlled:claims/controller/lane.yaml",
        "worktree_path": "/worktrees/lane", "envelope_ref": ".hermes/envelopes/lane.md",
        "lease_seconds": 3600, "claimed_at": "source-controlled:claims/controller/lane.yaml",
        "last_heartbeat_at": "source-controlled:claims/controller/lane.yaml",
    }, sort_keys=True), encoding="utf-8")
    ledger_root = tmp_path / "ledger"
    reservation = ledger_runtime.reserve_work_unit_reservation(
        cap=100, run_id="automerge-run", attempt_id="automerge-attempt",
        reservation_id="automerge-reservation", requested=1,
        policy_sha256=automerge_policy.default_mutation_policy().policy_sha,
        recorded_at="2026-07-18T00:00:00Z",
        occurred_at="2026-07-18T00:00:00Z", repo_root=tmp_path,
        side_effect_ledger_root=ledger_root, active_work_ledger_root=awl_root,
        controller_id="controller", lane_id="lane", claim_ref="claims/controller/lane.yaml",
    )
    binding = reservation.binding
    assert binding is not None
    return binding, {
        "side_effect_ledger_root": ledger_root,
        "active_work_ledger_root": awl_root,
        "controller_id": "controller",
        "lane_id": "lane",
        "run_id": "automerge-run",
        "attempt_id": "automerge-attempt",
        "reservation_id": "automerge-reservation",
        "policy_sha256": reservation.receipt["policy_sha256"],
    }


def test_a2_a3_automerge_requires_valid_work_unit_receipt(tmp_path: Path):
    receipt = work_unit_cap.reserve(
        (), cap=10, run_id="run", attempt_id="attempt", reservation_id="reservation", requested=1,
        policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z",
    ).receipt
    binding, context = valid_work_unit_receipt(tmp_path)
    assert not automerge_policy.work_unit_receipt_evidence(None, **context)["valid"]
    assert not automerge_policy.work_unit_receipt_evidence(dict(receipt, source_state="unknown"), **context)["valid"]
    assert not automerge_policy.work_unit_receipt_evidence(receipt, **context)["valid"]
    assert automerge_policy.work_unit_receipt_evidence(binding, **context)["valid"]


@pytest.mark.parametrize("mutate", [
    lambda receipt: None,
    lambda receipt: dict(receipt, receipt_id="0" * 64),
    lambda receipt: dict(receipt, source_state="late"),
    lambda receipt: dict(receipt, unit="ce.usd.v1"),
    lambda receipt: dict(receipt, policy_sha256="b" * 64),
])
def test_a2_a3_predicate_is_not_live_in_production_decide_path(mutate, tmp_path: Path) -> None:
    receipt = work_unit_cap.reserve(
        (), cap=10, run_id="run", attempt_id="attempt", reservation_id="reservation", requested=1,
        policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z",
    ).receipt
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]), paths=["README.md"], declared_work_class="tiny",
        policy_state=state_with_flags("docs"), checks=GREEN_CHECKS,
        work_unit_receipt=mutate(receipt), **canary_identity(),
    )
    assert not any(item.startswith("work_unit_receipt_") for item in decision.rationale)
    bypass = decide_automerge(
        numstat=numstat_for(["README.md"]), paths=["README.md"], declared_work_class="tiny",
        policy_state=state_with_flags("docs"), checks=GREEN_CHECKS, work_unit_required=False,
        **canary_identity(),
    )
    assert decision.decision == bypass.decision
    assert decision.rationale == bypass.rationale


def test_a2_a3_bound_receipt_does_not_change_production_decide_path(tmp_path: Path) -> None:
    binding, _context = valid_work_unit_receipt(tmp_path)
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]), paths=["README.md"], declared_work_class="tiny",
        policy_state=state_with_flags("docs"), checks=GREEN_CHECKS,
        work_unit_receipt=binding, **canary_identity(),
    )
    assert not any(item.startswith("work_unit_receipt_") for item in decision.rationale)
POLICY_SHA = "a" * 64

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
    REQUIRED_CHECK: "success",
    "unit": "success",
    "reviewDecision": "APPROVED",
}
LIVE_GREEN_CHECKS = {
    "checks": [
        {"name": REQUIRED_CHECK, "state": "SUCCESS", "conclusion": "success"},
        {"name": "unit", "state": "SUCCESS", "conclusion": "success"},
    ]
}


def state_with_flags(
    *enabled: str,
    run_mode: str = "ceo",
    kill_switch: bool = False,
    enabled_tiers: tuple[str, ...] = (),
) -> AutoMergePolicyState:
    return AutoMergePolicyState(
        run_mode=run_mode,
        kill_switch=kill_switch,
        classes={
            class_name: AutoMergeClassPolicy(auto_merge=class_name in enabled)
            for class_name in ALL_CLASSES
        },
        tiers={
            AUTOMERGE_TIER_CARRIER_CHANGELOG: AutoMergeTierPolicy(
                auto_merge=AUTOMERGE_TIER_CARRIER_CHANGELOG in enabled_tiers
            ),
            AUTOMERGE_TIER_DOCS_ENVELOPE: AutoMergeTierPolicy(
                auto_merge="docs" in enabled
                or AUTOMERGE_TIER_DOCS_ENVELOPE in enabled_tiers
            ),
            AUTOMERGE_TIER_BRAIN_SUPERSEDE: AutoMergeTierPolicy(
                auto_merge=AUTOMERGE_TIER_BRAIN_SUPERSEDE in enabled_tiers
            ),
        },
        enabling_decision_ref="ce-ops#291-test-enable",
    )


def canary_identity() -> dict[str, str]:
    return {"author_login": "author-dev", "approver_login": "reviewer-dev"}


def numstat_for(paths: list[str], additions: int = 1, deletions: int = 0) -> list[ChangeStat]:
    return [
        ChangeStat(path=path, additions=additions, deletions=deletions, binary=False)
        for path in paths
    ]


BRAIN_SUPERSEDE_PATHS = [
    ".ce/brain/assertions.yaml",
    ".ce/changelog/ce-413-automerge-tier-b.md",
    ".ce/pr-manifests/ce-413-automerge-tier-b.md",
]
DOCS_ENVELOPE_PATHS = [
    # ce-621: must not be a docs/adr/** or docs/decisions/** or docs/governance/**
    # path — those are now governance class (ADR-0016 §8 non-goal 8).
    "docs/guide/automerge-feature.md",
    ".ce/changelog/ce-a3-docs-envelope-automerge.md",
    ".ce/pr-manifests/ce-a3-docs-envelope-automerge.md",
]


def brain_supersede_fixture() -> tuple[str, str, list[dict], list[dict]]:
    initial = brain_runtime.assert_claim(
        claim={
            "subject": "doctrine-item",
            "predicate": "asserts",
            "object": "merge-queue-conflict-gate",
            "item": 10,
            "verdict": "present",
        },
        scope="doctrine/day1",
        evidence_ref="probe:integrator_belt_merge_queue_conflict_gate",
        assertion_id="brain-assertion-d1b-10-merge-queue-conflict-gate-v5",
        records=[],
        write=lambda _path, _text: None,
    )
    old_text = initial.ledger_text
    old_records = brain_runtime.load_ledger_text(old_text)
    corrected = brain_runtime.correct_claim(
        assertion_id="brain-assertion-d1b-10-merge-queue-conflict-gate-v5",
        claim={
            "subject": "doctrine-item",
            "predicate": "asserts",
            "object": "merge-queue-conflict-gate",
            "item": 10,
            "verdict": "present",
            "details": "Merge-queue automation owns sequencing and escalates conflict repair.",
        },
        scope="doctrine/day1",
        evidence_ref="probe:integrator_belt_merge_queue_conflict_gate",
        new_assertion_id="brain-assertion-d1b-10-merge-queue-conflict-gate-v6",
        records=old_records,
        write=lambda _path, _text: None,
    )
    new_text = corrected.ledger_text
    new_records = brain_runtime.load_ledger_text(new_text)
    return old_text, new_text, old_records, new_records


def rehash_records(records: list[dict], *, start: int = 0) -> list[dict]:
    updated = copy.deepcopy(records)
    for idx in range(start, len(updated)):
        updated[idx]["prev_hash"] = (
            brain_runtime.GENESIS_PREV_HASH
            if idx == 0
            else updated[idx - 1]["content_hash"]
        )
        updated[idx]["content_hash"] = brain_runtime.canonical_content_hash(updated[idx])
    return updated


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


def test_variable_materialization_defaults_to_dormant_dev(tmp_path: Path) -> None:
    path = tmp_path / ".ce" / "state" / "automerge" / "policy.json"

    state = materialize_automerge_policy_state_from_variables(path)

    loaded = load_automerge_policy_state(path)
    assert state == loaded
    assert loaded.run_mode == "dev"
    assert loaded.kill_switch is False
    assert loaded.enabling_decision_ref is None
    assert all(not policy.auto_merge for policy in loaded.classes.values())
    assert loaded.tier_flag(AUTOMERGE_TIER_CARRIER_CHANGELOG) is False
    assert loaded.tier_flag(AUTOMERGE_TIER_BRAIN_SUPERSEDE) is False


@pytest.mark.parametrize("run_mode", ["", "CEO", "ceo ", "dev", "prod", "true"])
def test_variable_materialization_malformed_run_mode_stays_dormant(
    tmp_path: Path,
    run_mode: str,
) -> None:
    path = tmp_path / "policy.json"

    state = materialize_automerge_policy_state_from_variables(
        path,
        run_mode_variable=run_mode,
        enabling_ref_variable="ce-ops#313-enable",
    )

    assert state.run_mode == "dev"
    assert state.kill_switch is False
    assert all(not policy.auto_merge for policy in state.classes.values())


def test_variable_materialization_ceo_arms_docs_only(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"

    state = materialize_automerge_policy_state_from_variables(
        path,
        run_mode_variable="ceo",
        enabling_ref_variable="ce-ops#313-enable",
    )

    assert state.run_mode == "ceo"
    assert state.kill_switch is False
    assert state.enabling_decision_ref == "ce-ops#313-enable"
    assert state.class_flag("docs") is True
    assert state.tier_flag(AUTOMERGE_TIER_DOCS_ENVELOPE) is True
    assert all(
        not policy.auto_merge
        for class_name, policy in state.classes.items()
        if class_name != "docs"
    )
    assert state.tier_flag(AUTOMERGE_TIER_CARRIER_CHANGELOG) is False


def test_variable_materialization_arms_carrier_changelog_tier_only_when_enabled(
    tmp_path: Path,
) -> None:
    path = tmp_path / "policy.json"

    state = materialize_automerge_policy_state_from_variables(
        path,
        run_mode_variable="ceo",
        enabling_ref_variable="ce-ops#412-enable",
        tier_carrier_changelog_variable="true",
    )

    assert state.class_flag("docs") is True
    assert state.tier_flag(AUTOMERGE_TIER_DOCS_ENVELOPE) is True
    assert state.tier_flag(AUTOMERGE_TIER_CARRIER_CHANGELOG) is True
    assert state.tier_flag(AUTOMERGE_TIER_BRAIN_SUPERSEDE) is False


def test_variable_materialization_arms_brain_supersede_tier_only_when_enabled(
    tmp_path: Path,
) -> None:
    path = tmp_path / "policy.json"

    state = materialize_automerge_policy_state_from_variables(
        path,
        run_mode_variable="ceo",
        enabling_ref_variable="ce-ops#413-enable",
        tier_brain_supersede_variable="true",
    )

    assert state.class_flag("docs") is True
    assert state.tier_flag(AUTOMERGE_TIER_DOCS_ENVELOPE) is True
    assert state.tier_flag(AUTOMERGE_TIER_CARRIER_CHANGELOG) is False
    assert state.tier_flag(AUTOMERGE_TIER_BRAIN_SUPERSEDE) is True


def test_variable_materialization_tier_flag_is_subordinate_to_run_mode(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"

    state = materialize_automerge_policy_state_from_variables(
        path,
        run_mode_variable="dev",
        enabling_ref_variable="ce-ops#412-enable",
        tier_carrier_changelog_variable="true",
        tier_brain_supersede_variable="true",
    )

    assert state.class_flag("docs") is False
    assert state.tier_flag(AUTOMERGE_TIER_DOCS_ENVELOPE) is False
    assert state.tier_flag(AUTOMERGE_TIER_CARRIER_CHANGELOG) is False
    assert state.tier_flag(AUTOMERGE_TIER_BRAIN_SUPERSEDE) is False


def test_variable_materialization_strangeloop_arms_docs_only(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"

    state = materialize_automerge_policy_state_from_variables(
        path,
        run_mode_variable="strangeLoop",
        enabling_ref_variable="ce-ops#313-enable",
    )

    assert state.run_mode == "strangeLoop"
    assert state.kill_switch is False
    assert state.enabling_decision_ref == "ce-ops#313-enable"
    assert state.class_flag("docs") is True
    assert state.tier_flag(AUTOMERGE_TIER_DOCS_ENVELOPE) is True
    assert all(
        not policy.auto_merge
        for class_name, policy in state.classes.items()
        if class_name != "docs"
    )


def test_variable_materialization_kill_switch_halts_even_when_strangeloop(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"

    state = materialize_automerge_policy_state_from_variables(
        path,
        run_mode_variable="strangeLoop",
        enabling_ref_variable="ce-ops#313-enable",
        kill_switch_variable="true",
    )

    assert state.run_mode == "strangeLoop"
    assert state.kill_switch is True
    assert state.class_flag("docs") is True


def test_state_rejects_invalid_payload() -> None:
    with pytest.raises(AutoMergePolicyStateError):
        AutoMergePolicyState.from_payload({"run_mode": "dev", "kill_switch": "false"})
    with pytest.raises(AutoMergePolicyStateError):
        AutoMergePolicyState.from_payload(
            {"run_mode": "dev", "classes": {"docs": {"auto_merge": "yes"}}}
        )


def test_policy_state_path_uses_configured_default() -> None:
    assert str(automerge_policy_state_path()).endswith(".ce/state/automerge/policy.json")


def test_carrier_changelog_tier_predicate_accepts_only_carrier_and_changelog_paths() -> None:
    assert carrier_changelog_tier_matches(
        [
            ".ce/changelog/ce-412-automerge-tier-a.md",
            ".ce/pr-manifests/ce-412-automerge-tier-a.md",
        ]
    )


def test_carrier_changelog_tier_predicate_rejects_negative_path() -> None:
    assert not carrier_changelog_tier_matches(["README.md"])


def test_carrier_changelog_tier_predicate_rejects_mixed_path_set() -> None:
    assert not carrier_changelog_tier_matches(
        [
            ".ce/changelog/ce-412-automerge-tier-a.md",
            "docs/usage.md",
        ]
    )


def test_docs_envelope_tier_predicate_accepts_ratified_path_set() -> None:
    assert docs_envelope_tier_matches(DOCS_ENVELOPE_PATHS)
    assert docs_envelope_tier_matches(["README.md", "docs/usage.md"])


def test_docs_envelope_tier_predicate_rejects_code_path() -> None:
    assert not docs_envelope_tier_matches(
        [*DOCS_ENVELOPE_PATHS, "validators/creator_engine_validator/forge/example.py"]
    )


# ce-ops#619 — extension allow-list deny cases
def test_docs_envelope_tier_predicate_rejects_python_in_docs() -> None:
    assert not docs_envelope_tier_matches(["docs/scripts/build.py"])


def test_docs_envelope_tier_predicate_rejects_shell_in_docs() -> None:
    assert not docs_envelope_tier_matches(["docs/hooks/x.sh"])


def test_docs_envelope_tier_predicate_rejects_yaml_in_docs() -> None:
    assert not docs_envelope_tier_matches(["docs/conf.yaml"])


def test_docs_envelope_tier_predicate_rejects_no_extension_in_docs() -> None:
    assert not docs_envelope_tier_matches(["docs/Makefile"])


# ce-ops#619 — extension allow-list allow cases
def test_docs_envelope_tier_predicate_allows_md_in_docs() -> None:
    assert docs_envelope_tier_matches(["docs/guide.md"])


def test_docs_envelope_tier_predicate_allows_root_readme() -> None:
    assert docs_envelope_tier_matches(["README.md"])


def test_docs_envelope_tier_predicate_allows_svg_in_docs() -> None:
    assert docs_envelope_tier_matches(["docs/img/logo.svg"])


def test_docs_envelope_tier_predicate_allows_mixed_valid_set() -> None:
    assert docs_envelope_tier_matches(
        [
            "docs/guide.md",
            "README.md",
            "docs/img/logo.svg",
            ".ce/changelog/ce-619-docs-envelope-allowlist.md",
            ".ce/pr-manifests/ce-619-docs-envelope-allowlist.md",
        ]
    )


# ce-ops#619 — extension match is case-insensitive
def test_docs_envelope_tier_predicate_extension_match_is_case_insensitive() -> None:
    assert docs_envelope_tier_matches(["docs/screenshot.PNG"])
    assert not docs_envelope_tier_matches(["docs/script.PY"])


def test_brain_supersede_tier_predicate_accepts_real_supersede_fixture() -> None:
    old_text, new_text, _old_records, _new_records = brain_supersede_fixture()

    decision = decide_automerge(
        numstat=numstat_for(BRAIN_SUPERSEDE_PATHS, additions=2, deletions=0),
        paths=BRAIN_SUPERSEDE_PATHS,
        declared_work_class="XS",
        policy_state=state_with_flags(
            "docs",
            enabled_tiers=(AUTOMERGE_TIER_BRAIN_SUPERSEDE,),
        ),
        checks=GREEN_CHECKS,
        repo="creator-engine/creator-engine",
        branch="ce-413-automerge-tier-b",
        base="main",
        brain_ledger_base_text=old_text,
        brain_ledger_head_text=new_text,
        work_unit_receipt=valid_work_unit_receipt(),
        **canary_identity(),
    )

    payload = decision.to_payload()
    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert payload["tier"] == AUTOMERGE_TIER_BRAIN_SUPERSEDE
    assert payload["tier_flag"] is True
    assert payload["path_envelope"] == AUTOMERGE_TIER_BRAIN_SUPERSEDE_PATH_ENVELOPE
    assert payload["ledger_evidence"]["old_record_count"] == 1
    assert payload["ledger_evidence"]["new_record_count"] == 3
    assert payload["ledger_evidence"]["old_active_count"] == 1
    assert payload["ledger_evidence"]["new_active_count"] == 1
    assert payload["ledger_evidence"]["superseded_assertion_ids"] == [
        "brain-assertion-d1b-10-merge-queue-conflict-gate-v5"
    ]
    assert payload["ledger_evidence"]["old_head_content_hash"]
    assert payload["ledger_evidence"]["new_head_content_hash"]
    assert payload["reviewer_venue"] == "reviewer-dev"


def test_brain_supersede_tier_flag_off_blocks_default() -> None:
    old_text, new_text, _old_records, _new_records = brain_supersede_fixture()

    decision = decide_automerge(
        numstat=numstat_for(BRAIN_SUPERSEDE_PATHS, additions=2, deletions=0),
        paths=BRAIN_SUPERSEDE_PATHS,
        declared_work_class="XS",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        brain_ledger_base_text=old_text,
        brain_ledger_head_text=new_text,
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.tier == AUTOMERGE_TIER_BRAIN_SUPERSEDE
    assert "tier_brain_supersede_false" in decision.rationale


def test_brain_supersede_tier_rejects_existing_record_mutation() -> None:
    _old_text, _new_text, old_records, new_records = brain_supersede_fixture()
    mutated = copy.deepcopy(new_records)
    mutated[0]["statement"] = "mutated prior record"
    mutated = rehash_records(mutated, start=0)

    evidence, reason = brain_supersede_tier_evidence(
        BRAIN_SUPERSEDE_PATHS,
        declared_work_class="XS",
        old_records=old_records,
        new_records=mutated,
    )

    assert evidence is None
    assert reason == "tier_brain_supersede_existing_record_mutation"


def test_brain_supersede_tier_rejects_two_chains_in_one_pr() -> None:
    _old_text, new_text, old_records, new_records = brain_supersede_fixture()
    second = brain_runtime.correct_claim(
        assertion_id="brain-assertion-d1b-10-merge-queue-conflict-gate-v6",
        claim={
            "subject": "doctrine-item",
            "predicate": "asserts",
            "object": "merge-queue-conflict-gate",
            "item": 10,
            "verdict": "present",
            "details": "second supersede",
        },
        scope="doctrine/day1",
        evidence_ref="probe:integrator_belt_merge_queue_conflict_gate",
        new_assertion_id="brain-assertion-d1b-10-merge-queue-conflict-gate-v7",
        records=brain_runtime.load_ledger_text(new_text),
        write=lambda _path, _text: None,
    )

    evidence, reason = brain_supersede_tier_evidence(
        BRAIN_SUPERSEDE_PATHS,
        declared_work_class="XS",
        old_records=old_records,
        new_records=brain_runtime.load_ledger_text(second.ledger_text),
    )

    assert evidence is None
    assert reason == "tier_brain_supersede_not_single_chain"


def test_brain_supersede_tier_rejects_extra_path() -> None:
    assert not brain_supersede_path_envelope_matches([*BRAIN_SUPERSEDE_PATHS, "README.md"])


def test_brain_supersede_tier_rejects_active_count_mismatch() -> None:
    _old_text, _new_text, old_records, new_records = brain_supersede_fixture()
    mutated = copy.deepcopy(new_records)
    mutated[-1]["status"] = "superseded"
    mutated[-1]["superseded_by"] = "brain-assertion-d1b-10-merge-queue-conflict-gate-v8"
    mutated[-1]["content_hash"] = brain_runtime.canonical_content_hash(mutated[-1])

    evidence, reason = brain_supersede_tier_evidence(
        BRAIN_SUPERSEDE_PATHS,
        declared_work_class="XS",
        old_records=old_records,
        new_records=mutated,
    )

    assert evidence is None
    assert reason == "tier_brain_supersede_new_ledger_invalid"


def test_brain_supersede_tier_rejects_forbidden_fields() -> None:
    _old_text, _new_text, old_records, new_records = brain_supersede_fixture()
    mutated = copy.deepcopy(new_records)
    mutated[-1]["claim"]["token"] = "forbidden"
    mutated = rehash_records(mutated, start=len(old_records))

    evidence, reason = brain_supersede_tier_evidence(
        BRAIN_SUPERSEDE_PATHS,
        declared_work_class="XS",
        old_records=old_records,
        new_records=mutated,
    )

    assert evidence is None
    assert reason == "tier_brain_supersede_new_ledger_invalid"


def test_brain_supersede_tier_rejects_wrong_work_class() -> None:
    _old_text, _new_text, old_records, new_records = brain_supersede_fixture()

    evidence, reason = brain_supersede_tier_evidence(
        BRAIN_SUPERSEDE_PATHS,
        declared_work_class="S",
        old_records=old_records,
        new_records=new_records,
    )

    assert evidence is None
    assert reason == "tier_brain_supersede_work_class_not_xs"


def test_composes_classifier_with_size_ceremony_for_docs_auto() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        work_unit_receipt=valid_work_unit_receipt(),
        repo="creator-engine/creator-engine",
        branch="ce/docs",
        base="main",
        **canary_identity(),
    )
    assert decision.mutation_class == "docs"
    assert decision.gates == tuple(size_ceremony("tiny", "docs")["ratification_gates"])
    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert decision.to_payload()["class"] == "XS"
    assert decision.to_payload()["repo"] == "creator-engine/creator-engine"
    assert decision.to_payload()["branch"] == "ce/docs"
    assert decision.to_payload()["base"] == "main"
    assert decision.to_payload()["required_checks"] == [REQUIRED_CHECK]
    assert decision.to_payload()["author_login"] == "author-dev"
    assert decision.to_payload()["approver_login"] == "reviewer-dev"
    assert len(decision.policy_sha) == 64


def test_carrier_changelog_tier_flag_off_blocks_tier_default() -> None:
    paths = [
        ".ce/changelog/ce-412-automerge-tier-a.md",
        ".ce/pr-manifests/ce-412-automerge-tier-a.md",
    ]

    decision = decide_automerge(
        numstat=numstat_for(paths),
        paths=paths,
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        work_unit_receipt=valid_work_unit_receipt(),
        repo="creator-engine/creator-engine",
        branch="ce-412-automerge-tier-a",
        base="main",
        **canary_identity(),
    )

    payload = decision.to_payload()
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.tier == AUTOMERGE_TIER_CARRIER_CHANGELOG
    assert decision.tier_flag is False
    assert "tier_carrier_changelog_false" in decision.rationale
    assert payload["reviewer_venue"] == "reviewer-dev"


def test_carrier_changelog_tier_auto_payload_includes_audit_fields() -> None:
    paths = [
        ".ce/changelog/ce-412-automerge-tier-a.md",
        ".ce/pr-manifests/ce-412-automerge-tier-a.md",
    ]

    decision = decide_automerge(
        numstat=numstat_for(paths),
        paths=paths,
        declared_work_class="S",
        policy_state=state_with_flags(
            "docs",
            enabled_tiers=(AUTOMERGE_TIER_CARRIER_CHANGELOG,),
        ),
        checks=GREEN_CHECKS,
        work_unit_receipt=valid_work_unit_receipt(),
        repo="creator-engine/creator-engine",
        branch="ce-412-automerge-tier-a",
        base="main",
        **canary_identity(),
    )

    payload = decision.to_payload()
    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert payload["tier"] == AUTOMERGE_TIER_CARRIER_CHANGELOG
    assert payload["tier_flag"] is True
    assert payload["path_envelope"] == AUTOMERGE_TIER_CARRIER_CHANGELOG_PATH_ENVELOPE
    assert payload["changed_paths"] == paths
    assert payload["reviewer_venue"] == "reviewer-dev"


def test_mixed_carrier_changelog_path_set_uses_docs_envelope_tier() -> None:
    paths = [
        ".ce/changelog/ce-412-automerge-tier-a.md",
        "README.md",
    ]

    decision = decide_automerge(
        numstat=numstat_for(paths),
        paths=paths,
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        work_unit_receipt=valid_work_unit_receipt(),
        repo="creator-engine/creator-engine",
        branch="ce-412-automerge-tier-a",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert decision.tier == AUTOMERGE_TIER_DOCS_ENVELOPE
    assert decision.tier_flag is True


def test_docs_envelope_tier_771_path_set_auto_when_docs_class_armed() -> None:
    decision = decide_automerge(
        numstat=numstat_for(DOCS_ENVELOPE_PATHS),
        paths=DOCS_ENVELOPE_PATHS,
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        work_unit_receipt=valid_work_unit_receipt(),
        repo="creator-engine/creator-engine",
        branch="ce-a3-docs-envelope-automerge",
        base="main",
        **canary_identity(),
    )

    payload = decision.to_payload()
    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert payload["tier"] == AUTOMERGE_TIER_DOCS_ENVELOPE
    assert payload["tier_flag"] is True
    assert payload["path_envelope"] == AUTOMERGE_TIER_DOCS_ENVELOPE_PATH_ENVELOPE
    assert payload["changed_paths"] == DOCS_ENVELOPE_PATHS


def test_docs_envelope_tier_flag_off_blocks_when_docs_class_armed() -> None:
    """ADR-0016 §2.b P12: docs class armed but docs_envelope tier disarmed → GESTURE."""
    state = AutoMergePolicyState(
        run_mode="ceo",
        kill_switch=False,
        classes={
            class_name: AutoMergeClassPolicy(auto_merge=class_name == "docs")
            for class_name in ALL_CLASSES
        },
        tiers={
            AUTOMERGE_TIER_CARRIER_CHANGELOG: AutoMergeTierPolicy(auto_merge=False),
            AUTOMERGE_TIER_DOCS_ENVELOPE: AutoMergeTierPolicy(auto_merge=False),
            AUTOMERGE_TIER_BRAIN_SUPERSEDE: AutoMergeTierPolicy(auto_merge=False),
        },
        enabling_decision_ref="ce-ops#291-test-enable",
    )

    decision = decide_automerge(
        numstat=numstat_for(DOCS_ENVELOPE_PATHS),
        paths=DOCS_ENVELOPE_PATHS,
        declared_work_class="tiny",
        policy_state=state,
        checks=GREEN_CHECKS,
        repo="creator-engine/creator-engine",
        branch="ce-a3-docs-envelope-automerge",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.tier == AUTOMERGE_TIER_DOCS_ENVELOPE
    assert decision.tier_flag is False
    assert "tier_docs_envelope_false" in decision.rationale


def test_docs_envelope_tier_771_path_set_plus_code_file_is_not_auto() -> None:
    paths = [
        *DOCS_ENVELOPE_PATHS,
        "validators/creator_engine_validator/forge/automerge_policy.py",
    ]

    decision = decide_automerge(
        numstat=numstat_for(paths),
        paths=paths,
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        repo="creator-engine/creator-engine",
        branch="ce-a3-docs-envelope-automerge",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.tier is None
    assert decision.mutation_class == "code"
    assert "gesture_class" in decision.rationale


@pytest.mark.parametrize("declared_work_class", ["M", "L"])
def test_docs_envelope_tier_larger_work_classes_are_not_auto(
    declared_work_class: str,
) -> None:
    decision = decide_automerge(
        numstat=numstat_for(DOCS_ENVELOPE_PATHS),
        paths=DOCS_ENVELOPE_PATHS,
        declared_work_class=declared_work_class,
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        repo="creator-engine/creator-engine",
        branch="ce-a3-docs-envelope-automerge",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.tier == AUTOMERGE_TIER_DOCS_ENVELOPE
    assert "work_class_outside_canary" in decision.rationale


def test_decide_returns_auto_with_live_pr_data_when_policy_is_armed() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="S",
        policy_state=state_with_flags("docs", run_mode="ceo"),
        checks=LIVE_GREEN_CHECKS,
        review_decision="APPROVED",
        work_unit_receipt=valid_work_unit_receipt(),
        pr_number=313,
        head_sha=HEAD_SHA,
        repo="creator-engine/creator-engine",
        branch="ce/live-pr-data",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert decision.review_decision == "APPROVED"
    assert decision.checks_green is True
    assert decision.enabling_decision_ref == "ce-ops#291-test-enable"


@pytest.mark.parametrize("declared_work_class", ["XS", "S", "tiny", "story"])
def test_canary_work_class_aliases_are_accepted(declared_work_class: str) -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class=declared_work_class,
        policy_state=state_with_flags("docs", run_mode="ceo"),
        checks=LIVE_GREEN_CHECKS,
        review_decision="APPROVED",
        work_unit_receipt=valid_work_unit_receipt(),
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert decision.work_class in {"XS", "S"}


@pytest.mark.parametrize("declared_work_class", ["M", "L", "feature", "epic"])
def test_larger_work_classes_are_outside_canary(declared_work_class: str) -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class=declared_work_class,
        policy_state=state_with_flags("docs", run_mode="ceo"),
        checks=LIVE_GREEN_CHECKS,
        review_decision="APPROVED",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "work_class_outside_canary" in decision.rationale


def test_review_required_blocks_auto_even_with_approver_evidence() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="S",
        policy_state=state_with_flags("docs", run_mode="ceo"),
        checks=LIVE_GREEN_CHECKS,
        review_decision="REVIEW_REQUIRED",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "reviewDecision_not_APPROVED" in decision.rationale


@pytest.mark.parametrize("review_decision", [None, ""])
def test_missing_review_decision_blocks_auto_even_with_approver_evidence(
    review_decision: str | None,
) -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="S",
        policy_state=state_with_flags("docs", run_mode="ceo"),
        checks=LIVE_GREEN_CHECKS,
        review_decision=review_decision,
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "reviewDecision_not_APPROVED" in decision.rationale


def test_composes_classifier_with_size_ceremony_for_schema_gesture() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["schemas/automerge-policy.schema.yaml"]),
        paths=["schemas/automerge-policy.schema.yaml"],
        declared_work_class="story",
        policy_state=state_with_flags("schema"),
        checks=GREEN_CHECKS,
        **canary_identity(),
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
        **canary_identity(),
    )
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "run_mode_dev" in decision.rationale


def test_default_dev_mode_returns_gesture_without_gh_calls(monkeypatch) -> None:
    def explode(*args, **kwargs):  # pragma: no cover
        raise AssertionError("disarmed decision must not call gh or network")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)

    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="S",
        policy_state=AutoMergePolicyState.default(),
        checks=LIVE_GREEN_CHECKS,
        review_decision="APPROVED",
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        **canary_identity(),
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
        work_unit_receipt=valid_work_unit_receipt(),
        repo="creator-engine/creator-engine",
        branch="ce/docs",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_AUTO
    written = tmp_path / "291-abc123.json"
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["decision"] == "AUTO"
    assert payload["mutation_class"] == "docs"
    assert payload["checks_snapshot"][REQUIRED_CHECK] == "success"
    assert payload["repo"] == "creator-engine/creator-engine"
    assert payload["branch"] == "ce/docs"
    assert payload["base"] == "main"
    assert payload["author_login"] == "author-dev"
    assert payload["approver_login"] == "reviewer-dev"


class FakeActuateGh:
    def __init__(self, *, check_conclusion: str = "success") -> None:
        self.check_conclusion = check_conclusion
        self.calls: list[list[str]] = []

    def __call__(self, argv, input_text=None):
        self.calls.append(list(argv))
        if argv[:3] == ["gh", "pr", "checks"]:
            payload = [{"name": REQUIRED_CHECK, "conclusion": self.check_conclusion}]
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")
        if argv[:3] == ["gh", "pr", "view"]:
            payload = {
                "author": {"login": "author-dev"},
                "latestReviews": [
                    {"author": {"login": "reviewer-dev"}, "state": "APPROVED"}
                ],
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        query = next((str(arg) for arg in argv if str(arg).startswith("query=")), "")
        if "enablePullRequestAutoMerge" in query:
            payload = {
                "data": {
                    "enablePullRequestAutoMerge": {
                        "pullRequest": {
                            "autoMergeRequest": {
                                "enabledAt": "now",
                                "mergeMethod": "SQUASH",
                            }
                        }
                    }
                }
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        payload = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "id": "PR_kwDO_strangeLoop",
                        "autoMergeRequest": None,
                    }
                }
            }
        }
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

    def mutation_calls(self) -> list[list[str]]:
        return [
            call
            for call in self.calls
            if any("enablePullRequestAutoMerge" in str(arg) for arg in call)
        ]


def _strange_loop_decision(**overrides):
    payload = {
        "class": "S",
        "size_band": "target_advisory",
        "minimum_work_class": "S",
        "mutation_class": "docs",
        "gates": ["auto_back_gate"],
        "decision": "AUTO",
        "rationale": ["all_auto_guards_passed"],
        "policy_sha": POLICY_SHA,
        "checks_snapshot": {"required_checks": [REQUIRED_CHECK]},
        "required_checks": [REQUIRED_CHECK],
        "run_mode": "ceo",
        "kill_switch": False,
        "class_flag": True,
        "enabling_decision_ref": "ce-ops#313-enable",
        "reviewDecision": "APPROVED",
        "checks_green": True,
        "pr_number": 313,
        "head_sha": HEAD_SHA,
        "author_login": "author-dev",
        "approver_login": "reviewer-dev",
        "change": {
            "repo": "strange-loop/creator-engine",
            "branch": "ce-arm-automerge-actuate",
            "base": "main",
            "pr_number": 313,
            "head_sha": HEAD_SHA,
            "manifest_paths": [".ce/pr-manifests/ce-arm-automerge-actuate.md"],
            "author_login": "author-dev",
            "approver_login": "reviewer-dev",
        },
    }
    payload.update(overrides)
    return payload


def _write_decision(tmp_path: Path, payload) -> Path:
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_live_automerge_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_mode: str = "ceo",
) -> Path:
    monkeypatch.chdir(tmp_path)
    path = automerge_policy_state_path(tmp_path / ".ce" / "state")
    save_automerge_policy_state(path, state_with_flags("docs", run_mode=run_mode))
    return path


def test_actuate_caller_dormant_in_dev_run_mode_makes_no_gh_calls(tmp_path: Path) -> None:
    gh = FakeActuateGh()

    result = actuate_decision(
        _write_decision(tmp_path, _strange_loop_decision(run_mode="dev")),
        gh_runner=gh,
    )

    assert result.dormant is True
    assert result.reason == "run_mode_not_armed"
    assert result.acted is False
    assert gh.calls == []


def test_actuate_caller_mutates_only_after_actuator_predicates_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_live_automerge_policy(tmp_path, monkeypatch)
    red_gh = FakeActuateGh(check_conclusion="failure")

    refused = actuate_decision(
        _write_decision(tmp_path, _strange_loop_decision()),
        gh_runner=red_gh,
    )

    assert refused.refused is True
    assert refused.reason == "required_checks_not_green"
    assert refused.acted is False
    assert red_gh.mutation_calls() == []

    green_gh = FakeActuateGh(check_conclusion="success")

    actuated = actuate_decision(
        _write_decision(tmp_path, _strange_loop_decision()),
        gh_runner=green_gh,
    )

    assert actuated.actuated is True
    assert actuated.reason == "all_predicates_green"
    assert actuated.acted is True
    assert len(green_gh.mutation_calls()) == 1


def test_actuator_strangeloop_armed_mode_actuates_like_ceo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_live_automerge_policy(tmp_path, monkeypatch, run_mode="strangeLoop")
    gh = FakeActuateGh(check_conclusion="success")

    result = actuate_decision(
        _write_decision(tmp_path, _strange_loop_decision(run_mode="strangeLoop")),
        gh_runner=gh,
    )

    assert result.actuated is True
    assert result.reason == "all_predicates_green"
    assert result.acted is True
    assert len(gh.mutation_calls()) == 1


def test_materialized_decision_reaches_actuator_with_change_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = tmp_path / ".ce" / "state" / "automerge" / "policy.json"
    state = materialize_automerge_policy_state_from_variables(
        policy_path,
        run_mode_variable="ceo",
        enabling_ref_variable="ce-ops#313-enable",
    )
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state,
        checks=GREEN_CHECKS,
        work_unit_receipt=valid_work_unit_receipt(),
        pr_number=313,
        head_sha=HEAD_SHA,
        repo="strange-loop/creator-engine",
        branch="ce-arm-automerge-actuate",
        base="main",
        **canary_identity(),
    )
    payload = decision.to_payload()
    assert payload["decision"] == AUTOMERGE_DECISION_AUTO
    assert payload["repo"] == "strange-loop/creator-engine"
    assert payload["branch"] == "ce-arm-automerge-actuate"
    assert payload["base"] == "main"

    gh = FakeActuateGh(check_conclusion="success")
    result = actuate_decision(_write_decision(tmp_path, payload), gh_runner=gh)

    assert result.actuated is True
    assert result.reason == "all_predicates_green"
    assert len(gh.mutation_calls()) == 1


def test_unset_variable_policy_keeps_actuator_dormant(tmp_path: Path) -> None:
    policy_path = tmp_path / ".ce" / "state" / "automerge" / "policy.json"
    state = materialize_automerge_policy_state_from_variables(policy_path)
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state,
        checks=GREEN_CHECKS,
        pr_number=313,
        head_sha=HEAD_SHA,
        repo="strange-loop/creator-engine",
        branch="ce-arm-automerge-actuate",
        base="main",
        **canary_identity(),
    )

    gh = FakeActuateGh(check_conclusion="success")
    result = actuate_decision(_write_decision(tmp_path, decision.to_payload()), gh_runner=gh)

    assert result.dormant is True
    assert result.reason == "run_mode_not_armed"
    assert result.acted is False
    assert gh.calls == []


def test_decision_requires_author_approver_separation_for_auto() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=state_with_flags("docs", run_mode="strangeLoop"),
        checks=GREEN_CHECKS,
        author_login="same-dev",
        approver_login="same-dev",
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "author_approver_not_distinct" in decision.rationale


def test_decision_refuses_feature_work_class_outside_canary() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="feature",
        policy_state=state_with_flags("docs", run_mode="strangeLoop"),
        checks=GREEN_CHECKS,
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "work_class_outside_canary" in decision.rationale


def test_run_mode_cli_override_is_advisory_without_class_flag() -> None:
    decision = decide_automerge(
        numstat=numstat_for(["README.md"]),
        paths=["README.md"],
        declared_work_class="tiny",
        policy_state=AutoMergePolicyState.default(),
        checks=GREEN_CHECKS,
        run_mode="strangeLoop",
        **canary_identity(),
    )

    assert decision.run_mode == "strangeLoop"
    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert "class_auto_merge_false" in decision.rationale


def test_automerge_workflows_materialize_policy_before_validator_invocation() -> None:
    decide = _workflow_steps(REPO_ROOT / ".github/workflows/automerge-decide.yml")
    actuate = _workflow_steps(REPO_ROOT / ".github/workflows/automerge-actuate.yml")

    _assert_materialize_step_before(
        decide,
        later_step="Run automerge decision",
    )
    _assert_materialize_step_before(
        actuate,
        later_step="Actuate if ready",
    )


def _workflow_steps(path: Path) -> list[dict]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    jobs = loaded["jobs"]
    assert isinstance(jobs, dict)
    job = next(iter(jobs.values()))
    assert isinstance(job, dict)
    steps = job["steps"]
    assert isinstance(steps, list)
    return steps


def _assert_materialize_step_before(steps: list[dict], *, later_step: str) -> None:
    step_names = [step.get("name") for step in steps]
    materialize_index = step_names.index("Materialize automerge policy")
    assert materialize_index < step_names.index(later_step)
    step = steps[materialize_index]
    assert step["env"] == {
        "CE_AUTOMERGE_RUN_MODE": "${{ vars.CE_AUTOMERGE_RUN_MODE || '' }}",
        "CE_AUTOMERGE_ENABLING_REF": "${{ vars.CE_AUTOMERGE_ENABLING_REF || '' }}",
        "CE_AUTOMERGE_KILL_SWITCH": "${{ vars.CE_AUTOMERGE_KILL_SWITCH || '' }}",
        "CE_AUTOMERGE_TIER_CARRIER_CHANGELOG": "${{ vars.CE_AUTOMERGE_TIER_CARRIER_CHANGELOG || '' }}",
        "CE_AUTOMERGE_TIER_BRAIN_SUPERSEDE": "${{ vars.CE_AUTOMERGE_TIER_BRAIN_SUPERSEDE || '' }}",
    }
    run = step["run"]
    assert "materialize_automerge_policy_state_from_variables" in run
    assert 'Path(".ce/state/automerge/policy.json")' in run
    assert "kill_switch_variable" in run
    assert "tier_carrier_changelog_variable" in run
    assert "tier_brain_supersede_variable" in run


def test_pull_request_paths_use_pr_file_list_not_stale_base_diff(tmp_path: Path) -> None:
    steps = _workflow_steps(REPO_ROOT / ".github/workflows/automerge-decide.yml")
    resolve_step = next(step for step in steps if step.get("name") == "Resolve changed paths")
    run_script = resolve_step["run"]

    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    git("init")
    git("checkout", "-b", "main")
    git("config", "user.email", "ci@example.test")
    git("config", "user.name", "CI")

    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "base")
    stale_base_sha = git("rev-parse", "HEAD")

    github_path = repo / ".github" / "workflows" / "deploy.yml"
    github_path.parent.mkdir(parents=True)
    github_path.write_text("name: deploy\n", encoding="utf-8")
    git("add", ".github/workflows/deploy.yml")
    git("commit", "-m", "main deploy workflow")

    git("checkout", "-b", "docs-pr")
    docs_path = repo / "docs" / "usage.md"
    docs_path.parent.mkdir()
    docs_path.write_text("usage\n", encoding="utf-8")
    git("add", "docs/usage.md")
    git("commit", "-m", "docs update")
    head_sha = git("rev-parse", "HEAD")

    stale_two_dot_paths = git(
        "diff",
        "--name-only",
        "--find-renames",
        f"{stale_base_sha}..{head_sha}",
    ).splitlines()
    assert ".github/workflows/deploy.yml" in stale_two_dot_paths

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    gh_args = fake_bin / "gh-args.txt"
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' \"$@\" > '{gh_args.as_posix()}'\n"
        "if [[ \"$#\" -eq 7 && \"$1\" == 'pr' && \"$2\" == 'view' && \"$3\" == '704' "
        "&& \"$4\" == '--json' && \"$5\" == 'files' && \"$6\" == '--jq' "
        "&& \"$7\" == '.files[].path' ]]; then\n"
        "  printf 'docs/usage.md\\n'\n"
        "  exit 0\n"
        "fi\n"
        "exit 64\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    github_output = tmp_path / "github-output.txt"
    env = {
        **os.environ,
        "EVENT_NAME": "pull_request",
        "GH_TOKEN": "test-token",
        "GITHUB_OUTPUT": str(github_output),
        "GITHUB_SHA": head_sha,
        "MERGE_GROUP_BASE_REF": "",
        "MERGE_GROUP_BASE_SHA": "",
        "MERGE_GROUP_HEAD_REF": "",
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "PR_AUTHOR_LOGIN": "author-dev",
        "PR_BASE_REF": "main",
        "PR_BASE_SHA": stale_base_sha,
        "PR_HEAD_REF": "docs-pr",
        "PR_HEAD_SHA": head_sha,
        "PR_NUMBER": "704",
        "RUNNER_TEMP": str(runner_temp),
    }
    subprocess.run(["bash", "-c", run_script], cwd=repo, env=env, check=True)

    outputs = dict(
        line.split("=", 1)
        for line in github_output.read_text(encoding="utf-8").splitlines()
    )
    resolved_paths = Path(outputs["paths-file"]).read_text(encoding="utf-8").splitlines()

    assert gh_args.read_text(encoding="utf-8").splitlines() == [
        "pr",
        "view",
        "704",
        "--json",
        "files",
        "--jq",
        ".files[].path",
    ]
    assert resolved_paths == ["docs/usage.md"]

    decision = decide_automerge(
        numstat=numstat_for(resolved_paths),
        paths=resolved_paths,
        declared_work_class="tiny",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        **canary_identity(),
    )
    assert decision.mutation_class == "docs"


# ce-621: ADR-0016 §8 non-goal 8 — decisions/ paths must force GESTURE even inside docs_envelope


_DECISIONS_ADR_PATH = "docs/decisions/ADR-9999-x.md"
_DECISIONS_ENVELOPE_PATHS = [
    _DECISIONS_ADR_PATH,
    ".ce/changelog/ce-621-decisions-governance-class.md",
    ".ce/pr-manifests/ce-621-decisions-governance-class.md",
]


def test_decisions_adr_path_classifies_governance_not_docs() -> None:
    """docs/decisions/ADR-9999-x.md must be classified governance by the mutation policy.

    ADR-0016 §8 non-goal 8: ADR / ratification records are governance class, always two-key.
    Precedence: governance rank (5) > docs rank (1) in class_order → governance wins.
    """
    from creator_engine_validator.forge.mutation_classifier import mutation_class_for_paths

    assert mutation_class_for_paths([_DECISIONS_ADR_PATH]) == "governance"


def test_decide_automerge_returns_gesture_for_decisions_adr_even_when_docs_armed() -> None:
    """decide_automerge must return GESTURE when a docs_envelope-shaped PR contains an ADR path.

    Engagement path (automerge_policy.py):
      1. mutation_class_for_paths([...]) → "governance"  (governance rank > docs rank)
      2. mutation_class in GESTURE_CLASSES → True
      3. automerge_policy.py:586 appends "gesture_class" to auto_blockers → GESTURE
    The docs_envelope_tier_matches() predicate still passes for .md under docs/**,
    but mutation-class escalation to governance is what blocks AUTO before tier logic
    can fire (docs_envelope_tier_matches requires mutation_class == "docs" at line 1024).
    """
    decision = decide_automerge(
        numstat=numstat_for(_DECISIONS_ENVELOPE_PATHS),
        paths=_DECISIONS_ENVELOPE_PATHS,
        declared_work_class="XS",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        repo="creator-engine/creator-engine",
        branch="ce-621-decisions-governance-class",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.mutation_class == "governance"
    assert "gesture_class" in decision.rationale


def test_decide_automerge_returns_gesture_for_decisions_adr_with_tiers_armed() -> None:
    """GESTURE is returned even when docs class flag AND docs_envelope tier flag are both True.

    The mutation-class escalation to governance (GESTURE_CLASSES) at
    automerge_policy.py:586 fires before the tier auto-merge path is reached.
    """
    decision = decide_automerge(
        numstat=numstat_for(_DECISIONS_ENVELOPE_PATHS),
        paths=_DECISIONS_ENVELOPE_PATHS,
        declared_work_class="S",
        policy_state=state_with_flags(
            "docs",
            enabled_tiers=(AUTOMERGE_TIER_DOCS_ENVELOPE,),
        ),
        checks=GREEN_CHECKS,
        repo="creator-engine/creator-engine",
        branch="ce-621-decisions-governance-class",
        base="main",
        **canary_identity(),
    )

    assert decision.decision == AUTOMERGE_DECISION_GESTURE
    assert decision.mutation_class == "governance"
    assert "gesture_class" in decision.rationale


def test_plain_docs_guide_still_classifies_docs_and_may_auto() -> None:
    """Regression: plain docs/guide.md must still classify docs (not promoted to governance)."""
    decision = decide_automerge(
        numstat=numstat_for(["docs/guide.md"]),
        paths=["docs/guide.md"],
        declared_work_class="XS",
        policy_state=state_with_flags("docs"),
        checks=GREEN_CHECKS,
        repo="creator-engine/creator-engine",
        branch="ce/docs-guide",
        base="main",
        **canary_identity(),
    )

    assert decision.mutation_class == "docs"
    assert decision.decision == AUTOMERGE_DECISION_AUTO
    assert decision.mutation_class != "deploy"
