"""Materialize CE's packaged Claude hook-pack into a tenant workspace.

The hook assets are package data so an installed wheel, rather than a source
checkout, can prepare a fresh tenant repository. Existing tenant settings are
merged structurally; malformed or incompatible settings are refused instead of
being overwritten.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

ASSET_DIR = "hook_pack_assets"
SETTINGS_NAME = "settings.json"
HOOK_SCRIPT_NAMES = ("ce-hook-common.sh", "ce-pretooluse.sh", "ce-stop.sh")


class HookPackMaterializationError(RuntimeError):
    """The tenant hook-pack cannot be merged without clobbering user content."""


@dataclass(frozen=True)
class HookPackMaterializationResult:
    created: tuple[str, ...]
    updated: tuple[str, ...]
    unchanged: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": list(self.created),
            "updated": list(self.updated),
            "unchanged": list(self.unchanged),
        }


def _asset_bytes(name: str) -> bytes:
    return resources.files("creator_engine_validator").joinpath(ASSET_DIR, name).read_bytes()


def _asset_settings() -> dict[str, Any]:
    parsed = json.loads(_asset_bytes(SETTINGS_NAME).decode("utf-8"))
    if not isinstance(parsed, dict):  # pragma: no cover - package authoring invariant
        raise HookPackMaterializationError("packaged hook settings are not a JSON object")
    return parsed


def _canonical_hook_entries() -> tuple[dict[str, Any], dict[str, Any]]:
    hooks = _asset_settings().get("hooks")
    if not isinstance(hooks, dict):  # pragma: no cover - package authoring invariant
        raise HookPackMaterializationError("packaged hook settings have no hooks object")
    pretooluse = hooks.get("PreToolUse")
    stop = hooks.get("Stop")
    if not isinstance(pretooluse, list) or len(pretooluse) != 1:
        raise HookPackMaterializationError("packaged PreToolUse hook is malformed")
    if not isinstance(stop, list) or len(stop) != 1:
        raise HookPackMaterializationError("packaged Stop hook is malformed")
    return dict(pretooluse[0]), dict(stop[0])


def _read_existing_settings(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return {}, False
    if not path.is_file():
        raise HookPackMaterializationError(f"refusing to replace non-file tenant settings: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HookPackMaterializationError(
            f"refusing to overwrite tenant settings.json that is not valid JSON: {path}: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise HookPackMaterializationError(
            f"refusing to overwrite tenant settings.json that is not a JSON object: {path}"
        )
    return parsed, True


def _merge_settings(existing: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Append CE hook entries without replacing tenant-owned settings entries."""
    merged = dict(existing)
    hooks = merged.get("hooks")
    if hooks is None:
        hooks = {}
        merged["hooks"] = hooks
    if not isinstance(hooks, dict):
        raise HookPackMaterializationError(
            "refusing to overwrite tenant settings.json: top-level 'hooks' is not an object"
        )
    pretooluse, stop = _canonical_hook_entries()
    changed = False
    for event, entry in (("PreToolUse", pretooluse), ("Stop", stop)):
        entries = hooks.get(event)
        if entries is None:
            hooks[event] = [entry]
            changed = True
            continue
        if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
            raise HookPackMaterializationError(
                f"refusing to overwrite tenant settings.json: hooks.{event} is not a list of objects"
            )
        if entry not in entries:
            entries.append(entry)
            changed = True
    return merged, changed


def _write_atomic(path: Path, data: bytes, *, executable: bool = False) -> None:
    temporary = path.with_name(f".{path.name}.ce-hook-pack.tmp")
    try:
        temporary.write_bytes(data)
        temporary.chmod(0o755 if executable else 0o644)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def materialize_claude_hook_pack(repo_root: Path | str) -> HookPackMaterializationResult:
    """Install CE hook assets and merge the minimal hook registrations safely.

    Hook scripts are CE-owned names. A tenant file with one of those names and
    different bytes is left untouched and causes a clear refusal; silently
    replacing a locally modified hook would hide an operator decision.
    """
    root = Path(repo_root)
    claude_dir = root / ".claude"
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []

    for name in HOOK_SCRIPT_NAMES:
        target = hooks_dir / name
        expected = _asset_bytes(name)
        rel = str(target.relative_to(root))
        if target.exists():
            if not target.is_file():
                raise HookPackMaterializationError(
                    f"refusing to replace non-file tenant hook asset: {target}"
                )
            if target.read_bytes() != expected:
                raise HookPackMaterializationError(
                    f"refusing to replace tenant-owned hook asset with different content: {target}"
                )
            if not os.access(target, os.X_OK):
                target.chmod(target.stat().st_mode | 0o111)
                updated.append(rel)
            else:
                unchanged.append(rel)
            continue
        _write_atomic(target, expected, executable=True)
        created.append(rel)

    settings_path = claude_dir / SETTINGS_NAME
    settings, existed = _read_existing_settings(settings_path)
    merged, changed = _merge_settings(settings)
    settings_rel = str(settings_path.relative_to(root))
    if not existed:
        _write_atomic(settings_path, json.dumps(merged, indent=2, sort_keys=True).encode("utf-8") + b"\n")
        created.append(settings_rel)
    elif changed:
        _write_atomic(settings_path, json.dumps(merged, indent=2, sort_keys=True).encode("utf-8") + b"\n")
        updated.append(settings_rel)
    else:
        unchanged.append(settings_rel)

    return HookPackMaterializationResult(
        created=tuple(created), updated=tuple(updated), unchanged=tuple(unchanged)
    )
