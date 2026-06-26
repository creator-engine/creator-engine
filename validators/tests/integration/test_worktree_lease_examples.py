"""Integration tests for the bundled worktree-lease example fixtures.

Confirms that:

- ``examples/well-formed/worktree-leases/`` passes
  ``worktree_lease_schema``;
- the well-formed ``lease-covered-claim/`` directory passes both
  ``worktree_lease_schema`` and ``active_work_ledger_conflicts``
  (the claim is covered by a live lease under the same controller);
- each malformed fixture under
  ``examples/malformed/worktree-leases/`` fails with its expected
  error code:
    * ``missing-required-fields.yaml`` → ``PCO-020``
    * ``bad-controller-id-pattern.yaml`` → ``PCO-020``
    * ``unknown-top-level-field.yaml`` → ``PCO-020``
    * ``cross-controller-conflict/`` → ``PCO-022``
    * ``claim-without-live-lease/`` → ``PCO-021``
- ``--list-checks`` includes ``worktree_lease_schema``;
- ``check-examples`` includes each malformed lease fixture in its
  expectation matrix.
"""

from pathlib import Path

import pytest

from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_well_formed_worktree_leases_pass(capsys):
    assert main(["scan-worktree-leases", "examples/well-formed/worktree-leases"]) == 0
    out = capsys.readouterr().out
    assert "PASS worktree_lease_schema" in out


def test_lease_covered_claim_fixture_passes_conflict_check(capsys):
    assert (
        main(
            [
                "scan-active-work-ledger-conflicts",
                "examples/well-formed/worktree-leases/lease-covered-claim",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "PASS active_work_ledger_conflicts" in out


def test_missing_required_fields_fixture_triggers_pco_020(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/worktree-leases/missing-required-fields.yaml",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL worktree_lease_schema" in out
    assert "PCO-020" in out


def test_bad_controller_id_pattern_fixture_triggers_pco_020(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/worktree-leases/bad-controller-id-pattern.yaml",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL worktree_lease_schema" in out
    assert "PCO-020" in out


def test_unknown_top_level_field_fixture_triggers_pco_020(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/worktree-leases/unknown-top-level-field.yaml",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL worktree_lease_schema" in out
    assert "PCO-020" in out


def test_cross_controller_conflict_fixture_triggers_pco_022(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/worktree-leases/cross-controller-conflict",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL active_work_ledger_conflicts" in out
    assert "PCO-022" in out


def test_claim_without_live_lease_fixture_triggers_pco_021(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/worktree-leases/claim-without-live-lease",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL active_work_ledger_conflicts" in out
    assert "PCO-021" in out


def test_list_checks_includes_worktree_lease_schema(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "worktree_lease_schema" in out
    assert "PCO-020" in out
    assert "PCO-024" in out


def test_well_formed_signed_lease_passes(capsys):
    assert main(["scan-worktree-leases", "examples/well-formed/worktree-leases/signed-lease"]) == 0
    out = capsys.readouterr().out
    assert "PASS worktree_lease_schema" in out


def test_signed_lease_bad_sig_triggers_pco024(capsys):
    assert (
        main(["check", "examples/malformed/worktree-leases/signed-lease-bad-sig"]) == 1
    )
    out = capsys.readouterr().out
    assert "FAIL worktree_lease_schema" in out
    assert "PCO-024" in out


def test_signed_lease_revoked_key_triggers_pco024(capsys):
    assert (
        main(["check", "examples/malformed/worktree-leases/signed-lease-revoked-key"]) == 1
    )
    out = capsys.readouterr().out
    assert "FAIL worktree_lease_schema" in out
    assert "PCO-024" in out


def test_signed_lease_unknown_key_triggers_pco024(capsys):
    assert (
        main(["check", "examples/malformed/worktree-leases/signed-lease-unknown-key.yaml"]) == 1
    )
    out = capsys.readouterr().out
    assert "FAIL worktree_lease_schema" in out
    assert "PCO-024" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_includes_worktree_lease_fixtures(check_examples_result):
    exit_code, out = check_examples_result
    assert "examples/malformed/worktree-leases/missing-required-fields.yaml" in out
    assert "examples/malformed/worktree-leases/bad-controller-id-pattern.yaml" in out
    assert "examples/malformed/worktree-leases/unknown-top-level-field.yaml" in out
    assert "examples/malformed/worktree-leases/cross-controller-conflict" in out
    assert "examples/malformed/worktree-leases/claim-without-live-lease" in out
    assert "examples/malformed/worktree-leases/signed-lease-bad-sig" in out
    assert "examples/malformed/worktree-leases/signed-lease-revoked-key" in out
    assert "examples/malformed/worktree-leases/signed-lease-unknown-key.yaml" in out
    assert exit_code == 0
