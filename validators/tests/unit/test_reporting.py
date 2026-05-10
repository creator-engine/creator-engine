from creator_engine_validator.reporting import make_error


def test_error_format_includes_fr_path_message_and_contract():
    error = make_error("FR-027", "examples/bad.yml", "field", "bad value", "docs/contracts/example.md")
    rendered = error.format()
    assert "FR-027" in rendered
    assert "examples/bad.yml:field" in rendered
    assert "bad value" in rendered
    assert "docs/contracts/example.md" in rendered
