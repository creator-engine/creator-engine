"""Offline contained-controller parity validator for ce-ops#241.

The contained controller is accepted only when it demonstrates the same
controller capabilities as the host controller through injected seams. This
module is intentionally transport-free: it does not open sockets, spawn
subprocesses, or call Docker/runsc. Live adapters can implement the protocol,
but this validator exercises them through in-memory method calls only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


DEFAULT_REPO = "creator-engine/creator-engine"
DEFAULT_PR_NUMBER = 241
DEFAULT_HEAD_SHA = "f" * 40
DEFAULT_AMBIENT_ENV = {
    "GH_TOKEN": "ambient-gh-token",
    "GITHUB_TOKEN": "ambient-github-token",
    "PATH": "/usr/bin",
}
DEFAULT_INJECTED_CREDENTIAL = "mock-c2-gate-credential"
REQUIRED_OPERATOR_ATTACH_SURFACE = "launch-resume-herdr"
REQUIRED_DAEMONS = frozenset({"integrator", "review-pickup"})
FORBIDDEN_DISPATCH_ENV = frozenset(
    {
        "CONTROLLER_SOCKET",
        "CE_CONTROLLER_SOCKET",
        "HERDR_SOCKET",
        "HERDR_SOCKET_PATH",
    }
)
FORBIDDEN_TRANSPORT_FLAGS = frozenset({"docker", "runsc", "subprocess", "socket"})


class ParityValidationError(AssertionError):
    """Raised when a contained controller fails the parity contract."""


@dataclass(frozen=True)
class CapabilitySpec:
    """One required contained-controller parity capability."""

    capability_id: str
    title: str
    requirement: str
    evidence: str


@dataclass(frozen=True)
class TerminalReceipt:
    kind: str
    surface: str
    pane: str


@dataclass(frozen=True)
class DispatchReceipt:
    route: str
    terminal: TerminalReceipt
    seat_env: dict[str, str]


@dataclass(frozen=True)
class PullRequestGate:
    repo: str
    pr_number: int
    head_sha: str | None
    review_decision: str
    checks_state: str
    governed: bool
    author: str
    reviewer: str


@dataclass(frozen=True)
class MergeGateDecision:
    eligible: bool
    approved: bool
    enqueued: bool
    merged: bool
    head_pinned: bool
    refused_reason: str | None = None


@dataclass(frozen=True)
class DaemonSpec:
    name: str
    runnable: bool
    configurable: bool
    credential_handle: str
    credential_value: str | None = None


@dataclass(frozen=True)
class AttachSurface:
    plane: str
    surface: str
    visible: bool
    continuation_only: bool = False


@dataclass(frozen=True)
class CredentialInvocation:
    child_env: dict[str, str]
    argv: tuple[str, ...]
    input_text: str
    logs: str


@dataclass(frozen=True)
class ParityReport:
    capability_ids: tuple[str, ...]
    checked_denials: int
    daemon_names: tuple[str, ...]
    attach_surfaces: tuple[str, ...]


class ContainedController(Protocol):
    """Injected capability seam used by the offline parity validator."""

    def dispatch_to_seat(self, *, seat: str, task: str) -> DispatchReceipt:
        """Dispatch work to a governed seat without exposing controller sockets."""

    def hold_merge_gate(self, gate: PullRequestGate) -> MergeGateDecision:
        """Approve/enqueue only when the governed merge gate is satisfied."""

    def gate_daemons(self) -> tuple[DaemonSpec, ...]:
        """Return gate daemon specs without resolving live credentials."""

    def operator_attach_surfaces(self) -> tuple[AttachSurface, ...]:
        """Return operator attach surfaces visible through the reach plane."""

    def invoke_gate_with_credential(
        self,
        *,
        ambient_env: dict[str, str],
        injected_credential: str,
    ) -> CredentialInvocation:
        """Invoke the gate through an explicit credential injection seam."""

    def offline_probe(self) -> dict[str, bool]:
        """Report whether any live transport was used by the harness path."""


def capability_checklist() -> tuple[CapabilitySpec, ...]:
    """Return the ce-ops#241 contained-controller parity checklist."""

    return (
        CapabilitySpec(
            capability_id="dispatch.herdr_reach",
            title="Dispatch to seats through herdr/reach",
            requirement=(
                "Controller dispatches tasks to governed seats through the "
                "herdr/reach route and returns a terminal receipt without "
                "leaking controller socket handles into the seat environment."
            ),
            evidence="DispatchReceipt.route == 'herdr/reach' with terminal and seat env.",
        ),
        CapabilitySpec(
            capability_id="merge_gate.approve_enqueue",
            title="Governed merge gate approve/enqueue",
            requirement=(
                "Controller approves and enqueues only when the PR is governed, "
                "approved, green, head-pinned, and author != reviewer; it never "
                "directly merges in the parity harness."
            ),
            evidence="MergeGateDecision for positive and refused gate permutations.",
        ),
        CapabilitySpec(
            capability_id="gate_daemons.runnable_configurable",
            title="Gate daemons are runnable and configurable",
            requirement=(
                "Integrator and review-pickup gate daemons are advertised as "
                "runnable and configurable using credential handles, not secret values."
            ),
            evidence="DaemonSpec entries for required gate daemons.",
        ),
        CapabilitySpec(
            capability_id="operator_attach.a4_reach",
            title="Operator attach through A4 reach plane",
            requirement=(
                "Operator attach is available through the A4 reach plane on a "
                "visible launch-resume-herdr surface and is not continuation-only."
            ),
            evidence="AttachSurface with plane='A4', surface='launch-resume-herdr', and visible=True.",
        ),
        CapabilitySpec(
            capability_id="credentials.no_ambient_gate_secret",
            title="No ambient gate credential",
            requirement=(
                "Gate actions use an explicit injected or mocked credential seam; "
                "ambient GH_TOKEN/GITHUB_TOKEN values are not inherited as the gate "
                "credential, and no live secret appears in argv, input, logs, or specs."
            ),
            evidence="CredentialInvocation and DaemonSpec values are secret-free.",
        ),
        CapabilitySpec(
            capability_id="harness.offline_transport_free",
            title="Offline harness transport-free",
            requirement=(
                "Parity checks execute with injected controller calls only and "
                "perform no Docker, runsc, socket, or subprocess live transport."
            ),
            evidence="offline_probe reports all forbidden transport flags false.",
        ),
    )


