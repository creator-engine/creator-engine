"""Dry-run argv tests for the VPS runsc/herdr launcher."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "deploy" / "vps-runsc" / "run-vps-runsc.sh"


def run_wrapper(*args: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "CE_VPS_DRY_RUN": "1",
            "CE_VPS_REPO": "/repo/creator-engine",
            "CE_VPS_CODEX_HOME": "/home/seat/.codex",
            "CE_VPS_CODEX_BIN": "/opt/codex/bin/codex",
            "CE_VPS_CLAUDE_BIN": "/opt/claude/bin/claude",
            "CE_VPS_CONTAINER_USER": "seat",
            "CE_VPS_UID": "1234",
            "CE_VPS_GID": "5678",
            "CE_VPS_TTY_FLAGS": "-i",
            "TERM": "xterm-256color",
            "CLAUDE_CODE_OAUTH_TOKEN": "synthetic-secret-token-value",
        }
    )
    env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT), "--dry-run", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def dry_run_argv(result: subprocess.CompletedProcess[str]) -> list[str]:
    assert result.returncode == 0, result.stderr
    return shlex.split(result.stdout)


def test_vps_launcher_shell_syntax_is_valid() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_codex_dry_run_uses_vps_containment_defaults() -> None:
    result = run_wrapper("exec", "summarize status")

    argv = dry_run_argv(result)

    assert argv[:2] == ["docker", "run"]
    assert "--runtime=runsc-gvproxy-ptrace" in argv
    assert "--network=host" in argv
    assert "--security-opt=no-new-privileges" in argv
    assert "--cap-drop=ALL" in argv
    assert "--user" in argv
    assert "1234:5678" in argv
    assert "creator-engine/codex-runsc:x86_64" in argv
    assert argv[-3:] == ["creator-engine/codex-runsc:x86_64", "exec", "summarize status"]
    assert "CE_DGX_HARNESS=codex" in argv
    assert "CE_DGX_HARNESS_MODE=exec" in argv
    assert "CODEX_HOME=/home/seat/.codex" in argv
    assert "TERM=xterm-256color" in argv


def test_codex_tui_dry_run_ends_at_image_without_literal_tui_subcommand() -> None:
    argv = dry_run_argv(run_wrapper("tui"))

    assert argv[-1] == "creator-engine/codex-runsc:x86_64"
    assert "CE_DGX_HARNESS=codex" in argv
    assert "CE_DGX_HARNESS_MODE=tui" in argv
    assert "tui" not in argv[argv.index("creator-engine/codex-runsc:x86_64") + 1 :]


def test_codex_dry_run_mounts_repo_codex_home_and_codex_binary() -> None:
    argv = dry_run_argv(run_wrapper("tui"))

    assert any(
        arg == "type=bind,source=/repo/creator-engine,target=/workspace/creator-engine"
        for arg in argv
    )
    assert any(
        arg == "type=bind,source=/home/seat/.codex,target=/home/seat/.codex"
        for arg in argv
    )
    assert any(
        arg == "type=bind,source=/opt/codex/bin/codex,target=/usr/local/bin/codex,readonly"
        for arg in argv
    )


def test_controller_variant_uses_claude_harness_marker_without_secret_value() -> None:
    result = run_wrapper("--harness", "controller", "tui")

    argv = dry_run_argv(result)

    assert argv[-1] == "creator-engine/codex-runsc:x86_64"
    assert "CE_DGX_HARNESS=claude" in argv
    assert "CE_DGX_HARNESS_MODE=tui" in argv
    assert "CLAUDE_CODE_OAUTH_TOKEN" in argv
    assert "synthetic-secret-token-value" not in result.stdout
    assert "tui" not in argv[argv.index("creator-engine/codex-runsc:x86_64") + 1 :]
    assert any(
        arg == "type=bind,source=/opt/claude/bin/claude,target=/usr/local/bin/claude,readonly"
        for arg in argv
    )


def test_no_herdr_socket_path_carrier_or_host_socket_mount_reaches_docker_argv() -> None:
    result = run_wrapper(
        "tui",
        HERDR_SOCKET_PATH="/run/user/1000/herdr.sock",
        HERDR_SOCKET="/run/user/1000/legacy-herdr.sock",
        CE_DGX_HERDR_SOCKET_PATH="/run/user/1000/ce-dgx-herdr.sock",
        CE_DGX_SOCKET_PATH="/run/user/1000/ce-dgx-generic.sock",
    )

    argv = dry_run_argv(result)
    rendered = result.stdout

    assert "HERDR_SOCKET" not in rendered
    assert "CE_DGX_HERDR_SOCKET_PATH" not in rendered
    assert not re.search(r"CE_DGX_[A-Z0-9_]*SOCKET[A-Z0-9_]*=", rendered)
    assert "/run/user/1000/herdr.sock" not in rendered
    assert "/run/user/1000/legacy-herdr.sock" not in rendered
    assert "/run/user/1000/ce-dgx-herdr.sock" not in rendered
    assert "/run/user/1000/ce-dgx-generic.sock" not in rendered
    assert not any(
        arg.startswith("type=bind,") and (".sock" in arg or "socket" in arg.lower())
        for arg in argv
    )
