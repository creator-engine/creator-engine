"""Plan-only reviewer triage.

This module is deliberately offline: it consumes explicit PR facts and tracked
repo policy data, then emits a reviewer-triage decision record. It never sends a
review request, mints an envelope, launches a venue, or calls a source host.
"""
from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .loader import load_yaml

NON_AUTHORITY_STATEMENT = (
    "Reviewer triage assigns review only; it does not approve, ratify, merge, or waive policy."
)
PRIVILEGED_MUTATION_CLASSES = frozenset({
    "deploy",
    "governance",
    "identity",
    "security",
    "attestation",
    "redaction",
})


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _clean_owner(owner: str) -> str:
    owner = owner.strip()
    if owner.startswith("@"):
        owner = owner[1:]
    if "/" in owner:
        owner = owner.rsplit("/", 1)[-1]
    return owner


def _path_matches(pattern: str, path: str) -> bool:
    pattern = pattern.strip()
    if not pattern:
        return False
    if pattern == "*":
        return True
    if pattern.endswith("/"):
        pattern = f"{pattern}**"
    if pattern.startswith("/"):
        pattern = pattern[1:]
    return fnmatch.fnmatch(path, pattern)


def _any_path_matches(patterns: list[str], changed_paths: list[str]) -> bool:
    if not changed_paths:
        return True
    return any(_path_matches(pattern, path) for pattern in patterns for path in changed_paths)


def _codeowners_candidates(codeowners_text: str, changed_paths: list[str]) -> list[str]:
    candidates: list[str] = []
    for raw in codeowners_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern, owners = parts[0], parts[1:]
        if not _any_path_matches([pattern], changed_paths):
            continue
        for owner in owners:
            clean = _clean_owner(owner)
            if clean and clean not in candidates:
                candidates.append(clean)
    return candidates


def _coordination_area_refs(policy: dict[str, Any] | None, changed_paths: list[str]) -> list[str]:
    if not isinstance(policy, dict):
        return []
    authority = policy.get("ratification_authority")
    if not isinstance(authority, dict):
        return []
    area_owners = authority.get("area_owners")
    if not isinstance(area_owners, dict):
        return []
    refs: list[str] = []
    for pattern, owners in area_owners.items():
        if not _any_path_matches([str(pattern)], changed_paths):
            continue
        for owner in _as_list(owners):
            owner_s = str(owner)
            if owner_s not in refs:
                refs.append(owner_s)
    return refs


