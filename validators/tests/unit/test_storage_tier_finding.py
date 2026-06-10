"""Unit tests for the v3.5-C A-C2 ``storage_tier_finding`` check."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import decision_record as dr_chk
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import storage_tier_finding as chk

FIXTURES = Path(__file__).resolve().parents[2] / "examples" / "storage-tier-finding"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _fixture(name: str) -> Path:
    return FIXTURES / name


def _finding(**overrides):
    base = {
        "kind": "storage-tier-finding", "schema_version": "1",
        "artifact_ref": ".ce/state/research/x.md", "advisory": True,
        "classifications": [
            {"part_ref": "whole", "relevance": "project-relevant",
             "tier": "repo-docs", "rationale": "travels with the repo"},
        ],
        "promotion": {"promoted": False},
    }
    base.update(overrides)
    return base


def _codes(record):
    return sorted({e.code for e in chk.validate_finding(record, Path("f.ce.yml"))})


# --- registration -------------------------------------------------------------
def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg
    assert chk.CODE_AUTO_PROMOTED in reg[chk.CHECK_NAME].frs


# --- fixtures (the gate's green-def) -------------------------------------------
def test_valid_advisory_fixture_passes():
    result = chk.run([_fixture("valid-advisory.ce.yml")])
    assert result.ok, [e.format() for e in result.errors]


def test_valid_split_fixture_passes():
    result = chk.run([_fixture("valid-split.ce.yml")])
    assert result.ok, [e.format() for e in result.errors]


def test_auto_promoted_fixture_rejected():
    result = chk.run([_fixture("invalid-auto-promoted.ce.yml")])
    assert any(e.code == chk.CODE_AUTO_PROMOTED for e in result.errors)


def test_policy_adr_validates_under_decision_record_check():
    # A-C2 green-def: the public/private policy ADR is a valid governance
    # Decision Record under the A-C1 check.
    adr = REPO_ROOT / "docs" / "decisions" / "ADR-0001-public-private-storage-policy.md"
    assert adr.is_file()
    result = dr_chk.run([adr])
    assert result.ok, [e.format() for e in result.errors]


# --- the no-auto-promotion invariant --------------------------------------------
def test_promoted_with_ratification_ref_passes():
    rec = _finding(promotion={"promoted": True, "ratification_ref": "a" * 64})
    assert _codes(rec) == []


def test_promoted_without_ratification_ref_rejected():
    assert chk.CODE_AUTO_PROMOTED in _codes(_finding(promotion={"promoted": True}))


def test_promoted_with_malformed_ref_rejected_by_schema():
    rec = _finding(promotion={"promoted": True, "ratification_ref": "not-a-digest"})
    assert chk.CODE_SCHEMA in _codes(rec)


def test_no_promotion_code_path_exists():
    # The hard invariant: the only constructor emits unpromoted, and the module
    # ships no promote()/approve()-style mutator at all.
    emitted = chk.emit_finding("artifact.md", [
        {"part_ref": "whole", "relevance": "project-relevant",
         "tier": "repo-docs", "rationale": "r"},
    ])
    assert emitted["advisory"] is True
    assert emitted["promotion"] == {"promoted": False}
    assert _codes(emitted) == []
    mutators = [
        n for n in dir(chk)
        if callable(getattr(chk, n)) and ("promote" in n.lower() or "approve" in n.lower())
    ]
    assert mutators == []


# --- triage seam -----------------------------------------------------------------
def test_triage_stages_are_the_five_stage_loop():
    assert chk.TRIAGE_STAGES == (
        "read_only_classify", "schema_finding", "deterministic_gates",
        "discard_on_drift", "guarded_mutation",
    )


# --- split + noise invariants -----------------------------------------------------
def test_split_with_duplicate_part_ref_rejected():
    rec = _finding(classifications=[
        {"part_ref": "whole", "relevance": "project-relevant",
         "tier": "repo-docs", "rationale": "r"},
        {"part_ref": "whole", "relevance": "team-relevant",
         "tier": "ops-private", "rationale": "r"},
    ])
    assert chk.CODE_SPLIT_DUPLICATE_PART in _codes(rec)


def test_noise_proposed_into_shared_tier_rejected():
    for tier in sorted(chk.SHARED_TIERS):
        rec = _finding(classifications=[
            {"part_ref": "whole", "relevance": "instance-local-noise",
             "tier": tier, "rationale": "r"},
        ])
        assert chk.CODE_NOISE_SHARED_TIER in _codes(rec), tier


def test_noise_kept_local_passes():
    rec = _finding(classifications=[
        {"part_ref": "whole", "relevance": "instance-local-noise",
         "tier": "instance-local", "rationale": "scratch"},
    ])
    assert _codes(rec) == []


# --- schema teeth ------------------------------------------------------------------
def test_advisory_false_rejected():
    assert chk.CODE_SCHEMA in _codes(_finding(advisory=False))


def test_unknown_tier_rejected():
    rec = _finding(classifications=[
        {"part_ref": "whole", "relevance": "project-relevant",
         "tier": "s3-bucket", "rationale": "r"},
    ])
    assert chk.CODE_SCHEMA in _codes(rec)


def test_missing_rationale_rejected():
    rec = _finding(classifications=[
        {"part_ref": "whole", "relevance": "project-relevant", "tier": "repo-docs"},
    ])
    assert chk.CODE_SCHEMA in _codes(rec)


def test_empty_classifications_rejected():
    assert chk.CODE_SCHEMA in _codes(_finding(classifications=[]))


# --- run() over a directory ---------------------------------------------------------
def test_run_over_fixture_dir_flags_only_the_invalid(tmp_path):
    result = chk.run([FIXTURES])
    flagged = {Path(e.path.split(":")[0]).name for e in result.errors}
    assert any(name.startswith("invalid-auto-promoted") for name in flagged)
    assert not any(name.startswith("valid-") for name in flagged)


def test_run_ignores_non_finding_records(tmp_path):
    (tmp_path / "other.yml").write_text(yaml.safe_dump({"kind": "scope-record"}))
    assert chk.run([tmp_path]).ok
