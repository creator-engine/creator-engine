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

from . import containment_probe


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
    containment_attestation: dict[str, Any]
    runtime_probe: dict[str, Any] | None
    surface: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_key": self.backend_key,
            "handle_ref": self.handle_ref,
            "policy_sha": self.policy_sha,
            "started_ref": self.started_ref,
            "exit_code": self.exit_code,
            "argv": list(self.argv),
            "containment_attestation": dict(self.containment_attestation),
            "runtime_probe": dict(self.runtime_probe) if self.runtime_probe is not None else None,
        }


class _SurfaceBoundContainerRunner:
    """ContainerRunner adapter that starts Docker/runsc inside a visible surface."""

    def __init__(
        self,
        *,
        delegate: Any,
        visibility_backend: Any,
        run_id: str,
        session: str,
        window: str,
        cwd: str | None,
        env: Mapping[str, str] | None,
        seat_dir: str | None,
    ) -> None:
        self._delegate = delegate
        self._visibility_backend = visibility_backend
        self._run_id = run_id
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
        completed = subprocess.CompletedProcess(list(self.argv), 0, stdout="", stderr="")
        runtime_probe = _runner_runtime_probe(
            self._delegate,
            run_id=self._run_id,
            argv=self.argv,
            surface=self.surface,
        )
        if runtime_probe is not None:
            setattr(completed, "runtime_probe", runtime_probe)
        return completed


def _runner_runtime_probe(
    delegate: Any,
    *,
    run_id: str,
    argv: Sequence[str],
    surface: Any,
) -> dict[str, Any] | None:
    probe = getattr(delegate, "runtime_probe", None)
    if not callable(probe):
        return None
    payload = probe(run_id=run_id, argv=tuple(argv), surface=surface)
    return dict(payload) if isinstance(payload, Mapping) else None


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
    containment_proc_root: str | os.PathLike[str] = "/proc",
    containment_host_pid: int | str = 1,
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
        run_id=run_id,
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
    containment_attestation = _probe_launched_surface_containment(
        surface_runner.surface,
        runtime_probe=result.runtime_probe,
        expected_run_id=run_id,
        proc_root=containment_proc_root,
        host_pid=containment_host_pid,
    )
    return VisibleRunnerExecution(
        backend_key=handle.backend_key,
        handle_ref=handle.ref,
        policy_sha=handle.policy_sha,
        started_ref=result.started_ref,
        exit_code=result.exit_code,
        argv=surface_runner.argv,
        containment_attestation=containment_attestation,
        runtime_probe=dict(result.runtime_probe) if result.runtime_probe is not None else None,
        surface=surface_runner.surface,
    )


def _probe_launched_surface_containment(
    surface: Any,
    *,
    runtime_probe: Mapping[str, Any] | None,
    expected_run_id: str,
    proc_root: str | os.PathLike[str],
    host_pid: int | str,
) -> dict[str, Any]:
    if runtime_probe is None:
        raise RuntimeBackendBridgeError(
            "contained runtime launch returned no launch-owned runtime probe "
            "pid; refusing unproven containment"
        )
    probe_run_id = runtime_probe.get("run_id")
    if probe_run_id != expected_run_id:
        raise RuntimeBackendBridgeError(
            "contained runtime launch returned a runtime probe pid not bound "
            f"to run_id {expected_run_id!r}; refusing unproven containment"
        )
    pid = runtime_probe.get("pid")
    pid_text = str(pid).strip() if pid is not None else ""
    if not pid_text.isdigit() or int(pid_text) <= 0:
        raise RuntimeBackendBridgeError(
            "contained runtime launch returned no launch-owned runtime probe "
            "pid; refusing unproven containment"
        )
    verdict = containment_probe.probe_containment(
        pid_text,
        reader=containment_probe.ProcReader(root=str(proc_root)),
        host_pid=host_pid,
    )
    payload = verdict.payload
    payload["pid"] = pid_text
    payload["run_id"] = expected_run_id
    payload["proc_root"] = str(proc_root)
    if not verdict.contained:
        raise RuntimeBackendBridgeError(
            "contained runtime launch failed containment probe for pid "
            f"{pid_text}: {verdict.reason}"
        )
    return payload
