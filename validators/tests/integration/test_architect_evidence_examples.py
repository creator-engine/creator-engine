from creator_engine_validator.cli import main


def test_architect_evidence_well_formed_example_passes(capsys):
    assert main(["check", "examples/well-formed/architect-evidence/example-architect-evidence.yml"]) == 0
    out = capsys.readouterr().out
    assert "PASS architect_evidence_schema" in out


def test_architect_evidence_missing_verdict_example_fails_with_fr001(capsys):
    assert main(["check", "examples/malformed/architect-evidence/missing-verdict.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL architect_evidence_schema" in out
    assert "FR-001" in out
    assert "docs/contracts/architect-evidence.md" in out


def test_architect_evidence_invalid_verdict_value_example_fails_with_fr001(capsys):
    assert main(["check", "examples/malformed/architect-evidence/invalid-verdict-value.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL architect_evidence_schema" in out
    assert "FR-001" in out
    assert "verdict" in out
    assert "docs/contracts/architect-evidence.md" in out


def test_architect_evidence_missing_non_ratification_statement_example_fails_with_fr001(capsys):
    assert main(["check", "examples/malformed/architect-evidence/missing-non-ratification-statement.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL architect_evidence_schema" in out
    assert "FR-001" in out
    assert "non_ratification_statement" in out
    assert "docs/contracts/architect-evidence.md" in out


def test_architect_evidence_template_passes(capsys):
    assert main(["check", "templates/architect-evidence.template.yaml"]) == 0
    out = capsys.readouterr().out
    assert "PASS architect_evidence_schema" in out


def test_check_examples_includes_architect_evidence(capsys):
    assert main(["check-examples"]) == 0
    out = capsys.readouterr().out
    assert "examples/malformed/architect-evidence/missing-verdict.yml" in out
    assert "examples/malformed/architect-evidence/invalid-verdict-value.yml" in out
    assert "examples/malformed/architect-evidence/missing-non-ratification-statement.yml" in out
