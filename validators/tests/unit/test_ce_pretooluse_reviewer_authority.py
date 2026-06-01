"""G2.007.3 — the live PreToolUse hook forwards the launch-pinned reviewer-authority ref.

A governed reviewer venue exports ``CE_REVIEWER_AUTHORITY_REF`` (a repo-relative
reviewer-authority envelope path) into the pane environment at launch. The committed
``.claude/hooks/ce-pretooluse.sh`` must pass it to the Ring-2 validator as
``--reviewer-authority-ref`` so ``hook_check`` can resolve ``ce.reviewer_authority_ref``.

Fail-closed: when the env var is unset/empty, the flag MUST NOT be added (no authority
=> restricted mechanics stay denied). The validator is stubbed on PATH to capture argv;
no real validator, Claude launch, or pane spawn occurs.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / ".claude" / "hooks" / "ce-pretooluse.sh"


def _stub_validator(bin_dir: Path, capture: Path) -> None:
    """Write an executable `creator-engine-validator` stub that records its argv."""
    stub = bin_dir / "creator-engine-validator"
    stub.write_text(
        "#!/usr/bin/env sh\n"
        f'printf "%s\\n" "$@" > {capture}\n'
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)


def _run_hook(tmp_path: Path, *, env_ref: str | None) -> list[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "argv.txt"
    _stub_validator(bin_dir, capture)

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    if env_ref is None:
        env.pop("CE_REVIEWER_AUTHORITY_REF", None)
    else:
        env["CE_REVIEWER_AUTHORITY_REF"] = env_ref

    event = '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"gh pr review 108 --approve"}}'
    proc = subprocess.run(
        ["sh", str(HOOK)], input=event, text=True, env=env,
        capture_output=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return capture.read_text(encoding="utf-8").splitlines() if capture.is_file() else []


@pytest.mark.skipif(not HOOK.is_file(), reason="hook script not present")
def test_hook_forwards_reviewer_authority_ref_when_set(tmp_path):
    argv = _run_hook(tmp_path, env_ref=".hermes/g20073/reviewer-authority.ce.yml")
    assert "hook-check" in argv
    assert "--reviewer-authority-ref" in argv
    idx = argv.index("--reviewer-authority-ref")
    assert argv[idx + 1] == ".hermes/g20073/reviewer-authority.ce.yml"


@pytest.mark.skipif(not HOOK.is_file(), reason="hook script not present")
def test_hook_omits_flag_when_env_unset(tmp_path):
    argv = _run_hook(tmp_path, env_ref=None)
    assert "hook-check" in argv
    assert "--reviewer-authority-ref" not in argv
