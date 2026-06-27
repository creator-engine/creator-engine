"""Claude Code Ring-1 adapter declaration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..harness_adapter import CapabilityDeclaration, HarnessAdapter
from ..hook_pack_confirm import HookPackConfirmation, confirm_hook_pack


_PRETOOLUSE_ENTRY = {
    "matcher": "Edit|Write|MultiEdit|Read|Bash",
    "hooks": [
        {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/ce-pretooluse.sh",
        }
    ],
}


def _has_equivalent_pretooluse_entry(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("matcher") != _PRETOOLUSE_ENTRY["matcher"]:
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(hook, dict)
        and hook.get("type") == "command"
        and hook.get("command") == "$CLAUDE_PROJECT_DIR/.claude/hooks/ce-pretooluse.sh"
        for hook in hooks
    )


def _hook_failure_detail(confirmation: HookPackConfirmation) -> str:
    detail = "; ".join(confirmation.detail) if confirmation.detail else "no detail reported"
    return (
        "Claude Code hook pack confirmation failed: "
        f"confirmed={confirmation.confirmed}, "
        f"pretooluse_registered={confirmation.pretooluse_registered}; {detail}"
    )


class ClaudeCodeAdapter(HarnessAdapter):
    """Claude Code can bind Ring-1 decisions through native PreToolUse hooks."""

    def get_capability_declaration(self) -> CapabilityDeclaration:
        return CapabilityDeclaration(
            harness="claude_code",
            enforcement_levels=["native_blocking_hook"],
            observability_levels=["observe_only"],
            known_gaps=[],
            evidence_refs=[],
        )

    def prepare_launch(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return {
            **(context or {}),
            "harness": "claude_code",
            "status": "prepared",
            "enforcement": "native_blocking_hook",
        }

    def install_enforcement(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        if context is None or "project_dir" not in context:
            raise ValueError("project_dir required for install_enforcement")

        project_dir = Path(context["project_dir"])
        settings_path = project_dir / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                raise ValueError("settings.json must contain a JSON object")
        else:
            settings = {}

        hooks_cfg = settings.setdefault("hooks", {})
        if not isinstance(hooks_cfg, dict):
            hooks_cfg = {}
            settings["hooks"] = hooks_cfg
        pretooluse_entries = hooks_cfg.setdefault("PreToolUse", [])
        if not isinstance(pretooluse_entries, list):
            pretooluse_entries = []
            hooks_cfg["PreToolUse"] = pretooluse_entries
        if not any(_has_equivalent_pretooluse_entry(entry) for entry in pretooluse_entries):
            pretooluse_entries.append(_PRETOOLUSE_ENTRY)

        tmp_path = settings_path.with_name(f"{settings_path.name}.tmp")
        tmp_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(settings_path)

        confirmation = confirm_hook_pack(project_dir)
        if not confirmation.pretooluse_registered or not confirmation.confirmed:
            raise RuntimeError(_hook_failure_detail(confirmation))

        return {
            **context,
            "harness": "claude_code",
            "status": "enforcement_installed",
            "mechanism": "pre_tool_use_hook",
            "hook_confirmed": True,
            "settings_path": str(settings_path),
        }

    def spawn(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return {
            **(context or {}),
            "harness": "claude_code",
            "status": "not_implemented",
            "reason": "gvisor_spawn_pending",
        }

    def seed(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return {**(context or {}), "harness": "claude_code", "status": "seeded"}

    def collect(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return {**(context or {}), "harness": "claude_code", "status": "evidence_collected"}

    def retire(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return {**(context or {}), "harness": "claude_code", "status": "retired"}

    def cleanup_on_failure(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return {
            **(context or {}),
            "harness": "claude_code",
            "status": "cleaned_up",
            "failure": True,
        }
