from __future__ import annotations

import json
import os
from pathlib import Path

from creator_engine_validator import ce_cli
from creator_engine_validator import controller_posture


def test_posture_json_emits_required_fields(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: True)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: True)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: True)
    monkeypatch.setenv("CE_RING0_CONFIRMED", "true")
    monkeypatch.setenv("CE_RING1_ACTIVE", "true")
    monkeypatch.setenv("CE_RING2_CLOSEOUT_SUPPORT", "true")
    monkeypatch.setenv("CE_CREDENTIAL_SCRUB_STATUS", "clean")
    monkeypatch.setenv("CE_REMOTE_CONTROL_STATUS", "brokered")
    monkeypatch.setenv("CE_APPROVAL_WALL_ARMED", "true")
    monkeypatch.setenv("CE_SIGNING_DEPUTY_STATUS", "openbao-backed")

    rc = ce_cli.main(
        [
            "posture",
            "--repo-root",
            str(tmp_path),
            "--role",
            "controller",
            "--harness",
            "codex",
            "--launch-mode",
            "governed",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert list(payload) == list(controller_posture.FIELD_ORDER)
    assert payload == {
        "role": "controller",
        "harness": "codex",
        "launch_mode": "governed",
        "ring0_confirmed": True,
        "ring1_active": True,
        "ring2_closeout_support": True,
        "credential_scrub_status": "clean",
        "remote_control_status": "brokered",
        "approval_wall_armed": True,
        "signing_deputy_status": "openbao-backed",
        "allowed_posture": "gate-capable",
    }


def test_posture_text_is_stable_and_read_only(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: True)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: True)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: False)
    monkeypatch.setenv("CE_RING2_CLOSEOUT_SUPPORT", "false")
    monkeypatch.setenv("CE_REMOTE_CONTROL_STATUS", "disabled")
    monkeypatch.setenv("CE_APPROVAL_WALL_ARMED", "false")
    monkeypatch.setenv("CE_SIGNING_DEPUTY_STATUS", "unavailable")

    rc = ce_cli.main(
        [
            "posture",
            "--repo-root",
            str(tmp_path),
            "--role",
            "foreman",
            "--harness",
            "claude",
            "--launch-mode",
            "governed",
        ]
    )

    assert rc == 0
    assert capsys.readouterr().out == (
        "CE controller posture\n"
        "role: foreman\n"
        "harness: claude\n"
        "launch_mode: governed\n"
        "ring0_confirmed: true\n"
        "ring1_active: true\n"
        "ring2_closeout_support: false\n"
        "credential_scrub_status: not-applicable\n"
        "remote_control_status: disabled\n"
        "approval_wall_armed: false\n"
        "signing_deputy_status: unavailable\n"
        "allowed_posture: foreman\n"
    )
    assert not any(tmp_path.iterdir())


def test_invalid_status_env_values_fall_back_to_safe_defaults(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: False)
    monkeypatch.setenv("CE_RING0_CONFIRMED", "false")
    monkeypatch.setenv("CE_RING1_ACTIVE", "false")
    monkeypatch.setenv("CE_CREDENTIAL_SCRUB_STATUS", "secret-looking freeform text")
    monkeypatch.setenv("CE_REMOTE_CONTROL_STATUS", "wide-open")
    monkeypatch.setenv("CE_SIGNING_DEPUTY_STATUS", "root-key")

    banner = controller_posture.collect_posture(
        repo_root=tmp_path,
        environ=dict(os.environ),
        role="controller",
        harness="codex",
    )

    assert banner.credential_scrub_status == "unknown"
    assert banner.remote_control_status == "disabled"
    assert banner.signing_deputy_status == "unavailable"
    assert banner.allowed_posture == "read-only"


def test_unknown_signing_deputy_does_not_yield_gate_capable(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: True)
    monkeypatch.setenv("CE_SIGNING_DEPUTY_STATUS", "unknown")

    banner = controller_posture.collect_posture(
        repo_root=tmp_path,
        environ=dict(os.environ),
        role="controller",
        harness="codex",
    )

    assert banner.approval_wall_armed is True
    assert banner.signing_deputy_status == "unknown"
    assert banner.allowed_posture == "read-only"


def test_env_true_cannot_assert_ring_or_wall_state(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: False)
    monkeypatch.setenv("CE_RING0_CONFIRMED", "true")
    monkeypatch.setenv("CE_RING1_ACTIVE", "true")
    monkeypatch.setenv("CE_APPROVAL_WALL_ARMED", "true")
    monkeypatch.setenv("CE_SIGNING_DEPUTY_STATUS", "openbao-backed")

    banner = controller_posture.collect_posture(
        repo_root=tmp_path,
        environ=dict(os.environ),
        role="controller",
        harness="codex",
    )

    assert banner.ring0_confirmed is False
    assert banner.ring1_active is False
    assert banner.approval_wall_armed is False
    assert banner.allowed_posture == "read-only"


def test_missing_hook_pack_degrades_to_read_only(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: True)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: False)

    banner = controller_posture.collect_posture(
        repo_root=tmp_path,
        environ={},
        role="controller",
        harness="claude",
    )

    assert banner.ring0_confirmed is True
    assert banner.ring1_active is False
    assert banner.allowed_posture == "read-only"


def test_disabled_approval_wall_degrades_from_gate_capable(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: True)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: True)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: True)
    monkeypatch.setenv("CE_APPROVAL_WALL_ARMED", "false")
    monkeypatch.setenv("CE_SIGNING_DEPUTY_STATUS", "openbao-backed")

    banner = controller_posture.collect_posture(
        repo_root=tmp_path,
        environ=dict(os.environ),
        role="controller",
        harness="codex",
    )

    assert banner.ring0_confirmed is True
    assert banner.ring1_active is True
    assert banner.approval_wall_armed is False
    assert banner.allowed_posture == "foreman"


def test_codex_credential_scrub_defaults_to_unknown_without_evidence(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(controller_posture, "_ring0_confirmed", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_ring1_active", lambda *, harness, repo_root: False)
    monkeypatch.setattr(controller_posture, "_approval_wall_armed", lambda repo_root: False)

    banner = controller_posture.collect_posture(
        repo_root=tmp_path,
        environ={},
        role="controller",
        harness="codex",
    )

    assert banner.credential_scrub_status == "unknown"
