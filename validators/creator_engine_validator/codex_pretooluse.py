"""Codex PreToolUse adapter for CE's shared ``hook-check`` policy.

Codex and Claude Code use different hook input envelopes, but CE policy must
stay single-sourced in :mod:`creator_engine_validator.hook_check`. This adapter
normalizes Codex's ``PreToolUse`` JSON into the existing hook-check CLI shape,
invokes that validator, and translates the result back into Codex's deny-capable
contract.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DENY_EVENT = "PreToolUse"
DEFAULT_EVIDENCE_ROOT = ".hermes"
HOOK_CHECK_FORMAT = "claude"
HOOK_CHECK_INVOCATION_FAILED = "hook-check invocation failed"


class CodexHookInputError(ValueError):
    """The Codex hook payload cannot be safely normalized."""


@dataclass(frozen=True)
class HookCheckInvocation:
    argv: tuple[str, ...]
    input_json: str
    cwd: Path
    env: Mapping[str, str]


def codex_deny_payload(reason: str) -> dict[str, Any]:
    """Return the exact Codex PreToolUse deny output shape."""
    return {
        "hookSpecificOutput": {
            "hookEventName": DENY_EVENT,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _string_field(payload: Mapping[str, Any], *names: str) -> str | None:
    for name in names:
        value = payload.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_tool_name(raw: str) -> str:
    """Map Codex tool names onto hook-check's existing policy vocabulary."""
    if raw in {"Bash", "Read", "Edit", "Write", "MultiEdit"}:
        return raw
    lowered = raw.lower()
    if lowered == "apply_patch":
        return "Edit"
    if lowered in {"edit", "write", "multiedit", "read", "bash"}:
        return raw[:1].upper() + raw[1:]
    return raw


def _first_patch_path(patch_text: str) -> str | None:
    """Best-effort path extraction for Codex ``apply_patch`` payloads.

    This is adapter-only normalization, not policy. Missing paths intentionally
    remain missing; ``hook-check`` then treats mutating tools conservatively for
    foreman-delegation classification.
    """
    for line in patch_text.splitlines():
        if line.startswith("*** Update File: "):
            return line.removeprefix("*** Update File: ").strip()
        if line.startswith("*** Add File: "):
            return line.removeprefix("*** Add File: ").strip()
        if line.startswith("*** Delete File: "):
            return line.removeprefix("*** Delete File: ").strip()
    return None


