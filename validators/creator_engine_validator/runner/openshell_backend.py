"""CE v3.5-A plane-C backend: OpenShell governed sandbox (A.2a — registered + wired).

The second live-capable runner backend behind the G-1.1 ``RunnerBackend``
adapter: it translates a runtime-policy record (the G-1.0 contract) into an
**OpenShell** ``SandboxPolicy`` and drives OpenShell's create-then-exec sandbox
lifecycle (``CreateSandbox -> ExecSandbox -> WatchSandbox/OCSF -> DeleteSandbox``),
behind the ``openshell`` key the G-1.1 registry reserved from the start
(``runner/backend.py:187-189``). **A.1 DEFINED this backend; A.2a (this slice)
REGISTERS it** (flipping ``available_backends()`` to the sorted 3-tuple) and wires
a live ``SandboxClient`` over the ``openshell sandbox`` CLI — kept IN this module
(mirroring how the gVisor backend keeps ``SubprocessContainerRunner`` in
``gvisor_proxy_backend.py``) so no new ``runner.*`` module enters the v3 runtime
surface. The recorded real run + its replayable evidence-bundle fixture are the
SEPARATE follow-on **A.2b**; token/spend metering is **A.3 / v3.5-D**.

Architectural fit (the NVIDIA-partnership arc, ``ce-openshell-integration-research``):
OpenShell is the *inner* runtime-safety grader at the kernel (Landlock + seccomp +
an external OPA egress proxy — "the grader lives outside the agent," realized);
CE stays the *outer* SDLC-correctness grader. They compose; they do not merge —
CE's binding gate stays external (consistent with the substrate ACP decision).

This slice ships, all green-now in CI (no live gateway, no new dependency):

* ``translate_to_sandbox_policy`` — a PURE policy translation (no I/O), the
  analog of the gVisor backend's ``translate_to_runsc_plan``;
* ``render_sandbox_policy_yaml`` — a PURE serializer of that policy into the
  OpenShell ``SandboxPolicy`` YAML the ``--policy`` flag consumes;
* ``parse_ocsf_textlog`` — a PURE OpenShell-OCSF-text-log-line -> dict parser
  (A.2b LIVE-VERIFIED: the audit surface is text over ``openshell logs``, NOT the
  empty JSONL sink; the live log read is the only I/O, isolated inside the client);
* a ``SandboxClient`` Protocol (the analog of the gVisor ``ContainerRunner``
  seam) with an in-memory ``FakeSandboxClient`` for tests, an inert default
  ``_UnwiredSandboxClient`` (the registered-but-not-auto-live posture: a
  default-constructed instance refuses at ``provision`` with ``BackendUnavailable``
  until a live client is injected), and ``SubprocessSandboxClient`` — the live
  transport over the ``openshell sandbox`` CLI (availability-gated; every live
  shell-out carries ``# pragma: no cover``).

LOAD-BEARING translate-vs-execute split (CI has no OpenShell daemon / no SDK):

* the pure functions above have NO side effects — fully unit-tested.
* All live work goes through the injectable ``SandboxClient`` seam: tests inject
  a fake; importing this module performs no I/O and pulls in no ``grpcio`` /
  ``openshell`` SDK (the gRPC/SDK transport is a deferred, dependency-gated later
  slice — the CLI rides the same gateway with zero new deps).
* The deny surface stays load-bearing at the boundary: ``provision`` refuses any
  runtime-policy record that does not validate clean (raises ``PolicyRejected``),
  exactly like the gVisor and noop backends.

Out of scope here (halt + amend if tempted): the A.2b recorded-run capture +
committed evidence-bundle fixture + offline replay test; a gRPC/SDK
``SandboxClient`` or any ``grpcio``/``openshell`` dependency (-> a deferred later
A.x); token/spend metering and the G-5 envelope (-> **A.3 / v3.5-D**, the gap
OpenShell itself leaves open).

Defensive only — hardens our own agent runtime; never an offensive capability.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

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
from .ring1_tool_guard import (
    DEFAULT_SHIM_DIR as DEFAULT_RING1_SHIM_DIR,
    Ring1GuardRuntime,
    Ring1ToolGuardConfig,
    build_runtime as build_ring1_runtime,
    render_install_script as render_ring1_install_script,
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
# CE egress is all-REST today; websocket is a future per-endpoint refinement;
# full/raw-tunnel endpoints omit the L7 axis.
DEFAULT_ENDPOINT_PROTOCOL = "rest"
DEFAULT_RING1_POSTURE_ROOT = "/runtime/worktree"

#: The OpenShell ``SandboxPolicy`` YAML schema version. The live v0.0.57 gateway
#: REQUIRES a top-level ``version`` (it is the one non-defaulted field in the
#: ``PolicyFile`` struct; A.2b verified ``version: 1`` against the gateway).
SANDBOX_POLICY_SCHEMA_VERSION = 1

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
    """One allowed egress endpoint inside a network rule (OPA-proxy enforced).

    Carries only what the live OpenShell ``NetworkEndpointDef`` consumes from CE's
    host:port allowlist: ``host`` + the optional ``port`` + the binding
    ``enforcement``/``access``. The OpenShell render carries ``protocol: rest``,
    the live-verified L7 value for CE's REST egress today. ``access: full``
    endpoints omit that L7 axis because raw tunnels are not expressible as
    OpenShell's ``rest``/``websocket`` enum; websocket is a future per-endpoint
    refinement once CE expresses such egress.
    """

    host: str
    port: int | None
    enforcement: str  # "enforce" | "audit" — always "enforce" here
    access: str  # "read-only" | "read-write" | "full"


@dataclass(frozen=True)
class NetworkRule:
    """A named OpenShell ``network_policies`` entry (one per CE egress entry).

    ``binaries`` carries the optional calling-binary scoping (the live
    ``NetworkPolicyRuleDef.binaries[{path}]``), populated from a CE egress rule's
    ``binary_identity`` when present (else empty → the rule applies to any binary).
    """

    name: str
    endpoints: tuple[Endpoint, ...]
    binaries: tuple[str, ...] = ()


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
        endpoint = Endpoint(
            host=host,
            port=port,
            enforcement=ENDPOINT_ENFORCEMENT,
            access=DEFAULT_ENDPOINT_ACCESS,
        )
        # CE's optional calling-binary identity -> the rule's binaries[{path}] scope.
        binary_identity = entry.get("binary_identity")
        binaries = (
            (str(binary_identity),)
            if isinstance(binary_identity, str) and binary_identity
            else ()
        )
        rules.append(
            NetworkRule(
                name=_network_rule_name(host, port, index),
                endpoints=(endpoint,),
                binaries=binaries,
            )
        )

    return SandboxPolicy(
        filesystem=filesystem,
        landlock=LandlockPolicy(compatibility=DEFAULT_LANDLOCK_COMPATIBILITY),
        process=ProcessPolicy(run_as_user=DEFAULT_RUN_AS_USER, run_as_group=DEFAULT_RUN_AS_GROUP),
        network_policies=tuple(rules),
    )


def render_sandbox_policy_yaml(policy: SandboxPolicy) -> str:
    """Serialize a :class:`SandboxPolicy` into the OpenShell SandboxPolicy YAML (pure).

    The on-the-wire form ``openshell sandbox create --policy <file>`` consumes,
    **LIVE-VERIFIED against OpenShell v0.0.57** (A.2b; the gateway's ``PolicyFile``
    struct uses ``deny_unknown_fields``, so the field names must be exact):

    * top-level ``version`` (REQUIRED — the one non-defaulted field);
    * ``filesystem_policy.{include_workdir, read_only, read_write}`` — note the key
      is ``filesystem_policy``, **not** ``filesystem`` (A.2b: the gateway rejects
      ``filesystem`` as an unknown field);
    * ``landlock.compatibility``;
    * ``process.{run_as_user, run_as_group}``;
    * ``network_policies`` as a **map keyed by rule name**, each value an OpenShell
      ``NetworkPolicyRuleDef``: ``name`` + an ``endpoints[]`` list (``host`` + the
      optional ``port`` + ``protocol: rest`` + the binding
      ``enforcement``/``access``; ``protocol`` is omitted only for ``access:
      full`` endpoints) + the optional ``binaries: [{path}]`` calling-binary
      scope.

    Deny-by-default is preserved on the wire: an EMPTY ``network_policies``
    (``no_egress``) serializes to an empty map ``{}`` — the OPA proxy then denies
    all egress. Deterministic (PyYAML ``sort_keys`` default; no insertion-order
    dependence) and side-effect-free, so it is unit-tested directly.
    """
    network_policies: dict[str, Any] = {}
    for rule in policy.network_policies:
        endpoints: list[dict[str, Any]] = []
        for endpoint in rule.endpoints:
            mapped: dict[str, Any] = {"host": endpoint.host}
            if endpoint.port is not None:
                mapped["port"] = endpoint.port
            if endpoint.access != "full":
                mapped["protocol"] = DEFAULT_ENDPOINT_PROTOCOL
            mapped["enforcement"] = endpoint.enforcement
            mapped["access"] = endpoint.access
            endpoints.append(mapped)
        rule_doc: dict[str, Any] = {"name": rule.name, "endpoints": endpoints}
        if rule.binaries:
            rule_doc["binaries"] = [{"path": path} for path in rule.binaries]
        network_policies[rule.name] = rule_doc

    document: dict[str, Any] = {
        "version": SANDBOX_POLICY_SCHEMA_VERSION,
        "filesystem_policy": {
            "include_workdir": policy.filesystem.include_workdir,
            "read_only": list(policy.filesystem.read_only),
            "read_write": list(policy.filesystem.read_write),
        },
        "landlock": {"compatibility": policy.landlock.compatibility},
        "process": {
            "run_as_user": policy.process.run_as_user,
            "run_as_group": policy.process.run_as_group,
        },
        "network_policies": network_policies,
    }
    return yaml.safe_dump(document, default_flow_style=False)


def _image_ref_string(runtime_policy: dict[str, Any]) -> str:
    """Assemble the digest-pinned ``template.image`` string from ``image_ref``."""
    image = runtime_policy.get("image_ref") or {}
    name = image.get("name", "") if isinstance(image, dict) else ""
    sha = image.get("sha", "") if isinstance(image, dict) else ""
    return f"{name}@{sha}" if name and sha else str(name)


# ---------------------------------------------------------------------------
# OpenShell OCSF audit surface = TEXT log lines (A.2b LIVE-VERIFIED).
#
# OpenShell v0.0.57 does NOT emit OCSF-v1.7.0 JSONL to a file: the
# ``ocsf_json_enabled`` JSONL sink stays EMPTY on this release (A.2b finding —
# the design-of-record §5 "JSONL at /var/log/openshell-ocsf.<date>.log" premise
# is wrong on the live gateway). The real, retrievable audit records are TEXT log
# lines over the gRPC log stream (``openshell logs --source all``) and the
# in-sandbox ``/var/log/openshell.<date>.log``, e.g. (verbatim, captured live)::
#
#   [1780982102.452] [sandbox] [OCSF ] [ocsf] NET:OPEN [MED] DENIED \
#       /usr/bin/curl(54) -> example.com:443 [policy:- engine:opa] \
#       [reason:endpoint example.com:443 is not allowed by any policy]
#
# Each OCSF line carries an ``EVENT:TYPE [SEVERITY] [ALLOWED|DENIED] <actor ->
# target> [policy:… engine:…] [reason:…]`` core (after any ``[epoch] [sandbox]
# [ocsf]`` prefix). ``parse_ocsf_textlog`` extracts those fields and
# ``_map_ocsf_record`` surfaces them into the evidence record.
# ---------------------------------------------------------------------------

#: One OCSF event core: ``EVENT:TYPE [SEVERITY] <rest>`` (matched anywhere in the
#: line, so any ``[epoch]/[sandbox]/[ocsf]`` prefix is skipped).
_OCSF_LINE_RE = re.compile(
    r"(?P<event>[A-Z][A-Z0-9_]*:[A-Z][A-Z0-9_]*)\s+\[(?P<severity>[A-Za-z0-9]+)\]\s*(?P<rest>.*)$"
)
#: A leading allow/deny disposition token on the event's remainder.
_OCSF_DISPOSITION_RE = re.compile(r"^(?P<disposition>ALLOWED|DENIED)\b\s*(?P<after>.*)$")
#: ``actor -> target`` (the NET:* connection lines).
_OCSF_ARROW_RE = re.compile(r"(?P<actor>\S+)\s+->\s+(?P<target>\S+)")
#: The bracketed ``policy:`` / ``engine:`` / ``reason:`` metadata.
_OCSF_POLICY_RE = re.compile(r"policy:(?P<policy>[^\s\]]+)")
_OCSF_ENGINE_RE = re.compile(r"engine:(?P<engine>[^\s\]]+)")
_OCSF_REASON_RE = re.compile(r"reason:(?P<reason>[^\]]+)")

#: Decision fields surfaced into the evidence record (A.2b live-verified format).
_OCSF_DECISION_FIELDS = (
    "event_type",
    "severity",
    "disposition",
    "actor",
    "target",
    "policy",
    "engine",
    "reason",
)


def parse_ocsf_textlog(text: str) -> list[dict[str, Any]]:
    """Parse OpenShell OCSF *text* log output into structured records (pure; no I/O).

    The A.2b-verified replacement for the (wrong) JSONL reader: OpenShell v0.0.57
    streams its OCSF audit as TEXT log lines (``openshell logs --source all`` /
    ``/var/log/openshell.<date>.log``), not JSONL. Each OCSF line carries an
    ``EVENT:TYPE [SEVERITY] [ALLOWED|DENIED] <actor -> target> [policy:… engine:…]
    [reason:…]`` core (after any ``[epoch] [sandbox] [ocsf]`` prefix). This is the
    pure line->record parser the live :meth:`SubprocessSandboxClient.collect_evidence`
    log read feeds into; the decision-field mapping into the evidence spine stays
    :func:`_map_ocsf_record`'s job, kept separate so this parser is unit-testable
    with no I/O.

    Only a line that carries an ``ocsf`` marker AND a parseable event core is
    surfaced; every other line (blank, non-OCSF, or unparseable) is skipped — log
    noise is never mis-parsed into the evidence chain. Each returned record keeps
    the full original line under ``raw`` for evidence-spine fidelity.
    """
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or "ocsf" not in stripped.lower():
            continue
        match = _OCSF_LINE_RE.search(stripped)
        if match is None:
            continue
        record: dict[str, Any] = {
            "event_type": match.group("event"),
            "severity": match.group("severity"),
            "raw": stripped,
        }
        rest = match.group("rest").strip()
        disposition = _OCSF_DISPOSITION_RE.match(rest)
        if disposition is not None:
            record["disposition"] = disposition.group("disposition")
            rest = disposition.group("after").strip()
        arrow = _OCSF_ARROW_RE.search(rest)
        if arrow is not None:
            record["actor"] = arrow.group("actor")
            record["target"] = arrow.group("target")
        for regex, key in (
            (_OCSF_POLICY_RE, "policy"),
            (_OCSF_ENGINE_RE, "engine"),
            (_OCSF_REASON_RE, "reason"),
        ):
            found = regex.search(stripped)
            if found is not None:
                record[key] = found.group(key).strip()
        records.append(record)
    return records


def _map_ocsf_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map one parsed OpenShell OCSF text record into a CollectedEvidence record.

    Surfaces the load-bearing decision fields (``disposition: ALLOWED/DENIED``,
    plus ``policy``/``engine``/``reason``/``target``; A.2b live-verified) at the
    top level while preserving the full parsed record (incl. the original ``raw``
    line) under ``raw`` so the hash-chained evidence spine keeps complete fidelity.
    """
    mapped: dict[str, Any] = {
        field: record[field] for field in _OCSF_DECISION_FIELDS if record.get(field) is not None
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
        preexec_fn: Callable[[], None] | None = None,
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
        preexec_fn: Callable[[], None] | None = None,
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

    #: Canned records in the live ``parse_ocsf_textlog`` output shape (A.2b format):
    #: one ALLOWED + one DENIED OCSF connection record.
    _DEFAULT_OCSF: tuple[dict[str, Any], ...] = (
        {
            "event_type": "NET:OPEN",
            "severity": "INFO",
            "disposition": "ALLOWED",
            "actor": "/usr/bin/curl(48)",
            "target": "api.github.com:443",
            "policy": "model_provider_example_443",
            "engine": "opa",
            "raw": "NET:OPEN [INFO] ALLOWED /usr/bin/curl(48) -> api.github.com:443 "
            "[policy:model_provider_example_443 engine:opa]",
        },
        {
            "event_type": "NET:OPEN",
            "severity": "MED",
            "disposition": "DENIED",
            "actor": "/usr/bin/curl(54)",
            "target": "example.com:443",
            "policy": "-",
            "engine": "opa",
            "reason": "endpoint example.com:443 is not allowed by any policy",
            "raw": "NET:OPEN [MED] DENIED /usr/bin/curl(54) -> example.com:443 "
            "[policy:- engine:opa] [reason:endpoint example.com:443 is not allowed by any policy]",
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
        self.exec_environments: list[dict[str, str] | None] = []
        self.exec_workdirs: list[str | None] = []
        self.exec_timeouts: list[int | None] = []
        self.exec_preexec_fns: list[Callable[[], None] | None] = []
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
        preexec_fn: Callable[[], None] | None = None,
    ) -> ExecOutcome:
        self.exec_calls.append((sandbox_id, tuple(command)))
        self.exec_environments.append(dict(environment) if environment is not None else None)
        self.exec_workdirs.append(workdir)
        self.exec_timeouts.append(timeout_seconds)
        self.exec_preexec_fns.append(preexec_fn)
        return ExecOutcome(exit_code=self._exit_code, stdout=self._stdout, stderr=self._stderr)

    def collect_evidence(self, sandbox_id: str) -> Sequence[dict[str, Any]]:
        return [dict(record) for record in self._ocsf]

    def delete_sandbox(self, sandbox_id: str) -> bool:
        self.deleted.append(sandbox_id)
        return self._delete_released


class SubprocessSandboxClient:
    """The live ``SandboxClient``: drives the ``openshell sandbox`` CLI via subprocess.

    Mirrors the gVisor ``SubprocessContainerRunner`` — the one surface that ever
    touches a real OpenShell gateway, kept IN this module so the backend adds no
    new ``runner.*`` module (and so the version_boundary surface stays untouched).
    Availability-gated (:meth:`available`); every live shell-out + the OCSF log
    read carries ``# pragma: no cover`` (CI has no ``openshell`` binary and runs
    none of it). NO ``grpcio``/``openshell`` SDK and no module-level network — the
    higher-fidelity gRPC/SDK transport is a deferred, dependency-gated later slice;
    the CLI rides the SAME gateway with zero new deps (consistent with the
    substrate ACP decision's "plain-subprocess is a permanent first-class floor").

    NOT the registered backend's default client — that stays ``_UnwiredSandboxClient``
    (the honest registered-but-not-auto-live posture); inject this explicitly (or
    via the A.2b-ii live harness) to drive a real gateway. The create-then-exec
    mapping + the OCSF collection are **A.2b-i LIVE-VERIFIED against OpenShell
    v0.0.57**: ``create`` needs a trailing command to return (it otherwise blocks
    on an interactive shell); ``exec`` has no ``--env`` flag (env is injected as an
    ``env K=V`` command prefix); the OCSF audit is TEXT over ``openshell logs``
    (the JSONL sink is empty on this release — see :func:`parse_ocsf_textlog`).
    """

    _BINARY = "openshell"
    #: Default number of log lines pulled when collecting OCSF evidence.
    _DEFAULT_LOG_LINES = 1000

    def __init__(self, binary: str = "openshell") -> None:
        self._binary = binary

    def available(self) -> bool:
        """True when the ``openshell`` CLI is on PATH (cheap; no side effect).

        A gateway-connected probe (``openshell status``) is intentionally left to
        the A.2b harness to keep this side-effect-free; the registered backend's
        default client is ``_UnwiredSandboxClient``, so this is never auto-invoked
        in CI.
        """
        return shutil.which(self._binary) is not None

    def _derive_sandbox_name(self, spec: SandboxCreateSpec) -> str:
        """A deterministic, content-derived sandbox name (the spec carries no run-id)."""
        digest = hashlib.sha256(
            f"{spec.image}\n{render_sandbox_policy_yaml(spec.policy)}".encode("utf-8")
        ).hexdigest()
        return f"ce-openshell-{digest[:12]}"

    def create_sandbox(self, spec: SandboxCreateSpec) -> str:  # pragma: no cover - requires a live OpenShell gateway
        name = self._derive_sandbox_name(spec)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="ce-openshell-policy-", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(render_sandbox_policy_yaml(spec.policy))
            policy_path = handle.name
        try:
            # A.2b live finding: `create` with no command drops into an interactive
            # shell and never returns. A trailing benign command (`-- true`) makes it
            # return while keeping the sandbox alive (no `--no-keep`) for `exec`.
            subprocess.run(
                [self._binary, "sandbox", "create", "--name", name, "--from", spec.image,
                 "--policy", policy_path, "--no-tty", "--", "true"],
                capture_output=True, text=True, check=True,
            )
        finally:
            Path(policy_path).unlink(missing_ok=True)
        return name

    def exec_sandbox(  # pragma: no cover - requires a live OpenShell gateway
        self,
        sandbox_id: str,
        command: Sequence[str],
        *,
        workdir: str | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
        preexec_fn: Callable[[], None] | None = None,
    ) -> ExecOutcome:
        argv = [self._binary, "sandbox", "exec", "-n", sandbox_id, "--no-tty"]
        if workdir is not None:
            argv += ["--workdir", workdir]
        if timeout_seconds is not None:
            argv += ["--timeout", str(timeout_seconds)]
        # A.2b live finding: `exec` has NO `--env` flag. Inject the environment as
        # an `env K=V …` command prefix (the POSIX `env` utility is present in the
        # base sandbox image; verified live).
        env_prefix: list[str] = []
        if environment:
            env_prefix = ["env", *(f"{key}={value}" for key, value in environment.items())]
        argv += ["--", *env_prefix, *command]
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            preexec_fn=preexec_fn,
        )
        return ExecOutcome(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

    def collect_evidence(self, sandbox_id: str) -> Sequence[dict[str, Any]]:  # pragma: no cover - reads the live OCSF text log
        # A.2b live finding: the OCSF JSONL sink stays empty on v0.0.57; the real
        # audit records are TEXT over the gRPC log stream. Pull the sandbox's log
        # (gateway + sandbox sources) and parse the OCSF decision lines out of it.
        completed = subprocess.run(
            [self._binary, "logs", sandbox_id, "-n", str(self._DEFAULT_LOG_LINES),
             "--source", "all"],
            capture_output=True, text=True, check=False,
        )
        return parse_ocsf_textlog(completed.stdout or "")

    def delete_sandbox(self, sandbox_id: str) -> bool:  # pragma: no cover - requires a live OpenShell gateway
        completed = subprocess.run(
            [self._binary, "sandbox", "delete", sandbox_id],
            capture_output=True, text=True, check=False,
        )
        return completed.returncode == 0


# ---------------------------------------------------------------------------
# The backend
# ---------------------------------------------------------------------------
class OpenShellBackend(RunnerBackend):
    """OpenShell governed-sandbox backend (pure translation + injected client)."""

    backend_key = BACKEND_KEY

    def __init__(
        self,
        client: SandboxClient | None = None,
        ring1_guard: Ring1ToolGuardConfig | None = None,
        ring1_posture_root: str | None = None,
        ring1_ledger_root: str | None = None,
    ) -> None:
        self._client: SandboxClient = client if client is not None else _UnwiredSandboxClient()
        self._ring1_guard = ring1_guard
        self._ring1_posture_root = ring1_posture_root
        self._ring1_ledger_root = ring1_ledger_root
        #: handle.ref -> OpenShell sandbox_id
        self._sandboxes: dict[str, str] = {}
        #: handle.ref -> installed Ring-1 guard runtime. Carries PATH-shim
        #: mediation for shell-level git/gh plus the Section-8c Landlock
        #: pre-exec hook required for the runner subprocess launch.
        self._guard_runtimes: dict[str, Ring1GuardRuntime] = {}

    @staticmethod
    def _default_ring1_posture_root(record: Mapping[str, Any]) -> str:
        mount_manifest = record.get("mount_manifest")
        if isinstance(mount_manifest, list):
            for entry in mount_manifest:
                if not isinstance(entry, dict) or entry.get("mode") != "rw":
                    continue
                mount_path = entry.get("path")
                justification = entry.get("write_justification")
                if not isinstance(mount_path, str) or not mount_path:
                    continue
                if (
                    mount_path == DEFAULT_RING1_POSTURE_ROOT
                    or mount_path.rstrip("/").endswith("/worktree")
                    or (
                        isinstance(justification, str)
                        and "worktree" in justification.lower()
                    )
                ):
                    return mount_path
        return DEFAULT_RING1_POSTURE_ROOT

    def _effective_ring1_guard(self, record: Mapping[str, Any]) -> Ring1ToolGuardConfig:
        if self._ring1_guard is not None:
            return self._ring1_guard
        posture_root = self._ring1_posture_root or self._default_ring1_posture_root(record)
        return Ring1ToolGuardConfig(posture_root=posture_root, ledger_root=self._ring1_ledger_root)

    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        # The G-1.0 deny surface (mapping + validate_runtime_policy → PolicyRejected)
        # is enforced by the RunnerBackend.provision template method before we get here.
        record = request.runtime_policy
        guard = self._effective_ring1_guard(record)
        runtime = build_ring1_runtime(guard, DEFAULT_RING1_SHIM_DIR)
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
        install = render_ring1_install_script(guard, runtime.shim_dir)
        outcome = self._client.exec_sandbox(sandbox_id, ("sh", "-c", install))
        if outcome.exit_code != 0:
            self._sandboxes.pop(handle.ref, None)
            self._guard_runtimes.pop(handle.ref, None)
            self._client.delete_sandbox(sandbox_id)
            detail = (outcome.stderr or outcome.stdout or "").strip()
            suffix = f": {detail}" if detail else ""
            raise BackendUnavailable(f"failed to install Ring-1 tool guard{suffix}")
        self._guard_runtimes[handle.ref] = runtime
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        sandbox_id = self._sandboxes.get(handle.ref, handle.ref)
        runtime = self._guard_runtimes.get(handle.ref)
        outcome = self._client.exec_sandbox(
            sandbox_id,
            request.command,
            environment=runtime.env if runtime is not None else None,
            preexec_fn=runtime.fs_preexec_fn if runtime is not None else None,
        )
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
        self._guard_runtimes.pop(handle.ref, None)
        released = self._client.delete_sandbox(sandbox_id)
        return TeardownResult(handle_ref=handle.ref, released=bool(released))


# A.2a REGISTERS the backend under the ``openshell`` key the G-1.1 registry
# reserved (``backend.py:187-189``: "registered by later slices"). This flips
# ``available_backends()`` to the sorted 3-tuple ``("gvisor-proxy", "local-noop",
# "openshell")`` and resolves ``get_backend("openshell")`` to an ``OpenShellBackend``;
# the ~10 registry-pinning tests A.1 deferred are updated to that 3-tuple in the
# same (A.2a) manifest. Registration adds NO validator check (``register_backend``
# is the BACKEND registry, not the ``@register`` check registry), so ``--list-checks``
# stays byte-identical. A default (registry-resolved) instance carries the inert
# ``_UnwiredSandboxClient`` and refuses at ``provision`` with ``BackendUnavailable``
# (the honest "registered but not auto-live in CI" posture, mirroring gVisor's
# availability gate) until a ``SubprocessSandboxClient`` (or the A.2b live harness)
# is injected. Mirrors ``gvisor_proxy_backend.py:289``.
register_backend(BACKEND_KEY, OpenShellBackend)
