from __future__ import annotations

import pytest

from creator_engine_validator import pickup
from creator_engine_validator.forge import integrator_belt
from creator_engine_validator.pickup_payload_schema import (
    DiscoveryPayloadRejected,
    MAX_DISCOVERY_PAYLOAD_FIELD_LENGTHS,
    validate_discovery_payload,
)


def _valid_payload() -> dict[str, str]:
    return {
        "issue": "388",
        "branch_name": "ce-388-payload-data-only",
        "pr_title": "Implement payload-as-data-only",
        "pr_body": "Payload is data only.",
    }


def test_unknown_field_fails_closed_and_emits_audit_record():
    audit: list[dict] = []
    payload = {**_valid_payload(), "surprise": "ignored"}

    with pytest.raises(DiscoveryPayloadRejected) as raised:
        validate_discovery_payload(payload, audit_sink=lambda record: audit.append(dict(record)))

    assert "discovery payload rejected" in str(raised.value)
    assert audit == list(raised.value.audit_records)
    assert audit[0]["action"] == "discovery_payload_rejected"
    assert audit[0]["reason"] == "unknown_field"
    assert audit[0]["field"] == "surprise"
    assert "ignored" not in str(audit[0])


@pytest.mark.parametrize(
    "field",
    [
        "validate_command",
        "base",
        "remote",
        "repo_path",
        "worktree_path",
        "bundle_path",
        "pr_base",
    ],
)
def test_banned_control_fields_are_rejected_and_audited(field: str):
    audit: list[dict] = []
    payload = {**_valid_payload(), field: "attacker-controlled"}

    with pytest.raises(DiscoveryPayloadRejected) as raised:
        validate_discovery_payload(payload, audit_sink=lambda record: audit.append(dict(record)))

    assert audit == list(raised.value.audit_records)
    assert audit[0]["reason"] == "banned_control_field"
    assert audit[0]["field"] == field
    assert "attacker-controlled" not in str(audit[0])


def test_oversized_field_is_rejected_and_audited():
    audit: list[dict] = []
    payload = {
        **_valid_payload(),
        "pr_title": "x" * (MAX_DISCOVERY_PAYLOAD_FIELD_LENGTHS["pr_title"] + 1),
    }

    with pytest.raises(DiscoveryPayloadRejected) as raised:
        validate_discovery_payload(payload, audit_sink=lambda record: audit.append(dict(record)))

    assert audit == list(raised.value.audit_records)
    assert audit[0]["reason"] == "field_oversized"
    assert audit[0]["field"] == "pr_title"
    assert audit[0]["detail"] == f"max_length={MAX_DISCOVERY_PAYLOAD_FIELD_LENGTHS['pr_title']}"


def test_missing_required_field_is_rejected_and_audited():
    audit: list[dict] = []
    payload = _valid_payload()
    del payload["issue"]

    with pytest.raises(DiscoveryPayloadRejected) as raised:
        validate_discovery_payload(payload, audit_sink=lambda record: audit.append(dict(record)))

    assert audit == list(raised.value.audit_records)
    assert audit[0]["reason"] == "missing_required_field"
    assert audit[0]["field"] == "issue"


def test_non_string_field_is_rejected_and_audited():
    audit: list[dict] = []
    payload = {**_valid_payload(), "pr_body": 123}

    with pytest.raises(DiscoveryPayloadRejected) as raised:
        validate_discovery_payload(payload, audit_sink=lambda record: audit.append(dict(record)))

    assert audit == list(raised.value.audit_records)
    assert audit[0]["reason"] == "schema_mismatch"
    assert audit[0]["field"] == "pr_body"
    assert audit[0]["detail"] == "field_not_string"


def test_non_mapping_payload_is_rejected_and_audited():
    audit: list[dict] = []

    with pytest.raises(DiscoveryPayloadRejected) as raised:
        validate_discovery_payload(None, audit_sink=lambda record: audit.append(dict(record)))  # type: ignore[arg-type]

    assert audit == list(raised.value.audit_records)
    assert audit[0]["reason"] == "schema_mismatch"
    assert audit[0]["detail"] == "payload_not_mapping"
    assert "field" not in audit[0]


def test_well_formed_four_field_payload_is_accepted():
    payload = _valid_payload()

    parsed = validate_discovery_payload(payload)

    assert parsed.to_dict() == payload


def test_pickup_parser_uses_data_only_schema():
    payload = _valid_payload()

    parsed = pickup.parse_conveyor_discovery_payload(payload)

    assert parsed.branch_name == "ce-388-payload-data-only"


def test_integrator_belt_parser_rejects_before_dispatch_and_audits():
    audit: list[dict] = []
    payload = {**_valid_payload(), "gh_options": ["--repo", "evil/repo"]}

    with pytest.raises(DiscoveryPayloadRejected):
        integrator_belt.parse_conveyor_discovery_payload(
            payload,
            audit_sink=lambda record: audit.append(dict(record)),
        )

    assert audit
    assert audit[0]["source"] == "integrator_belt"
    assert audit[0]["reason"] == "banned_control_field"
    assert audit[0]["field"] == "gh_options"
