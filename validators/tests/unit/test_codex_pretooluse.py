from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from creator_engine_validator import codex_pretooluse as cpt

REPO_ROOT = Path(__file__).resolve().parents[3]


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


def test_hook_check_cli_pretooluse_without_pyyaml_allows_and_denies(tmp_path):
    script = r'''
import contextlib
import importlib.abc
import io
import json
import sys


class BlockYaml(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "yaml" or fullname.startswith("yaml."):
            raise ModuleNotFoundError("blocked yaml")
        return None


sys.meta_path.insert(0, BlockYaml())
for name in list(sys.modules):
    if name == "yaml" or name.startswith("yaml."):
        del sys.modules[name]

from creator_engine_validator.cli import main

assert "yaml" not in sys.modules


def call(command):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "ce": {"posture": "governed", "seat_class": "worker"},
    }
    old_stdin = sys.stdin
    out = io.StringIO()
    sys.stdin = io.StringIO(json.dumps(event))
    try:
        with contextlib.redirect_stdout(out):
            code = main(["hook-check", "--stdin", "--format", "claude", "--posture", "governed"])
    finally:
        sys.stdin = old_stdin
    return {
        "code": code,
        "payload": json.loads(out.getvalue()),
        "yaml_imported": "yaml" in sys.modules,
    }


print(json.dumps([call("git status --short"), call("git push origin main")]))
'''
    env = dict(os.environ)
    validators_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = str(validators_root)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        check=True,
    )
    allow, deny = json.loads(completed.stdout)
    assert allow["code"] == 0
    assert allow["payload"]["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert allow["yaml_imported"] is False
    assert deny["code"] == 0
    assert deny["payload"]["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "restricted mechanic (deploy)" in deny["payload"]["hookSpecificOutput"]["permissionDecisionReason"]
    assert deny["yaml_imported"] is False


def test_codex_wrapper_without_pyyaml_allows_ls_and_denies_git_push(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.mkdir()
    (blocker / "sitecustomize.py").write_text(
        """
import importlib.abc


class BlockYaml(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "yaml" or fullname.startswith("yaml."):
            raise ModuleNotFoundError("blocked yaml")
        return None


import sys
sys.meta_path.insert(0, BlockYaml())
for name in list(sys.modules):
    if name == "yaml" or name.startswith("yaml."):
        del sys.modules[name]
""",
        encoding="utf-8",
    )

    env = dict(os.environ)
    validators_root = REPO_ROOT / "validators"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(blocker)
        + os.pathsep
        + str(validators_root)
        + (os.pathsep + existing if existing else "")
    )
    wrapper = REPO_ROOT / ".codex" / "hooks" / "ce-pretooluse-codex.py"

    def run(command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(wrapper)],
            input=json.dumps(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": command},
                    "cwd": str(tmp_path),
                    "ce": {"posture": "governed", "seat_class": "worker"},
                }
            ),
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )

    allow = run("ls")
    assert allow.stdout == ""
    assert allow.stderr == ""

    deny = run("git push origin main")
    assert deny.stderr == ""
    payload = json.loads(deny.stdout)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "restricted mechanic (deploy)" in payload["hookSpecificOutput"]["permissionDecisionReason"]
