"""Benign Controller continuity drill harness.

The drill composes the read-only posture banner and takeover planner into one
scheduled proof record.  It never starts a controller, takes over live state,
re-arms watchers, mutates settings, signs, approves, merges, or enqueues.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import controller_posture, seat_lifecycle, takeover_runtime

DRILL_KIND = "ce-continuity-drill-record"
SCHEMA_VERSION = 1
WEEKLY_INTERVAL_DAYS = 7
REQUIRED_CLEAN_RUNS = 2
STANDBY_LIVENESS_ABSENT_NOTE = (
    "ABSENT — D6 Drill #1 gap; provision standby surface per ce-502"
)
FORBIDDEN_MECHANICS = (
    "merge",
    "approve",
    "enqueue",
    "sign",
    "settings_mutation",
    "live_daemon_mutation",
    "real_watcher_mutation",
    "real_takeover",
)
_CLEAN_STATUSES = frozenset({"clean", "pass", "passed", "ok", "success"})
_DIRTY_STATUSES = frozenset({"dirty", "failed", "fail", "blocked", "error"})


class ContinuityDrillError(Exception):
    code = "CE-CONTINUITY-DRILL-ERROR"


class InvalidRunHistory(ContinuityDrillError):
    code = "CE-CONTINUITY-DRILL-BAD-HISTORY"


@dataclass(frozen=True)
class PriorRun:
    run_date: date
    status: str

    @property
    def clean(self) -> bool:
        return self.status in _CLEAN_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.run_date.isoformat(),
            "status": self.status,
            "clean": self.clean,
        }


@dataclass(frozen=True)
class CadenceStatus:
    as_of: date
    phase: str
    required: bool
    reason: str
    consecutive_clean_runs: int
    next_due: str
    prior_runs: tuple[PriorRun, ...]
    promotion_candidate: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat(),
            "phase": self.phase,
            "required": self.required,
            "reason": self.reason,
            "consecutive_clean_runs": self.consecutive_clean_runs,
            "next_due": self.next_due,
            "promotion_candidate": self.promotion_candidate,
            "prior_runs": [run.to_dict() for run in self.prior_runs],
        }


@dataclass(frozen=True)
class StandbyLiveness:
    ok: bool
    status: str
    note: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "note": self.note,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class DrillRecord:
    predecessor: str
    harness: str
    repo_root: Path
    run_at: str
    host_id: str
    cadence: CadenceStatus
    posture: controller_posture.PostureBanner
    takeover_plan: takeover_runtime.TakeoverPlan
    gate_cycle: dict[str, Any]
    standby_liveness: StandbyLiveness

    @property
    def base_clean(self) -> bool:
        return bool(
            self.takeover_plan.predecessor_detected
            and self.takeover_plan.ring0_ok
            and self.gate_cycle["no_side_effects"]
            and not self.gate_cycle["forbidden_mechanics_present"]
        )

    @property
    def status(self) -> str:
        if not self.base_clean:
            return "RED"
        if not self.standby_liveness.ok:
            return "WARNING"
        return "GREEN"

    @property
    def clean(self) -> bool:
        return self.status == "GREEN"

    @property
    def exit_code(self) -> int:
        return 1 if self.status == "RED" else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": DRILL_KIND,
            "schema_version": SCHEMA_VERSION,
            "repo_root": str(self.repo_root),
            "predecessor": self.predecessor,
            "selected_harness": self.harness,
            "run_at": self.run_at,
            "host_id": self.host_id,
            "cadence": self.cadence.to_dict(),
            "posture": self.posture.to_dict(),
            "takeover_evidence": self.takeover_plan.to_dict(),
            "benign_gate_cycle": self.gate_cycle,
            "standby_liveness": self.standby_liveness.to_dict(),
            "status": self.status,
            "clean": self.clean,
        }

    def format_lines(self) -> list[str]:
        clean = "CLEAN" if self.status == "GREEN" else self.status
        lines = [
            f"ce continuity-drill: {clean}",
            f"cadence: {self.cadence.phase} ({self.cadence.reason})",
            f"required: {'true' if self.cadence.required else 'false'}",
            f"consecutive clean runs: {self.cadence.consecutive_clean_runs}",
            f"next due: {self.cadence.next_due}",
            f"predecessor: {self.predecessor} "
            f"({'detected' if self.takeover_plan.predecessor_detected else 'not detected'})",
            f"selected harness: {self.harness}",
            f"run at: {self.run_at}",
            f"host id: {self.host_id}",
            f"Ring-0 verify: {'PASS' if self.takeover_plan.ring0_ok else 'WOULD-REFUSE'}",
            f"standby liveness: {self.standby_liveness.status} ({self.standby_liveness.note})",
            f"posture allowed: {self.posture.allowed_posture}",
            "benign governed gate cycle:",
        ]
        for step in self.gate_cycle["steps"]:
            lines.append(f"  - {step['name']}: {step['status']} (execute={str(step['execute']).lower()})")
        lines.append(
            "forbidden mechanics: "
            + ("present" if self.gate_cycle["forbidden_mechanics_present"] else "absent")
        )
        return lines


def parse_prior_run(value: str) -> PriorRun:
    if ":" not in value:
        raise InvalidRunHistory(
            f"prior run {value!r} must use YYYY-MM-DD:clean or YYYY-MM-DD:failed"
        )
    raw_date, raw_status = value.split(":", 1)
    try:
        run_date = date.fromisoformat(raw_date.strip())
    except ValueError as exc:
        raise InvalidRunHistory(f"invalid prior run date {raw_date!r}") from exc
    status = raw_status.strip().lower()
    if status not in (_CLEAN_STATUSES | _DIRTY_STATUSES):
        raise InvalidRunHistory(
            f"invalid prior run status {raw_status!r}; expected clean or failed"
        )
    return PriorRun(run_date=run_date, status="clean" if status in _CLEAN_STATUSES else "failed")


def _normalize_prior_runs(prior_runs: Iterable[PriorRun] | None) -> tuple[PriorRun, ...]:
    return tuple(sorted(prior_runs or (), key=lambda run: run.run_date, reverse=True))


def _consecutive_clean_runs(prior_runs: Sequence[PriorRun]) -> int:
    count = 0
    for run in prior_runs:
        if not run.clean:
            break
        count += 1
    return count


def _parse_as_of(value: str | date | None) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidRunHistory(f"invalid --as-of date {value!r}") from exc


def _current_run_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compute_cadence(
    *,
    as_of: str | date | None = None,
    prior_runs: Iterable[PriorRun] | None = None,
    promotion_candidate: bool = False,
) -> CadenceStatus:
    resolved_as_of = _parse_as_of(as_of)
    runs = _normalize_prior_runs(prior_runs)
    clean_count = _consecutive_clean_runs(runs)
    weekly_phase = clean_count < REQUIRED_CLEAN_RUNS
    phase = "weekly-until-two-clean-runs" if weekly_phase else "promotion-gated"
    if promotion_candidate:
        return CadenceStatus(
            as_of=resolved_as_of,
            phase=phase,
            required=True,
            reason="controller_substrate_promotion",
            consecutive_clean_runs=clean_count,
            next_due="before-controller-substrate-promotion",
            prior_runs=runs,
            promotion_candidate=True,
        )

    if not weekly_phase:
        return CadenceStatus(
            as_of=resolved_as_of,
            phase=phase,
            required=False,
            reason="two_consecutive_clean_runs_satisfied",
            consecutive_clean_runs=clean_count,
            next_due="before-controller-substrate-promotion",
            prior_runs=runs,
            promotion_candidate=False,
        )

    last_date = runs[0].run_date if runs else None
    due = resolved_as_of if last_date is None else last_date + timedelta(days=WEEKLY_INTERVAL_DAYS)
    required = last_date is None or resolved_as_of >= due
    return CadenceStatus(
        as_of=resolved_as_of,
        phase=phase,
        required=required,
        reason="weekly_due" if required else "weekly_not_due",
        consecutive_clean_runs=clean_count,
        next_due=due.isoformat(),
        prior_runs=runs,
        promotion_candidate=False,
    )


def build_record(
    *,
    predecessor: str,
    harness: str,
    repo_root: str | Path,
    as_of: str | date | None = None,
    prior_runs: Iterable[PriorRun] | None = None,
    promotion_candidate: bool = False,
    environ: Mapping[str, str] | None = None,
    which: Any | None = None,
    standby_liveness: bool | Mapping[str, Any] | None = None,
) -> DrillRecord:
    root = Path(repo_root).resolve()
    cadence = compute_cadence(
        as_of=as_of,
        prior_runs=prior_runs,
        promotion_candidate=promotion_candidate,
    )
    posture = controller_posture.collect_posture(
        repo_root=root,
        environ=environ,
        role="controller",
        harness=harness,
        launch_mode="governed-drill",
    )
    takeover_plan = takeover_runtime.build_plan(
        predecessor=predecessor,
        harness=harness,
        repo_root=root,
        dry_run=True,
        which=which,
    )
    resolved_standby_liveness = _standby_liveness_from_context(
        standby_liveness=standby_liveness,
        environ=environ,
    )
    gate_cycle = _gate_cycle_proof(
        posture=posture,
        takeover_plan=takeover_plan,
        standby_liveness=resolved_standby_liveness,
    )
    return DrillRecord(
        predecessor=predecessor,
        harness=harness,
        repo_root=root,
        run_at=_current_run_at(),
        host_id=seat_lifecycle.default_host_id(),
        cadence=cadence,
        posture=posture,
        takeover_plan=takeover_plan,
        gate_cycle=gate_cycle,
        standby_liveness=resolved_standby_liveness,
    )


def _standby_liveness_from_context(
    *,
    standby_liveness: bool | Mapping[str, Any] | None,
    environ: Mapping[str, str] | None,
) -> StandbyLiveness:
    if standby_liveness is not None:
        return _standby_liveness_from_value(standby_liveness)

    env = environ or {}
    raw_json = env.get("CE_STANDBY_LIVENESS_JSON")
    if raw_json:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            return StandbyLiveness(
                ok=False,
                status="WARNING",
                note=f"invalid CE_STANDBY_LIVENESS_JSON: {exc}",
                evidence={"source": "CE_STANDBY_LIVENESS_JSON"},
            )
        if isinstance(payload, Mapping):
            return _standby_liveness_from_value(payload)
        return StandbyLiveness(
            ok=False,
            status="WARNING",
            note="CE_STANDBY_LIVENESS_JSON must decode to an object",
            evidence={"source": "CE_STANDBY_LIVENESS_JSON"},
        )

    raw_flag = env.get("CE_STANDBY_LIVENESS")
    if raw_flag is not None:
        return StandbyLiveness(
            ok=False,
            status="WARNING",
            note=(
                "CE_STANDBY_LIVENESS is not accepted as standby proof; expected "
                "CE_STANDBY_LIVENESS_JSON from ce takeover --dry-run --json"
            ),
            evidence={"source": "CE_STANDBY_LIVENESS", "value": raw_flag},
        )

    return StandbyLiveness(
        ok=False,
        status="WARNING",
        note=STANDBY_LIVENESS_ABSENT_NOTE,
        evidence={"source": "absent"},
    )


def _standby_liveness_from_value(value: bool | Mapping[str, Any]) -> StandbyLiveness:
    if isinstance(value, bool):
        return StandbyLiveness(
            ok=False,
            status="WARNING",
            note=(
                "standby liveness requires structured ce takeover --dry-run --json "
                "evidence"
            ),
            evidence={"source": "boolean"},
        )

    evidence = dict(value)
    ring0_verify = evidence.get("ring0_verify", {})
    if not isinstance(ring0_verify, Mapping):
        ring0_verify = {}
    ring0_ok = ring0_verify.get("ok") is True
    initial_state_ok = evidence.get("initial_state") == "AWAITING-OPERATOR"
    ok = ring0_ok and initial_state_ok
    if ok:
        note = "standby emitted valid ce takeover --dry-run --json packet"
    else:
        note = (
            "standby liveness packet invalid: expected ring0_verify.ok=true and "
            "initial_state=AWAITING-OPERATOR"
        )
    return StandbyLiveness(
        ok=ok,
        status="PASS" if ok else "WARNING",
        note=note,
        evidence=evidence,
    )


def _gate_cycle_proof(
    *,
    posture: controller_posture.PostureBanner,
    takeover_plan: takeover_runtime.TakeoverPlan,
    standby_liveness: StandbyLiveness,
) -> dict[str, Any]:
    takeover_actions = [dict(action) for action in takeover_plan.hydration_actions]
    steps = [
        {
            "name": "collect-posture-banner",
            "status": "PASS",
            "execute": False,
            "evidence": {"allowed_posture": posture.allowed_posture},
        },
        {
            "name": "build-takeover-evidence-packet",
            "status": "PASS" if takeover_plan.predecessor_detected else "NEEDS-EVIDENCE",
            "execute": False,
            "evidence": {
                "predecessor_detected": takeover_plan.predecessor_detected,
                "evidence_gap_count": len(takeover_plan.evidence_gaps),
            },
        },
        {
            "name": "verify-ring0-harness",
            "status": "PASS" if takeover_plan.ring0_ok else "WOULD-REFUSE",
            "execute": False,
            "evidence": {"ring0_ok": takeover_plan.ring0_ok},
        },
        {
            "name": "plan-governed-gate-cycle",
            "status": "PASS",
            "execute": False,
            "evidence": {
                "review_decision": "not-submitted",
                "queue_decision": "not-submitted",
                "merge_decision": "not-submitted",
            },
        },
        {
            "name": "verify-standby-liveness",
            "status": "PASS" if standby_liveness.ok else "WARNING",
            "execute": False,
            "evidence": standby_liveness.to_dict(),
        },
    ]
    step_side_effects = [step for step in steps if step.get("execute") is not False]
    takeover_side_effects = [action for action in takeover_actions if action.get("execute") is not False]
    forbidden_mechanics = _forbidden_mechanics(steps=steps, takeover_actions=takeover_actions)
    return {
        "without_predecessor_chat_history": True,
        "proof_mode": "plan-only",
        "steps": steps,
        "takeover_actions": takeover_actions,
        "forbidden_mechanics": forbidden_mechanics,
        "forbidden_mechanics_present": any(item["present"] for item in forbidden_mechanics),
        "side_effect_violations": [*step_side_effects, *takeover_side_effects],
        "no_side_effects": not step_side_effects and not takeover_side_effects,
    }


def _forbidden_mechanics(
    *,
    steps: Sequence[Mapping[str, Any]],
    takeover_actions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates = [*steps, *takeover_actions]
    return [
        {"mechanic": mechanic, "present": _mechanic_present(mechanic, candidates)}
        for mechanic in FORBIDDEN_MECHANICS
    ]


def _mechanic_present(mechanic: str, candidates: Sequence[Mapping[str, Any]]) -> bool:
    needles = _mechanic_needles(mechanic)
    for candidate in candidates:
        if candidate.get("execute") is False:
            continue
        text = " ".join(
            str(candidate.get(key, ""))
            for key in ("name", "action", "detail", "status")
        ).lower()
        if any(needle in text for needle in needles):
            return True
    return False


def _mechanic_needles(mechanic: str) -> tuple[str, ...]:
    normalized = mechanic.replace("_", "-")
    return (mechanic, normalized, *tuple(part for part in normalized.split("-") if part))


def abort_record(
    *,
    predecessor: str,
    harness: str,
    repo_root: str | Path,
    error: Exception,
) -> dict[str, Any]:
    code = getattr(error, "code", ContinuityDrillError.code)
    return {
        "kind": DRILL_KIND,
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(Path(repo_root).resolve()),
        "predecessor": predecessor,
        "selected_harness": harness,
        "run_at": _current_run_at(),
        "host_id": seat_lifecycle.default_host_id(),
        "clean": False,
        "aborted": True,
        "error_code": code,
        "error": str(error),
    }


def render_json(record: DrillRecord) -> str:
    return json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n"


def render_abort_json(
    *,
    predecessor: str,
    harness: str,
    repo_root: str | Path,
    error: Exception,
) -> str:
    return json.dumps(
        abort_record(
            predecessor=predecessor,
            harness=harness,
            repo_root=repo_root,
            error=error,
        ),
        indent=2,
        sort_keys=True,
    ) + "\n"
