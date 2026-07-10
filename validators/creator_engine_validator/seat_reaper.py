"""Automated seat/venue retirement reaper — the substrate-neutral POLICY fold (ce-ops#43).

The reaper mechanizes the manual retirement runbook (archive transcript → kill
pane → remove worktree → release the instance-local ledger markers), triggered by
the **terminal lifecycle facts** the seat sentinel (ce-ops#26) writes — never by
orchestrator memory, live pane discovery, or inferred scheduler intent.

This module is the POLICY layer:

- it folds local state ONLY (dispatch records, sentinel events, runtime-evidence
  chains, escalation records, the active-work ledger markers, and the reaper's own
  private ledger) and classifies each observed seat into exactly one bucket;
- it RE-IMPLEMENTS the seat-sentinel outcome resolution READ-ONLY — it never calls
  ``seat_sentinel.resolve_outcome()`` (which APPENDS an ``outcome_resolved`` event
  and would forge writer-provenance + mutate the trigger surface on every pass);
- it orchestrates the ordered retirement pipeline (lock → archive → close venue →
  release worktree/markers → record), delegating every IRREVERSIBLE substrate
  action to an injected executor selected by the venue substrate (§3.5);
- it NEVER shells out to tmux, git, or a worker runtime directly. The policy is
  substrate-neutral; the executor is per-substrate (``reaper_executors``).

Version boundary (§3.6): this is a V3_RUNTIME module. It imports NO V1_RUNTIME
module. It reads ``seat_sentinel`` (a *shared*-classified module) as DATA for its
tolerant readers + contract constants. All crossings to the v1 transcript-archive
and ``pco-release`` legs happen inside the executor as subprocess+DATA.

Read-only discipline (§4.1): ``status`` and the EVALUATION phase of ``once``/
``watch`` write NOTHING — they never append to ``events.jsonl`` and never write a
dispatch, escalation, reaper-ledger, archive, or pane-registry record.

See ``docs/operations/SEAT_REAPER_PROTOCOL.md`` for the prose contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, Sequence

import yaml

from . import seat_sentinel
from .schema import validate_with_schema

# --- contract constants ----------------------------------------------------

SCHEMA_VERSION = "1"

#: Local-state subtrees the fold reads (relative to the v3 state root).
DISPATCHES_SUBDIR = seat_sentinel.DISPATCHES_SUBDIR  # "dispatches"
RUNS_SUBDIR = seat_sentinel.RUNS_SUBDIR  # "runs"
ESCALATIONS_SUBDIR = "escalations"
REAPER_SUBDIR = "reaper"
REAPER_LEDGER_FILENAME = "ledger.ndjson"

#: The active-work ledger root + transcript-archive root are instance-local paths
#: the v1 launch substrate owns; the v3 reaper never bakes that path literal (the
#: v3 surface stays bootstrapping-harness-residue-free, the cockpit_readmodel
#: pattern). They are supplied by the operator via the CLI flag or these env vars.
LEDGER_ROOT_ENV = "CE_LEDGER_ROOT"
ARCHIVE_ROOT_ENV = "CE_TRANSCRIPT_ARCHIVE_ROOT"

_ESCALATION_SCHEMA = "schemas/escalation-record.schema.yaml"

#: A clean-exited seat whose outcome cannot be resolved is benign while collect
#: has simply not run yet; once it stays unresolvable past this window it
#: escalates through the staleness tier (§3.1/§5.2). Seconds.
DEFAULT_GRACE_SECONDS = 1800  # 30 minutes

#: A launched-no-exited seat with a live pid is only treated as a stale dangling
#: launched (→ escalation) once no new event has arrived for this window (§3.4).
DEFAULT_STALE_SECONDS = 3600  # 1 hour

# --- classifications (§5.2) -------------------------------------------------

CLASS_ELIGIBLE = "eligible"
CLASS_CONSERVED = "conserved"
CLASS_ARCHIVE_THEN_RETIRE = "archive_then_retire"
CLASS_ESCALATE_UNCLEAN_STOP = "escalate_unclean_stop"
CLASS_ESCALATE_UNRESOLVED_OUTCOME = "escalate_unresolved_outcome"
CLASS_ESCALATE_MISSING_ARCHIVE = "escalate_missing_archive"
CLASS_ESCALATE_UNKNOWN_EXECUTOR = "escalate_unknown_executor"
CLASS_ACTIVE_OR_UNKNOWN = "active_or_unknown"
CLASS_ALREADY_RETIRED = "already_retired"
CLASS_FAILED = "failed"

#: The classifications that, when re-run with a real executor, drive a teardown.
_RETIREABLE = frozenset({CLASS_ELIGIBLE, CLASS_ARCHIVE_THEN_RETIRE})
_ESCALATING = frozenset(
    {
        CLASS_ESCALATE_UNCLEAN_STOP,
        CLASS_ESCALATE_UNRESOLVED_OUTCOME,
        CLASS_ESCALATE_MISSING_ARCHIVE,
        CLASS_ESCALATE_UNKNOWN_EXECUTOR,
    }
)

# --- per-step result statuses (§9) ------------------------------------------

STEP_SUCCEEDED = "succeeded"
STEP_ALREADY_SATISFIED = "already_satisfied"
STEP_NOT_APPLICABLE = "not_applicable"
STEP_FAILED = "failed"

# --- release-reason mapping (§6.4) ------------------------------------------

RELEASE_REASON_COMPLETED = "completed"
RELEASE_REASON_ABORTED = "aborted"

# --- supported substrates ---------------------------------------------------

SUBSTRATE_TMUX = "tmux"


# ---------------------------------------------------------------------------
# Time helpers (injectable for determinism)
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(value: Any) -> datetime | None:
    """Parse a sentinel ``ts`` (``%Y-%m-%dT%H:%M:%SZ``) to an aware datetime, else None."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _default_pid_alive(pid: int) -> bool:
    """Best-effort liveness probe (read-only): ``os.kill(pid, 0)`` semantics."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    except (OSError, OverflowError, ValueError):
        return False
    return True


# ---------------------------------------------------------------------------
# Read-only outcome resolution (§3.1) — re-implements seat_sentinel.resolve_outcome
# WITHOUT the write. seat_sentinel.resolve_outcome APPENDS an outcome_resolved
# event; calling it from the reaper would forge writer-provenance + mutate the
# trigger surface on every evaluation pass. We read the chain as DATA only.
# ---------------------------------------------------------------------------


def resolve_outcome_readonly(
    events: Sequence[dict[str, Any]], state_root: Path, *, run_id: str | None = None
) -> tuple[str | None, str]:
    """Return ``(outcome, outcome_source)`` for a seat WITHOUT writing anything.

    Mirrors ``seat_sentinel.resolve_outcome`` exactly: read the ``launched``
    event's ``run_id``, read ``<state_root>/runs/<run_id>.runtime-evidence.yaml``
    when present, and let the LAST in-enum outcome record win. Chain absent or
    unreadable ⇒ ``(None, "unresolved")``; chain present ⇒ source is
    ``runtime_evidence`` even if no in-enum outcome is found.
    """
    rid = run_id
    if rid is None:
        for event in events:
            if event.get("event") == seat_sentinel.EVENT_LAUNCHED:
                candidate = event.get("run_id")
                rid = candidate if isinstance(candidate, str) and candidate else None
                break
    if not rid:
        return None, seat_sentinel.OUTCOME_SOURCE_UNRESOLVED

    chain_path = state_root / RUNS_SUBDIR / f"{rid}{seat_sentinel.CHAIN_SUFFIX}"
    if not chain_path.is_file():
        return None, seat_sentinel.OUTCOME_SOURCE_UNRESOLVED
    try:
        doc = yaml.safe_load(chain_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None, seat_sentinel.OUTCOME_SOURCE_UNRESOLVED
    if not isinstance(doc, dict):
        return None, seat_sentinel.OUTCOME_SOURCE_UNRESOLVED

    outcome: str | None = None
    records = doc.get("records")
    if isinstance(records, list):
        for rec in reversed(records):
            if isinstance(rec, dict) and rec.get("outcome") in seat_sentinel.OUTCOME_ENUM:
                outcome = rec["outcome"]
                break
    return outcome, seat_sentinel.OUTCOME_SOURCE_RUNTIME_EVIDENCE


# ---------------------------------------------------------------------------
# The executor contract (§3.5) — the policy delegates IRREVERSIBLE actions here.
# reaper_executors implements TmuxExecutor against this protocol.
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """One pipeline step's recorded result (the honest per-step accounting, §9)."""

    status: str  # STEP_SUCCEEDED | STEP_ALREADY_SATISFIED | STEP_NOT_APPLICABLE | STEP_FAILED
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (STEP_SUCCEEDED, STEP_ALREADY_SATISFIED, STEP_NOT_APPLICABLE)