def _reviewers(registry: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(registry, dict):
        return []
    reviewers = registry.get("reviewers")
    return reviewers if isinstance(reviewers, list) else []


def _identity_values(reviewer: dict[str, Any], key: str) -> list[str]:
    identities = reviewer.get("source_host_identities")
    if not isinstance(identities, dict):
        return []
    return [str(v) for v in _as_list(identities.get(key))]


def _candidate_record(candidate: str, reviewers: list[dict[str, Any]]) -> dict[str, Any] | None:
    for reviewer in reviewers:
        if not isinstance(reviewer, dict):
            continue
        values = {
            str(reviewer.get("reviewer_id", "")),
            *_identity_values(reviewer, "logins"),
            *_identity_values(reviewer, "teams"),
            *_identity_values(reviewer, "bot_slugs"),
            *[str(v) for v in _as_list(reviewer.get("ownership", {}).get("area_owner_refs") if isinstance(reviewer.get("ownership"), dict) else [])],
        }
        if candidate in values:
            return reviewer
    return None


def _candidate_id(candidate: str, reviewer: dict[str, Any] | None) -> str:
    if reviewer is None:
        return candidate
    return str(reviewer.get("reviewer_id") or candidate)


def _has_source_host_review_permission(reviewer: dict[str, Any]) -> bool:
    identities = reviewer.get("source_host_identities")
    if not isinstance(identities, dict):
        return False
    return any(_as_list(identities.get(key)) for key in ("logins", "teams", "app_installation_ids", "bot_slugs"))


def _is_owner_for_paths(reviewer: dict[str, Any], changed_paths: list[str], codeowners: list[str], area_refs: list[str]) -> bool:
    ownership = reviewer.get("ownership")
    if not isinstance(ownership, dict):
        return False
    logins = set(_identity_values(reviewer, "logins"))
    teams = set(_identity_values(reviewer, "teams"))
    if (logins | teams).intersection(codeowners) and _any_path_matches(
        [str(p) for p in _as_list(ownership.get("path_globs"))], changed_paths
    ):
        return True
    if set(str(ref) for ref in _as_list(ownership.get("area_owner_refs"))).intersection(area_refs):
        return True
    return False


def _capability_allows(reviewer: dict[str, Any], mutation_classes: list[str], risk_tier: str) -> list[str]:
    capabilities = reviewer.get("capabilities")
    if not isinstance(capabilities, dict):
        return ["missing_capabilities"]
    reasons: list[str] = []
    allowed_classes = set(str(v) for v in _as_list(capabilities.get("mutation_classes")))
    if allowed_classes and not set(mutation_classes).issubset(allowed_classes):
        reasons.append("mutation_class_not_allowed")
    allowed_risks = set(str(v) for v in _as_list(capabilities.get("risk_tiers")))
    if allowed_risks and risk_tier not in allowed_risks:
        reasons.append("risk_tier_not_allowed")
    return reasons


def _availability(reviewer: dict[str, Any] | None, reviewer_id: str) -> dict[str, Any]:
    if reviewer is None:
        return {"reviewer_id": reviewer_id, "available": False, "reasons": ["missing_reviewer_registry_record"]}
    availability = reviewer.get("availability")
    if not isinstance(availability, dict):
        return {"reviewer_id": reviewer_id, "available": False, "reasons": ["missing_availability"]}
    reasons: list[str] = []
    status = str(availability.get("status", "available"))
    if status != "available":
        reasons.append(f"availability_status_{status}")
    active = availability.get("active_reviews", 0)
    max_active = availability.get("max_active_reviews")
    if isinstance(active, int) and isinstance(max_active, int) and active >= max_active:
        reasons.append("max_active_reviews_reached")
    return {"reviewer_id": reviewer_id, "available": not reasons, "reasons": reasons}


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def plan_reviewer_triage(
    *,
    repo: str,
    pr_number: int,
    head_sha: str,
    expected_head_sha: str | None,
    author_run_id: str,
    author_identity: dict[str, Any],
    last_pusher: dict[str, Any] | None,
    changed_paths: list[str],
    mutation_classes: list[str],
    risk_tier: str,
    codeowners_text: str,
    coordination_policy: dict[str, Any] | None,
    registry: dict[str, Any] | None,
    ruleset_required_teams: list[str] | None = None,
) -> dict[str, Any]:
    reviewers = _reviewers(registry)
    codeowners = _codeowners_candidates(codeowners_text, changed_paths)
    area_refs = _coordination_area_refs(coordination_policy, changed_paths)

    registry_path_candidates: list[str] = []
    for reviewer in reviewers:
        if not isinstance(reviewer, dict):
            continue
        ownership = reviewer.get("ownership")
        if isinstance(ownership, dict) and _any_path_matches(
            [str(p) for p in _as_list(ownership.get("path_globs"))], changed_paths
        ):
            registry_path_candidates.append(str(reviewer.get("reviewer_id", "")))

    raw_candidates = _dedupe([*codeowners, *area_refs, *registry_path_candidates])
    required_teams = set(ruleset_required_teams or [])
    author_human = author_identity.get("human_id")
    author_login = author_identity.get("login")
    author_controller = author_identity.get("controller_id")
    author_venue = author_identity.get("venue_id")
    last_pusher_human = last_pusher.get("human_id") if isinstance(last_pusher, dict) else None

    eligibility_results: list[dict[str, Any]] = []
    availability_results: list[dict[str, Any]] = []
    candidate_records: dict[str, dict[str, Any] | None] = {}
    for candidate in raw_candidates:
        reviewer = _candidate_record(candidate, reviewers)
        reviewer_id = _candidate_id(candidate, reviewer)
        candidate_records[reviewer_id] = reviewer
        reasons: list[str] = []
        identity_ref = ""
        human_id = ""
        if reviewer is None:
            reasons.append("missing_ratified_reviewer_identity")
        else:
            identity_ref = str(reviewer.get("identity_ref") or "")
            human_id = str(reviewer.get("human_id") or "")
            if not identity_ref or not human_id:
                reasons.append("missing_ratified_reviewer_identity")
            if not _has_source_host_review_permission(reviewer):
                reasons.append("missing_source_host_review_counting_permission")
            if required_teams and not required_teams.issubset(set(_identity_values(reviewer, "teams"))):
                reasons.append("missing_required_ruleset_team")
            if repo not in set(str(v) for v in _as_list(reviewer.get("allowed_repositories"))):
                reasons.append("repo_not_allowed")
            reasons.extend(_capability_allows(reviewer, mutation_classes, risk_tier))
            if not _is_owner_for_paths(reviewer, changed_paths, codeowners, area_refs):
                reasons.append("not_owner_for_changed_paths")
            if human_id and author_human and human_id == author_human:
                reasons.append("same_human_as_author")
            if human_id and last_pusher_human and human_id == last_pusher_human:
                reasons.append("same_human_as_last_pusher")
            if author_login and author_login in _identity_values(reviewer, "logins"):
                reasons.append("same_login_as_author")
            if author_controller and author_controller == reviewer.get("controller_id"):
                reasons.append("same_controller_as_author")
            if author_venue and author_venue == reviewer.get("venue_id"):
                reasons.append("same_venue_as_author")
        eligibility_results.append({
            "reviewer_id": reviewer_id,
            "eligible": not reasons,
            "reasons": reasons,
            "identity_ref": identity_ref,
            "human_id": human_id,
        })
        availability_results.append(_availability(reviewer, reviewer_id))

    eligible = {r["reviewer_id"] for r in eligibility_results if r["eligible"]}
    available = {r["reviewer_id"] for r in availability_results if r["available"]}
    selected: list[str] = []
    selected_refs: list[str] = []
    escalation_status = "none"
    escalation_reason = "none"

    if expected_head_sha and expected_head_sha != head_sha:
        escalation_status = "operator"
        escalation_reason = "head_sha_mismatch"
    elif risk_tier == "privileged" or PRIVILEGED_MUTATION_CLASSES.intersection(mutation_classes):
        escalation_status = "operator"
        escalation_reason = "privileged_requires_source"
    else:
        selectable = sorted(eligible.intersection(available))
        if selectable:
            selected = [selectable[0]]
            reviewer = candidate_records.get(selected[0])
            selected_refs = [str(reviewer.get("identity_ref"))] if isinstance(reviewer, dict) else []
        else:
            escalation_status = "operator"
            escalation_reason = "no_eligible_available_reviewer"

    return {
        "kind": "reviewer-triage-decision",
        "schema_version": "1",
        "work_ref": {
            "repo": repo,
            "pr_number": pr_number,
            "head_sha": head_sha,
            "author_run_id": author_run_id,
            "author_identity": author_identity,
        },
        "changed_paths": changed_paths,
        "mutation_classes": mutation_classes,
        "risk_tier": risk_tier,
        "candidate_generation": {
            "sources": ["CODEOWNERS", ".ce/coordination.yml", "reviewer-registry"],
            "ownership_only": True,
            "git_history_scoring": False,
            "candidates": raw_candidates,
            "ranking_method": "lexicographic_reviewer_id",
            "broad_team_fallback": None,
        },
        "eligibility_results": eligibility_results,
        "availability_results": availability_results,
        "assignment": {
            "selected_reviewers": selected,
            "selected_identity_refs": selected_refs,
            "review_request_action": "request_review" if selected else "none",
            "venue_dispatch_ref": None,
            "envelope_ref": None,
            "broad_team_fallback": None,
        },
        "escalation": {"status": escalation_status, "reason": escalation_reason},
        "non_authority_statement": NON_AUTHORITY_STATEMENT,
    }


def load_optional_yaml(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    data = load_yaml(p)
    return data if isinstance(data, dict) else None


def read_text_if_exists(path: str | Path) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def git_value(repo_root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def git_changed_paths(repo_root: Path) -> list[str]:
    raw = git_value(repo_root, "diff", "--name-only", "origin/main...HEAD")
    return raw.splitlines() if raw else []


def infer_mutation_classes(paths: list[str]) -> list[str]:
    classes: list[str] = []
    for path in paths:
        if path.startswith("schemas/"):
            classes.append("schema")
        elif path.startswith("docs/") or path.startswith("README"):
            classes.append("docs")
        elif path.startswith(".github/") or path.startswith(".ce/"):
            classes.append("governance")
        elif path.startswith("validators/"):
            classes.append("code")
    return _dedupe(classes) or ["code"]
