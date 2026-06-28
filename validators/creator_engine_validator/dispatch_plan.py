"""Dispatch plan composer for W8 forge-triage lane (ce-ops#42).

Consumes a TriageResult from forge_triage.plan_triage() and a seat list,
and emits a deterministic DispatchPlan: each triage-ready item gets a seat
assignment, a branch-name suggestion, and the sizing ceremony output.
This module is plan-only and makes NO mutations (no labels, no launches,
no forge calls).
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import forge_triage

DEFAULT_PICKUP_LABEL = forge_triage.DEFAULT_PICKUP_LABEL

_BRANCH_UNSAFE_RE = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True)
class DispatchPlanItem:
    """One triage-ready issue assigned to a governed seat plan."""

    issue: forge_triage.IssueCandidate
    arc_ticket: str
    work_class: str
    mutation_class: str
    sizing: Mapping[str, Any]
    seat: str | None
    suggested_branch: str
    pickup_label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "arc_ticket": self.arc_ticket,
            "issue": self.issue.to_dict(),
            "work_key": self.issue.work_key.work_key,
            "work_class": self.work_class,
            "mutation_class": self.mutation_class,
            "sizing": dict(self.sizing),
            "seat": self.seat,
            "suggested_branch": self.suggested_branch,
            "pickup_label": self.pickup_label,
        }


@dataclass(frozen=True)
class DispatchPlan:
    """A deterministic dry-run dispatch plan."""

    arc_ticket: str
    pickup_label: str
    items: tuple[DispatchPlanItem, ...]
    skipped: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "dispatch-plan",
            "arc_ticket": self.arc_ticket,
            "pickup_label": self.pickup_label,
            "count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "skipped_count": len(self.skipped),
            "skipped": [dict(item) for item in self.skipped],
        }


def plan_dispatch(
    *,
    arc_ticket: str,
    issues: Any,
    repo: str | None = None,
    pickup_label: str = DEFAULT_PICKUP_LABEL,
    assign_to: Sequence[str] = (),
) -> DispatchPlan:
    """Compose a deterministic dispatch plan from offline issue JSON."""

    triage = forge_triage.plan_triage(
        arc_ticket=arc_ticket,
        issues=issues,
        repo=repo,
        pickup_label=pickup_label,
    )
    seats = _normalize_seats(assign_to)
    items: list[DispatchPlanItem] = []
    for index, action in enumerate(triage.items):
        seat = seats[index % len(seats)] if seats else None
        items.append(
            DispatchPlanItem(
                issue=action.issue,
                arc_ticket=action.arc_ticket,
                work_class=action.work_class,
                mutation_class=action.mutation_class,
                sizing=dict(action.sizing),
                seat=seat,
                suggested_branch=_suggested_branch(action.issue),
                pickup_label=action.pickup_label,
            )
        )
    return DispatchPlan(
        arc_ticket=triage.arc_ticket,
        pickup_label=triage.pickup_label,
        items=tuple(items),
        skipped=triage.skipped,
    )


def _normalize_seats(assign_to: Sequence[str]) -> tuple[str, ...]:
    seats: list[str] = []
    seen: set[str] = set()
    for raw in assign_to or ():
        for part in str(raw).split(","):
            seat = part.strip()
            if seat and seat not in seen:
                seen.add(seat)
                seats.append(seat)
    return tuple(seats)


def _suggested_branch(issue: forge_triage.IssueCandidate) -> str:
    owner = issue.repo.split("/", 1)[0].lower()
    words = []
    for raw_word in issue.title.split():
        word = _BRANCH_UNSAFE_RE.sub("-", raw_word.lower()).strip("-")
        if word:
            words.append(word)
    slug = "-".join(words[:5]) or "issue"
    return f"{owner}-{issue.number}-{slug}"


__all__ = [
    "DEFAULT_PICKUP_LABEL",
    "DispatchPlan",
    "DispatchPlanItem",
    "plan_dispatch",
]
