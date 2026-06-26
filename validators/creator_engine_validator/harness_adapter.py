"""Harness-neutral Ring-1 adapter contract.

The shared policy core remains ``hook_check``: it classifies a harness event
into an allow/deny decision. Binding that decision to a live harness is adapter
specific, so adapters declare their actual capabilities and implement the run
lifecycle separately from the classifier.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Mapping

CAPABILITY_VOCAB = frozenset(
    {
        "observe_only",
        "external_gate",
        "native_blocking_hook",
        "sandbox_shim_shell_binary",
        "sandbox_posture_pinned",
        "sandbox_mount_over_binary",
        "sandbox_egress_enforced",
        "sandbox_fs_enforced",
        "forge_op_guarded",
    }
)


@dataclass(frozen=True)
class CapabilityDeclaration:
    harness: str
    enforcement_levels: list[str] = field(default_factory=list)
    observability_levels: list[str] = field(default_factory=list)
    known_gaps: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)


def validate_capability_declaration(decl: CapabilityDeclaration) -> CapabilityDeclaration:
    """Validate declared capability tokens and return ``decl`` unchanged."""
    unknown = sorted(
        {
            token
            for token in [*decl.enforcement_levels, *decl.observability_levels]
            if token not in CAPABILITY_VOCAB
        }
    )
    if unknown:
        raise ValueError(f"unknown harness capability token(s): {', '.join(unknown)}")
    return decl


class HarnessAdapter(ABC):
    """Base contract for binding the neutral policy core to a harness run."""

    @staticmethod
    def policy_core() -> Any:
        """Load the neutral classifier only when an adapter needs to classify."""
        return import_module("creator_engine_validator.hook_check")

    @abstractmethod
    def get_capability_declaration(self) -> CapabilityDeclaration:
        """Return this adapter's per-run enforcement and observability posture."""

    @abstractmethod
    def prepare_launch(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Prepare launch metadata without installing enforcement."""

    @abstractmethod
    def install_enforcement(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Install this harness's binding enforcement layer."""

    @abstractmethod
    def spawn(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Start the harness under the prepared posture."""

    @abstractmethod
    def seed(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Seed the run with initial instructions or state."""

    @abstractmethod
    def collect(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Collect evidence needed to reconstruct posture and decisions."""

    @abstractmethod
    def retire(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Retire a successful run and finalize evidence."""

    @abstractmethod
    def cleanup_on_failure(self, context: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Clean up after a failed run without weakening enforcement evidence."""
