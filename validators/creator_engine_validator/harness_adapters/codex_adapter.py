"""Codex Ring-1 adapter declaration."""

from __future__ import annotations

from typing import Any, Mapping

from ..harness_adapter import CapabilityDeclaration, HarnessAdapter


class CodexAdapter(HarnessAdapter):
    """Codex has no native Ring-1 hook; enforcement is external_gate only."""

    def get_capability_declaration(self) -> CapabilityDeclaration:
        return CapabilityDeclaration(
            harness="codex",
            enforcement_levels=["external_gate"],
            observability_levels=["observe_only"],
            known_gaps=["no_native_blocking_hook", "no_sandbox_posture_pinned"],
            evidence_refs=[],
        )

    def prepare_launch(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return dict(context or {})

    def install_enforcement(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return dict(context or {})

    def spawn(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return dict(context or {})

    def seed(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return dict(context or {})

    def collect(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return dict(context or {})

    def retire(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return dict(context or {})

    def cleanup_on_failure(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return dict(context or {})
