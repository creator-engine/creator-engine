from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import identity_denylist_autogen_sync as chk
from creator_engine_validator.identity_denylist import digest_token, load_identity_denylist

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


def test_committed_identity_denylist_is_valid_and_hashed_only():
    denylist = load_identity_denylist()

    assert denylist.entries
    raw = (REPO_ROOT / chk.ARTIFACT_REPO_RELATIVE).read_text(encoding="utf-8")
    assert "creator-engine/ce-ops" not in raw
    assert "ubuntuaws745-cmyk" not in raw


def test_sync_check_accepts_current_repo():
    errors = chk.validate_repo(REPO_ROOT)

    assert errors == []


def test_generator_derives_only_identifier_allowlist_fields(tmp_path: Path):
    module = _load_generator()
    registry_path = tmp_path / "identity-registry.yaml"
    artifact_path = tmp_path / "identity_denylist.generated.yaml"
    registry_path.write_text(yaml.safe_dump(_registry_fixture(), sort_keys=False), encoding="utf-8")

    module.write(registry_path, artifact_path)
    assert module.check(registry_path, artifact_path)

    rendered = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    digests = {entry["sha256"] for entry in rendered["entries"]}
    assert digest_token("fixture-login") in digests
    assert digest_token("fixture-seat") in digests
    assert digest_token("topology-user") in digests
    assert digest_token("matrix-reviewer") in digests
    assert digest_token("TODO_VERIFY") not in digests
    assert digest_token("creator-engine/*") not in digests
    assert digest_token("not-derived-key-name") not in digests
