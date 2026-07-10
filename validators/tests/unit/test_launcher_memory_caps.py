"""Memory cap and preflight wrapper tests for contained-seat launchers."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parents[3]
DGX_SCRIPT = REPO_ROOT / "deploy" / "dgx-runsc" / "run-codex-runsc.sh"
VPS_SCRIPT = REPO_ROOT / "deploy" / "vps-runsc" / "run-vps-runsc.sh"
PREFLIGHT_CAPS = REPO_ROOT / "tools" / "preflight-caps.sh"


def _run_dgx(**env_overrides: str | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("CE_LEDGER_ROOT", None)
    env.pop("CE_REVIEWER_AUTHORITY_REF", None)
    with tempfile.TemporaryDirectory(prefix="ce-dgx-memory-cap-test-") as runtime_dir:
        env.update(
            {
                "CE_DGX_DRY_RUN": "1",
                "CE_DGX_IMAGE": "creator-engine/codex-runsc:test",
                "CE_DGX_REPO": "/repo/creator-engine",
                "CE_DGX_CODEX_HOME": "/home/cedev4/.codex",
                "CE_DGX_CODEX_BIN": "/opt/codex/bin/codex",
                "CE_DGX_SEAT_LOG_DIR": f"{runtime_dir}/seat-logs",
                "CE_DGX_UID": "1000",
                "CE_DGX_GID": "1000",
            }
        )
        for key, value in env_overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            ["bash", str(DGX_SCRIPT), "--dry-run", "tui"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )


def _run_vps(**env_overrides: str | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("CE_LEDGER_ROOT", None)
    env.pop("CE_REVIEWER_AUTHORITY_REF", None)
    with tempfile.TemporaryDirectory(prefix="ce-vps-memory-cap-test-") as runtime_dir:
        env.update(
            {
                "CE_VPS_DRY_RUN": "1",
                "CE_VPS_REPO": "/repo/creator-engine",
                "CE_VPS_CODEX_HOME": "/home/seat/.codex",
                "CE_VPS_CODEX_BIN": "/opt/codex/bin/codex",
                "CE_VPS_CLAUDE_BIN": "/opt/claude/bin/claude",
                "CE_VPS_CONTAINER_USER": "seat",
                "CE_VPS_SEAT_LOG_DIR": f"{runtime_dir}/seat-logs",
                "CE_VPS_UID": "1234",
                "CE_VPS_GID": "5678",
                "XDG_RUNTIME_DIR": runtime_dir,
                "TERM": "xterm-256color",
            }
        )
        for key, value in env_overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            ["bash", str(VPS_SCRIPT), "--dry-run", "tui"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )


def _argv(result: subprocess.CompletedProcess[str]) -> list[str]:
    assert result.returncode == 0, result.stderr
    return shlex.split(result.stdout)


def test_dgx_memory_limit_default_in_argv(tmp_path: Path) -> None:
    argv = _argv(_run_dgx(HOME=str(tmp_path), CE_DGX_MEMORY_LIMIT=None))

    assert "--memory" in argv
    assert argv[argv.index("--memory") + 1] == "8g"


def test_dgx_memory_limit_custom_in_argv(tmp_path: Path) -> None:
    argv = _argv(_run_dgx(HOME=str(tmp_path), CE_DGX_MEMORY_LIMIT="16g"))

    assert "--memory" in argv
    assert argv[argv.index("--memory") + 1] == "16g"


def test_dgx_memory_limit_disabled_when_empty(tmp_path: Path) -> None:
    argv = _argv(_run_dgx(HOME=str(tmp_path), CE_DGX_MEMORY_LIMIT=""))

    assert "--memory" not in argv


def test_vps_memory_limit_default_in_argv(tmp_path: Path) -> None:
    argv = _argv(_run_vps(HOME=str(tmp_path), CE_VPS_MEMORY_LIMIT=None))

    assert "--memory" in argv
    assert argv[argv.index("--memory") + 1] == "8g"


def test_vps_memory_limit_custom_in_argv(tmp_path: Path) -> None:
    argv = _argv(_run_vps(HOME=str(tmp_path), CE_VPS_MEMORY_LIMIT="12g"))

    assert "--memory" in argv
    assert argv[argv.index("--memory") + 1] == "12g"


def test_vps_memory_limit_disabled_when_empty(tmp_path: Path) -> None:
    argv = _argv(_run_vps(HOME=str(tmp_path), CE_VPS_MEMORY_LIMIT=""))

    assert "--memory" not in argv


def test_preflight_caps_script_exists_and_executable() -> None:
    assert PREFLIGHT_CAPS.is_file()
    assert os.access(PREFLIGHT_CAPS, os.X_OK)


def test_preflight_caps_env_defaults_to_home_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CE_PREFLIGHT_TMPDIR", raising=False)
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)

    result = subprocess.run(
        ["bash", str(PREFLIGHT_CAPS), "bash", "-c", 'printf "TMPDIR=%s\\n" "$TMPDIR"'],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert f"TMPDIR={tmp_path / 'tmp'}" in result.stdout


def test_preflight_caps_rewrites_n_auto_and_forwards_args(tmp_path: Path) -> None:
    preflight_tmp = tmp_path / "preflight-tmp"
    env = os.environ.copy()
    env["CE_PREFLIGHT_TMPDIR"] = str(preflight_tmp)
    env["CE_PREFLIGHT_MAX_WORKERS"] = "2"

    result = subprocess.run(
        [
            "bash",
            str(PREFLIGHT_CAPS),
            "bash",
            "-c",
            'printf "%s\\n" "$@"',
            "argv0",
            "-n",
            "auto",
            "--dist",
            "loadgroup",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["-n", "2", "--dist", "loadgroup"]
    assert "[preflight-caps] Capped -n auto to -n 2" in result.stderr


def test_preflight_caps_cleans_pytest_tmpdirs_after_run(tmp_path: Path) -> None:
    preflight_tmp = tmp_path / "preflight-tmp"
    stale_pytest_tmp = preflight_tmp / "pytest-of-stale"
    keep_dir = preflight_tmp / "not-pytest-of-stale"
    stale_pytest_tmp.mkdir(parents=True)
    keep_dir.mkdir(parents=True)
    (stale_pytest_tmp / "sentinel.txt").write_text("remove me", encoding="utf-8")
    (keep_dir / "sentinel.txt").write_text("keep me", encoding="utf-8")

    env = os.environ.copy()
    env["CE_PREFLIGHT_TMPDIR"] = str(preflight_tmp)

    result = subprocess.run(
        [
            "bash",
            str(PREFLIGHT_CAPS),
            "bash",
            "-c",
            'mkdir -p "$TMPDIR/pytest-of-child"; printf "done\\n"',
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "done\n"
    assert not stale_pytest_tmp.exists()
    assert not (preflight_tmp / "pytest-of-child").exists()
    assert keep_dir.is_dir()
    assert (keep_dir / "sentinel.txt").read_text(encoding="utf-8") == "keep me"
