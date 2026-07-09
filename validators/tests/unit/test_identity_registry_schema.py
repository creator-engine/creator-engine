from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "schemas" / "identity-registry.schema.yaml"
EXAMPLE_PATH = REPO_ROOT / "docs" / "governance" / "identity-registry.example.yaml"


def load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_example() -> dict:
    with EXAMPLE_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema())


def assert_valid(instance: dict) -> None:
    errors = sorted(validator().iter_errors(instance), key=lambda err: list(err.path))
    assert errors == []


def assert_invalid(instance: dict, path_fragment: str) -> None:
    errors = sorted(validator().iter_errors(instance), key=lambda err: list(err.path))
    assert errors
    assert any(path_fragment in "/".join(str(part) for part in err.path) for err in errors)


def valid_registry() -> dict:
    return {
        "repos": [
            {
                "name": "EXAMPLE_REPO",
                "visibility": "private",
                "owner": "EXAMPLE_OWNER",
                "purpose": "EXAMPLE_PURPOSE",
                "access": ["EXAMPLE_ACCESS_GROUP"],
            }
        ],
        "accounts": [
            {
                "login": "EXAMPLE_LOGIN",
                "github_id": "TODO_VERIFY",
                "role": "governed-seat",
                "owning_seat": "EXAMPLE_SEAT",
                "host": "EXAMPLE_HOST",
                "noreply_commit_email": "TODO_VERIFY",
                "email_of_record": "TODO_VERIFY",
            }
        ],
        "apps": [
            {
                "app_id": "TODO_VERIFY",
                "install_id": "TODO_VERIFY",
                "repo_scope": "EXAMPLE_OWNER/EXAMPLE_REPO",
                "pem_custody": "openbao-ref:EXAMPLE_MOUNT/EXAMPLE_PATH",
            }
        ],
        "tokens": [
            {
                "type": "PAT",
                "host_binding": "EXAMPLE_HOST",
                "storage_pointer": {
                    "host": "EXAMPLE_HOST",
                    "path": "EXAMPLE_STORAGE_POINTER",
                },
                "rotation_owner": "EXAMPLE_SEAT",
                "permission_scopes": ["EXAMPLE_SCOPE_READ"],
                "resource_owner": "EXAMPLE_OWNER",
                "expiry": "TODO_VERIFY",
            }
        ],
        "signing_keys": [
            {
                "key_name": "EXAMPLE_KEY",
                "custody_seat": "EXAMPLE_SEAT",
                "custody_host": "EXAMPLE_HOST",
                "key_path_pointer": "TODO_VERIFY",
            }
        ],
        "host_topology": [
            {
                "name": "EXAMPLE_HOST",
                "host": "EXAMPLE_HOST",
                "tailnet_ip": "TODO_VERIFY",
                "users": ["EXAMPLE_SEAT"],
                "role": "worker-host",
                "reach_method": "TODO_VERIFY",
                "credential_pointers": ["openbao-ref:EXAMPLE_MOUNT/EXAMPLE_PATH"],
            }
        ],
        "authoring_review_matrix": [
            {
                "seat": "EXAMPLE_SEAT",
                "authors_as": ["EXAMPLE_LOGIN"],
                "may_review": ["EXAMPLE_REVIEWER"],
                "status": "needs-rewire",
            }
        ],
    }


def test_checked_in_identity_registry_example_validates() -> None:
    assert_valid(load_example())


def test_extended_identity_registry_shape_validates() -> None:
    assert_valid(valid_registry())


@pytest.mark.parametrize("field", ["permission_scopes", "resource_owner", "expiry"])
def test_token_requires_new_inventory_dimensions(field: str) -> None:
    registry = valid_registry()
    del registry["tokens"][0][field]

    assert_invalid(registry, "tokens/0")


def test_repos_are_required() -> None:
    registry = valid_registry()
    del registry["repos"]

    assert_invalid(registry, "")


