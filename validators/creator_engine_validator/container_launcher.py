"""Shared container-engine launcher primitives.

This module is the single place that constructs ``podman run`` argv and starts
``podman run`` processes for Creator Engine container substrates. The caller
supplies policy-shaped inputs; this module pins the image by digest and keeps
the command-runner seam injectable for offline tests.
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass
from typing import Any, Literal, Protocol, Sequence


PODMAN_TIMEOUT_PROBE_SECONDS = 5
PODMAN_TIMEOUT_CLEANUP_SECONDS = 10
PODMAN_TIMEOUT_RETURNCODE = 124


class CommandRunner(Protocol):
    """Minimal subprocess seam used by the shared launcher."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run argv and return a ``subprocess.CompletedProcess``-compatible object."""


@dataclass(frozen=True)
class ContainerRunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    container_id: str | None = None
    timed_out: bool = False
    container_name: str | None = None
    cleanup_attempted: bool = False
    cleanup_returncode: int | None = None
    cleanup_stdout: str = ""
    cleanup_stderr: str = ""
    cleanup_error: str | None = None


class SubprocessCommandRunner:
    """Default command runner for live rootless Podman invocations."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:  # pragma: no cover - live CLI seam
        return subprocess.run(  # noqa: S603 - argv is fully assembled by this launcher.
            list(argv),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )


def podman_available(binary: str = "podman") -> bool:
    return shutil.which(binary) is not None


def _coerce_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _secret_argv(secret_grants: Sequence[Any]) -> list[str]:
    argv: list[str] = []
    for grant in secret_grants:
        mode = getattr(grant, "mode")
        name = getattr(grant, "secret_name")
        if mode == "file":
            argv += ["--secret", f"{name},type=mount,target=/run/secrets/{name}"]
        else:
            argv += ["--secret", f"{name},type=env,target={name}"]
    return argv


def _mount_argv(mounts: Sequence[dict[str, Any]]) -> list[str]:
    argv: list[str] = []
    for entry in mounts:
        path = entry["path"]
        mode = entry["mode"]
        argv += ["-v", f"{path}:{path}:{mode}"]
    return argv


def _env_argv(env: Sequence[tuple[str, str]] | dict[str, str]) -> list[str]:
    items = env.items() if isinstance(env, dict) else env
    argv: list[str] = []
    for key, value in items:
        argv += ["--env", f"{key}={value}"]
    return argv


def _tmpfs_argv(tmpfs: Sequence[str]) -> list[str]:
    argv: list[str] = []
    for mount in tmpfs:
        argv += ["--tmpfs", mount]
    return argv


def _new_foreground_instance_id() -> str:
    return f"ce-foreground-{uuid.uuid4().hex[:12]}"


def build_podman_run_argv(
    *,
    image_name: str,
    image_sha: str,
    mode: Literal["detached", "foreground"],
    network_mode: str,
    mounts: Sequence[dict[str, Any]] = (),
    secret_grants: Sequence[Any] = (),
    instance_id: str | None = None,
    command: Sequence[str] = (),
    workdir: str | None = None,
    env: Sequence[tuple[str, str]] | dict[str, str] = (),
    tmpfs: Sequence[str] = (),
    engine_timeout_seconds: int | None = None,
    binary: str = "podman",
) -> list[str]:
    """Construct a deterministic rootless ``podman run`` argv."""
    if not instance_id:
        raise ValueError(f"{mode} podman run requires instance_id")
    if mode == "foreground" and not command:
        raise ValueError("foreground podman run requires a trailing command")

    argv: list[str] = [binary, "run"]
    if mode == "detached":
        argv += ["--detach", "--name", str(instance_id)]
    else:
        argv += ["--rm", "--name", str(instance_id)]

    argv += [
        "--userns=keep-id",
        "--security-opt", "no-new-privileges",
        "--network", network_mode,
    ]
    if engine_timeout_seconds is not None:
        argv += ["--timeout", str(engine_timeout_seconds)]
    if workdir:
        argv += ["--workdir", workdir]
    argv += _env_argv(env)
    argv += _mount_argv(mounts)
    argv += _tmpfs_argv(tmpfs)
    argv += _secret_argv(secret_grants)
    argv.append(f"{image_name}@{image_sha}")
    if mode == "foreground":
        argv += list(command)
    return argv


def podman_run_supports_timeout(
    *,
    runner: CommandRunner,
    binary: str = "podman",
) -> bool:
    """Probe whether the installed Podman supports ``podman run --timeout``."""
    support_probe = getattr(runner, "podman_run_supports_timeout", None)
    if callable(support_probe):
        return bool(support_probe(binary))
    try:
        completed = runner.run(
            [binary, "run", "--help"],
            timeout=PODMAN_TIMEOUT_PROBE_SECONDS,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    output = f"{completed.stdout or ''}\n{completed.stderr or ''}"
    return completed.returncode == 0 and "--timeout" in output


def run_detached_podman(
    argv: Sequence[str],
    *,
    runner: CommandRunner | None = None,
) -> ContainerRunResult:
    """Run an already-built detached ``podman run`` argv."""
    command_runner = runner or SubprocessCommandRunner()
    completed = command_runner.run(argv, timeout=None)
    stdout = completed.stdout or ""
    container_id = stdout.strip().splitlines()[-1] if stdout.strip() else None
    return ContainerRunResult(
        completed.returncode,
        stdout,
        completed.stderr or "",
        container_id,
    )


def _cleanup_timed_out_container(
    *,
    runner: CommandRunner,
    binary: str,
    container_name: str,
) -> tuple[int | None, str, str, str | None]:
    try:
        completed = runner.run(
            [binary, "rm", "-f", container_name],
            timeout=PODMAN_TIMEOUT_CLEANUP_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return (
            None,
            _coerce_timeout_output(exc.stdout),
            _coerce_timeout_output(exc.stderr),
            f"podman rm -f timed out after {PODMAN_TIMEOUT_CLEANUP_SECONDS}s",
        )
    except (FileNotFoundError, OSError) as exc:
        return None, "", "", str(exc)
    return (
        completed.returncode,
        completed.stdout or "",
        completed.stderr or "",
        None,
    )


def run_foreground_podman(
    *,
    image_name: str,
    image_sha: str,
    command: Sequence[str],
    timeout_seconds: int,
    network_mode: str = "none",
    mounts: Sequence[dict[str, Any]] = (),
    workdir: str | None = None,
    env: Sequence[tuple[str, str]] | dict[str, str] = (),
    tmpfs: Sequence[str] = (),
    secret_grants: Sequence[Any] = (),
    instance_id: str | None = None,
    runner: CommandRunner | None = None,
    binary: str = "podman",
) -> ContainerRunResult:
    """Run a foreground ephemeral ``podman run --rm`` command with capture.

    The host-side timeout is mandatory. The engine-side ``--timeout`` flag is
    included only after probing support on the active Podman installation.
    """
    command_runner = runner or SubprocessCommandRunner()
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    container_name = instance_id or _new_foreground_instance_id()

    engine_timeout = (
        timeout_seconds
        if podman_run_supports_timeout(runner=command_runner, binary=binary)
        else None
    )
    argv = build_podman_run_argv(
        image_name=image_name,
        image_sha=image_sha,
        mode="foreground",
        network_mode=network_mode,
        mounts=mounts,
        secret_grants=secret_grants,
        instance_id=container_name,
        command=command,
        workdir=workdir,
        env=env,
        tmpfs=tmpfs,
        engine_timeout_seconds=engine_timeout,
        binary=binary,
    )
    try:
        completed = command_runner.run(argv, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        stderr = _coerce_timeout_output(exc.stderr)
        if stderr:
            stderr = f"{stderr}\npodman run timed out after {timeout_seconds}s"
        else:
            stderr = f"podman run timed out after {timeout_seconds}s"
        cleanup_returncode, cleanup_stdout, cleanup_stderr, cleanup_error = _cleanup_timed_out_container(
            runner=command_runner,
            binary=binary,
            container_name=container_name,
        )
        return ContainerRunResult(
            PODMAN_TIMEOUT_RETURNCODE,
            _coerce_timeout_output(exc.stdout),
            stderr,
            timed_out=True,
            container_name=container_name,
            cleanup_attempted=True,
            cleanup_returncode=cleanup_returncode,
            cleanup_stdout=cleanup_stdout,
            cleanup_stderr=cleanup_stderr,
            cleanup_error=cleanup_error,
        )
    return ContainerRunResult(
        completed.returncode,
        completed.stdout or "",
        completed.stderr or "",
        container_name=container_name,
    )
