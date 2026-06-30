"""Fail-closed actuator for dry-run automerge decisions."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

from .automerge_policy import (
    AUTOMERGE_ARMING_RUN_MODES,
    AutoMergePolicyStateError,
    automerge_policy_state_path,
    load_automerge_policy_state,
)

_AUTO_DECISION = "AUTO"
_ARMING_RUN_MODES = AUTOMERGE_ARMING_RUN_MODES
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_GREEN = {"success", "successful", "passed", "green", "completed"}


@dataclass(frozen=True)
class ActuationResult:
    """Secret-free actuator outcome."""

    status: str
    reason: str
    acted: bool = False
    auto_merge_result: Any | None = None
    audit_record: Mapping[str, Any] = field(default_factory=dict)

    @property
    def dormant(self) -> bool:
        return self.status == "Dormant"

    @property
    def refused(self) -> bool:
        return self.status == "Refused"

    @property
    def actuated(self) -> bool:
        return self.status == "Actuated"


@dataclass(frozen=True)
class _ActuatorChange:
    repo: str
    branch: str
    base: str
    pr_number: int
    head_sha: str | None
    manifest_paths: tuple[str, ...]
    plan_ref: str
    author_login: str
    approver_login: str
    changed: bool = False
    applied: bool = True
    verified: bool = True


def actuate_if_ready(decision_path, *, gh_runner) -> ActuationResult:
    """Enable auto-merge only after re-verifying every actuator predicate."""

    loaded = _load_decision(decision_path)
    if isinstance(loaded, ActuationResult):
        return loaded
    payload = loaded

    if not _run_mode_armed(payload.get("run_mode")):
        return _dormant("run_mode_not_armed", payload)

    if payload.get("decision") != _AUTO_DECISION:
        return _refuse("decision_not_auto", payload)
    if payload.get("kill_switch") is not False:
        return _refuse("kill_switch_not_false", payload)
    if payload.get("class_flag") is not True:
        return _refuse("class_flag_not_true", payload)
    if payload.get("class") not in {"tiny", "story"}:
        return _refuse("work_class_outside_canary", payload)

    enabling_ref = payload.get("enabling_decision_ref")
    if not isinstance(enabling_ref, str) or not enabling_ref.strip():
        return _refuse("enabling_decision_ref_missing", payload)

    required_checks = _required_checks(payload)
    if isinstance(required_checks, ActuationResult):
        return _with_payload_audit(required_checks, payload)

    change = _change_ref(payload)
    if isinstance(change, ActuationResult):
        return _with_payload_audit(change, payload)

    if gh_runner is None:
        return _refuse("gh_runner_missing", payload)

    live_policy = _live_policy_state()
    if isinstance(live_policy, ActuationResult):
        return _with_payload_audit(live_policy, payload)
    if not _run_mode_armed(live_policy.run_mode):
        return _dormant("live_run_mode_not_armed", payload, live_run_mode=live_policy.run_mode)
    if live_policy.kill_switch:
        return _refuse("live_kill_switch_active", payload, live_run_mode=live_policy.run_mode)

    independent = _live_author_approver_independent(change, gh_runner)
    if isinstance(independent, ActuationResult):
        return _with_payload_audit(independent, payload)
    if not independent:
        return _refuse("author_approver_not_distinct", payload, live_run_mode=live_policy.run_mode)

    live = _live_required_checks_green(change, required_checks, gh_runner)
    if isinstance(live, ActuationResult):
        return _with_payload_audit(live, payload)
    if not live:
        return _refuse("required_checks_not_green", payload, live_run_mode=live_policy.run_mode)

    try:
        result = _enable_auto_merge(change, gh_runner)
    except Exception as exc:  # pragma: no cover - defensive fail-closed actuator guard
        return _refuse(f"enable_auto_merge_failed:{exc}", payload, live_run_mode=live_policy.run_mode)
    return ActuationResult(
        status="Actuated",
        reason="all_predicates_green",
        acted=True,
        auto_merge_result=result,
        audit_record=_audit_record(
            payload,
            status="Actuated",
            reason="all_predicates_green",
            acted=True,
            live_run_mode=live_policy.run_mode,
        ),
    )


def _load_decision(decision_path: str | Path) -> Mapping[str, Any] | ActuationResult:
    try:
        payload = json.loads(Path(decision_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return _refuse(f"decision_unreadable:{exc}")
    if not isinstance(payload, Mapping):
        return _refuse("decision_record_not_object")
    return payload


def _required_checks(payload: Mapping[str, Any]) -> tuple[str, ...] | ActuationResult:
    raw = payload.get("required_checks")
    if raw is None:
        snapshot = payload.get("checks_snapshot")
        if isinstance(snapshot, Mapping):
            raw = snapshot.get("required_checks")
    if raw is None:
        return _refuse("required_checks_missing")
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        return _refuse("required_checks_invalid")
    checks = tuple(str(item).strip() for item in raw if str(item).strip())
    if len(checks) != len(raw):
        return _refuse("required_checks_invalid")
    if not checks:
        return _refuse("required_checks_empty")
    return checks


def _change_ref(payload: Mapping[str, Any]) -> _ActuatorChange | ActuationResult:
    raw_change = payload.get("change")
    if raw_change is None:
        raw_change = payload
    if not isinstance(raw_change, Mapping):
        return _refuse("change_invalid")

    repo = raw_change.get("repo")
    branch = raw_change.get("branch")
    base = raw_change.get("base")
    pr_number = raw_change.get("pr_number", payload.get("pr_number"))
    head_sha = raw_change.get("head_sha", payload.get("head_sha"))
    policy_sha = payload.get("policy_sha")
    raw_manifest_paths = raw_change.get("manifest_paths", ())
    author_login = raw_change.get("author_login", payload.get("author_login"))
    approver_login = raw_change.get("approver_login", payload.get("approver_login"))

    if not isinstance(repo, str) or not _REPO_RE.match(repo):
        return _refuse("change_repo_invalid")
    if not isinstance(branch, str) or not branch.strip():
        return _refuse("change_branch_invalid")
    if not isinstance(base, str) or not base.strip():
        return _refuse("change_base_invalid")
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number <= 0:
        return _refuse("change_pr_number_invalid")
    if head_sha is not None and not isinstance(head_sha, str):
        return _refuse("change_head_sha_invalid")
    if not isinstance(policy_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", policy_sha):
        return _refuse("policy_sha_invalid")
    if isinstance(raw_manifest_paths, (str, bytes)) or not isinstance(raw_manifest_paths, Sequence):
        return _refuse("manifest_paths_invalid")

    manifest_paths = tuple(str(path).strip() for path in raw_manifest_paths if str(path).strip())
    if len(manifest_paths) != len(raw_manifest_paths):
        return _refuse("manifest_paths_invalid")
    if not _distinct_login_pair(author_login, approver_login):
        return _refuse("author_approver_not_distinct")

    return _ActuatorChange(
        repo=repo,
        branch=branch,
        base=base,
        pr_number=pr_number,
        head_sha=head_sha,
        manifest_paths=manifest_paths,
        plan_ref=policy_sha,
        author_login=str(author_login).strip(),
        approver_login=str(approver_login).strip(),
        changed=False,
        applied=True,
        verified=True,
    )


def _live_author_approver_independent(
    change: _ActuatorChange,
    gh_runner,
) -> bool | ActuationResult:
    try:
        proc = gh_runner(
            [
                "gh",
                "pr",
                "view",
                str(change.pr_number),
                "--repo",
                change.repo,
                "--json",
                "author,latestReviews",
            ],
            None,
        )
    except Exception as exc:  # pragma: no cover - defensive fail-closed transport guard
        return _refuse(f"live_review_state_unreadable:{exc}")
    if getattr(proc, "returncode", 1) != 0:
        return _refuse("live_review_state_unreadable")
    try:
        payload = json.loads((getattr(proc, "stdout", "") or "").strip() or "{}")
    except (json.JSONDecodeError, TypeError, ValueError):
        return _refuse("live_review_state_unparseable")
    if not isinstance(payload, Mapping):
        return _refuse("live_review_state_unparseable")

    live_author = _login_from_actor(payload.get("author"))
    if not live_author or live_author.lower() != change.author_login.lower():
        return _refuse("live_author_mismatch")

    latest_reviews = payload.get("latestReviews")
    if not isinstance(latest_reviews, Sequence) or isinstance(latest_reviews, (str, bytes)):
        return _refuse("live_reviews_missing")

    for review in latest_reviews:
        if not isinstance(review, Mapping):
            continue
        state = str(review.get("state") or "").upper()
        reviewer = _login_from_actor(review.get("author"))
        if state == "APPROVED" and reviewer and reviewer.lower() == change.approver_login.lower():
            return reviewer.lower() != live_author.lower()
    return False


def _live_required_checks_green(
    change: _ActuatorChange,
    required_checks: Sequence[str],
    gh_runner,
) -> bool | ActuationResult:
    if not required_checks:
        return _refuse("required_checks_empty")
    if gh_runner is None:
        return _refuse("gh_runner_missing")
    try:
        proc = gh_runner(
            [
                "gh",
                "pr",
                "checks",
                str(change.pr_number),
                "--repo",
                change.repo,
                "--json",
                "name,state,status,conclusion",
            ],
            None,
        )
    except Exception as exc:  # pragma: no cover - defensive fail-closed transport guard
        return _refuse(f"live_required_checks_unreadable:{exc}")
    if getattr(proc, "returncode", 1) != 0:
        return _refuse("live_required_checks_unreadable")
    try:
        rows = json.loads((getattr(proc, "stdout", "") or "").strip() or "[]")
    except (json.JSONDecodeError, TypeError, ValueError):
        return _refuse("live_required_checks_unparseable")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return _refuse("live_required_checks_unparseable")

    statuses: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = row.get("name")
        if not name:
            continue
        status = row.get("conclusion")
        if status is None:
            status = row.get("state", row.get("status"))
        statuses[str(name)] = status

    return all(_status_is_green(statuses.get(name)) for name in required_checks)


def _status_is_green(status: Any) -> bool:
    return str(status).lower() in _GREEN


def _enable_auto_merge(change: _ActuatorChange, gh_runner):
    auto_merge = import_module(".auto_merge", __package__)
    return auto_merge.enable_auto_merge(change, apply=True, gh_runner=gh_runner)


def _run_mode_armed(value: Any) -> bool:
    return isinstance(value, str) and value in _ARMING_RUN_MODES


def _live_policy_state():
    try:
        return load_automerge_policy_state(automerge_policy_state_path())
    except AutoMergePolicyStateError as exc:
        return _dormant(f"live_policy_unreadable:{exc}")


def _dormant(
    reason: str,
    payload: Mapping[str, Any] | None = None,
    *,
    live_run_mode: str | None = None,
) -> ActuationResult:
    return ActuationResult(
        status="Dormant",
        reason=reason,
        acted=False,
        audit_record=_audit_record(
            payload,
            status="Dormant",
            reason=reason,
            acted=False,
            live_run_mode=live_run_mode,
        ),
    )


def _refuse(
    reason: str,
    payload: Mapping[str, Any] | None = None,
    *,
    live_run_mode: str | None = None,
) -> ActuationResult:
    return ActuationResult(
        status="Refused",
        reason=reason,
        acted=False,
        audit_record=_audit_record(
            payload,
            status="Refused",
            reason=reason,
            acted=False,
            live_run_mode=live_run_mode,
        ),
    )


def _with_payload_audit(result: ActuationResult, payload: Mapping[str, Any]) -> ActuationResult:
    if result.audit_record:
        return result
    return ActuationResult(
        status=result.status,
        reason=result.reason,
        acted=result.acted,
        auto_merge_result=result.auto_merge_result,
        audit_record=_audit_record(
            payload,
            status=result.status,
            reason=result.reason,
            acted=result.acted,
        ),
    )


def _audit_record(
    payload: Mapping[str, Any] | None,
    *,
    status: str,
    reason: str,
    acted: bool,
    live_run_mode: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "surface": "ce-automerge-actuator",
        "status": status,
        "reason": reason,
        "acted": acted,
    }
    if live_run_mode is not None:
        record["live_run_mode"] = live_run_mode
    if not isinstance(payload, Mapping):
        return record
    raw_change = payload.get("change")
    change = raw_change if isinstance(raw_change, Mapping) else payload
    record.update(
        {
            "decision": payload.get("decision"),
            "run_mode": payload.get("run_mode"),
            "kill_switch": payload.get("kill_switch"),
            "class_flag": payload.get("class_flag"),
            "work_class": payload.get("class"),
            "mutation_class": payload.get("mutation_class"),
            "repo": change.get("repo"),
            "pr_number": change.get("pr_number", payload.get("pr_number")),
            "head_sha": change.get("head_sha", payload.get("head_sha")),
            "branch": change.get("branch"),
            "base": change.get("base"),
            "author_login": change.get("author_login", payload.get("author_login")),
            "approver_login": change.get("approver_login", payload.get("approver_login")),
            "single_pr": True,
            "enabling_decision_ref_present": bool(
                isinstance(payload.get("enabling_decision_ref"), str)
                and payload.get("enabling_decision_ref").strip()
            ),
        }
    )
    return record


def _distinct_login_pair(author_login: Any, approver_login: Any) -> bool:
    if not isinstance(author_login, str) or not isinstance(approver_login, str):
        return False
    author = author_login.strip()
    approver = approver_login.strip()
    return bool(author and approver and author.lower() != approver.lower())


def _login_from_actor(actor: Any) -> str | None:
    if not isinstance(actor, Mapping):
        return None
    login = actor.get("login")
    if not isinstance(login, str):
        return None
    stripped = login.strip()
    return stripped or None


__all__ = ["ActuationResult", "actuate_if_ready"]