def assert_checklist_conformance(
    checklist: tuple[CapabilitySpec, ...] | None = None,
) -> tuple[CapabilitySpec, ...]:
    """Validate that a checklist covers every required parity capability."""

    specs = checklist or capability_checklist()
    required = {
        "dispatch.herdr_reach",
        "merge_gate.approve_enqueue",
        "gate_daemons.runnable_configurable",
        "operator_attach.a4_reach",
        "credentials.no_ambient_gate_secret",
        "harness.offline_transport_free",
    }
    seen = {spec.capability_id for spec in specs}
    missing = sorted(required - seen)
    extra_empty = [spec.capability_id for spec in specs if not _spec_has_text(spec)]
    if missing:
        raise ParityValidationError(f"missing contained-controller capabilities: {missing}")
    if extra_empty:
        raise ParityValidationError(f"capability specs lack required text: {extra_empty}")
    return specs


def approved_gate(**overrides: Any) -> PullRequestGate:
    """Return a positive merge-gate fixture for offline parity checks."""

    base = dict(
        repo=DEFAULT_REPO,
        pr_number=DEFAULT_PR_NUMBER,
        head_sha=DEFAULT_HEAD_SHA,
        review_decision="APPROVED",
        checks_state="SUCCESS",
        governed=True,
        author="ce-dev-3",
        reviewer="ce-dev-4",
    )
    base.update(overrides)
    return PullRequestGate(**base)


def assert_contained_controller_parity(
    controller: ContainedController,
    *,
    ambient_env: dict[str, str] | None = None,
    injected_credential: str = DEFAULT_INJECTED_CREDENTIAL,
) -> ParityReport:
    """Assert every ce-ops#241 parity capability against a controller instance."""

    specs = assert_checklist_conformance()
    _validate_dispatch(controller)
    checked_denials = _validate_merge_gate(controller)
    daemon_names = _validate_gate_daemons(controller)
    attach_surfaces = _validate_operator_attach(controller)
    _validate_credential_seam(
        controller,
        ambient_env=ambient_env or DEFAULT_AMBIENT_ENV,
        injected_credential=injected_credential,
    )
    _validate_offline_probe(controller)
    return ParityReport(
        capability_ids=tuple(spec.capability_id for spec in specs),
        checked_denials=checked_denials,
        daemon_names=tuple(sorted(daemon_names)),
        attach_surfaces=tuple(sorted(attach_surfaces)),
    )


def _spec_has_text(spec: CapabilitySpec) -> bool:
    return all(
        isinstance(value, str) and bool(value.strip())
        for value in (spec.capability_id, spec.title, spec.requirement, spec.evidence)
    )


