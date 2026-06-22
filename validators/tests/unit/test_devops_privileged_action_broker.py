from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.devops_privileged_action_broker import (
    CHECK_NAME,
    iter_envelope_files,
    run,
)
from creator_engine_validator.devops_privileged_action_broker import (
    BROKER_PROXY_MODE,
    CAPABILITY_HANDOFF_MODE,
    CODE_CAPABILITY,
    CODE_EXECUTION,
    CODE_SCHEMA,
    CODE_SECRET,
    BrokerLedger,
    StubActionResult,
    dispatch,
    validate_envelope,
)
from creator_engine_validator.runtime_evidence_spine import verify_chain


def _now() -> datetime:
    return datetime(2026, 6, 22, 15, 0, 0, tzinfo=UTC)


def _pilot_envelope() -> dict:
    return {
        "privileged_action_envelope": {
            "envelope_id": "pae-ce185-vps-tmp-root-20260622",
            "schema_version": "1",
            "task_id": "ce-ops#184",
            "requester": {
                "seat_id": "ce-dev-3",
                "role": "implementer",
                "actor_ref": "github:ce-dev-3",
            },
            "capability": {
                "engine": "openbao_ssh",
                "operation": "ssh_sign_public_key",
                "capability_ref": "openbao:ssh/sign/ce-vps-root-tmp",
                "openbao_mount": "ssh",
                "mode": "signed_ssh_certificate",
            },
            "target": {
                "target_type": "host",
                "target_ref": "vps:ce-ops-184",
                "target_path": "/etc/tmpfiles.d/ce-vps-tmp.conf",
                "target_principal": "root",
                "environment_ref": "ce-vps-pilot",
            },
            "scope": {
                "allowed_actions": ["edit_file"],
                "resource_refs": ["path:/etc/tmpfiles.d/ce-vps-tmp.conf"],
                "filesystem_paths": ["/etc/tmpfiles.d/ce-vps-tmp.conf"],
                "command_refs": [
                    "install -m 0644 tmpfiles.d",
                    "systemd-tmpfiles --cat-config",
                ],
                "network_egress": "target_only",
                "max_uses": 1,
                "constraints": [
                    "No shell beyond file write and verification readback.",
                    "No static root key material.",
                    "No secret value may enter LLM context, argv, ledger, or logs.",
                ],
            },
            "ttl_seconds": 300,
            "expires_at": "2026-06-22T15:05:00Z",
            "ratification_ref": {
                "kind": "issue",
                "ref": "ce-ops#184",
                "ratified_prompt_sha": "8a0f89fee53dc43c26dd8a3f2a3b50191e6564453aa6c19b05a1bc907fc88aac",
                "ratifier_role": "operator",
                "ratified_by": "operator",
                "ratified_at": "2026-06-22T15:00:00Z",
            },
            "execution": {
                "custody_mode": "broker-mints-ephemeral",
                "execution_mode": "broker-proxies",
                "blast_radius": "high",
                "irreversible": True,
                "reason": "Root write to /etc is high-blast, so the broker executes and returns evidence only.",
            },
            "audit_hooks": [
                {
                    "hook_type": "side_effect_ledger",
                    "hook_ref": "side-effect-ledger:ce-ops-184:vps-tmp-root",
                    "required": True,
                },
                {
                    "hook_type": "lease_revocation",
                    "hook_ref": "openbao-lease:pending-runtime-id",
                    "required": True,
                },
            ],
            "metadata": {
                "openbao_version_basis": "OpenBao 2.5.x docs verified 2026-06-22",
            },
        }
    }


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_valid_pilot_ssh_sign_dispatches_broker_proxy_and_appends_verified_chain(tmp_path: Path):
    ledger = BrokerLedger(tmp_path / "broker-ledger.yaml")

    result = dispatch(_pilot_envelope(), ledger=ledger, now=_now)

    assert result.accepted is True
    assert result.errors == ()
    assert result.action_result is not None
    assert result.action_result.executor == BROKER_PROXY_MODE
    doc = ledger.load()
    assert doc["kind"] == "runtime-evidence-chain"
    assert len(doc["records"]) == 2
    assert verify_chain(doc["records"]) == []
    assert doc["records"][0]["record_type"] == "devops_privileged_action_broker_decision"
    assert doc["records"][0]["verdict"] == "accepted"
    assert doc["records"][1]["record_type"] == "devops_privileged_action_broker_action"
    assert doc["records"][1]["executor"] == BROKER_PROXY_MODE


def test_metadata_password_rejects_structurally_pab_001():
    document = _pilot_envelope()
    document["privileged_action_envelope"]["metadata"]["password"] = "not-recorded"

    errors = validate_envelope(document)

    assert _codes(errors) == {CODE_SCHEMA}


def test_high_irreversible_handoff_rejects_structurally_pab_001():
    document = _pilot_envelope()
    document["privileged_action_envelope"]["execution"]["execution_mode"] = CAPABILITY_HANDOFF_MODE

    errors = validate_envelope(document)

    assert _codes(errors) == {CODE_SCHEMA}


