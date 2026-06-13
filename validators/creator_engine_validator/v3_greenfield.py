"""Pure greenfield first-project read model for the v3 onboard path.

E4 does not execute onboarding. The side-effecting scaffold/repo/App/protection
legs belong to E2's ``onboard_apply`` seam. This module folds those E2 facts into
the Frame->Ship first-project state and keeps the bootstrap scaffold distinct
from the first governed shipped change.
"""

from __future__ import annotations

import posixpath
import re
from typing import Any, Iterable, Mapping

__ce_version_line__ = "v3"

DEFAULT_SCAFFOLD_KIND = "minimal"
WORKSPACE_CHECKOUT_LEG = "workspace_checkout"
E2_SMOKE_SCOPE_ID = "ce-first-project-smoke"
E2_CONVERGENCE_LEGS: tuple[str, ...] = (
    "workspace_checkout",
    "github_repo_create",
    "github_app_install",
    "github_workflow_install",
    "github_branch_protection",
)
FRAME_TO_SHIP_KEYS: tuple[str, ...] = (
    "first_scope_filed",
    "first_scope_ratified",
    "first_build_spawned",
    "first_pr_opened",
    "first_review_recorded",
    "first_pr_merged",
)
_LOCAL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def project_name_from_repo(repo: Any) -> str | None:
    """Return the repo basename from an owner/name repo string."""
    if not isinstance(repo, str) or "/" not in repo:
        return None
    name = repo.rsplit("/", 1)[-1].strip()
    return name if _LOCAL_NAME_RE.match(name) else None


def resolve_project_name(values: Mapping[str, Any]) -> str | None:
    """Resolve the greenfield local project name, falling back to repo name."""
    explicit = values.get("project.name")
    if isinstance(explicit, str) and _LOCAL_NAME_RE.match(explicit.strip()):
        return explicit.strip()
    return project_name_from_repo(values.get("github.repo"))


def resolve_project_root(values: Mapping[str, Any]) -> str | None:
    """Compute ``<workspace-root>/<project-name>`` without touching the host."""
    name = resolve_project_name(values)
    if not name:
        return None
    workspace_root = values.get("host.workspace_root") or "~/ce-workspaces"
    root = str(workspace_root).rstrip("/")
    return posixpath.join(root, name)


def minimal_scaffold_input(project_root: str | None, *, kind: Any = None) -> dict[str, Any]:
    """The E4-owned scaffold content contract supplied to E2's workspace leg."""
    scaffold_kind = str(kind or DEFAULT_SCAFFOLD_KIND)
    return {
        "kind": scaffold_kind,
        "supplied_to_e2_leg": WORKSPACE_CHECKOUT_LEG,
        "project_root": project_root,
        "content": {
            "gitignore": [".ce/state", ".claude", ".codex", ".pytest_cache", "__pycache__"],
            "readme": "neutral-starter-text",
            "initial_commit": "bootstrap-only-not-first-ship",
        },
    }


def is_e4_first_scope(scope_id: Any, *, smoke_scope_ids: Iterable[str] = (E2_SMOKE_SCOPE_ID,)) -> bool:
    """True only for the human-shaped E4 Scope, never E2's smoke Scope."""
    if not isinstance(scope_id, str) or not scope_id:
        return False
    return scope_id not in set(smoke_scope_ids)


def frame_to_ship_state(
    evidence: Mapping[str, Any] | None = None,
    *,
    smoke_scope_ids: Iterable[str] = (E2_SMOKE_SCOPE_ID,),
) -> dict[str, bool]:
    """Fold verified first-project evidence into the E4-owned counters."""
    evidence = evidence or {}
    scope_id = evidence.get("scope_id")
    real_scope = is_e4_first_scope(scope_id, smoke_scope_ids=smoke_scope_ids)
    first_scope_filed = bool(real_scope and evidence.get("scope_filed"))
    first_scope_ratified = bool(first_scope_filed and evidence.get("scope_ratified"))
    first_build_spawned = bool(first_scope_ratified and evidence.get("build_spawned"))
    first_pr_opened = bool(first_build_spawned and evidence.get("pr_opened"))
    first_review_recorded = bool(first_pr_opened and evidence.get("review_recorded"))
    first_pr_merged = bool(first_review_recorded and evidence.get("pr_merged"))
    return {
        "first_scope_filed": first_scope_filed,
        "first_scope_ratified": first_scope_ratified,
        "first_build_spawned": first_build_spawned,
        "first_pr_opened": first_pr_opened,
        "first_review_recorded": first_review_recorded,
        "first_pr_merged": first_pr_merged,
    }


