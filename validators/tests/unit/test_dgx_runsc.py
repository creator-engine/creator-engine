"""Dry-run argv and static entrypoint tests for the DGX Codex runsc wrapper."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "deploy" / "dgx-runsc" / "run-codex-runsc.sh"
ENTRYPOINT = REPO_ROOT / "deploy" / "dgx-runsc" / "herdr-harness-entrypoint.sh"
DOCKERFILE = REPO_ROOT / "deploy" / "dgx-runsc" / "Dockerfile"


def run_wrapper(*args: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "CE_DGX_DRY_RUN": "1",
            "CE_DGX_IMAGE": "creator-engine/codex-runsc:test",
            "CE_DGX_REPO": "/repo/creator-engine",
            "CE_DGX_CODEX_HOME": "/home/cedev4/.codex",
            "CE_DGX_CODEX_BIN": "/opt/codex/bin/codex",
            "CE_DGX_UID": "1000",
            "CE_DGX_GID": "1000",
            "CE_DGX_TTY_FLAGS": "-i",
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


def test_codex_wrapper_shell_syntax_is_valid() -> None:
    for path in (SCRIPT, ENTRYPOINT):
        result = subprocess.run(
            ["bash", "-n", str(path)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr


def test_codex_exec_dry_run_uses_runsc_image_entrypoint_and_harness_markers() -> None:
    result = run_wrapper("exec", "print working tree status")

    argv = dry_run_argv(result)

    assert argv[:2] == ["docker", "run"]
    assert "--runtime=runsc-gvproxy-ptrace" in argv
    assert "--security-opt=no-new-privileges" in argv
    assert "--cap-drop=ALL" in argv
    assert not any(arg.startswith("--network=") for arg in argv)
    assert "creator-engine/codex-runsc:test" in argv
    assert argv[-3:] == [
        "creator-engine/codex-runsc:test",
        "exec",
        "print working tree status",
    ]
    assert "/usr/local/bin/codex" not in argv[argv.index("creator-engine/codex-runsc:test") + 1 :]
    assert "CE_DGX_HARNESS=codex" in argv
    assert "CE_DGX_HARNESS_BIN=/usr/local/bin/codex" in argv
    assert "CE_DGX_HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock" in argv
    assert "CE_DGX_TERMINAL_KIND=herdr" in argv
    assert "CE_TERMINAL_KIND=herdr" in argv
    assert not any(arg.startswith("HERDR_SOCKET_PATH=") for arg in argv)
    assert any(
        arg == "type=bind,source=/repo/creator-engine,target=/workspace/creator-engine"
        for arg in argv
    )
    assert any(
        arg == "type=bind,source=/home/cedev4/.codex,target=/home/cedev4/.codex"
        for arg in argv
    )
    assert any(
        arg == "type=bind,source=/opt/codex/bin/codex,target=/usr/local/bin/codex,readonly"
        for arg in argv
    )
    assert not any("/run/creator-engine/herdr" in arg and arg.startswith("type=bind,") for arg in argv)


def test_codex_tui_dry_run_lets_image_entrypoint_select_default_harness() -> None:
    result = run_wrapper("tui")

    argv = dry_run_argv(result)

    assert argv[-1] == "creator-engine/codex-runsc:test"


def test_entrypoint_fail_closed_and_uses_herdr_control_path_only_for_cli() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")

    assert '[ -x "${HERDR_BIN}" ] || fail "herdr binary is not executable: ${HERDR_BIN}"' in text
    assert '[ -x "${HARNESS_BIN}" ] || fail "harness binary is not executable: ${HARNESS_BIN}"' in text
    assert 'DEFAULT_SOCKET="/run/creator-engine/herdr/herdr.sock"' in text
    assert 'install -d -m 0700 "${SOCKET_DIR}"' in text
    assert 'HERDR_SOCKET_PATH="${CE_DGX_HERDR_SOCKET_PATH:-${DEFAULT_SOCKET}}" "${HERDR_BIN}" "$@"' in text
    assert "herdr_cli server &" in text
    assert 'herdr_cli workspace create --cwd "${WORKSPACE_CWD}" --label "${WORKSPACE_LABEL}"' in text
    assert "json_get_root_pane_id" in text
    assert 'herdr_cli pane run "${ROOT_PANE_ID}" "$(quote_cmd "${harness_cmd[@]}")"' in text
    assert "-u HERDR_SOCKET_PATH" in text
    assert "-u HERDR_SOCKET" in text
    assert "exec ${HARNESS_BIN}" not in text
    assert "raw harness" not in text.lower()


def test_dockerfile_bakes_herdr_entrypoint_and_uses_tini() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")

    assert "bash" in text
    assert "procps" in text
    assert "python3" in text
    assert "tini" in text
    assert "COPY herdr /usr/local/bin/herdr" in text
    assert (
        'install -d -m 0700 -o "${CE_DGX_UID}" -g "${CE_DGX_GID}" /run/creator-engine/herdr'
        in text
    )
    assert (
        "COPY herdr-harness-entrypoint.sh /usr/local/bin/ce-herdr-harness-entrypoint"
        in text
    )
    assert "test -x /usr/local/bin/herdr" in text
    assert (
        'ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/ce-herdr-harness-entrypoint"]'
        in text
    )