def _validate_dispatch(controller: ContainedController) -> None:
    dispatch = controller.dispatch_to_seat(seat="ce-dev-4", task="ce-ops#241 parity smoke")
    _require(dispatch.route == "herdr/reach", "dispatch route must be herdr/reach")
    _require(dispatch.terminal.kind in {"herdr", "tmux"}, "dispatch must return a terminal")
    _require(bool(dispatch.terminal.surface), "dispatch terminal surface is required")
    _require(bool(dispatch.terminal.pane), "dispatch terminal pane is required")
    leaked = sorted(FORBIDDEN_DISPATCH_ENV & set(dispatch.seat_env))
    _require(not leaked, f"dispatch leaked forbidden controller env keys: {leaked}")


def _validate_merge_gate(controller: ContainedController) -> int:
    allowed = controller.hold_merge_gate(approved_gate())
    _require(allowed.eligible, "approved governed green head-pinned PR must be eligible")
    _require(allowed.approved, "eligible PR must be approved by the gate")
    _require(allowed.enqueued, "eligible PR must be enqueued by the gate")
    _require(allowed.head_pinned, "eligible PR must be head-pinned")
    _require(not allowed.merged, "parity harness must not directly merge")

    denied_gates = (
        approved_gate(review_decision="REVIEW_REQUIRED"),
        approved_gate(checks_state="PENDING"),
        approved_gate(head_sha=None),
        approved_gate(governed=False),
        approved_gate(author="ce-dev-3", reviewer="ce-dev-3"),
    )
    for gate in denied_gates:
        decision = controller.hold_merge_gate(gate)
        _require(not decision.eligible, f"ineligible gate was accepted: {gate!r}")
        _require(not decision.approved, "ineligible gate must not approve")
        _require(not decision.enqueued, "ineligible gate must not enqueue")
        _require(not decision.merged, "ineligible gate must not merge")
    return len(denied_gates)


def _validate_gate_daemons(controller: ContainedController) -> set[str]:
    daemon_specs = {spec.name: spec for spec in controller.gate_daemons()}
    missing = sorted(REQUIRED_DAEMONS - set(daemon_specs))
    _require(not missing, f"missing gate daemons: {missing}")
    for spec in daemon_specs.values():
        _require(spec.runnable, f"gate daemon {spec.name!r} is not runnable")
        _require(spec.configurable, f"gate daemon {spec.name!r} is not configurable")
        _require(
            spec.credential_handle.startswith(("c2://", "mock://", "injected://")),
            f"gate daemon {spec.name!r} lacks injected credential handle",
        )
        _require(spec.credential_value is None, f"gate daemon {spec.name!r} exposes a secret")
    return set(daemon_specs)


def _validate_operator_attach(controller: ContainedController) -> set[str]:
    surfaces = controller.operator_attach_surfaces()
    visible = {
        surface.surface
        for surface in surfaces
        if surface.plane == "A4"
        and surface.surface == REQUIRED_OPERATOR_ATTACH_SURFACE
        and surface.visible
        and not surface.continuation_only
    }
    _require(
        visible,
        "operator attach must expose visible non-continuation A4 launch-resume-herdr surface",
    )
    return visible


def _validate_credential_seam(
    controller: ContainedController,
    *,
    ambient_env: dict[str, str],
    injected_credential: str,
) -> None:
    _require(bool(injected_credential), "injected credential must be non-empty")
    invocation = controller.invoke_gate_with_credential(
        ambient_env=dict(ambient_env),
        injected_credential=injected_credential,
    )
    _require(
        invocation.child_env.get("GH_TOKEN") == injected_credential,
        "gate invocation must use the injected credential",
    )
    _require("GITHUB_TOKEN" not in invocation.child_env, "ambient GITHUB_TOKEN must be stripped")
    ambient_gate_token = ambient_env.get("GH_TOKEN")
    _require(
        not ambient_gate_token or invocation.child_env.get("GH_TOKEN") != ambient_gate_token,
        "ambient GH_TOKEN must not be reused as the gate credential",
    )
    _require(
        all(injected_credential not in item for item in invocation.argv),
        "injected credential leaked into argv",
    )
    _require(injected_credential not in invocation.input_text, "injected credential leaked into input")
    _require(injected_credential not in invocation.logs, "injected credential leaked into logs")


def _validate_offline_probe(controller: ContainedController) -> None:
    probe = controller.offline_probe()
    _require(probe.get("injected") is True, "offline harness must use injected calls")
    live_flags = sorted(flag for flag in FORBIDDEN_TRANSPORT_FLAGS if probe.get(flag))
    _require(not live_flags, f"offline harness used forbidden live transport: {live_flags}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ParityValidationError(message)
