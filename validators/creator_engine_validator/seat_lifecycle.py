"""CE-substrate seat lifecycle registry (ce-ops#95 Phase 1).

This shared module owns the spawn-time lifecycle record written under the PCO
ledger. It imports no v1 or v3 runtime modules; launch runtimes pass it plain
data and injectable probe seams. Phase 1 writes the registry/audit surfaces and
registration-failure escalation; later phases can reuse the reader/probe seams
for `ce seats ls`, sampling, and reaper policy.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml

from . import seat_sentinel
from .schema import validate_with_schema

SCHEMA = "schemas/seat-lifecycle.schema.yaml"
SCHEMA_VERSION = "1"

KIND = "seat-lifecycle-record"
RECORD_TYPE = "seat_lifecycle"

STATE_ALIVE = "alive"
STATE_IDLE = "idle"
STATE_SPENT = "spent"
STATE_DEAD = "dead"
LIFECYCLE_STATES = frozenset({STATE_ALIVE, STATE_IDLE, STATE_SPENT, STATE_DEAD})

REGISTRATION_STATE_GOVERNED = "alive"
REGISTRATION_STATE_UNGOVERNED = "ungoverned_registration_failed"

DEFAULT_POLICY_ID = "default-governed-seat-v1"
DEFAULT_TTL_SECONDS = 28800
DEFAULT_IDLE_TIMEOUT_SECONDS = 7200
DEFAULT_SPENT_GRACE_SECONDS = 600
DEFAULT_DEAD_GRACE_SECONDS = 300
DEFAULT_REQUIRE_OPERATOR_FOR = (
    "attached_controller",
    "live_process",
    "dirty_worktree",
    "unpushed_commits",
    "missing_transcript_archive",
    "unresolved_outcome",
    "cross_host_unreachable",
)

DISPATCH_ARCHIVE_REL = ".ce/state/archive/dispatches"

# Operator-ratified rollout posture for ce-ops#95 Phase 1. This release writes,
# warns, and escalates when a post-spawn lifecycle registration fails; the next
# release flips this constant to make the same failure block the launch.
SEAT_LIFECYCLE_FAIL_CLOSED = False

SEATS_SUBDIR = "seats"
SEAT_EVENTS_SUBDIR = "seat-events"
ESCALATIONS_SUBDIR = "escalations"
EVENT_REGISTERED = "registered"
EVENT_REGISTRATION_FAILED = "registration_failed"

CHECK_CODE = "SEAT-LIFECYCLE-001"


class SeatLifecycleError(Exception):
    """Lifecycle registry write/read failure."""

    code = "SEAT-LIFECYCLE-ERROR"


class SeatLifecycleSchemaError(SeatLifecycleError):
    code = "SEAT-LIFECYCLE-SCHEMA"


class TmuxProbe(Protocol):
    def __call__(self, terminal: Mapping[str, Any]) -> Mapping[str, Any]: ...


class ProcProbe(Protocol):
    def __call__(self, pid: int) -> Mapping[str, Any]: ...


class GitProbe(Protocol):
    def __call__(self, worktree_path: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class ProbeSet:
    """Injectable liveness/resource seams for later sampling phases."""

    tmux: TmuxProbe | None = None
    proc: ProcProbe | None = None
    git: GitProbe | None = None


@dataclass(frozen=True)
class WorkClaimBinding:
    work_key: str
    claim_id: str
    claim_comment_url: str | None = None
    holder: str | None = None
    host: str | None = None
    stale_after_seconds: int | None = None

    def to_record(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "work_key": self.work_key,
            "claim_id": self.claim_id,
        }
        _maybe_set(out, "claim_comment_url", self.claim_comment_url)
        _maybe_set(out, "holder", self.holder)
        _maybe_set(out, "host", self.host)
        _maybe_set(out, "stale_after_seconds", self.stale_after_seconds)
        return out


@dataclass(frozen=True)
class RegistrationResult:
    record_path: Path
    event_path: Path
    state: str = REGISTRATION_STATE_GOVERNED


def _utc_now_str(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value).lower()).strip("-")
    return slug or fallback


def default_host_id() -> str:
    return _slug(socket.gethostname() or "unknown-host", fallback="unknown-host")


def default_controller_id() -> str:
    return _slug(os.environ.get("CE_CONTROLLER_ID") or default_host_id(), fallback="controller")


def command_ref(command: list[str] | tuple[str, ...] | None) -> str | None:
    if not command:
        return None
    joined = "\x00".join(str(part) for part in command)
    return f"value-free-digest:{hashlib.sha256(joined.encode('utf-8')).hexdigest()}"


def seat_record_path(ledger_root: Path | str, host_id: str, seat_id: str) -> Path:
    return Path(ledger_root) / SEATS_SUBDIR / _slug(host_id, fallback="host") / f"{seat_id}.yaml"


def seat_event_path(ledger_root: Path | str, host_id: str, seat_id: str) -> Path:
    return Path(ledger_root) / SEAT_EVENTS_SUBDIR / _slug(host_id, fallback="host") / f"{seat_id}.ndjson"


def dispatch_archive_root(repo_root: Path | str) -> Path:
    return Path(repo_root) / DISPATCH_ARCHIVE_REL


def load_record(path: Path | str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise SeatLifecycleError(f"seat lifecycle record is unreadable: {path}") from exc
    if not isinstance(data, dict):
        raise SeatLifecycleError(f"seat lifecycle record is not a YAML mapping: {path}")
    return data


def iter_records(ledger_root: Path | str) -> list[tuple[Path, dict[str, Any]]]:
    base = Path(ledger_root) / SEATS_SUBDIR
    if not base.is_dir():
        return []
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(base.glob("*/*.yaml")):
        try:
            out.append((path, load_record(path)))
        except SeatLifecycleError:
            continue
    return out


def reconcile_from_sentinel_events(
    record_path: Path | str,
    *,
    now: datetime | None = None,
) -> bool:
    """Update a lifecycle record from terminal sentinel exit evidence.

    Returns True only when the record was changed. Exit 0 means the seat is
    terminally spent; any nonzero exit, including exec-fail 127, means dead.
    """
    path = Path(record_path)
    record = load_record(path)
    events_ref = record.get("dispatch", {}).get("events_ref")
    if not isinstance(events_ref, str) or not events_ref:
        return False

    exit_code: int | None = None
    for event in seat_sentinel.iter_events_file(events_ref):
        if event.get("event") != seat_sentinel.EVENT_EXITED:
            continue
        raw_code = event.get("exit_code")
        if isinstance(raw_code, int):
            exit_code = raw_code
    if exit_code is None:
        return False

    next_state = STATE_SPENT if exit_code == 0 else STATE_DEAD
    reason = "sentinel-exited-zero" if exit_code == 0 else "sentinel-exited-nonzero"
    lifecycle = record.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise SeatLifecycleError(f"seat lifecycle record has no lifecycle mapping: {path}")
    if (
        lifecycle.get("state") == next_state
        and lifecycle.get("terminal_exit_code") == exit_code
        and lifecycle.get("state_reason") == reason
    ):
        return False

    timestamp = _utc_now_str(now)
    lifecycle["state"] = next_state
    lifecycle["state_reason"] = reason
    lifecycle["state_since"] = timestamp
    lifecycle["last_activity_at"] = timestamp
    lifecycle["terminal_exit_code"] = exit_code

    errors = validate_record(record, path)
    if errors:
        raise SeatLifecycleSchemaError(
            "reconciled seat lifecycle record is invalid: " + "; ".join(errors)
        )
    _atomic_write(path, yaml.safe_dump(record, sort_keys=True))
    return True


def validate_record(record: dict[str, Any], path: Path | str) -> list[str]:
    return [
        e.format()
        for e in validate_with_schema(record, SCHEMA, path, code=CHECK_CODE, contract=SCHEMA)
    ]


def register_spawn(
    *,
    ledger_root: Path | str,
    repo_root: Path | str,
    seat_id: str,
    owner_controller_id: str | None,
    host_id: str | None,
    launch_surface: str,
    terminal: Mapping[str, Any],
    harness_kind: str,
    spawned_at: str | None = None,
    purpose: str | None = None,
    cwd: Path | str | None = None,
    launch_command: list[str] | tuple[str, ...] | None = None,
    work_claim: WorkClaimBinding | Mapping[str, Any] | None = None,
    ticket: str | None = None,
    pco_claim_ref: str | None = None,
    pco_lease_ref: str | None = None,
    worktree_path: str | None = None,
    branch: str | None = None,
    envelope_ref: str | None = None,
    dispatch_ref: str | None = None,
    events_ref: str | None = None,
    sentinel_wrapper_ref: str | None = None,
    pane_registry_ref: str | None = None,
    run_id: str | None = None,
    scope_id: str | None = None,
    mutation_class: str | None = None,
    harness_boundary: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    harness_session_id: str | None = None,
    transcript_ref: str | None = None,
    runtime_policy_ref: str | None = None,
    resource_bound: dict[str, Any] | str | None = None,
    resource_confirm: dict[str, Any] | None = None,
    now: datetime | None = None,
    probes: ProbeSet | None = None,
) -> RegistrationResult:
    """Write one lifecycle object and one append-only registration audit event."""

    timestamp = spawned_at or _utc_now_str(now)
    host = _slug(host_id or default_host_id(), fallback="host")
    controller = owner_controller_id or default_controller_id()
    repo = Path(repo_root)
    record_path = seat_record_path(ledger_root, host, seat_id)
    event_path = seat_event_path(ledger_root, host, seat_id)
    terminal_record = _terminal_record(terminal)
    sample = _initial_sample(terminal_record, worktree_path=worktree_path, probes=probes)

    record: dict[str, Any] = {
        "kind": KIND,
        "record_type": RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "seat": {
            "seat_id": seat_id,
            "host_id": host,
            "owner_controller_id": controller,
            "launch_surface": launch_surface,
            "registered_at": timestamp,
            "spawned_at": timestamp,
            "repo_root": str(repo),
        },
        "work": {},
        "dispatch": {},
        "terminal": terminal_record,
        "harness": {"kind": harness_kind},
        "resources": {
            "resource_bound": resource_bound,
            "resource_confirm": resource_confirm,
            "last_sample": sample,
        },
        "lifecycle": {
            "state": STATE_ALIVE,
            "state_reason": "registered-at-spawn",
            "state_since": timestamp,
            "last_heartbeat_at": timestamp,
            "last_activity_at": timestamp,
            "idle_since": None,
            "terminal_exit_code": None,
            "outcome": None,
            "outcome_source": "unresolved",
        },
        "policy": default_policy(),
        "retirement": {
            "status": "not_requested",
            "eligible_after": None,
            "escalation_ref": None,
            "ratification_ref": None,
            "retirement_ledger_ref": None,
            "retired_at": None,
        },
    }

    _maybe_set(record["seat"], "launch_command_ref", command_ref(launch_command))
    _maybe_set(record["seat"], "purpose", purpose)
    _maybe_set(record["seat"], "cwd", str(cwd) if cwd is not None else None)
    _maybe_set(record["work"], "ticket", ticket)
    claim_record = _claim_record(work_claim)
    if claim_record is not None:
        record["work"]["work_claim"] = claim_record
    _maybe_set(record["work"], "pco_claim_ref", pco_claim_ref)
    _maybe_set(record["work"], "pco_lease_ref", pco_lease_ref)
    _maybe_set(record["work"], "worktree_path", worktree_path)
    _maybe_set(record["work"], "branch", branch)
    _maybe_set(record["work"], "envelope_ref", envelope_ref)
    _maybe_set(record["dispatch"], "dispatch_ref", dispatch_ref)
    _maybe_set(record["dispatch"], "events_ref", events_ref)
    _maybe_set(record["dispatch"], "sentinel_wrapper_ref", sentinel_wrapper_ref)
    _maybe_set(record["dispatch"], "pane_registry_ref", pane_registry_ref)
    _maybe_set(record["dispatch"], "run_id", run_id)
    _maybe_set(record["dispatch"], "scope_id", scope_id)
    _maybe_set(record["dispatch"], "mutation_class", mutation_class)
    _maybe_set(record["dispatch"], "conserve", False)
    _maybe_set(record["harness"], "harness_boundary", harness_boundary)
    _maybe_set(record["harness"], "model", model)
    _maybe_set(record["harness"], "effort", effort)
    _maybe_set(record["harness"], "harness_session_id", harness_session_id)
    _maybe_set(record["harness"], "transcript_ref", transcript_ref)
    _maybe_set(record["resources"], "runtime_policy_ref", runtime_policy_ref)

    errors = validate_record(record, record_path)
    if errors:
        raise SeatLifecycleSchemaError(
            "generated seat lifecycle record is invalid: " + "; ".join(errors)
        )
    _atomic_write(record_path, yaml.safe_dump(record, sort_keys=True))
    append_event(
        event_path,
        {
            "event": EVENT_REGISTERED,
            "seat_id": seat_id,
            "host_id": host,
            "state": STATE_ALIVE,
            "ts": timestamp,
            "record_ref": str(record_path),
        },
    )
    return RegistrationResult(record_path=record_path, event_path=event_path)


def default_policy() -> dict[str, Any]:
    return {
        "policy_id": DEFAULT_POLICY_ID,
        "ttl_seconds": DEFAULT_TTL_SECONDS,
        "idle_timeout_seconds": DEFAULT_IDLE_TIMEOUT_SECONDS,
        "spent_grace_seconds": DEFAULT_SPENT_GRACE_SECONDS,
        "dead_grace_seconds": DEFAULT_DEAD_GRACE_SECONDS,
        "auto_reap_spent": True,
        "auto_reap_dead_clean": True,
        "auto_reap_idle": False,
        "require_operator_for": list(DEFAULT_REQUIRE_OPERATOR_FOR),
    }


def write_registration_failure_escalation(
    *,
    state_root: Path | str,
    host_id: str | None,
    seat_id: str,
    source_ref: str | None,
    error: BaseException | str,
    now: datetime | None = None,
) -> Path:
    host = _slug(host_id or default_host_id(), fallback="host")
    created = _utc_now_str(now)
    digest = hashlib.sha256(
        f"{host}:{seat_id}:seat-lifecycle-registration-failed".encode("utf-8")
    ).hexdigest()
    record = {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": digest,
        "title": "Seat lifecycle registration failed after spawn",
        "decision_needed": (
            "Inspect the ungoverned spawned seat, then ratify retirement or manual "
            "registry repair before relying on it as governed."
        ),
        "recommendation": (
            "Conserve the pane for inspection; do not auto-kill. Flip "
            "SEAT_LIFECYCLE_FAIL_CLOSED only after the compatibility release."
        ),
        "created_at": created,
        "source_ref": source_ref or f"seat:{seat_id}",
    }
    path = Path(state_root) / ESCALATIONS_SUBDIR / f"{digest}.yaml"
    _atomic_write(path, yaml.safe_dump(record, sort_keys=True))
    return path


def warn_registration_failure(*, surface: str, escalation_ref: Path, error: BaseException | str) -> None:
    print(
        "WARNING: seat lifecycle registration failed after pane spawn; "
        f"{surface} is proceeding ungoverned for this compatibility release; "
        f"AWAITING-OPERATOR escalation={escalation_ref}: {error}",
        file=sys.stderr,
    )


def append_event(path: Path | str, event: Mapping[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(event), sort_keys=True, separators=(",", ":")) + "\n")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


def _maybe_set(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def _claim_record(work_claim: WorkClaimBinding | Mapping[str, Any] | None) -> dict[str, Any] | None:
    if work_claim is None:
        return None
    if isinstance(work_claim, WorkClaimBinding):
        return work_claim.to_record()
    work_key = work_claim.get("work_key")
    claim_id = work_claim.get("claim_id")
    if not work_key or not claim_id:
        return None
    out = {
        "work_key": str(work_key),
        "claim_id": str(claim_id),
    }
    for key in ("claim_comment_url", "holder", "host", "stale_after_seconds"):
        _maybe_set(out, key, work_claim.get(key))
    return out


def _terminal_record(terminal: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"kind": str(terminal.get("kind") or "unknown")}
    for key in (
        "session_id",
        "window_id",
        "pane_id",
        "pane_tty",
        "pane_pid",
        "surface_ref",
        "pid",
    ):
        _maybe_set(out, key, terminal.get(key))
    out["attached_controller"] = {"attached": False, "evidence": "not-sampled"}
    return out


def _initial_sample(
    terminal: Mapping[str, Any],
    *,
    worktree_path: str | None,
    probes: ProbeSet | None,
) -> dict[str, Any] | None:
    if probes is None:
        return None
    sample: dict[str, Any] = {}
    if probes.tmux is not None:
        sample["tmux"] = dict(probes.tmux(terminal))
    pid = terminal.get("pane_pid")
    if probes.proc is not None and pid is not None:
        try:
            sample["proc"] = dict(probes.proc(int(pid)))
        except (TypeError, ValueError):
            sample["proc"] = {"error": "invalid-pane-pid"}
    if probes.git is not None and worktree_path:
        sample["git"] = dict(probes.git(worktree_path))
    return sample or None
