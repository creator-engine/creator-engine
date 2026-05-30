"""Unit tests for the G2.001.2 ``role_enum_v2`` privileged-role check."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.role_enum_v2 import (
    CHECK_NAME,
    CODE_AGENT_RATIFIER_ACTIVE,
    CODE_PRIVILEGED_FLOOR_AGENT,
    run,
    validate_file,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_AGENT_RATIFIER_ACTIVE in frs
    assert CODE_PRIVILEGED_FLOOR_AGENT in frs


def test_real_g20012_sidecar_passes(repo_root: Path):
    path = repo_root / "specs/v2/001-v2-foundation-substrate/spec.ce.yml"
    errors = validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_canonical_role_enum_fixture_passes(examples_root: Path):
    path = examples_root / "well-formed/role-enum-v2/canonical-role-policy.ce.yml"
    errors = validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_agent_reviewer_advisory_policy_passes(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "review-policy.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "review_policy:\n"
        "  reviewer_role: agent_reviewer\n"
        "  authority: advisory_only\n"
        "  may: [review, test, recommend]\n",
        encoding="utf-8",
    )
    assert validate_file(p) == []


def test_agent_ratifier_active_authority_binding_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "bad-ratifier.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "ratification_policy:\n"
        "  required_ratifier_role: agent_ratifier\n"
        "  status: active\n",
        encoding="utf-8",
    )
    assert CODE_AGENT_RATIFIER_ACTIVE in _codes(validate_file(p))


def test_agent_ratifier_schema_placeholder_passes(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "reserved-ratifier.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "role_enum_v2:\n"
        "  roles:\n"
        "    - id: agent_ratifier\n"
        "      status: reserved_inactive\n"
        "      authority_binding: none\n"
        "      activation: AOS-RATIFIER-MILESTONE\n",
        encoding="utf-8",
    )
    assert validate_file(p) == []


def test_privileged_mutation_delegated_to_agent_reviewer_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "bad-privileged-floor.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "policy:\n"
        "  mutation_class: governance\n"
        "  required_ratifier_role: agent_reviewer\n"
        "  privileged: true\n",
        encoding="utf-8",
    )
    assert CODE_PRIVILEGED_FLOOR_AGENT in _codes(validate_file(p))


def test_key_encoded_agent_reviewer_in_privileged_policy_fails(examples_root: Path):
    path = examples_root / "malformed/role-enum-v2/key-encoded-agent-authority.ce.yml"
    errors = validate_file(path)
    assert CODE_PRIVILEGED_FLOOR_AGENT in _codes(errors)


def test_key_encoded_agent_ratifier_in_ratification_policy_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "bad-key-ratifier.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "policy:\n"
        "  mutation_class: governance\n"
        "  privileged: true\n"
        "  ratification_policy:\n"
        "    agent_ratifier: required\n",
        encoding="utf-8",
    )
    codes = _codes(validate_file(p))
    assert CODE_AGENT_RATIFIER_ACTIVE in codes
    assert CODE_PRIVILEGED_FLOOR_AGENT in codes


def test_emergency_override_delegated_to_agent_role_fails(tmp_path: Path):
    p = tmp_path / "specs" / "v2" / "bad-emergency.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "mode_policy:\n"
        "  emergency_override:\n"
        "    authorized_role: agent_reviewer\n",
        encoding="utf-8",
    )
    assert CODE_PRIVILEGED_FLOOR_AGENT in _codes(validate_file(p))


def test_run_over_well_formed_dir_passes(examples_root: Path):
    result = run([examples_root / "well-formed/role-enum-v2"])
    assert result.ok, [e.format() for e in result.errors]


def test_run_over_malformed_dir_fails_closed(examples_root: Path):
    result = run([examples_root / "malformed/role-enum-v2"])
    assert not result.ok
    assert {CODE_AGENT_RATIFIER_ACTIVE, CODE_PRIVILEGED_FLOOR_AGENT}.issubset(_codes(result.errors))


def test_out_of_scope_paths_are_ignored(tmp_path: Path):
    p = tmp_path / "docs" / "bad-privileged-floor.ce.yml"
    p.parent.mkdir(parents=True)
    p.write_text(
        "policy:\n  mutation_class: governance\n  required_ratifier_role: agent_reviewer\n",
        encoding="utf-8",
    )
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]
