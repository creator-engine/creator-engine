"""Fail-closed actuator for dry-run automerge decisions."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from .automerge_policy import (
    AutoMergePolicyStateError,
    automerge_policy_state_path,
    load_automerge_policy_state,
)

_AUTO_DECISION = "AUTO"
_ARMING_RUN_MODES = frozenset({"ceo"})
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_GREEN = {"success", "successful", "passed", "green", "completed"}


@dataclass(frozen=True)
class ActuationResult:
    """Secret-free actuator outcome."""

    status: str
    reason: str
    acted: bool = False
    auto_merge_result: Any | None = None

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
        return _dormant("run_mode_not_armed")

    if payload.get("decision") != _AUTO_DECISION:
        return _refuse("decision_not_auto")
    if payload.get("kill_switch") is not False:
        return _refuse("kill_switch_not_false")
    if payload.get("class_flag") is not True:
        return _refuse("class_flag_not_true")

    enabling_ref = payload.get("enabling_decision_ref")
    if not isinstance(enabling_ref, str) or not enabling_ref.strip():
        return _refuse("enabling_decision_ref_missing")

    required_checks = _required_checks(payload)
    if isinstance(required_checks, ActuationResult):
        return required_checks

    change = _change_ref(payload)
    if isinstance(change, ActuationResult):
        return change

    if gh_runner is None:
        return _refuse("gh_runner_missing")

    live_policy = _live_policy_state()
    if isinstance(live_policy, ActuationResult):
        return live_policy
    if not _run_mode_armed(live_policy.run_mode):
        return _dormant("live_run_mode_not_armed")
    if live_policy.kill_switch:
        return _refuse("live_kill_switch_active")

    live = _live_required_checks_green(change, required_checks, gh_runner)
    if isinstance(live, ActuationResult):
        return live
    if not live:
        return _refuse("required_checks_not_green")

    try:
        result = _enable_auto_merge(change, gh_runner)
    except Exception as exc:  # pragma: no cover - defensive fail-closed actuator guard
        return _refuse(f"enable_auto_merge_failed:{exc}")
    return ActuationResult(
        status="Actuated",
        reason="all_predicates_green",
        acted=True,
        auto_merge_result=result,
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

    return _ActuatorChange(
        repo=repo,
        branch=branch,
        base=base,
        pr_number=pr_number,
        head_sha=head_sha,
        manifest_paths=manifest_paths,
        plan_ref=policy_sha,
        changed=False,
        applied=True,
        verified=True,
    )


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


def _dormant(reason: str) -> ActuationResult:
    return ActuationResult(status="Dormant", reason=reason, acted=False)


def _refuse(reason: str) -> ActuationResult:
    return ActuationResult(status="Refused", reason=reason, acted=False)


__all__ = ["ActuationResult", "actuate_if_ready"]
