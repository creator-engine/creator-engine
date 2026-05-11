from pathlib import Path

from creator_engine_validator.schema import validate_with_schema


def test_validate_with_schema_reports_json_pointer(tmp_path: Path):
    schema = tmp_path / "schema.yaml"
    schema.write_text("""
$schema: https://json-schema.org/draft/2020-12/schema
required: [name]
properties:
  name:
    type: string
""".lstrip())

    errors = validate_with_schema({}, schema, "example.yml", code="FR-X", contract="docs/contracts/example.md")

    assert len(errors) == 1
    assert errors[0].code == "FR-X"
    assert errors[0].path == "example.yml:/"
    assert errors[0].contract == "docs/contracts/example.md"