def test_repo_visibility_is_constrained() -> None:
    registry = valid_registry()
    registry["repos"][0]["visibility"] = "EXAMPLE_VISIBILITY"

    assert_invalid(registry, "repos/0/visibility")


def test_host_credential_pointers_must_be_openbao_refs() -> None:
    registry = valid_registry()
    registry["host_topology"][0]["credential_pointers"] = ["EXAMPLE_POINTER"]

    assert_invalid(registry, "host_topology/0/credential_pointers/0")


def test_optional_account_email_of_record_is_allowed_to_be_absent() -> None:
    registry = deepcopy(valid_registry())
    del registry["accounts"][0]["email_of_record"]

    assert_valid(registry)


def test_human_contributor_account_omits_owning_seat_and_host() -> None:
    """human-contributor role does not require owning_seat or host."""
    registry = valid_registry()
    registry["accounts"].append(
        {
            "login": "EXAMPLE_LOGIN_HUMAN",
            "github_id": "TODO_VERIFY",
            "role": "human-contributor",
            "noreply_commit_email": "TODO_VERIFY",
            "email_of_record": "TODO_VERIFY",
            "trust_tier": "external",
            "onboarding_date": "TODO_VERIFY",
        }
    )

    assert_valid(registry)


def test_non_human_contributor_still_requires_owning_seat() -> None:
    """Existing bot accounts still require owning_seat."""
    registry = valid_registry()
    del registry["accounts"][0]["owning_seat"]

    assert_invalid(registry, "accounts/0")


def test_non_human_contributor_still_requires_host() -> None:
    """Existing bot accounts still require host."""
    registry = valid_registry()
    del registry["accounts"][0]["host"]

    assert_invalid(registry, "accounts/0")


def test_human_contributor_trust_tier_constrained() -> None:
    """trust_tier only accepts constrained values."""
    registry = valid_registry()
    registry["accounts"].append(
        {
            "login": "EXAMPLE_LOGIN_HUMAN",
            "github_id": "TODO_VERIFY",
            "role": "human-contributor",
            "noreply_commit_email": "TODO_VERIFY",
            "trust_tier": "INVALID_TIER",
        }
    )

    assert_invalid(registry, "accounts/1/trust_tier")


def test_human_contributor_with_optional_owning_seat_and_host_is_valid() -> None:
    """human-contributor may include owning_seat and host if desired."""
    registry = valid_registry()
    registry["accounts"].append(
        {
            "login": "EXAMPLE_LOGIN_HUMAN",
            "github_id": "TODO_VERIFY",
            "role": "human-contributor",
            "noreply_commit_email": "TODO_VERIFY",
            "owning_seat": "TODO_VERIFY",
            "host": "TODO_VERIFY",
        }
    )

    assert_valid(registry)


# --- tenant App validation (added by ce-470 schema slice) ---


def test_app_with_tenant_fields_valid() -> None:
    """An app entry with the new optional tenant fields validates successfully."""
    registry = valid_registry()
    registry["apps"].append(
        {
            "app_id": 4103119,
            "install_id": 141552951,
            "repo_scope": "chmod735-dor/* (all repos, account-wide installation)",
            "pem_custody": "file://~/.ce-keys/mythos-ce.2026-06-20.private-key.pem",
            "app_name": "mythos-ce",
            "client_id": "Iv23liuJp6OxfCWvwfSl",
            "tenant_scope": "account-wide",
        }
    )

    assert_valid(registry)


def test_app_without_tenant_fields_still_valid() -> None:
    """Existing app entries without tenant metadata remain valid."""
    registry = valid_registry()

    assert_valid(registry)


def test_app_invalid_tenant_scope_rejected() -> None:
    """tenant_scope must be one of the allowed enum values."""
    registry = valid_registry()
    registry["apps"][0]["tenant_scope"] = "all"

    assert_invalid(registry, "apps/0/tenant_scope")
