"""Integration tests for bundled seat-class-policy examples."""

from pathlib import Path

import pytest

from creator_engine_validator.checks import seat_class_policy as chk
from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]
WELL_FORMED = REPO_ROOT / "examples" / "well-formed" / "seat-class-policy"
MALFORMED = REPO_ROOT / "examples" / "malformed" / "seat-class-policy"


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


@pytest.mark.parametrize("name", ["minimal.yaml", "foreman.yaml", "worker.yaml"])
def test_well_formed_examples_pass(name):
    assert chk.run([WELL_FORMED / name]).errors == ()


@pytest.mark.parametrize(
    "name,code",
    [
        ("default-not-foreman.yaml", "VAL-SEAT-CLASS-DEFAULT"),
        ("bad-mutation-class.yaml", "VAL-SEAT-CLASS-MUTATION"),
        ("secret-value.yaml", "VAL-SEAT-CLASS-SECRET"),
        ("bad-depth.yaml", "VAL-SEAT-CLASS-RECURSION"),
        ("worker-seat-class.yaml", "VAL-SEAT-CLASS-FOREMAN"),
        ("missing-foreman-dispatch.yaml", "VAL-SEAT-CLASS-FOREMAN-DISPATCH"),
        ("incomplete-foreman-dispatch.yaml", "VAL-SEAT-CLASS-FOREMAN-DISPATCH"),
    ],
)
def test_malformed_examples_emit_expected_code(name, code):
    assert code in {err.code for err in chk.run([MALFORMED / name]).errors}


def test_list_checks_includes_seat_class_policy(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "seat_class_policy" in out
    assert "VAL-SEAT-CLASS-DEFAULT" in out


def test_cli_check_surfaces_failure_end_to_end(capsys):
    assert main(["check", "examples/malformed/seat-class-policy/default-not-foreman.yaml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL seat_class_policy" in out
    assert "VAL-SEAT-CLASS-DEFAULT" in out
