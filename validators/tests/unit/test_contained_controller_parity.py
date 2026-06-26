"""Unit coverage for the ce-ops#241 contained-controller parity validator."""
from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass, field
from typing import Any

import pytest

from creator_engine_validator.contained_controller_parity import (
    DEFAULT_HEAD_SHA,
    CapabilitySpec,
    CredentialInvocation,
    DaemonSpec,
    DispatchReceipt,
    MergeGateDecision,
    ParityValidationError,
    PullRequestGate,
    TerminalReceipt,
    approved_gate,
    assert_checklist_conformance,
    assert_contained_controller_parity,
    capability_checklist,
)


GATE_SECRET = "ghs_C2_SCOPED_GATE_SECRET"
AMBIENT_ENV = {
    "GH_TOKEN": "ambient-gh-token",
    "GITHUB_TOKEN": "ambient-github-token",
    "PATH": "/usr/bin",
}


@dataclass
class FakeContainedController:
    """Injected offline adapter for the production parity validator."""

    effects: list[dict[str, Any]] = field(default_factory=list)
    leak_ambient_credential: bool = False
    use_live_transport: bool = False
    wrong_attach_surface: bool = False

    def dispatch_to_seat(self, *, seat: str, task: str) -> DispatchReceipt:
        self.effects.append({"kind": "dispatch", "seat": seat, "task": task})
        return DispatchReceipt(
            route="herdr/reach",
            terminal=TerminalReceipt(
                kind="herdr",
                surface="launch-resume-herdr",
                pane="%17",
            ),
            seat_env={
                "CE_SEAT": seat,
                "CE_REACH_PLANE": "A4",
            },
        )

    def hold_merge_gate(self, gate: PullRequestGate) -> MergeGateDecision:
        head_pinned = gate.head_sha == DEFAULT_HEAD_SHA
        eligible = (
            gate.governed
            and gate.review_decision == "APPROVED"
            and gate.checks_state == "SUCCESS"
            and head_pinned
            and gate.author != gate.reviewer
        )
        if not eligible:
            return MergeGateDecision(
                eligible=False,
                approved=False,
                enqueued=False,
                merged=False,
                head_pinned=head_pinned,
                refused_reason="gate-ineligible",
            )
        self.effects.append(
            {
                "kind": "merge-gate",
                "repo": gate.repo,
                "pr_number": gate.pr_number,
                "head_sha": gate.head_sha,
                "actions": ("approve", "enqueue"),
            }
        )
        return MergeGateDecision(
            eligible=True,
            approved=True,
            enqueued=True,
            merged=False,
            head_pinned=True,
        )

    def gate_daemons(self) -> tuple[DaemonSpec, ...]:
        return (
            DaemonSpec(
                name="integrator",
                runnable=True,
                configurable=True,
                credential_handle="c2://gate/integrator",
            ),
            DaemonSpec(
                name="review-pickup",
                runnable=True,
                configurable=True,
                credential_handle="c2://gate/review-pickup",
            ),
        )

    def operator_attach_surfaces(self) -> tuple[Any, ...]:
        from creator_engine_validator.contained_controller_parity import AttachSurface

        return (
            AttachSurface(
                plane="A4",
                surface="other-a4-surface" if self.wrong_attach_surface else "launch-resume-herdr",
                visible=True,
            ),
        )

    def invoke_gate_with_credential(
        self,
        *,
        ambient_env: dict[str, str],
        injected_credential: str,
    ) -> CredentialInvocation:
        child_env = dict(ambient_env)
        child_env.pop("GITHUB_TOKEN", None)
        if self.leak_ambient_credential:
            child_env["GH_TOKEN"] = ambient_env["GH_TOKEN"]
        else:
            child_env["GH_TOKEN"] = injected_credential
        self.effects.append({"kind": "credential-injection", "handle": "c2://gate/integrator"})
        return CredentialInvocation(
            child_env=child_env,
            argv=("gh", "api", "repos/creator-engine/creator-engine/pulls/241"),
            input_text='{"sha":"ffffffffffffffffffffffffffffffffffffffff"}',
            logs="gate invocation used injected credential handle c2://gate/integrator",
        )

    def offline_probe(self) -> dict[str, bool]:
        self.effects.append({"kind": "offline-probe"})
        return {
            "injected": True,
            "docker": False,
            "runsc": False,
            "subprocess": self.use_live_transport,
            "socket": False,
        }


