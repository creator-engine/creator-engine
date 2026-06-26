from creator_engine_validator.cli import main
import pytest

pytestmark = pytest.mark.slow



def test_us2_well_formed_examples_pass(capsys):
    assert main(["check", "examples/well-formed/"]) == 0
    out = capsys.readouterr().out
    assert "PASS sidecar_conformance" in out
    assert "PASS definition_of_ready" in out
    assert "PASS duplicate_spec_id" in out


def test_us2_missing_acceptance_fixture_fails_with_fr013(capsys):
    assert main(["check", "examples/malformed/spec.creator-engine.missing-acceptance.yml"]) == 1
    out = capsys.readouterr().out
    assert "FR-013" in out
    assert "docs/contracts/definition-of-ready.md" in out


def test_us2_duplicate_spec_id_fixture_fails_with_fr027a(capsys):
    assert main(["check", "examples/malformed/duplicate-spec-id/"]) == 1
    out = capsys.readouterr().out
    assert "FR-027a" in out
    assert "docs/contracts/spec-wrapper-sidecar.md" in out
