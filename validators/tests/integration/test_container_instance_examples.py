"""Integration tests for bundled container-instance example fixtures.

Confirms that:

- Both well-formed instance examples pass ``container_instance``;
- ``examples/malformed/container-instances/missing-policy-sha.yaml``
  fails with ``PCO-041``;
- ``examples/malformed/container-instances/image-sha-mismatch.yaml``
  fails with ``PCO-044``;
- ``examples/malformed/container-instances/outlives-released-claim.yaml``
  fails with ``PCO-043``;
- ``--list-checks`` includes ``container_instance``;
- ``check-examples`` succeeds (well-formed examples pass all checks).
"""

from pathlib import Path

import pytest

from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_well_formed_running_instance_passes(capsys):
    assert main(["check", "examples/well-formed/container-instances/running-implementer.yaml"]) == 0
    out = capsys.readouterr().out
    assert "PASS container_instance" in out


def test_well_formed_stopped_instance_passes(capsys):
    assert main(["check", "examples/well-formed/container-instances/stopped-implementer.yaml"]) == 0
    out = capsys.readouterr().out
    assert "PASS container_instance" in out


def test_missing_policy_sha_fixture_triggers_pco_041(capsys):
    assert main(["check", "examples/malformed/container-instances/missing-policy-sha.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL container_instance" in out
    assert "PCO-041" in out


def test_image_sha_mismatch_fixture_triggers_pco_044(capsys):
    assert main(["check", "examples/malformed/container-instances/image-sha-mismatch.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL container_instance" in out
    assert "PCO-044" in out


def test_outlives_released_claim_fixture_triggers_pco_043(capsys):
    assert main(["check", "examples/malformed/container-instances/outlives-released-claim.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL container_instance" in out
    assert "PCO-043" in out


def test_list_checks_includes_container_instance(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "container_instance: PCO-041, PCO-043, PCO-044" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_succeeds(check_examples_result):
    exit_code, out = check_examples_result
    assert exit_code == 0, f"check-examples failed:\n{out}"
