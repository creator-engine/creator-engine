from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from creator_engine_validator.harness_adapters.claude_code_adapter import ClaudeCodeAdapter


LIFECYCLE_METHODS = (
    ("prepare_launch", "prepared"),
    ("install_enforcement", "enforcement_installed"),
    ("spawn", "spawned"),
    ("seed", "seeded"),
    ("collect", "evidence_collected"),
    ("retire", "retired"),
    ("cleanup_on_failure", "cleaned_up"),
)


@pytest.mark.parametrize(("method_name", "status"), LIFECYCLE_METHODS)
def test_claude_code_lifecycle_methods_return_mapping_with_none(
    method_name: str, status: str
) -> None:
    result = getattr(ClaudeCodeAdapter(), method_name)(None)

    assert isinstance(result, Mapping)
    assert result["harness"] == "claude_code"
    assert result["status"] == status


@pytest.mark.parametrize(("method_name", "status"), LIFECYCLE_METHODS)
def test_claude_code_lifecycle_methods_merge_context(method_name: str, status: str) -> None:
    result = getattr(ClaudeCodeAdapter(), method_name)({"caller_key": "v"})

    assert result["caller_key"] == "v"
    assert result["harness"] == "claude_code"
    assert result["status"] == status


def test_claude_code_cleanup_on_failure_marks_failure() -> None:
    result = ClaudeCodeAdapter().cleanup_on_failure()

    assert result["failure"] is True


def test_claude_code_spawn_records_gvisor_sandbox() -> None:
    result = ClaudeCodeAdapter().spawn()

    assert result["sandbox"] == "gvisor"


def test_claude_code_install_enforcement_records_pretooluse_hook() -> None:
    result = ClaudeCodeAdapter().install_enforcement()

    assert result["mechanism"] == "pre_tool_use_hook"


@pytest.mark.parametrize(("method_name", "_status"), LIFECYCLE_METHODS)
def test_claude_code_all_lifecycle_results_identify_harness(
    method_name: str, _status: str
) -> None:
    result: Mapping[str, Any] = getattr(ClaudeCodeAdapter(), method_name)()

    assert result["harness"] == "claude_code"
