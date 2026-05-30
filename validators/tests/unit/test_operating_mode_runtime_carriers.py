"""Unit tests for the G2.002.1 operating-mode runtime-carrier validator.

The check enforces floor preservation on runtime carriers (Active-Work Ledger
records carrying carrier fields, and operating-mode-policy sidecars carrying a
`runtime_carriers` block). It reuses the G2.002.0 `operating_mode_policy`
substrate helpers and mints no new authority.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.operating_mode_runtime_carriers import (
    CHECK_NAME,
    CODE_AGENT_RATIFIER_ACTIVE,
    CODE_AUTONOMY_ENUM,
    CODE_ELEVATION_REQUIRES_RATIFICATION,
    CODE_LANE_KIND_ENUM,
    CODE_MIGRATED_DEFAULT,
    CODE_MODE_ENUM,
    CODE_RESERVED_AUTONOMY_ACTIVE,
    CODE_ROLE_SEPARATION,
    run,
    validate_carrier,
    validate_file,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


# ---------------------------------------------------------------------------
# Direct carrier-shape validation
# ---------------------------------------------------------------------------


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_MODE_ENUM in frs
    assert CODE_ELEVATION_REQUIRES_RATIFICATION in frs
    assert CODE_AGENT_RATIFIER_ACTIVE in frs


def test_strict_implementation_carrier_passes():
    carrier = {
        "operating_mode": "strict",
        "autonomy_class": "operator_ratified_privileged",
        "lane_kind": "implementation",
    }
    assert validate_carrier(carrier, Path("x.yaml"), ()) == []


def test_absent_operating_mode_resolves_strict_passes():
    # Absent mode resolves to strict; carrier with only a lane_kind is valid.
    assert validate_carrier({"lane_kind": "implementation"}, Path("x.yaml"), ()) == []
    assert validate_carrier({}, Path("x.yaml"), ()) == []


def test_unknown_operating_mode_rejected():
    errors = validate_carrier({"operating_mode": "permissive"}, Path("x.yaml"), ())
    assert CODE_MODE_ENUM in _codes(errors)


def test_unknown_autonomy_class_rejected():
    errors = validate_carrier({"autonomy_class": "fully_autonomous"}, Path("x.yaml"), ())
    assert CODE_AUTONOMY_ENUM in _codes(errors)


def test_unknown_lane_kind_rejected():
    errors = validate_carrier({"lane_kind": "deploy-and-merge"}, Path("x.yaml"), ())
    assert CODE_LANE_KIND_ENUM in _codes(errors)


def test_reserved_future_agent_ratification_active_rejected():
    errors = validate_carrier(
        {"operating_mode": "strict", "autonomy_class": "reserved_future_agent_ratification"},
        Path("x.yaml"),
        (),
    )
    assert CODE_RESERVED_AUTONOMY_ACTIVE in _codes(errors)


def test_auto_without_ratification_evidence_rejected():
    errors = validate_carrier({"operating_mode": "auto"}, Path("x.yaml"), ())
    assert CODE_ELEVATION_REQUIRES_RATIFICATION in _codes(errors)


def test_transcendence_without_ratification_evidence_rejected():
    errors = validate_carrier({"operating_mode": "transcendence"}, Path("x.yaml"), ())
    assert CODE_ELEVATION_REQUIRES_RATIFICATION in _codes(errors)


def test_auto_with_ratification_evidence_passes():
    carrier = {
        "operating_mode": "auto",
        "autonomy_class": "operator_ratified_privileged",
        "lane_kind": "implementation",
        "ratification_evidence_ref": {
            "ratified_prompt": ".hermes/research/example/POLICY.md",
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        },
    }
    assert validate_carrier(carrier, Path("x.yaml"), ()) == []


def test_empty_ratification_evidence_does_not_satisfy_elevation():
    errors = validate_carrier(
        {"operating_mode": "auto", "ratification_evidence_ref": "   "},
        Path("x.yaml"),
        (),
    )
    assert CODE_ELEVATION_REQUIRES_RATIFICATION in _codes(errors)


def test_privileged_lane_kind_without_ratification_rejected():
    for kind in ("approval", "merge"):
        errors = validate_carrier(
            {"operating_mode": "strict", "lane_kind": kind},
            Path("x.yaml"),
            (),
        )
        assert CODE_ELEVATION_REQUIRES_RATIFICATION in _codes(errors), kind


def test_privileged_lane_kind_with_ratification_passes():
    carrier = {
        "operating_mode": "strict",
        "autonomy_class": "operator_ratified_privileged",
        "lane_kind": "approval",
        "ratification_evidence_ref": ".hermes/research/example/RATIFIED.md",
    }
    assert validate_carrier(carrier, Path("x.yaml"), ()) == []


def test_review_and_audit_lane_kinds_pass_without_ratification():
    for kind in ("review", "audit", "read-only"):
        assert validate_carrier(
            {"operating_mode": "strict", "lane_kind": kind}, Path("x.yaml"), ()
        ) == [], kind


def test_active_agent_ratifier_in_carrier_rejected():
    carrier = {
        "operating_mode": "strict",
        "lane_kind": "implementation",
        "privileged_floor": {
            "agent_ratifier": {"status": "active", "active_authority": "privileged_governance"},
        },
    }
    errors = validate_carrier(carrier, Path("x.yaml"), ())
    assert CODE_AGENT_RATIFIER_ACTIVE in _codes(errors)


def test_reserved_agent_ratifier_placeholder_in_carrier_passes():
    carrier = {
        "operating_mode": "strict",
        "lane_kind": "implementation",
        "privileged_floor": {
            "agent_ratifier": {"status": "reserved-inactive", "active_authority": "none"},
        },
    }
    assert validate_carrier(carrier, Path("x.yaml"), ()) == []


def test_migrated_default_non_strict_rejected():
    errors = validate_carrier(
        {"operating_mode": "strict", "default_for_migrated_v1_tenants": "auto"},
        Path("x.yaml"),
        (),
    )
    assert CODE_MIGRATED_DEFAULT in _codes(errors)


def test_privileged_lane_kind_delegated_autonomy_is_role_separation_violation():
    carrier = {
        "operating_mode": "strict",
        "autonomy_class": "delegated_non_privileged",
        "lane_kind": "merge",
        "ratification_evidence_ref": ".hermes/research/example/RATIFIED.md",
    }
    errors = validate_carrier(carrier, Path("x.yaml"), ())
    assert CODE_ROLE_SEPARATION in _codes(errors)


# ---------------------------------------------------------------------------
# File discovery: Active-Work Ledger records carrying carriers
# ---------------------------------------------------------------------------


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


LEDGER_CARRIER_BAD_MODE = """
kind: active-work-ledger-record
record_type: claim
schema_version: "4"
controller_id: hermes-primary
lane_id: carrier-lane
record_timestamp: "2026-05-20T03:30:30Z"
worktree_path: /worktrees/carrier-lane
envelope_ref: .hermes/envelopes/carrier.md
lease_seconds: 3600
claimed_at: "2026-05-20T03:30:30Z"
last_heartbeat_at: "2026-05-20T03:30:30Z"
operating_mode: permissive
lane_kind: implementation
"""

LEDGER_PLAIN_V1 = """
kind: active-work-ledger-record
record_type: claim
schema_version: "1"
controller_id: hermes-primary
lane_id: plain-lane
record_timestamp: "2026-05-20T03:30:30Z"
worktree_path: /worktrees/plain-lane
envelope_ref: .hermes/envelopes/plain.md
lease_seconds: 3600
claimed_at: "2026-05-20T03:30:30Z"
last_heartbeat_at: "2026-05-20T03:30:30Z"
"""


def test_run_flags_ledger_record_with_bad_carrier(tmp_path: Path):
    _write(tmp_path / "claim.yaml", LEDGER_CARRIER_BAD_MODE)
    result = run([tmp_path])
    assert not result.ok
    assert CODE_MODE_ENUM in _codes(result.errors)


def test_run_ignores_ledger_record_without_carriers(tmp_path: Path):
    _write(tmp_path / "claim.yaml", LEDGER_PLAIN_V1)
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


# ---------------------------------------------------------------------------
# File discovery: operating-mode-policy sidecars carrying runtime_carriers
# ---------------------------------------------------------------------------


POLICY_WITH_GOOD_CARRIERS = """
operating_mode_policy:
  operating_mode: strict
  autonomy_class: operator_ratified_privileged
  default_for_migrated_v1_tenants: strict
  privileged_floor:
    privileged_mutation_classes: [governance, identity]
    required_ratifier_role: operator
    agent_reviewer: advisory_only
    agent_ratifier:
      status: reserved-inactive
      active_authority: none
  policy_authority:
    ratification_required_for_modes: [auto, transcendence]
    activation_record_required: true
  risk_coverage:
    required_validation_refs: [VAL-CARRIER-MODE-ENUM]
