"""Integration tests for bundled Pane Registry fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_well_formed_pane_registry_examples_pass(capsys):
    assert main(["scan-pane-registry", "examples/well-formed/pane-registry"]) == 0
    out = capsys.readouterr().out
    assert "PASS pane_registry" in out


def test_malformed_plain_terminal_fixture_triggers_pco_049(capsys):
    assert main(["scan-pane-registry", "examples/malformed/pane-registry/plain-terminal.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL pane_registry" in out
    assert "PCO-049" in out


def test_malformed_duplicate_live_pane_fixture_triggers_pco_051(capsys):
    assert main(["scan-pane-registry", "examples/malformed/pane-registry/duplicate-live-pane"]) == 1
    out = capsys.readouterr().out
    assert "FAIL pane_registry" in out
    assert "PCO-051" in out


def test_malformed_container_binding_fixture_triggers_pco_052(capsys):
    assert main(["scan-pane-registry", "examples/malformed/pane-registry/container-binding-mismatch"]) == 1
    out = capsys.readouterr().out
    assert "FAIL pane_registry" in out
    assert "PCO-052" in out


def test_list_checks_includes_pane_registry(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "pane_registry: PCO-046, PCO-047, PCO-048, PCO-049, PCO-050, PCO-051, PCO-052, PCO-053" in out
