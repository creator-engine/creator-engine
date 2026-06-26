"""Integration tests for the bundled completion-report example fixtures.

Confirms that:

- ``examples/well-formed/completion-reports/`` passes CR-001, CR-002,
  and CR-003.
- Each malformed fixture under
  ``examples/malformed/completion-reports/`` fails with its expected
  error code:
    * ``missing-envelope-sha256.yaml`` → CR-001
    * ``mismatched-sha.yaml`` → CR-002 (schema-valid; pairing fails)
    * ``blocked-without-blocker.yaml`` → CR-001
    * ``none-without-rationale.yaml`` → CR-001
    * ``missing-section-header.md`` → CR-003 (warn-only)
- ``check-examples`` includes the completion-report malformed
  fixtures in its expectation matrix.
"""

from pathlib import Path

import pytest

from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_well_formed_completion_reports_pass(capsys):
    assert (
        main(["scan-completion-reports", "examples/well-formed/completion-reports"])
        == 0
    )
    out = capsys.readouterr().out
    assert "PASS completion_report_schema" in out
    assert "PASS completion_report_required_for_envelope" in out


def test_missing_envelope_sha256_fixture_triggers_cr_001(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/completion-reports/missing-envelope-sha256.yaml",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL completion_report_schema" in out
    assert "CR-001" in out


def test_mismatched_sha_fixture_triggers_cr_002(capsys):
    assert (
        main(["check", "examples/malformed/completion-reports/mismatched-sha.yaml"])
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL completion_report_required_for_envelope" in out
    assert "CR-002" in out


def test_blocked_without_blocker_fixture_triggers_cr_001(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/completion-reports/blocked-without-blocker.yaml",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL completion_report_schema" in out
    assert "CR-001" in out


def test_none_without_rationale_fixture_triggers_cr_001(capsys):
    assert (
        main(
            [
                "check",
                "examples/malformed/completion-reports/none-without-rationale.yaml",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "FAIL completion_report_schema" in out
    assert "CR-001" in out


def test_missing_section_header_fixture_warns_cr_003(capsys):
    # CR-003 is warn-only in v1; the run still passes the section check
    # (no hard errors emitted from CR-003 itself). The YAML sidecar is
    # itself schema-valid so CR-001 passes. CR-003 emits a warning.
    main(
        [
            "scan-completion-reports",
            "examples/malformed/completion-reports/missing-section-header.yaml",
        ]
    )
    out = capsys.readouterr().out
    assert "PASS completion_report_schema" in out
    assert "WARN" in out and "CR-003" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_includes_completion_report_fixtures(check_examples_result):
    exit_code, out = check_examples_result
    assert "examples/malformed/completion-reports/missing-envelope-sha256.yaml" in out
    assert "examples/malformed/completion-reports/mismatched-sha.yaml" in out
    assert "examples/malformed/completion-reports/blocked-without-blocker.yaml" in out
    assert "examples/malformed/completion-reports/none-without-rationale.yaml" in out
    assert exit_code == 0


def test_list_checks_includes_cr_001_cr_002(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "completion_report_schema: CR-001" in out
    assert "completion_report_required_for_envelope: CR-002" in out
