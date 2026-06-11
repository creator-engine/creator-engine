import pytest

from creator_engine_validator.cli import main


def test_review_evidence_well_formed_example_passes(capsys):
    assert main(["check", "examples/well-formed/review-evidence/example-review-evidence.yml"]) == 0
    out = capsys.readouterr().out
    assert "PASS review_evidence_schema" in out


def test_review_evidence_missing_verdict_example_fails_with_fr001(capsys):
    assert main(["check", "examples/malformed/review-evidence/missing-verdict.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL review_evidence_schema" in out
    assert "FR-001" in out
    assert "docs/contracts/review-evidence.md" in out


def test_review_evidence_invalid_verdict_value_example_fails_with_fr001(capsys):
    assert main(["check", "examples/malformed/review-evidence/invalid-verdict-value.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL review_evidence_schema" in out
    assert "FR-001" in out
    assert "verdict" in out
    assert "docs/contracts/review-evidence.md" in out


def test_review_evidence_missing_non_ratification_statement_example_fails_with_fr001(capsys):
    assert main(["check", "examples/malformed/review-evidence/missing-non-ratification-statement.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL review_evidence_schema" in out
    assert "FR-001" in out
    assert "non_ratification_statement" in out
    assert "docs/contracts/review-evidence.md" in out


def test_review_evidence_template_passes(capsys):
    assert main(["check", "templates/review-evidence.template.yaml"]) == 0
    out = capsys.readouterr().out
    assert "PASS review_evidence_schema" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_includes_review_evidence(check_examples_result):
    exit_code, out = check_examples_result
    assert "examples/malformed/review-evidence/missing-verdict.yml" in out
    assert "examples/malformed/review-evidence/invalid-verdict-value.yml" in out
    assert "examples/malformed/review-evidence/missing-non-ratification-statement.yml" in out
    assert exit_code == 0
