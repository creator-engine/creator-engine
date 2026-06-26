"""Integration tests for the bundled harness-seat-contract fixtures + the hook-pack template.

The valid examples pass the `harness_seat_contract` check; each invalid fixture fails
with its specific `VAL-SEAT-*` code; `templates/hook-pack.template.yaml` independently
validates against the G2.006.0 `extension_hook_contract`; and the check is registered +
surfaces end-to-end through `ce check`. Offline.
"""
from pathlib import Path

import pytest

from creator_engine_validator.checks import extension_hook_contract as e
from creator_engine_validator.checks import harness_seat_contract as h
from creator_engine_validator.cli import main

REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_EXAMPLES = REPO_ROOT / "validators" / "examples" / "harness-seat-contract"
WELL_FORMED = REPO_ROOT / "examples" / "well-formed" / "harness-seat-contract"
MALFORMED = REPO_ROOT / "examples" / "malformed" / "harness-seat-contract"
TEMPLATE = REPO_ROOT / "templates" / "hook-pack.template.yaml"


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def _codes(name: str) -> set[str]:
    return {err.code for err in h.run_harness_seat_contract([MALFORMED / name]).errors}


@pytest.mark.parametrize("path", [
    WELL_FORMED / "complete-foreman-dispatch.yaml",
    LEGACY_EXAMPLES / "valid-claude-code-seat.ce.yml",
    LEGACY_EXAMPLES / "valid-codex-seat.ce.yml",
    LEGACY_EXAMPLES / "valid-hermes-seat.ce.yml",
    LEGACY_EXAMPLES / "valid-openclaw-seat.ce.yml",
])
def test_valid_examples_pass(path):
    assert h.run_harness_seat_contract([path]).errors == ()


@pytest.mark.parametrize("name,code", [
    ("missing-foreman-dispatch.yaml", "VAL-SEAT-FOREMAN-DISPATCH"),
    ("incomplete-foreman-dispatch.yaml", "VAL-SEAT-FOREMAN-DISPATCH"),
    ("unpinned-foreman-dispatch.yaml", "VAL-SEAT-FOREMAN-DISPATCH"),
])
def test_invalid_examples_emit_expected_code(name, code):
    assert code in _codes(name)


def test_hook_pack_template_validates_against_g2_006_0():
    # The hook-pack template must be a valid G2.006.0 extension_contract (cross-gate reuse).
    assert e.validate_extension_contract_file(TEMPLATE) == []


def test_list_checks_includes_harness_seat_contract(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "harness_seat_contract" in out
    assert "VAL-SEAT-FULL-PERMISSION" in out
    assert "VAL-SEAT-FOREMAN-DISPATCH" in out


def test_cli_check_surfaces_failure_end_to_end(capsys):
    assert main(["check", "examples/malformed/harness-seat-contract/unpinned-foreman-dispatch.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL harness_seat_contract" in out
    assert "VAL-SEAT-FOREMAN-DISPATCH" in out
