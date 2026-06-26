"""Unit tests for the ce-ops#244 governed worker-tier contract."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from creator_engine_validator import worker_spawn
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import worker_tier_contract as chk


def _record(role: str = "implementer") -> dict:
    lane_kind = {"researcher": "read-only", "implementer": "implementation", "reviewer": "review"}[role]
    return {
        "kind": "ce-worker-spawn-record",
        "schema_version": "1",
        "worker_id": f"worker-{role}-123",
        "role": role,
        "lane_kind": lane_kind,
        "harness": "claude",
        "scope_id": "ce-ops#244",
        "parent_id": "ce-dev-1",
        "worktree_path": "/tmp/worker",
        "prompt": {"kind": "brief", "ref": "inline-brief", "sha256": "a" * 64},
        "depth": 1,
        "max_depth": 3,
        "record_path": "/tmp/worker/.ce/state/workers/worker-implementer-123/worker.yaml",
        "launch_command": ["ce", "launch"],
        "launch_command_sha256": "b" * 64,
        "scrubbed_env_names": ["GH_TOKEN"],
        "child_env_names": ["CE_WORKER_ID", "CE_WORKER_ROLE", "HOME", "PATH"],
        "dry_run": False,
        "launch_state": "launched",
        "seat_refs": {"seat_lifecycle_state": "active"},
        "governed_worker_contract": worker_spawn.governed_worker_contract(role=role, max_depth=3),
    }


def _write(tmp_path: Path, record: dict) -> Path:
    path = tmp_path / "worker.yaml"
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _write_repo_record(tmp_path: Path, record: dict) -> Path:
    path = tmp_path / ".ce" / "state" / "workers" / record["worker_id"] / "worker.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _write_role_surface(tmp_path: Path, role: str = "implementer") -> Path:
    ref = chk.ROLE_SURFACE_REFS[role]
    path = tmp_path / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {role}\n", encoding="utf-8")
    return path


def _codes(record: dict, tmp_path: Path) -> set[str]:
    return {err.code for err in chk.validate_worker_tier_contract_file(_write(tmp_path, record))}


def test_check_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_conforming_worker_contract_passes(tmp_path):
    assert chk.validate_worker_tier_contract_file(_write(tmp_path, _record())) == []


def test_repo_context_requires_existing_role_surface_ref(tmp_path):
    record = _record()
    path = _write_repo_record(tmp_path, record)

    assert chk.CODE_SURFACE in {err.code for err in chk.validate_worker_tier_contract_file(path)}

    _write_role_surface(tmp_path)
    assert chk.validate_worker_tier_contract_file(path) == []


def test_direct_record_validation_accepts_explicit_temp_repo_root(tmp_path):
    record = _record("reviewer")
    _write_role_surface(tmp_path, "reviewer")

    assert chk.validate_worker_tier_contract_record(record, tmp_path / "worker.yaml", repo_root=tmp_path) == []


def test_worker_spawn_stamps_governed_contract_for_worker_tier_roles(tmp_path):
    worktree = tmp_path / "worker"
    worktree.mkdir()

    plan = worker_spawn.plan_worker_spawn(
        role="reviewer",
        harness="claude",
        worktree=worktree,
        scope_id="ce-ops#244",
        brief="review without recording this body",
        environ={},
    )

    record = plan.to_record()
    assert record["governed_worker_contract"]["role"] == "reviewer"
    assert record["governed_worker_contract"]["inherited_governance"] == {
        "ring": "ring_1",
        "refusal": "inherited",
        "envelope": "inherited",
        "ambient_credentials": "none",
    }
    assert chk.validate_worker_tier_contract_record(record, tmp_path / "worker.yaml") == []


def test_missing_worker_contract_is_flagged(tmp_path):
    record = _record()
    record.pop("governed_worker_contract")

    assert chk.CODE_SCHEMA in _codes(record, tmp_path)


def test_declared_push_capability_is_flagged(tmp_path):
    record = copy.deepcopy(_record())
    record["governed_worker_contract"]["declared_capabilities"].append("push")

    assert chk.CODE_CAPABILITY in _codes(record, tmp_path)


def test_exceeding_depth_bound_is_flagged(tmp_path):
    record = copy.deepcopy(_record())
    record["depth"] = 4

    assert chk.CODE_BOUNDS in _codes(record, tmp_path)