runtime_carriers:
  - operating_mode: strict
    autonomy_class: operator_ratified_privileged
    lane_kind: implementation
  - operating_mode: strict
    lane_kind: review
"""

POLICY_WITH_BAD_CARRIER = POLICY_WITH_GOOD_CARRIERS.replace(
    "    lane_kind: review", "    lane_kind: not-a-lane-kind"
)


def test_run_validates_policy_runtime_carriers_block(tmp_path: Path):
    _write(
        tmp_path / "validators" / "examples" / "operating-mode-policy" / "carriers.ce.yml",
        POLICY_WITH_BAD_CARRIER,
    )
    result = run([tmp_path])
    assert not result.ok
    assert CODE_LANE_KIND_ENUM in _codes(result.errors)


def test_run_passes_policy_with_valid_runtime_carriers(tmp_path: Path):
    _write(
        tmp_path / "validators" / "examples" / "operating-mode-policy" / "carriers.ce.yml",
        POLICY_WITH_GOOD_CARRIERS,
    )
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


def test_run_ignores_policy_without_runtime_carriers(tmp_path: Path):
    body = POLICY_WITH_GOOD_CARRIERS.split("runtime_carriers:")[0]
    _write(
        tmp_path / "validators" / "examples" / "operating-mode-policy" / "plain.ce.yml",
        body,
    )
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


# ---------------------------------------------------------------------------
# Checked-in reference fixtures under validators/examples/operating-mode-policy/
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "validators" / "examples" / "operating-mode-policy"


def test_reference_valid_runtime_carriers_fixture_passes_both_checks():
    from creator_engine_validator.checks import operating_mode_policy as omp

    fixture = FIXTURE_DIR / "valid-runtime-carriers.ce.yml"
    # The policy block remains a valid G2.002.0 policy.
    assert omp.validate_file(fixture) == [], [e.format() for e in omp.validate_file(fixture)]
    # The runtime_carriers block satisfies the G2.002.1 carrier floor.
    assert validate_file(fixture) == [], [e.format() for e in validate_file(fixture)]


def test_reference_invalid_elevation_fixture_flags_elevation_code():
    fixture = FIXTURE_DIR / "invalid-carrier-elevation-without-ratification.ce.yml"
    errors = validate_file(fixture)
    assert CODE_ELEVATION_REQUIRES_RATIFICATION in _codes(errors)


def test_reference_invalid_agent_ratifier_fixture_flags_ratifier_code():
    fixture = FIXTURE_DIR / "invalid-carrier-agent-ratifier-active.ce.yml"
    errors = validate_file(fixture)
    assert CODE_AGENT_RATIFIER_ACTIVE in _codes(errors)


def test_reference_invalid_fixtures_keep_valid_policy_blocks():
    # The invalid-carrier fixtures are invalid only in their carrier block; their
    # operating_mode_policy block stays a valid G2.002.0 policy so the existing
    # check is unaffected.
    from creator_engine_validator.checks import operating_mode_policy as omp

    for name in (
        "invalid-carrier-elevation-without-ratification.ce.yml",
        "invalid-carrier-agent-ratifier-active.ce.yml",
    ):
        fixture = FIXTURE_DIR / name
        assert omp.validate_file(fixture) == [], (name, [e.format() for e in omp.validate_file(fixture)])
