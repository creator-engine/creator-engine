from creator_engine_validator.cli import main


def test_identity_well_formed_example_passes(capsys):
    assert main(["check", "examples/well-formed/identity-record.yml"]) == 0
    out = capsys.readouterr().out
    assert "PASS identity" in out


def test_identity_malformed_example_fails_with_fr001(capsys):
    assert main(["check", "examples/malformed/identity-record.missing-fields.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL identity" in out
    assert "FR-001" in out
    assert "docs/contracts/identity-record.md" in out
