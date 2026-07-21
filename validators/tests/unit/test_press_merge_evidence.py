from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from creator_engine_validator.forge.press_merge_evidence import (
    approval_current_for_head,
    assemble_press_merge_evidence,
    canonical_json_digest,
    head_staleness_status,
)


HEAD = "a" * 40
OTHER_HEAD = "b" * 40


def _decision(**overrides):
    payload = {
        "class": "S",
        "size_band": "target_advisory",
        "minimum_work_class": "S",
        "mutation_class": "code",
        "gates": [],
        "decision": "AUTO",
        "rationale": ["ok"],
        "policy_sha": "c" * 64,
        "checks_snapshot": {"unit": "success"},
        "run_mode": "ceo",
        "kill_switch": False,
        "class_flag": True,
        "enabling_decision_ref": "ratified",
        "reviewDecision": "APPROVED",
        "checks_green": True,
        "pr_number": 294,
        "head_sha": HEAD,
        "repo": "creator-engine/creator-engine",
        "branch": "ce-294-press-merge-bundle",
        "base": "main",
        "required_checks": ["unit"],
        "author_login": "author",
        "approver_login": "reviewer",
    }
    payload.update(overrides)
    return payload


def _bundle(**kwargs):
    return assemble_press_merge_evidence(
        decision_payload=kwargs.pop("decision_payload", _decision()),
        changed_paths=kwargs.pop("changed_paths", ["validators/tests/unit/test_press_merge_evidence.py"]),
        checks_payload=kwargs.pop("checks_payload", {"checks": [{"name": "unit", "state": "SUCCESS"}]}),
        pr_metadata=kwargs.pop(
            "pr_metadata",
            {
                "number": 294,
                "url": "https://github.com/creator-engine/creator-engine/pull/294",
                "title": "press merge evidence",
                "baseRefName": "main",
                "headRefName": "ce-294-press-merge-bundle",
                "headRefOid": HEAD,
                "isDraft": False,
            },
        ),
        approval_witnesses=kwargs.pop(
            "approval_witnesses",
            [
                {
                    "reviewer_login": "reviewer",
                    "commit_oid": HEAD,
                    "state": "APPROVED",
                    "review_id": "R1",
                }
            ],
        ),
        minted_at_utc=kwargs.pop("minted_at_utc", "2026-07-03T00:00:00+00:00"),
        assembler_workflow=kwargs.pop("assembler_workflow", "CE Automerge Decide"),
        assembler_run_id=kwargs.pop("assembler_run_id", "1"),
        assembler_run_attempt=kwargs.pop("assembler_run_attempt", "1"),
        read_repo_sha=kwargs.pop("read_repo_sha", "d" * 40),
        **kwargs,
    )


def test_source_mapping_and_schema_include_tier_b_ledger_fields(repo_root: Path):
    bundle = _bundle()

    field_sources = bundle["provenance"]["field_sources"]
    assert field_sources["/subject/head_sha"] == "live_pr"
    assert field_sources["/decision/payload/head_sha"] == "decision"
    assert field_sources["/validation/validate_pr/available"] == "validate_pr_gap"
    assert field_sources["/tier_b_ledger/old_record_count"] == "tier_b_ledger"
    assert field_sources["/tier_b_ledger/new_record_count"] == "tier_b_ledger"
    assert field_sources["/tier_b_ledger/old_active_count"] == "tier_b_ledger"
    assert field_sources["/tier_b_ledger/new_active_count"] == "tier_b_ledger"
    assert field_sources["/tier_b_ledger/old_head_hash"] == "tier_b_ledger"
    assert field_sources["/tier_b_ledger/new_head_hash"] == "tier_b_ledger"
    assert field_sources["/tier_b_ledger/superseded_assertion_ids"] == "tier_b_ledger"

    schema_path = (
        repo_root
        / "validators"
        / "creator_engine_validator"
        / "schemas"
        / "ce-press-merge-evidence-bundle.v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(bundle)
    verdict_schema = schema["properties"]["summary"]["properties"]["verdict"]
    assert "NON-authority-bearing" in verdict_schema["description"]


def test_stale_head_invalidation():
    assert head_staleness_status(HEAD, HEAD) == "current"
    assert head_staleness_status(HEAD, OTHER_HEAD) == "stale"

    bundle = _bundle(current_head_sha_observed=OTHER_HEAD)

    assert bundle["staleness"] == {
        "valid_for_head_sha": HEAD,
        "current_head_sha_observed": OTHER_HEAD,
        "status": "stale",
    }
    assert bundle["summary"]["verdict"] == "stale"


def test_approval_witness_current_head_logic():
    witnesses = [
        {"reviewer_login": "old", "commit_oid": OTHER_HEAD, "state": "APPROVED", "review_id": "1"},
        {"reviewer_login": "current", "commit_oid": HEAD, "state": "APPROVED", "review_id": "2"},
    ]
    assert approval_current_for_head(witnesses, HEAD)
    assert not approval_current_for_head(witnesses[:1], HEAD)
    assert not approval_current_for_head(
        [{"reviewer_login": "dismissed", "commit_oid": HEAD, "state": "COMMENTED", "review_id": "3"}],
        HEAD,
    )

    bundle = _bundle(approval_witnesses=witnesses[:1])

    assert bundle["approval"]["current_head_approved"] is False
    assert "no approval witness is bound to the bundle head" in bundle["summary"]["reasons"]


def test_missing_optional_validate_pr_evidence_marks_gap():
    bundle = _bundle()

    validate_pr = bundle["validation"]["validate_pr"]
    assert validate_pr["available"] is False
    assert validate_pr["command"] is None
    assert "not accepted as gate evidence" in validate_pr["source_gap"]


def test_canonical_json_digest_stability():
    left = {"z": [3, 2, 1], "a": {"b": True, "c": None}}
    right = {"a": {"c": None, "b": True}, "z": [3, 2, 1]}

    assert canonical_json_digest(left) == canonical_json_digest(right)
