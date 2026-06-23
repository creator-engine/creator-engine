"""Pure controller escalation events for unresolved integrator conflicts.

Unit 2 deterministic resolvers distinguish mechanical outcomes from semantic or
malformed conflicts. This module turns only unresolved resolver outputs into
structured controller-action events. It has no git, network, credential, or write
authority; callers own transport and persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable

from .deterministic_resolvers import ResolverResult

ESCALATION_KIND = "integrator_controller_escalation"
ESCALATION_EVENT_KIND = "integrator_conflict_unresolved"
ESCALATION_SEVERITY = "controller_action_required"


class IntegratorEscalationRefused(ValueError):
    """Raised when an unresolved resolver result lacks controller evidence."""


@dataclass(frozen=True)
class EscalationContext:
    """Repository/change identity attached to every controller escalation."""

    repo: str
    pr_number: int | None = None
    head_ref: str | None = None


@dataclass(frozen=True)
class ControllerEscalationEvent:
    """Structured, data-only event for controller action."""

    kind: str
    event_kind: str
    severity: str
    repo: str
    pr_number: int | None
    head_ref: str | None
    paths: tuple[str, ...]
    conflict_family: str
    resolver: str
    resolver_reason: str
    resolver_evidence: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "event_kind": self.event_kind,
            "severity": self.severity,
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_ref": self.head_ref,
            "paths": list(self.paths),
            "conflict_family": self.conflict_family,
            "resolver": self.resolver,
            "resolver_reason": self.resolver_reason,
            "resolver_evidence": list(self.resolver_evidence),
            "created_at": self.created_at,
        }


def escalation_for_result(
    result: ResolverResult,
    *,
    context: EscalationContext,
    now: datetime | None = None,
) -> ControllerEscalationEvent | None:
    """Return a controller event for one unresolved result, or ``None``.

    Mechanical/resolved/not-applicable outputs do not escalate. Any result marked
    unresolved must be evidence-complete enough for a controller to act, or this
    function refuses instead of silently parking it.
    """

    if not result.unresolved:
        return None
    _validate_context(context)
    paths = _validate_unresolved_result(result)
    created_at = _rfc3339(now or datetime.now(UTC))
    return ControllerEscalationEvent(
        kind=ESCALATION_KIND,
        event_kind=ESCALATION_EVENT_KIND,
        severity=ESCALATION_SEVERITY,
        repo=context.repo,
        pr_number=context.pr_number,
        head_ref=context.head_ref,
        paths=paths,
        conflict_family=result.resolver,
        resolver=result.resolver,
        resolver_reason=result.reason,
        resolver_evidence=tuple(str(item) for item in result.evidence),
        created_at=created_at,
    )


def escalate_unresolved_results(
    results: Iterable[ResolverResult],
    *,
    context: EscalationContext,
    now: datetime | None = None,
) -> tuple[ControllerEscalationEvent, ...]:
    """Fold resolver outputs into explicit controller escalations.

    Every unresolved result becomes one event. Malformed unresolved results
    raise :class:`IntegratorEscalationRefused`; resolved outputs are ignored.
    """

    effective_now = now or datetime.now(UTC)
    events: list[ControllerEscalationEvent] = []
    for result in results:
        event = escalation_for_result(result, context=context, now=effective_now)
        if event is not None:
            events.append(event)
    return tuple(events)


def _validate_context(context: EscalationContext) -> None:
    if not context.repo or not context.repo.strip():
        raise IntegratorEscalationRefused("repo is required for integrator escalation")
    if context.pr_number is not None and context.pr_number <= 0:
        raise IntegratorEscalationRefused("pr_number must be positive when provided")
    if context.head_ref is not None and not context.head_ref.strip():
        raise IntegratorEscalationRefused("head_ref must be non-empty when provided")


def _validate_unresolved_result(result: ResolverResult) -> tuple[str, ...]:
    if not result.applicable:
        raise IntegratorEscalationRefused("unresolved resolver result must be applicable")
    if result.resolved:
        raise IntegratorEscalationRefused("resolver result cannot be both resolved and unresolved")
    if not result.resolver or result.resolver == "none":
        raise IntegratorEscalationRefused("resolver/conflict family is required for unresolved escalation")
    if not result.reason or not result.reason.strip():
        raise IntegratorEscalationRefused("resolver reason is required for unresolved escalation")
    paths = tuple(str(path) for path in result.changed_paths)
    if not paths or any(not path.strip() for path in paths):
        raise IntegratorEscalationRefused("changed_paths are required for unresolved escalation")
    return paths


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
