"""Integration coverage for bundled state-version-record examples (RV1-022)."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_scan_accepts_well_formed_examples(capsys):
    exit_code = main(["scan-state-version-record", "examples/well-formed/state-version-record"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "PASS state_version_record" in captured.out


def test_scan_rejects_stale_version(capsys):
    exit_code = main(
        ["scan-state-version-record", "examples/malformed/state-version-record/stale-version.yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL state_version_record" in captured.out
    assert "RV1-022-STALE" in captured.out


def test_scan_rejects_invalid_status(capsys):
    exit_code = main(
        ["scan-state-version-record", "examples/malformed/state-version-record/invalid-status.yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL state_version_record" in captured.out
    assert "RV1-022" in captured.out
