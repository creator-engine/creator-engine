"""Integration tests for the bundled reviewer-authority-envelope fixtures + the registered check.

The valid example passes the `reviewer_authority_envelope` check; each invalid fixture fails with
its specific `VAL-RVA-*` code; the check is registered + surfaces through `ce check`. Offline.
"""
from pathlib import Path

import pytest

from creator_engine_validator.checks import reviewer_authority_envelope as r
from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "validators" / "examples" / "reviewer-authority-envelope"


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def _codes(name: str) -> set[str]:
    return {e.code for e in r.run_reviewer_authority_envelope([EXAMPLES / name]).errors}


def test_valid_example_passes():
    assert r.run_reviewer_authority_envelope([EXAMPLES / "valid-pr-review-authority.ce.yml"]).errors == ()


@pytest.mark.parametrize("name,code", [
    ("invalid-unknown-mechanic.ce.yml", "VAL-RVA-MECHANIC"),
    ("invalid-missing-binding.ce.yml", "VAL-RVA-BINDING"),
    ("invalid-secret-value.ce.yml", "VAL-RVA-SECRET"),
])
def test_invalid_examples_emit_expected_code(name, code):
    assert code in _codes(name)


def test_list_checks_includes_reviewer_authority_envelope(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "reviewer_authority_envelope" in out
    assert "VAL-RVA-MECHANIC" in out


def test_cli_check_surfaces_failure_end_to_end(capsys):
    assert main(["check", "validators/examples/reviewer-authority-envelope/invalid-unknown-mechanic.ce.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL reviewer_authority_envelope" in out
    assert "VAL-RVA-MECHANIC" in out
