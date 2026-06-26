from __future__ import annotations

import pytest

from creator_engine_validator.harness_adapter import (
    CapabilityDeclaration,
    HarnessAdapter,
    validate_capability_declaration,
)
from creator_engine_validator.harness_adapters.claude_code_adapter import ClaudeCodeAdapter
from creator_engine_validator.harness_adapters.codex_adapter import CodexAdapter


def test_validate_capability_declaration_rejects_unknown_tokens() -> None:
    decl = CapabilityDeclaration(
        harness="test",
        enforcement_levels=["external_gate", "not_a_capability"],
    )

    with pytest.raises(ValueError, match="not_a_capability"):
        validate_capability_declaration(decl)


def test_codex_declares_external_gate_only_not_native_hook() -> None:
    decl = CodexAdapter().get_capability_declaration()

    validate_capability_declaration(decl)
    assert decl.harness == "codex"
    assert decl.enforcement_levels == ["external_gate"]
    assert "native_blocking_hook" not in decl.enforcement_levels
    assert decl.observability_levels == ["observe_only"]
    assert decl.known_gaps == ["no_native_blocking_hook", "no_sandbox_posture_pinned"]


def test_claude_code_declares_native_blocking_hook() -> None:
    decl = ClaudeCodeAdapter().get_capability_declaration()

    validate_capability_declaration(decl)
    assert decl.harness == "claude_code"
    assert "native_blocking_hook" in decl.enforcement_levels


def test_harness_adapter_lifecycle_contract_requires_methods() -> None:
    abstract_methods = HarnessAdapter.__abstractmethods__

    assert {
        "prepare_launch",
        "install_enforcement",
        "spawn",
        "seed",
        "collect",
        "retire",
        "cleanup_on_failure",
    }.issubset(abstract_methods)
    assert "get_capability_declaration" in abstract_methods
