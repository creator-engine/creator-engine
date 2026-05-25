"""Integration coverage for bundled controller-runtime-contract examples (RV1-020)."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.cli import main

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_scan_accepts_well_formed_examples(capsys):
    exit_code = main(["scan-controller-runtime-contract", "examples/well-formed/controller-runtime-contract"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "PASS controller_runtime_contract" in captured.out


def test_scan_rejects_misclassified_hosted_authority(capsys):
    exit_code = main(
        ["scan-controller-runtime-contract", "examples/malformed/controller-runtime-contract/misclassified-hosted-authority.yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL controller_runtime_contract" in captured.out
    assert "RV1-020-AUTH" in captured.out


def test_scan_rejects_secret_value(capsys):
    exit_code = main(
        ["scan-controller-runtime-contract", "examples/malformed/controller-runtime-contract/secret-value.yaml"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL controller_runtime_contract" in captured.out
    assert "RV1-020-SECRET" in captured.out
