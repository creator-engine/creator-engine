"""Integration tests for the bundled extension-hook-contract example fixtures.

The valid example (which models the committed CC-G-C hook-pack) passes the
``extension_hook_contract`` check; each invalid fixture fails with its specific
``VAL-EXT-*`` code. Also confirms the check is registered in ``--list-checks`` and
surfaces end-to-end through ``ce check``. Offline.
"""
from pathlib import Path

import pytest

from creator_engine_validator.checks import extension_hook_contract as e
from creator_engine_validator.cli import main

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "validators" / "examples" / "extension-hook-contract"


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def _codes(name: str) -> set[str]:
    result = e.run_extension_hook_contract([EXAMPLES / name])
    return {err.code for err in result.errors}


def test_valid_example_passes():
    assert e.run_extension_hook_contract([EXAMPLES / "valid-extension-hook-contract.ce.yml"]).errors == ()


@pytest.mark.parametrize("name,code", [
    ("invalid-unknown-ring.ce.yml", "VAL-EXT-RING"),
    ("invalid-ring1-claims-hard.ce.yml", "VAL-EXT-RING-COHERENCE"),
    ("invalid-secret-value.ce.yml", "VAL-EXT-SECRET"),
    ("invalid-inline-metadata.md", "VAL-EXT-NO-INLINE"),
])
def test_invalid_examples_emit_expected_code(name, code):
    assert code in _codes(name)


def test_ring1_claims_hard_is_schema_valid_but_coherence_rejected():
    # The headline rule: schema-valid (ring_1 + hard are both valid enum values) but the
    # cross-field three-ring invariant rejects it.
    codes = _codes("invalid-ring1-claims-hard.ce.yml")
    assert "VAL-EXT-RING-COHERENCE" in codes
    assert "VAL-EXT-SCHEMA" not in codes


def test_list_checks_includes_extension_hook_contract(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "extension_hook_contract" in out
    assert "VAL-EXT-RING-COHERENCE" in out


def test_cli_check_surfaces_failure_end_to_end(capsys):
    assert main(["check", "validators/examples/extension-hook-contract/invalid-ring1-claims-hard.ce.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL extension_hook_contract" in out
    assert "VAL-EXT-RING-COHERENCE" in out
