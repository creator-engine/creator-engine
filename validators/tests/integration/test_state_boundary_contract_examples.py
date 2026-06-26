"""Integration coverage for bundled state-boundary-contract examples (RV1-021)."""

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
    exit_code = main(["scan-state-boundary-contract", "examples/well-formed/state-boundary-contract"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "PASS state_boundary_contract" in captured.out


def test_scan_rejects_tracked_write_root(capsys):
    exit_code = main(
        ["scan-state-boundary-contract", "examples/malformed/state-boundary-contract/tracked-write-root.yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL state_boundary_contract" in captured.out
    assert "RV1-021-WRITE" in captured.out


def test_scan_rejects_secret_config_value(capsys):
    exit_code = main(
        ["scan-state-boundary-contract", "examples/malformed/state-boundary-contract/secret-config-value.yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL state_boundary_contract" in captured.out
    assert "RV1-021-SECRET" in captured.out


def test_scan_rejects_hermes_not_ignored(capsys):
    exit_code = main(
        ["scan-state-boundary-contract", "examples/malformed/state-boundary-contract/hermes-not-ignored.yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL state_boundary_contract" in captured.out
    assert "RV1-021-IGNORE" in captured.out
