from creator_engine_validator.cli import main
import pytest

pytestmark = pytest.mark.slow



def test_a2_mutation_class_listed_via_cli(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "mutation_class:" in out
    assert "FR-006" in out
    assert "FR-008" in out
    assert "FR-027a" in out
    assert "ratification:" not in out


def test_a2_well_formed_examples_pass_mutation_class(capsys):
    assert main(["check", "examples/well-formed/"]) == 0
    out = capsys.readouterr().out
    assert "PASS mutation_class" in out


def test_a2_class_action_mismatch_fixture_fails_with_fr_citations(capsys):
    assert main(["check", "examples/malformed/tasks.creator-engine.class-action-mismatch.yml"]) == 1
    out = capsys.readouterr().out
    assert "FR-027a" in out
    assert "docs/contracts/mutation-class-taxonomy.md" in out
