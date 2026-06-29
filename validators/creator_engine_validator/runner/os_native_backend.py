"""The unprivileged OS-native runner backend — user-elected, fail-closed.

This is the neutral-keyed (``os-native``) realization of #71's headline direction:
a daemonless, rootless backend (Linux ``bwrap`` + Landlock + seccomp + a host
deny-by-default proxy; Seatbelt on macOS as a later lane) that lets a user elect
the lowest-privilege tier of the RunnerBackend menu.

**Scope (deliberate, load-bearing): this slice ships SELECTION + CAPABILITY
PROBING + fail-closed refusal, NOT command execution.** OQ-1 Option A is ratified:
the Linux mechanism is ``bwrap`` + Landlock + seccomp + a deny-by-default egress
proxy, while ``gvisor-proxy`` remains the default backend. When the primitives are
not present, :meth:`_provision` refuses with :class:`BackendUnavailable`. When they
are present, this backend returns a governed scaffold handle so the selector path
can proceed; :meth:`run` still refuses until the full sandbox launch is wired.
This preserves CE's fail-closed posture: a selected-but-unbuilt backend never
silently downgrades to an unsandboxed run.

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
* **Zero I/O on import / no live side effect.** Importing allocates nothing; the
  fail-closed refusal is the only behavior, and it raises before any side effect.
* **Defensive.** This hardens CE's own agent runtime; it is never an offensive
  capability.
"""

from __future__ import annotations

import platform
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fs_mediation import landlock_abi_version
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

BACKEND_KEY = "os-native"

#: The ratified OQ-1 Option-A Linux primitives for the user-elected Tier-1
#: backend. They are probe-only prerequisites here, never auto-installed; that
#: keeps os-native zero-root and fail-closed.
LINUX_SANDBOX_PRIMITIVES: tuple[str, ...] = ("bwrap", "landlock", "seccomp", "proxy")

_EXECUTION_FOLLOWON_REASON = (
    "the 'os-native' backend capability probe passed, but full bwrap + Landlock + "
    "seccomp + deny-by-default proxy command execution is a follow-on; refusing to "
    "run a command rather than launching unsandboxed"
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


class OsNativeBackend(RunnerBackend):
    """The unprivileged OS-native backend — selectable, probed, and fail-closed."""

    backend_key = BACKEND_KEY

    def __init__(self, *, capability_probe: CapabilityProbe | None = None) -> None:
        self._capability_probe = capability_probe
        self._capabilities: dict[str, OsNativeCapability] = {}

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        # The deny surface (mapping + validate_runtime_policy → PolicyRejected) is
        # enforced by the RunnerBackend.provision template method before we get
        # here. A clean record reaches the OQ-1 capability probe. Missing or
        # unsupported primitives fail closed; a complete probe gets a scaffold
        # handle, but command execution remains refused until the full mechanism
        # launch is implemented.
        probe = self._capability_probe or probe_os_native_capability
        capability = probe()
        if not capability.available:
            raise BackendUnavailable(_unavailable_reason(capability))
        record = request.runtime_policy
        policy_sha = record.get("policy_sha", "")
        handle = ProvisionedHandle(
            backend_key=self.backend_key,
            run_id=request.run_id,
            policy_sha=policy_sha if isinstance(policy_sha, str) else "",
            ref=f"os-native-scaffold:{request.run_id}",
        )
        self._capabilities[handle.ref] = capability
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:  # pragma: no cover - unreachable until a live mechanism lands
        raise BackendUnavailable(_EXECUTION_FOLLOWON_REASON)

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        capability = self._capabilities.get(handle.ref)
        records: tuple[dict[str, object], ...] = ()
        if capability is not None:
            records = (
                {
                    "backend_key": self.backend_key,
                    "mechanism": "bwrap+landlock+seccomp+proxy",
                    "platform": capability.platform_name,
                    "landlock_abi": capability.landlock_abi,
                    "seccomp_available": capability.seccomp_available,
                    "execution": "follow-on",
                },
            )
        return CollectedEvidence(
            handle_ref=handle.ref,
            records=records,
            note=f"os-native scaffold evidence for {handle.ref}; execution follow-on",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        self._capabilities.pop(handle.ref, None)
        return TeardownResult(handle_ref=handle.ref, released=True)


register_backend(BACKEND_KEY, OsNativeBackend)
