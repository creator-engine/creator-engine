"""Integration tests for the bundled harness-seat-contract fixtures + the hook-pack template.

The valid example (modeling the committed Claude Code seat) passes the
`harness_seat_contract` check; each invalid fixture fails with its specific `VAL-SEAT-*`
code; `templates/hook-pack.template.yaml` independently validates against the G2.006.0
`extension_hook_contract`; and the check is registered + surfaces end-to-end through
`ce check`. Offline.
"""
from pathlib import Path

import pytest

from creator_engine_validator.checks import extension_hook_contract as e
from creator_engine_validator.checks import harness_seat_contract as h
from creator_engine_validator.cli import main

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "validators" / "examples" / "harness-seat-contract"
TEMPLATE = REPO_ROOT / "templates" / "hook-pack.template.yaml"


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def _codes(name: str) -> set[str]:
    return {err.code for err in h.run_harness_seat_contract([EXAMPLES / name]).errors}


@pytest.mark.parametrize("name", [
    "valid-claude-code-seat.ce.yml",   # G2.007.0 reference instance
    "valid-codex-seat.ce.yml",         # G2.007.1: codex binds --yolo
    "valid-hermes-seat.ce.yml",        # G2.007.1: hermes binds --profile creator-engine
    "valid-openclaw-seat.ce.yml",      # G2.007.1: openclaw SEAM (full_permission_mode: false)
])
def test_valid_examples_pass(name):
    assert h.run_harness_seat_contract([EXAMPLES / name]).errors == ()


@pytest.mark.parametrize("name,code", [
    ("invalid-unknown-harness.ce.yml", "VAL-SEAT-HARNESS"),
    ("invalid-full-permission-without-ring0.ce.yml", "VAL-SEAT-FULL-PERMISSION"),
    ("invalid-permission-flag-mismatch.ce.yml", "VAL-SEAT-PERMISSION-FLAG"),
    ("invalid-permits-prohibited-flag.ce.yml", "VAL-SEAT-PROHIBITED"),
    ("invalid-nondefeasible-hookpack.ce.yml", "VAL-SEAT-HOOKPACK"),
    ("invalid-hermes-flag-mismatch.ce.yml", "VAL-SEAT-PERMISSION-FLAG"),  # G2.007.1 hermes binding
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


def test_cli_check_surfaces_failure_end_to_end(capsys):
    assert main(["check", "validators/examples/harness-seat-contract/invalid-full-permission-without-ring0.ce.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL harness_seat_contract" in out
    assert "VAL-SEAT-FULL-PERMISSION" in out
