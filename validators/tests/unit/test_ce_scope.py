"""Unit tests for the v3 G-6 ``ce_scope`` check (Scope record validation)."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator import coordination as co
from creator_engine_validator.checks import ce_scope as chk
from creator_engine_validator.checks import registered_checks


def _scope(**overrides):
    base = {
        "kind": "scope-record", "record_type": "scope", "schema_version": "1",
        "scope_id": "demo-scope", "intent": "do the thing",
        "acceptance_criteria": ["it works"], "appetite": {"amount": 12.0, "unit": "$"},
        "mutation_class": "code",
        "ratification": {"approver_ref": "a" * 64, "ratified_scope_sha": "b" * 64},
        "state": "ready",
    }
    base.update(overrides)
    return base


def _codes(scope):
    return sorted({e.code for e in chk.validate_scope(scope, Path("scope.yml"))})


# --- registration + canon drift-guard ----------------------------------------
def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg and reg[chk.CHECK_NAME].frs


def test_canon_constants_in_sync_with_coordination():
    # ce_scope must NOT import the v3 coordination module (version_boundary), so the
    # canon constants are a duplicate — guard that they never drift.
    assert chk.PHASE_BY_STATE == co.PHASE_BY_STATE
    assert chk.READY_OR_LATER == co.READY_OR_LATER
    assert set(chk.SPEND_UNITS) == {"$", "%"}


# --- green paths -------------------------------------------------------------
def test_valid_ready_scope_passes():
    assert _codes(_scope()) == []


def test_draft_scope_may_omit_dor_fields():
    # a draft Scope being framed/shaped need not yet have AC / appetite / bet.
    draft = {"kind": "scope-record", "record_type": "scope", "schema_version": "1",
             "scope_id": "draft-scope", "intent": "framing", "mutation_class": "code", "state": "draft"}
    assert _codes(draft) == []


def test_matching_phase_skin_passes():
    assert _codes(_scope(phase="Shape")) == []  # ready -> Shape


def test_scope_with_binding_decisions_validates():
    # v3.5-C A-C1: the A<->B seam field — ids of Decision Records the Scope cites
    # as binding context. A-C1 adds the FIELD only; status-must-be-accepted
    # enforcement is the B-C2 readiness gate.
    assert _codes(_scope(binding_decisions=["ADR-0007"])) == []
    assert _codes(_scope(binding_decisions=["ADR-0007", "RFC-0102"])) == []


# --- teeth: DoR / appetite / ratification / skin-drift ------------------------
def test_ready_without_acceptance_criteria_fires_dor():
    assert chk.CODE_DOR_INCOMPLETE in _codes(_scope(acceptance_criteria=[]))


def test_ready_without_appetite_fires_dor():
    s = _scope(); del s["appetite"]
    assert chk.CODE_DOR_INCOMPLETE in _codes(s)


def test_bad_appetite_amount_fires_appetite_invalid():
    assert chk.CODE_APPETITE_INVALID in _codes(_scope(appetite={"amount": 0, "unit": "$"}))


def test_bad_appetite_unit_fires_appetite_invalid():
    assert chk.CODE_APPETITE_INVALID in _codes(_scope(appetite={"amount": 5, "unit": "eur"}))


def test_ready_without_ratification_fires_unbound():
    assert chk.CODE_RATIFICATION_UNBOUND in _codes(_scope(ratification=None))


def test_invalid_ratification_hex_fires_schema_not_unbound():
    # malformed shape is the schema's job; presence is the semantic check's.
    codes = _codes(_scope(ratification={"approver_ref": "short", "ratified_scope_sha": "b" * 64}))
    assert chk.CODE_SCHEMA in codes


def test_stored_phase_drift_fires_state_inconsistent():
    assert chk.CODE_STATE_INCONSISTENT in _codes(_scope(phase="Build"))  # ready -> Shape, not Build


def test_bad_kind_or_missing_required_fires_schema():
    assert chk.CODE_SCHEMA in _codes(_scope(mutation_class="bogus"))
    s = _scope(); del s["intent"]
    assert chk.CODE_SCHEMA in _codes(s)


# --- run() over a directory --------------------------------------------------
def test_run_green_on_valid_scope_dir(tmp_path):
    (tmp_path / "scope.yml").write_text(yaml.safe_dump(_scope()))
    result = chk.run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


def test_run_fires_on_invalid_scope_dir(tmp_path):
    (tmp_path / "scope.yml").write_text(yaml.safe_dump(_scope(ratification=None)))
    result = chk.run([tmp_path])
    assert not result.ok
    assert any(e.code == chk.CODE_RATIFICATION_UNBOUND for e in result.errors)


def test_run_ignores_non_scope_records(tmp_path):
    (tmp_path / "other.yml").write_text(yaml.safe_dump({"kind": "runtime-policy-record"}))
    assert chk.run([tmp_path]).ok
