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
    assert "--tmpfs" in argv
    assert "/run/creator-engine:uid=1000,gid=1000,mode=0700" in argv
    assert "--network=bridge" not in argv
    assert "--env" in argv
    assert "CLAUDE_CODE_OAUTH_TOKEN" in argv
    assert "synthetic-secret-token-value" not in result.stdout
    assert "creator-engine/claude-controller-runsc:test" in argv
    assert argv[-1] == "creator-engine/claude-controller-runsc:test"
    assert "CE_DGX_HARNESS=claude" in argv
    assert "CE_DGX_HARNESS_BIN=/usr/local/bin/claude" in argv
    assert "CE_DGX_HARNESS_HOME=/home/cedev4" in argv
    assert "CE_DGX_HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock" in argv
    assert "XDG_CONFIG_HOME=/run/creator-engine/xdg/config" in argv
    assert "XDG_STATE_HOME=/run/creator-engine/xdg/state" in argv
    assert "XDG_CACHE_HOME=/run/creator-engine/xdg/cache" in argv
    assert "CE_DGX_TERMINAL_KIND=herdr" in argv
    assert "CE_TERMINAL_KIND=herdr" in argv
    assert not any(arg.startswith("HERDR_SOCKET_PATH=") for arg in argv)
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
    assert not any("/run/creator-engine/herdr" in arg and arg.startswith("type=bind,") for arg in argv)


def test_controller_exec_dry_run_maps_to_claude_print_mode():
    result = run_wrapper("exec", "summarize status")

    argv = dry_run_argv(result)

    assert argv[-3:] == [
        "creator-engine/claude-controller-runsc:test",
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


def test_controller_detach_flag_uses_named_persistent_container():
    result = run_wrapper("--detach", "tui")

    argv = dry_run_argv(result)

    assert "-d" in argv
    assert "--name" in argv
    assert "ce-dgx-controller" in argv
    name_idx = argv.index("--name")
    assert argv[name_idx + 1] == "ce-dgx-controller"
    assert "--rm" not in argv


def test_controller_detach_custom_container_name_propagates():
    result = run_wrapper(
        "--detach", "tui", CE_DGX_CONTROLLER_CONTAINER_NAME="ce-controller-canary"
    )

    argv = dry_run_argv(result)

    assert "--name" in argv
    name_idx = argv.index("--name")
    assert argv[name_idx + 1] == "ce-controller-canary"
    assert "ce-dgx-controller" not in argv
    assert "--rm" not in argv


def test_controller_foreground_default_keeps_rm_not_detached():
    result = run_wrapper("tui")

    argv = dry_run_argv(result)

    assert "--rm" in argv
    assert "-d" not in argv
    assert "--name" not in argv


def test_controller_detach_env_triggers_detached_argv():
    result = run_wrapper("tui", CE_DGX_CONTROLLER_DETACH="1")

    argv = dry_run_argv(result)

    assert "-d" in argv
    assert "--name" in argv
    assert "ce-dgx-controller" in argv
    assert "--rm" not in argv


def test_controller_detach_keeps_oauth_token_passthrough_valueless():
    result = run_wrapper("--detach", "tui")

    argv = dry_run_argv(result)

    assert "CLAUDE_CODE_OAUTH_TOKEN" in argv
    assert not any(arg.startswith("CLAUDE_CODE_OAUTH_TOKEN=") for arg in argv)
    assert "synthetic-secret-token-value" not in result.stdout
