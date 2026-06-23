"""CC-G-D Ring 0 — committed Claude hook-pack confirmation predicate.

``confirm_hook_pack`` is the pure-ish precondition the Ring 0 kernel checks
*before* permitting ``--dangerously-skip-permissions`` (clause ``CC-D-6`` in
:mod:`claude_launch_spec`). It confirms the committed hook-pack is present,
its ``.claude/settings.json`` parses, the expected PreToolUse/Stop hooks are
registered, the hook scripts carry the executable bit, and the validator is
reachable.

It reads only ``.claude/**`` under ``repo_root`` and the validator probe is
**injectable** so callers/tests never shell out, never launch Claude, and never
make a network call. Confirming the pack does **not** strengthen Ring 1 from
RUNTIME/DEFEASIBLE to HARD — it only supplies the Ring 0 fact that the pack is
active (seat contract §8.2).
"""
from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# The PreToolUse matcher must cover at least these tools (seat contract §5 / CC-G-C).
EXPECTED_PRETOOLUSE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "Read", "Bash"})

# The committed hook scripts that must exist and be executable.
EXPECTED_HOOK_SCRIPTS = ("ce-hook-common.sh", "ce-pretooluse.sh", "ce-stop.sh")

CODEX_REQUIREMENTS_PATH = Path(".codex/requirements.toml")
CODEX_HOOK_SCRIPT = Path(".codex/hooks/ce-pretooluse-codex.py")
CODEX_EXPECTED_PRETOOLUSE_TOOLS = (
    "Bash",
    "apply_patch",
    "Edit",
    "Write",
    "MultiEdit",
    "mcp__filesystem__read_file",
)
CODEX_HOOK_COMMAND_NEEDLE = ".codex/hooks/ce-pretooluse-codex.py"

ValidatorProbe = Callable[[], bool]


@dataclass(frozen=True)
class HookPackConfirmation:
    present: bool
    settings_parsed: bool
    pretooluse_registered: bool
    stop_registered: bool
    hooks_executable: bool
    validator_reachable: bool
    detail: tuple[str, ...] = ()

    @property
    def confirmed(self) -> bool:
        return all(
            (
                self.present,
                self.settings_parsed,
                self.pretooluse_registered,
                self.stop_registered,
                self.hooks_executable,
                self.validator_reachable,
            )
        )

    def to_dict(self) -> dict:
        return {
            "confirmed": self.confirmed,
            "present": self.present,
            "settings_parsed": self.settings_parsed,
            "pretooluse_registered": self.pretooluse_registered,
            "stop_registered": self.stop_registered,
            "hooks_executable": self.hooks_executable,
            "validator_reachable": self.validator_reachable,
            "detail": list(self.detail),
        }


@dataclass(frozen=True)
class CodexManagedHookPackConfirmation:
    present: bool
    requirements_parsed: bool
    managed_requirements_source: bool
    hooks_feature_pinned: bool
    pretooluse_registered: bool
    hook_command_bound: bool
    hook_script_present: bool
    hook_script_executable: bool
    validator_reachable: bool
    user_disable_blocked: bool
    detail: tuple[str, ...] = ()

    @property
    def confirmed(self) -> bool:
        return all(
            (
                self.present,
                self.requirements_parsed,
                self.managed_requirements_source,
                self.hooks_feature_pinned,
                self.pretooluse_registered,
                self.hook_command_bound,
                self.hook_script_present,
                self.hook_script_executable,
                self.validator_reachable,
                self.user_disable_blocked,
            )
        )

    def to_dict(self) -> dict:
        return {
            "confirmed": self.confirmed,
            "present": self.present,
            "requirements_parsed": self.requirements_parsed,
            "managed_requirements_source": self.managed_requirements_source,
            "hooks_feature_pinned": self.hooks_feature_pinned,
            "pretooluse_registered": self.pretooluse_registered,
            "hook_command_bound": self.hook_command_bound,
            "hook_script_present": self.hook_script_present,
            "hook_script_executable": self.hook_script_executable,
            "validator_reachable": self.validator_reachable,
            "user_disable_blocked": self.user_disable_blocked,
            "detail": list(self.detail),
        }


def _default_validator_probe() -> bool:
    """Reachability probe that never launches Claude or touches the network.

    It only confirms the validator bridge is importable in-process (a
    ``hook-check``-class dry probe).
    """
    try:
        from . import hook_check  # noqa: F401

        return True
    except Exception:  # pragma: no cover - import failure is the only false path
        return False


