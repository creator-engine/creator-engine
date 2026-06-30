from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from creator_engine_validator.orchestrator_records import validate_orchestrator_record

SHA256 = "a" * 64
HEAD_SHA = "b" * 40


def _checkpoint() -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-checkpoint",
        "version": 1,
        "checkpoint_id": "checkpoint-001",
        "created_at": "2026-06-28T00:00:00Z",
        "controller_id": "controller-dev4",
        "objective": "Ship Orchestrator runtime record schemas",
        "lifecycle_state": "CHECKPOINT",
        "refs": {
            "issues": ["ce-ops#616"],
            "prs": ["creator-engine#1"],
            "branches": ["ce-orchestrator-record-schemas"],
        },
        "active_claims": [
            {
                "claim_ref": "claim-001",
                "worker_id": "worker-dev4",
                "role": "implementer",
                "branch": "ce-orchestrator-record-schemas",
                "worktree": "/tmp/ce-orchestrator-record-schemas",
                "containment": "contained",
                "stop_line": "ready-for-harvest",
            }
        ],
        "territory_map_ref": "territory-map-001",
        "gate": {
            "validation": "pending",
            "independent_review": "missing",
            "declared_work_class": "M",
            "ratification": "not_required",
        },
        "operator_decisions": ["decision-001"],
        "next_action": "run validate-pr",
    }


def _territory_map() -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-territory-map",
        "version": 1,
        "map_id": "territory-map-001",
        "created_at": "2026-06-28T00:00:00Z",
        "base_ref": "origin/main",
        "entries": [
            {
                "path_pattern": "validators/creator_engine_validator/schemas/orchestrator-*.schema.yaml",
                "owner_worker": "worker-dev4",
                "issue_ref": "ce-ops#616",
                "pr_ref": "none-yet",
                "branch": "ce-orchestrator-record-schemas",
                "claim_ref": "claim-001",
                "lock_status": "locked",
                "changed_paths": ["validators/creator_engine_validator/orchestrator_records.py"],
            }
        ],
        "collision_checks": [
            {
                "candidate_ref": "ce-orchestrator-record-schemas",
                "result": "clear",
                "reason": "target paths are absent at base",
            }
        ],
    }


def _harvest_packet() -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-harvest-packet",
        "version": 1,
        "packet_id": "harvest-packet-001",
        "worker_id": "worker-dev4",
        "role": "implementer",
        "brief_ref": ".ce/briefs/ce-orch-schemas-dev4.md",
        "brief_sha256": SHA256,
        "branch": "ce-orchestrator-record-schemas",
        "base_ref": "83907bb7ff14b453c149caebca6bc4231adb8efd",
        "head_sha": HEAD_SHA,
        "changed_paths": ["validators/tests/unit/test_orchestrator_records.py"],
        "diff_summary": "Adds Orchestrator runtime record schemas and tests.",
        "evidence": {
            "validation_commands": ["python -m pytest validators/tests/unit/test_orchestrator_records.py"],
            "validation_result": "pass",
            "artifacts": [],
        },
        "stop_line_result": "ready",
        "scope_verdict": "in_scope",
    }


def _operator_decision() -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-operator-decision",
        "version": 1,
        "decision_id": "decision-001",
        "created_at": "2026-06-28T00:00:00Z",
        "requested_by": "controller-dev4",
        "authority_basis": "reserved",
        "request": "Resolve reserved publish authority.",
        "options": [
            {
                "id": "hold",
                "label": "Hold",
                "consequence": "No publish action is taken.",
            },
            {
                "id": "approve",
                "label": "Approve",
                "consequence": "Controller may proceed after all gates pass.",
            },
        ],
        "recommended_option": "hold",
        "halt_until_resolved": True,
        "resolution": {
            "status": "pending",
            "resolved_by": None,
            "resolved_at": None,
            "notes": None,
        },
    }


@pytest.mark.parametrize(
    ("kind", "record"),
    [
        ("ce-orchestrator-checkpoint", _checkpoint()),
        ("ce-orchestrator-territory-map", _territory_map()),
        ("ce-orchestrator-harvest-packet", _harvest_packet()),
        ("ce-orchestrator-operator-decision", _operator_decision()),
    ],
)
def test_orchestrator_record_valid_examples_pass(kind: str, record: dict[str, object]):
    validate_orchestrator_record(kind, record)


@pytest.mark.parametrize(
    ("kind", "record", "mutation"),
    [
        ("ce-orchestrator-checkpoint", _checkpoint(), lambda r: r.pop("checkpoint_id")),
        ("ce-orchestrator-territory-map", _territory_map(), lambda r: r.__setitem__("entries", "not-a-list")),
        ("ce-orchestrator-harvest-packet", _harvest_packet(), lambda r: r.__setitem__("brief_sha256", "bad")),
        (
            "ce-orchestrator-operator-decision",
            _operator_decision(),
            lambda r: r.__setitem__("halt_until_resolved", "yes"),
        ),
    ],
)
def test_orchestrator_record_invalid_examples_raise(kind: str, record: dict[str, object], mutation):
    invalid = deepcopy(record)
    mutation(invalid)

    with pytest.raises(JsonSchemaValidationError):
        validate_orchestrator_record(kind, invalid)


def test_validate_orchestrator_record_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown orchestrator record kind"):
        validate_orchestrator_record("ce-orchestrator-unknown", {})
