"""Dry-run argv tests for the DGX Controller runsc wrapper."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "deploy" / "dgx-controller-runsc" / "run-controller-runsc.sh"


def run_wrapper(*args: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "CE_DGX_DRY_RUN": "1",
            "CE_DGX_CONTROLLER_IMAGE": "creator-engine/claude-controller-runsc:test",
            "CE_DGX_REPO": "/repo/creator-engine",
            "CE_DGX_CONTROLLER_HOME": "/home/cedev4/.ce-controller",
            "CE_DGX_CLAUDE_BIN": "/opt/claude/bin/claude",
            "CE_DGX_UID": "1000",
            "CE_DGX_GID": "1000",
            "CE_DGX_TTY_FLAGS": "-i",
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


def test_controller_wrapper_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_controller_tui_dry_run_uses_contained_defaults():
    result = run_wrapper("tui")

    argv = dry_run_argv(result)

    assert argv[:2] == ["docker", "run"]
    assert "--runtime=runsc-gvproxy-ptrace" in argv
    assert "--security-opt=no-new-privileges" in argv
    assert "--cap-drop=ALL" in argv
    assert "--network=bridge" not in argv
    assert "--env" in argv
    assert "CLAUDE_CODE_OAUTH_TOKEN" in argv
    assert "synthetic-secret-token-value" not in result.stdout
    assert "creator-engine/claude-controller-runsc:test" in argv
    assert argv[-2:] == [
        "creator-engine/claude-controller-runsc:test",
        "/usr/local/bin/claude",
    ]
    assert any(
        arg == "type=bind,source=/repo/creator-engine,target=/workspace/creator-engine"
        for arg in argv
    )
    assert any(
        arg == "type=bind,source=/home/cedev4/.ce-controller,target=/home/cedev4"
        for arg in argv
    )
    assert any(
        arg == "type=bind,source=/opt/claude/bin/claude,target=/usr/local/bin/claude,readonly"
        for arg in argv
    )


def test_controller_exec_dry_run_maps_to_claude_print_mode():
    result = run_wrapper("exec", "summarize status")

    argv = dry_run_argv(result)

    assert argv[-4:] == [
        "creator-engine/claude-controller-runsc:test",
        "/usr/local/bin/claude",
        "-p",
        "summarize status",
    ]


def test_controller_wrapper_mounts_optional_supervisor_socket():
    result = run_wrapper("tui", CE_DGX_SUPERVISOR_SOCKET="/run/user/1000/ce-supervisor.sock")

    argv = dry_run_argv(result)

    assert "CE_SUPERVISOR_SOCKET=/run/ce-supervisor.sock" in argv
    assert any(
        arg
        == (
            "type=bind,source=/run/user/1000/ce-supervisor.sock,"
            "target=/run/ce-supervisor.sock"
        )
        for arg in argv
    )


def test_controller_wrapper_refuses_plain_runsc_by_default():
    result = run_wrapper("tui", CE_DGX_RUNTIME="runsc")

    assert result.returncode == 2
    assert "Refusing CE_DGX_RUNTIME=runsc" in result.stderr


def test_controller_wrapper_refuses_docker_network_by_default():
    result = run_wrapper("tui", CE_DGX_DOCKER_NETWORK="bridge")

    assert result.returncode == 2
    assert "Refusing Docker --network=bridge" in result.stderr
