"""Unit tests for G2.002.0 operating-mode policy substrate."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.operating_mode_policy import (
    CHECK_NAME,
    CODE_AGENT_RATIFIER_ACTIVE,
    CODE_AUTO_REQUIRES_POLICY,
    CODE_EMERGENCY_OVERRIDE,
    CODE_MODE_ENUM,
    CODE_NO_INLINE,
    CODE_PRIVILEGED_FLOOR_AGENT,
    CODE_RESERVED_AUTONOMY_ACTIVE,
    CODE_TRANSCENDENCE_REQUIRES_POLICY,
    CODE_V1_DEFAULT,
    run,
    validate_file,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def _write_policy(tmp_path: Path, body: str, name: str = "policy.ce.yml") -> Path:
    p = tmp_path / "validators" / "examples" / "operating-mode-policy" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


VALID_STRICT = """
operating_mode_policy:
  operating_mode: strict
  autonomy_class: operator_ratified_privileged
  default_for_migrated_v1_tenants: strict
  privileged_floor:
    privileged_mutation_classes: [deploy, governance, identity, security, attestation, redaction]
    required_ratifier_role: operator
    agent_reviewer: advisory_only
    agent_ratifier:
      status: reserved-inactive
      activation_requires: AOS-RATIFIER-MILESTONE
      active_authority: none
  policy_authority:
    ratification_required_for_modes: [auto, transcendence]
    activation_record_required: true
  risk_coverage:
    required_validation_refs:
      - VAL-OPERATING-MODE-ENUM
"""

VALID_AUTO = """
operating_mode_policy:
  operating_mode: auto
  autonomy_class: delegated_non_privileged
  default_for_migrated_v1_tenants: strict
  operator_policy_ref:
    ratified_prompt: .hermes/research/example/POLICY.md
    sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  privileged_floor:
    privileged_mutation_classes: [governance, security]
    required_ratifier_role: operator
    agent_reviewer: advisory_only
    agent_ratifier:
      status: reserved-inactive
      active_authority: none
  policy_authority:
    ratification_required_for_modes: [auto, transcendence]
    activation_record_required: true
  risk_coverage:
    required_validation_refs: [VAL-AUTO-REQUIRES-OPERATOR-POLICY]
"""


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_MODE_ENUM in frs
    assert CODE_AUTO_REQUIRES_POLICY in frs
    assert CODE_PRIVILEGED_FLOOR_AGENT in frs


def test_valid_strict_policy_passes(tmp_path: Path):
    path = _write_policy(tmp_path, VALID_STRICT)
    errors = validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_valid_auto_with_operator_policy_pointer_passes(tmp_path: Path):
    path = _write_policy(tmp_path, VALID_AUTO)
    errors = validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_allows_agent_ratifier_reserved_placeholder(tmp_path: Path):
    path = _write_policy(tmp_path, VALID_STRICT)
    errors = validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_rejects_reserved_future_agent_ratification_as_active_autonomy(tmp_path: Path):
    path = _write_policy(tmp_path, VALID_STRICT.replace("operator_ratified_privileged", "reserved_future_agent_ratification"))
    assert CODE_RESERVED_AUTONOMY_ACTIVE in _codes(validate_file(path))


def test_rejects_unknown_operating_mode(tmp_path: Path):
    path = _write_policy(tmp_path, VALID_STRICT.replace("operating_mode: strict", "operating_mode: permissive"))
    assert CODE_MODE_ENUM in _codes(validate_file(path))


def test_rejects_migrated_default_other_than_strict(tmp_path: Path):
    path = _write_policy(tmp_path, VALID_STRICT.replace("default_for_migrated_v1_tenants: strict", "default_for_migrated_v1_tenants: auto"))
    assert CODE_V1_DEFAULT in _codes(validate_file(path))


def test_rejects_auto_without_operator_policy_pointer(tmp_path: Path):
    body = VALID_STRICT.replace("operating_mode: strict", "operating_mode: auto")
    path = _write_policy(tmp_path, body)
    assert CODE_AUTO_REQUIRES_POLICY in _codes(validate_file(path))


def test_rejects_transcendence_without_operator_policy_pointer(tmp_path: Path):
    body = VALID_STRICT.replace("operating_mode: strict", "operating_mode: transcendence")
    path = _write_policy(tmp_path, body)
    assert CODE_TRANSCENDENCE_REQUIRES_POLICY in _codes(validate_file(path))


def test_rejects_agent_reviewer_as_privileged_ratifier(tmp_path: Path):
    path = _write_policy(tmp_path, VALID_STRICT.replace("required_ratifier_role: operator", "required_ratifier_role: agent_reviewer"))
    assert CODE_PRIVILEGED_FLOOR_AGENT in _codes(validate_file(path))


def test_rejects_agent_ratifier_active_binding_even_in_auto(tmp_path: Path):
    body = VALID_AUTO.replace("active_authority: none", "active_authority: privileged_governance")
    path = _write_policy(tmp_path, body)
    assert CODE_AGENT_RATIFIER_ACTIVE in _codes(validate_file(path))


def test_rejects_emergency_override_not_operator_only(tmp_path: Path):
    body = VALID_STRICT + "  emergency_override: agent_ratifier\n"
    path = _write_policy(tmp_path, body)
    assert CODE_EMERGENCY_OVERRIDE in _codes(validate_file(path))


def test_rejects_ce_metadata_inline_in_spec_md(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "002-operating-mode-substrate" / "spec.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# Spec\n\n```yaml\noperating_mode_policy:\n  operating_mode: auto\n```\n", encoding="utf-8")
    assert CODE_NO_INLINE in _codes(validate_file(p))


def test_run_over_fixture_dir_reports_expected_codes(tmp_path: Path):
    _write_policy(tmp_path, VALID_STRICT, "valid-strict-spec.ce.yml")
    _write_policy(tmp_path, VALID_STRICT.replace("operating_mode: strict", "operating_mode: permissive"), "invalid-unknown-mode.ce.yml")
    result = run([tmp_path / "validators" / "examples" / "operating-mode-policy"])
    assert not result.ok
    assert CODE_MODE_ENUM in _codes(result.errors)


def test_out_of_scope_policy_is_ignored(tmp_path: Path):
    p = tmp_path / "docs" / "policy.ce.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("operating_mode_policy:\n  operating_mode: permissive\n", encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]
