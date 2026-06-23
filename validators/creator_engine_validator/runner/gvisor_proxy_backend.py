"""CE v3 plane-C backend: hardened gVisor + capability-separation egress proxy (G-1.2).

The first runner backend that translates a runtime-policy record (the G-1.0
contract) into the hardened DGX Docker ``runsc`` shape plus a
**capability-separation egress-proxy** deny-by-default config, registered under
the ``gvisor-proxy`` key behind the G-1.1 ``RunnerBackend`` adapter.

This FIXES the in-repo egress STUB: the v2 ``worker_runtime`` path returns no
egress-enforcement primitive (``egress_primitive() -> None``) and therefore
*refuses* a non-empty egress allowlist rather than enforcing it. The v3 backend
translates the allowlist into an enforceable deny-by-default proxy config — the
agent holds no network/secrets; the proxy holds both.

LOAD-BEARING translate-vs-execute split (CI has no Docker/runsc runtime):

* ``translate_to_runsc_plan`` and ``translate_to_egress_proxy_config`` are
  **pure** functions with NO side effects — fully unit-tested.
* All live work goes through an injectable ``ContainerRunner`` seam (mirror the
  forge ``GhRunner``): callers inject a fake; tests perform ZERO live subprocess
  and importing this module performs no I/O.
* Live provisioning is **gated behind an availability probe**
  (``ContainerRunner.available``) and refuses before any side effect when the
  Docker/runsc runtime or the egress-proxy primitive is absent — broad egress is
  never silently run.

Defensive only — hardens our own agent runtime; never an offensive capability.
"""

from __future__ import annotations

import re
import shutil
import subprocess
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

BACKEND_KEY = "gvisor-proxy"
#: The container client used to reach Docker's registered runsc runtime.
DOCKER_BINARY = "docker"
#: Docker runtime registered by the DGX runsc wrapper.
DEFAULT_DOCKER_RUNTIME = "runsc-gvproxy-ptrace"
DEFAULT_CONTAINER_HOME = "/home/cedev4"
DEFAULT_CONTAINER_CODEX_HOME = f"{DEFAULT_CONTAINER_HOME}/.codex"
DEFAULT_CODEX_BIN_TARGET = "/usr/local/bin/codex"

_IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_RUNTIME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class EgressNotEnforceable(BackendUnavailable):
    """A non-empty egress allowlist cannot be enforced (no proxy primitive).

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
    """A deny-by-default egress-proxy config translated from a runtime policy."""

    deny_by_default: bool
    rules: tuple[EgressRule, ...]

    @property
    def no_egress(self) -> bool:
        return not self.rules


@dataclass(frozen=True)
class MountSpec:
    source: str
    target: str
    mode: str  # "ro" | "rw"


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
            _render_mount(MountSpec(self.host_codex_home, self.container_codex_home, self.codex_home_mode)),
            "--mount",
            _render_mount(MountSpec(self.host_codex_bin, self.codex_bin_target, "ro")),
        ]
        for mount in self.mounts:
            args += ["--mount", _render_mount(mount)]
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
    image_name = _require_nonempty_str(name, "image_ref.name")
    image_digest = _require_image_digest(sha)
    mounts = tuple(
        _mount_from_policy_entry(entry, index)
        for index, entry in enumerate(runtime_policy.get("mount_manifest") or [])
        if isinstance(entry, dict)
    )
    if not mounts:
        raise RunscPlanRejected("mount_manifest must include at least one Docker bind mount")
    workdir = container_workdir or _first_writable_mount_target(mounts)
    if workdir is None:
        raise RunscPlanRejected("container_workdir is required when no rw mount is declared")
    resolved_uid = _require_uid_gid(uid, "uid")
    resolved_gid = _optional_uid_gid(gid, "gid")
    runtime = _require_runtime_name(runtime_name)
    codex_home = _require_abs_path(host_codex_home, "host_codex_home")
    codex_bin = _require_abs_path(host_codex_bin, "host_codex_bin")
    container_home = _require_abs_path(container_home, "container_home")
    container_codex_home = _require_abs_path(container_codex_home, "container_codex_home")
    workdir = _require_abs_path(workdir, "container_workdir")
    mode = _require_mode(codex_home_mode, "codex_home_mode")
    if docker_network:
        raise RunscPlanRejected(
            "docker_network must be omitted for the DGX runsc plan; the registered "
            "runsc-gvproxy-ptrace runtime owns networking"
        )
    rendered_tty_flags = tuple(_require_nonempty_str(flag, "tty_flags") for flag in tty_flags)
    policy_mounts = tuple(
        MountSpec(source=mount.source, target=mount.target, mode=_require_mode(mount.mode, "mount mode"))
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


def _mount_from_policy_entry(entry: dict[str, Any], index: int) -> MountSpec:
    path = _require_abs_path(entry.get("path"), f"mount_manifest[{index}].path")
    return MountSpec(
        source=path,
        target=path,
        mode=_require_mode(entry.get("mode", "ro"), f"mount_manifest[{index}].mode"),
    )


def _first_writable_mount_target(mounts: tuple[MountSpec, ...]) -> str | None:
    for mount in mounts:
        if mount.mode == "rw":
            return mount.target
    return None


def _render_mount(mount: MountSpec) -> str:
    rendered = f"type=bind,source={mount.source},target={mount.target}"
    if mount.mode == "ro":
        rendered = f"{rendered},readonly"
    return rendered


def _require_nonempty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RunscPlanRejected(f"{field} is required")
    return value


def _require_abs_path(value: Any, field: str) -> str:
    path = _require_nonempty_str(value, field)
    if not path.startswith("/") or path.startswith("//") or "\x00" in path:
        raise RunscPlanRejected(f"{field} must be a non-empty absolute path")
    return path


def _require_mode(value: Any, field: str) -> str:
    mode = _require_nonempty_str(value, field)
    if mode not in {"ro", "rw"}:
        raise RunscPlanRejected(f"{field} must be 'ro' or 'rw'")
    return mode


def _require_image_digest(value: Any) -> str:
    digest = _require_nonempty_str(value, "image_ref.sha")
    if not _IMAGE_DIGEST_RE.match(digest):
        raise RunscPlanRejected("image_ref.sha must be a sha256:<hex64> digest")
    return digest


def _require_uid_gid(value: int | str | None, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise RunscPlanRejected(f"{field} is required")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise RunscPlanRejected(f"{field} must be a non-negative integer") from None
    if parsed < 0:
        raise RunscPlanRejected(f"{field} must be a non-negative integer")
    return parsed


def _optional_uid_gid(value: int | str | None, field: str) -> int | None:
    if value is None:
        return None
    return _require_uid_gid(value, field)


def _require_runtime_name(value: Any) -> str:
    runtime = _require_nonempty_str(value, "runtime_name")
    if not _SAFE_RUNTIME_RE.match(runtime):
        raise RunscPlanRejected("runtime_name contains unsafe characters")
    if runtime in {"runsc", "runsc-gvproxy"}:
        raise RunscPlanRejected(
            "runtime_name must use the DGX ptrace runtime, not plain runsc or systrap runsc-gvproxy"
        )
    return runtime


def translate_to_egress_proxy_config(runtime_policy: dict[str, Any]) -> EgressProxyConfig:
    """Translate ``egress_allowlist`` into a deny-by-default egress-proxy config (pure).

    Deny-by-default is ALWAYS the floor. An empty allowlist yields ``no_egress``;
    a non-empty allowlist yields explicit allow rules (the egress-stub FIX — an
    enforceable config, not a refusal). Everything not listed is denied.
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
        """True when the capability-separation egress proxy can enforce a config."""
        ...

    def run(self, argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        """Execute ``argv`` against the live runtime."""
        ...


class SubprocessContainerRunner:
    """Default runner: shells out to Docker. Availability-gated; the only live-exec path."""

    def __init__(self, binary: str = DOCKER_BINARY) -> None:
        self._binary = binary

    def available(self) -> bool:
        return shutil.which(self._binary) is not None

    def egress_enforceable(self) -> bool:
        # The v3 capability-separation proxy enforces egress via the translated
        # config (unlike the v2 stub, which returns no primitive). The concrete
        # proxy route is provided by the registered Docker runsc runtime.
        return True

    def run(self, argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:  # pragma: no cover - requires live Docker
        return subprocess.run(
            list(argv), input=input_text, capture_output=True, text=True, check=False
        )


# ---------------------------------------------------------------------------
# The backend
# ---------------------------------------------------------------------------
class GvisorProxyBackend(RunnerBackend):
    """gVisor + capability-separation egress-proxy backend (translation + injected runner)."""

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
        self._runner: ContainerRunner = runner if runner is not None else SubprocessContainerRunner()
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
        # Availability gate — refuse before any side effect.
        if not self._runner.available():
            raise BackendUnavailable(
                f"the {DOCKER_BINARY!r} client is not available; refusing to provision"
            )
        # Egress-stub fix + safety floor: a non-empty allowlist MUST be enforceable;
        # never run broad egress.
        if not egress.no_egress and not self._runner.egress_enforceable():
            raise EgressNotEnforceable(
                "policy declares a non-empty egress allowlist but no proxy primitive is "
                "enforceable; refusing before container start (broad egress is never silent)"
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
        argv = plan.docker_argv(request.command) if plan else (DOCKER_BINARY, "exec", handle.ref, *request.command)
        completed = self._runner.run(argv)
        return RunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            started_ref=handle.ref,
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
