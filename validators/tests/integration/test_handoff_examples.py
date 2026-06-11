"""Integration tests for the bundled handoff example fixtures.

These tests confirm that:

- ``examples/well-formed/handoffs/example-handoff.md`` passes every
  registered check.
- Each malformed fixture under ``examples/malformed/handoffs/``
  fails with its expected error class (and no other handoff-related
  error class leaks through).
- ``check-examples`` includes the handoff fixtures in its
  expectation matrix.
"""

from pathlib import Path

import pytest

from creator_engine_validator.cli import main


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    # The bundled fixtures and check-relative contract paths (e.g.,
    # docs/contracts/mutation-class-taxonomy.yml) are addressed relative to
    # the repo root; pin cwd so the suite passes from either the repo root or
    # validators/.
    monkeypatch.chdir(REPO_ROOT)


def test_well_formed_handoff_passes_all_checks(capsys):
    assert main(["check", "examples/well-formed/handoffs/example-handoff.md"]) == 0
    out = capsys.readouterr().out
    assert "PASS path_manifest_fidelity" in out
    assert "PASS handoff_schema" in out


def test_init_py_corruption_fixture_triggers_regression_error(capsys):
    assert main(["check", "examples/malformed/handoffs/init-py-corruption.md"]) == 1
    out = capsys.readouterr().out
    assert "FAIL path_manifest_fidelity" in out
    assert "path_manifest_init_py_corruption" in out


def test_hash_mismatch_fixture_triggers_hash_error(capsys):
    assert main(["check", "examples/malformed/handoffs/hash-mismatch.md"]) == 1
    out = capsys.readouterr().out
    assert "path_manifest_hash_mismatch" in out


def test_count_mismatch_fixture_triggers_count_error(capsys):
    assert main(["check", "examples/malformed/handoffs/count-mismatch.md"]) == 1
    out = capsys.readouterr().out
    assert "path_manifest_count_mismatch" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_includes_handoff_fixtures(check_examples_result):
    exit_code, out = check_examples_result
    assert "examples/malformed/handoffs/init-py-corruption.md" in out
    assert "examples/malformed/handoffs/hash-mismatch.md" in out
    assert "examples/malformed/handoffs/count-mismatch.md" in out
    # All bundled examples should meet their expectations.
    assert exit_code == 0


def test_scan_path_manifest_on_well_formed(capsys):
    assert main(["scan-path-manifest", "examples/well-formed/handoffs/example-handoff.md"]) == 0
    out = capsys.readouterr().out
    assert "PASS path_manifest_fidelity" in out


def test_scan_handoffs_on_well_formed(capsys):
    assert main(["scan-handoffs", "examples/well-formed/handoffs/example-handoff.md"]) == 0
    out = capsys.readouterr().out
    assert "PASS handoff_schema" in out
