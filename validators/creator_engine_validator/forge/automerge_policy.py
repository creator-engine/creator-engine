"""CEO-mode auto-merge policy engine (PR-A: classify + dry-run only).

This module is PR-A scope ONLY: it classifies PRs and produces an AUTO/GESTURE
decision record.  It NEVER mints capability markers, NEVER calls ``gh pr merge``,
and NEVER performs any live merge operation.  All policy flags ship as FALSE
(disarmed); arming is PR-B / Operator-only.

``decide_automerge(...)`` composes three existing axes that are ALREADY BUILT:

1. ``mutation_class_for_paths()`` → mutation class (this PR).
2. ``classify_change_size()`` → size band (this PR).
3. ``size_ceremony(work_class, mutation_class)["ratification_gates"]``
   → AUTO / GESTURE from the ratified ceremony table.

Additional AUTO guards (all must hold for AUTO decision):
- policy_state.kill_switch must be False.
- policy_state.run_mode must be "ceo" (in dev mode nothing auto-merges).
- per-class flag ``policy_state.classes[mutation_class].auto_merge`` must be True.
- checks snapshot must show all required checks green.
- review_decision must NOT be "CHANGES_REQUESTED".
- size band must NOT be "split_required".
- mutation class must be in AUTO_CLASSES (not a GESTURE_CLASSES member).

If ANY guard fails the decision is GESTURE_REQUIRED regardless of class.

The ``AutoMergePolicyState`` mirrors ``ApprovalWallState`` in structure: durable,
secret-free, atomic-write, JSON at ``.ce/state/automerge/policy.json``.
Ships with ALL flags FALSE — no path auto-merges until a human Operator flips
the enabling decision.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Mapping

from ..checks.work_sizing_floor import classify_change_size, ChangeStat
from ..work_sizing import size_ceremony
from .mutation_classifier import (
    AUTO_CLASSES,
    GESTURE_CLASSES,
    mutation_class_for_paths,
)

# ── Constants ────────────────────────────────────────────────────────────────

AUTOMERGE_DECISION_AUTO: Final[str] = "AUTO"
AUTOMERGE_DECISION_GESTURE: Final[str] = "GESTURE_REQUIRED"

DEFAULT_AUTOMERGE_POLICY_STATE_RELATIVE: Final[Path] = (
    Path("automerge") / "policy.json"
)

# All known mutation classes — mirrors work_sizing.MUTATION_CLASSES.
_ALL_MUTATION_CLASSES: Final[tuple[str, ...]] = (
    "none",
    "docs",
    "code",
    "schema",
    "deploy",
    "governance",
    "identity",
    "security",
    "attestation",
    "redaction",
)

# ── Durable state ────────────────────────────────────────────────────────────


class AutoMergePolicyStateError(Exception):
    """Durable auto-merge policy state could not be loaded or written safely."""


@dataclass(frozen=True)
class AutoMergeClassPolicy:
    """Per-mutation-class auto-merge flag.  Ships as ``auto_merge=False``."""

    auto_merge: bool = False

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AutoMergeClassPolicy":
        value = payload.get("auto_merge", False)
        if not isinstance(value, bool):
            raise AutoMergePolicyStateError(
                "auto_merge must be a boolean"
            )
        return cls(auto_merge=value)

    def to_payload(self) -> dict[str, Any]:
        return {"auto_merge": self.auto_merge}


@dataclass(frozen=True)
class AutoMergePolicyState:
    """Durable, secret-free auto-merge policy state.

    Ships with ``run_mode="dev"`` and all class flags ``False`` so nothing
    auto-merges until an Operator flips the enabling decision (PR-B / R2).

    Mirrors ``ApprovalWallState`` — atomic-write, no secrets, JSON on disk.
    """

    run_mode: str = "dev"
    kill_switch: bool = False
    classes: dict[str, AutoMergeClassPolicy] = field(
        default_factory=lambda: {
            cls: AutoMergeClassPolicy(auto_merge=False)
            for cls in _ALL_MUTATION_CLASSES
        }
    )
    enabling_decision_ref: str | None = None

    @classmethod
    def default(cls) -> "AutoMergePolicyState":
        """Return the shipped-safe default: dev mode, all flags False."""
        return cls(
            run_mode="dev",
            kill_switch=False,
            classes={
                c: AutoMergeClassPolicy(auto_merge=False)
                for c in _ALL_MUTATION_CLASSES
            },
            enabling_decision_ref=None,
        )

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
        if not isinstance(raw_classes, dict):
            raise AutoMergePolicyStateError("classes must be an object")

        classes: dict[str, AutoMergeClassPolicy] = {
            c: AutoMergeClassPolicy(auto_merge=False) for c in _ALL_MUTATION_CLASSES
        }
        for cls_name, cls_payload in raw_classes.items():
            if not isinstance(cls_payload, dict):
                raise AutoMergePolicyStateError(
                    f"classes.{cls_name} must be an object"
                )
            classes[cls_name] = AutoMergeClassPolicy.from_payload(cls_payload)

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
                cls_name: cls_policy.to_payload()
                for cls_name, cls_policy in self.classes.items()
            },
            "enabling_decision_ref": self.enabling_decision_ref,
        }

    def class_flag(self, mutation_class: str) -> bool:
        """Return the per-class auto_merge flag; default False for unknown classes."""
        policy = self.classes.get(mutation_class)
        return policy.auto_merge if policy is not None else False


def automerge_policy_state_path(root: str | Path = ".ce/state") -> Path:
    """Return the default durable policy-state path below a local-state root."""
    return Path(root) / DEFAULT_AUTOMERGE_POLICY_STATE_RELATIVE


def load_automerge_policy_state(path: str | Path) -> AutoMergePolicyState:
    """Load durable policy state from ``path``; absent file → shipped default."""
    state_path = Path(path)
    if not state_path.exists():
        return AutoMergePolicyState.default()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutoMergePolicyStateError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise AutoMergePolicyStateError("automerge policy state must be a JSON object")
    return AutoMergePolicyState.from_payload(payload)


def save_automerge_policy_state(
    path: str | Path, state: AutoMergePolicyState
) -> None:
    """Atomically write ``state`` to ``path``."""
    state_path = Path(path)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_name(f".{state_path.name}.tmp")
        tmp.write_text(
            json.dumps(state.to_payload(), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(state_path)
    except OSError as exc:
        raise AutoMergePolicyStateError(str(exc)) from exc


# ── Decision ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AutoMergeDecision:
    """Value-only auto-merge decision record.

    ``decision`` is one of ``"AUTO"`` or ``"GESTURE_REQUIRED"``.
    ``rationale`` is a human-readable list of reasons (gates passed / failed).
    This record is never secret-bearing and is safe to write to disk / emit as JSON.
    """

    decision: str
    mutation_class: str
    size_band: str
    minimum_work_class: str
    ratification_gates: list[str]
    run_mode: str
    kill_switch: bool
    class_flag: bool
    rationale: list[str]
    checks_green: bool
    review_decision_blocked: bool
    pr_number: int | None = None
    head_sha: str | None = None

    @property
    def is_auto(self) -> bool:
        return self.decision == AUTOMERGE_DECISION_AUTO

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "mutation_class": self.mutation_class,
            "size_band": self.size_band,
            "minimum_work_class": self.minimum_work_class,
            "ratification_gates": self.ratification_gates,
            "run_mode": self.run_mode,
            "kill_switch": self.kill_switch,
            "class_flag": self.class_flag,
            "checks_green": self.checks_green,
            "review_decision_blocked": self.review_decision_blocked,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "rationale": self.rationale,
        }


def decide_automerge(
    *,
    changed_paths: list[str],
    change_stats: list[ChangeStat] | list[dict[str, Any]] | None = None,
    declared_work_class: str = "story",
    policy_state: AutoMergePolicyState | None = None,
    checks: Mapping[str, str] | None = None,
    review_decision: str | None = None,
    pr_number: int | None = None,
    head_sha: str | None = None,
) -> AutoMergeDecision:
    """Classify ``changed_paths`` and produce an AUTO/GESTURE_REQUIRED decision.

    This function is pure: it never merges, never mints a capability marker,
    and never performs any I/O.  Fail-closed: any error in classification or
    policy resolution produces GESTURE_REQUIRED.

    Args:
        changed_paths: list of repo-relative paths changed in the PR.
        change_stats: optional git --numstat stats for size classification.
        declared_work_class: the declared work class from the PR (default ``story``).
        policy_state: loaded ``AutoMergePolicyState``; absent → shipped default
            (dev mode, all False → always GESTURE_REQUIRED).
        checks: mapping of check-name → status (``"success"``/``"failure"``/etc.).
        review_decision: GitHub reviewDecision (e.g. ``"APPROVED"`` / ``"CHANGES_REQUESTED"``).
        pr_number: optional PR number for the audit record.
        head_sha: optional head SHA for the audit record.
    """
    state = policy_state if policy_state is not None else AutoMergePolicyState.default()
    rationale: list[str] = []

    # 1. Mutation class (fail-closed).
    try:
        mutation_class = mutation_class_for_paths(changed_paths)
    except Exception as exc:  # noqa: BLE001
        return AutoMergeDecision(
            decision=AUTOMERGE_DECISION_GESTURE,
            mutation_class="unknown",
            size_band="unknown",
            minimum_work_class="unknown",
            ratification_gates=[],
            run_mode=state.run_mode,
            kill_switch=state.kill_switch,
            class_flag=False,
            checks_green=False,
            review_decision_blocked=False,
            rationale=[f"mutation_class_error: {exc}"],
            pr_number=pr_number,
            head_sha=head_sha,
        )

    # 2. Size classification (fail-closed).
    size_band = "unknown"
    minimum_work_class = "unknown"
    if change_stats is not None:
        try:
            size_result = classify_change_size(change_stats)
            size_band = size_result["size_band"]
            minimum_work_class = size_result["minimum_work_class"]
        except Exception:  # noqa: BLE001
            size_band = "unknown"
            minimum_work_class = "unknown"

    # 3. Ceremony gates from the ratified risk table.
    try:
        ceremony = size_ceremony(declared_work_class, mutation_class)
        ratification_gates: list[str] = list(ceremony["ratification_gates"])
    except ValueError:
        # Unknown work_class or mutation_class → GESTURE.
        rationale.append(f"ceremony_lookup_failed: work_class={declared_work_class!r} mutation_class={mutation_class!r}")
        return AutoMergeDecision(
            decision=AUTOMERGE_DECISION_GESTURE,
            mutation_class=mutation_class,
            size_band=size_band,
            minimum_work_class=minimum_work_class,
            ratification_gates=[],
            run_mode=state.run_mode,
            kill_switch=state.kill_switch,
            class_flag=state.class_flag(mutation_class),
            checks_green=False,
            review_decision_blocked=False,
            rationale=rationale,
            pr_number=pr_number,
            head_sha=head_sha,
        )

    # 4. Evaluate guards in priority order; first failure → GESTURE.

    # Guard: kill_switch
    if state.kill_switch:
        rationale.append("kill_switch=true: all auto-merge halted")
        return _gesture(mutation_class, size_band, minimum_work_class, ratification_gates, state, rationale, pr_number, head_sha)

    # Guard: mutation class must be in AUTO_CLASSES
    if mutation_class not in AUTO_CLASSES:
        rationale.append(f"mutation_class={mutation_class!r} requires operator_merge (not in AUTO_CLASSES)")
        return _gesture(mutation_class, size_band, minimum_work_class, ratification_gates, state, rationale, pr_number, head_sha)

    # Guard: ratification_gates must be auto_back_gate only
    gates_set = set(ratification_gates)
    if "operator_merge" in gates_set:
        rationale.append("ratification_gates includes operator_merge: gesture required")
        return _gesture(mutation_class, size_band, minimum_work_class, ratification_gates, state, rationale, pr_number, head_sha)
    if "auto_back_gate" not in gates_set:
        rationale.append("ratification_gates does not include auto_back_gate: gesture required")
        return _gesture(mutation_class, size_band, minimum_work_class, ratification_gates, state, rationale, pr_number, head_sha)

    # Guard: run_mode must be "ceo"
    if state.run_mode != "ceo":
        rationale.append(f"run_mode={state.run_mode!r}: not in CEO mode, nothing auto-merges")
        return _gesture(mutation_class, size_band, minimum_work_class, ratification_gates, state, rationale, pr_number, head_sha)

    # Guard: per-class flag must be enabled
    class_flag = state.class_flag(mutation_class)
    if not class_flag:
        rationale.append(f"class_flag[{mutation_class!r}].auto_merge=False: class not enabled")
        return _gesture(mutation_class, size_band, minimum_work_class, ratification_gates, state, rationale, pr_number, head_sha)

    # Guard: enabling_decision_ref must be set
    if not state.enabling_decision_ref:
        rationale.append("enabling_decision_ref is null: Operator has not ratified auto-merge")
        return _gesture(mutation_class, size_band, minimum_work_class, ratification_gates, state, rationale, pr_number, head_sha)

    # Guard: checks must all be green
    checks_green = _checks_all_green(checks)
    if not checks_green:
        failing = _failing_checks(checks)
        rationale.append(f"checks not green: {failing!r}")
        return AutoMergeDecision(
            decision=AUTOMERGE_DECISION_GESTURE,
            mutation_class=mutation_class,
            size_band=size_band,
            minimum_work_class=minimum_work_class,
            ratification_gates=ratification_gates,
            run_mode=state.run_mode,
            kill_switch=state.kill_switch,
            class_flag=class_flag,
            checks_green=False,
            review_decision_blocked=False,
            rationale=rationale,
            pr_number=pr_number,
            head_sha=head_sha,
        )

    # Guard: CHANGES_REQUESTED blocks auto-merge
    review_blocked = review_decision == "CHANGES_REQUESTED"
    if review_blocked:
        rationale.append("reviewDecision=CHANGES_REQUESTED: gesture required")
        return AutoMergeDecision(
            decision=AUTOMERGE_DECISION_GESTURE,
            mutation_class=mutation_class,
            size_band=size_band,
            minimum_work_class=minimum_work_class,
            ratification_gates=ratification_gates,
            run_mode=state.run_mode,
            kill_switch=state.kill_switch,
            class_flag=class_flag,
            checks_green=True,
            review_decision_blocked=True,
            rationale=rationale,
            pr_number=pr_number,
            head_sha=head_sha,
        )

    # Guard: size band must not be split_required
    if size_band == "split_required":
        rationale.append("size_band=split_required: PR too large, must be split")
        return AutoMergeDecision(
            decision=AUTOMERGE_DECISION_GESTURE,
            mutation_class=mutation_class,
            size_band=size_band,
            minimum_work_class=minimum_work_class,
            ratification_gates=ratification_gates,
            run_mode=state.run_mode,
            kill_switch=state.kill_switch,
            class_flag=class_flag,
            checks_green=True,
            review_decision_blocked=False,
            rationale=rationale,
            pr_number=pr_number,
            head_sha=head_sha,
        )

    # All guards passed → AUTO.
    rationale.append(
        f"AUTO: mutation_class={mutation_class!r}, run_mode=ceo, "
        f"class_flag=True, checks_green, review_decision={review_decision!r}, "
        f"enabling_decision_ref set"
    )
    return AutoMergeDecision(
        decision=AUTOMERGE_DECISION_AUTO,
        mutation_class=mutation_class,
        size_band=size_band,
        minimum_work_class=minimum_work_class,
        ratification_gates=ratification_gates,
        run_mode=state.run_mode,
        kill_switch=state.kill_switch,
        class_flag=class_flag,
        checks_green=True,
        review_decision_blocked=False,
        rationale=rationale,
        pr_number=pr_number,
        head_sha=head_sha,
    )


def _gesture(
    mutation_class: str,
    size_band: str,
    minimum_work_class: str,
    ratification_gates: list[str],
    state: AutoMergePolicyState,
    rationale: list[str],
    pr_number: int | None,
    head_sha: str | None,
) -> AutoMergeDecision:
    """Return a GESTURE_REQUIRED decision."""
    return AutoMergeDecision(
        decision=AUTOMERGE_DECISION_GESTURE,
        mutation_class=mutation_class,
        size_band=size_band,
        minimum_work_class=minimum_work_class,
        ratification_gates=ratification_gates,
        run_mode=state.run_mode,
        kill_switch=state.kill_switch,
        class_flag=state.class_flag(mutation_class),
        checks_green=False,
        review_decision_blocked=False,
        rationale=rationale,
        pr_number=pr_number,
        head_sha=head_sha,
    )


def _checks_all_green(checks: Mapping[str, str] | None) -> bool:
    """Return True if all provided checks have ``"success"`` status."""
    if checks is None:
        # No checks provided → assume not green (fail-closed).
        return False
    if not checks:
        # Empty checks dict → no checks to fail, treat as green.
        return True
    return all(str(v).lower() == "success" for v in checks.values())


def _failing_checks(checks: Mapping[str, str] | None) -> list[str]:
    """Return list of check names that are not ``"success"``."""
    if not checks:
        return []
    return [k for k, v in checks.items() if str(v).lower() != "success"]
