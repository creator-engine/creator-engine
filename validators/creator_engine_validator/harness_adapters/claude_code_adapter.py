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
        raise NotImplementedError("Claude Code launch preparation is adapter-specific")

    def install_enforcement(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        raise NotImplementedError("Claude Code hook installation is adapter-specific")

    def spawn(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        raise NotImplementedError("Claude Code spawning is adapter-specific")

    def seed(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        raise NotImplementedError("Claude Code seeding is adapter-specific")

    def collect(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        raise NotImplementedError("Claude Code evidence collection is adapter-specific")

    def retire(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        raise NotImplementedError("Claude Code retirement is adapter-specific")

    def cleanup_on_failure(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        raise NotImplementedError("Claude Code failure cleanup is adapter-specific")