def test_checklist_covers_required_capabilities() -> None:
    checklist = assert_checklist_conformance()
    by_id = {spec.capability_id: spec for spec in checklist}

    assert set(by_id) == {
        "dispatch.herdr_reach",
        "merge_gate.approve_enqueue",
        "gate_daemons.runnable_configurable",
        "operator_attach.a4_reach",
        "credentials.no_ambient_gate_secret",
        "harness.offline_transport_free",
    }
    assert "herdr/reach" in by_id["dispatch.herdr_reach"].requirement
    assert "approved, green, head-pinned" in by_id["merge_gate.approve_enqueue"].requirement
    assert "author != reviewer" in by_id["merge_gate.approve_enqueue"].requirement
    assert "runnable and configurable" in by_id["gate_daemons.runnable_configurable"].requirement
    assert "A4 reach plane" in by_id["operator_attach.a4_reach"].requirement
    assert "launch-resume-herdr" in by_id["operator_attach.a4_reach"].requirement
    assert "explicit injected or mocked credential seam" in by_id[
        "credentials.no_ambient_gate_secret"
    ].requirement
    assert "Docker, runsc, socket, or subprocess" in by_id[
        "harness.offline_transport_free"
    ].requirement


def test_checklist_conformance_rejects_missing_capability() -> None:
    incomplete = tuple(
        spec for spec in capability_checklist() if spec.capability_id != "operator_attach.a4_reach"
    )

    with pytest.raises(ParityValidationError, match="missing contained-controller capabilities"):
        assert_checklist_conformance(incomplete)


def test_checklist_conformance_rejects_empty_spec_text() -> None:
    invalid = capability_checklist() + (
        CapabilitySpec(
            capability_id="invalid.empty",
            title="",
            requirement="missing title",
            evidence="missing title",
        ),
    )

    with pytest.raises(ParityValidationError, match="lack required text"):
        assert_checklist_conformance(invalid)


def test_contained_controller_parity_acceptance_harness_is_offline(monkeypatch) -> None:
    def explode(*_args: Any, **_kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("C3 parity harness must use injected fakes only")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)

    controller = FakeContainedController()
    report = assert_contained_controller_parity(
        controller,
        ambient_env=AMBIENT_ENV,
        injected_credential=GATE_SECRET,
    )

    assert report.checked_denials == 5
    assert report.daemon_names == ("integrator", "review-pickup")
    assert report.attach_surfaces == ("launch-resume-herdr",)
    assert effect_kinds(controller) == [
        "dispatch",
        "merge-gate",
        "credential-injection",
        "offline-probe",
    ]


def test_merge_gate_positive_and_denied_permutations_are_asserted() -> None:
    controller = FakeContainedController()

    allowed = controller.hold_merge_gate(approved_gate())
    assert allowed.eligible is True
    assert allowed.approved is True
    assert allowed.enqueued is True
    assert allowed.head_pinned is True
    assert allowed.merged is False

    denied = (
        approved_gate(review_decision="REVIEW_REQUIRED"),
        approved_gate(checks_state="PENDING"),
        approved_gate(head_sha=None),
        approved_gate(governed=False),
        approved_gate(author="ce-dev-3", reviewer="ce-dev-3"),
    )
    for gate in denied:
        decision = controller.hold_merge_gate(gate)
        assert decision.eligible is False
        assert decision.approved is False
        assert decision.enqueued is False
        assert decision.merged is False


def test_credential_seam_rejects_ambient_gate_token_reuse() -> None:
    controller = FakeContainedController(leak_ambient_credential=True)

    with pytest.raises(ParityValidationError, match="injected credential"):
        assert_contained_controller_parity(
            controller,
            ambient_env=AMBIENT_ENV,
            injected_credential=GATE_SECRET,
        )


def test_operator_attach_rejects_wrong_visible_a4_surface() -> None:
    controller = FakeContainedController(wrong_attach_surface=True)

    with pytest.raises(ParityValidationError, match="launch-resume-herdr"):
        assert_contained_controller_parity(
            controller,
            ambient_env=AMBIENT_ENV,
            injected_credential=GATE_SECRET,
        )


def test_offline_probe_rejects_live_transport_flags() -> None:
    controller = FakeContainedController(use_live_transport=True)

    with pytest.raises(ParityValidationError, match="forbidden live transport"):
        assert_contained_controller_parity(
            controller,
            ambient_env=AMBIENT_ENV,
            injected_credential=GATE_SECRET,
        )


def effect_kinds(controller: FakeContainedController) -> list[str]:
    return [effect["kind"] for effect in controller.effects]