def _pretooluse_registered(hooks_cfg: dict) -> bool:
    for entry in hooks_cfg.get("PreToolUse", []) or []:
        matcher = entry.get("matcher", "") if isinstance(entry, dict) else ""
        tools = {part for part in str(matcher).split("|") if part}
        if EXPECTED_PRETOOLUSE_TOOLS <= tools:
            return True
    return False


def _stop_registered(hooks_cfg: dict) -> bool:
    for entry in hooks_cfg.get("Stop", []) or []:
        if isinstance(entry, dict) and entry.get("hooks"):
            return True
    return False


def _codex_pretooluse_registered(hooks_cfg: dict) -> bool:
    for entry in hooks_cfg.get("PreToolUse", []) or []:
        if not isinstance(entry, dict):
            continue
        matcher = entry.get("matcher", "")
        if not isinstance(matcher, str) or not matcher:
            continue
        try:
            pattern = re.compile(matcher)
        except re.error:
            continue
        if all(pattern.fullmatch(tool) for tool in CODEX_EXPECTED_PRETOOLUSE_TOOLS):
            return True
    return False


def _codex_hook_command_bound(hooks_cfg: dict) -> bool:
    for entry in hooks_cfg.get("PreToolUse", []) or []:
        if not isinstance(entry, dict):
            continue
        handlers = entry.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            if not isinstance(handler, dict):
                continue
            if handler.get("type") != "command":
                continue
            command = handler.get("command")
            if isinstance(command, str) and CODEX_HOOK_COMMAND_NEEDLE in command:
                return True
    return False


def _codex_user_disable_blocked(requirements_doc: dict, user_config_doc: dict | None) -> bool:
    """Model Codex requirements precedence for the hooks feature."""
    features = requirements_doc.get("features")
    if not isinstance(features, dict) or features.get("hooks") is not True:
        return False
    if user_config_doc is None:
        return True
    user_features = user_config_doc.get("features")
    if not isinstance(user_features, dict):
        return True
    # A user-local ``hooks = false`` conflicts with managed requirements; the
    # managed value wins, so the pack remains enabled and non-disableable.
    return user_features.get("hooks") in (None, False, True)


def confirm_hook_pack(
    repo_root: Path | str, *, validator_probe: ValidatorProbe | None = None
) -> HookPackConfirmation:
    """Confirm the committed Claude hook-pack under ``repo_root``.

    Pure I/O: reads ``.claude/settings.json`` and stats ``.claude/hooks/*.sh``
    only. The ``validator_probe`` defaults to an in-process import probe; pass a
    callable to inject reachability in tests.
    """
    root = Path(repo_root)
    claude_dir = root / ".claude"
    settings_path = claude_dir / "settings.json"
    hooks_dir = claude_dir / "hooks"
    detail: list[str] = []

    present = settings_path.is_file() and hooks_dir.is_dir()
    if not present:
        detail.append(f"hook-pack not present at {claude_dir}")

    settings_parsed = False
    hooks_cfg: dict = {}
    if settings_path.is_file():
        try:
            parsed = json.loads(settings_path.read_text(encoding="utf-8"))
            settings_parsed = isinstance(parsed, dict)
            hooks_cfg = parsed.get("hooks", {}) if settings_parsed else {}
        except (OSError, json.JSONDecodeError) as exc:
            detail.append(f"settings.json did not parse: {exc}")

    pretooluse_registered = settings_parsed and _pretooluse_registered(hooks_cfg)
    if settings_parsed and not pretooluse_registered:
        detail.append(
            "PreToolUse matcher does not cover " + "|".join(sorted(EXPECTED_PRETOOLUSE_TOOLS))
        )
    stop_registered = settings_parsed and _stop_registered(hooks_cfg)
    if settings_parsed and not stop_registered:
        detail.append("no Stop hook registered")

    hooks_executable = True
    for name in EXPECTED_HOOK_SCRIPTS:
        script = hooks_dir / name
        if not script.is_file():
            hooks_executable = False
            detail.append(f"missing hook script {name}")
            continue
        if not os.access(script, os.X_OK):
            hooks_executable = False
            detail.append(f"hook script {name} is not executable")

    probe = validator_probe or _default_validator_probe
    try:
        validator_reachable = bool(probe())
    except Exception as exc:  # a misbehaving probe is a reachability failure
        validator_reachable = False
        detail.append(f"validator probe raised: {exc}")
    if not validator_reachable:
        detail.append("validator not reachable")

    return HookPackConfirmation(
        present=present,
        settings_parsed=settings_parsed,
        pretooluse_registered=pretooluse_registered,
        stop_registered=stop_registered,
        hooks_executable=hooks_executable,
        validator_reachable=validator_reachable,
        detail=tuple(detail),
    )


