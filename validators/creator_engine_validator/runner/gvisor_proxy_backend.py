"""CE v3 plane-C backend: hardened gVisor runner with honest egress gating (G-1.2).

The first runner backend that translates a runtime-policy record (the G-1.0
contract) into the hardened DGX Docker ``runsc`` shape plus a deny-by-default
egress allowlist config object, registered under the ``gvisor-proxy`` key behind
the G-1.1 ``RunnerBackend`` adapter.

This keeps the in-repo egress posture honest: like the v2 ``worker_runtime``
path, a non-empty egress allowlist is *refused* unless a real allowlist
enforcement primitive is proven present. DGX ``runsc``/``gvproxy`` metadata
proves containment/routing only; it is not by itself allowlist enforcement.

LOAD-BEARING translate-vs-execute split (CI has no Docker/runsc runtime):

* ``translate_to_runsc_plan`` and ``translate_to_egress_proxy_config`` are
  **pure** functions with NO side effects — fully unit-tested.
* All live work goes through an injectable ``ContainerRunner`` seam (mirror the
  forge ``GhRunner``): callers inject a fake; tests perform ZERO live subprocess
  and importing this module performs no I/O.
* Live provisioning is **gated behind an availability probe**
  (``ContainerRunner.available``) and refuses before any side effect when the
  Docker/runsc runtime or an allowlist enforcement primitive is absent — broad
  egress is never silently run.

Defensive only — hardens our own agent runtime; never an offensive capability.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

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
from .translation import (
    LAUNCH_PROBE_CONTRACT,
    LAUNCH_PROBE_CONTRACT_LABEL,
    LAUNCH_PROBE_RUN_ID_LABEL,
    MountSpec,
    argv_carries_launch_probe_contract,
    bind_launch_owned_probe_contract,
    first_writable_mount_target,
    launch_probe_container_name,
    mount_from_policy_entry,
    optional_uid_gid,
    render_mount,
    require_abs_path,
    require_image_digest,
    require_mode,
    require_nonempty_str,
    require_uid_gid,
)

BACKEND_KEY = "gvisor-proxy"
#: The container client used to reach Docker's registered runsc runtime.
DOCKER_BINARY = "docker"
#: Docker runtime registered by the DGX runsc wrapper.
DEFAULT_DOCKER_RUNTIME = "runsc-gvproxy-ptrace"
DEFAULT_CONTAINER_HOME = "/home/cedev4"
DEFAULT_CONTAINER_CODEX_HOME = f"{DEFAULT_CONTAINER_HOME}/.codex"
DEFAULT_CODEX_BIN_TARGET = "/usr/local/bin/codex"

_SAFE_RUNTIME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_HOST_NETWORK_ARG_RE = re.compile(r"^--?(?:network|net)=host$")

_NETWORK_KEYS = {
    "network",
    "network_mode",
    "networkmode",
    "docker_network",
    "dockernetwork",
    "net",
    "net_mode",
    "netmode",
}


class EgressNotEnforceable(BackendUnavailable):
    """A non-empty egress allowlist cannot be enforced (no proven primitive).

    Defined locally (subclassing the G-1.1 ``BackendUnavailable``) so the stable
    ``runner/backend.py`` ABC stays untouched. Raised *before* any side effect,
    preserving the v2 "never run broad egress" safety invariant.
    """


class RunscPlanRejected(ValueError):
    """The Docker/runsc plan lacks required safe rendering inputs."""


# ---------------------------------------------------------------------------
# Pure translation outputs (consumed in-process; no persistence boundary → no schema)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EgressRule:
    host: str
    port: int | None
    protocol: str | None
    assurance: tuple[str, ...]
    tls_terminated: bool


@dataclass(frozen=True)
class EgressProxyConfig:
    """A deny-by-default egress config translated from a runtime policy.

    This is a pure policy object. It is not proof that a live runner can enforce
    the allowlist.
    """

    deny_by_default: bool
    rules: tuple[EgressRule, ...]

    @property
    def no_egress(self) -> bool:
        return not self.rules


@dataclass(frozen=True)
class RunscPlan:
    """A Docker-backed gVisor/runsc container plan translated from a policy."""

    docker_binary: str
    runtime_name: str
    image_name: str
    image_digest: str
    mounts: tuple[MountSpec, ...]
    network: str  # "none" (no egress) | "proxy" (mediated, default-deny)
    uid: int
    gid: int | None
    container_home: str
    container_codex_home: str
    host_codex_home: str
    host_codex_bin: str
    container_workdir: str
    codex_home_mode: str
    codex_bin_target: str
    remove: bool
    no_new_privileges: bool
    drop_all_capabilities: bool
    docker_network: str | None = None
    tty_flags: tuple[str, ...] = ()

    @property
    def image_ref(self) -> str:
        return f"{self.image_name}@{self.image_digest}"

    @property
    def user_spec(self) -> str:
        return str(self.uid) if self.gid is None else f"{self.uid}:{self.gid}"

    def docker_argv(self, command: Sequence[str]) -> tuple[str, ...]:
        """Render the DGX Docker/runsc invocation argv for ``command``."""
        args: list[str] = [self.docker_binary, "run"]
        if self.remove:
            args.append("--rm")
        args.append(f"--runtime={self.runtime_name}")
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
            "--mount",
            render_mount(MountSpec(self.host_codex_home, self.container_codex_home, self.codex_home_mode)),
            "--mount",
            render_mount(MountSpec(self.host_codex_bin, self.codex_bin_target, "ro")),
        ]
        for mount in self.mounts:
            args += ["--mount", render_mount(mount)]
        if self.docker_network:
            args.append(f"--network={self.docker_network}")
        args += list(self.tty_flags)
        args += [self.image_ref, *command]
        return tuple(args)

    def runsc_argv(self, command: Sequence[str]) -> tuple[str, ...]:
        """Compatibility alias for callers that still ask for the runsc argv."""
        return self.docker_argv(command)


# ---------------------------------------------------------------------------
# Pure translation functions
# ---------------------------------------------------------------------------
def translate_to_runsc_plan(
    runtime_policy: dict[str, Any],
    *,
    uid: int | str | None = None,
    gid: int | str | None = None,
    runtime_name: str = DEFAULT_DOCKER_RUNTIME,
    host_codex_home: str | None = None,
    host_codex_bin: str | None = None,
    container_home: str = DEFAULT_CONTAINER_HOME,
    container_codex_home: str = DEFAULT_CONTAINER_CODEX_HOME,
    container_workdir: str | None = None,
    codex_home_mode: str = "rw",
    docker_network: str | None = None,
    tty_flags: Sequence[str] = (),
) -> RunscPlan:
    """Translate a runtime-policy record into a Docker/runsc container plan (pure)."""
    image = runtime_policy.get("image_ref") or {}
    name = image.get("name", "") if isinstance(image, dict) else ""
    sha = image.get("sha", "") if isinstance(image, dict) else ""
    image_name = require_nonempty_str(name, "image_ref.name", error_type=RunscPlanRejected)
    image_digest = require_image_digest(sha, error_type=RunscPlanRejected)
    mounts = tuple(
        mount_from_policy_entry(entry, index, error_type=RunscPlanRejected)
        for index, entry in enumerate(runtime_policy.get("mount_manifest") or [])
        if isinstance(entry, dict)
    )
    if not mounts:
        raise RunscPlanRejected("mount_manifest must include at least one Docker bind mount")
    workdir = container_workdir or first_writable_mount_target(mounts)
    if workdir is None:
        raise RunscPlanRejected("container_workdir is required when no rw mount is declared")
    resolved_uid = require_uid_gid(uid, "uid", error_type=RunscPlanRejected)
    resolved_gid = optional_uid_gid(gid, "gid", error_type=RunscPlanRejected)
    runtime = _require_runtime_name(runtime_name)
    codex_home = require_abs_path(host_codex_home, "host_codex_home", error_type=RunscPlanRejected)
    codex_bin = require_abs_path(host_codex_bin, "host_codex_bin", error_type=RunscPlanRejected)
    container_home = require_abs_path(container_home, "container_home", error_type=RunscPlanRejected)
    container_codex_home = require_abs_path(
        container_codex_home, "container_codex_home", error_type=RunscPlanRejected
    )
    workdir = require_abs_path(workdir, "container_workdir", error_type=RunscPlanRejected)
    mode = require_mode(codex_home_mode, "codex_home_mode", error_type=RunscPlanRejected)
    if docker_network:
        raise RunscPlanRejected(
            "docker_network must be omitted for the DGX runsc plan; the registered "
            "runsc-gvproxy-ptrace runtime owns networking"
        )
    rendered_tty_flags = tuple(
        require_nonempty_str(flag, "tty_flags", error_type=RunscPlanRejected)
        for flag in tty_flags
    )
    policy_mounts = tuple(
        MountSpec(
            source=mount.source,
            target=mount.target,
            mode=require_mode(mount.mode, "mount mode", error_type=RunscPlanRejected),
        )
        for mount in mounts
    )
    has_egress = bool(runtime_policy.get("egress_allowlist") or [])
    return RunscPlan(
        docker_binary=DOCKER_BINARY,
        runtime_name=runtime,
        image_name=image_name,
        image_digest=image_digest,
        mounts=policy_mounts,
        network="proxy" if has_egress else "none",
        uid=resolved_uid,
        gid=resolved_gid,
        container_home=container_home,
        container_codex_home=container_codex_home,
        host_codex_home=codex_home,
        host_codex_bin=codex_bin,
        container_workdir=workdir,
        codex_home_mode=mode,
        codex_bin_target=DEFAULT_CODEX_BIN_TARGET,
        remove=True,
        no_new_privileges=True,
        drop_all_capabilities=True,
        docker_network=None,
        tty_flags=rendered_tty_flags,
    )


def _require_runtime_name(value: Any) -> str:
    runtime = require_nonempty_str(value, "runtime_name", error_type=RunscPlanRejected)
    if not _SAFE_RUNTIME_RE.match(runtime):
        raise RunscPlanRejected("runtime_name contains unsafe characters")
    if runtime in {"runsc", "runsc-gvproxy"}:
        raise RunscPlanRejected(
            "runtime_name must use the DGX ptrace runtime, not plain runsc or systrap runsc-gvproxy"
        )
    return runtime


def translate_to_egress_proxy_config(runtime_policy: dict[str, Any]) -> EgressProxyConfig:
    """Translate ``egress_allowlist`` into a deny-by-default egress config (pure).

    Deny-by-default is ALWAYS the floor. An empty allowlist yields ``no_egress``;
    a non-empty allowlist yields explicit allow rules. Live provisioning still
    refuses the non-empty case unless the runner proves a real allowlist
    enforcement primitive.
    """
    rules: list[EgressRule] = []
    for entry in runtime_policy.get("egress_allowlist") or []:
        if not isinstance(entry, dict):
            continue
        assurance = entry.get("assurance")
        rules.append(
            EgressRule(
                host=str(entry.get("host", "")),
                port=entry.get("port") if isinstance(entry.get("port"), int) else None,
                protocol=entry.get("protocol") if isinstance(entry.get("protocol"), str) else None,
                assurance=tuple(assurance) if isinstance(assurance, list) else (),
                tls_terminated=entry.get("tls_terminated") is True,
            )
        )
    return EgressProxyConfig(deny_by_default=True, rules=tuple(rules))


# ---------------------------------------------------------------------------
# Injectable runner seam (mirror the forge GhRunner) + availability gate
# ---------------------------------------------------------------------------
class ContainerRunner(Protocol):
    """The live-execution seam. The ONLY surface that ever touches a real runtime."""

    def available(self) -> bool:
        """True when the Docker client/runtime path is present in this environment."""
        ...

    def egress_enforceable(self) -> bool:
        """True only when a concrete allowlist enforcement primitive is proven."""
        ...

    def run(self, argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        """Execute ``argv`` against the live runtime."""
        ...


class SubprocessContainerRunner:
    """Default runner: shells out to Docker. Availability-gated; the only live-exec path."""

    def __init__(
        self,
        binary: str = DOCKER_BINARY,
        required_runtime: str = DEFAULT_DOCKER_RUNTIME,
        *,
        probe_timeout_seconds: float = 2.0,
        probe_interval_seconds: float = 0.05,
    ) -> None:
        self._binary = binary
        self._required_runtime = required_runtime
        self._probe_timeout_seconds = max(0.0, float(probe_timeout_seconds))
        self._probe_interval_seconds = max(0.0, float(probe_interval_seconds))

    def available(self) -> bool:
        return shutil.which(self._binary) is not None and self._runtime_registered()

    def _runtime_registered(self) -> bool:
        runtimes = self._docker_runtimes()
        return runtimes is not None and self._required_runtime in runtimes

    def _registered_runtime_config(self) -> dict[str, Any] | None:
        runtimes = self._docker_runtimes()
        if runtimes is None:
            return None
        config = runtimes.get(self._required_runtime)
        return config if isinstance(config, dict) else None

    def _docker_runtimes(self) -> dict[str, Any] | None:
        try:
            completed = subprocess.run(
                [self._binary, "info", "--format", "{{json .Runtimes}}"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        if completed.returncode != 0:
            return None
        try:
            runtimes = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            return None
        if not isinstance(runtimes, dict):
            return None
        return runtimes

    def egress_enforceable(self) -> bool:
        config = self._registered_runtime_config()
        if config is None:
            return False
        return _runtime_declares_allowlist_enforcement_primitive(config)

    def run(self, argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:  # pragma: no cover - requires live Docker
        return subprocess.run(
            list(argv), input=input_text, capture_output=True, text=True, check=False
        )

    def runtime_probe(
        self,
        *,
        run_id: str,
        argv: Sequence[str],
        surface: Any,
    ) -> dict[str, Any] | None:
        """Observe the launched Docker/runsc container and return its host PID.

        The visible launch path starts ``docker run`` in an operator-visible
        surface, not through this runner. This method is therefore a separate
        launch-owned observation step: it accepts only argv carrying the CE-owned
        name/label contract and then verifies those labels through Docker inspect
        before returning the PID that the containment probe must independently
        check.
        """
        del surface  # the ownership proof is Docker-observed name/labels.
        expected_name = launch_probe_container_name(run_id)
        if not argv_carries_launch_probe_contract(argv, run_id=run_id, name=expected_name):
            return None
        deadline = time.monotonic() + self._probe_timeout_seconds
        while True:
            payload = self._inspect_launch_probe_container(expected_name, run_id=run_id)
            if payload is not None:
                return payload
            if time.monotonic() >= deadline:
                return None
            time.sleep(self._probe_interval_seconds)

    def _inspect_launch_probe_container(self, name: str, *, run_id: str) -> dict[str, Any] | None:
        try:
            completed = subprocess.run(
                [self._binary, "inspect", "--format", "{{json .}}", name],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        if completed.returncode != 0:
            return None
        try:
            inspected = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            return None
        if not isinstance(inspected, dict):
            return None
        config = inspected.get("Config")
        labels = config.get("Labels") if isinstance(config, dict) else None
        if not isinstance(labels, dict):
            return None
        if labels.get(LAUNCH_PROBE_RUN_ID_LABEL) != run_id:
            return None
        if labels.get(LAUNCH_PROBE_CONTRACT_LABEL) != LAUNCH_PROBE_CONTRACT:
            return None
        state = inspected.get("State")
        pid = state.get("Pid") if isinstance(state, dict) else None
        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            return None
        if pid_int <= 0:
            return None
        return {
            "pid": str(pid_int),
            "run_id": run_id,
            "launch_owned": True,
            "probe_contract": LAUNCH_PROBE_CONTRACT,
            "source": "docker-inspect",
            "container_name": name,
        }


def _runtime_declares_host_network(config: dict[str, Any]) -> bool:
    for key, value in _walk_runtime_metadata(config):
        normalized = _normalize_metadata_key(key)
        if normalized in _NETWORK_KEYS and _metadata_value(value) == "host":
            return True
        if _sequence_declares_host_network(value):
            return True
        if isinstance(value, str) and _HOST_NETWORK_ARG_RE.match(value.strip().lower()):
            return True
    return False


def _runtime_declares_allowlist_enforcement_primitive(config: dict[str, Any]) -> bool:
    """Return True only for known allowlist enforcement primitives.

    The DGX Docker runtime metadata can prove that Docker will invoke runsc and
    may route traffic through gvproxy, but this module does not currently wire a
    live allowlist-enforcing proxy/config handoff. Treating generic
    ``gvproxy``/``proxy``/``egressPolicy`` strings as enforcement would be a
    false attestation, so the current known-primitive set is intentionally empty.
    """
    if _runtime_declares_host_network(config):
        return False
    return False


def _walk_runtime_metadata(value: Any, key: str = ""):
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_key_str = str(child_key)
            yield child_key_str, child_value
            yield from _walk_runtime_metadata(child_value, child_key_str)
    elif isinstance(value, (list, tuple)):
        for child_value in value:
            yield key, child_value
            yield from _walk_runtime_metadata(child_value, key)


def _sequence_declares_host_network(value: Any) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    parts = [_metadata_value(part) for part in value]
    return _sequence_has_network_value(parts, "host") or any(
        _HOST_NETWORK_ARG_RE.match(part) for part in parts
    )


def _sequence_has_network_value(parts: list[str], expected: str) -> bool:
    for index, part in enumerate(parts[:-1]):
        if part in {"--network", "network", "--net", "net"} and parts[index + 1] == expected:
            return True
    return False


def _normalize_metadata_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _metadata_value(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


# ---------------------------------------------------------------------------
# The backend
# ---------------------------------------------------------------------------
class GvisorProxyBackend(RunnerBackend):
    """gVisor runner backend with deny-by-default egress gating."""

    backend_key = BACKEND_KEY

    def __init__(
        self,
        runner: ContainerRunner | None = None,
        *,
        uid: int | str | None = None,
        gid: int | str | None = None,
        runtime_name: str = DEFAULT_DOCKER_RUNTIME,
        host_codex_home: str | None = None,
        host_codex_bin: str | None = None,
        container_home: str = DEFAULT_CONTAINER_HOME,
        container_codex_home: str = DEFAULT_CONTAINER_CODEX_HOME,
        container_workdir: str | None = None,
        codex_home_mode: str = "rw",
        tty_flags: Sequence[str] = (),
    ) -> None:
        self._runner: ContainerRunner = (
            runner if runner is not None else SubprocessContainerRunner(required_runtime=runtime_name)
        )
        self._plans: dict[str, RunscPlan] = {}
        self._plan_kwargs = {
            "uid": uid,
            "gid": gid,
            "runtime_name": runtime_name,
            "host_codex_home": host_codex_home,
            "host_codex_bin": host_codex_bin,
            "container_home": container_home,
            "container_codex_home": container_codex_home,
            "container_workdir": container_workdir,
            "codex_home_mode": codex_home_mode,
            "tty_flags": tuple(tty_flags),
        }

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        # The deny surface (mapping + validate_runtime_policy → PolicyRejected) is
        # enforced by the RunnerBackend.provision template method before we get here.
        record = request.runtime_policy
        # Pure translation (no side effects).
        try:
            plan = translate_to_runsc_plan(record, **self._plan_kwargs)
        except RunscPlanRejected as exc:
            raise BackendUnavailable(f"invalid Docker/runsc plan: {exc}") from exc
        egress = translate_to_egress_proxy_config(record)
        # Safety floor: a non-empty allowlist MUST have proven enforcement;
        # mirror worker_runtime and refuse before Docker/runsc availability probing.
        if not egress.no_egress and not self._runner.egress_enforceable():
            raise EgressNotEnforceable(
                "policy declares a non-empty egress allowlist but no allowlist enforcement "
                "primitive is proven; refusing before container start (broad egress is never "
                "silently labelled governed)"
            )
        # Availability gate — refuse before any side effect.
        if not self._runner.available():
            raise BackendUnavailable(
                f"the {DOCKER_BINARY!r} client is not available; refusing to provision"
            )
        policy_sha = record.get("policy_sha", "")
        handle = ProvisionedHandle(
            backend_key=self.backend_key,
            run_id=request.run_id,
            policy_sha=policy_sha if isinstance(policy_sha, str) else "",
            ref=f"gvisor:{request.run_id}",
        )
        self._plans[handle.ref] = plan
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        plan = self._plans.get(handle.ref)
        if plan is None:
            raise BackendUnavailable(
                f"no provisioned Docker/runsc plan for handle {handle.ref!r}; refusing unproven handle"
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
            note=f"gvisor-proxy backend evidence for {handle.ref}",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        self._plans.pop(handle.ref, None)
        return TeardownResult(handle_ref=handle.ref, released=True)


register_backend(BACKEND_KEY, GvisorProxyBackend)