@dataclass
class RetirementPlan:
    """The value-free inputs an executor needs to retire one seat's venue."""

    seat_id: str
    run_id: str
    classification: str
    release_reason: str
    state_root: Path
    dispatch: dict[str, Any]
    dispatch_path: Path
    events_path: Path
    archive_root: Path | None
    batch_slug: str
    role: str
    terminal: dict[str, Any] | None
    harness_session_id: str | None
    transcript_ref: str | None
    archive_expected: bool
    # pco binding (None when the seat allocated no secondary worktree)
    lane_id: str | None
    controller_id: str | None
    ledger_root: Path | None
    worktree_path: Path | None
    pane_registry_path: Path | None


class Executor(Protocol):
    """Per-substrate IRREVERSIBLE-action surface the policy delegates to (§3.5)."""

    substrate: str

    def archive_transcript(self, plan: RetirementPlan) -> StepResult: ...

    def close_venue(self, plan: RetirementPlan) -> StepResult: ...

    def release_worktree(self, plan: RetirementPlan) -> StepResult: ...


#: A factory ``(terminal_kind | None) -> Executor | None``. Returns None for an
#: unsupported substrate (→ escalate_unknown_executor). Injected so tests fake it.
ExecutorFor = Callable[[str | None], "Executor | None"]


