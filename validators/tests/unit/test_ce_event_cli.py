"""Unit tests for the ``ce event`` CLI command family (RV2-003-011..017).

Drives ``creator_engine_validator.ce_cli.main`` directly. Asserts the
``ce event {sign,verify,append,replay,index}`` surface exists, appends a block
under the ignored ``.ce/ce-events/spool/`` root, round-trips append -> verify,
refuses role-floor / write-freeze violations non-zero with the stable code, and
leaves the existing ``ce`` groups intact.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli

RECORDED = "2026-05-30T16:00:00Z"
EVENT_JSON = json.dumps({"kind": "gate_progress", "subject": "G2.003.1", "summary": "cli"})


def _event_root(tmp_path: Path) -> Path:
    root = tmp_path / ".ce" / "ce-events"
    (root / "spool").mkdir(parents=True, exist_ok=True)
    return root


def _append_argv(root: Path, block_id: str, **override) -> list[str]:
    argv = [
        "event", "append",
        "--stream", "demo",
        "--event-root", str(root),
        "--block-id", block_id,
        "--emitting-role", override.get("role", "controller"),
        "--operating-mode", override.get("mode", "strict"),
        "--recorded-at", RECORDED,
        "--event-json", override.get("event_json", EVENT_JSON),
    ]
    if "signature_value" in override:
        argv += ["--signature-value", override["signature_value"]]
    return argv


def _spool(root: Path, stream: str = "demo") -> Path:
    return root / "spool" / stream


def _block_files(root: Path) -> list[Path]:
    return sorted(p for p in _spool(root).glob("*.json") if p.name != "_head.json")


# ---------------------------------------------------------------------------
# --help reachability (argparse wiring)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["event", "--help"],
    ["event", "append", "--help"],
    ["event", "verify", "--help"],
    ["event", "sign", "--help"],
    ["event", "replay", "--help"],
    ["event", "index", "--help"],
])
def test_event_help_is_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# ce event append / verify
# ---------------------------------------------------------------------------


def test_ce_event_append_writes_block(tmp_path):
    root = _event_root(tmp_path)
    assert ce_cli.main(_append_argv(root, "ceevt-demo-0000")) == 0
    assert len(_block_files(root)) == 1


def test_ce_event_append_json_reports_hash_and_sequence(tmp_path, capsys):
    root = _event_root(tmp_path)
    ret = ce_cli.main([*_append_argv(root, "ceevt-demo-0000"), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sequence"] == 0
    assert len(payload["content_hash"]) == 64
    assert payload["parent_hash"] is None


def test_ce_event_append_then_verify_roundtrips(tmp_path):
    root = _event_root(tmp_path)
    assert ce_cli.main(_append_argv(root, "ceevt-demo-0000")) == 0
    assert ce_cli.main(_append_argv(root, "ceevt-demo-0001")) == 0
    assert ce_cli.main(["event", "verify", "--stream", "demo", "--event-root", str(root)]) == 0


def test_ce_event_replay_and_index_exit_zero(tmp_path):
    root = _event_root(tmp_path)
    ce_cli.main(_append_argv(root, "ceevt-demo-0000"))
    assert ce_cli.main(["event", "replay", "--stream", "demo", "--event-root", str(root)]) == 0
    assert ce_cli.main(["event", "index", "--stream", "demo", "--event-root", str(root)]) == 0


# ---------------------------------------------------------------------------
# ce event append — fail-closed refusals (non-zero, no block written)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["agent_ratifier", "source"])
def test_ce_event_append_refuses_role_floor_nonzero(tmp_path, role):
    root = _event_root(tmp_path)
    ret = ce_cli.main(_append_argv(root, "ceevt-demo-0000", role=role))
    assert ret != 0
    assert _block_files(root) == []


def test_ce_event_append_refuses_unknown_mode_nonzero(tmp_path):
    root = _event_root(tmp_path)
    ret = ce_cli.main(_append_argv(root, "ceevt-demo-0000", mode="hyperdrive"))
    assert ret != 0
    assert _block_files(root) == []


def test_ce_event_append_refuses_write_freeze_nonzero(tmp_path):
    root = _event_root(tmp_path)
    event_json = json.dumps(
        {"kind": "gate_progress", "subject": "G2.003.1", "summary": "cli",
         "payload": {"target": ".hermes/ce-events/x.ce.yml"}}
    )
    ret = ce_cli.main(_append_argv(root, "ceevt-demo-0000", event_json=event_json))
    assert ret != 0
    assert _block_files(root) == []


def test_ce_event_append_refuses_nonreserved_signature_nonzero(tmp_path):
    root = _event_root(tmp_path)
    ret = ce_cli.main(_append_argv(root, "ceevt-demo-0000", signature_value="active"))
    assert ret != 0
    assert _block_files(root) == []


def test_ce_event_append_reports_stable_code_on_stderr(tmp_path, capsys):
    root = _event_root(tmp_path)
    ce_cli.main(_append_argv(root, "ceevt-demo-0000", role="agent_ratifier"))
    err = capsys.readouterr().err
    assert "G2-EVENT-ROLE-FLOOR" in err


def test_ce_event_verify_detects_tampered_chain_nonzero(tmp_path):
    root = _event_root(tmp_path)
    ce_cli.main(_append_argv(root, "ceevt-demo-0000"))
    block = _block_files(root)[0]
    data = json.loads(block.read_text(encoding="utf-8"))
    data["content_hash"] = "0" * 64
    block.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    assert ce_cli.main(["event", "verify", "--stream", "demo", "--event-root", str(root)]) != 0


# ---------------------------------------------------------------------------
# ce event sign
# ---------------------------------------------------------------------------


def test_ce_event_sign_emits_signed_block(tmp_path, capsys):
    draft = {
        "block_id": "ceevt-demo-0000",
        "sequence": 0,
        "parent_hash": None,
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": RECORDED,
        "event": {"kind": "gate_progress", "subject": "G2.003.1", "summary": "cli"},
    }
    ret = ce_cli.main(["event", "sign", "--block-json", json.dumps(draft), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["signature"]["value"] == "reserved-inactive"
    assert len(payload["content_hash"]) == 64


# ---------------------------------------------------------------------------
# Compatibility — existing ce groups unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["lane", "--help"],
    ["ledger", "--help"],
    ["worker", "--help"],
    ["fanin", "--help"],
    ["queue", "--help"],
    ["check", "--help"],
    ["doctor", "--help"],
    ["init", "--help"],
    ["launch", "--help"],
    ["hud", "--help"],
])
def test_existing_groups_help_still_exits_zero(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0
