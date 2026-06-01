"""Unit tests for the G2.006.0 extension + hook contract validator.

Covers schema/enum rejection, the three-ring coherence invariant (the headline rule),
role/mode floors, secret + inline-metadata refusal, and that the contract can describe
the committed CC-G-C hook-pack. Offline.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks import extension_hook_contract as e
from creator_engine_validator.checks import registered_checks


def _valid(**override) -> dict:
    rec = {
        "extension_id": "ext-ce-claude-hook-pack",
        "extension_kind": "hook_pack",
        "ring": "ring_1",
        "enforcement_strength": "defeasible",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "hooks": [
            {
                "event": "PreToolUse",
                "matcher": "Edit|Write|MultiEdit|Read|Bash",
                "decision_protocol": "allow_deny",
                "failure_posture": "fail_open",
                "validator_binding": "hook-check",
                "defeasible": True,
            }
        ],
        "recorded_at": "2026-06-01T07:44:19Z",
    }
    rec.update(override)
    return rec


def _write(tmp_path: Path, rec: dict, name: str = "x.ce.yml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump({"extension_contract": rec}), encoding="utf-8")
    return p


def _codes(tmp_path: Path, rec: dict) -> set[str]:
    return {err.code for err in e.validate_extension_contract_file(_write(tmp_path, rec))}


def test_check_is_registered():
    assert "extension_hook_contract" in registered_checks()


def test_valid_contract_passes(tmp_path):
    assert e.validate_extension_contract_file(_write(tmp_path, _valid())) == []


def test_unknown_ring_rejected(tmp_path):
    assert "VAL-EXT-RING" in _codes(tmp_path, _valid(ring="ring_3"))


def test_unknown_kind_rejected(tmp_path):
    assert "VAL-EXT-KIND" in _codes(tmp_path, _valid(extension_kind="plugin"))


def test_unknown_hook_event_rejected(tmp_path):
    rec = _valid(hooks=[{"event": "OnFire", "decision_protocol": "allow_deny", "failure_posture": "fail_open", "defeasible": True}])
    assert "VAL-EXT-HOOK" in _codes(tmp_path, rec)


# --- the three-ring coherence invariant (headline rule) ---------------------
def test_hard_outside_ring0_rejected(tmp_path):
    # hard enforcement at ring_2 (not ring_0) -> coherence violation
    assert "VAL-EXT-RING-COHERENCE" in _codes(tmp_path, _valid(ring="ring_2", enforcement_strength="hard"))


def test_ring1_claims_hard_rejected(tmp_path):
    assert "VAL-EXT-RING-COHERENCE" in _codes(tmp_path, _valid(ring="ring_1", enforcement_strength="hard"))


def test_ring1_nondefeasible_hook_rejected(tmp_path):
    rec = _valid(hooks=[{"event": "PreToolUse", "decision_protocol": "allow_deny", "failure_posture": "fail_open", "defeasible": False}])
    assert "VAL-EXT-RING-COHERENCE" in _codes(tmp_path, rec)


def test_ring1_failclosed_hook_rejected(tmp_path):
    rec = _valid(hooks=[{"event": "PreToolUse", "decision_protocol": "allow_deny", "failure_posture": "fail_closed", "defeasible": True}])
    assert "VAL-EXT-RING-COHERENCE" in _codes(tmp_path, rec)


def test_ring0_hard_is_coherent(tmp_path):
    # hard enforcement at ring_0 is the one allowed place
    rec = _valid(ring="ring_0", enforcement_strength="hard",
                 hooks=[{"event": "SessionStart", "decision_protocol": "advisory", "failure_posture": "fail_closed", "defeasible": False}])
    assert e.validate_extension_contract_file(_write(tmp_path, rec)) == []


# --- floors -----------------------------------------------------------------
def test_reserved_ratifier_role_rejected(tmp_path):
    assert "VAL-EXT-ROLE" in _codes(tmp_path, _valid(emitting_role="agent_ratifier"))


def test_unknown_operating_mode_rejected(tmp_path):
    assert "VAL-EXT-MODE" in _codes(tmp_path, _valid(operating_mode="yolo"))


def test_secret_value_rejected(tmp_path):
    assert "VAL-EXT-SECRET" in _codes(tmp_path, _valid(metadata={"token": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"}))


def test_inline_metadata_in_markdown_rejected(tmp_path):
    md = tmp_path / "extension-hook-contract" / "note.md"
    md.parent.mkdir(parents=True)
    md.write_text("# note\n\n```yaml\nextension_contract:\n  extension_id: ext-inline\n```\n", encoding="utf-8")
    codes = {err.code for err in e.validate_extension_contract_file(md)}
    assert "VAL-EXT-NO-INLINE" in codes


def test_check_imports_no_other_feature_runtime():
    import ast

    tree = ast.parse(Path(e.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = node.module or ""
            imported.add(base)
            imported.update(f"{base}.{n.name}" for n in node.names)
        elif isinstance(node, ast.Import):
            imported.update(n.name for n in node.names)
    assert not any(("pcl" in m or "ce_event" in m or "distributed_identity" in m or "connector_runtime" in m) for m in imported), imported
