"""The inert local / no-op runner backend (G-1.1).

:class:`LocalNoopBackend` implements the full :class:`RunnerBackend` lifecycle
WITHOUT touching a real runtime: it allocates no container, opens no socket, and
runs no subprocess. It exists so G-1.1 ships a runnable-but-inert backend behind
the adapter — exercised by tests and usable as a local stand-in until the live
gVisor + capability-separation-proxy backend lands at G-1.2.

It applies the G-1.0 deny surface at the boundary: ``provision`` refuses any
runtime-policy record that does not validate clean against
``schemas/runtime-policy.schema.yaml`` + the ``ce_runtime_policy`` predicates
(raises :class:`PolicyRejected`) — so the digest-pin / forbidden-mount /
names-only-secret / deny-by-default-egress denies stay load-bearing here.
"""

from __future__ import annotations

from pathlib import Path

from ..checks.ce_runtime_policy import validate_runtime_policy
from .backend import (
    CollectedEvidence,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunnerBackend,
    RunRequest,
    RunResult,
    TeardownResult,
    register_backend,
)

BACKEND_KEY = "local-noop"


class LocalNoopBackend(RunnerBackend):
    """An inert backend: records the lifecycle, touches no real runtime."""

    backend_key = BACKEND_KEY

    def provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        record = request.runtime_policy
        if not isinstance(record, dict):
            raise PolicyRejected("runtime_policy must be a mapping")
        errors = validate_runtime_policy(record, Path(f"<provision:{request.run_id}>"))
        if errors:
            rendered = "; ".join(error.format() for error in errors)
            raise PolicyRejected(
                f"runtime-policy did not validate clean; refusing to provision: {rendered}"
            )
        policy_sha = record.get("policy_sha", "")
        return ProvisionedHandle(
            backend_key=self.backend_key,
            run_id=request.run_id,
            policy_sha=policy_sha if isinstance(policy_sha, str) else "",
            ref=f"noop:{request.run_id}",
        )

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        # Inert: no command is executed. The command is echoed into stdout so a
        # caller can assert what WOULD have run, with a non-error exit code.
        return RunResult(
            exit_code=0,
            stdout=f"noop: would run {list(request.command)!r}",
            stderr="",
            started_ref=handle.ref,
        )

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        return CollectedEvidence(
            handle_ref=handle.ref,
            records=(),
            note=f"local-noop backend collected no live evidence for {handle.ref}",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        return TeardownResult(handle_ref=handle.ref, released=True)


register_backend(BACKEND_KEY, LocalNoopBackend)
