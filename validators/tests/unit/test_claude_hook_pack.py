"""Package-data and tenant materialization coverage for the Claude hook-pack."""
from __future__ import annotations

import json
import os
import tomllib
from importlib import resources

import pytest

from creator_engine_validator import claude_hook_pack, hook_pack_confirm


def test_hook_pack_assets_are_packaged_and_include_every_required_file():
    assets = resources.files("creator_engine_validator").joinpath(claude_hook_pack.ASSET_DIR)
    names = {child.name for child in assets.iterdir()}
    assert {"settings.json", *claude_hook_pack.HOOK_SCRIPT_NAMES} <= names
    assert json.loads(assets.joinpath("settings.json").read_text(encoding="utf-8"))["hooks"]
    for name in claude_hook_pack.HOOK_SCRIPT_NAMES:
        assert assets.joinpath(name).read_text(encoding="utf-8").startswith("#!/usr/bin/env sh\n")


def test_pyproject_declares_hook_pack_package_data(repo_root):
    pyproject = repo_root / "validators" / "pyproject.toml"
    package_data = (
        tomllib.loads(pyproject.read_text(encoding="utf-8"))
        .get("tool", {})
        .get("setuptools", {})
        .get("package-data", {})
        .get("creator_engine_validator", [])
    )
    assert "hook_pack_assets/*.json" in package_data
    assert "hook_pack_assets/*.sh" in package_data


def test_packaged_hook_assets_match_the_committed_hook_pack(repo_root):
    assets = resources.files("creator_engine_validator").joinpath(claude_hook_pack.ASSET_DIR)
    assert assets.joinpath("settings.json").read_bytes() == (repo_root / ".claude" / "settings.json").read_bytes()
    for name in claude_hook_pack.HOOK_SCRIPT_NAMES:
        assert assets.joinpath(name).read_bytes() == (repo_root / ".claude" / "hooks" / name).read_bytes()


def test_materialize_fresh_tenant_hook_pack_confirms(tmp_path):
    result = claude_hook_pack.materialize_claude_hook_pack(tmp_path)
    confirmation = hook_pack_confirm.confirm_hook_pack(tmp_path)

    assert confirmation.confirmed, confirmation.detail
    assert set(result.created) == {
        ".claude/settings.json",
        *(f".claude/hooks/{name}" for name in claude_hook_pack.HOOK_SCRIPT_NAMES),
    }
    for name in claude_hook_pack.HOOK_SCRIPT_NAMES:
        assert os.access(tmp_path / ".claude" / "hooks" / name, os.X_OK)

    repeated = claude_hook_pack.materialize_claude_hook_pack(tmp_path)
    assert not repeated.created and not repeated.updated
    assert set(repeated.unchanged) == set(result.created)


def test_materialize_merges_existing_tenant_settings_without_dropping_fields(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(
        json.dumps({"permissions": {"allow": ["Bash(git status)"]}, "hooks": {}}),
        encoding="utf-8",
    )

    result = claude_hook_pack.materialize_claude_hook_pack(tmp_path)
    merged = json.loads(settings.read_text(encoding="utf-8"))

    assert merged["permissions"] == {"allow": ["Bash(git status)"]}
    assert "PreToolUse" in merged["hooks"] and "Stop" in merged["hooks"]
    assert ".claude/settings.json" in result.updated


def test_materialize_refuses_invalid_tenant_settings_without_overwrite(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{not json", encoding="utf-8")

    with pytest.raises(claude_hook_pack.HookPackMaterializationError, match="valid JSON"):
        claude_hook_pack.materialize_claude_hook_pack(tmp_path)

    assert settings.read_text(encoding="utf-8") == "{not json"


def test_materialize_refuses_to_replace_tenant_owned_hook_script(tmp_path):
    script = tmp_path / ".claude" / "hooks" / "ce-stop.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env sh\necho tenant\n", encoding="utf-8")

    with pytest.raises(claude_hook_pack.HookPackMaterializationError, match="tenant-owned hook asset"):
        claude_hook_pack.materialize_claude_hook_pack(tmp_path)

    assert script.read_text(encoding="utf-8") == "#!/usr/bin/env sh\necho tenant\n"
