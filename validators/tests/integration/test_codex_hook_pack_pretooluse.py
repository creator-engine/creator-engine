"""Integration tests for the committed Codex PreToolUse hook shim."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]
PRETOOLUSE = REPO_ROOT / ".codex/hooks/ce-pretooluse-codex.py"


def _event(command: str, cwd: Path) -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
        "session_id": "codex-session",
        "tool_use_id": "tool-use-1",
        "ce": {"posture": "governed", "manifest_paths": ["docs/keep.md"]},
    }


def _tool_event(tool_name: str, tool_input: dict, cwd: Path) -> dict:
    return {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "cwd": str(cwd),
        "session_id": "codex-session",
        "tool_use_id": "tool-use-1",
        "ce": {"posture": "governed", "manifest_paths": ["docs/keep.md"]},
    }


def _run(payload: dict | str, cwd: Path) -> subprocess.CompletedProcess[str]:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "validators") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, str(PRETOOLUSE)],
        input=text,
        text=True,
        capture_output=True,
        cwd=cwd,
        env=env,
        check=False,
    )


def _permission(stdout: str) -> str | None:
    if not stdout.strip():
        return None
    payload = json.loads(stdout)
    return payload["hookSpecificOutput"]["permissionDecision"]


def test_codex_governed_git_push_denies(tmp_path):
    proc = _run(_event("git push origin main", tmp_path), tmp_path)

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "restricted mechanic (deploy) is denied without a matching ratified "
                "reviewer-venue side-effect-authority envelope (G2.007.2)"
            ),
        }
    }


def test_codex_governed_git_push_without_envelope_denies(tmp_path):
    proc = _run(_event("git push origin main", tmp_path), tmp_path)

    assert proc.returncode == 0
    assert _permission(proc.stdout) == "deny"
    assert "restricted mechanic (deploy)" in proc.stdout


def test_codex_governed_git_status_allows_with_no_output(tmp_path):
    proc = _run(_event("git status --short", tmp_path), tmp_path)

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""
    assert _permission(proc.stdout) is None


def test_codex_governed_credential_read_denies_without_secret_echo(tmp_path):
    proc = _run(
        _tool_event("Read", {"file_path": ".env", "token": "synthetic-secret-token-value"}, tmp_path),
        tmp_path,
    )

    assert proc.returncode == 0
    assert proc.stderr == ""
    payload = json.loads(proc.stdout)
    output = payload["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert "credential-like path denied" in output["permissionDecisionReason"]
    assert "synthetic-secret-token-value" not in proc.stdout


def test_codex_governed_out_of_manifest_apply_patch_is_advisory_allow(tmp_path):
    proc = _run(
        _tool_event(
            "apply_patch",
            {
                "command": (
                    "*** Begin Patch\n"
                    "*** Update File: docs/outside.md\n"
                    "@@\n"
                    "-old\n"
                    "+new\n"
                    "*** End Patch\n"
                )
            },
            tmp_path,
        ),
        tmp_path,
    )

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""


def test_codex_malformed_input_fails_closed(tmp_path):
    proc = _run("{not json", tmp_path)

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "failed closed" in payload["hookSpecificOutput"]["permissionDecisionReason"]
