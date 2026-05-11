from pathlib import Path

from creator_engine_validator.checks.identity import validate_identity_record


def valid_identity(tmp_path: Path) -> dict:
    paths = {}
    for name in ("attestations", "ratifications", "redactions"):
        path = tmp_path / name
        path.mkdir()
        paths[name] = str(path)
    return {
        "tenant_id": "example-tenant",
        "source_host": "github",
        "source_host_installation_id": "123456",
        "agent_app_slug": "example-agent[bot]",
        "agent_actor_id": "987654321",
        "runtime_tool": "Codex CLI",
        "role_category": "implementer",
        "authority_context": {
            "description": "Example authority context.",
            "governing_spec_refs": ["specs/example/spec.md"],
            "ratifier_authority_refs": ["docs/contracts/identity-record.md"],
        },
        "human_ratifier_roles": ["source"],
        "mutation_classes": ["docs", "code"],
        "allowed_repositories": ["github.com/example-org/example-repo"],
        "signing_policy": {
            "commit_signing_required": False,
            "commit_signing_method": "none",
            "attestation_signing_required": False,
        },
        "attestation_storage_path": paths["attestations"],
        "ratification_storage_path": paths["ratifications"],
        "redaction_storage_path": paths["redactions"],
    }


def test_identity_accepts_well_formed_dict(tmp_path):
    record = valid_identity(tmp_path)
    assert validate_identity_record(record, tmp_path / "identity-record.yml") == []


def test_identity_missing_required_fields_cites_fr001_and_contract(tmp_path):
    record = valid_identity(tmp_path)
    del record["tenant_id"]
    errors = validate_identity_record(record, tmp_path / "identity-record.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)
    assert all(error.contract == "docs/contracts/identity-record.md" for error in errors)


def test_identity_empty_human_ratifier_roles_cites_fr001_and_contract(tmp_path):
    record = valid_identity(tmp_path)
    record["human_ratifier_roles"] = []
    errors = validate_identity_record(record, tmp_path / "identity-record.yml")
    assert any(error.code == "FR-001" and "human_ratifier_roles" in error.path for error in errors)
    assert any(error.contract == "docs/contracts/identity-record.md" for error in errors)


def test_identity_missing_storage_directory_cites_fr004(tmp_path):
    record = valid_identity(tmp_path)
    record["attestation_storage_path"] = str(tmp_path / "missing-attestations")
    errors = validate_identity_record(record, tmp_path / "identity-record.yml")
    assert any(error.code == "FR-004" and "attestation_storage_path" in error.path for error in errors)
