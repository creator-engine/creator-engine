"""Read-only workflow ratification registry for forge workflow artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class WorkflowCatalogEntry:
    """A cataloged governed workflow and its ratification state."""

    name: str
    purpose: str
    classification: str
    ratified: bool = False


_WORKFLOW_ENTRIES: tuple[WorkflowCatalogEntry, ...] = (
    WorkflowCatalogEntry(
        name="review-gate",
        purpose=(
            "route an authored change through independent review evidence and "
            "merge eligibility checks without letting the author ratify the work."
        ),
        classification=(
            "mixed. Review routing, check watching, stale-review detection, and "
            "return-to-author are autonomous when predicates hold. Merge, policy "
            "exception, guard weakening, release, deploy, and any "
            "missing-predicate override remain reserved."
        ),
    ),
    WorkflowCatalogEntry(
        name="harvest-preflight-pr",
        purpose=(
            "turn worker output into a governed delivery PR while preserving "
            "scope, evidence, and carrier discipline."
        ),
        classification=(
            "autonomous for ordinary in-scope delivery PR creation and updates. "
            "Reserved if the output requests broader paths, broader credentials, "
            "live settings, deploy, release, history rewrite, or a governance "
            "exception."
        ),
    ),
    WorkflowCatalogEntry(
        name="dispatch-watch-harvest",
        purpose=(
            "dispatch a role-shaped worker, monitor the run, and harvest only "
            "the authorized output."
        ),
        classification=(
            "autonomous when the dispatch is file-disjoint, role-scoped, and "
            "within the active run mode. Reserved if dispatch would broaden "
            "tool, credential, mount, egress, path, or policy authority."
        ),
    ),
    WorkflowCatalogEntry(
        name="autoreview-decide",
        purpose=(
            "decide whether automated review evidence can be routed, refreshed, "
            "or returned without treating automation as ratification."
        ),
        classification=(
            "mixed. Evidence collection, stale-state detection, and "
            "return-to-author are autonomous. Approval submission requires the "
            "reviewer authority predicates named by ADR-0013. Self-review, "
            "missing-envelope approval, policy exceptions, and merge overrides "
            "are reserved or refused."
        ),
    ),
    WorkflowCatalogEntry(
        name="trigger-triage-claim",
        purpose=(
            "map forge events into claimable work without letting the event "
            "itself authorize mutation."
        ),
        classification=(
            "autonomous for intake, territory mapping, claim-or-skip, and queue "
            "updates. Reserved if the trigger asks for privileged mutation, "
            "authority expansion, release, deploy, policy exception, or "
            "ambiguous high-consequence scope."
        ),
    ),
    WorkflowCatalogEntry(
        name="forge-setup-plan-apply",
        purpose=(
            "produce and, when ratified, apply a forge-side setup plan for "
            "branch protection, required checks, app permissions, workflow "
            "installation, reviewer identity, and rollback evidence."
        ),
        classification=(
            "mixed. Inventory, plan generation, readback, and refusal are "
            "autonomous. Live forge settings mutation, credential grants, "
            "branch-protection changes, app installation changes, release, and "
            "deploy are reserved."
        ),
    ),
    WorkflowCatalogEntry(
        name="resource-lock-queue",
        purpose=(
            "coordinate advisory locks and priority queues for forge artifacts "
            "such as issues, PRs, branches, workflows, and setup targets."
        ),
        classification=(
            "autonomous for advisory claim management and queue rendering. "
            "Reserved if a takeover would hide evidence, erase history, bypass "
            "dependency order, or grant broader authority than the requested "
            "workflow already has."
        ),
    ),
    WorkflowCatalogEntry(
        name="workflow-memory-proposal",
        purpose=(
            "convert retrospectives and run outcomes into proposed workflow, "
            "prompt, trigger, or guardrail changes without self-mutating the "
            "active system."
        ),
        classification=(
            "autonomous for collecting evidence and drafting proposals. Reserved "
            "for activating workflow changes, weakening guardrails, changing "
            "authority, broadening tools or credentials, or applying memory "
            "automatically."
        ),
    ),
)

WORKFLOW_REGISTRY: Mapping[str, WorkflowCatalogEntry] = MappingProxyType(
    {entry.name: entry for entry in _WORKFLOW_ENTRIES}
)


def is_ratified(name: str) -> bool:
    """Return whether a workflow is explicitly ratified; unknown names fail closed."""

    entry = WORKFLOW_REGISTRY.get(name)
    return bool(entry and entry.ratified)


def list_workflows() -> tuple[WorkflowCatalogEntry, ...]:
    """Return all cataloged workflows in catalog order."""

    return tuple(WORKFLOW_REGISTRY.values())


def get_workflow(name: str) -> WorkflowCatalogEntry | None:
    """Return a cataloged workflow by name, or ``None`` for unknown names."""

    return WORKFLOW_REGISTRY.get(name)


__all__ = [
    "WORKFLOW_REGISTRY",
    "WorkflowCatalogEntry",
    "get_workflow",
    "is_ratified",
    "list_workflows",
]