def fold_e2_convergence(e2_apply_result: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Read-through fold of E2 apply counters and leg verification facts."""
    if not e2_apply_result:
        return None
    legs = e2_apply_result.get("legs") or []
    by_id = {
        str(leg.get("id")): leg
        for leg in legs
        if isinstance(leg, Mapping) and leg.get("id") in E2_CONVERGENCE_LEGS
    }
    e2_counts = {
        key: e2_apply_result.get(key)
        for key in (
            "legs_total",
            "verified_count",
            "applied",
            "already_satisfied",
            "failed",
            "refused",
            "greenfield_repos_created",
            "repos_already_satisfied",
            "brownfield_deferred",
        )
        if key in e2_apply_result
    }
    facts: dict[str, Any] = {}
    for leg_id in E2_CONVERGENCE_LEGS:
        leg = by_id.get(leg_id) or {}
        verification = leg.get("verification") if isinstance(leg, Mapping) else {}
        verification = verification if isinstance(verification, Mapping) else {}
        facts[leg_id] = {
            "status": leg.get("status") if isinstance(leg, Mapping) else None,
            "verified": bool(verification.get("ok")),
            "verification": dict(verification),
        }
    return {"source": "e2_apply_result", "counts": e2_counts, "legs": facts}


def review_ship_agreement(evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Check whether review, merge, runtime, manifest, and report facts agree."""
    evidence = evidence or {}
    required = (
        "scope_id",
        "run_id",
        "pr_number",
        "review_evidence",
        "merge_evidence",
        "runtime_evidence",
        "manifest_evidence",
        "report_evidence",
    )
    missing = [key for key in required if not evidence.get(key)]
    pr_number = evidence.get("pr_number")
    review = evidence.get("review_evidence") or {}
    merge = evidence.get("merge_evidence") or {}
    mismatches: list[str] = []
    if isinstance(review, Mapping) and review.get("pr_number") not in (None, pr_number):
        mismatches.append("review_pr_number")
    if isinstance(merge, Mapping) and merge.get("pr_number") not in (None, pr_number):
        mismatches.append("merge_pr_number")
    return {"ok": not missing and not mismatches, "missing": missing, "mismatches": mismatches}


def build_first_project_plan(
    values: Mapping[str, Any],
    *,
    missing_keys: Iterable[str] = (),
    e2_plan_ref: str = "github_leg",
    e2_apply_result: Mapping[str, Any] | None = None,
    e2_apply_result_ref: str | None = None,
    frame_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build the greenfield first-project payload, or ``None`` when not new."""
    if values.get("github.mode") != "new":
        return None
    missing = sorted(set(str(key) for key in missing_keys))
    project_root = resolve_project_root(values)
    frame_state = frame_to_ship_state(frame_evidence)
    payload: dict[str, Any] = {
        "mode": "greenfield",
        "project_root": project_root,
        "scaffold_input": minimal_scaffold_input(
            project_root,
            kind=values.get("project.scaffold.kind", DEFAULT_SCAFFOLD_KIND),
        ),
        "e2_plan_ref": e2_plan_ref,
        "e2_apply_result_ref": e2_apply_result_ref,
        "e2_apply_required": e2_apply_result is None,
        "frame_to_ship": frame_state,
        "first_ship_not_yet_counted": not frame_state["first_pr_merged"],
        "missing_answers": missing,
    }
    e2_convergence = fold_e2_convergence(e2_apply_result)
    if e2_convergence is not None:
        payload["e2_convergence"] = e2_convergence
    return payload
