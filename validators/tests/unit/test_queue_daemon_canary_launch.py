"""Canary-mode tests for the queue daemon launcher."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"
LIVE_ROOT = "/var/lib/ce-queue-daemon/v3"


def write_executable(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


def run_launcher(tmp_path: Path, env_overrides: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    fake_daemon = write_executable(tmp_path / "fake-queue-daemon", "#!/bin/sh\nexit 0\n")
    fake_lease_python = write_executable(
        tmp_path / "fake-lease-python",
        "#!/bin/sh\n"
        "shift\n"
        "printf '%s\\n' \"$*\"\n"
        "exit 0\n",
    )
    env = {
        "PATH": os.environ.get("PATH", ""),
        "CE_DAEMON_UNCONTAINED": "1",
        "CE_DAEMON_LEASE_PYTHON": str(fake_lease_python),
        "CE_DAEMON_LEASE_ROOT": str(tmp_path / "leases"),
        "CE_QUEUE_DAEMON_BIN": str(fake_daemon),
        "PYTHONPATH": str(REPO_ROOT / "validators"),
    }
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


def canary_env(tmp_path: Path) -> dict[str, str | None]:
    return {
        "GH_TOKEN": "gh-read-only-token",
        "CE_GATE_REPO": "creator-engine/creator-engine",
        "CE_GATE_AUTHORIZED_REVIEWERS": "authorized-reviewer",
        "CE_QUEUE_DAEMON_CANARY": "1",
        "CE_DAEMON_STATE_ROOT": str(tmp_path / "canary-state"),
    }


def test_canary_mode_requires_no_bao_vars(tmp_path: Path) -> None:
    result = run_launcher(tmp_path, canary_env(tmp_path))

    assert result.returncode == 0, result.stderr
    assert "missing required environment variable: BAO_TOKEN" not in result.stderr
    argv = shlex.split(result.stdout)
    assert "--dry-run" in argv
    assert "--approval-wall-secret-backend" not in argv
    assert "--root" in argv
    assert argv[argv.index("--root") + 1] == str(tmp_path / "canary-state")


def test_canary_mode_emits_banner(tmp_path: Path) -> None:
    result = run_launcher(tmp_path, canary_env(tmp_path))

    assert result.returncode == 0, result.stderr
    assert "CANARY MODE — dry_run=true" in result.stderr


def test_canary_mode_refuses_shared_state_root(tmp_path: Path) -> None:
    env = canary_env(tmp_path)
    env["CE_DAEMON_STATE_ROOT"] = LIVE_ROOT

    result = run_launcher(tmp_path, env)

    assert result.returncode != 0
    assert "state root collision" in result.stderr
    assert LIVE_ROOT in result.stderr


def test_non_canary_mode_still_requires_bao(tmp_path: Path) -> None:
    result = run_launcher(
        tmp_path,
        {
            "GH_TOKEN": "gh-live-token",
            "CE_GATE_REPO": "creator-engine/creator-engine",
            "CE_GATE_AUTHORIZED_REVIEWERS": "authorized-reviewer",
        },
    )

    assert result.returncode != 0
    assert "missing required environment variable: BAO_TOKEN" in result.stderr
