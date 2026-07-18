"""Focused tests for the CE605 standing-rider validator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import standing_rider as chk


NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def _note(**overrides):
    note = {
        "kind": "standing-rider-note",
        "schema_version": "1",
        "rider_id": "CE605",
        "sequence": 1,
        "observed_at": "2026-07-11T12:00:00Z",
        "cadence_due_at": "2026-07-18T12:00:00Z",
        "source_state": "authenticated",
        "source_refs": [{
            "class": "advisory-finding",
            "path_or_digest": "finding:ce605-input",
            "sha256": "a" * 64,
        }],
        "assessment": "no_change",
        "tripwire": "clear",
        "previous_note_sha256": "0" * 64,
    }
    note.update(overrides)
    return chk.with_note_sha256(note)


def _line(note: dict) -> str:
    return chk.canonical_note_bytes(note).decode("utf-8")


def _codes(note: dict, *, previous=None, now=NOW):
    return {error.code for error in chk.validate_note(note, Path("note.ndjson"), previous=previous, now=now)}


def test_registered_in_check_surface():
    registry = registered_checks()
    assert chk.CHECK_NAME in registry
    assert chk.CODE_CHAIN in registry[chk.CHECK_NAME].frs


def test_valid_genesis_and_continuation_pass():
    first = _note()
    second = _note(
        sequence=2,
        observed_at="2026-07-18T12:00:00Z",
        cadence_due_at="2026-07-25T12:00:00Z",
        previous_note_sha256=first["note_sha256"],
    )
    assert not _codes(first, now=datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
    assert not _codes(second, previous=first, now=NOW)


def test_canonicalization_is_stable_and_digest_excludes_digest_field():
    note = _note()
    expected = hashlib.sha256(chk.canonical_note_bytes(note, include_digest=False)).hexdigest()
    assert note["note_sha256"] == expected
    assert _line(note) == json.dumps(note, sort_keys=True, separators=(",", ":")) + "\n"


def test_bad_digest_and_predecessor_rewrite_are_rejected():
    first = _note()
    bad_digest = dict(first, note_sha256="b" * 64)
    assert chk.CODE_DIGEST in _codes(bad_digest, now=datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
    second = _note(
        sequence=2,
        observed_at="2026-07-18T12:00:00Z",
        cadence_due_at="2026-07-25T12:00:00Z",
        previous_note_sha256="b" * 64,
    )
    assert chk.CODE_CHAIN in _codes(second, previous=first)


def test_source_states_and_private_references_tripwire():
    unavailable = _note(
        source_state="unavailable", assessment="deferred", tripwire="source_unavailable",
        cadence_due_at="2026-07-25T12:00:00Z",
    )
    assert not _codes(unavailable)
    stale = _note(
        source_state="stale", assessment="deferred", tripwire="immediate_review_required",
        cadence_due_at="2026-07-25T12:00:00Z",
    )
    assert not _codes(stale)
    contradictory = _note(
        source_state="contradictory", assessment="deferred", tripwire="immediate_review_required",
        cadence_due_at="2026-07-25T12:00:00Z",
    )
    assert not _codes(contradictory)
    private = _note(source_refs=[{
        "class": "advisory-finding",
        "path_or_digest": "https://private.example.invalid/token",
        "sha256": "a" * 64,
    }], cadence_due_at="2026-07-25T12:00:00Z")
    assert chk.CODE_SOURCE_REF in _codes(private)


def test_no_change_requires_authenticated_sources_and_clear_tripwire():
    note = _note(source_state="stale", tripwire="immediate_review_required")
    assert chk.CODE_TRIPWIRE in _codes(note)


def test_cadence_due_and_multi_interval_catch_up_are_deterministic():
    last = _note(cadence_due_at="2026-07-04T12:00:00Z")
    evaluation = chk.evaluate_cadence(last, NOW)
    assert evaluation.due is True
    assert evaluation.next_due_at == datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    assert evaluation.missed_boundaries == 2
    assert chk.CODE_CADENCE in _codes(last, now=NOW)


def test_future_input_clock_is_rejected():
    note = _note(observed_at="2026-07-19T12:00:00Z")
    assert chk.CODE_CLOCK in _codes(note)


def test_ndjson_chain_rejects_duplicate_sequences_and_noncanonical_lines(tmp_path):
    first = _note()
    duplicate = _note(sequence=1, cadence_due_at="2026-07-25T12:00:00Z")
    path = tmp_path / "notes.ndjson"
    path.write_text(_line(first) + _line(duplicate), encoding="utf-8")
    assert chk.CODE_CHAIN in {error.code for error in chk.validate_note_stream(path, now=NOW)}
    path.write_text(json.dumps(first, indent=2) + "\n", encoding="utf-8")
    assert chk.CODE_CANONICAL in {error.code for error in chk.validate_note_stream(path, now=NOW)}


def test_run_checks_proposed_adr_and_duplicate_note_artifact(tmp_path):
    decisions = tmp_path / "docs" / "decisions"
    decisions.mkdir(parents=True)
    (decisions / "ADR-0605-standing-rider-cadence.md").write_text(
        "---\n"
        "kind: decision-record\nrecord_type: adr\nschema_version: '1'\n"
        "id: ADR-0605\ntitle: standing rider\nstatus: proposed\n"
        "date: '2026-07-11'\ndecision_makers: [ce-dev-3]\n"
        "review_by: '2026-10-11'\nmutation_class: governance\n"
        "evidence_refs: [{kind: doc, ref: docs/x.md, tag: x}]\n---\n# rider\n",
        encoding="utf-8",
    )
    (decisions / "ce605-standing-rider-notes.ndjson").write_text(_line(_note()), encoding="utf-8")
    duplicate_dir = tmp_path / "docs" / "alternate"
    duplicate_dir.mkdir()
    (duplicate_dir / "ce605-standing-rider-notes.ndjson").write_text(_line(_note()), encoding="utf-8")
    codes = {error.code for error in chk.run([tmp_path]).errors}
    assert chk.CODE_UNRATIFIED in codes
    assert chk.CODE_ARTIFACT in codes
