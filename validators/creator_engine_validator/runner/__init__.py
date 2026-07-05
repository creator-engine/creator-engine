"""CE v3 runner-backend adapter — the thin runner abstraction (G-1.1, plane C).

This sub-package is the second slice of the v3 plane-C runtime: the small
lifecycle seam the (future, thin) orchestrator calls to run an agent seat inside
an isolation backend — ``provision -> run -> collect -> teardown`` — consuming a
runtime-policy record (the G-1.0 contract). See
``docs/contracts/runtime-policy.md`` and the secure-runtime architect report.

Design invariants (deliberate, load-bearing):

* **Not a validator check.** Nothing here is ``@register``-ed; importing this
  package registers no check and leaves ``--list-checks`` byte-identical.
* **Pure interface in G-1.1.** This slice ships the ABC, the
  provision/run/collect/teardown data model, the error hierarchy, the backend
  registry, and a single INERT backend (``LocalNoopBackend``). It allocates no
  container, opens no socket, runs no subprocess, and performs no network I/O on
  import. The live gVisor + capability-separation-proxy backend is G-1.2; an
  OpenShell backend is a fast-follow behind this same adapter.
* **Deny surface stays load-bearing.** ``LocalNoopBackend.provision`` refuses a
  runtime-policy record that does not validate clean against the G-1.0
  ``ce_runtime_policy`` predicates (raises ``PolicyRejected``).

This adapter may later be EXTRACTED into a standalone ``ce_orchestrator``
package on the architect's pre-committed trigger; until then it lives in the
installable validator package so the existing CI pytest job covers it.
"""

from __future__ import annotations

from .backend import (
    BackendAlreadyRegistered,
    BackendUnavailable,
    CollectedEvidence,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunChangeSet,
    RunnerBackend,
    RunnerError,
    RunRequest,
    RunResult,
    TeardownResult,
    UnknownBackend,
    available_backends,
    get_backend,
    register_backend,
)
from .noop_backend import BACKEND_KEY as LOCAL_NOOP_BACKEND_KEY
from .noop_backend import LocalNoopBackend
from .translation import (
    LAUNCH_PROBE_CONTRACT,
    LAUNCH_PROBE_CONTRACT_LABEL,
    LAUNCH_PROBE_RUN_ID_LABEL,
    argv_carries_launch_probe_contract,
    bind_launch_owned_probe_contract,
    launch_probe_container_name,
    render_mount,
)
from .gvisor_proxy_backend import BACKEND_KEY as GVISOR_PROXY_BACKEND_KEY
from .gvisor_proxy_backend import (
    ContainerRunner,
    EgressNotEnforceable,
    EgressProxyConfig,
    EgressRule,
    GvisorProxyBackend,
    MountSpec,
    RunscPlan,
    RunscPlanRejected,
    SubprocessContainerRunner,
    translate_to_egress_proxy_config,
    translate_to_runsc_plan,
)
from .docker_backend import BACKEND_KEY as DOCKER_BACKEND_KEY
from .docker_backend import (
    DockerBackend,
    DockerMountSpec,
    DockerPlan,
    DockerPlanRejected,
    SubprocessDockerRunner,
    translate_to_docker_plan,
)
from .os_native_backend import BACKEND_KEY as OS_NATIVE_BACKEND_KEY
from .os_native_backend import (
    LINUX_SANDBOX_PRIMITIVES,
    OsNativeCapability,
    OsNativeBackend,
    probe_os_native_capability,
)
from .openshell_backend import BACKEND_KEY as OPENSHELL_BACKEND_KEY
from .openshell_backend import (
    OPENSHELL_PINNED_VERSION,
    Endpoint,
    ExecOutcome,
    FakeSandboxClient,
    FilesystemPolicy,
    LandlockPolicy,
    NetworkRule,
    OpenShellBackend,
    ProcessPolicy,
    SandboxClient,
    SandboxCreateSpec,
    SandboxPolicy,
    SubprocessSandboxClient,
    render_sandbox_policy_yaml,
    translate_to_sandbox_policy,
)
from .ring1_tool_guard import (
    DEFAULT_SHIM_DIR,
    DENY_EXIT_CODE,
    Ring1GuardRuntime,
    Ring1ToolGuardConfig,
    build_runtime,
    guarded_env,
    render_install_script,
    render_posix_tool_shim,
)
from .audit_overlay import (
    ALLOWED,
    DENIED,
    ESCALATE,
    AuditOverlayBackend,
    Clock,
    CounterClock,
    EgressEvent,
    LifecycleEvent,
    MountEvent,
    SecretEvent,
    classify,
)

__all__ = [
    "ALLOWED",
    "AuditOverlayBackend",
    "Clock",
    "CounterClock",
    "DENIED",
    "DEFAULT_SHIM_DIR",
    "DENY_EXIT_CODE",
    "DOCKER_BACKEND_KEY",
    "ESCALATE",
    "DockerBackend",
    "DockerMountSpec",
    "DockerPlan",
    "DockerPlanRejected",
    "EgressEvent",
    "LifecycleEvent",
    "MountEvent",
    "SecretEvent",
    "classify",
    "BackendAlreadyRegistered",
    "BackendUnavailable",
    "CollectedEvidence",
    "ContainerRunner",
    "EgressNotEnforceable",
    "EgressProxyConfig",
    "EgressRule",
    "Endpoint",
    "ExecOutcome",
    "FakeSandboxClient",
    "FilesystemPolicy",
    "GVISOR_PROXY_BACKEND_KEY",
    "GvisorProxyBackend",
    "LAUNCH_PROBE_CONTRACT",
    "LAUNCH_PROBE_CONTRACT_LABEL",
    "LAUNCH_PROBE_RUN_ID_LABEL",
    "LINUX_SANDBOX_PRIMITIVES",
    "LOCAL_NOOP_BACKEND_KEY",
    "LandlockPolicy",
    "LocalNoopBackend",
    "MountSpec",
    "OS_NATIVE_BACKEND_KEY",
    "OsNativeCapability",
    "OsNativeBackend",
    "NetworkRule",
    "OPENSHELL_BACKEND_KEY",
    "OPENSHELL_PINNED_VERSION",
    "OpenShellBackend",
    "PolicyRejected",
    "ProcessPolicy",
    "ProvisionRequest",
    "ProvisionedHandle",
    "Ring1GuardRuntime",
    "Ring1ToolGuardConfig",
    "RunChangeSet",
    "RunRequest",
    "RunResult",
    "RunnerBackend",
    "RunnerError",
    "RunscPlan",
    "RunscPlanRejected",
    "SandboxClient",
    "SandboxCreateSpec",
    "SandboxPolicy",
    "SubprocessContainerRunner",
    "SubprocessDockerRunner",
    "SubprocessSandboxClient",
    "TeardownResult",
    "UnknownBackend",
    "available_backends",
    "argv_carries_launch_probe_contract",
    "bind_launch_owned_probe_contract",
    "build_runtime",
    "get_backend",
    "guarded_env",
    "launch_probe_container_name",
    "probe_os_native_capability",
    "register_backend",
    "render_install_script",
    "render_mount",
    "render_posix_tool_shim",
    "render_sandbox_policy_yaml",
    "translate_to_egress_proxy_config",
    "translate_to_docker_plan",
    "translate_to_runsc_plan",
    "translate_to_sandbox_policy",
]
