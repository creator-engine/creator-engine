"""Unit tests for ``ce brain init`` (ce-ops#206).

Drives ``creator_engine_validator.ce_cli.main`` directly. Each case uses a real
on-disk state root under ``tmp_path`` so the SSOT genesis write, the idempotent
no-op, and the fail-closed refusal on a corrupt ledger are all exercised against
the same code paths a freshly-installed workspace would hit.
"""
from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import brain_runtime, ce_cli


def _state_root(tmp_path: Path) -> Path:
    return tmp_path / ".ce" / "state"


def _init_argv(state_root: Path, *, json_output: bool = False) -> list[str]:
    argv = ["brain", "init", "--state-root", str(state_root)]
    if json_output:
        argv.append("--json")
    return argv


def test_brain_init_creates_valid_genesis_ledger(tmp_path):
    state_root = _state_root(tmp_path)
    path = brain_runtime.ledger_path(state_root)
    assert not path.exists()

    ret = ce_cli.main(_init_argv(state_root))

    assert ret == 0
    assert path.is_file()
    # The whole point: a fresh init must leave a ledger that verifies ok=True so
    # the G3-BRAIN-BOOTSTRAP-REFUSED lane-launch gate passes with no hand step.
    verify = brain_runtime.verify_ledger(state_root)
    assert verify.ok
    assert verify.summary["record_count"] == 1
    assert verify.summary["active_count"] == 1


def test_brain_init_json_reports_created(tmp_path, capsys):
    state_root = _state_root(tmp_path)

    ret = ce_cli.main(_init_argv(state_root, json_output=True))

    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] is True
    assert payload["already_initialized"] is False
    assert payload["record_count"] == 1
    assert payload["genesis_id"] == "brain-assertion-genesis-0001"
    assert payload["ledger_path"] == str(brain_runtime.ledger_path(state_root))


def test_brain_init_is_idempotent_no_op_on_valid_ledger(tmp_path, capsys):
    state_root = _state_root(tmp_path)

    assert ce_cli.main(_init_argv(state_root)) == 0
    path = brain_runtime.ledger_path(state_root)
    first_bytes = path.read_bytes()
    capsys.readouterr()  # drain

    ret = ce_cli.main(_init_argv(state_root, json_output=True))

    assert ret == 0
    # Byte-identical: re-running init must NOT append a duplicate genesis or
    # rewrite the ledger.
    assert path.read_bytes() == first_bytes
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] is False
    assert payload["already_initialized"] is True
    assert payload["record_count"] == 1


def test_brain_init_refuses_corrupt_ledger_without_overwrite(tmp_path, capsys):
    state_root = _state_root(tmp_path)

    assert ce_cli.main(_init_argv(state_root)) == 0
    path = brain_runtime.ledger_path(state_root)

    # Tamper with the genesis record's content hash so the hash chain no longer
    # validates — a corrupt/conflicting ledger must fail closed, not be healed.
    records = brain_runtime.load_records(state_root)
    records[0]["content_hash"] = "0" * 64
    corrupt_text = brain_runtime.serialize_ledger(records)
    path.write_text(corrupt_text, encoding="utf-8")

    ret = ce_cli.main(_init_argv(state_root))

    assert ret != 0
    # Refusal must not overwrite/repair the (corrupt) on-disk ledger.
    assert path.read_text(encoding="utf-8") == corrupt_text
    err = capsys.readouterr().err
    assert "CE-BRAIN-INIT-REFUSED" in err


def test_brain_init_refuses_non_mapping_ledger(tmp_path, capsys):
    state_root = _state_root(tmp_path)
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    ret = ce_cli.main(_init_argv(state_root))

    assert ret != 0
    assert "CE-BRAIN-INIT-REFUSED" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == "- not\n- a\n- mapping\n"


def test_brain_init_then_lane_launch_brain_gate_passes(tmp_path, monkeypatch):
    """Integration: a workspace initialized via ``ce brain init`` passes the
    lane-launch G3 brain bootstrap gate (the same preflight a real launch runs).
    """
    state_root = tmp_path / ".ce" / "state"

    # Sanity: before init the gate refuses (file absent).
    before = brain_runtime.verify_ledger(state_root)
    assert not before.ok

    assert ce_cli.main(_init_argv(state_root)) == 0

    # Reuse the exact preflight the lane-launch CLI runs (ce_cli wires this for
    # `lane launch`): it raises LaneLaunchError when the brain bootstrap is
    # missing/invalid and is a no-op (returns 0) when it is ready.
    args = type("Args", (), {})()
    args.claim_ticket = "creator-engine/ce-ops#206"
    args.repo_root = str(tmp_path)
    args.role = "implementer"

    code = ce_cli._preflight_launch_brain_bootstrap(args, "lane launch")
    assert code == 0
