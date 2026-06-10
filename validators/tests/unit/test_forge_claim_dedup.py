"""Unit tests for the v3.5-C A-C4 ``forge_claim_dedup`` check."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import forge_claim_dedup as chk
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.forge.backlog import idempotency_key as backlog_key

FIXTURES = Path(__file__).resolve().parents[2] / "examples" / "forge-claim"

_TUPLE = ("creator-engine/creator-engine", "PVTI_x", "instance-alpha",
          "2026-06-10T08:00:00Z/PT4H")


def _fixture(name: str) -> Path:
    return FIXTURES / name


def _claim(**overrides):
    base = {
        "kind": "forge-claim", "schema_version": "1",
        "repo": _TUPLE[0], "item_id": _TUPLE[1],
        "claimant_instance": _TUPLE[2], "lease_window": _TUPLE[3],
        "claimed_at": "2026-06-10T08:00:12Z", "status": "claimed",
        "idempotency_key": chk.derive_idempotency_key(*_TUPLE),
    }
    base.update(overrides)
    return base


def _codes(record):
    return sorted({e.code for e in chk.validate_claim(record, Path("claim.ce.yml"))})


# --- registration -------------------------------------------------------------
def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg
    assert chk.CODE_SILENT_OVERWRITE in reg[chk.CHECK_NAME].frs


# --- the key derivation is drift-guarded against the v3 adapter -----------------
def test_key_derivation_in_sync_with_forge_backlog():
    # forge_claim_dedup is a SHARED check and must not import the v3
    # forge.backlog — the derivation is re-implemented; this guards the twin.
    assert chk.derive_idempotency_key(*_TUPLE) == backlog_key(*_TUPLE)


# --- fixtures (the gate's green-def) -------------------------------------------
def test_valid_claim_fixture_passes():
    result = chk.run([_fixture("valid-claim.ce.yml")])
    assert result.ok, [e.format() for e in result.errors]


def test_silent_overwrite_fixture_rejected():
    result = chk.run([_fixture("invalid-silent-overwrite.ce.yml")])
    assert any(e.code == chk.CODE_SILENT_OVERWRITE for e in result.errors)


def test_nondeterministic_dedup_fixture_rejected():
    result = chk.run([_fixture("invalid-nondeterministic-dedup.ce.yml")])
    assert any(e.code == chk.CODE_DEDUP_NONDETERMINISTIC for e in result.errors)


def test_fixture_dir_scan_flags_only_the_invalid():
    result = chk.run([FIXTURES])
    flagged = {Path(e.path.split(":")[0]).name for e in result.errors}
    assert any(name.startswith("invalid-silent-overwrite") for name in flagged)
    assert any(name.startswith("invalid-nondeterministic-dedup") for name in flagged)
    assert not any(name.startswith("valid-") for name in flagged)


# --- idempotency-key integrity ---------------------------------------------------
def test_forged_idempotency_key_rejected():
    assert chk.CODE_IDEMPOTENCY in _codes(_claim(idempotency_key="a" * 64))


def test_key_must_track_the_lease_window():
    rec = _claim(lease_window="2026-06-10T12:00:00Z/PT4H")  # key now stale
    assert chk.CODE_IDEMPOTENCY in _codes(rec)


# --- escalation, never silent overwrite -------------------------------------------
def test_contended_without_contention_block_rejected():
    assert chk.CODE_SILENT_OVERWRITE in _codes(_claim(status="contended"))


def test_contention_surfaced_as_escalation_passes():
    rec = _claim(status="contended", contention={
        "competing_claimants": ["instance-beta"],
        "observed_claimed_at": "2026-06-10T07:59:00Z",
        "surfaced_as": "escalation",
        "winner": "instance-beta",
    })
    assert _codes(rec) == []


def test_silent_overwrite_rejected_inline():
    rec = _claim(status="contended", contention={
        "competing_claimants": ["instance-beta"],
        "surfaced_as": "silent-overwrite",
    })
    assert chk.CODE_SILENT_OVERWRITE in _codes(rec)


# --- deterministic dedup bar --------------------------------------------------------
def test_dedup_high_embedding_similarity_with_pinned_model_suffices():
    rec = _claim(dedup={"duplicate_of": "PVTI_y", "evidence": [
        {"kind": "embedding_similarity", "score": 0.93, "threshold": 0.9,
         "model_ref": "embed-model@v4"},
    ]})
    assert _codes(rec) == []


def test_dedup_embedding_below_threshold_rejected():
    rec = _claim(dedup={"duplicate_of": "PVTI_y", "evidence": [
        {"kind": "embedding_similarity", "score": 0.71, "threshold": 0.9,
         "model_ref": "embed-model@v4"},
    ]})
    assert chk.CODE_DEDUP_NONDETERMINISTIC in _codes(rec)


def test_dedup_embedding_without_pinned_model_rejected():
    rec = _claim(dedup={"duplicate_of": "PVTI_y", "evidence": [
        {"kind": "embedding_similarity", "score": 0.95, "threshold": 0.9},
    ]})
    assert chk.CODE_DEDUP_NONDETERMINISTIC in _codes(rec)


def test_dedup_overlap_plus_crossref_is_additive_corroboration():
    rec = _claim(dedup={"duplicate_of": "PVTI_y", "evidence": [
        {"kind": "title_token_overlap", "shared_tokens": ["cockpit", "readmodel"]},
        {"kind": "cross_reference", "ref": "creator-engine/creator-engine#190"},
    ]})
    assert _codes(rec) == []


def test_dedup_overlap_alone_rejected():
    rec = _claim(dedup={"duplicate_of": "PVTI_y", "evidence": [
        {"kind": "title_token_overlap", "shared_tokens": ["cockpit"]},
    ]})
    assert chk.CODE_DEDUP_NONDETERMINISTIC in _codes(rec)


def test_dedup_crossref_alone_rejected():
    rec = _claim(dedup={"duplicate_of": "PVTI_y", "evidence": [
        {"kind": "cross_reference", "ref": "creator-engine/creator-engine#190"},
    ]})
    assert chk.CODE_DEDUP_NONDETERMINISTIC in _codes(rec)


def test_dedup_unknown_evidence_kind_rejected_by_schema():
    rec = _claim(dedup={"duplicate_of": "PVTI_y", "evidence": [
        {"kind": "llm_judgment"},
    ]})
    assert chk.CODE_SCHEMA in _codes(rec)


# --- schema teeth + discovery ---------------------------------------------------------
def test_missing_tuple_member_rejected_by_schema():
    rec = _claim()
    del rec["lease_window"]
    assert chk.CODE_SCHEMA in _codes(rec)


def test_non_iso_claimed_at_rejected_by_schema():
    assert chk.CODE_SCHEMA in _codes(_claim(claimed_at="yesterday"))


def test_run_ignores_non_claim_records(tmp_path):
    (tmp_path / "other.yml").write_text(yaml.safe_dump({"kind": "scope-record"}))
    assert chk.run([tmp_path]).ok
