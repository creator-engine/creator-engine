"""Integration tests for the ``ce ledger`` runtime end-to-end.

Exercises the full ``ce ledger record`` -> ``ce ledger verify`` -> replay flow
through ``ce_cli.main``, including negative paths (tamper, deleted record,
claim mismatch) and ``ce lane`` co-existence.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from creator_engine_validator import ce_cli


CONTROLLER = "hermes-primary"
LANE = "pco-slice4-impl"


def _claim(awl: Path, controller: str = CONTROLLER, lane: str = LANE) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "record_timestamp": f"source-controlled:claims/{controller}/{lane}.yaml",
        "worktree_path": "/worktrees/pco-slice4-impl",
        "envelope_ref": ".hermes/envelopes/pco-slice4.md",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller}/{lane}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller}/{lane}.yaml",
    }
    path = awl / "claims" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _record(tmp_path, sel, awl, effect_id, kind="tracked_file_change", occurred="2026-05-25T12:10:00Z"):
    return ce_cli.main([
        "ledger", "record",
        "--controller-id", CONTROLLER,
        "--lane-id", LANE,
        "--claim-ref", f"claims/{CONTROLLER}/{LANE}.yaml",
        "--effect-id", effect_id,
        "--effect-kind", kind,
        "--effect-status", "succeeded",
        "--summary", f"Effect {effect_id}.",
        "--occurred-at", occurred,
        "--repo-root", str(tmp_path),
        "--side-effect-ledger-root", str(sel),
        "--active-work-ledger-root", str(awl),
    ])


def _ledger_records(sel: Path) -> list[Path]:
    return sorted(p for p in sel.rglob("*.json") if p.name != "_head.json")


def test_record_then_verify_then_replay(tmp_path, capsys):
    sel = tmp_path / "side-effect-ledger"
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)

    assert _record(tmp_path, sel, awl, "effect-a", kind="tracked_file_change") == 0
    assert _record(tmp_path, sel, awl, "effect-b", kind="git_mutation") == 0
    assert _record(tmp_path, sel, awl, "effect-c", kind="github_mutation") == 0
    capsys.readouterr()

    ret = ce_cli.main([
        "ledger", "verify",
        "--side-effect-ledger-root", str(sel),
        "--active-work-ledger-root", str(awl),
        "--json",
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["record_count"] == 3
    assert payload["effect_kind_counts"] == {
        "git_mutation": 1,
        "github_mutation": 1,
        "tracked_file_change": 1,
    }
    chain = payload["chains"][0]
    assert chain["controller_id"] == CONTROLLER
    assert chain["lane_id"] == LANE
    assert chain["record_count"] == 3
    assert chain["first_record_ref"].endswith("000001-effect-a.json")
    assert chain["last_record_ref"].endswith("000003-effect-c.json")


def test_tampered_chain_fails_verify(tmp_path):
    sel = tmp_path / "side-effect-ledger"
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _record(tmp_path, sel, awl, "effect-a")
    _record(tmp_path, sel, awl, "effect-b")
    target = _ledger_records(sel)[0]
    record = json.loads(target.read_text(encoding="utf-8"))
    record["effect_status"] = "failed"
    target.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    assert ce_cli.main(["ledger", "verify", "--side-effect-ledger-root", str(sel)]) != 0


def test_deleted_intermediate_record_fails_verify(tmp_path):
    sel = tmp_path / "side-effect-ledger"
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _record(tmp_path, sel, awl, "effect-a")
    _record(tmp_path, sel, awl, "effect-b")
    _record(tmp_path, sel, awl, "effect-c")
    _ledger_records(sel)[1].unlink()
    assert ce_cli.main(["ledger", "verify", "--side-effect-ledger-root", str(sel)]) != 0


def test_verify_against_missing_claim_root_fails(tmp_path):
    sel = tmp_path / "side-effect-ledger"
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _record(tmp_path, sel, awl, "effect-a")
    empty = tmp_path / "empty-awl"
    empty.mkdir()
    assert ce_cli.main([
        "ledger", "verify",
        "--side-effect-ledger-root", str(sel),
        "--active-work-ledger-root", str(empty),
    ]) != 0


def test_ce_lane_and_ce_ledger_coexist(tmp_path):
    # The ledger group does not disturb the lane group dispatch.
    import pytest

    for argv in (["lane", "verify", "--help"], ["ledger", "verify", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
