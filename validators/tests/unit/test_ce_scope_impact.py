"""Unit tests for the warning-only ``ce_scope_impact`` check."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator import cli
from creator_engine_validator.checks import ce_scope, ce_scope_impact as chk, registered_checks


def _scope(**overrides):
    base = {
        "kind": "scope-record",
        "record_type": "scope",
        "schema_version": "1",
        "scope_id": "demo-scope",
        "intent": "do the thing",
        "acceptance_criteria": ["it works"],
        "appetite": {"amount": 12.0, "unit": "$"},
        "mutation_class": "code",
        "ratification": {"approver_ref": "a" * 64, "ratified_scope_sha": "0" * 64},
        "state": "ratified",
    }
    base.update(overrides)
    return base


def _with_current_sha(scope):
    scope = dict(scope)
    ratification = dict(scope["ratification"])
    scope["ratification"] = ratification
    ratification["ratified_scope_sha"] = chk.ratified_scope_sha(scope)
    return scope


def _codes(result):
    return [warning.code for warning in result.warnings]


def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg and reg[chk.CHECK_NAME].frs


def test_drift_detected_as_warning_not_error():
    result = chk.run([Path("unused.yml")])
    assert result.ok
    assert result.errors == ()

    warnings = chk.validate_scope_impact(_scope(), Path("scope.yml"))
    assert [warning.code for warning in warnings] == [chk.CODE_SCOPE_CONTENT_DRIFT]


def test_downstream_refs_each_flagged_when_scope_drifts():
    scope = _scope(
        downstream_refs=[
            {"kind": "plan", "path": "docs/plans/demo.md"},
            {"kind": "decision_record", "id": "ADR-0007"},
            {"kind": "test_pattern", "glob": "validators/tests/unit/test_demo.py"},
            {"kind": "validator_check", "name": "ce_scope"},
            {"kind": "scope", "scope_id": "follow-up-scope"},
        ]
    )

    warnings = chk.validate_scope_impact(scope, Path("scope.yml"))

    assert [warning.code for warning in warnings] == [
        chk.CODE_SCOPE_CONTENT_DRIFT,
        chk.CODE_DOWNSTREAM_AFFECTED,
        chk.CODE_DOWNSTREAM_AFFECTED,
        chk.CODE_DOWNSTREAM_AFFECTED,
        chk.CODE_DOWNSTREAM_AFFECTED,
        chk.CODE_DOWNSTREAM_AFFECTED,
    ]
    messages = [warning.message for warning in warnings]
    assert "plan path=docs/plans/demo.md" in messages[1]
    assert "decision_record id=ADR-0007" in messages[2]
    assert "test_pattern glob=validators/tests/unit/test_demo.py" in messages[3]
    assert "validator_check name=ce_scope" in messages[4]
    assert "scope scope_id=follow-up-scope" in messages[5]


def test_no_drift_is_silent():
    result = chk.validate_scope_impact(_with_current_sha(_scope()), Path("scope.yml"))
    assert result == []


def test_scope_without_downstream_refs_is_green_when_not_drifted():
    scope = _with_current_sha(_scope())
    assert "downstream_refs" not in scope
    assert ce_scope.validate_scope(scope, Path("scope.yml")) == []
    assert chk.validate_scope_impact(scope, Path("scope.yml")) == []


def test_downstream_refs_are_valid_scope_schema():
    scope = _scope(
        downstream_refs=[
            {"kind": "plan", "path": "docs/plans/demo.md"},
            {"kind": "decision_record", "id": "ADR-0007"},
            {"kind": "test_pattern", "glob": "validators/tests/unit/test_*.py"},
            {"kind": "validator_check", "name": "ce_scope"},
            {"kind": "scope", "scope_id": "follow-up-scope"},
        ]
    )
    assert ce_scope.validate_scope(scope, Path("scope.yml")) == []


def test_run_reports_warnings_without_blocking_cli_result(tmp_path, capsys):
    (tmp_path / "scope.yml").write_text(yaml.safe_dump(_scope()), encoding="utf-8")

    result = chk.run([tmp_path])
    assert result.ok
    assert _codes(result) == [chk.CODE_SCOPE_CONTENT_DRIFT]
    assert cli._emit_results([result], json_output=False) == 0

    out = capsys.readouterr().out
    assert "PASS ce_scope_impact" in out
    assert "WARN IMPACT-SCOPE-CONTENT-DRIFT" in out
