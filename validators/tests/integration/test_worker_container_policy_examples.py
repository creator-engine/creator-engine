"""Integration tests for bundled worker-container-policy example fixtures.

Confirms that:

- All three well-formed policy examples pass ``worker_container_policy``;
- ``examples/malformed/worker-container-policies/missing-role.yaml``
  fails with ``PCO-040``;
- ``examples/malformed/worker-container-policies/forbidden-home-mount.yaml``
  fails with ``PCO-045``;
- ``examples/malformed/worker-container-policies/forbidden-engine-socket.yaml``
  fails with ``PCO-045``;
- ``examples/malformed/worker-container-policies/controller-key-secret-allowlisted.yaml``
  fails with ``PCO-045``;
- ``--list-checks`` includes ``worker_container_policy``;
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


def test_well_formed_architect_research_policy_passes(capsys):
    assert main(["check", "examples/well-formed/worker-container-policies/podman-architect-research.yaml"]) == 0
    out = capsys.readouterr().out
    assert "PASS worker_container_policy" in out


def test_well_formed_implementer_policy_passes(capsys):
    assert main(["check", "examples/well-formed/worker-container-policies/podman-implementer.yaml"]) == 0
    out = capsys.readouterr().out
    assert "PASS worker_container_policy" in out


def test_well_formed_verification_policy_passes(capsys):
    assert main(["check", "examples/well-formed/worker-container-policies/podman-verification.yaml"]) == 0
    out = capsys.readouterr().out
    assert "PASS worker_container_policy" in out


def test_missing_role_fixture_triggers_pco_040(capsys):
    assert main(["check", "examples/malformed/worker-container-policies/missing-role.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL worker_container_policy" in out
    assert "PCO-040" in out


def test_forbidden_home_mount_fixture_triggers_pco_045(capsys):
    assert main(["check", "examples/malformed/worker-container-policies/forbidden-home-mount.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL worker_container_policy" in out
    assert "PCO-045" in out


def test_forbidden_engine_socket_fixture_triggers_pco_045(capsys):
    assert main(["check", "examples/malformed/worker-container-policies/forbidden-engine-socket.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL worker_container_policy" in out
    assert "PCO-045" in out


def test_controller_key_secret_allowlisted_fixture_triggers_pco_045(capsys):
    assert main(["check", "examples/malformed/worker-container-policies/controller-key-secret-allowlisted.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL worker_container_policy" in out
    assert "PCO-045" in out


def test_list_checks_includes_worker_container_policy(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "worker_container_policy: PCO-040, PCO-045" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_succeeds(check_examples_result):
    exit_code, out = check_examples_result
    assert exit_code == 0, f"check-examples failed:\n{out}"
