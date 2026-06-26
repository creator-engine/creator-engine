"""Dry-run argv tests for the DGX Controller runsc wrapper."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "deploy" / "dgx-controller-runsc" / "run-controller-runsc.sh"
DOCKERFILE = REPO_ROOT / "deploy" / "dgx-controller-runsc" / "Dockerfile"
GH_GUARD = REPO_ROOT / "deploy" / "dgx-controller-runsc" / "ce-controller-gh-guard.sh"
README = REPO_ROOT / "deploy" / "dgx-controller-runsc" / "README.md"
DESIGN = REPO_ROOT / "deploy" / "dgx-controller-runsc" / "DESIGN.md"
TOKEN_ENV_NAME = "CLAUDE_CODE_OAUTH_TOKEN"
SYNTHETIC_TOKEN = "synthetic-secret-token-value"


def run_wrapper(*args: str, **env_overrides: str | None) -> subprocess.CompletedProcess[str]:
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
            # C1 credential injection is SEAM-STUB only. Keep a host token present
            # so dry-run tests prove the wrapper does not pass it through.
            TOKEN_ENV_NAME: SYNTHETIC_TOKEN,
        }
    )
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
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


def assert_no_claude_token_leaked(
    result: subprocess.CompletedProcess[str], argv: list[str] | None = None
) -> None:
    haystacks = [result.stdout, result.stderr]
    if argv is not None:
        haystacks.extend(argv)

    for haystack in haystacks:
        assert TOKEN_ENV_NAME not in haystack
        assert SYNTHETIC_TOKEN not in haystack
        assert "CE_DGX_CONTROLLER_ALLOW_DETACHED_TOKEN_ENV" not in haystack


def test_controller_wrapper_shell_syntax_is_valid() -> None:
    for script in (SCRIPT, GH_GUARD):
        result = subprocess.run(
            ["bash", "-n", str(script)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, f"{script}: {result.stderr}"


def test_controller_gh_guard_defaults_to_fail_closed_without_credential_seam() -> None:
    env = os.environ.copy()
    env.update(
        {
            TOKEN_ENV_NAME: SYNTHETIC_TOKEN,
            "CE_DGX_CREDENTIAL_INJECTION": "SEAM-STUB",
            "CE_TRANSPORT_DEPUTY_SEAM_STATUS": "stub-ce-ops-239-no-secret-injection",
        }
    )

    result = subprocess.run(
        ["bash", str(GH_GUARD), "auth", "status", SYNTHETIC_TOKEN],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 78
    assert "Refusing controller gh action" in result.stderr
    assert "gate/source-host actions fail closed" in result.stderr
    assert "stub-ce-ops-239-no-secret-injection" in result.stderr
    assert "ready-ce-ops-239-credential-injection" in result.stderr
    assert "TRANSPORT-DEPUTY" in result.stderr
    assert "auth status" not in result.stderr
    assert TOKEN_ENV_NAME not in result.stderr
    assert SYNTHETIC_TOKEN not in result.stderr
    assert result.stdout == ""


def test_controller_gh_guard_refuses_partial_ready_marker() -> None:
    env = os.environ.copy()
    env.update(
        {
            "CE_DGX_CREDENTIAL_INJECTION": "SEAM-STUB",
            "CE_TRANSPORT_DEPUTY_SEAM_STATUS": "ready-ce-ops-239-credential-injection",
        }
    )

    result = subprocess.run(
        ["bash", str(GH_GUARD), "pr", "merge"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 78
    assert "Refusing controller gh action" in result.stderr
    assert "pr merge" not in result.stderr
    assert TOKEN_ENV_NAME not in result.stderr
    assert SYNTHETIC_TOKEN not in result.stderr


def test_controller_tui_dry_run_uses_contained_defaults() -> None:
    result = run_wrapper("tui")

    argv = dry_run_argv(result)

    assert argv[:2] == ["docker", "run"]
    assert "--runtime=runsc-gvproxy-ptrace" in argv
    assert "--security-opt=no-new-privileges" in argv
    assert "--cap-drop=ALL" in argv
    assert "--tmpfs" in argv
    assert "/run/creator-engine:uid=1000,gid=1000,mode=0700" in argv
    assert "/run/creator-engine/controller-log:uid=1000,gid=1000,mode=0700" in argv
    assert not any(arg.startswith("--network=") for arg in argv)
    assert "--env" in argv
    assert "CE_SEAT_LOG_DIR=/run/creator-engine/controller-log" in argv
    assert "CE_CODEX_STDERR_LOG=/run/creator-engine/controller-log/controller-stderr.log" in argv
    assert "CE_DGX_CREDENTIAL_INJECTION=SEAM-STUB" in argv
    assert_no_claude_token_leaked(result, argv)
    assert "creator-engine/claude-controller-runsc:test" in argv
    assert argv[-1] == "creator-engine/claude-controller-runsc:test"
    assert "CE_DGX_HARNESS=claude" in argv
    assert "CE_DGX_HARNESS_BIN=/usr/local/bin/ce-controller-harness" in argv
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


def test_controller_exec_dry_run_maps_to_claude_print_mode() -> None:
    result = run_wrapper("exec", "summarize status")

    argv = dry_run_argv(result)

    assert argv[-3:] == [
        "creator-engine/claude-controller-runsc:test",
        "-p",
        "summarize status",
    ]
    assert_no_claude_token_leaked(result, argv)


def test_controller_wrapper_mounts_optional_supervisor_socket() -> None:
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
    assert_no_claude_token_leaked(result, argv)


def test_controller_dry_run_does_not_mount_host_control_sockets() -> None:
    result = run_wrapper("tui")

    argv = dry_run_argv(result)
    mounts = [argv[index + 1] for index, arg in enumerate(argv[:-1]) if arg == "--mount"]
    forbidden_fragments = (
        "/run/creator-engine/herdr",
        "/tmp/tmux-",
        "/run/tmux",
        "/var/run/docker.sock",
        "/run/docker.sock",
        "/run/podman/podman.sock",
        "/run/containerd/containerd.sock",
    )

    assert mounts
    for mount in mounts:
        assert not any(fragment in mount for fragment in forbidden_fragments)


def test_controller_wrapper_refuses_plain_runsc_by_default() -> None:
    result = run_wrapper("tui", CE_DGX_RUNTIME="runsc")

    assert result.returncode == 2
    assert "Refusing CE_DGX_RUNTIME=runsc" in result.stderr
    assert_no_claude_token_leaked(result)


def test_controller_wrapper_refuses_docker_network_by_default() -> None:
    result = run_wrapper("tui", CE_DGX_DOCKER_NETWORK="bridge")

    assert result.returncode == 2
    assert "Refusing Docker --network=bridge" in result.stderr
    assert_no_claude_token_leaked(result)


def test_controller_detach_flag_uses_named_persistent_container_without_token_optin() -> None:
    result = run_wrapper("--detach", "tui")

    argv = dry_run_argv(result)

    assert "-d" in argv
    assert "--name" in argv
    assert "ce-dgx-controller" in argv
    name_idx = argv.index("--name")
    assert argv[name_idx + 1] == "ce-dgx-controller"
    assert "--rm" not in argv
    assert_no_claude_token_leaked(result, argv)


def test_controller_detach_custom_container_name_propagates() -> None:
    result = run_wrapper(
        "--detach",
        "tui",
        CE_DGX_CONTROLLER_CONTAINER_NAME="ce-controller-canary",
    )

    argv = dry_run_argv(result)

    assert "--name" in argv
    name_idx = argv.index("--name")
    assert argv[name_idx + 1] == "ce-controller-canary"
    assert "ce-dgx-controller" not in argv
    assert "--rm" not in argv
    assert_no_claude_token_leaked(result, argv)


def test_controller_foreground_default_keeps_rm_not_detached() -> None:
    result = run_wrapper("tui")

    argv = dry_run_argv(result)

    assert "--rm" in argv
    assert "-d" not in argv
    assert "--name" not in argv
    assert_no_claude_token_leaked(result, argv)


def test_controller_detach_env_triggers_detached_argv_without_token_optin() -> None:
    result = run_wrapper("tui", CE_DGX_CONTROLLER_DETACH="1")

    argv = dry_run_argv(result)

    assert "-d" in argv
    assert "--name" in argv
    assert "ce-dgx-controller" in argv
    assert "--rm" not in argv
    assert_no_claude_token_leaked(result, argv)


def test_controller_detach_ignores_legacy_token_retention_optin() -> None:
    result = run_wrapper(
        "--detach", "tui", CE_DGX_CONTROLLER_ALLOW_DETACHED_TOKEN_ENV="1"
    )

    argv = dry_run_argv(result)

    assert "-d" in argv
    assert "--rm" not in argv
    assert "REFUSED" not in result.stderr
    assert "WARNING" not in result.stderr
    assert_no_claude_token_leaked(result, argv)


def test_herdr_pane_list_parser_fails_closed_on_invalid_json() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "def has_pane(value):" in text
    assert "except json.JSONDecodeError:\n    raise SystemExit(1)" in text
    assert "except json.JSONDecodeError:\n    raise SystemExit(0)" not in text


def test_controller_image_scaffolding_has_pinned_herdr_builder_and_tools() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM rust:1-bookworm AS herdr-builder" in text
    assert "HERDR_CE_REF=" in text
    assert "cargo build" in text
    assert "--release" in text
    assert "--locked" in text
    assert "COPY --from=herdr-builder" in text
    assert "/usr/local/bin/herdr" in text
    assert "gh" in text
    assert "git" in text
    assert "PYTHONPATH=/workspace/creator-engine/validators" in text
    assert "creator_engine_validator" in text
    assert "COPY deploy/dgx-controller-runsc/ce-controller-gh-guard.sh /usr/local/bin/ce-controller-gh-guard" in text
    assert "ln -s /usr/local/bin/ce-controller-gh-guard /usr/local/bin/gh" in text
    assert "/usr/bin/gh --version" in text
    assert "/usr/local/bin/gh auth status" in text
    assert 'test "$?" = "78"' in text
    assert "} >/usr/local/bin/ce-controller-harness" in text
    assert 'export PYTHONPATH="${validator_path}${PYTHONPATH:+:${PYTHONPATH}}"' in text
    assert 'export CE_DGX_CREDENTIAL_INJECTION="${CE_DGX_CREDENTIAL_INJECTION:-SEAM-STUB}"' in text
    assert (
        'export CE_TRANSPORT_DEPUTY_SEAM_STATUS="${CE_TRANSPORT_DEPUTY_SEAM_STATUS:-stub-ce-ops-239-no-secret-injection}"'
        in text
    )
    assert 'exec /usr/local/bin/claude "$@"' in text
    assert TOKEN_ENV_NAME not in text
    assert SYNTHETIC_TOKEN not in text


def test_controller_docs_state_gh_guard_refusal_contract() -> None:
    readme = README.read_text(encoding="utf-8")
    design = DESIGN.read_text(encoding="utf-8")

    for text in (readme, design):
        assert "/usr/local/bin/gh" in text
        assert "ce-controller-gh-guard" in text
        assert "stub-ce-ops-239-no-secret-injection" in text
        assert "ready-ce-ops-239-credential-injection" in text
        assert "TRANSPORT-DEPUTY" in text
        assert "CE_TRANSPORT_DEPUTY_GH_REAL=/usr/bin/gh" in text
        assert "fail closed" in text
