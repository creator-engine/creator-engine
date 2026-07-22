"""Tests for the Deferred-Work Ledger schema and read-back ratchet."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.deferred_work_ledger import (
    CHECK_NAME,
    CODE_FUTURE_TIMESTAMP,
    CODE_READ_BACK_STALE,
    CODE_SCHEMA,
    CODE_TIMESTAMP_ORDER,
    MAX_CLOCK_SKEW_SECONDS,
    run,
    validate_deferred_work_ledger,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 7, 22, tzinfo=UTC)


def valid_ledger() -> dict:
    return {
        "kind": "deferred-work-ledger",
        "schema_version": "1",
        "read_back_max_age_days": 14,
        "entries": [
            {
                "id": "ce604-example-residue",
                "triage_state": "buildable-bundle",
                "summary": "Example governed residue for validator coverage.",
                "provenance": {"source_kind": "review", "source_ref": "reviews/example.md"},
                "scope_ref": "vision.md#deferred-work-ledger",
                "created_at": "2026-07-01T00:00:00Z",
                "triaged_at": "2026-07-01T00:00:00Z",
                "last_read_at": "2026-07-21T00:00:00Z",
                "read_back_marker": "controller-pickup-scan",
            }
        ],
    }


def _write(path: Path, ledger: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
    return path


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs
    assert CODE_READ_BACK_STALE in checks[CHECK_NAME].frs
    assert CODE_FUTURE_TIMESTAMP in checks[CHECK_NAME].frs
    assert CODE_TIMESTAMP_ORDER in checks[CHECK_NAME].frs


def test_valid_seed_passes():
    result = run([REPO_ROOT], now=NOW)
    assert result.ok, [error.format() for error in result.errors]


def test_malformed_entry_fails_closed(tmp_path: Path):
    ledger = valid_ledger()
    del ledger["entries"][0]["scope_ref"]
    errors = validate_deferred_work_ledger(ledger, tmp_path / "ledger.yaml", now=NOW)
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_missing_read_back_marker_fails_closed(tmp_path: Path):
    ledger = valid_ledger()
    del ledger["entries"][0]["read_back_marker"]
    errors = validate_deferred_work_ledger(ledger, tmp_path / "ledger.yaml", now=NOW)
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_aged_unread_entry_fails_read_back_ratchet(tmp_path: Path):
    ledger = valid_ledger()
    ledger["entries"][0]["last_read_at"] = "2026-07-07T00:00:00Z"
    _write(tmp_path / ".ce" / "deferred" / "ledger.yaml", ledger)
    result = run([tmp_path], now=NOW)
    assert not result.ok
    assert any(error.code == CODE_READ_BACK_STALE for error in result.errors)


def test_fresh_entry_passes_read_back_ratchet(tmp_path: Path):
    ledger = valid_ledger()
    ledger["entries"][0]["last_read_at"] = (NOW - timedelta(days=14)).isoformat().replace("+00:00", "Z")
    _write(tmp_path / ".ce" / "deferred" / "ledger.yaml", ledger)
    result = run([tmp_path], now=NOW)
    assert result.ok, [error.format() for error in result.errors]


def test_ratchet_uses_schema_declared_threshold_not_a_hardcoded_value(tmp_path: Path):
    ledger = valid_ledger()
    ledger["read_back_max_age_days"] = 3
    ledger["entries"][0]["last_read_at"] = "2026-07-18T00:00:00Z"
    _write(tmp_path / ".ce" / "deferred" / "ledger.yaml", ledger)
    result = run([tmp_path], now=NOW)
    assert any(error.code == CODE_READ_BACK_STALE for error in result.errors)


def test_future_dated_last_read_fails_closed_with_entry_identity(tmp_path: Path):
    ledger = valid_ledger()
    ledger["entries"][0]["last_read_at"] = "9999-01-01T00:00:00Z"
    errors = validate_deferred_work_ledger(ledger, tmp_path / "ledger.yaml", now=NOW)
    future_errors = [error for error in errors if error.code == CODE_FUTURE_TIMESTAMP]
    assert future_errors
    assert "ce604-example-residue" in future_errors[0].message


def test_last_read_before_created_fails_closed(tmp_path: Path):
    ledger = valid_ledger()
    ledger["entries"][0]["last_read_at"] = "2026-06-30T23:59:59Z"
    errors = validate_deferred_work_ledger(ledger, tmp_path / "ledger.yaml", now=NOW)
    assert any(error.code == CODE_TIMESTAMP_ORDER for error in errors)


def test_future_created_at_fails_closed(tmp_path: Path):
    ledger = valid_ledger()
    ledger["entries"][0]["created_at"] = "9999-01-01T00:00:00Z"
    ledger["entries"][0]["last_read_at"] = "9999-01-01T00:00:00Z"
    errors = validate_deferred_work_ledger(ledger, tmp_path / "ledger.yaml", now=NOW)
    assert any(error.code == CODE_FUTURE_TIMESTAMP for error in errors)


def test_clock_skew_window_edge_passes(tmp_path: Path):
    ledger = valid_ledger()
    skew_edge = (NOW + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)).isoformat().replace("+00:00", "Z")
    ledger["entries"][0]["created_at"] = skew_edge
    ledger["entries"][0]["last_read_at"] = skew_edge
    errors = validate_deferred_work_ledger(ledger, tmp_path / "ledger.yaml", now=NOW)
    assert errors == []


def test_malformed_yaml_ledger_fails_closed_with_invalid_code(tmp_path: Path):
    ledger_path = tmp_path / ".ce" / "deferred" / "ledger.yaml"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text("entries: [unterminated\n", encoding="utf-8")
    result = run([tmp_path], now=NOW)
    assert any(error.code == "deferred_work_ledger_invalid" for error in result.errors)


@pytest.mark.parametrize("content", ["[]\n", "kind: a-different-ledger\n"])
def test_non_mapping_or_wrong_kind_ledger_fails_closed(tmp_path: Path, content: str):
    ledger_path = tmp_path / ".ce" / "deferred" / "ledger.yaml"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(content, encoding="utf-8")
    result = run([tmp_path], now=NOW)
    assert any(error.code == "deferred_work_ledger_invalid" for error in result.errors)


def test_empty_ledger_fails_closed(tmp_path: Path):
    ledger_path = tmp_path / ".ce" / "deferred" / "ledger.yaml"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text("", encoding="utf-8")
    result = run([tmp_path], now=NOW)
    assert any(error.code == "deferred_work_ledger_invalid" for error in result.errors)


def test_absent_ledger_is_skipped(tmp_path: Path):
    result = run([tmp_path], now=NOW)
    assert result.ok