def _default_executor_for(terminal_kind: str | None) -> Executor | None:
    # Lazy import keeps the policy module free of any executor/substrate coupling
    # at import time (the policy stays substrate-neutral).
    from . import reaper_executors

    return reaper_executors.default_executor_for(terminal_kind)


# ---------------------------------------------------------------------------
# Discovery (§5.1)
# ---------------------------------------------------------------------------


@dataclass
class SeatObservation:
    seat_id: str
    run_id: str
    dispatch: dict[str, Any] | None
    dispatch_path: Path | None
    events: list[dict[str, Any]]
    events_path: Path


def _iter_dispatch_dirs(state_root: Path) -> list[Path]:
    base = state_root / DISPATCHES_SUBDIR
    if not base.is_dir():
        return []
    return [d for d in sorted(base.iterdir()) if d.is_dir()]


def _load_dispatch(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def discover_seats(state_root: Path) -> list[SeatObservation]:
    """Fold every seat under ``<state_root>/dispatches/*`` (dispatch + events as DATA)."""
    out: list[SeatObservation] = []
    for d in _iter_dispatch_dirs(state_root):
        seat_id = d.name
        dispatch_path = d / "dispatch.yaml"
        events_path = d / seat_sentinel.EVENTS_FILENAME
        dispatch = _load_dispatch(dispatch_path) if dispatch_path.is_file() else None
        events = list(seat_sentinel.iter_events_file(events_path))
        if dispatch is None and not events:
            continue  # not a seat surface
        run_id = ""
        if dispatch and isinstance(dispatch.get("run_id"), str):
            run_id = dispatch["run_id"]
        if not run_id:
            for ev in events:
                if ev.get("event") == seat_sentinel.EVENT_LAUNCHED and isinstance(
                    ev.get("run_id"), str
                ):
                    run_id = ev["run_id"]
                    break
        if not run_id:
            run_id = seat_id
        out.append(
            SeatObservation(
                seat_id=seat_id,
                run_id=run_id,
                dispatch=dispatch,
                dispatch_path=dispatch_path if dispatch is not None else None,
                events=events,
                events_path=events_path,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Pane-registry / pco-binding resolution (§2.4) — read-only correlation
# ---------------------------------------------------------------------------


def _iter_pane_records(ledger_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    panes = ledger_root / "panes"
    if not panes.is_dir():
        return []
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(panes.rglob("*.yaml")):
        if ".tmp." in path.name:
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(data, dict):
            out.append((path, data))
    return out


def _resolve_pco_binding(
    seat: SeatObservation, ledger_root: Path | None
) -> tuple[Path | None, dict[str, Any] | None]:
    """Find the pane-registry record bound to this seat (lane_id==run_id, or pane match).

    Returns ``(pane_registry_path, pane_record)`` or ``(None, None)`` when the seat
    allocated no secondary worktree (a plain in-place dispatch seat).
    """
    if ledger_root is None or not ledger_root.is_dir():
        return None, None
    terminal = (seat.dispatch or {}).get("terminal") or {}
    want_pane = terminal.get("pane_id") if isinstance(terminal, dict) else None
    by_pane: tuple[Path, dict[str, Any]] | None = None
    for path, rec in _iter_pane_records(ledger_root):
        if rec.get("lane_id") == seat.run_id:
            return path, rec
        rec_term = rec.get("terminal") or {}
        if (
            want_pane
            and isinstance(rec_term, dict)
            and rec_term.get("pane_id") == want_pane
            and by_pane is None
        ):
            by_pane = (path, rec)
    if by_pane is not None:
        return by_pane
    return None, None


# ---------------------------------------------------------------------------
# Reaper private ledger (§6.5)
# ---------------------------------------------------------------------------


def _reaper_ledger_path(state_root: Path) -> Path:
    return state_root / REAPER_SUBDIR / REAPER_LEDGER_FILENAME


def load_reaper_ledger(state_root: Path) -> list[dict[str, Any]]:
    """Tolerant read of the reaper's append-only NDJSON ledger (missing ⇒ empty)."""
    path = _reaper_ledger_path(state_root)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _retired_seat_ids(ledger: Iterable[dict[str, Any]]) -> set[str]:
    return {
        str(e.get("seat_id"))
        for e in ledger
        if e.get("action") == "reap_retire" and e.get("seat_id")
    }


def _append_reaper_ledger(state_root: Path, entry: dict[str, Any]) -> None:
    path = _reaper_ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")


# ---------------------------------------------------------------------------
# Escalation emission (§7) — normal escalation records, deterministic, deduped.
# ---------------------------------------------------------------------------

_ESCALATION_COPY: dict[str, tuple[str, str, str]] = {
    "unclean-stop": (
        "Seat launched but no terminal sentinel exit",
        "Inspect the dispatch and decide whether to collect evidence, manually "
        "retire, or conserve.",
        "Do not run automatic retirement until a clean terminal outcome or explicit "
        "operator decision exists.",
    ),
    "stale-launched": (
        "Seat launched with no new sentinel event past the staleness window",
        "Inspect whether the seat is hung or its wrapper died, then collect, "
        "manually retire, or conserve.",
        "Do not kill the pane or release the worktree; reconcile the dangling "
        "launched seat first (composes with ce-ops#35).",
    ),
    "missing-events": (
        "Spawned dispatch has no usable sentinel events",
        "Inspect why the events surface is missing or unparseable before any "
        "teardown.",
        "Do not auto-retire; the terminal state cannot be trusted without events.",
    ),
    "unresolved-outcome": (
        "Terminal exit observed but outcome remains unresolvable past the grace window",
        "Inspect why the runtime-evidence chain never resolved (cev3 collect may "
        "have failed) and decide how to retire.",
        "Archive is conserved by archive-before-remove; resolve the outcome or "
        "retire manually after inspection.",
    ),
    "missing-archive": (
        "Archive required for retirement could not be produced",
        "Inspect the missing/ambiguous transcript and decide whether to salvage "
        "or conserve.",
        "Do not tear down the venue until the evidence is archived.",
    ),
    "unknown-executor": (
        "Seat venue substrate has no safe retirement executor",
        "Decide how the venue substrate should be torn down before retirement.",
        "Do not perform any teardown for an unknown substrate.",
    ),
    "root-checkout-refused": (
        "pco-release refused the root checkout",
        "Inspect the worktree binding; pco-release must run from a secondary "
        "worktree, never the root checkout.",
        "Do not bypass the root-checkout refusal; correct the binding or retire "
        "manually.",
    ),
    "pco-release-failed": (
        "pco-release failed during automatic retirement",
        "Inspect the claim/lease/worktree state and decide how to finish the "
        "release.",
        "Preserve the verified archive and pane-close state; do not retry blindly.",
    ),
    "pane-registry-failed": (
        "Pane registry write failed after archive during retirement",
        "Inspect the pane registry record before advancing to worktree release.",
        "Preserve the verified archive; do not release the worktree until the "
        "registry outcome is verified.",
    ),
    "worktree-verify-failed": (
        "Worktree/claim/lease verification failed after release",
        "Inspect the post-release ledger and worktree state to confirm the "
        "release actually completed.",
        "Do not attempt a second destructive pass until the state is verified.",
    ),
}


def _escalation_digest(seat_id: str, reason: str, source_ref: str) -> str:
    raw = f"{seat_id}|{reason}|{source_ref}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def build_escalation(
    *,
    seat_id: str,
    reason: str,
    source_ref: str,
    created_at: str,
    operator_guidance: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a schema-valid escalation record for a reaper refusal/escalation case."""
    title, decision, recommendation = _ESCALATION_COPY[reason]
    if reason == "stale-launched" and operator_guidance:
        session_id = operator_guidance.get("session_id")
        command = operator_guidance.get("command")
        if session_id and command:
            decision = (
                f"{decision} Live tmux session {session_id!r} is still present."
            )
            recommendation = (
                f"Clear the named stale launch surface with `{command}`, then rerun "
                "`ce reap once`."
            )
    digest = _escalation_digest(seat_id, reason, source_ref)
    return {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": f"reaper-{reason}-{digest}",
        "title": title,
        "decision_needed": decision,
        "recommendation": recommendation,
        "source_ref": source_ref,
        "created_at": created_at,
    }


def _escalation_path(state_root: Path, escalation_id: str) -> Path:
    return state_root / ESCALATIONS_SUBDIR / f"{escalation_id}.yaml"


def _validate_escalation(record: dict[str, Any], path: Path) -> list[str]:
    return [
        e.format()
        for e in validate_with_schema(
            record,
            _ESCALATION_SCHEMA,
            path,
            code="VAL-ESCALATION-RECORD-SCHEMA",
            contract=_ESCALATION_SCHEMA,
        )
    ]


# ---------------------------------------------------------------------------
# Classification (§5.2) — pure, deterministic
# ---------------------------------------------------------------------------


@dataclass
class Classification:
    classification: str
    reason: str | None = None  # escalation reason key when escalating
    outcome: str | None = None
    outcome_source: str = seat_sentinel.OUTCOME_SOURCE_UNRESOLVED
    source_ref: str = ""
    operator_guidance: dict[str, str] = field(default_factory=dict)


def _source_ref(seat: SeatObservation) -> str:
    """Where an escalation/record points: events.jsonl when present, else dispatch.yaml."""
    if seat.events_path.is_file():
        return f"{DISPATCHES_SUBDIR}/{seat.seat_id}/{seat_sentinel.EVENTS_FILENAME}"
    return f"{DISPATCHES_SUBDIR}/{seat.seat_id}/dispatch.yaml"


def _launched_pid(events: Sequence[dict[str, Any]]) -> int | None:
    for ev in events:
        if ev.get("event") == seat_sentinel.EVENT_LAUNCHED:
            pid = ev.get("pid")
            if isinstance(pid, int):
                return pid
    return None


def _stale_launch_guidance(dispatch: dict[str, Any]) -> dict[str, str]:
    terminal = dispatch.get("terminal") if isinstance(dispatch.get("terminal"), dict) else None
    if not terminal or terminal.get("kind") != SUBSTRATE_TMUX:
        return {}
    session_id = terminal.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return {}
    command = f"tmux kill-session -t {shlex.quote(session_id)}"
    return {
        "session_id": session_id,
        "command": command,
        "next_command": "ce reap once",
    }


def _last_event_ts(events: Sequence[dict[str, Any]]) -> datetime | None:
    latest: datetime | None = None
    for ev in events:
        ts = _parse_ts(ev.get("ts"))
        if ts and (latest is None or ts > latest):
            latest = ts
    return latest


def _exit_ts(events: Sequence[dict[str, Any]]) -> datetime | None:
    latest: datetime | None = None
    for ev in events:
        if ev.get("event") == seat_sentinel.EVENT_EXITED:
            ts = _parse_ts(ev.get("ts"))
            if ts and (latest is None or ts > latest):
                latest = ts
    return latest


def classify_seat(
    seat: SeatObservation,
    *,
    state_root: Path,
    now: datetime,
    retired_ids: set[str],
    executor_for: ExecutorFor,
    pid_alive: Callable[[int], bool],
    grace_seconds: int,
    stale_seconds: int,
) -> Classification:
    """Map ONE observed seat to exactly one classification (deterministic)."""
    src = _source_ref(seat)
    dispatch = seat.dispatch or {}

    # already retired (ledger says so) — verified-enough for idempotency (§12)
    if seat.seat_id in retired_ids:
        return Classification(CLASS_ALREADY_RETIRED, source_ref=src)

    # conserved marker = ABSOLUTE stop (§3.2), even when terminal
    if bool(dispatch.get("conserve")):
        return Classification(CLASS_CONSERVED, source_ref=src)

    has_launched = any(e.get("event") == seat_sentinel.EVENT_LAUNCHED for e in seat.events)
    has_exited = any(e.get("event") == seat_sentinel.EVENT_EXITED for e in seat.events)
    spawned = bool(dispatch.get("spawned_at") or dispatch.get("terminal"))
    spawn_failed = bool(dispatch.get("spawn_failed_at"))
    terminal = dispatch.get("terminal") if isinstance(dispatch.get("terminal"), dict) else None
    terminal_kind = terminal.get("kind") if terminal else None

    # failed/refused spawn with no conserve marker → archive-then-retire (§3.2 case 2)
    if spawn_failed:
        if terminal is not None and executor_for(terminal_kind) is None:
            return Classification(
                CLASS_ESCALATE_UNKNOWN_EXECUTOR, reason="unknown-executor", source_ref=src
            )
        return Classification(CLASS_ARCHIVE_THEN_RETIRE, source_ref=src)

    # spawned but no usable events at all → cannot trust terminal state (§3.3)
    if spawned and not seat.events:
        return Classification(
            CLASS_ESCALATE_UNCLEAN_STOP, reason="missing-events", source_ref=src
        )

    # never spawned and not failure-stamped → in-flight front-gate artifact, skip
    if not spawned and not has_launched:
        return Classification(CLASS_ACTIVE_OR_UNKNOWN, source_ref=src)

    # launched without a terminal exit → unclean/unknown OR still live (§3.3/§3.4)
    if has_launched and not has_exited:
        pid = _launched_pid(seat.events)
        alive = pid is not None and pid_alive(pid)
        last_ts = _last_event_ts(seat.events)
        stale = last_ts is None or (now - last_ts).total_seconds() > stale_seconds
        if alive and not stale:
            return Classification(CLASS_ACTIVE_OR_UNKNOWN, source_ref=src)
        reason = "stale-launched" if alive else "unclean-stop"
        guidance = _stale_launch_guidance(dispatch) if reason == "stale-launched" else {}
        return Classification(
            CLASS_ESCALATE_UNCLEAN_STOP,
            reason=reason,
            source_ref=src,
            operator_guidance=guidance,
        )

    # launched + exited → terminal-clean candidate; resolve the outcome READ-ONLY
    if has_launched and has_exited:
        outcome, source = resolve_outcome_readonly(seat.events, state_root, run_id=seat.run_id)
        # substrate must have a safe executor when a venue exists
        if terminal is not None and executor_for(terminal_kind) is None:
            return Classification(
                CLASS_ESCALATE_UNKNOWN_EXECUTOR,
                reason="unknown-executor",
                source_ref=src,
                outcome=outcome,
                outcome_source=source,
            )
        # chain absent + unresolved + past grace → escalate (§3.1/§5.2)
        if source == seat_sentinel.OUTCOME_SOURCE_UNRESOLVED:
            exit_ts = _exit_ts(seat.events)
            past_grace = exit_ts is None or (now - exit_ts).total_seconds() > grace_seconds
            if past_grace:
                return Classification(
                    CLASS_ESCALATE_UNRESOLVED_OUTCOME,
                    reason="unresolved-outcome",
                    source_ref=src,
                    outcome=outcome,
                    outcome_source=source,
                )
        return Classification(
            CLASS_ELIGIBLE, source_ref=src, outcome=outcome, outcome_source=source
        )

    # exited without launched, or any other shape → not trusted
    return Classification(CLASS_ESCALATE_UNCLEAN_STOP, reason="missing-events", source_ref=src)


# ---------------------------------------------------------------------------
# Plan assembly + the ordered retirement pipeline (§6)
# ---------------------------------------------------------------------------


def _build_plan(
    seat: SeatObservation,
    cls: Classification,
    *,
    state_root: Path,
    archive_root: Path | None,
    ledger_root: Path | None,
) -> RetirementPlan:
    dispatch = seat.dispatch or {}
    terminal = dispatch.get("terminal") if isinstance(dispatch.get("terminal"), dict) else None
    release_reason = (
        RELEASE_REASON_COMPLETED
        if cls.classification == CLASS_ELIGIBLE
        else RELEASE_REASON_ABORTED
    )
    pane_path, pane_rec = _resolve_pco_binding(seat, ledger_root)
    lane_id = controller_id = None
    worktree_path: Path | None = None
    if pane_rec is not None:
        lane_id = pane_rec.get("lane_id")
        controller_id = pane_rec.get("controller_id")
        wt = pane_rec.get("worktree_path")
        worktree_path = Path(wt) if isinstance(wt, str) and wt else None
    # a clean terminal-clean seat expects a transcript; a failed/refused spawn may not
    archive_expected = cls.classification == CLASS_ELIGIBLE
    return RetirementPlan(
        seat_id=seat.seat_id,
        run_id=seat.run_id,
        classification=cls.classification,
        release_reason=release_reason,
        state_root=state_root,
        dispatch=dispatch,
        dispatch_path=seat.dispatch_path or (state_root / DISPATCHES_SUBDIR / seat.seat_id / "dispatch.yaml"),
        events_path=seat.events_path,
        archive_root=archive_root,
        batch_slug=str(dispatch.get("scope_id") or seat.run_id),
        role=str(dispatch.get("role") or "implementer"),
        terminal=terminal,
        harness_session_id=dispatch.get("harness_session_id"),
        transcript_ref=dispatch.get("transcript_ref"),
        archive_expected=archive_expected,
        lane_id=lane_id,
        controller_id=controller_id,
        ledger_root=ledger_root,
        worktree_path=worktree_path,
        pane_registry_path=pane_path,
    )


@dataclass
class PipelineResult:
    classification: str
    reaped: bool
    failed: bool
    escalate_reason: str | None
    steps: dict[str, StepResult]


def _verify_archive(plan: RetirementPlan, result: StepResult) -> StepResult:
    """Policy-side archive verification (§6.2): file exists, hash matches, evidence intact."""
    if result.status in (STEP_NOT_APPLICABLE, STEP_FAILED):
        return result
    archive_path = result.data.get("archive_path")
    sha = result.data.get("sha256")
    if not archive_path or not sha:
        return StepResult(STEP_FAILED, "archive result missing path/sha", result.data)
    p = Path(archive_path)
    if not p.is_file():
        return StepResult(STEP_FAILED, f"archive file absent: {archive_path}", result.data)
    try:
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError as exc:
        return StepResult(STEP_FAILED, f"archive unreadable: {exc}", result.data)
    if actual != sha:
        return StepResult(STEP_FAILED, "archive hash mismatch", result.data)
    # dispatch + runtime-evidence must still exist after archive (never destroyed)
    if plan.dispatch_path.exists() is False and plan.dispatch:
        return StepResult(STEP_FAILED, "dispatch record vanished during archive", result.data)
    return result


def run_pipeline(
    plan: RetirementPlan, executor: Executor
) -> PipelineResult:
    """Execute the ordered retirement pipeline for ONE eligible/archive-then-retire seat.

    Ordering is the contract (§6): archive is VERIFIED before any pane kill, and
    the worktree is released only after the venue close verifies. A later step
    never runs unless the earlier step's verification passed or was already
    satisfied.
    """
    steps: dict[str, StepResult] = {}

    # Step 1: archive evidence (before any venue/worktree mutation)
    archive = executor.archive_transcript(plan)
    archive = _verify_archive(plan, archive)
    steps["archive"] = archive
    if archive.status == STEP_FAILED:
        reason = "missing-archive" if plan.archive_expected else None
        return PipelineResult(plan.classification, False, True, reason, steps)

    # Step 2: close terminal venue (kill pane, verify absence, update pane registry)
    if plan.terminal is None:
        steps["close_venue"] = StepResult(STEP_NOT_APPLICABLE, "no terminal venue")
    else:
        close = executor.close_venue(plan)
        steps["close_venue"] = close
        if close.status == STEP_FAILED:
            reason = (
                "pane-registry-failed"
                if close.data.get("pane_registry_failed")
                else "unclean-stop"
            )
            return PipelineResult(plan.classification, False, True, reason, steps)

    # Step 3: release worktree + ledger markers via pco-release (subprocess+DATA)
    if plan.lane_id and plan.controller_id and plan.worktree_path is not None:
        release = executor.release_worktree(plan)
        steps["release"] = release
        if release.status == STEP_FAILED:
            if release.data.get("root_checkout_refused"):
                return PipelineResult(plan.classification, False, True, "root-checkout-refused", steps)
            if release.data.get("worktree_verify_failed"):
                return PipelineResult(plan.classification, False, True, "worktree-verify-failed", steps)
            return PipelineResult(plan.classification, False, True, "pco-release-failed", steps)
    else:
        steps["release"] = StepResult(STEP_NOT_APPLICABLE, "no pco worktree binding")

    return PipelineResult(plan.classification, True, False, None, steps)


# ---------------------------------------------------------------------------
# Counters (§9)
# ---------------------------------------------------------------------------


def _empty_step_counts() -> dict[str, int]:
    return {STEP_SUCCEEDED: 0, STEP_ALREADY_SATISFIED: 0, STEP_NOT_APPLICABLE: 0, STEP_FAILED: 0}


# ---------------------------------------------------------------------------
# status (read-only fold, §4.1) and once (fold + one action pass, §4.2)
# ---------------------------------------------------------------------------


def _seat_row(seat: SeatObservation, cls: Classification) -> dict[str, Any]:
    row = {
        "seat_id": seat.seat_id,
        "run_id": seat.run_id,
        "classification": cls.classification,
        "reason": cls.reason,
        "outcome": cls.outcome,
        "outcome_source": cls.outcome_source,
    }
    if cls.operator_guidance:
        row["operator_guidance"] = dict(cls.operator_guidance)
    return row


def reap_status(
    state_root: Path,
    *,
    ledger_root: Path | None = None,
    now: datetime | None = None,
    executor_for: ExecutorFor | None = None,
    pid_alive: Callable[[int], bool] | None = None,
    grace_seconds: int = DEFAULT_GRACE_SECONDS,
    stale_seconds: int = DEFAULT_STALE_SECONDS,
) -> dict[str, Any]:
    """Pure read model: fold + classify + count. Writes NOTHING (§4.1)."""
    now = now or _utc_now()
    executor_for = executor_for or _default_executor_for
    pid_alive = pid_alive or _default_pid_alive
    retired = _retired_seat_ids(load_reaper_ledger(state_root))

    seats = discover_seats(state_root)
    rows: list[dict[str, Any]] = []
    observed = 0
    counts = {
        "eligible": 0,
        "conserved": 0,
        "would_escalate": 0,
        "already_retired": 0,
        "active_or_unknown": 0,
    }
    for seat in seats:
        if seat.dispatch is not None:
            observed += 1
        cls = classify_seat(
            seat,
            state_root=state_root,
            now=now,
            retired_ids=retired,
            executor_for=executor_for,
            pid_alive=pid_alive,
            grace_seconds=grace_seconds,
            stale_seconds=stale_seconds,
        )
        rows.append(_seat_row(seat, cls))
        if cls.classification == CLASS_ELIGIBLE:
            counts["eligible"] += 1
        elif cls.classification == CLASS_ARCHIVE_THEN_RETIRE:
            counts["eligible"] += 1
        elif cls.classification == CLASS_CONSERVED:
            counts["conserved"] += 1
        elif cls.classification in _ESCALATING:
            counts["would_escalate"] += 1
        elif cls.classification == CLASS_ALREADY_RETIRED:
            counts["already_retired"] += 1
        else:
            counts["active_or_unknown"] += 1

    return {
        "action": "reap_status",
        "root": str(state_root),
        "observed_dispatches": observed,
        "eligible": counts["eligible"],
        "conserved": counts["conserved"],
        "would_escalate": counts["would_escalate"],
        "already_retired": counts["already_retired"],
        "active_or_unknown": counts["active_or_unknown"],
        "seats": rows,
    }


def reap_once(
    state_root: Path,
    *,
    ledger_root: Path | None = None,
    repo_root: Path | None = None,
    archive_root: Path | None = None,
    executor_for: ExecutorFor | None = None,
    now: datetime | None = None,
    pid_alive: Callable[[int], bool] | None = None,
    grace_seconds: int = DEFAULT_GRACE_SECONDS,
    stale_seconds: int = DEFAULT_STALE_SECONDS,
    command_id: str | None = None,
    action: str = "reap_once",
) -> dict[str, Any]:
    """One fold + one bounded action pass (§4.2). Returns the honest counter payload."""
    now = now or _utc_now()
    executor_for = executor_for or _default_executor_for
    pid_alive = pid_alive or _default_pid_alive
    repo_root = repo_root or Path.cwd()
    # ledger/archive roots are operator-supplied (flag or env) — the v3 surface
    # never bakes the instance-local path literal. Absent ⇒ the dependent step
    # degrades safely (worktree release / archive become not_applicable / escalate).
    if ledger_root is None:
        env_ledger = os.environ.get(LEDGER_ROOT_ENV)
        ledger_root = Path(env_ledger) if env_ledger else None
    if archive_root is None:
        env_archive = os.environ.get(ARCHIVE_ROOT_ENV)
        archive_root = Path(env_archive) if env_archive else None
    created_at = _rfc3339(now)
    if command_id is None:
        import uuid

        command_id = uuid.uuid4().hex

    retired = _retired_seat_ids(load_reaper_ledger(state_root))
    seats = discover_seats(state_root)

    counters = {
        "observed_dispatches": 0,
        "eligible": 0,
        "reaped": 0,
        "conserved": 0,
        "escalated": 0,
        "skipped_active_or_unknown": 0,
        "already_retired": 0,
        "failed": 0,
    }
    step_counts = _empty_step_counts()
    retirements: list[dict[str, Any]] = []
    escalations: list[dict[str, Any]] = []

    def _emit_escalation(
        seat: SeatObservation,
        reason: str,
        src: str,
        operator_guidance: dict[str, str] | None = None,
    ) -> None:
        record = build_escalation(
            seat_id=seat.seat_id,
            reason=reason,
            source_ref=src,
            created_at=created_at,
            operator_guidance=operator_guidance,
        )
        path = _escalation_path(state_root, record["escalation_id"])
        reused = path.is_file()
        if not reused:
            errs = _validate_escalation(record, path)
            if errs:  # pragma: no cover - our own records are schema-valid by construction
                counters["failed"] += 1
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                yaml.safe_dump(record, sort_keys=True, default_flow_style=False),
                encoding="utf-8",
            )
        counters["escalated"] += 1
        item = {"escalation_id": record["escalation_id"], "reason": reason, "reused": reused}
        if operator_guidance:
            item["operator_guidance"] = dict(operator_guidance)
        escalations.append(item)

    for seat in seats:
        if seat.dispatch is not None:
            counters["observed_dispatches"] += 1
        cls = classify_seat(
            seat,
            state_root=state_root,
            now=now,
            retired_ids=retired,
            executor_for=executor_for,
            pid_alive=pid_alive,
            grace_seconds=grace_seconds,
            stale_seconds=stale_seconds,
        )

        if cls.classification == CLASS_CONSERVED:
            counters["conserved"] += 1
            continue
        if cls.classification == CLASS_ALREADY_RETIRED:
            counters["already_retired"] += 1
            continue
        if cls.classification == CLASS_ACTIVE_OR_UNKNOWN:
            counters["skipped_active_or_unknown"] += 1
            continue
        if cls.classification in _ESCALATING:
            assert cls.reason is not None
            _emit_escalation(seat, cls.reason, cls.source_ref, cls.operator_guidance)
            continue

        # eligible | archive_then_retire — run the ordered pipeline
        terminal = (seat.dispatch or {}).get("terminal")
        terminal_kind = terminal.get("kind") if isinstance(terminal, dict) else None
        executor = executor_for(terminal_kind)
        if executor is None:
            # safety net — classify_seat already escalates this, but never tear down
            _emit_escalation(seat, "unknown-executor", cls.source_ref)
            continue
        counters["eligible"] += 1

        plan = _build_plan(
            seat, cls, state_root=state_root, archive_root=archive_root, ledger_root=ledger_root
        )
        result = run_pipeline(plan, executor)
        for step in result.steps.values():
            step_counts[step.status] = step_counts.get(step.status, 0) + 1

        if result.reaped:
            counters["reaped"] += 1
            entry = {
                "schema_version": SCHEMA_VERSION,
                "action": "reap_retire",
                "seat_id": plan.seat_id,
                "run_id": plan.run_id,
                "dispatch_ref": f"{DISPATCHES_SUBDIR}/{seat.seat_id}/dispatch.yaml",
                "events_ref": f"{DISPATCHES_SUBDIR}/{seat.seat_id}/{seat_sentinel.EVENTS_FILENAME}",
                "terminal_ref": (plan.terminal or {}).get("pane_id"),
                "classification": plan.classification,
                "release_reason": plan.release_reason,
                "steps": {k: {"status": v.status, "detail": v.detail} for k, v in result.steps.items()},
                "archive": result.steps.get("archive", StepResult(STEP_NOT_APPLICABLE)).data,
                "pco_release": result.steps.get("release", StepResult(STEP_NOT_APPLICABLE)).data,
                "timestamp": created_at,
                "command_id": command_id,
            }
            _append_reaper_ledger(state_root, entry)
            retired.add(plan.seat_id)
            retirements.append(
                {"seat_id": plan.seat_id, "run_id": plan.run_id, "classification": plan.classification}
            )
        else:
            counters["failed"] += 1
            if result.escalate_reason:
                _emit_escalation(seat, result.escalate_reason, cls.source_ref)

    return {
        "action": action,
        "root": str(state_root),
        **counters,
        "step_counts": step_counts,
        "retirements": retirements,
        "escalations": escalations,
    }
