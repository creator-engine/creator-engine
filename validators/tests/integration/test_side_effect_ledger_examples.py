"""Integration tests for bundled Side-Effect Ledger fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.cli import main


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_well_formed_side_effect_ledger_examples_pass(capsys):
    assert main(["scan-side-effect-ledger", "examples/well-formed/side-effect-ledger"]) == 0
    out = capsys.readouterr().out
    assert "PASS side_effect_ledger" in out


def test_malformed_missing_claim_fixture_triggers_pco_056(capsys):
    assert main(["scan-side-effect-ledger", "examples/malformed/side-effect-ledger/missing-claim"]) == 1
    out = capsys.readouterr().out
    assert "FAIL side_effect_ledger" in out
    assert "PCO-056" in out


def test_malformed_duplicate_effect_id_fixture_triggers_pco_057(capsys):
    assert main(["scan-side-effect-ledger", "examples/malformed/side-effect-ledger/duplicate-effect-id"]) == 1
    out = capsys.readouterr().out
    assert "FAIL side_effect_ledger" in out
    assert "PCO-057" in out


def test_malformed_secret_payload_fixture_triggers_pco_059(capsys):
    assert main(["scan-side-effect-ledger", "examples/malformed/side-effect-ledger/secret-payload.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL side_effect_ledger" in out
    assert "PCO-059" in out


def test_malformed_unknown_field_fixture_triggers_pco_063(capsys):
    assert main(["scan-side-effect-ledger", "examples/malformed/side-effect-ledger/unknown-field.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL side_effect_ledger" in out
    assert "PCO-063" in out


def test_list_checks_includes_side_effect_ledger(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert (
        "side_effect_ledger: PCO-055, PCO-056, PCO-057, PCO-058, "
        "PCO-059, PCO-060, PCO-061, PCO-062, PCO-063"
    ) in out
