from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import identity_denylist_autogen_sync as chk
from creator_engine_validator.identity_denylist import IdentityDenylistError, load_identity_denylist

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATOR = REPO_ROOT / "scripts" / "gen_identity_denylist.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_identity_denylist", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _registry_fixture() -> dict[str, object]:
    return {
        "repos": [
            {
                "name": "private-registry",
                "visibility": "private",
                "owner": "fixture-owner",
                "purpose": "fixture",
                "access": ["fixture"],
            }
        ],
        "accounts": [
            {
                "login": "fixture-login",
                "github_id": "TODO_VERIFY",
                "role": "worker",
                "owning_seat": "fixture-seat",
                "host": "fixture-host",
                "noreply_commit_email": "TODO_VERIFY",
            }
        ],
        "apps": [
            {
                "app_id": "TODO_VERIFY",
                "install_id": "TODO_VERIFY",
                "repo_scope": "creator-engine/*",
                "pem_custody": "TODO_VERIFY",
            }
        ],
        "tokens": [
            {
                "type": "PAT",
                "host_binding": "TODO_VERIFY",
                "storage_pointer": {"host": "TODO_VERIFY", "path": "TODO_VERIFY"},
                "rotation_owner": "TODO_VERIFY",
                "permission_scopes": ["contents:read"],
                "resource_owner": "TODO_VERIFY",
                "expiry": "TODO_VERIFY",
            }
        ],
        "signing_keys": [
            {
                "key_name": "not-derived-key-name",
                "custody_seat": "signing-seat",
                "custody_host": "signing-host",
                "key_path_pointer": "TODO_VERIFY",
            }
        ],
        "host_topology": [
            {
                "name": "topology-name",
                "host": "topology-host",
                "tailnet_ip": "TODO_VERIFY",
                "users": ["topology-user"],
                "role": "fixture",
                "reach_method": "TODO_VERIFY",
            }
        ],
        "authoring_review_matrix": [
            {
                "seat": "matrix-seat",
                "authors_as": ["matrix-author"],
                "may_review": ["matrix-reviewer"],
                "status": "TODO_VERIFY",
            }
        ],
    }


def test_identity_denylist_autogen_sync_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_identity_denylist_runtime_artifact_is_not_committed():
    artifact = REPO_ROOT / chk.ARTIFACT_REPO_RELATIVE

    assert not artifact.exists()
    status = subprocess.run(
        ["git", "status", "--short", "--", str(chk.ARTIFACT_REPO_RELATIVE)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    assert status.stdout in {"", f" D {chk.ARTIFACT_REPO_RELATIVE}\n"}


def test_sync_check_accepts_current_repo_with_absence_advisory():
    errors = chk.validate_repo(REPO_ROOT)
    root_errors, root_warnings = chk.validate_repo_with_warnings(REPO_ROOT)

    assert errors == []
    assert root_errors == []
    assert {warning.code for warning in root_warnings} == {chk.CODE_RUNTIME_ABSENT}


def test_generator_derives_only_identifier_allowlist_fields(tmp_path: Path):
    module = _load_generator()
    registry_path = tmp_path / "identity-registry.yaml"
    artifact_path = tmp_path / "identity_denylist.generated.yaml"
    registry_path.write_text(yaml.safe_dump(_registry_fixture(), sort_keys=False), encoding="utf-8")

    module.write(registry_path, artifact_path)
    assert module.check(registry_path, artifact_path)

    rendered = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    tokens = {entry["token"] for entry in rendered["entries"]}
    legacy_lengths_key = "token" + "_lengths"
    legacy_digest_key = "sha" + "256"
    assert legacy_lengths_key not in rendered
    assert all(legacy_digest_key not in entry and "length" not in entry for entry in rendered["entries"])
    assert "fixture-login" in tokens
    assert "fixture-seat" in tokens
    assert "topology-user" in tokens
    assert "matrix-reviewer" in tokens
    assert "TODO_VERIFY" not in tokens
    assert "creator-engine/*" not in tokens
    assert "not-derived-key-name" not in tokens


def test_generated_runtime_artifact_loads_plaintext_tokens(tmp_path: Path):
    module = _load_generator()
    registry_path = tmp_path / "identity-registry.yaml"
    artifact_path = tmp_path / "identity_denylist.generated.yaml"
    registry_path.write_text(yaml.safe_dump(_registry_fixture(), sort_keys=False), encoding="utf-8")

    module.write(registry_path, artifact_path)
    denylist = load_identity_denylist(artifact_path)

    assert denylist is not None
    assert {entry.token for entry in denylist.entries} >= {"fixture-login", "fixture-seat"}


def test_hash_or_length_metadata_is_rejected(tmp_path: Path):
    artifact_path = tmp_path / "identity_denylist.generated.yaml"
    legacy_lengths_key = "token" + "_lengths"
    legacy_digest_key = "sha" + "256"
    artifact_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "generated_by": "scripts/gen_identity_denylist.py",
                "source": "identity-registry",
                "normalization": "casefold",
                legacy_lengths_key: [12],
                "entries": [
                    {
                        legacy_digest_key: "0" * 64,
                        "length": 12,
                        "categories": ["account-login"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(IdentityDenylistError):
        load_identity_denylist(artifact_path)


def test_digest_shaped_token_is_rejected(tmp_path: Path):
    artifact_path = tmp_path / "identity_denylist.generated.yaml"
    digest_token = "a" * 64
    artifact_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "generated_by": "scripts/gen_identity_denylist.py",
                "source": "identity-registry",
                "normalization": "casefold",
                "entries": [
                    {
                        "token": digest_token,
                        "categories": ["account-login"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(IdentityDenylistError, match="must not be a digest"):
        load_identity_denylist(artifact_path)
