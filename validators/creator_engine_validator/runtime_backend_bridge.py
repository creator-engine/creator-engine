"""Visible runtime-backend bridge for ``ce launch`` and ``ce lane launch``.

This v1 launcher bridge composes the v3 runner backend as a runtime surface
without importing it statically across the version boundary. The gVisor backend
renders the Docker/runsc command through ``RunnerBackend.provision -> run``; the
container runner it receives starts that command on the selected visibility
backend instead of spawning a hidden subprocess.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


class RuntimeBackendBridgeError(Exception):
    """The requested runtime backend cannot be honored by the visible launcher."""


@dataclass(frozen=True)
class VisibleRunnerExecution:
    """Result of one runner-backed visible launch."""

    backend_key: str
    handle_ref: str
    policy_sha: str
    started_ref: str
    exit_code: int
    argv: tuple[str, ...]
    surface: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_key": self.backend_key,
            "handle_ref": self.handle_ref,
            "policy_sha": self.policy_sha,
            "started_ref": self.started_ref,
            "exit_code": self.exit_code,
            "argv": list(self.argv),
        }


class _SurfaceBoundContainerRunner:
    """ContainerRunner adapter that starts Docker/runsc inside a visible surface."""

    def __init__(
        self,
        *,
        delegate: Any,
        visibility_backend: Any,
        session: str,
        window: str,
        cwd: str | None,
        env: Mapping[str, str] | None,
        seat_dir: str | None,
    ) -> None:
        self._delegate = delegate
        self._visibility_backend = visibility_backend
        self._session = session
        self._window = window
        self._cwd = cwd
        self._env = dict(env) if env is not None else None
        self._seat_dir = seat_dir
        self.surface: Any | None = None
        self.argv: tuple[str, ...] = ()

    def available(self) -> bool:
        return bool(self._delegate.available()) and bool(self._visibility_backend.is_available())

    def egress_enforceable(self) -> bool:
        return bool(self._delegate.egress_enforceable())

    def run(
        self, argv: Sequence[str], input_text: str | None = None
    ) -> subprocess.CompletedProcess:
        if input_text is not None:
            raise RuntimeBackendBridgeError(
                "visible runtime launch does not accept stdin payloads"
            )
        self.argv = tuple(str(part) for part in argv)
        self.surface = self._visibility_backend.ensure_surface(
            session=self._session,
            window=self._window,
            command=self.argv,
            cwd=self._cwd,
            env=self._env,
            seat_dir=self._seat_dir,
        )
        return subprocess.CompletedProcess(list(self.argv), 0, stdout="", stderr="")


def _runner_package() -> Any:
    return importlib.import_module("creator_engine_validator.runner")


def _default_gvisor_plan_kwargs() -> dict[str, Any]:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        raise RuntimeBackendBridgeError(
            "gvisor-proxy launch requires a codex binary on PATH so the DGX "
            "Docker/runsc plan can mount the governed harness"
        )
    return {
        "uid": os.getuid(),
        "gid": os.getgid(),
        "host_codex_home": str(Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))),
        "host_codex_bin": codex_bin,
    }


def run_visible_runtime(
    *,
    resolved_backend: str,
    runtime_policy: dict[str, Any],
    run_id: str,
    command: Sequence[str],
    visibility_backend: Any,
    session: str,
    window: str,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    seat_dir: str | None = None,
    container_runner: Any | None = None,
    gvisor_plan_kwargs: Mapping[str, Any] | None = None,
) -> VisibleRunnerExecution:
    """Provision and run ``command`` through a visible runtime backend.

    Only the gVisor Docker/runsc backend is currently honorably composable with a
    v1 visibility surface. Other registered backends fail closed here rather than
    silently falling back to raw tmux.
    """

    runner_pkg = _runner_package()
    if resolved_backend != runner_pkg.GVISOR_PROXY_BACKEND_KEY:
        raise RuntimeBackendBridgeError(
            f"runtime backend {resolved_backend!r} cannot yet be composed with "
            "the v1 visibility surface; refusing raw fallback"
        )

    plan_kwargs = dict(gvisor_plan_kwargs or {})
    if not {"uid", "gid", "host_codex_home", "host_codex_bin"}.issubset(plan_kwargs):
        defaults = _default_gvisor_plan_kwargs()
        defaults.update(plan_kwargs)
        plan_kwargs = defaults

    delegate = container_runner if container_runner is not None else runner_pkg.SubprocessContainerRunner()
    surface_runner = _SurfaceBoundContainerRunner(
        delegate=delegate,
        visibility_backend=visibility_backend,
        session=session,
        window=window,
        cwd=cwd,
        env=env,
        seat_dir=seat_dir,
    )
    backend = runner_pkg.GvisorProxyBackend(runner=surface_runner, **plan_kwargs)
    try:
        handle = backend.provision(
            runner_pkg.ProvisionRequest(runtime_policy=runtime_policy, run_id=run_id)
        )
        result = backend.run(handle, runner_pkg.RunRequest(command=tuple(command)))
    except runner_pkg.RunnerError as exc:
        raise RuntimeBackendBridgeError(str(exc)) from exc
    if surface_runner.surface is None:
        raise RuntimeBackendBridgeError(
            f"runtime backend {resolved_backend!r} returned without a visible surface"
        )
    return VisibleRunnerExecution(
        backend_key=handle.backend_key,
        handle_ref=handle.ref,
        policy_sha=handle.policy_sha,
        started_ref=result.started_ref,
        exit_code=result.exit_code,
        argv=surface_runner.argv,
        surface=surface_runner.surface,
    )
