"""Unit tests for the v3 G-4 Tier-B derivation seam (cc_hook_adapter).

The adapter is a PURE function mapping a Claude-Code ``PreToolUse``-shaped payload
to the canonical ``AgentActionEvent``. These tests perform ZERO live subprocess /
socket and confirm the boundary-clean reuse rule (mutation_class via the shared
``checks.mutation_class`` taxonomy, never the v1 ``hook_check`` runtime).
"""

import socket
import subprocess

from creator_engine_validator.checks.mutation_class import BASELINE_NAMES_SET
from creator_engine_validator.runner.audit_overlay import AgentActionEvent
from creator_engine_validator.runner.cc_hook_adapter import (
    TIER_B_FIDELITY,
    TIER_B_TIMING,
    from_pre_tool_use,
)


def test_derives_write_docs_from_edit():
    ev = from_pre_tool_use({"tool_name": "Edit", "tool_input": {"file_path": "docs/x.md"}})
    assert isinstance(ev, AgentActionEvent)
    assert (ev.op, ev.mutation_class) == ("write", "docs")
    assert ev.target == "docs/x.md"
    assert ev.fidelity == TIER_B_FIDELITY == "best_effort"
    assert ev.timing == TIER_B_TIMING == "pre"


def test_derives_code_class_for_source_path():
    ev = from_pre_tool_use({"tool_name": "Write", "tool_input": {"file_path": "validators/x.py"}})
    assert (ev.op, ev.mutation_class) == ("write", "code")


def test_derives_governance_and_deploy_for_github():
    gov = from_pre_tool_use({"tool_name": "Edit", "tool_input": {"file_path": ".github/CODEOWNERS"}})
    assert gov.mutation_class == "governance"
    dep = from_pre_tool_use({"tool_name": "Edit", "tool_input": {"file_path": ".github/workflows/ci.yml"}})
    assert dep.mutation_class == "deploy"


def test_reads_are_observe_only():
    ev = from_pre_tool_use({"tool_name": "Read", "tool_input": {"file_path": "README.md"}})
    assert ev.op == "read"


def test_bash_command_op_derivation():
    assert from_pre_tool_use({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}).op == "vcs"
    assert from_pre_tool_use({"tool_name": "Bash", "tool_input": {"command": "curl https://x.example"}}).op == "egress"
    assert from_pre_tool_use({"tool_name": "Bash", "tool_input": {"command": "gpg --decrypt s.gpg"}}).op == "secret"
    assert from_pre_tool_use({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}).op == "exec"


def test_git_push_is_deploy_class():
    ev = from_pre_tool_use({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})
    assert ev.mutation_class == "deploy"


def test_camelcase_payload_keys_supported():
    ev = from_pre_tool_use({"toolName": "Edit", "toolInput": {"file_path": "docs/x.md"}})
    assert (ev.op, ev.mutation_class) == ("write", "docs")


def test_non_dict_payload_is_conservative():
    ev = from_pre_tool_use("not-a-dict")
    assert (ev.op, ev.mutation_class, ev.fidelity) == ("exec", "none", "best_effort")


def test_derived_class_is_always_in_shared_vocabulary():
    # Every derived class is a member of the shared taxonomy (or the explicit "none").
    samples = [
        {"tool_name": "Edit", "tool_input": {"file_path": p}}
        for p in (
            "docs/x.md", "validators/x.py", ".github/workflows/ci.yml", "schemas/x.schema.yaml",
            "secrets/key.pem", "governance/POLICY.md", "random/unknown.txt",
        )
    ]
    for payload in samples:
        cls = from_pre_tool_use(payload).mutation_class
        assert cls == "none" or cls in BASELINE_NAMES_SET


def test_derivation_is_pure(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the adapter must not touch a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    ev = from_pre_tool_use({"tool_name": "Edit", "tool_input": {"file_path": "docs/x.md"}})
    assert ev.op == "write"


def test_adapter_does_not_import_v1_hook_check():
    # Boundary guard at the source level: the Tier-B adapter must NOT couple the
    # v3 runner surface to the v1 hook_check runtime (that is a HARD version_boundary
    # crossing); it reuses the SHARED checks.mutation_class taxonomy instead. We
    # inspect the *imports* (the docstring may mention hook_check to explain the rule).
    import ast
    from pathlib import Path

    import creator_engine_validator.runner.cc_hook_adapter as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any("hook_check" in name for name in imported)
    assert any("checks.mutation_class" in name for name in imported)
