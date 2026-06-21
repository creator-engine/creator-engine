"""Unit tests for the F1 ``work_sizing`` schema check."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import work_sizing as chk
from creator_engine_validator.work_sizing import size_ceremony


def _record(**overrides):
    record = size_ceremony("story", "code")
    record.update(overrides)
    return record


def _codes(record):
    return sorted({e.code for e in chk.validate_work_sizing(record, Path("sizing.yml"))})


def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg and reg[chk.CHECK_NAME].frs


def test_valid_sizing_record_passes():
    assert _codes(_record()) == []


def test_schema_error_fires_on_bad_class():
    assert chk.CODE_SCHEMA in _codes(_record(work_class="bogus"))


def test_schema_error_fires_on_empty_artifact_set():
    assert chk.CODE_SCHEMA in _codes(_record(artifact_set=[]))


def test_projection_drift_fires_on_schema_valid_mismatched_gates():
    record = _record(
        mutation_class="docs",
        ratification_gates=["operator_front_bet", "operator_merge"],
        adr_required=True,
    )
    assert chk.CODE_INVALID in _codes(record)


def test_run_green_on_valid_sizing_record_dir(tmp_path):
    (tmp_path / "sizing.yml").write_text(yaml.safe_dump(_record()))
    result = chk.run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


def test_run_fires_on_invalid_sizing_record_dir(tmp_path):
    (tmp_path / "sizing.yml").write_text(yaml.safe_dump(_record(ratification_gates=[])))
    result = chk.run([tmp_path])
    assert not result.ok
    assert any(e.code == chk.CODE_SCHEMA for e in result.errors)


def test_run_ignores_non_sizing_records_and_schema_paths(tmp_path):
    (tmp_path / "other.yml").write_text(yaml.safe_dump({"kind": "scope-record"}))
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "sizing.yml").write_text(yaml.safe_dump(_record()))
    assert chk.run([tmp_path]).ok
