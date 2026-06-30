from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import fleet_manifest_guard as chk
from creator_engine_validator.fleet_manifest import iter_fleet_manifest_paths, load_fleet_manifest


def _manifest() -> dict[str, object]:
    return {
        "kind": "fleet-manifest",
        "version": "1",
        "project": {
            "name": "Example Product",
            "slug": "example-product",
            "repo": "example-org/example-product",
            "description": "Isolated per-project fleet.",
        },
        "tier": "fleet",
        "seats": [
            {
                "id": "planner-1",
                "role": "planner",
                "isolation_backend": "container",
                "model_account_ref": "modelref://example-product/planner",
            }
        ],
        "isolation": {
            "backend": "container",
            "profile_ref": "policyref://example-product/container-profile",
        },
        "secrets": {
            "github_token": "openbao://projects/example-product/github-token",
        },
        "identity": {
            "workload": "identityref://projects/example-product/workload",
        },
        "egress": {
            "policy": "default-deny",
            "allowed_refs": ["egressref://projects/example-product/default"],
        },
    }


def _write_manifest(root: Path, doc: dict[str, object], *, name: str = "fleet-manifest.yaml") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_fleet_manifest_guard_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_clean_manifest_passes_schema_and_guard(tmp_path: Path):
    _write_manifest(tmp_path, _manifest())

    result = chk.run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]
    loaded = load_fleet_manifest(tmp_path / "fleet-manifest.yaml")
    assert loaded.data["tier"] == "fleet"


def test_fleet_manifest_schema_file_is_not_treated_as_manifest(tmp_path: Path):
    schema_path = tmp_path / "validators" / "creator_engine_validator" / "schemas" / "fleet-manifest.schema.yaml"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text("title: Fleet manifest\n", encoding="utf-8")

    assert iter_fleet_manifest_paths([tmp_path]) == ()
    assert chk.run([tmp_path]).ok


def test_surfaces_manifest_under_fleet_named_parent_is_not_treated_as_fleet_manifest(tmp_path: Path):
    surfaces = tmp_path / "wt-fleet-p0" / "surfaces" / "manifest.yaml"
    surfaces.parent.mkdir(parents=True)
    surfaces.write_text(
        yaml.safe_dump({"surfaces": [{"name": "codex", "source": "test"}]}, sort_keys=False),
        encoding="utf-8",
    )

    assert iter_fleet_manifest_paths([tmp_path]) == ()
    assert chk.run([tmp_path]).ok


@pytest.mark.parametrize(
    ("category", "path", "value"),
    [
        ("internal repo", ("project", "repo"), "creator-engine/creator-engine"),
        ("internal issue repo", ("project", "description"), "tracked in creator-engine/ce-ops"),
        ("internal issue key", ("project", "description"), "see ce-ops#123"),
        ("internal seat", ("seats", 0, "id"), "dev-4"),
        ("internal host", ("project", "description"), "runs on ce-dgx-codex"),
        ("DGX marker", ("project", "description"), "DGX lab host"),
        ("spark host", ("project", "description"), "spark-b824"),
        ("dgx spark host", ("project", "description"), "dgx-spark"),
        ("provider host", ("project", "description"), "Hetzner control plane"),
        ("tailnet range", ("project", "description"), "100.99.88.77"),
        ("contained seat", ("project", "description"), "cedev4"),
        ("internal OpenBao mount", ("secrets", "api"), "openbao://ce-kv/prod/api"),
        ("internal forge path", ("identity", "app"), "identityref://forge/shared-app"),
        ("overwatch app", ("identity", "app"), "identityref://ce-overwatch/app"),
        ("internal shared app", ("project", "description"), "uses the internal shared App"),
        ("herdr socket path", ("project", "description"), "/run/creator-engine/herdr.sock"),
        ("brain endpoint", ("project", "description"), "http://ce-brain.internal:8080"),
        ("vllm endpoint", ("project", "description"), "http://vllm.internal:8000"),
    ],
)
def test_internal_identifier_categories_fail(tmp_path: Path, category: str, path: tuple[object, ...], value: str):
    doc = deepcopy(_manifest())
    target = doc
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    _write_manifest(tmp_path / category.replace(" ", "-"), doc)

    result = chk.run([tmp_path])

    assert chk.CODE_INTERNAL_IDENTIFIER in _codes(result), [error.format() for error in result.errors]


def test_inline_secret_in_secrets_field_fails_schema(tmp_path: Path):
    doc = _manifest()
    doc["secrets"]["github_token"] = "ghp_inlineSecretMaterial1234567890"  # type: ignore[index]
    _write_manifest(tmp_path, doc)

    result = chk.run([tmp_path])

    assert "fleet_manifest_schema" in _codes(result)
    assert any("/secrets/github_token" in error.path for error in result.errors)


def test_inline_secret_in_identity_field_fails_schema(tmp_path: Path):
    doc = _manifest()
    doc["identity"]["workload"] = {"ref": "-----BEGIN PRIVATE KEY-----"}  # type: ignore[index]
    _write_manifest(tmp_path, doc)

    result = chk.run([tmp_path])

    assert "fleet_manifest_schema" in _codes(result)
    assert any("/identity/workload" in error.path for error in result.errors)


def test_tier_enum_validation_rejects_unknown_tier(tmp_path: Path):
    doc = _manifest()
    doc["tier"] = "enterprise"
    _write_manifest(tmp_path, doc)

    result = chk.run([tmp_path])

    assert "fleet_manifest_schema" in _codes(result)
    assert any("/tier" in error.path for error in result.errors)
