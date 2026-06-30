"""The unprivileged OS-native runner backend — user-elected, fail-closed.

This is the neutral-keyed (``os-native``) realization of #71's headline direction:
a daemonless, rootless backend (Linux ``bwrap`` + Landlock + seccomp + a host
deny-by-default proxy; Seatbelt on macOS as a later lane) that lets a user elect
the lowest-privilege tier of the RunnerBackend menu.

OQ-1 Option A is ratified: the Linux mechanism is ``bwrap`` + Landlock +
seccomp + a deny-by-default egress proxy, while ``gvisor-proxy`` remains the
default backend. When the primitives are not present, :meth:`_provision` refuses
with :class:`BackendUnavailable`. When the host primitives are present but CE has
no concrete os-native host-proxy handoff and restrictive seccomp policy to wire,
provisioning still refuses before any side effect. That preserves the cardinal
invariant: os-native never silently downgrades to an unsandboxed or weaker local
launch.

What this backend DOES enforce today, fully:

* **The G-1.0 deny surface stays load-bearing.** Provisioning runs through the
  :class:`RunnerBackend.provision` template method, which validates the
  runtime-policy record FIRST (``validate_runtime_policy`` → :class:`PolicyRejected`
  on a dirty record) before :meth:`_provision` is ever called. Because #71 ADDS this
  backend, that validate-at-provision invariant is what keeps the grader-outside moat
  intact for the new lighter tier — and it is enforced at the ABC, not here.
* **Registration + selection.** It registers under the ``os-native`` key
  (``schemas/runtime-policy.schema.yaml`` enum) so a policy/profile can SELECT it and
  audit predicates can attest the selection. Omitted runtime-policy records still
  resolve to ``gvisor-proxy`` through the shared resolver.

Design invariants (shared with the other backends):

* **Not a validator check.** ``register_backend`` is the BACKEND registry, not the
  ``@register`` check registry — importing this module adds no check and leaves
  ``--list-checks`` byte-identical.
* **Zero I/O on import / no live side effect.** Importing allocates nothing. The
  live path is behind an injectable runner seam and only starts after policy,
  capability, mount, egress, Landlock, and seccomp gates succeed.
* **Defensive.** This hardens CE's own agent runtime; it is never an offensive
  capability.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..fs_mediation import RunnerFsConfinement, landlock_abi_version, landlock_preexec
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
    EgressProxyConfig,
    EgressRule,
    translate_to_egress_proxy_config,
)

BACKEND_KEY = "os-native"

#: The ratified OQ-1 Option-A Linux primitives for the user-elected Tier-1
#: backend. They are probe-only prerequisites here, never auto-installed; that
#: keeps os-native zero-root and fail-closed.
LINUX_SANDBOX_PRIMITIVES: tuple[str, ...] = ("bwrap", "landlock", "seccomp", "proxy")
_SECCOMP_RET_ALLOW = 0x7FFF0000
_BPF_RET_K = 0x06
_DEFAULT_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
_SYSTEM_RO_BIND_ROOTS: tuple[str, ...] = (
    "/usr",
    "/bin",
    "/lib",
    "/lib64",
    "/sbin",
    "/etc",
)
_EXECUTION_CONTRACT_UNAVAILABLE_REASON = (
    "the 'os-native' backend capability probe passed, but no concrete "
    "deny-by-default host-proxy enforcement contract and restrictive seccomp "
    "policy are available to wire for OQ-1 Option A; refusing before sandbox "
    "start rather than launching a weaker or unsandboxed command"
)


@dataclass(frozen=True)
class OsNativeCapability:
    """Pure capability probe result for the OQ-1 Option-A Linux mechanism."""

    platform_name: str
    bwrap_path: str | None
    landlock_abi: int | None
    seccomp_available: bool
    proxy_path: str | None
    missing: tuple[str, ...]

    @property
    def available(self) -> bool:
        return not self.missing


CapabilityProbe = Callable[[], OsNativeCapability]
OpenShellBackendFactory = Callable[[], RunnerBackend]


class OsNativePlanRejected(ValueError):
    """The os-native sandbox plan lacks required safe rendering inputs."""


@dataclass(frozen=True)
class OsNativeMount:
    source: str
    target: str
    mode: str  # "ro" | "rw"


@dataclass(frozen=True)
class OsNativePlan:
    """A bwrap-backed Linux os-native launch plan."""

    bwrap_path: str
    mounts: tuple[OsNativeMount, ...]
    workdir: str
    network: str  # currently "none"; non-empty egress policies refuse before launch
    proxy_path: str
    landlock_abi: int
    seccomp_filter: bytes
    env: tuple[tuple[str, str], ...]
    read_roots: tuple[str, ...]

    def bwrap_argv(self, command: tuple[str, ...], *, seccomp_fd: int) -> tuple[str, ...]:
        """Render the bubblewrap argv. The seccomp FD is supplied by ``run``."""
        args: list[str] = [
            self.bwrap_path,
            "--unshare-user",
            "--uid",
            "0",
            "--gid",
            "0",
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
        ]
        if self.network == "none":
            args.append("--unshare-net")
        for key, value in self.env:
            args += ["--setenv", key, value]
        for root in _SYSTEM_RO_BIND_ROOTS:
            if Path(root).exists():
                args += ["--ro-bind", root, root]
        for mount in self.mounts:
            args += [
                "--bind" if mount.mode == "rw" else "--ro-bind",
                mount.source,
                mount.target,
            ]
        args += ["--chdir", self.workdir, "--seccomp", str(seccomp_fd), "--", *command]
        return tuple(args)


@dataclass
class _OpenShellDelegation:
    backend: RunnerBackend
    handle: ProvisionedHandle
    p3_verified: bool = False


class OsNativeCommandRunner(Protocol):
    """The live bwrap execution seam. Tests inject a fake; default uses subprocess."""

    def available(self, capability: OsNativeCapability) -> bool:
        """True when the probed primitives are still executable at launch time."""
        ...

    def run(
        self,
        argv: tuple[str, ...],
        *,
        preexec_fn: Callable[[], None],
        pass_fds: tuple[int, ...],
    ) -> subprocess.CompletedProcess:
        """Execute the rendered bwrap argv."""
        ...


class SubprocessOsNativeRunner:
    """Default runner: shells out to bwrap only after all fail-closed gates pass."""

    def available(self, capability: OsNativeCapability) -> bool:
        return (
            capability.available
            and capability.bwrap_path is not None
            and capability.proxy_path is not None
            and Path(capability.bwrap_path).is_file()
            and Path(capability.proxy_path).is_file()
        )

    def run(
        self,
        argv: tuple[str, ...],
        *,
        preexec_fn: Callable[[], None],
        pass_fds: tuple[int, ...],
    ) -> subprocess.CompletedProcess:  # pragma: no cover - requires live bwrap/Landlock
        return subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            check=False,
            preexec_fn=preexec_fn,
            pass_fds=pass_fds,
            close_fds=True,
        )


_P3_BLOCKED_HOST = "203.0.113.1"
_P3_BLOCKED_PORT = 443
_P3_BLOCKED_TARGET = f"{_P3_BLOCKED_HOST}:{_P3_BLOCKED_PORT}"
_P3_BLOCKED_PROBE_COMMAND = (
    "python3",
    "-c",
    (
        "import socket, sys\n"
        f"host = {_P3_BLOCKED_HOST!r}\n"
        f"port = {_P3_BLOCKED_PORT!r}\n"
        "try:\n"
        "    sock = socket.create_connection((host, port), timeout=2)\n"
        "except OSError:\n"
        "    sys.exit(0)\n"
        "else:\n"
        "    sock.close()\n"
        "    sys.exit(42)\n"
    ),
)


def _default_openshell_backend() -> RunnerBackend:
    """Return a live OpenShell backend only when its CLI transport is available."""

    from .openshell_backend import OpenShellBackend, SubprocessSandboxClient

    client = SubprocessSandboxClient()
    if not client.available():
        raise BackendUnavailable(
            "policy declares a non-empty egress allowlist; os-native delegates egress "
            "enforcement to OpenShell for OQ-1 Option C, but the OpenShell CLI is not "
            "available. Refusing before any os-native proxy PATH probe or sandbox start."
        )
    return OpenShellBackend(client=client)


def _has_p3_denial(records: tuple[dict[str, Any], ...]) -> bool:
    for record in records:
        if record.get("disposition") != "DENIED":
            continue
        target = record.get("target")
        if target == _P3_BLOCKED_TARGET:
            return True
        raw = record.get("raw")
        if isinstance(raw, dict) and raw.get("target") == _P3_BLOCKED_TARGET:
            return True
    return False


def _seccomp_available() -> bool:
    """Return whether this Linux host exposes seccomp support, without mutating state."""

    actions = Path("/proc/sys/kernel/seccomp/actions_avail")
    if actions.is_file():
        return True
    status = Path("/proc/self/status")
    try:
        text = status.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(line.startswith("Seccomp:") for line in text.splitlines())


def probe_os_native_capability() -> OsNativeCapability:
    """Probe the ratified Linux os-native primitives without launching anything."""

    platform_name = platform.system()
    if platform_name != "Linux":
        return OsNativeCapability(
            platform_name=platform_name,
            bwrap_path=None,
            landlock_abi=None,
            seccomp_available=False,
            proxy_path=None,
            missing=("linux",),
        )

    bwrap_path = shutil.which("bwrap")
    proxy_path = shutil.which("proxy")
    landlock_abi = landlock_abi_version()
    seccomp_available = _seccomp_available()
    missing = tuple(
        primitive
        for primitive, present in (
            ("bwrap", bwrap_path is not None),
            ("landlock", landlock_abi is not None),
            ("seccomp", seccomp_available),
            ("proxy", proxy_path is not None),
        )
        if not present
    )
    return OsNativeCapability(
        platform_name=platform_name,
        bwrap_path=bwrap_path,
        landlock_abi=landlock_abi,
        seccomp_available=seccomp_available,
        proxy_path=proxy_path,
        missing=missing,
    )


def _unavailable_reason(capability: OsNativeCapability) -> str:
    if "linux" in capability.missing:
        return (
            "the 'os-native' backend is user-elected and fail-closed under OQ-1 "
            "Option A: Linux bwrap + Landlock + seccomp + a deny-by-default proxy "
            f"are required, but this host reports {capability.platform_name!r}; "
            "refusing rather than falling back to unsandboxed execution"
        )
    missing = ", ".join(capability.missing)
    required = ", ".join(LINUX_SANDBOX_PRIMITIVES)
    return (
        "the 'os-native' backend is user-elected and fail-closed under OQ-1 "
        f"Option A: required Linux primitives are {required}; missing: {missing}. "
        "Refusing rather than falling back to unsandboxed execution or gvisor-proxy."
    )


def _seccomp_allow_filter() -> bytes:
    """Return a minimal classic-BPF seccomp program for bwrap's --seccomp FD.

    Bubblewrap expects a raw sock_filter program as produced by
    seccomp_export_bpf. The live network boundary for this slice is the bwrap
    network namespace; the explicit filter proves the seccomp primitive is
    attached without trying to maintain a fragile syscall allowlist in Python.
    """
    return (
        _BPF_RET_K.to_bytes(2, "little")
        + b"\x00\x00"
        + _SECCOMP_RET_ALLOW.to_bytes(4, "little")
    )


def _require_abs_existing_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OsNativePlanRejected(f"{field} is required")
    if not value.startswith("/") or value.startswith("//") or "\x00" in value:
        raise OsNativePlanRejected(f"{field} must be a non-empty absolute path")
    path = Path(value)
    if not path.exists():
        raise OsNativePlanRejected(f"{field} does not exist: {value}")
    return value


def _require_mode(value: Any, field: str) -> str:
    mode = value if isinstance(value, str) else "ro"
    if mode not in {"ro", "rw"}:
        raise OsNativePlanRejected(f"{field} must be 'ro' or 'rw'")
    return mode


def _mount_from_policy_entry(entry: dict[str, Any], index: int) -> OsNativeMount:
    path = _require_abs_existing_path(entry.get("path"), f"mount_manifest[{index}].path")
    return OsNativeMount(
        source=path,
        target=path,
        mode=_require_mode(entry.get("mode", "ro"), f"mount_manifest[{index}].mode"),
    )


def _first_writable_mount(mounts: tuple[OsNativeMount, ...]) -> str | None:
    for mount in mounts:
        if mount.mode == "rw":
            return mount.target
    return mounts[0].target if mounts else None


def _format_egress_rules(rules: tuple[EgressRule, ...]) -> str:
    rendered: list[str] = []
    for rule in rules:
        suffix = f":{rule.port}" if rule.port is not None else ""
        rendered.append(f"{rule.host}{suffix}")
    return ", ".join(rendered)


def _translate_to_os_native_plan(
    runtime_policy: dict[str, Any],
    capability: OsNativeCapability,
) -> tuple[OsNativePlan, EgressProxyConfig]:
    if (
        capability.bwrap_path is None
        or capability.proxy_path is None
        or capability.landlock_abi is None
    ):
        raise OsNativePlanRejected("complete bwrap/proxy/Landlock capability is required")
    mounts = tuple(
        _mount_from_policy_entry(entry, index)
        for index, entry in enumerate(runtime_policy.get("mount_manifest") or [])
        if isinstance(entry, dict)
    )
    if not mounts:
        raise OsNativePlanRejected("mount_manifest must include at least one os-native bind mount")
    workdir = _first_writable_mount(mounts)
    if workdir is None:
        raise OsNativePlanRejected("os-native workdir could not be resolved from mount_manifest")
    egress = translate_to_egress_proxy_config(runtime_policy)
    if not egress.no_egress:
        rules = _format_egress_rules(egress.rules)
        raise BackendUnavailable(
            "policy declares a non-empty egress allowlist but the os-native backend "
            "does not have a proven host proxy handoff for these rules; refusing before "
            f"sandbox start (allowlist: {rules})"
        )
    read_roots = tuple(dict.fromkeys(mount.source for mount in mounts))
    plan = OsNativePlan(
        bwrap_path=capability.bwrap_path,
        mounts=mounts,
        workdir=workdir,
        network="none",
        proxy_path=capability.proxy_path,
        landlock_abi=capability.landlock_abi,
        seccomp_filter=_seccomp_allow_filter(),
        env=(
            ("HOME", workdir),
            ("PATH", _DEFAULT_PATH),
            ("CE_EGRESS_MODE", "deny"),
            ("CE_EGRESS_PROXY", capability.proxy_path),
        ),
        read_roots=read_roots,
    )
    return plan, egress


class OsNativeBackend(RunnerBackend):
    """The unprivileged OS-native backend — bwrap/Landlock/seccomp fail-closed."""

    backend_key = BACKEND_KEY

    def __init__(
        self,
        *,
        capability_probe: CapabilityProbe | None = None,
        runner: OsNativeCommandRunner | None = None,
        openshell_backend_factory: OpenShellBackendFactory | None = None,
    ) -> None:
        self._capability_probe = capability_probe
        self._runner: OsNativeCommandRunner = (
            runner if runner is not None else SubprocessOsNativeRunner()
        )
        self._openshell_backend_factory = openshell_backend_factory or _default_openshell_backend
        self._capabilities: dict[str, OsNativeCapability] = {}
        self._plans: dict[str, OsNativePlan] = {}
        self._egress: dict[str, EgressProxyConfig] = {}
        self._delegations: dict[str, _OpenShellDelegation] = {}

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        # The deny surface (mapping + validate_runtime_policy → PolicyRejected) is
        # enforced by the RunnerBackend.provision template method before we get
        # here. A clean record reaches pure plan translation; all missing or
        # unsupported primitives fail closed before the live runner can start.
        egress = translate_to_egress_proxy_config(request.runtime_policy)
        if not egress.no_egress:
            delegated_backend = self._openshell_backend_factory()
            delegated_handle = delegated_backend.provision(request)
            record = request.runtime_policy
            policy_sha = record.get("policy_sha", "")
            handle = ProvisionedHandle(
                backend_key=self.backend_key,
                run_id=request.run_id,
                policy_sha=policy_sha if isinstance(policy_sha, str) else "",
                ref=f"os-native:openshell:{request.run_id}",
            )
            self._egress[handle.ref] = egress
            self._delegations[handle.ref] = _OpenShellDelegation(
                backend=delegated_backend,
                handle=delegated_handle,
            )
            return handle
        probe = self._capability_probe or probe_os_native_capability
        capability = probe()
        if not capability.available:
            raise BackendUnavailable(_unavailable_reason(capability))
        raise BackendUnavailable(_EXECUTION_CONTRACT_UNAVAILABLE_REASON)
        try:
            plan, egress = _translate_to_os_native_plan(request.runtime_policy, capability)
        except OsNativePlanRejected as exc:
            raise BackendUnavailable(f"invalid os-native sandbox plan: {exc}") from exc
        if not self._runner.available(capability):
            raise BackendUnavailable(
                "the probed os-native primitives are not available at launch time; "
                "refusing before sandbox start"
            )
        record = request.runtime_policy
        policy_sha = record.get("policy_sha", "")
        handle = ProvisionedHandle(
            backend_key=self.backend_key,
            run_id=request.run_id,
            policy_sha=policy_sha if isinstance(policy_sha, str) else "",
            ref=f"os-native:{request.run_id}",
        )
        self._capabilities[handle.ref] = capability
        self._plans[handle.ref] = plan
        self._egress[handle.ref] = egress
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        delegation = self._delegations.get(handle.ref)
        if delegation is not None:
            self._verify_delegated_p3(delegation)
            result = delegation.backend.run(delegation.handle, request)
            return RunResult(
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                started_ref=handle.ref,
                change_set=result.change_set,
                runtime_probe=result.runtime_probe,
            )
        plan = self._plans.get(handle.ref)
        if plan is None:
            raise BackendUnavailable(
                f"no provisioned os-native sandbox plan for handle {handle.ref!r}; "
                "refusing unproven handle"
            )
        if not request.command:
            raise BackendUnavailable("os-native run request command must not be empty")
        confinement = RunnerFsConfinement(workspace_read_roots=plan.read_roots)
        preexec_fn = landlock_preexec(confinement)
        try:
            with tempfile.TemporaryFile() as seccomp:
                seccomp.write(plan.seccomp_filter)
                seccomp.flush()
                seccomp.seek(0)
                fd = seccomp.fileno()
                argv = plan.bwrap_argv(request.command, seccomp_fd=fd)
                completed = self._runner.run(argv, preexec_fn=preexec_fn, pass_fds=(fd,))
        except OSError as exc:
            raise BackendUnavailable(f"failed to prepare os-native sandbox launch: {exc}") from exc
        return RunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            started_ref=handle.ref,
        )

    def _verify_delegated_p3(
        self,
        delegation: _OpenShellDelegation,
    ) -> None:
        if delegation.p3_verified:
            return
        probe_result = delegation.backend.run(
            delegation.handle,
            RunRequest(command=_P3_BLOCKED_PROBE_COMMAND),
        )
        if probe_result.exit_code != 0:
            raise BackendUnavailable(
                "OpenShell delegated egress P3 behavioral denial probe failed before "
                f"os-native run: probe exited {probe_result.exit_code}; refusing user command"
            )
        evidence = delegation.backend.collect(delegation.handle)
        if not _has_p3_denial(evidence.records):
            raise BackendUnavailable(
                "OpenShell delegated egress P3 behavioral denial probe produced no "
                f"DENIED OCSF evidence for {_P3_BLOCKED_TARGET}; refusing user command"
            )
        delegation.p3_verified = True

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        delegation = self._delegations.get(handle.ref)
        if delegation is not None:
            evidence = delegation.backend.collect(delegation.handle)
            records = (
                {
                    "backend_key": self.backend_key,
                    "mechanism": "openshell-delegated-egress",
                    "delegated_backend": delegation.handle.backend_key,
                    "delegated_ref": delegation.handle.ref,
                    "egress": "openshell",
                    "p3_behavioral_denial_verified": delegation.p3_verified,
                    "p3_blocked_target": _P3_BLOCKED_TARGET,
                },
                *evidence.records,
            )
            return CollectedEvidence(
                handle_ref=handle.ref,
                records=records,
                note=f"os-native delegated egress evidence for {handle.ref}",
                change_set=evidence.change_set,
            )
        capability = self._capabilities.get(handle.ref)
        plan = self._plans.get(handle.ref)
        egress = self._egress.get(handle.ref)
        records: tuple[dict[str, object], ...] = ()
        if capability is not None and plan is not None and egress is not None:
            records = (
                {
                    "backend_key": self.backend_key,
                    "mechanism": "bwrap+landlock+seccomp+proxy",
                    "platform": capability.platform_name,
                    "landlock_abi": capability.landlock_abi,
                    "seccomp_available": capability.seccomp_available,
                    "execution": "enabled",
                    "network": plan.network,
                    "egress": "deny" if egress.no_egress else "proxy",
                    "mounts": [
                        {"source": mount.source, "target": mount.target, "mode": mount.mode}
                        for mount in plan.mounts
                    ],
                },
            )
        return CollectedEvidence(
            handle_ref=handle.ref,
            records=records,
            note=f"os-native sandbox evidence for {handle.ref}",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        delegation = self._delegations.pop(handle.ref, None)
        if delegation is not None:
            result = delegation.backend.teardown(delegation.handle)
            self._egress.pop(handle.ref, None)
            return TeardownResult(handle_ref=handle.ref, released=result.released)
        self._capabilities.pop(handle.ref, None)
        self._plans.pop(handle.ref, None)
        self._egress.pop(handle.ref, None)
        return TeardownResult(handle_ref=handle.ref, released=True)


register_backend(BACKEND_KEY, OsNativeBackend)
