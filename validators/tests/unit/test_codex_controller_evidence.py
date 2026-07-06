from __future__ import annotations

from pathlib import Path

from creator_engine_validator import codex_controller_evidence as evidence


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def _complete_payload() -> dict:
    return {
        "kind": evidence.PACKET_KIND,
        "schema_version": evidence.SCHEMA_VERSION,
        "generated_at": "2026-07-06T17:30:00Z",
        "host_id": "host-a",
        "harness": "codex",
        "argv_after_rewrite": ["env", "CE_CONTROLLER_ROLE=read-only", "/bin/codex"],
        "managed_hook_confirmed": {"confirmed": True, "sha": HEX_C},
        "cdxd_result": {"ok": True, "bypass_mode": "config", "refusals": []},
        "bypass_mode_source": "config",
        "remote_control_status": "disabled",
        "hook_requirements_sha": HEX_A,
        "hook_script_sha": HEX_B,
        "lifecycle_sentinel_refs": ["/tmp/events.jsonl", "/tmp/sentinel-wrapper.sh"],
        "ring1_smoke_result": {"status": "pass"},
        "known_gaps": [],
    }


def test_absent_packet_fails_closed(tmp_path: Path):
    result = evidence.read_packet(tmp_path, host_id="host-a")

    assert result.status == "absent"
    assert result.ok is False
    assert result.path == evidence.packet_path(tmp_path, host_id="host-a")


def test_incomplete_packet_reports_missing_field_class():
    payload = _complete_payload()
    payload.pop("ring1_smoke_result")

    result = evidence.validate_packet(payload, host_id="host-a")

    assert result.status == "incomplete"
    assert "ring1_smoke_result" in result.missing_field_classes


def test_managed_hook_confirmed_requires_bool_and_sha():
    payload = _complete_payload()
    payload["managed_hook_confirmed"] = {"confirmed": True}

    result = evidence.validate_packet(payload, host_id="host-a")

    assert result.status == "incomplete"
    assert "managed_hook_confirmed" in result.missing_field_classes


def test_packet_host_id_is_bound_to_current_host():
    result = evidence.validate_packet(_complete_payload(), host_id="host-b")

    assert result.status == "incomplete"
    assert "host_id" in result.missing_field_classes


def test_each_required_field_class_is_fail_closed():
    for field in evidence.REQUIRED_FIELD_CLASSES:
        payload = _complete_payload()
        payload.pop(field)

        result = evidence.validate_packet(payload, host_id="host-a")

        assert result.status == "incomplete", field
        assert field in result.missing_field_classes


def test_build_packet_records_missing_codex_closeout_hook_gap(tmp_path: Path):
    requirements = tmp_path / ".codex" / "requirements.toml"
    script = tmp_path / ".codex" / "hooks" / "ce-pretooluse-codex.py"
    requirements.parent.mkdir(parents=True)
    script.parent.mkdir(parents=True)
    requirements.write_text("[features]\nhooks = true\n", encoding="utf-8")
    script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    script.chmod(0o755)

    packet = evidence.build_packet(
        repo_root=tmp_path,
        host_id="host-a",
        argv_after_rewrite=["env", "/bin/codex"],
        managed_hook_confirmed=True,
        cdxd_result={"ok": True, "refusals": []},
        bypass_mode_source="config",
        remote_control_status="disabled",
        lifecycle_sentinel_refs=["events.jsonl", "sentinel-wrapper.sh"],
        ring1_smoke_result={"status": "pass"},
    )

    assert packet["hook_requirements_sha"]
    assert packet["hook_script_sha"]
    assert packet["managed_hook_confirmed"]["sha"]
    assert packet["known_gaps"] == [
        {
            "id": "codex-closeout-hook-gap",
            "path": ".codex/hooks/ce-stop-codex.py",
            "status": "missing",
            "detail": "Codex closeout hook ce-stop-codex.py is not present",
        }
    ]
