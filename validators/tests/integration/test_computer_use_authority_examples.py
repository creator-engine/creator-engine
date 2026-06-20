"""Integration tests for computer-use-authority-envelope fixtures and registry."""
from pathlib import Path

import pytest

from creator_engine_validator.checks import ce_computer_use_authority_envelope as c
from creator_engine_validator.cli import main

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "validators" / "examples" / "computer-use-authority-envelope"


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def _codes(name: str) -> set[str]:
    return {e.code for e in c.run_computer_use_authority_envelope([EXAMPLES / name]).errors}


@pytest.mark.parametrize(
    "name",
    [
        "valid-account-rename.ce.yml",
        "valid-app-rename.ce.yml",
        "valid-console-setting.ce.yml",
    ],
)
def test_valid_examples_pass(name):
    assert c.run_computer_use_authority_envelope([EXAMPLES / name]).errors == ()


@pytest.mark.parametrize(
    "name,code",
    [
        ("invalid-mechanic-target.ce.yml", "VAL-CUA-MECHANIC-TARGET"),
        ("invalid-open-target.ce.yml", "VAL-CUA-TARGET"),
        ("invalid-missing-dor.ce.yml", "VAL-CUA-DOR-INCOMPLETE"),
        ("invalid-ratification-binding.ce.yml", "VAL-CUA-RATIFICATION"),
        ("invalid-secret-value.ce.yml", "VAL-CUA-SECRET"),
        ("invalid-secret-value-numeric.ce.yml", "VAL-CUA-SECRET"),
    ],
)
def test_invalid_examples_emit_expected_code(name, code):
    assert code in _codes(name)


def test_list_checks_includes_computer_use_authority(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "ce_computer_use_authority_envelope" in out
    assert "VAL-CUA-MECHANIC-TARGET" in out


def test_cli_check_surfaces_failure_end_to_end(capsys):
    assert main(["check", "validators/examples/computer-use-authority-envelope/invalid-open-target.ce.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_computer_use_authority_envelope" in out
    assert "VAL-CUA-TARGET" in out
