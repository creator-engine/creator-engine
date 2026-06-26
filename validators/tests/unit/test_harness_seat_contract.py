"""Unit tests for the G2.007.0 harness seat-contract validator.

Covers schema/harness/posture rejection, the refused-modes floor, the full-permission-mode
invariant + the harness-specific permission_mode_flag binding (the headline rules), the
required-hook-pack reuse of G2.006.0, the role/mode/secret/inline floors, and that the
contract describes the committed Claude Code seat. Offline.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks import harness_seat_contract as h
from creator_engine_validator.checks import registered_checks


def _valid() -> dict:
    return {
        "seat_id": "seat-ce-claude-controller",
        "harness": "claude_code",
        "launch_posture": {
            "model_pin": True,
            "effort": "high",
            "setting_sources": ["project"],
            "terminal_visibility": "operator_visible",
            "strict_mcp_config": True,
            "full_permission_mode": True,
            "permission_mode_flag": "--dangerously-skip-permissions",
            "ring0_hook_pack_confirmed": True,
        },
        "refused_modes": ["bare", "print_headless", "background_agents", "remote_control", "settings_local_weakening"],
        "enforcement_ring": "ring_0",
        "foreman_dispatch": {
            "launch_pinned": True,
            "contract_ref": "docs/contracts/harness-seat-contract.md",
            "roles": {
                "researcher": {
                    "dispatch_capability": "multi_agent researcher dispatch",
                    "dispatch_surface": ["multi_agent.researcher"],
                },
                "implementer": {
                    "dispatch_capability": "multi_agent implementer dispatch",
                    "dispatch_surface": ["multi_agent.implementer"],
                },
                "reviewer": {
                    "dispatch_capability": "multi_agent reviewer dispatch",
                    "dispatch_surface": ["multi_agent.reviewer"],
                },
            },
        },
        "required_hook_pack": {
            "extension_id": "ext-ce-claude-hook-pack",
            "extension_kind": "hook_pack",
            "ring": "ring_1",
            "enforcement_strength": "defeasible",
            "emitting_role": "controller",
            "operating_mode": "strict",
            "hooks": [
                {"event": "PreToolUse", "matcher": "Bash", "decision_protocol": "allow_deny", "failure_posture": "fail_open", "validator_binding": "hook-check", "defeasible": True}
            ],
            "recorded_at": "2026-06-01T09:03:02Z",
        },
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T09:03:02Z",
    }


def _write(tmp_path: Path, rec: dict, name: str = "x.ce.yml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump({"seat_contract": rec}), encoding="utf-8")
    return p


def _codes(tmp_path: Path, mutate) -> set[str]:
    rec = copy.deepcopy(_valid())
    mutate(rec)
    return {err.code for err in h.validate_seat_contract_file(_write(tmp_path, rec))}


def test_check_is_registered():
    assert "harness_seat_contract" in registered_checks()


def test_valid_seat_contract_passes(tmp_path):
    assert h.validate_seat_contract_file(_write(tmp_path, _valid())) == []


def test_unknown_harness_rejected(tmp_path):
    assert "VAL-SEAT-HARNESS" in _codes(tmp_path, lambda r: r.update(harness="jenkins"))


@pytest.mark.parametrize("mutate", [
    lambda r: r["launch_posture"].update(setting_sources=["project", "local"]),
    lambda r: r["launch_posture"].update(setting_sources=["user"]),
    lambda r: r["launch_posture"].update(strict_mcp_config=False),
    lambda r: r["launch_posture"].update(terminal_visibility="hidden"),
    lambda r: r["launch_posture"].update(model_pin=False),
    lambda r: r.update(enforcement_ring="ring_1"),
])
def test_weakened_posture_rejected(tmp_path, mutate):
    assert "VAL-SEAT-POSTURE" in _codes(tmp_path, mutate)


def test_missing_refused_mode_rejected(tmp_path):
    assert "VAL-SEAT-PROHIBITED" in _codes(tmp_path, lambda r: r.update(refused_modes=["print_headless", "background_agents", "remote_control", "settings_local_weakening"]))


# --- the headline full-permission rules ---
def test_full_permission_without_ring0_rejected(tmp_path):
    assert "VAL-SEAT-FULL-PERMISSION" in _codes(tmp_path, lambda r: r["launch_posture"].update(ring0_hook_pack_confirmed=False))


def test_full_permission_off_does_not_require_ring0(tmp_path):
    # full_permission_mode false: ring0 confirmation not required (no VAL-SEAT-FULL-PERMISSION).
    codes = _codes(tmp_path, lambda r: r["launch_posture"].update(full_permission_mode=False, ring0_hook_pack_confirmed=False))
    assert "VAL-SEAT-FULL-PERMISSION" not in codes


def test_claude_code_wrong_flag_rejected(tmp_path):
    assert "VAL-SEAT-PERMISSION-FLAG" in _codes(tmp_path, lambda r: r["launch_posture"].update(permission_mode_flag="--yolo"))


def test_codex_seat_binds_yolo(tmp_path):
    # A codex seat in full-permission mode must declare --yolo; the correct flag passes.
    def to_codex(r):
        r.update(seat_id="seat-codex-controller", harness="codex")
        r["launch_posture"].update(permission_mode_flag="--yolo")
    assert "VAL-SEAT-PERMISSION-FLAG" not in _codes(tmp_path, to_codex)


def test_hermes_binds_profile_flag(tmp_path):
    # G2.007.1: a hermes seat in full_permission_mode binds --profile creator-engine (Hermes
    # realizes full-permission via its pinned governed profile; the --yolo approval-bypass is
    # REFUSED, HM-D-2). The wrong flag is rejected; the bound flag passes.
    def to_hermes_wrong(r):
        r.update(seat_id="seat-hermes-controller", harness="hermes")
        r["launch_posture"].update(permission_mode_flag="--yolo")
    assert "VAL-SEAT-PERMISSION-FLAG" in _codes(tmp_path, to_hermes_wrong)

    def to_hermes_ok(r):
        r.update(seat_id="seat-hermes-controller", harness="hermes")
        r["launch_posture"].update(permission_mode_flag="--profile creator-engine")
    assert "VAL-SEAT-PERMISSION-FLAG" not in _codes(tmp_path, to_hermes_ok)


def test_openclaw_seam_no_flag_passes(tmp_path):
    # G2.007.1: openclaw is a SEAM (never in-seat) — full_permission_mode: false, no flag bound.
    # Such a seat is fully valid (no VAL-SEAT-PERMISSION-FLAG, no VAL-SEAT-FULL-PERMISSION).
    def to_openclaw(r):
        r.update(seat_id="seat-openclaw-seam", harness="openclaw")
        r["launch_posture"].update(full_permission_mode=False, ring0_hook_pack_confirmed=False)
        r["launch_posture"].pop("permission_mode_flag", None)
    assert _codes(tmp_path, to_openclaw) == set()


# --- deterministic foreman dispatch (ce-ops#163) ---
def test_missing_foreman_dispatch_rejected(tmp_path):
    assert "VAL-SEAT-FOREMAN-DISPATCH" in _codes(tmp_path, lambda r: r.pop("foreman_dispatch"))


def test_unpinned_foreman_dispatch_rejected(tmp_path):
    assert "VAL-SEAT-FOREMAN-DISPATCH" in _codes(tmp_path, lambda r: r["foreman_dispatch"].update(launch_pinned=False))


@pytest.mark.parametrize("mutate", [
    lambda r: r["foreman_dispatch"]["roles"].pop("reviewer"),
    lambda r: r["foreman_dispatch"]["roles"]["implementer"].update(dispatch_surface=[]),
    lambda r: r["foreman_dispatch"]["roles"]["researcher"].update(dispatch_capability=""),
])
def test_incomplete_foreman_dispatch_rejected(tmp_path, mutate):
    assert "VAL-SEAT-FOREMAN-DISPATCH" in _codes(tmp_path, mutate)


# --- required hook-pack (G2.006.0 reuse) ---
def test_nondefeasible_hookpack_rejected(tmp_path):
    assert "VAL-SEAT-HOOKPACK" in _codes(tmp_path, lambda r: r["required_hook_pack"]["hooks"][0].update(defeasible=False))


def test_non_ring1_hookpack_rejected(tmp_path):
    assert "VAL-SEAT-HOOKPACK" in _codes(tmp_path, lambda r: r["required_hook_pack"].update(ring="ring_0"))


def test_wrong_kind_hookpack_rejected(tmp_path):
    assert "VAL-SEAT-HOOKPACK" in _codes(tmp_path, lambda r: r["required_hook_pack"].update(extension_kind="connector"))


# --- floors ---
def test_reserved_role_rejected(tmp_path):
    assert "VAL-SEAT-ROLE" in _codes(tmp_path, lambda r: r.update(emitting_role="agent_ratifier"))


def test_unknown_mode_rejected(tmp_path):
    assert "VAL-SEAT-MODE" in _codes(tmp_path, lambda r: r.update(operating_mode="yolo"))


def test_secret_value_rejected(tmp_path):
    assert "VAL-SEAT-SECRET" in _codes(tmp_path, lambda r: r.setdefault("metadata", {}).update(token="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"))


def test_inline_metadata_in_markdown_rejected(tmp_path):
    md = tmp_path / "harness-seat-contract" / "note.md"
    md.parent.mkdir(parents=True)
    md.write_text("# note\n\n```yaml\nseat_contract:\n  seat_id: seat-inline\n```\n", encoding="utf-8")
    assert "VAL-SEAT-NO-INLINE" in {err.code for err in h.validate_seat_contract_file(md)}
