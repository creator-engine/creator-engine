from __future__ import annotations

import json
import subprocess
from pathlib import Path

from creator_engine_validator import codex_pretooluse as cpt


def test_normalize_maps_bash_tool_input_command():
    event = cpt.normalize_codex_pretooluse(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git status --short"},
            "cwd": "/worktree",
            "session_id": "s1",
            "tool_use_id": "t1",
        }
    )
    assert event["hook_event_name"] == "PreToolUse"
    assert event["tool_name"] == "Bash"
    assert event["tool_input"]["command"] == "git status --short"
    assert event["cwd"] == "/worktree"
    assert event["session_id"] == "s1"
    assert event["tool_use_id"] == "t1"


def test_normalize_maps_apply_patch_to_edit_and_extracts_path():
    event = cpt.normalize_codex_pretooluse(
        {
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: docs/x.md\n@@\n-old\n+new\n*** End Patch\n"
            },
        }
    )
    assert event["tool_name"] == "Edit"
    assert event["tool_input"]["file_path"] == "docs/x.md"


def test_run_allows_with_no_output_on_hook_check_allow(tmp_path):
    seen = {}

    def runner(argv, **kwargs):
        seen["argv"] = argv
        seen["input"] = json.loads(kwargs["input"])
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "ok",
                    }
                }
            ),
            stderr="",
        )

    code, out, err = cpt.run_codex_pretooluse(
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(tmp_path)}),
        adapter_path=Path("/repo/.codex/hooks/ce-pretooluse-codex.py"),
        runner=runner,
    )

    assert code == 0
    assert out == ""
    assert err == ""
    assert seen["input"]["tool_input"]["command"] == "git status"
    assert "--format" in seen["argv"] and "claude" in seen["argv"]


def test_run_translates_hook_check_deny_to_codex_contract(tmp_path):
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "restricted mechanic (deploy)",
                    }
                }
            ),
            stderr="",
        )

    code, out, err = cpt.run_codex_pretooluse(
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": str(tmp_path)}),
        adapter_path=Path("/repo/.codex/hooks/ce-pretooluse-codex.py"),
        runner=runner,
    )

    assert code == 0
    assert err == ""
    assert json.loads(out) == cpt.codex_deny_payload("restricted mechanic (deploy)")


def test_run_fails_closed_on_malformed_input():
    code, out, err = cpt.run_codex_pretooluse(
        "{not json",
        adapter_path=Path("/repo/.codex/hooks/ce-pretooluse-codex.py"),
    )
    payload = json.loads(out)
    assert code == 0
    assert err == ""
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "failed closed" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_run_fails_closed_on_hook_check_invocation_failure(tmp_path):
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv,
            2,
            stdout="synthetic-secret-token-value in stdout",
            stderr="synthetic-secret-token-value in stderr",
        )

    code, out, _err = cpt.run_codex_pretooluse(
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(tmp_path)}),
        adapter_path=Path("/repo/.codex/hooks/ce-pretooluse-codex.py"),
        runner=runner,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = payload["hookSpecificOutput"]["permissionDecisionReason"]
    assert "failed closed" in reason
    assert "hook-check invocation failed" in reason
    assert "synthetic-secret-token-value" not in out
    assert "synthetic-secret-token-value" not in reason


def test_run_fails_closed_on_hook_check_runner_exception_without_details(tmp_path):
    def runner(argv, **kwargs):
        raise RuntimeError("synthetic-secret-token-value")

    code, out, _err = cpt.run_codex_pretooluse(
        json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(tmp_path)}),
        adapter_path=Path("/repo/.codex/hooks/ce-pretooluse-codex.py"),
        runner=runner,
    )

    assert code == 0
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = payload["hookSpecificOutput"]["permissionDecisionReason"]
    assert "failed closed" in reason
    assert "hook-check invocation failed" in reason
    assert "synthetic-secret-token-value" not in out
    assert "synthetic-secret-token-value" not in reason
