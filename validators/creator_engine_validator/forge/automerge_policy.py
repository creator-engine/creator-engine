"""Dry-run automerge policy engine for ce-ops#291 W1a.

This module is decision-only. It classifies PR changes, composes the existing
size and mutation ceremony, emits structured dry-run decisions, and never
approves, merges, enqueues, enables auto-merge, mints approval markers, or runs
GitHub mutations.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from ..checks.work_sizing_floor import ChangeStat, classify_change_size
from ..work_sizing import MUTATION_CLASSES, normalize_work_class, size_ceremony
from .mutation_classifier import (
    AUTO_CLASSES,
    GESTURE_CLASSES,
    MutationPolicy,
    default_mutation_policy,
    mutation_class_for_paths,
)

AUTOMERGE_DECISION_AUTO: Final[str] = "AUTO"
AUTOMERGE_DECISION_GESTURE: Final[str] = "GESTURE"
DEFAULT_AUTOMERGE_POLICY_STATE_RELATIVE: Final[Path] = Path("automerge") / "policy.json"
DEFAULT_AUTOMERGE_DECISIONS_RELATIVE: Final[Path] = Path("automerge") / "decisions"
AUTOMERGE_RUN_MODE_CEO: Final[str] = "ceo"
AUTOMERGE_RUN_MODE_DEV: Final[str] = "dev"
AUTOMERGE_RUN_MODE_STRANGE_LOOP: Final[str] = "strangeLoop"
AUTOMERGE_ARMING_RUN_MODES: Final[frozenset[str]] = frozenset(
    {AUTOMERGE_RUN_MODE_CEO, AUTOMERGE_RUN_MODE_STRANGE_LOOP}
)
AUTOMERGE_CANARY_WORK_CLASSES: Final[frozenset[str]] = frozenset(
    {normalize_work_class("tiny"), normalize_work_class("story")}
)


class AutoMergePolicyStateError(Exception):
    """Durable automerge policy state could not be loaded or written safely."""


@dataclass(frozen=True)
class AutoMergeClassPolicy:
    """Per-mutation-class automerge flag."""

    auto_merge: bool = False

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AutoMergeClassPolicy":
        auto_merge = payload.get("auto_merge", False)
        if not isinstance(auto_merge, bool):
            raise AutoMergePolicyStateError("auto_merge must be a boolean")
        return cls(auto_merge=auto_merge)

    def to_payload(self) -> dict[str, bool]:
        return {"auto_merge": self.auto_merge}


@dataclass(frozen=True)
class AutoMergePolicyState:
    """Secret-free durable policy state, mirroring ``ApprovalWallState``."""

    run_mode: str = "dev"
    kill_switch: bool = False
    classes: Mapping[str, AutoMergeClassPolicy] = field(
        default_factory=lambda: {
            class_name: AutoMergeClassPolicy(auto_merge=False)
            for class_name in MUTATION_CLASSES
        }
    )
    enabling_decision_ref: str | None = None

    @classmethod
    def default(cls) -> "AutoMergePolicyState":
        return cls()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AutoMergePolicyState":
        run_mode = payload.get("run_mode", "dev")
        if not isinstance(run_mode, str) or not run_mode:
            raise AutoMergePolicyStateError("run_mode must be a non-empty string")

        kill_switch = payload.get("kill_switch", False)
        if not isinstance(kill_switch, bool):
            raise AutoMergePolicyStateError("kill_switch must be a boolean")

        enabling_decision_ref = payload.get("enabling_decision_ref")
        if enabling_decision_ref is not None and not isinstance(enabling_decision_ref, str):
            raise AutoMergePolicyStateError("enabling_decision_ref must be a string or null")

        raw_classes = payload.get("classes", {})
        if not isinstance(raw_classes, Mapping):
            raise AutoMergePolicyStateError("classes must be an object")

        classes = {
            class_name: AutoMergeClassPolicy(auto_merge=False)
            for class_name in MUTATION_CLASSES
        }
        for class_name, raw_policy in raw_classes.items():
            if class_name not in MUTATION_CLASSES:
                raise AutoMergePolicyStateError("classes contains unknown mutation class")
            if not isinstance(raw_policy, Mapping):
                raise AutoMergePolicyStateError("class policy must be an object")
            classes[str(class_name)] = AutoMergeClassPolicy.from_payload(raw_policy)

        return cls(
            run_mode=run_mode,
            kill_switch=kill_switch,
            classes=classes,
            enabling_decision_ref=enabling_decision_ref,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_mode": self.run_mode,
            "kill_switch": self.kill_switch,
            "classes": {
                class_name: policy.to_payload()
                for class_name, policy in self.classes.items()
            },
            "enabling_decision_ref": self.enabling_decision_ref,
        }

    def class_flag(self, mutation_class: str) -> bool:
        policy = self.classes.get(mutation_class)
        return bool(policy.auto_merge) if policy is not None else False


@dataclass(frozen=True)
class AutoMergeDecision:
    """Value-only automerge decision record."""

    decision: str
    work_class: str
    size_band: str
    minimum_work_class: str
    mutation_class: str
    gates: tuple[str, ...]
    rationale: tuple[str, ...]
    policy_sha: str
    checks_snapshot: Mapping[str, Any]
    run_mode: str
    kill_switch: bool
    class_flag: bool
    enabling_decision_ref: str | None = None
    review_decision: str | None = None
    checks_green: bool = False
    pr_number: int | None = None
    head_sha: str | None = None
    repo: str | None = None
    branch: str | None = None
    base: str | None = None
    required_checks: tuple[str, ...] = ()
    author_login: str | None = None
    approver_login: str | None = None

    @property
    def is_auto(self) -> bool:
        return self.decision == AUTOMERGE_DECISION_AUTO

    @property
    def ratification_gates(self) -> list[str]:
        return list(self.gates)

    @property
    def review_decision_blocked(self) -> bool:
        return self.review_decision == "CHANGES_REQUESTED"

    def to_payload(self) -> dict[str, Any]:
        return {
            "class": self.work_class,
            "size_band": self.size_band,
            "minimum_work_class": self.minimum_work_class,
            "mutation_class": self.mutation_class,
            "gates": list(self.gates),
            "decision": self.decision,
            "rationale": list(self.rationale),
            "policy_sha": self.policy_sha,
            "checks_snapshot": _jsonable(self.checks_snapshot),
            "run_mode": self.run_mode,
            "kill_switch": self.kill_switch,
            "class_flag": self.class_flag,
            "enabling_decision_ref": self.enabling_decision_ref,
            "reviewDecision": self.review_decision,
            "checks_green": self.checks_green,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "repo": self.repo,
            "branch": self.branch,
            "base": self.base,
            "required_checks": list(self.required_checks),
            "author_login": self.author_login,
            "approver_login": self.approver_login,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_payload()


def automerge_policy_state_path(
    root: str | Path = ".ce/state",
    policy: MutationPolicy | None = None,
) -> Path:
    """Return the durable policy-state path."""

    if policy is not None and root == ".ce/state":
        return Path(policy.state_path)
    return Path(root) / DEFAULT_AUTOMERGE_POLICY_STATE_RELATIVE


def load_automerge_policy_state(path: str | Path) -> AutoMergePolicyState:
    """Load durable policy state from disk; missing files return safe defaults."""

    state_path = Path(path)
    if not state_path.exists():
        return AutoMergePolicyState.default()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutoMergePolicyStateError(str(exc)) from exc
    if not isinstance(payload, Mapping):
        raise AutoMergePolicyStateError("automerge policy state must be a JSON object")
    return AutoMergePolicyState.from_payload(payload)


def load_decision_records(state_dir: str | Path) -> list[dict[str, Any]]:
    """Load emitted automerge decision records from ``state_dir``.

    This is read-only observability over ``.ce/state/automerge/decisions``:
    missing directories are empty, records are returned in deterministic path
    order, and malformed/unreadable records fail closed.
    """

    decisions_dir = Path(state_dir) / DEFAULT_AUTOMERGE_DECISIONS_RELATIVE
    if not decisions_dir.exists():
        return []
    if not decisions_dir.is_dir():
        raise AutoMergePolicyStateError(f"{decisions_dir} is not a directory")

    records: list[dict[str, Any]] = []
    for record_path in sorted(decisions_dir.glob("*.json")):
        try:
            payload = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AutoMergePolicyStateError(f"{record_path}: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise AutoMergePolicyStateError(f"{record_path}: decision record must be a JSON object")
        records.append(dict(payload))
    return records


def save_automerge_policy_state(path: str | Path, state: AutoMergePolicyState) -> None:
    """Atomically write durable, secret-free policy state."""

    state_path = Path(path)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_name(f".{state_path.name}.tmp")
        tmp.write_text(json.dumps(state.to_payload(), sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(state_path)
    except OSError as exc:
        raise AutoMergePolicyStateError(str(exc)) from exc


def update_automerge_policy_kill_switch(
    path: str | Path,
    *,
    active: bool,
) -> AutoMergePolicyState:
    """Set the durable live-policy kill-switch while preserving all other state."""

    current = load_automerge_policy_state(path)
    updated = AutoMergePolicyState(
        run_mode=current.run_mode,
        kill_switch=active,
        classes=current.classes,
        enabling_decision_ref=current.enabling_decision_ref,
    )
    save_automerge_policy_state(path, updated)
    return updated


def materialize_automerge_policy_state_from_variables(
    path: str | Path,
    *,
    run_mode_variable: str | None = None,
    enabling_ref_variable: str | None = None,
    kill_switch_variable: str | None = None,
) -> AutoMergePolicyState:
    """Write fail-safe automerge policy state from repository variable values.

    Only an explicit armed run mode enables the docs class. Every unset, empty,
    or otherwise malformed run-mode value materializes as the dormant dev policy.
    ``ceo`` is retained as the existing dev-2 override; ``strangeLoop`` is the
    explicit canary arming knob. The kill-switch defaults inactive but can be
    asserted independently to halt actuation before any source-host mutation.
    """

    run_mode = (
        str(run_mode_variable)
        if run_mode_variable in AUTOMERGE_ARMING_RUN_MODES
        else AUTOMERGE_RUN_MODE_DEV
    )
    docs_auto_merge = run_mode in AUTOMERGE_ARMING_RUN_MODES
    enabling_ref = _non_empty_string_or_none(enabling_ref_variable)
    kill_switch = _truthy_variable(kill_switch_variable)
    state = AutoMergePolicyState(
        run_mode=run_mode,
        kill_switch=kill_switch,
        classes={
            class_name: AutoMergeClassPolicy(
                auto_merge=class_name == "docs" and docs_auto_merge
            )
            for class_name in MUTATION_CLASSES
        },
        enabling_decision_ref=enabling_ref,
    )
    save_automerge_policy_state(path, state)
    return state


def decide_automerge(
    numstat: Iterable[ChangeStat | Mapping[str, Any]] | None = None,
    paths: Sequence[str] | None = None,
    declared_work_class: str = "S",
    policy_state: AutoMergePolicyState | None = None,
    checks: Mapping[str, Any] | None = None,
    *,
    policy: MutationPolicy | None = None,
    changed_paths: Sequence[str] | None = None,
    change_stats: Iterable[ChangeStat | Mapping[str, Any]] | None = None,
    review_decision: str | None = None,
    pr_number: int | None = None,
    head_sha: str | None = None,
    repo: str | None = None,
    branch: str | None = None,
    base: str | None = None,
    run_mode: str | None = None,
    author_login: str | None = None,
    approver_login: str | None = None,
) -> AutoMergeDecision:
    """Return an ``AUTO`` or ``GESTURE`` decision without side effects."""

    resolved_policy = policy or default_mutation_policy()
    resolved_state = policy_state or AutoMergePolicyState.default()
    if run_mode is not None:
        resolved_state = AutoMergePolicyState(
            run_mode=str(run_mode),
            kill_switch=resolved_state.kill_switch,
            classes=resolved_state.classes,
            enabling_decision_ref=resolved_state.enabling_decision_ref,
        )
    resolved_paths = tuple(paths if paths is not None else (changed_paths or ()))
    resolved_numstat = tuple(numstat if numstat is not None else (change_stats or ()))
    if not resolved_numstat:
        resolved_numstat = tuple(
            {"path": path, "additions": 0, "deletions": 0, "binary": False}
            for path in resolved_paths
        )

    checks_snapshot = _jsonable(checks or {})
    resolved_review_decision = _review_decision(checks, legacy_review_decision=review_decision)
    rationale: list[str] = []

    try:
        declared_work_class = normalize_work_class(declared_work_class)
    except ValueError:
        declared_work_class = str(declared_work_class)

    mutation_class = mutation_class_for_paths(resolved_paths, resolved_policy)
    size_projection = _classify_size_fail_closed(resolved_numstat)
    size_band = str(size_projection["size_band"])
    minimum_work_class = str(size_projection["minimum_work_class"])
    gates: tuple[str, ...] = ()

    try:
        ceremony = size_ceremony(declared_work_class, mutation_class)
        gates = tuple(str(gate) for gate in ceremony["ratification_gates"])
    except (KeyError, ValueError):
        rationale.append("size_ceremony refused the declared class or mutation class")
        return _decision(
            AUTOMERGE_DECISION_GESTURE,
            declared_work_class,
            size_band,
            minimum_work_class,
            mutation_class,
            gates,
            rationale,
            resolved_policy,
            checks_snapshot,
            resolved_state,
            resolved_review_decision,
            False,
            pr_number,
            head_sha,
            repo,
            branch,
            base,
            author_login,
            approver_login,
        )

    checks_green = _checks_all_green(checks, required_checks=resolved_policy.required_checks)
    gates_auto_only = gates == ("auto_back_gate",)
    class_flag = resolved_state.class_flag(mutation_class)

    rationale.append(f"mutation_class={mutation_class}")
    rationale.append(f"size_band={size_band}")
    rationale.append(f"gates={','.join(gates)}")

    auto_blockers: list[str] = []
    if not gates_auto_only:
        auto_blockers.append("gates_not_auto_back_gate_only")
    if not checks_green:
        auto_blockers.append("required_checks_not_green")
    if resolved_review_decision == "CHANGES_REQUESTED":
        auto_blockers.append("reviewDecision_CHANGES_REQUESTED")
    elif resolved_review_decision != "APPROVED":
        auto_blockers.append("reviewDecision_not_APPROVED")
    if size_band == "split_required":
        auto_blockers.append("size_band_split_required")
    if declared_work_class not in AUTOMERGE_CANARY_WORK_CLASSES:
        auto_blockers.append("work_class_outside_canary")
    if mutation_class in GESTURE_CLASSES:
        auto_blockers.append("gesture_class")
    if resolved_state.kill_switch:
        auto_blockers.append("kill_switch")
    if resolved_state.run_mode == "dev":
        auto_blockers.append("run_mode_dev")
    if resolved_state.run_mode not in AUTOMERGE_ARMING_RUN_MODES:
        auto_blockers.append("run_mode_not_armed")
    if not class_flag:
        auto_blockers.append("class_auto_merge_false")
    if class_flag and not resolved_state.enabling_decision_ref:
        auto_blockers.append("enabling_decision_ref_missing")
    if not _distinct_author_approver(author_login, approver_login):
        auto_blockers.append("author_approver_not_distinct")

    if auto_blockers:
        rationale.extend(auto_blockers)
        return _decision(
            AUTOMERGE_DECISION_GESTURE,
            declared_work_class,
            size_band,
            minimum_work_class,
            mutation_class,
            gates,
            rationale,
            resolved_policy,
            checks_snapshot,
            resolved_state,
            resolved_review_decision,
            checks_green,
            pr_number,
            head_sha,
            repo,
            branch,
            base,
            author_login,
            approver_login,
        )

    if mutation_class not in AUTO_CLASSES:
        rationale.append("not_in_auto_classes")
        return _decision(
            AUTOMERGE_DECISION_GESTURE,
            declared_work_class,
            size_band,
            minimum_work_class,
            mutation_class,
            gates,
            rationale,
            resolved_policy,
            checks_snapshot,
            resolved_state,
            resolved_review_decision,
            checks_green,
            pr_number,
            head_sha,
            repo,
            branch,
            base,
            author_login,
            approver_login,
        )

    rationale.append("all_auto_guards_passed")
    return _decision(
        AUTOMERGE_DECISION_AUTO,
        declared_work_class,
        size_band,
        minimum_work_class,
        mutation_class,
        gates,
        rationale,
        resolved_policy,
        checks_snapshot,
        resolved_state,
        resolved_review_decision,
        checks_green,
        pr_number,
        head_sha,
        repo,
        branch,
        base,
        author_login,
        approver_login,
    )


def emit_automerge_dry_run_decision(
    *,
    pr_number: int,
    head_sha: str,
    numstat: Iterable[ChangeStat | Mapping[str, Any]],
    paths: Sequence[str],
    declared_work_class: str,
    policy_state: AutoMergePolicyState | None,
    checks: Mapping[str, Any] | None,
    policy: MutationPolicy | None = None,
    output_dir: str | Path | None = None,
    repo: str | None = None,
    branch: str | None = None,
    base: str | None = None,
    run_mode: str | None = None,
    author_login: str | None = None,
    approver_login: str | None = None,
) -> AutoMergeDecision:
    """Write a dry-run decision JSON record and return the decision."""

    # TODO(ce-ops#291): register automerge-decide subcommand (dev-1 owns ce_cli.py).
    resolved_policy = policy or default_mutation_policy()
    decision = decide_automerge(
        numstat=numstat,
        paths=paths,
        declared_work_class=declared_work_class,
        policy_state=policy_state,
        checks=checks,
        policy=resolved_policy,
        pr_number=pr_number,
        head_sha=head_sha,
        repo=repo,
        branch=branch,
        base=base,
        run_mode=run_mode,
        author_login=author_login,
        approver_login=approver_login,
    )
    decisions_dir = Path(output_dir) if output_dir is not None else Path(resolved_policy.decisions_dir)
    decisions_dir.mkdir(parents=True, exist_ok=True)
    output_path = decisions_dir / f"{pr_number}-{_safe_ref(head_sha)}.json"
    output_path.write_text(json.dumps(decision.to_payload(), sort_keys=True) + "\n", encoding="utf-8")
    return decision


def dry_run_automerge_decision(**kwargs: Any) -> AutoMergeDecision:
    """Compatibility alias for the dry-run emitter."""

    return emit_automerge_dry_run_decision(**kwargs)


def _decision(
    decision: str,
    work_class: str,
    size_band: str,
    minimum_work_class: str,
    mutation_class: str,
    gates: tuple[str, ...],
    rationale: Sequence[str],
    policy: MutationPolicy,
    checks_snapshot: Mapping[str, Any],
    state: AutoMergePolicyState,
    review_decision: str | None,
    checks_green: bool,
    pr_number: int | None,
    head_sha: str | None,
    repo: str | None,
    branch: str | None,
    base: str | None,
    author_login: str | None,
    approver_login: str | None,
) -> AutoMergeDecision:
    return AutoMergeDecision(
        decision=decision,
        work_class=work_class,
        size_band=size_band,
        minimum_work_class=minimum_work_class,
        mutation_class=mutation_class,
        gates=gates,
        rationale=tuple(rationale),
        policy_sha=policy.policy_sha,
        checks_snapshot=checks_snapshot,
        run_mode=state.run_mode,
        kill_switch=state.kill_switch,
        class_flag=state.class_flag(mutation_class),
        enabling_decision_ref=state.enabling_decision_ref,
        review_decision=review_decision,
        checks_green=checks_green,
        pr_number=pr_number,
        head_sha=head_sha,
        repo=repo,
        branch=branch,
        base=base,
        required_checks=tuple(policy.required_checks),
        author_login=_non_empty_string_or_none(author_login),
        approver_login=_non_empty_string_or_none(approver_login),
    )


def _classify_size_fail_closed(
    numstat: Iterable[ChangeStat | Mapping[str, Any]],
) -> dict[str, Any]:
    try:
        return classify_change_size(numstat)
    except (TypeError, ValueError):
        return {
            "included_files": 0,
            "included_lines": 1001,
            "excluded_files": 0,
            "excluded_lines": 0,
            "excluded_path_categories": [],
            "size_band": "split_required",
            "minimum_work_class": "L",
        }


def _checks_all_green(
    checks: Mapping[str, Any] | None,
    *,
    required_checks: Sequence[str],
) -> bool:
    statuses = _check_statuses(checks)
    if checks is None:
        return False
    if required_checks:
        return all(_status_is_green(statuses.get(check)) for check in required_checks)
    if not statuses:
        return False
    return all(_status_is_green(status) for status in statuses.values())


def _check_statuses(checks: Mapping[str, Any] | None) -> dict[str, Any]:
    if checks is None:
        return {}

    for key in ("required_checks", "checks", "check_runs", "statuses"):
        raw = checks.get(key)
        if isinstance(raw, Mapping):
            return {str(name): status for name, status in raw.items()}
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            parsed: dict[str, Any] = {}
            for item in raw:
                if isinstance(item, Mapping):
                    name = item.get("name") or item.get("context")
                    status = item.get("conclusion")
                    if status is None:
                        status = item.get("status") or item.get("state")
                    if name:
                        parsed[str(name)] = status
            if parsed:
                return parsed

    ignored = {"reviewDecision", "review_decision", "reviewDecisionStatus"}
    return {
        str(name): status
        for name, status in checks.items()
        if name not in ignored and isinstance(status, str)
    }


def _status_is_green(status: Any) -> bool:
    return str(status).lower() in {"success", "successful", "passed", "green", "completed"}


def _review_decision(
    checks: Mapping[str, Any] | None,
    *,
    legacy_review_decision: str | None = None,
) -> str | None:
    if checks is None:
        return legacy_review_decision
    value = checks.get("reviewDecision", checks.get("review_decision"))
    return str(value) if value is not None else legacy_review_decision


def _non_empty_string_or_none(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _truthy_variable(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "kill", "halt"}


def _distinct_author_approver(author_login: str | None, approver_login: str | None) -> bool:
    author = _non_empty_string_or_none(author_login)
    approver = _non_empty_string_or_none(approver_login)
    return bool(author and approver and author.lower() != approver.lower())


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, Mapping):
            return {str(key): _jsonable(item) for key, item in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [_jsonable(item) for item in value]
        return str(value)


def _safe_ref(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
