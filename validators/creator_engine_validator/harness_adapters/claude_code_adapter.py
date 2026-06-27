"""Claude Code Ring-1 adapter declaration."""

from __future__ import annotations

from typing import Any, Mapping

from ..harness_adapter import CapabilityDeclaration, HarnessAdapter


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
        return {
            **(context or {}),
            "harness": "claude_code",
            "status": "enforcement_installed",
            "mechanism": "pre_tool_use_hook",
        }

    def spawn(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return {
            **(context or {}),
            "harness": "claude_code",
            "status": "spawned",
            "sandbox": "gvisor",
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
