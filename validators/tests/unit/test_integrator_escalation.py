"""Unit tests for ce-ops#216 Unit 4 integrator escalation seam."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from creator_engine_validator.forge import (
    EscalationContext,
    IntegratorEscalationRefused,
    ResolverResult,
    escalate_unresolved_results,
    escalation_for_result,
)


def _context() -> EscalationContext:
    return EscalationContext(
        repo="creator-engine/creator-engine",
        pr_number=377,
        head_ref="ce216-escalation-seam",
    )


def _unresolved_result() -> ResolverResult:
    return ResolverResult(
        resolver="versions_module_registry_union",
        applicable=True,
        resolved=False,
        unresolved=True,
        changed_paths=("validators/creator_engine_validator/_versions.py",),
        reason="registry entry changed or deleted relative to base; escalating as unresolved",
        evidence=("legacy_entry:missing_from=ours",),
    )


def test_unresolved_resolver_result_becomes_controller_escalation_event():
    event = escalation_for_result(
        _unresolved_result(),
        context=_context(),
        now=datetime(2026, 6, 23, 12, 34, 56, tzinfo=UTC),
    )

    assert event is not None
    assert event.kind == "integrator_controller_escalation"
    assert event.event_kind == "integrator_conflict_unresolved"
    assert event.severity == "controller_action_required"
    assert event.repo == "creator-engine/creator-engine"
    assert event.pr_number == 377
    assert event.head_ref == "ce216-escalation-seam"
    assert event.paths == ("validators/creator_engine_validator/_versions.py",)
    assert event.conflict_family == "versions_module_registry_union"
    assert event.resolver == "versions_module_registry_union"
    assert "registry entry changed or deleted" in event.resolver_reason
    assert event.resolver_evidence == ("legacy_entry:missing_from=ours",)
    assert event.created_at == "2026-06-23T12:34:56Z"

    assert event.to_dict() == {
        "kind": "integrator_controller_escalation",
        "event_kind": "integrator_conflict_unresolved",
        "severity": "controller_action_required",
        "repo": "creator-engine/creator-engine",
        "pr_number": 377,
        "head_ref": "ce216-escalation-seam",
        "paths": ["validators/creator_engine_validator/_versions.py"],
        "conflict_family": "versions_module_registry_union",
        "resolver": "versions_module_registry_union",
        "resolver_reason": "registry entry changed or deleted relative to base; escalating as unresolved",
        "resolver_evidence": ["legacy_entry:missing_from=ours"],
        "created_at": "2026-06-23T12:34:56Z",
    }


def test_resolved_or_not_applicable_results_do_not_escalate():
    resolved = ResolverResult(
        resolver="ce_carrier_non_overlapping_additions",
        applicable=True,
        resolved=True,
        unresolved=False,
        changed_paths=(".ce/changelog/a.md", ".ce/changelog/b.md"),
        reason="non-overlapping CE changelog/manifest additions unioned",
    )
    not_applicable = ResolverResult(
        resolver="none",
        applicable=False,
        resolved=False,
        unresolved=False,
        changed_paths=(),
        reason="unrecognized_conflict_family",
    )

    assert escalation_for_result(resolved, context=_context()) is None
    assert escalation_for_result(not_applicable, context=_context()) is None
    assert escalate_unresolved_results([resolved, not_applicable], context=_context()) == ()


def test_fold_turns_each_unresolved_result_into_explicit_escalation():
    second = ResolverResult(
        resolver="append_only_registry_union",
        applicable=True,
        resolved=False,
        unresolved=True,
        changed_paths=(".ce/registries/append-only.txt",),
        reason="overlapping append entries require semantic review",
        evidence=("overlap=same", "canonical_order=lexicographic"),
    )

    events = escalate_unresolved_results(
        [_unresolved_result(), second],
        context=_context(),
        now=datetime(2026, 6, 23, 0, 0, 0, tzinfo=UTC),
    )

    assert [event.conflict_family for event in events] == [
        "versions_module_registry_union",
        "append_only_registry_union",
    ]
    assert [event.paths for event in events] == [
        ("validators/creator_engine_validator/_versions.py",),
        (".ce/registries/append-only.txt",),
    ]


def test_unresolved_result_with_missing_controller_evidence_is_refused():
    malformed = ResolverResult(
        resolver="versions_module_registry_union",
        applicable=True,
        resolved=False,
        unresolved=True,
        changed_paths=(),
        reason="semantic review required",
    )

    with pytest.raises(IntegratorEscalationRefused, match="changed_paths"):
        escalation_for_result(malformed, context=_context())


def test_malformed_context_is_refused_before_event_creation():
    with pytest.raises(IntegratorEscalationRefused, match="repo"):
        escalation_for_result(
            _unresolved_result(),
            context=EscalationContext(repo=""),
        )
