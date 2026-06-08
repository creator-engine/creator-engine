"""CE v3.5-A plane-C backend: OpenShell governed sandbox (A.1 — pure, green-now).

The second live-capable runner backend behind the G-1.1 ``RunnerBackend``
adapter: it translates a runtime-policy record (the G-1.0 contract) into an
**OpenShell** ``SandboxPolicy`` and drives OpenShell's create-then-exec sandbox
lifecycle (``CreateSandbox -> ExecSandbox -> WatchSandbox/OCSF -> DeleteSandbox``),
behind the ``openshell`` key the G-1.1 registry reserved from the start
(``runner/backend.py:187-189``). **This A.1 slice DEFINES the backend but does NOT
register it** — registration (which flips ``available_backends()``) moves to A.2
with the live client, so the existing registry-pinning tests stay green untouched.

Architectural fit (the NVIDIA-partnership arc, ``ce-openshell-integration-research``):
OpenShell is the *inner* runtime-safety grader at the kernel (Landlock + seccomp +
an external OPA egress proxy — "the grader lives outside the agent," realized);
CE stays the *outer* SDLC-correctness grader. They compose; they do not merge —
CE's binding gate stays external (consistent with the substrate ACP decision).

This is the **A.1** slice — PURE / GREEN-NOW. It ships:

* ``translate_to_sandbox_policy`` — a PURE policy translation (no I/O), the
  analog of the gVisor backend's ``translate_to_runsc_plan``; and
* a ``SandboxClient`` Protocol (the analog of the gVisor ``ContainerRunner``
  seam) with an in-memory ``FakeSandboxClient`` for tests and an inert default
  that honestly refuses (``BackendUnavailable``) because the live gRPC/SDK client
  is **A.2**.

LOAD-BEARING translate-vs-execute split (CI has no OpenShell daemon / no gRPC):

* ``translate_to_sandbox_policy`` is a **pure** function with NO side effects —
  fully unit-tested.
* All live work goes through the injectable ``SandboxClient`` seam: callers
  inject a fake; tests perform ZERO network/gRPC and importing this module
  performs no I/O and pulls in no ``grpcio``/``openshell`` dependency.
* The deny surface stays load-bearing at the boundary: ``provision`` refuses any
  runtime-policy record that does not validate clean (raises ``PolicyRejected``),
  exactly like the gVisor and noop backends.

Out of scope here (halt + amend if tempted): the real gRPC/SDK ``SandboxClient``
implementation and any ``grpcio``/``openshell`` dependency (-> **A.2**); token/
spend metering and the G-5 envelope wiring (-> **A.3 / v3.5-D**, the gap OpenShell
itself leaves open).

Defensive only — hardens our own agent runtime; never an offensive capability.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..checks.ce_runtime_policy import validate_runtime_policy
from .backend import (
    BackendUnavailable,
    CollectedEvidence,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunnerBackend,
    RunRequest,
    RunResult,
    TeardownResult,
)

BACKEND_KEY = "openshell"

#: The OpenShell release this backend is validated against. OpenShell is Alpha
#: ("single-player mode") and its gRPC API carries no compat guarantee yet
#: (v0.0.37 was a documented breaking release) — gate any upgrade behind an
#: explicit ``OPENSHELL_ACK_BREAKING_UPGRADE`` acknowledgement (A.2 wires the
#: live client; this pure slice only pins the version it models).
OPENSHELL_PINNED_VERSION = "v0.0.57"

# Policy-translation defaults (design-of-record §3; match the quickstart example).
DEFAULT_LANDLOCK_COMPATIBILITY = "best_effort"
DEFAULT_RUN_AS_USER = "sandbox"
DEFAULT_RUN_AS_GROUP = "sandbox"
#: Every translated endpoint is binding, not advisory.
ENDPOINT_ENFORCEMENT = "enforce"
#: CE's egress allowlist carries no HTTP-method dimension, so a listed host is
#: authorized for ordinary read+write traffic (model inference POSTs, package
#: GETs) but NOT raw tunnelling (``full``). The host allowlist itself — plus
#: "empty allowlist => no egress" — is the deny-by-default gate, not the method
#: level. A.2 may refine per-endpoint access once CE expresses L7 method policy.
DEFAULT_ENDPOINT_ACCESS = "read-write"

_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------------
# Pure translation output: the OpenShell SandboxPolicy (consumed in-process at
# create; no persistence boundary -> no schema, frozen like the gVisor plan).
# Models the four OpenShell policy domains (design-of-record §3): filesystem +
# process are locked at create (immutable); network is hot-reloadable.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FilesystemPolicy:
    """Directory allowlists (no globs at the FS layer; Landlock-enforced)."""

    include_workdir: bool
    read_only: tuple[str, ...]
    read_write: tuple[str, ...]


@dataclass(frozen=True)
class LandlockPolicy:
    compatibility: str  # "best_effort" | "hard_requirement"


@dataclass(frozen=True)
class ProcessPolicy:
    run_as_user: str
    run_as_group: str


@dataclass(frozen=True)
class Endpoint:
    """One allowed egress endpoint inside a network rule (OPA-proxy enforced)."""

    host: str
    port: int | None
    protocol: str | None
    enforcement: str  # "enforce" | "audit" — always "enforce" here
    access: str  # "read-only" | "read-write" | "full"


@dataclass(frozen=True)
class NetworkRule:
    """A named OpenShell ``network_policies`` entry (one per CE egress entry)."""

    name: str
    endpoints: tuple[Endpoint, ...]


@dataclass(frozen=True)
class SandboxPolicy:
    """An OpenShell sandbox policy translated from a CE runtime-policy record.

    Deny-by-default is the floor: an empty ``egress_allowlist`` yields empty
    ``network_policies`` (``no_egress``) — the OPA proxy then blocks all egress.
    ``image_ref`` is NOT carried here (it is assembled into the create-spec's
    ``template.image`` in ``provision``); ``policy_sha`` rides on the handle as
    provenance.
    """

    filesystem: FilesystemPolicy
    landlock: LandlockPolicy
    process: ProcessPolicy
    network_policies: tuple[NetworkRule, ...]

    @property
    def no_egress(self) -> bool:
        return not self.network_policies


@dataclass(frozen=True)
class SandboxCreateSpec:
    """The ``CreateSandbox`` spec: the translated policy + the digest-pinned image.

    The minimal create-spec this slice needs (design-of-record §2:
    ``SandboxSpec{ policy, template{image,...}, ... }``). ``image`` is the
    create-spec ``template.image`` assembled from the record's ``image_ref``.
    """

    policy: SandboxPolicy
    image: str  # template.image — digest-pinned "name@sha256:..."


# ---------------------------------------------------------------------------
# Pure translation function (no side effects; fully unit-tested)
# ---------------------------------------------------------------------------
def _network_rule_name(host: str, port: int | None, index: int) -> str:
    """Derive a deterministic, map-safe name for a network rule from its host."""
    base = host if port is None else f"{host}_{port}"
    slug = _NON_SLUG_RE.sub("_", base.lower()).strip("_")
    return slug or f"endpoint_{index}"


def translate_to_sandbox_policy(runtime_policy: dict[str, Any]) -> SandboxPolicy:
    """Translate a runtime-policy record into an OpenShell ``SandboxPolicy`` (pure).

    Mapping (deny-by-default preserved):

    * ``mount_manifest[]`` ro/rw entries -> ``filesystem.read_only[]`` /
      ``filesystem.read_write[]`` (directory paths); ``include_workdir`` honours
      an explicit field, defaulting to ``True``.
    * ``egress_allowlist[]`` -> one named ``network_policies`` rule per entry,
      each a single binding ``enforce`` endpoint; an EMPTY allowlist yields
      empty ``network_policies`` => ``no_egress`` (no egress at all).

    Landlock defaults to ``best_effort`` and the process runs as ``sandbox``
    (matching the OpenShell quickstart). ``image_ref`` and ``policy_sha`` are
    deliberately NOT modelled here (see :class:`SandboxPolicy`).
    """
    read_only: list[str] = []
    read_write: list[str] = []
    for entry in runtime_policy.get("mount_manifest") or []:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path", ""))
        if entry.get("mode") == "rw":
            read_write.append(path)
        else:
            read_only.append(path)

    filesystem = FilesystemPolicy(
        include_workdir=bool(runtime_policy.get("include_workdir", True)),
        read_only=tuple(read_only),
        read_write=tuple(read_write),
    )

    rules: list[NetworkRule] = []
    for index, entry in enumerate(runtime_policy.get("egress_allowlist") or []):
        if not isinstance(entry, dict):
            continue
        host = str(entry.get("host", ""))
        port = entry.get("port") if isinstance(entry.get("port"), int) else None
        protocol = entry.get("protocol") if isinstance(entry.get("protocol"), str) else None
        endpoint = Endpoint(
            host=host,
            port=port,
            protocol=protocol,
            enforcement=ENDPOINT_ENFORCEMENT,
            access=DEFAULT_ENDPOINT_ACCESS,
        )
        rules.append(NetworkRule(name=_network_rule_name(host, port, index), endpoints=(endpoint,)))

    return SandboxPolicy(
        filesystem=filesystem,
        landlock=LandlockPolicy(compatibility=DEFAULT_LANDLOCK_COMPATIBILITY),
        process=ProcessPolicy(run_as_user=DEFAULT_RUN_AS_USER, run_as_group=DEFAULT_RUN_AS_GROUP),
        network_policies=tuple(rules),
    )


def _image_ref_string(runtime_policy: dict[str, Any]) -> str:
    """Assemble the digest-pinned ``template.image`` string from ``image_ref``."""
    image = runtime_policy.get("image_ref") or {}
    name = image.get("name", "") if isinstance(image, dict) else ""
    sha = image.get("sha", "") if isinstance(image, dict) else ""
    return f"{name}@{sha}" if name and sha else str(name)


# OCSF decision fields surfaced into the evidence record (design-of-record §5).
_OCSF_DECISION_FIELDS = (
    "class_uid",
    "action",
    "disposition",
    "status",
    "status_detail",
    "firewall_rule",
)


def _map_ocsf_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map one OpenShell OCSF JSONL record into a CollectedEvidence record.

    Surfaces the load-bearing decision fields (``action: Allowed/Denied``,
    ``disposition``, ``status``; design-of-record §5) at the top level while
    preserving the full raw OCSF record under ``raw`` so the hash-chained
    evidence spine keeps complete fidelity.
    """
    mapped: dict[str, Any] = {
        field: record.get(field) for field in _OCSF_DECISION_FIELDS if field in record
    }
    mapped["raw"] = dict(record)
    return mapped