def test_incoherent_capability_tuple_rejects_policy_gate_pab_002():
    document = _pilot_envelope()
    document["privileged_action_envelope"]["capability"].update(
        {
            "engine": "openbao_ssh",
            "operation": "transit_decrypt",
            "openbao_mount": "ssh",
            "mode": "service_account_token",
        }
    )

    errors = validate_envelope(document)

    assert _codes(errors) == {CODE_CAPABILITY}


def test_semantic_secret_value_in_allowed_metadata_field_rejects_pab_003():
    document = _pilot_envelope()
    document["privileged_action_envelope"]["metadata"]["note"] = "operator supplied password=supersecret"

    errors = validate_envelope(document)

    assert _codes(errors) == {CODE_SECRET}
    assert "supersecret" not in errors[0].message


def test_transit_decrypt_handoff_rejects_execution_policy_pab_004():
    document = _pilot_envelope()
    env = document["privileged_action_envelope"]
    env["capability"].update(
        {
            "engine": "openbao_transit",
            "operation": "transit_decrypt",
            "capability_ref": "openbao:transit/decrypt/staging-key",
            "openbao_mount": "transit",
            "mode": "transit_operation",
        }
    )
    env["target"].update({"target_type": "transit_key", "target_ref": "transit:staging-key"})
    env["scope"]["allowed_actions"] = ["decrypt"]
    env["execution"].update(
        {
            "execution_mode": CAPABILITY_HANDOFF_MODE,
            "blast_radius": "low",
            "irreversible": False,
        }
    )

    errors = validate_envelope(document)

    assert _codes(errors) == {CODE_EXECUTION}


def test_refused_validation_appends_refusal_and_does_not_call_executor(tmp_path: Path):
    document = _pilot_envelope()
    document["privileged_action_envelope"]["metadata"]["note"] = "token=should-not-be-seen"
    ledger = BrokerLedger(tmp_path / "broker-ledger.yaml")
    called = False

    def fail_if_called(_envelope):
        nonlocal called
        called = True
        raise AssertionError("executor must not run for refused envelopes")

    result = dispatch(
        document,
        ledger=ledger,
        executors={BROKER_PROXY_MODE: fail_if_called},
        now=_now,
    )

    assert result.accepted is False
    assert called is False
    records = ledger.load()["records"]
    assert len(records) == 1
    assert verify_chain(records) == []
    assert records[0]["verdict"] == "refused"
    assert records[0]["reasons"][0]["code"] == CODE_SECRET
    assert "should-not-be-seen" not in str(records)


def test_capability_handoff_valid_low_blast_path_dispatches_handoff_stub(tmp_path: Path):
    document = _pilot_envelope()
    env = document["privileged_action_envelope"]
    env["capability"].update(
        {
            "engine": "openbao_database",
            "operation": "database_dynamic_credentials",
            "capability_ref": "openbao:database/creds/disposable-test",
            "openbao_mount": "database",
            "mode": "dynamic_credential",
        }
    )
    env["target"].update({"target_type": "database", "target_ref": "database:disposable-test"})
    env["scope"]["allowed_actions"] = ["mint_dynamic_credential"]
    env["execution"].update(
        {
            "execution_mode": CAPABILITY_HANDOFF_MODE,
            "blast_radius": "low",
            "irreversible": False,
            "reason": "Disposable test database credential is low-blast and short-lived.",
        }
    )
    ledger = BrokerLedger(tmp_path / "broker-ledger.yaml")

    result = dispatch(document, ledger=ledger, now=_now)

    assert result.accepted is True
    assert result.action_result is not None
    assert result.action_result.executor == CAPABILITY_HANDOFF_MODE
    records = ledger.load()["records"]
    assert len(records) == 2
    assert verify_chain(records) == []
    assert records[1]["executor"] == CAPABILITY_HANDOFF_MODE


def test_registered_check_finds_well_and_malformed_envelope_files(tmp_path: Path):
    good = tmp_path / "well" / "good.yaml"
    bad = tmp_path / "malformed" / "bad.yaml"
    skipped_schema = tmp_path / "schemas" / "bad.yaml"
    skipped_template = tmp_path / "templates" / "bad.yaml"
    skipped_tmp = tmp_path / "well" / "bad.tmp.yaml"
    _write_yaml(good, _pilot_envelope())
    malformed = deepcopy(_pilot_envelope())
    malformed["privileged_action_envelope"]["metadata"]["note"] = "api_key=abc123"
    _write_yaml(bad, malformed)
    _write_yaml(skipped_schema, malformed)
    _write_yaml(skipped_template, malformed)
    _write_yaml(skipped_tmp, malformed)

    checks = registered_checks()
    result = run([tmp_path])

    assert CHECK_NAME in checks
    assert sorted(path.name for path in iter_envelope_files([tmp_path])) == ["bad.yaml", "good.yaml"]
    assert not result.ok
    assert _codes(result.errors) == {CODE_SECRET}