def normalize_codex_pretooluse(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a Codex PreToolUse JSON object into hook-check input."""
    raw_tool = _string_field(payload, "tool_name", "toolName")
    if raw_tool is None:
        raise CodexHookInputError("missing required string field: tool_name")
    raw_input = payload.get("tool_input", payload.get("toolInput", {}))
    if raw_input is None:
        raw_input = {}
    if not isinstance(raw_input, dict):
        raise CodexHookInputError("tool_input must be an object")

    tool = _normalize_tool_name(raw_tool)
    tool_input = dict(raw_input)
    if tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str) or not command.strip():
            raise CodexHookInputError("Bash tool_input.command must be a non-empty string")
    elif raw_tool.lower() == "apply_patch":
        path = _string_field(tool_input, "file_path", "filePath", "path")
        patch = tool_input.get("patch") or tool_input.get("command")
        if path is None and isinstance(patch, str):
            path = _first_patch_path(patch)
        if path:
            tool_input["file_path"] = path

    event: dict[str, Any] = {
        "hook_event_name": DENY_EVENT,
        "tool_name": tool,
        "tool_input": tool_input,
    }
    for source, target in (
        ("cwd", "cwd"),
        ("session_id", "session_id"),
        ("sessionId", "session_id"),
        ("tool_use_id", "tool_use_id"),
        ("toolUseId", "tool_use_id"),
    ):
        value = payload.get(source)
        if isinstance(value, str) and value:
            event[target] = value
    ce = payload.get("ce")
    if isinstance(ce, dict):
        event["ce"] = dict(ce)
    return event


def _repo_root_from_adapter(adapter_path: Path) -> Path:
    # .codex/hooks/ce-pretooluse-codex.py -> repo root
    return adapter_path.resolve().parents[2]


def build_hook_check_invocation(
    normalized_event: Mapping[str, Any],
    *,
    repo_root: Path,
    cwd: Path,
    python_executable: str | None = None,
    base_env: Mapping[str, str] | None = None,
) -> HookCheckInvocation:
    """Build the hook-check subprocess invocation."""
    py = python_executable or sys.executable
    env = dict(os.environ if base_env is None else base_env)
    existing = env.get("PYTHONPATH", "")
    validators_root = str(repo_root / "validators")
    env["PYTHONPATH"] = validators_root if not existing else validators_root + os.pathsep + existing

    argv: list[str] = [
        py,
        "-m",
        "creator_engine_validator",
        "hook-check",
        "--stdin",
        "--format",
        HOOK_CHECK_FORMAT,
        "--posture-root",
        str(cwd),
        "--evidence-root",
        DEFAULT_EVIDENCE_ROOT,
    ]
    ledger_root = env.get("CE_LEDGER_ROOT")
    if ledger_root:
        argv.extend(["--ledger-root", ledger_root])
    reviewer_ref = env.get("CE_REVIEWER_AUTHORITY_REF")
    if reviewer_ref:
        argv.extend(["--reviewer-authority-ref", reviewer_ref])
    return HookCheckInvocation(
        argv=tuple(argv),
        input_json=json.dumps(dict(normalized_event), separators=(",", ":")),
        cwd=cwd,
        env=env,
    )


def _decision_from_hook_check(stdout: str) -> tuple[str, str]:
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        raise CodexHookInputError(f"hook-check returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CodexHookInputError("hook-check returned a non-object decision")
    output = payload.get("hookSpecificOutput")
    if not isinstance(output, dict):
        raise CodexHookInputError("hook-check returned no hookSpecificOutput")
    decision = output.get("permissionDecision")
    reason = output.get("permissionDecisionReason")
    if decision not in {"allow", "deny"} or not isinstance(reason, str):
        raise CodexHookInputError("hook-check returned malformed PreToolUse decision")
    return decision, reason


def run_codex_pretooluse(
    stdin_text: str,
    *,
    adapter_path: Path,
    runner=subprocess.run,
) -> tuple[int, str, str]:
    """Run the adapter.

    Returns ``(exit_code, stdout, stderr)``. A policy deny exits 0 with Codex's
    deny JSON. An allow exits 0 with no output. Malformed input or hook-check
    failures fail closed as deny JSON.
    """
    try:
        payload = json.loads(stdin_text)
        if not isinstance(payload, dict):
            raise CodexHookInputError("Codex hook input must be a JSON object")
        normalized = normalize_codex_pretooluse(payload)
        cwd_raw = payload.get("cwd")
        cwd = Path(cwd_raw).expanduser() if isinstance(cwd_raw, str) and cwd_raw else Path.cwd()
        repo_root = _repo_root_from_adapter(adapter_path)
        invocation = build_hook_check_invocation(normalized, repo_root=repo_root, cwd=cwd)
        try:
            completed = runner(
                list(invocation.argv),
                input=invocation.input_json,
                text=True,
                capture_output=True,
                cwd=str(invocation.cwd),
                env=dict(invocation.env),
                check=False,
            )
        except Exception as exc:
            raise CodexHookInputError(HOOK_CHECK_INVOCATION_FAILED) from exc
        if completed.returncode != 0:
            raise CodexHookInputError(HOOK_CHECK_INVOCATION_FAILED)
        decision, reason = _decision_from_hook_check(completed.stdout or "")
        if decision == "allow":
            return 0, "", ""
        return 0, json.dumps(codex_deny_payload(reason), separators=(",", ":")) + "\n", ""
    except Exception as exc:
        reason = f"CE Codex PreToolUse hook failed closed: {exc}"
        return 0, json.dumps(codex_deny_payload(reason), separators=(",", ":")) + "\n", ""


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    code, stdout, stderr = run_codex_pretooluse(
        sys.stdin.read(),
        adapter_path=Path(__file__),
    )
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, file=sys.stderr, end="")
    return code


if __name__ == "__main__":  # pragma: no cover - script entry
    raise SystemExit(main())
