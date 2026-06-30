from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import ce_cli
from creator_engine_validator.orchestrator_status import load_status, render_human

SHA256 = "a" * 64
HEAD_SHA = "b" * 40


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _checkpoint() -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-checkpoint",
        "version": 1,
        "checkpoint_id": "checkpoint-001",
        "created_at": "2026-06-28T00:00:00Z",
        "controller_id": "controller-alpha",
        "objective": "Observe Orchestrator runtime state.",
        "lifecycle_state": "WATCH",
        "refs": {
            "issues": ["ce-ops#616"],
            "prs": ["creator-engine#700"],
            "branches": ["ce-orchestrator-cockpit"],
        },
        "active_claims": [
            {
                "claim_ref": "claim-001",
                "worker_id": "worker-alpha",
                "role": "implementer",
                "branch": "ce-orchestrator-cockpit",
                "worktree": "worktree-alpha",
                "containment": "contained",
                "stop_line": "ready-for-harvest",
            }
        ],
        "territory_map_ref": "territory-map-001",
        "gate": {
            "validation": "green",
            "independent_review": "pending",
            "declared_work_class": "M",
            "ratification": "not_required",
        },
        "operator_decisions": ["decision-001"],
        "next_action": "harvest worker output",
    }


def _territory_map() -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-territory-map",
        "version": 1,
        "map_id": "territory-map-001",
        "created_at": "2026-06-28T00:00:01Z",
        "base_ref": "origin/main",
        "entries": [
            {
                "path_pattern": "validators/creator_engine_validator/orchestrator_status.py",
                "owner_worker": "worker-alpha",
                "issue_ref": "ce-ops#616",
                "pr_ref": "creator-engine#700",
                "branch": "ce-orchestrator-cockpit",
                "claim_ref": "claim-001",
                "lock_status": "locked",
                "changed_paths": ["validators/creator_engine_validator/orchestrator_status.py"],
            }
        ],
        "collision_checks": [
            {
                "candidate_ref": "ce-orchestrator-cockpit",
                "result": "clear",
                "reason": "candidate paths are held by the same claim",
            }
        ],
    }


def _harvest_packet() -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-harvest-packet",
        "version": 1,
        "packet_id": "harvest-packet-001",
        "worker_id": "worker-alpha",
        "role": "implementer",
        "brief_ref": ".ce/briefs/ce-orch9-dev4.md",
        "brief_sha256": SHA256,
        "branch": "ce-orchestrator-cockpit",
        "base_ref": "origin/main",
        "head_sha": HEAD_SHA,
        "changed_paths": ["validators/creator_engine_validator/orchestrator_status.py"],
        "diff_summary": "Adds the read-only Orchestrator status cockpit.",
        "evidence": {
            "validation_commands": ["python -m pytest validators/tests/unit/test_orchestrator_status.py"],
            "validation_result": "pass",
            "artifacts": [],
        },
        "stop_line_result": "ready",
        "scope_verdict": "in_scope",
    }


def _operator_decision(status: str = "pending") -> dict[str, object]:
    return {
        "kind": "ce-orchestrator-operator-decision",
        "version": 1,
        "decision_id": "decision-001",
        "created_at": "2026-06-28T00:00:02Z",
        "requested_by": "controller-alpha",
        "authority_basis": "reserved",
        "request": "Choose whether to continue after a reserved action is requested.",
        "options": [
            {
                "id": "hold",
                "label": "Hold",
                "consequence": "No reserved action is taken.",
            }
        ],
        "recommended_option": "hold",
        "halt_until_resolved": True,
        "resolution": {
            "status": status,
            "resolved_by": None,
            "resolved_at": None,
            "notes": None,
        },
    }


def _populate_state(state_dir: Path) -> None:
    _write_json(state_dir / "checkpoints" / "checkpoint-001.json", _checkpoint())
    _write_json(state_dir / "territory-maps" / "territory-map-001.json", _territory_map())
    _write_json(state_dir / "harvest-packets" / "harvest-packet-001.json", _harvest_packet())
    _write_json(state_dir / "operator-decisions" / "decision-001.json", _operator_decision())


def test_load_status_missing_state_dir_is_empty_ok(tmp_path: Path) -> None:
    status = load_status(state_dir=tmp_path / "absent")

    assert status["ok"] is True
    assert status["record_count"] == 0
    assert status["counts"] == {
        "checkpoints": 0,
        "territory_maps": 0,
        "harvest_packets": 0,
        "operator_decisions": 0,
    }
    assert "no orchestrator runtime records found" in render_human(status)


def test_load_status_valid_records_are_grouped_and_summarized(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    _populate_state(state_dir)

    status = load_status(state_dir=state_dir)

    assert status["ok"] is True
    assert status["record_count"] == 4
    assert status["latest"]["checkpoints"]["lifecycle_state"] == "WATCH"
    assert status["latest"]["territory_maps"]["collision_results"] == {"clear": 1}
    assert status["latest"]["harvest_packets"]["validation_result"] == "pass"
    assert status["pending_operator_decisions"][0]["id"] == "decision-001"


def test_cli_status_json_output(tmp_path: Path, capsys) -> None:
    state_dir = tmp_path / "state"
    _populate_state(state_dir)

    rc = ce_cli.main(["orchestrator", "status", "--state-dir", str(state_dir), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["counts"]["operator_decisions"] == 1
    assert payload["latest"]["checkpoints"]["gate"]["validation"] == "green"


def test_cli_status_human_output(tmp_path: Path, capsys) -> None:
    state_dir = tmp_path / "state"
    _populate_state(state_dir)

    rc = ce_cli.main(["orchestrator", "status", "--state-dir", str(state_dir)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "ce orchestrator status: OK (4 record(s))" in out
    assert "latest checkpoint: checkpoint-001 state=WATCH validation=green review=pending" in out
    assert "pending operator decisions: 1" in out


def test_cli_status_invalid_record_reports_without_crashing(tmp_path: Path, capsys) -> None:
    state_dir = tmp_path / "state"
    bad = _checkpoint()
    bad["active_claims"] = "not-a-list"
    _write_json(state_dir / "checkpoints" / "bad.json", bad)

    rc = ce_cli.main(["orchestrator", "status", "--state-dir", str(state_dir), "--json"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["record_count"] == 0
    assert payload["errors"][0]["kind"] == "ce-orchestrator-checkpoint"
    assert "not of type 'array'" in payload["errors"][0]["message"]
