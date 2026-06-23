"""Integration tests for the committed Codex PreToolUse hook shim."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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


def test_codex_governed_git_status_allows_with_no_output(tmp_path):
    proc = _run(_event("git status --short", tmp_path), tmp_path)

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert proc.stderr == ""
    assert _permission(proc.stdout) is None


def test_codex_malformed_input_fails_closed(tmp_path):
    proc = _run("{not json", tmp_path)

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "failed closed" in payload["hookSpecificOutput"]["permissionDecisionReason"]
