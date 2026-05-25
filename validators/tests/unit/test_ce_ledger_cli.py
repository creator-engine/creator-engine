"""Unit tests for the ``ce ledger`` CLI command family (RV1-040/041/042).

Drives ``creator_engine_validator.ce_cli.main`` directly. Asserts the
``ce ledger record`` / ``ce ledger verify`` surface exists, refuses secret and
malformed input non-zero, and leaves all existing ``ce lane`` behavior intact.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
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


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    sel = tmp_path / "side-effect-ledger"
    awl = tmp_path / ".hermes" / "active-work-ledger"
    awl.mkdir(parents=True, exist_ok=True)
    return sel, awl


def _record_argv(tmp_path, sel, awl, **extra):
    argv = [
        "ledger", "record",
        "--controller-id", CONTROLLER,
        "--lane-id", LANE,
        "--claim-ref", f"claims/{CONTROLLER}/{LANE}.yaml",
        "--effect-id", extra.pop("effect_id", "effect-a"),
        "--effect-kind", "tracked_file_change",
        "--effect-status", "succeeded",
        "--summary", "Created a schema file.",
        "--occurred-at", "2026-05-25T12:10:00Z",
        "--repo-root", str(tmp_path),
        "--side-effect-ledger-root", str(sel),
        "--active-work-ledger-root", str(awl),
    ]
    for k, v in extra.items():
        flag = "--" + k.replace("_", "-")
        argv.extend([flag, str(v)])
    return argv


# ---------------------------------------------------------------------------
# --help reachability (argparse wiring)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["ledger", "--help"],
    ["ledger", "record", "--help"],
    ["ledger", "verify", "--help"],
])
def test_ledger_help_is_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# ce ledger record
# ---------------------------------------------------------------------------


def test_ce_ledger_record_appends_a_record(tmp_path):
    sel, awl = _roots(tmp_path)
    _claim(awl)
    ret = ce_cli.main(_record_argv(tmp_path, sel, awl))
    assert ret == 0
    records = list(sel.rglob("*.json"))
    records = [p for p in records if p.name != "_head.json"]
    assert len(records) == 1


def test_ce_ledger_record_refuses_secret_details_nonzero_no_record(tmp_path):
    sel, awl = _roots(tmp_path)
    _claim(awl)
    ret = ce_cli.main(_record_argv(tmp_path, sel, awl, details_json='{"api_token": "sk-abcdef1234567890"}'))
    assert ret != 0
    assert [p for p in sel.rglob("*.json") if p.name != "_head.json"] == []


def test_ce_ledger_record_rejects_non_object_details_json(tmp_path):
    sel, awl = _roots(tmp_path)
    _claim(awl)
    ret = ce_cli.main(_record_argv(tmp_path, sel, awl, details_json="[1, 2, 3]"))
    assert ret != 0


def test_ce_ledger_record_refuses_missing_claim_nonzero(tmp_path):
    sel, awl = _roots(tmp_path)  # no claim written
    ret = ce_cli.main(_record_argv(tmp_path, sel, awl))
    assert ret != 0


# ---------------------------------------------------------------------------
# ce ledger verify
# ---------------------------------------------------------------------------


def test_ce_ledger_verify_ok_after_record(tmp_path):
    sel, awl = _roots(tmp_path)
    _claim(awl)
    assert ce_cli.main(_record_argv(tmp_path, sel, awl, effect_id="effect-a")) == 0
    ret = ce_cli.main([
        "ledger", "verify",
        "--side-effect-ledger-root", str(sel),
        "--active-work-ledger-root", str(awl),
    ])
    assert ret == 0


def test_ce_ledger_verify_json_emits_stable_keys(tmp_path, capsys):
    sel, awl = _roots(tmp_path)
    _claim(awl)
    ce_cli.main(_record_argv(tmp_path, sel, awl, effect_id="effect-a"))
    capsys.readouterr()
    ret = ce_cli.main([
        "ledger", "verify",
        "--side-effect-ledger-root", str(sel),
        "--json",
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    for key in ("ok", "record_count", "chains", "effect_kind_counts", "effect_status_counts"):
        assert key in payload
    assert payload["ok"] is True
    assert payload["record_count"] == 1


def test_ce_ledger_verify_detects_tamper_nonzero(tmp_path):
    sel, awl = _roots(tmp_path)
    _claim(awl)
    ce_cli.main(_record_argv(tmp_path, sel, awl, effect_id="effect-a"))
    ce_cli.main(_record_argv(tmp_path, sel, awl, effect_id="effect-b"))
    first = sorted(p for p in sel.rglob("*.json") if p.name != "_head.json")[0]
    record = json.loads(first.read_text(encoding="utf-8"))
    record["summary"] = "tampered"
    first.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    ret = ce_cli.main([
        "ledger", "verify",
        "--side-effect-ledger-root", str(sel),
    ])
    assert ret != 0


# ---------------------------------------------------------------------------
# Compatibility — ce lane surface unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [["lane", "--help"], ["lane", "launch", "--help"]])
def test_ce_lane_help_still_exits_zero(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0