def confirm_codex_managed_hook_pack(
    repo_root: Path | str,
    *,
    validator_probe: ValidatorProbe | None = None,
    user_config_text: str | None = None,
) -> CodexManagedHookPackConfirmation:
    """Confirm CE's repo-shipped Codex managed hook-pack representation.

    The representation is a ``requirements.toml`` hook source. Per the Codex
    managed-configuration contract, hooks sourced from requirements are managed,
    trusted by policy, and cannot be disabled from the user hook browser. This
    predicate validates that the repo carries that managed source, that it pins
    hooks on, that its PreToolUse matcher covers CE's required Codex surfaces,
    and that a local ``[features].hooks = false`` config would not disable the
    managed pack under the requirements precedence model.
    """
    root = Path(repo_root)
    requirements_path = root / CODEX_REQUIREMENTS_PATH
    hook_script = root / CODEX_HOOK_SCRIPT
    detail: list[str] = []

    present = requirements_path.is_file()
    if not present:
        detail.append(f"Codex managed requirements not present at {CODEX_REQUIREMENTS_PATH}")

    requirements_parsed = False
    requirements_doc: dict = {}
    if requirements_path.is_file():
        try:
            parsed = tomllib.loads(requirements_path.read_text(encoding="utf-8"))
            requirements_parsed = isinstance(parsed, dict)
            requirements_doc = parsed if requirements_parsed else {}
        except (OSError, tomllib.TOMLDecodeError) as exc:
            detail.append(f"requirements.toml did not parse: {exc}")

    managed_requirements_source = present and requirements_path.name == "requirements.toml"
    if present and not managed_requirements_source:
        detail.append("Codex hook source is not a requirements.toml managed source")

    features = requirements_doc.get("features") if requirements_parsed else {}
    hooks_feature_pinned = isinstance(features, dict) and features.get("hooks") is True
    if requirements_parsed and not hooks_feature_pinned:
        detail.append("[features].hooks must be pinned true in requirements.toml")

    hooks_cfg = requirements_doc.get("hooks", {}) if requirements_parsed else {}
    if not isinstance(hooks_cfg, dict):
        hooks_cfg = {}
    pretooluse_registered = requirements_parsed and _codex_pretooluse_registered(hooks_cfg)
    if requirements_parsed and not pretooluse_registered:
        detail.append("Codex PreToolUse matcher does not cover Bash/apply_patch/Edit/Write/MCP")
    hook_command_bound = requirements_parsed and _codex_hook_command_bound(hooks_cfg)
    if requirements_parsed and not hook_command_bound:
        detail.append("Codex PreToolUse command does not bind ce-pretooluse-codex.py")

    hook_script_present = hook_script.is_file()
    if not hook_script_present:
        detail.append(f"missing Codex hook script {CODEX_HOOK_SCRIPT}")
    hook_script_executable = hook_script_present and os.access(hook_script, os.X_OK)
    if hook_script_present and not hook_script_executable:
        detail.append(f"Codex hook script {CODEX_HOOK_SCRIPT} is not executable")

    user_config_doc = None
    if user_config_text is not None:
        try:
            parsed_user = tomllib.loads(user_config_text)
            user_config_doc = parsed_user if isinstance(parsed_user, dict) else {}
        except tomllib.TOMLDecodeError as exc:
            detail.append(f"user config TOML did not parse: {exc}")
            user_config_doc = {}
    user_disable_blocked = (
        requirements_parsed
        and _codex_user_disable_blocked(requirements_doc, user_config_doc)
    )
    if requirements_parsed and not user_disable_blocked:
        detail.append("managed hooks could be disabled by user config in the requirements model")

    probe = validator_probe or _default_validator_probe
    try:
        validator_reachable = bool(probe())
    except Exception as exc:
        validator_reachable = False
        detail.append(f"validator probe raised: {exc}")
    if not validator_reachable:
        detail.append("validator not reachable")

    return CodexManagedHookPackConfirmation(
        present=present,
        requirements_parsed=requirements_parsed,
        managed_requirements_source=managed_requirements_source,
        hooks_feature_pinned=hooks_feature_pinned,
        pretooluse_registered=pretooluse_registered,
        hook_command_bound=hook_command_bound,
        hook_script_present=hook_script_present,
        hook_script_executable=hook_script_executable,
        validator_reachable=validator_reachable,
        user_disable_blocked=user_disable_blocked,
        detail=tuple(detail),
    )
