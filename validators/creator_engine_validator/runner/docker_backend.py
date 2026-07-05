"""Plain Docker runner backend for tenant contained launch.

This backend mirrors the gVisor runner's translate-vs-execute split while
targeting the default Docker runtime. It deliberately does not add a
``--runtime=`` flag and never bind-mounts a host Codex binary or host Codex
home; the image reference comes only from the runtime-policy record.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .backend import (
    BackendUnavailable,
    CollectedEvidence,
    ProvisionRequest,
    ProvisionedHandle,
    RunnerBackend,
    RunRequest,
    RunResult,
    TeardownResult,
    register_backend,
)
from .gvisor_proxy_backend import (
    DOCKER_BINARY,
    EgressNotEnforceable,
    SubprocessContainerRunner as _GvisorSubprocessContainerRunner,
    translate_to_egress_proxy_config,
)
from .translation import (
    MountSpec as DockerMountSpec,
    bind_launch_owned_probe_contract,
    first_writable_mount_target,
    mount_from_policy_entry,
    optional_uid_gid,
    render_mount,
    require_abs_path,
    require_image_digest,
    require_nonempty_str,
    require_uid_gid,
)

BACKEND_KEY = "docker"
DEFAULT_CONTAINER_HOME = "/tmp/ce-home"
DEFAULT_CONTAINER_CODEX_HOME = f"{DEFAULT_CONTAINER_HOME}/.codex"
DEFAULT_TMPFS_MOUNTS = ("/tmp:rw,nosuid,nodev,noexec,size=64m",)


class DockerPlanRejected(ValueError):
    """The Docker plan lacks required safe rendering inputs."""


@dataclass(frozen=True)
class DockerPlan:
    """A plain Docker container plan translated from a runtime policy."""

    docker_binary: str
    image_name: str
    image_digest: str
    mounts: tuple[DockerMountSpec, ...]
    network: str
    uid: int
    gid: int | None
    container_home: str
    container_codex_home: str
    container_workdir: str
    remove: bool
    no_new_privileges: bool
    drop_all_capabilities: bool
    read_only_rootfs: bool
    tmpfs_mounts: tuple[str, ...]
    tty_flags: tuple[str, ...] = ()

    @property
    def image_ref(self) -> str:
        return f"{self.image_name}@{self.image_digest}"

    @property
    def user_spec(self) -> str:
        return str(self.uid) if self.gid is None else f"{self.uid}:{self.gid}"

    def docker_argv(self, command: Sequence[str]) -> tuple[str, ...]:
        args: list[str] = [self.docker_binary, "run"]
        if self.remove:
            args.append("--rm")
        if self.no_new_privileges:
            args.append("--security-opt=no-new-privileges")
        if self.drop_all_capabilities:
            args.append("--cap-drop=ALL")
        args += [
            "--user",
            self.user_spec,
            "--workdir",
            self.container_workdir,
            "--env",
            f"HOME={self.container_home}",
            "--env",
            f"CODEX_HOME={self.container_codex_home}",
        ]
        if self.read_only_rootfs:
            args.append("--read-only")
        for tmpfs in self.tmpfs_mounts:
            args += ["--tmpfs", tmpfs]
        for mount in self.mounts:
            args += ["--mount", render_mount(mount)]
        if self.network == "none":
            args.append("--network=none")
        elif self.network == "proxy":
            raise DockerPlanRejected(
                "network='proxy' plans cannot be rendered into docker argv: docker-side "
                "egress mediation is not yet implemented (no flag here maps an egress "
                "allowlist to a Docker network primitive, so the container would default "
                "to the open bridge network if run). This backend's egress_enforceable() "
                "is hardcoded False, so provisioning refuses before this point today; this "
                "raise is a fail-closed backstop so a future runner that claims "
                "egress_enforceable()=True cannot silently produce an open, "
                "governed-labeled container."
            )
        else:
            raise DockerPlanRejected(f"unknown network mode {self.network!r}")
        args += list(self.tty_flags)
        args += [self.image_ref, *command]
        return tuple(args)


def translate_to_docker_plan(
    runtime_policy: dict[str, Any],
    *,
    uid: int | str | None = None,
    gid: int | str | None = None,
    container_home: str = DEFAULT_CONTAINER_HOME,
    container_codex_home: str = DEFAULT_CONTAINER_CODEX_HOME,
    container_workdir: str | None = None,
    tmpfs_mounts: Sequence[str] = DEFAULT_TMPFS_MOUNTS,
    tty_flags: Sequence[str] = (),
) -> DockerPlan:
    """Translate a runtime-policy record into a plain Docker plan (pure)."""
    image = runtime_policy.get("image_ref") or {}
    name = image.get("name", "") if isinstance(image, dict) else ""
    sha = image.get("sha", "") if isinstance(image, dict) else ""
    image_name = require_nonempty_str(name, "image_ref.name", error_type=DockerPlanRejected)
    image_digest = require_image_digest(sha, error_type=DockerPlanRejected)
    mounts = tuple(
        mount_from_policy_entry(entry, index, error_type=DockerPlanRejected)
        for index, entry in enumerate(runtime_policy.get("mount_manifest") or [])
        if isinstance(entry, dict)
    )
    if not mounts:
        raise DockerPlanRejected("mount_manifest must include at least one Docker bind mount")
    workdir = container_workdir or first_writable_mount_target(mounts)
    if workdir is None:
        raise DockerPlanRejected("container_workdir is required when no rw mount is declared")
    resolved_uid = require_uid_gid(uid, "uid", error_type=DockerPlanRejected)
    resolved_gid = optional_uid_gid(gid, "gid", error_type=DockerPlanRejected)
    container_home = require_abs_path(container_home, "container_home", error_type=DockerPlanRejected)
    container_codex_home = require_abs_path(
        container_codex_home, "container_codex_home", error_type=DockerPlanRejected
    )
    workdir = require_abs_path(workdir, "container_workdir", error_type=DockerPlanRejected)
    rendered_tmpfs = tuple(
        require_nonempty_str(mount, "tmpfs_mounts", error_type=DockerPlanRejected)
        for mount in tmpfs_mounts
    )
    rendered_tty_flags = tuple(
        require_nonempty_str(flag, "tty_flags", error_type=DockerPlanRejected)
        for flag in tty_flags
    )
    has_egress = bool(runtime_policy.get("egress_allowlist") or [])
    return DockerPlan(
        docker_binary=DOCKER_BINARY,
        image_name=image_name,
        image_digest=image_digest,
        mounts=mounts,
        network="proxy" if has_egress else "none",
        uid=resolved_uid,
        gid=resolved_gid,
        container_home=container_home,
        container_codex_home=container_codex_home,
        container_workdir=workdir,
        remove=True,
        no_new_privileges=True,
        drop_all_capabilities=True,
        read_only_rootfs=True,
        tmpfs_mounts=rendered_tmpfs,
        tty_flags=rendered_tty_flags,
    )


class SubprocessDockerRunner(_GvisorSubprocessContainerRunner):
    """Default plain-Docker runner. Availability only requires Docker itself."""

    def __init__(
        self,
        binary: str = DOCKER_BINARY,
        *,
        probe_timeout_seconds: float = 2.0,
        probe_interval_seconds: float = 0.05,
    ) -> None:
        super().__init__(
            binary=binary,
            required_runtime="",
            probe_timeout_seconds=probe_timeout_seconds,
            probe_interval_seconds=probe_interval_seconds,
        )

    def available(self) -> bool:
        return shutil.which(self._binary) is not None

    def egress_enforceable(self) -> bool:
        return False

    def run(self, argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:  # pragma: no cover - requires live Docker
        return subprocess.run(
            list(argv), input=input_text, capture_output=True, text=True, check=False
        )


class DockerBackend(RunnerBackend):
    """Plain Docker runner backend with deny-by-default egress gating."""

    backend_key = BACKEND_KEY

    def __init__(
        self,
        runner: Any | None = None,
        *,
        uid: int | str | None = None,
        gid: int | str | None = None,
        container_home: str = DEFAULT_CONTAINER_HOME,
        container_codex_home: str = DEFAULT_CONTAINER_CODEX_HOME,
        container_workdir: str | None = None,
        tmpfs_mounts: Sequence[str] = DEFAULT_TMPFS_MOUNTS,
        tty_flags: Sequence[str] = (),
    ) -> None:
        self._runner = runner if runner is not None else SubprocessDockerRunner()
        self._plans: dict[str, DockerPlan] = {}
        self._plan_kwargs = {
            "uid": uid,
            "gid": gid,
            "container_home": container_home,
            "container_codex_home": container_codex_home,
            "container_workdir": container_workdir,
            "tmpfs_mounts": tuple(tmpfs_mounts),
            "tty_flags": tuple(tty_flags),
        }

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        record = request.runtime_policy
        try:
            plan = translate_to_docker_plan(record, **self._plan_kwargs)
        except DockerPlanRejected as exc:
            raise BackendUnavailable(f"invalid Docker plan: {exc}") from exc
        egress = translate_to_egress_proxy_config(record)
        if not egress.no_egress and not self._runner.egress_enforceable():
            raise EgressNotEnforceable(
                "policy declares a non-empty egress allowlist but no allowlist enforcement "
                "primitive is proven; refusing before container start (broad egress is never "
                "silently labelled governed)"
            )
        if not self._runner.available():
            raise BackendUnavailable(
                f"the {DOCKER_BINARY!r} client is not available; refusing to provision"
            )
        policy_sha = record.get("policy_sha", "")
        handle = ProvisionedHandle(
            backend_key=self.backend_key,
            run_id=request.run_id,
            policy_sha=policy_sha if isinstance(policy_sha, str) else "",
            ref=f"docker:{request.run_id}",
        )
        self._plans[handle.ref] = plan
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        plan = self._plans.get(handle.ref)
        if plan is None:
            raise BackendUnavailable(
                f"no provisioned Docker plan for handle {handle.ref!r}; refusing unproven handle"
            )
        argv = bind_launch_owned_probe_contract(
            plan.docker_argv(request.command),
            run_id=handle.run_id,
        )
        completed = self._runner.run(argv)
        runtime_probe = getattr(completed, "runtime_probe", None)
        return RunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            started_ref=handle.ref,
            runtime_probe=dict(runtime_probe) if isinstance(runtime_probe, dict) else None,
        )

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        return CollectedEvidence(
            handle_ref=handle.ref,
            records=(),
            note=f"docker backend evidence for {handle.ref}",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        self._plans.pop(handle.ref, None)
        return TeardownResult(handle_ref=handle.ref, released=True)


register_backend(BACKEND_KEY, DockerBackend)
