"""TDD coverage for the G2.005.0 connector substrate.

Two shape-only families: connector descriptors and Mission-Brief records.
Substrate only — no runtime, no network/API, no secret values. The bounded
non-privileged `tracker_mirror` class is permitted; privileged classes are not.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.connector_substrate import (
    CONN_CHECK_NAME,
    CONN_CODE_CAPABILITY,
    CONN_CODE_CREDENTIAL_REF,
    CONN_CODE_KIND,
    CONN_CODE_NO_INLINE,
    CONN_CODE_ROLE_FLOOR,
    CONN_CODE_SCHEMA,
    CONN_CODE_SECRET,
    CONN_CODE_WRITE_FREEZE,
    MB_CHECK_NAME,
    MB_CODE_CLASS,
    MB_CODE_MODE_ENUM,
    MB_CODE_POINTER_SHAPE,
    MB_CODE_PRIVILEGE_ESCALATION,
    MB_CODE_ROLE_FLOOR,
    MB_CODE_SCHEMA,
    MB_CODE_SECRET,
    MB_CODE_SIGNATURE_SHAPE,
    run_connector,
    run_mission_brief,
    validate_connector_file,
    validate_mission_brief_file,
)


def _codes(errors) -> set[str]:
    return {e.code for e in errors}


def _conn_fixture(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "connector" / name


def _mb_fixture(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "mission-brief" / name


def _valid_connector() -> dict:
    return {
        "connector_id": "conn-tmp-0001",
        "connector_kind": "tracker",
        "provider_class": "issue-tracker",
        "capability": {"scope": "read_only", "verbs": ["issue-read"]},
        "credential_ref": {"ref_kind": "none", "ref_name": "unused"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:21:29Z",
    }


def _valid_brief() -> dict:
    return {
        "brief_id": "mb-tmp-0001",
        "assignment_ref": "lane:tmp",
        "declared_mutation_classes": ["docs", "tracker_mirror"],
        "capability_scope": "read_only",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:21:29Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }


def _write_conn(tmp_path: Path, record: dict, name: str = "c.ce.yml") -> Path:
    scope = tmp_path / "connector"
    scope.mkdir(exist_ok=True)
    p = scope / name
    p.write_text(yaml.safe_dump({"connector": record}), encoding="utf-8")
    return p


def _write_mb(tmp_path: Path, record: dict, name: str = "m.ce.yml") -> Path:
    scope = tmp_path / "mission-brief"
    scope.mkdir(exist_ok=True)
    p = scope / name
    p.write_text(yaml.safe_dump({"mission_brief": record}), encoding="utf-8")
    return p


# --- registration ------------------------------------------------------------
def test_checks_registered():
    checks = registered_checks()
    assert CONN_CHECK_NAME in checks and MB_CHECK_NAME in checks
    for c in (CONN_CODE_SCHEMA, CONN_CODE_KIND, CONN_CODE_ROLE_FLOOR, CONN_CODE_CREDENTIAL_REF, CONN_CODE_SECRET, CONN_CODE_CAPABILITY, CONN_CODE_NO_INLINE, CONN_CODE_WRITE_FREEZE):
        assert c in checks[CONN_CHECK_NAME].frs
    for c in (MB_CODE_SCHEMA, MB_CODE_CLASS, MB_CODE_PRIVILEGE_ESCALATION, MB_CODE_POINTER_SHAPE, MB_CODE_SIGNATURE_SHAPE, MB_CODE_ROLE_FLOOR, MB_CODE_MODE_ENUM, MB_CODE_SECRET):
        assert c in checks[MB_CHECK_NAME].frs


# --- connector family --------------------------------------------------------
def test_connector_valid_fixture_passes():
    errors = validate_connector_file(_conn_fixture("valid-connector.ce.yml"))
    assert errors == [], [e.format() for e in errors]


def test_connector_rejects_unknown_kind():
    assert CONN_CODE_KIND in _codes(validate_connector_file(_conn_fixture("invalid-unknown-kind.ce.yml")))


def test_connector_rejects_agent_ratifier_role():
    assert CONN_CODE_ROLE_FLOOR in _codes(validate_connector_file(_conn_fixture("invalid-agent-ratifier-role.ce.yml")))


def test_connector_rejects_secret_value():
    codes = _codes(validate_connector_file(_conn_fixture("invalid-secret-value.ce.yml")))
    assert CONN_CODE_SECRET in codes


def test_connector_rejects_inline_metadata():
    assert CONN_CODE_NO_INLINE in _codes(validate_connector_file(_conn_fixture("invalid-inline-metadata.md")))


def test_connector_rejects_privileged_write_verb(tmp_path):
    rec = _valid_connector()
    rec["capability"] = {"scope": "write", "verbs": ["issue-create", "merge-deploy"]}
    assert CONN_CODE_CAPABILITY in _codes(validate_connector_file(_write_conn(tmp_path, rec)))


def test_connector_rejects_missing_credential_ref(tmp_path):
    rec = _valid_connector()
    del rec["credential_ref"]
    codes = _codes(validate_connector_file(_write_conn(tmp_path, rec)))
    assert CONN_CODE_CREDENTIAL_REF in codes or CONN_CODE_SCHEMA in codes


def test_connector_rejects_hermes_write_target(tmp_path):
    rec = _valid_connector()
    rec["metadata"] = {"target": ".hermes/connector/x"}
    assert CONN_CODE_WRITE_FREEZE in _codes(validate_connector_file(_write_conn(tmp_path, rec)))


def test_connector_rejects_schema_violation(tmp_path):
    p = _write_conn(tmp_path, {"connector_id": "conn-bad"})
    assert CONN_CODE_SCHEMA in _codes(validate_connector_file(p))


def test_connector_run_over_dir_reports_codes():
    result = run_connector([_conn_fixture("valid-connector.ce.yml").parent])
    assert not result.ok
    codes = _codes(result.errors)
    assert CONN_CODE_KIND in codes
    assert CONN_CODE_ROLE_FLOOR in codes
    assert CONN_CODE_SECRET in codes
    assert CONN_CODE_NO_INLINE in codes


# --- mission-brief family ----------------------------------------------------
def test_mission_brief_valid_fixture_passes():
    errors = validate_mission_brief_file(_mb_fixture("valid-mission-brief.ce.yml"))
    assert errors == [], [e.format() for e in errors]


def test_mission_brief_rejects_privilege_escalation():
    assert MB_CODE_PRIVILEGE_ESCALATION in _codes(validate_mission_brief_file(_mb_fixture("invalid-privilege-escalation.ce.yml")))


def test_mission_brief_rejects_bad_pointer():
    assert MB_CODE_POINTER_SHAPE in _codes(validate_mission_brief_file(_mb_fixture("invalid-bad-pointer.ce.yml")))


def test_mission_brief_rejects_unknown_mode():
    assert MB_CODE_MODE_ENUM in _codes(validate_mission_brief_file(_mb_fixture("invalid-unknown-mode.ce.yml")))


def test_mission_brief_rejects_unknown_class(tmp_path):
    rec = _valid_brief()
    rec["declared_mutation_classes"] = ["frobnicate"]
    assert MB_CODE_CLASS in _codes(validate_mission_brief_file(_write_mb(tmp_path, rec)))


def test_mission_brief_rejects_agent_ratifier_role(tmp_path):
    rec = _valid_brief()
    rec["emitting_role"] = "agent_ratifier"
    assert MB_CODE_ROLE_FLOOR in _codes(validate_mission_brief_file(_write_mb(tmp_path, rec)))


def test_mission_brief_rejects_activated_signature(tmp_path):
    rec = _valid_brief()
    rec["signature"]["value"] = "active-bound"
    assert MB_CODE_SIGNATURE_SHAPE in _codes(validate_mission_brief_file(_write_mb(tmp_path, rec)))


def test_mission_brief_rejects_secret(tmp_path):
    rec = _valid_brief()
    rec["metadata"] = {"access_token": "github_pat_AAAAAAAAAAAAAAAAAAAA"}
    assert MB_CODE_SECRET in _codes(validate_mission_brief_file(_write_mb(tmp_path, rec)))


def test_mission_brief_run_over_dir_reports_codes():
    result = run_mission_brief([_mb_fixture("valid-mission-brief.ce.yml").parent])
    assert not result.ok
    codes = _codes(result.errors)
    assert MB_CODE_PRIVILEGE_ESCALATION in codes
    assert MB_CODE_POINTER_SHAPE in codes
    assert MB_CODE_MODE_ENUM in codes


# --- scope -------------------------------------------------------------------
def test_out_of_scope_yaml_ignored(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "random.ce.yml").write_text(yaml.safe_dump({"connector": {"connector_kind": "bogus"}}), encoding="utf-8")
    (tmp_path / "docs" / "random-mb.ce.yml").write_text(yaml.safe_dump({"mission_brief": {"operating_mode": "permissive"}}), encoding="utf-8")
    assert run_connector([tmp_path]).ok
    assert run_mission_brief([tmp_path]).ok