# ---------------------------------------------------------------------------
# Injectable sandbox-client seam (the A.2 gRPC/SDK boundary) + the test fake.
# Named after the OpenShell RPCs (design-of-record §2). NO gRPC/network here.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ExecOutcome:
    """The result of an ``ExecSandbox`` stream collapsed to its exit (§2)."""

    exit_code: int
    stdout: str
    stderr: str


class SandboxClient(Protocol):
    """The live-execution seam — the ONLY surface that will ever touch a real
    OpenShell gateway. The concrete gRPC/SDK implementation is A.2; this slice
    ships only the abstract Protocol + an in-memory fake.
    """

    def create_sandbox(self, spec: SandboxCreateSpec) -> str:
        """``CreateSandbox`` — provision a governed sandbox; return its id."""
        ...

    def exec_sandbox(
        self,
        sandbox_id: str,
        command: Sequence[str],
        *,
        workdir: str | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExecOutcome:
        """``ExecSandbox`` — run a command; return its collapsed exit outcome."""
        ...

    def collect_evidence(self, sandbox_id: str) -> Sequence[dict[str, Any]]:
        """Return the sandbox's raw OCSF/log records (design-of-record §5)."""
        ...

    def delete_sandbox(self, sandbox_id: str) -> bool:
        """``DeleteSandbox`` — tear the sandbox down; return whether released."""
        ...


class _UnwiredSandboxClient:
    """The default client: the live gRPC/SDK path is A.2, so every call honestly
    refuses (``BackendUnavailable``) rather than pretending to provision. Inject
    a real :class:`SandboxClient` (A.2) or a :class:`FakeSandboxClient` (tests).
    """

    _MESSAGE = (
        "the live OpenShell gRPC/SDK client is not wired yet (v3.5-A.2); "
        f"inject a SandboxClient (OpenShell {OPENSHELL_PINNED_VERSION})"
    )

    def create_sandbox(self, spec: SandboxCreateSpec) -> str:
        raise BackendUnavailable(self._MESSAGE)

    def exec_sandbox(
        self,
        sandbox_id: str,
        command: Sequence[str],
        *,
        workdir: str | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExecOutcome:
        raise BackendUnavailable(self._MESSAGE)

    def collect_evidence(self, sandbox_id: str) -> Sequence[dict[str, Any]]:
        raise BackendUnavailable(self._MESSAGE)

    def delete_sandbox(self, sandbox_id: str) -> bool:
        raise BackendUnavailable(self._MESSAGE)


class FakeSandboxClient:
    """An in-memory ``SandboxClient`` for tests — records calls, touches nothing.

    Returns a canned exec outcome and canned OCSF records so the full
    provision->run->collect->teardown lifecycle is exercised without a live
    gateway, gRPC wire, or network.
    """

    _DEFAULT_OCSF: tuple[dict[str, Any], ...] = (
        {
            "class_uid": 4001,
            "action": "Allowed",
            "disposition": "Allowed",
            "status": "Success",
            "firewall_rule": "model_provider_example_443",
        },
        {
            "class_uid": 4001,
            "action": "Denied",
            "disposition": "Blocked",
            "status": "Failure",
            "status_detail": "no matching policy",
        },
    )

    def __init__(
        self,
        *,
        sandbox_id: str = "openshell-sandbox-1",
        exit_code: int = 0,
        stdout: str = "ok",
        stderr: str = "",
        ocsf_records: Sequence[dict[str, Any]] | None = None,
        delete_released: bool = True,
    ) -> None:
        self._sandbox_id = sandbox_id
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr
        self._ocsf = tuple(ocsf_records) if ocsf_records is not None else self._DEFAULT_OCSF
        self._delete_released = delete_released
        self.created_specs: list[SandboxCreateSpec] = []
        self.exec_calls: list[tuple[str, tuple[str, ...]]] = []
        self.deleted: list[str] = []

    def create_sandbox(self, spec: SandboxCreateSpec) -> str:
        self.created_specs.append(spec)
        return self._sandbox_id

    def exec_sandbox(
        self,
        sandbox_id: str,
        command: Sequence[str],
        *,
        workdir: str | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExecOutcome:
        self.exec_calls.append((sandbox_id, tuple(command)))
        return ExecOutcome(exit_code=self._exit_code, stdout=self._stdout, stderr=self._stderr)

    def collect_evidence(self, sandbox_id: str) -> Sequence[dict[str, Any]]:
        return [dict(record) for record in self._ocsf]

    def delete_sandbox(self, sandbox_id: str) -> bool:
        self.deleted.append(sandbox_id)
        return self._delete_released


# ---------------------------------------------------------------------------
# The backend
# ---------------------------------------------------------------------------
class OpenShellBackend(RunnerBackend):
    """OpenShell governed-sandbox backend (pure translation + injected client)."""

    backend_key = BACKEND_KEY

    def __init__(self, client: SandboxClient | None = None) -> None:
        self._client: SandboxClient = client if client is not None else _UnwiredSandboxClient()
        #: handle.ref -> OpenShell sandbox_id
        self._sandboxes: dict[str, str] = {}

    def provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        record = request.runtime_policy
        if not isinstance(record, dict):
            raise PolicyRejected("runtime_policy must be a mapping")
        # Keep the G-1.0 deny surface load-bearing at the boundary.
        errors = validate_runtime_policy(record, Path(f"<provision:{request.run_id}>"))
        if errors:
            rendered = "; ".join(error.format() for error in errors)
            raise PolicyRejected(
                f"runtime-policy did not validate clean; refusing to provision: {rendered}"
            )
        # Pure translation (no side effects), then assemble the create-spec.
        policy = translate_to_sandbox_policy(record)
        spec = SandboxCreateSpec(policy=policy, image=_image_ref_string(record))
        # The only side effect: hand the create-spec to the injected client.
        sandbox_id = self._client.create_sandbox(spec)
        policy_sha = record.get("policy_sha", "")
        handle = ProvisionedHandle(
            backend_key=self.backend_key,
            run_id=request.run_id,
            policy_sha=policy_sha if isinstance(policy_sha, str) else "",
            ref=f"openshell:{request.run_id}",
        )
        self._sandboxes[handle.ref] = sandbox_id
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        sandbox_id = self._sandboxes.get(handle.ref, handle.ref)
        outcome = self._client.exec_sandbox(sandbox_id, request.command)
        return RunResult(
            exit_code=outcome.exit_code,
            stdout=outcome.stdout or "",
            stderr=outcome.stderr or "",
            started_ref=handle.ref,
        )

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        sandbox_id = self._sandboxes.get(handle.ref, handle.ref)
        raw = self._client.collect_evidence(sandbox_id)
        records = tuple(_map_ocsf_record(record) for record in raw if isinstance(record, dict))
        return CollectedEvidence(
            handle_ref=handle.ref,
            records=records,
            note=f"openshell backend evidence for {handle.ref} ({len(records)} OCSF records)",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        sandbox_id = self._sandboxes.pop(handle.ref, handle.ref)
        released = self._client.delete_sandbox(sandbox_id)
        return TeardownResult(handle_ref=handle.ref, released=bool(released))


# NOTE: A.1 deliberately does NOT call ``register_backend(BACKEND_KEY, ...)``.
# This slice *defines* the backend; **A.2 registers it** alongside the live
# gRPC/SDK client. Registering here would flip ``available_backends()`` and break
# the ~10 existing tests that pin the registry to ``("gvisor-proxy", "local-noop")``
# and assert ``openshell`` is unregistered — so registration + those test updates
# move together to A.2 (consistent with ``backend.py:187-189``: "registered by
# later slices"). Until then ``get_backend("openshell")`` correctly raises
# ``UnknownBackend``; callers instantiate ``OpenShellBackend`` directly.
