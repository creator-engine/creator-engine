"""Unit tests for the shared container launcher."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Sequence

import pytest

from creator_engine_validator import container_launcher
from creator_engine_validator.worker_runtime import BrokerGrant


IMAGE = "ghcr.io/example/verification:latest"
IMAGE_SHA = "sha256:" + "a" * 64


@dataclass
class FakeRunner:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    timeout_support: bool = False
    timeout_exc: subprocess.TimeoutExpired | None = None
    calls: list[tuple[list[str], float | None]] = field(default_factory=list)

    def podman_run_supports_timeout(self, binary: str) -> bool:
        self.calls.append(([binary, "run", "--help"], container_launcher.PODMAN_TIMEOUT_PROBE_SECONDS))
        return self.timeout_support

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(argv), timeout))
        if self.timeout_exc is not None and list(argv)[1:2] == ["run"]:
            raise self.timeout_exc
        return subprocess.CompletedProcess(
            list(argv),
            self.returncode,
            self.stdout,
            self.stderr,
        )


def test_build_detached_podman_run_argv_matches_worker_runtime_contract() -> None:
    grants = [
        BrokerGrant("grant-env", "MODEL_KEY", "env", "2026-07-04T00:00:00Z", 60),
        BrokerGrant("grant-file", "CONFIG_FILE", "file", "2026-07-04T00:00:00Z", 60),
    ]

    argv = container_launcher.build_podman_run_argv(
        image_name=IMAGE,
        image_sha=IMAGE_SHA,
        mode="detached",
        instance_id="inst-001",
        mounts=[{"path": "/worktree", "mode": "ro"}],
        secret_grants=grants,
        network_mode="none",
    )

    assert argv == [
        "podman", "run", "--detach",
        "--name", "inst-001",
        "--userns=keep-id",
        "--security-opt", "no-new-privileges",
        "--network", "none",
        "-v", "/worktree:/worktree:ro",
        "--secret", "MODEL_KEY,type=env,target=MODEL_KEY",
        "--secret", "CONFIG_FILE,type=mount,target=/run/secrets/CONFIG_FILE",
        f"{IMAGE}@{IMAGE_SHA}",
    ]


def test_build_foreground_podman_run_argv_covers_ephemeral_policy_shape() -> None:
    argv = container_launcher.build_podman_run_argv(
        image_name=IMAGE,
        image_sha=IMAGE_SHA,
        mode="foreground",
        network_mode="none",
        mounts=[{"path": "/repo", "mode": "ro"}],
        workdir="/repo",
        env=[("A", "1"), ("B", "two")],
        tmpfs=["/tmp:rw,size=64m"],
        engine_timeout_seconds=30,
        instance_id="fg-001",
        command=["python", "-m", "pytest"],
    )

    assert argv == [
        "podman", "run", "--rm",
        "--name", "fg-001",
        "--userns=keep-id",
        "--security-opt", "no-new-privileges",
        "--network", "none",
        "--timeout", "30",
        "--workdir", "/repo",
        "--env", "A=1",
        "--env", "B=two",
        "-v", "/repo:/repo:ro",
        "--tmpfs", "/tmp:rw,size=64m",
        f"{IMAGE}@{IMAGE_SHA}",
        "python", "-m", "pytest",
    ]
    assert "--detach" not in argv
    assert argv[argv.index("--name") + 1] == "fg-001"


def test_run_foreground_captures_stdout_stderr_returncode_and_host_timeout() -> None:
    runner = FakeRunner(returncode=7, stdout="out\n", stderr="err\n", timeout_support=False)

    result = container_launcher.run_foreground_podman(
        image_name=IMAGE,
        image_sha=IMAGE_SHA,
        command=["sh", "-c", "exit 7"],
        timeout_seconds=12,
        mounts=[{"path": "/repo", "mode": "ro"}],
        workdir="/repo",
        runner=runner,
    )

    assert result.returncode == 7
    assert result.stdout == "out\n"
    assert result.stderr == "err\n"
    assert result.timed_out is False
    assert result.container_name is not None
    run_call = runner.calls[-1]
    assert run_call[1] == 12
    assert "--rm" in run_call[0]
    assert "--name" in run_call[0]
    assert run_call[0][run_call[0].index("--name") + 1] == result.container_name
    assert "--timeout" not in run_call[0]


def test_run_foreground_adds_engine_timeout_only_after_probe_support() -> None:
    runner = FakeRunner(returncode=0, stdout="ok\n", timeout_support=True)

    result = container_launcher.run_foreground_podman(
        image_name=IMAGE,
        image_sha=IMAGE_SHA,
        command=["true"],
        timeout_seconds=9,
        runner=runner,
    )

    assert result.returncode == 0
    assert runner.calls[0] == (["podman", "run", "--help"], 5)
    argv, host_timeout = runner.calls[-1]
    assert host_timeout == 9
    assert "--timeout" in argv
    assert argv[argv.index("--timeout") + 1] == "9"


def test_run_foreground_handles_host_timeout_expired() -> None:
    runner = FakeRunner(
        timeout_support=False,
        timeout_exc=subprocess.TimeoutExpired(
            cmd=["podman", "run"],
            timeout=4,
            output="partial\n",
            stderr="busy\n",
        ),
    )

    result = container_launcher.run_foreground_podman(
        image_name=IMAGE,
        image_sha=IMAGE_SHA,
        command=["sleep", "99"],
        timeout_seconds=4,
        instance_id="fg-timeout",
        runner=runner,
    )

    assert result.returncode == container_launcher.PODMAN_TIMEOUT_RETURNCODE
    assert result.stdout == "partial\n"
    assert "busy" in result.stderr
    assert "timed out after 4s" in result.stderr
    assert result.timed_out is True
    assert result.container_name == "fg-timeout"
    assert result.cleanup_attempted is True
    assert result.cleanup_returncode == 0
    assert result.cleanup_error is None
    assert runner.calls[-1] == (
        ["podman", "rm", "-f", "fg-timeout"],
        container_launcher.PODMAN_TIMEOUT_CLEANUP_SECONDS,
    )


def test_foreground_run_requires_positive_host_timeout() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        container_launcher.run_foreground_podman(
            image_name=IMAGE,
            image_sha=IMAGE_SHA,
            command=["true"],
            timeout_seconds=0,
            runner=FakeRunner(),
        )
