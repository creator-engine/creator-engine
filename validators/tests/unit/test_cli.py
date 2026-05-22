from creator_engine_validator.cli import main


def test_list_checks_includes_identity(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "identity" in out
    assert "FR-001" in out


def test_list_checks_includes_pco024(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "worktree_lease_schema" in out
    assert "PCO-024" in out


def test_check_well_formed_identity_returns_zero(capsys):
    assert main(["check", "examples/well-formed/identity-record.yml"]) == 0
    assert "PASS identity" in capsys.readouterr().out


def test_check_examples_returns_zero_when_example_expectations_hold(capsys):
    assert main(["check-examples"]) == 0
    out = capsys.readouterr().out
    assert "examples/well-formed" in out
    assert "examples/malformed/identity-record.missing-fields.yml" in out
    assert "examples/malformed/spec.creator-engine.missing-acceptance.yml" in out
    assert "examples/malformed/duplicate-spec-id" in out
