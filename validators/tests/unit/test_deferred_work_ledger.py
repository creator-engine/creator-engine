"""Tests for the Deferred-Work Ledger schema and read-back ratchet."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.deferred_work_ledger import (
    CHECK_NAME,
    CODE_READ_BACK_STALE,
    CODE_SCHEMA,
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
