"""File-only runtime for the pure ratifier queue.

This adapter deliberately has no forge client, validator runner, credential
lookup, or approval surface.  Its caller supplies a versioned candidate
snapshot and injected attestation facts; the adapter folds those facts through
the pure queue reducer and atomically persists only the resulting proposal
state for a controller to inspect.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ratifier_queue import (
    RatifierCandidate,
    RatifierQueueState,
    compute_queue_state,
    drive_attestation,
    render_queue,
)
from .ready_attestation_nudge import ReadyAttestationFacts


DOCUMENT_VERSION = 1
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_CANDIDATE_FIELDS = frozenset({
    "pr_number", "head_sha", "branch", "enqueued_at", "attestation_state",
    "last_checked_at", "checked_count", "facts",
})
_STATE_FIELDS = frozenset({"version", "updated_at", "candidates"})
_FACT_FIELDS = frozenset({
    "ready_sha", "validation_sha", "validator_live", "exit_code",
    "structural_failures", "environment_failures",
})


class RatifierQueueRuntimeError(RuntimeError):
    """Raised when durable queue input or state is unsafe to use."""


def dedup_identity(candidate: RatifierCandidate) -> str:
    """Return the immutable PR-head identity used for restart-safe folding."""
    return f"ratifier-queue:{candidate.pr_number}:{candidate.head_sha}"


def _require_object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RatifierQueueRuntimeError(f"{label} must be an object")
    return value


def _iso(value: object, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise RatifierQueueRuntimeError(f"{label} must be an RFC3339 string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RatifierQueueRuntimeError(f"{label} must be an RFC3339 string") from exc
    return value


def _candidate_from_mapping(value: object, *, require_facts: bool) -> tuple[RatifierCandidate, ReadyAttestationFacts | None]:
    item = _require_object(value, "candidate")
    unknown = set(item) - _CANDIDATE_FIELDS
    required = _CANDIDATE_FIELDS - ({"facts"} if not require_facts else set())
    missing = required - set(item)
    if unknown or missing:
        raise RatifierQueueRuntimeError("candidate has unknown or missing fields")
    pr_number = item.get("pr_number")
    checked_count = item.get("checked_count")
    head_sha = item.get("head_sha")
    if (
        isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number <= 0
        or isinstance(checked_count, bool) or not isinstance(checked_count, int) or checked_count < 0
        or not isinstance(head_sha, str) or not _SHA_RE.fullmatch(head_sha.lower())
        or not isinstance(item.get("branch"), str) or not item["branch"].strip()
        or not isinstance(item.get("attestation_state"), str)
    ):
        raise RatifierQueueRuntimeError("candidate contains invalid identity or state")
    candidate = RatifierCandidate(
        pr_number=pr_number,
        head_sha=head_sha.lower(),
        branch=item["branch"],
        enqueued_at=str(_iso(item.get("enqueued_at"), "candidate.enqueued_at")),
        attestation_state=item["attestation_state"],
        last_checked_at=_iso(item.get("last_checked_at"), "candidate.last_checked_at", nullable=True),
        checked_count=checked_count,
    )
    if "facts" not in item:
        return candidate, None
    facts = _facts_from_mapping(item["facts"])
    return candidate, facts


def _facts_from_mapping(value: object) -> ReadyAttestationFacts:
    facts = _require_object(value, "candidate.facts")
    if set(facts) != _FACT_FIELDS:
        raise RatifierQueueRuntimeError("candidate.facts must use the complete versioned evidence shape")
    ready_sha = facts.get("ready_sha")
    validation_sha = facts.get("validation_sha")
    validator_live = facts.get("validator_live")
    exit_code = facts.get("exit_code")
    structural = facts.get("structural_failures")
    environment = facts.get("environment_failures")
    if not isinstance(ready_sha, str) or not isinstance(validator_live, bool):
        raise RatifierQueueRuntimeError("candidate.facts contains malformed evidence")
    if validation_sha is not None and not isinstance(validation_sha, str):
        raise RatifierQueueRuntimeError("candidate.facts contains malformed evidence")
    for field in (exit_code, structural, environment):
        if field is not None and (isinstance(field, bool) or not isinstance(field, int)):
            raise RatifierQueueRuntimeError("candidate.facts contains malformed evidence")
    return ReadyAttestationFacts(
        ready_sha=ready_sha,
        validation_sha=validation_sha,
        validator_live=validator_live,
        exit_code=exit_code,
        structural_failures=structural,
        environment_failures=environment,
    )


def load_candidate_document(path: Path | str) -> list[tuple[RatifierCandidate, ReadyAttestationFacts]]:
    """Read the strict caller-owned versioned candidate snapshot."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RatifierQueueRuntimeError("candidate document cannot be read as JSON") from exc
    document = _require_object(raw, "candidate document")
    if set(document) != {"version", "candidates"} or document.get("version") != DOCUMENT_VERSION:
        raise RatifierQueueRuntimeError("candidate document has an unsupported version or shape")
    candidates = document.get("candidates")
    if not isinstance(candidates, list):
        raise RatifierQueueRuntimeError("candidate document candidates must be a list")
    parsed = [_candidate_from_mapping(item, require_facts=True) for item in candidates]
    identities = [dedup_identity(candidate) for candidate, _ in parsed]
    if len(identities) != len(set(identities)):
        raise RatifierQueueRuntimeError("candidate document contains duplicate immutable identities")
    return [(candidate, facts) for candidate, facts in parsed if facts is not None]


def _assert_owner_only(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise RatifierQueueRuntimeError("durable state cannot be inspected") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise RatifierQueueRuntimeError("durable state is not an owner-only regular file")


def load_state(path: Path | str) -> dict[str, RatifierCandidate]:
    """Load prior state; a missing state file is the only empty-state case."""
    state_path = Path(path)
    if not state_path.exists():
        return {}
    _assert_owner_only(state_path)
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RatifierQueueRuntimeError("durable state cannot be read as JSON") from exc
    document = _require_object(raw, "durable state")
    if set(document) != _STATE_FIELDS or document.get("version") != DOCUMENT_VERSION:
        raise RatifierQueueRuntimeError("durable state has an unsupported version or shape")
    _iso(document.get("updated_at"), "durable state updated_at")
    values = document.get("candidates")
    if not isinstance(values, list):
        raise RatifierQueueRuntimeError("durable state candidates must be a list")
    parsed = [_candidate_from_mapping(item, require_facts=False)[0] for item in values]
    state = {dedup_identity(candidate): candidate for candidate in parsed}
    if len(state) != len(parsed):
        raise RatifierQueueRuntimeError("durable state contains duplicate immutable identities")
    return state


def _serialized_candidate(candidate: RatifierCandidate) -> dict[str, object]:
    return {
        "pr_number": candidate.pr_number,
        "head_sha": candidate.head_sha,
        "branch": candidate.branch,
        "enqueued_at": candidate.enqueued_at,
        "attestation_state": candidate.attestation_state,
        "last_checked_at": candidate.last_checked_at,
        "checked_count": candidate.checked_count,
    }


def _atomic_write_state(path: Path, candidates: tuple[RatifierCandidate, ...], now: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {
        "version": DOCUMENT_VERSION,
        "updated_at": now,
        "candidates": [_serialized_candidate(candidate) for candidate in candidates],
    }
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError as exc:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise RatifierQueueRuntimeError("durable state cannot be atomically persisted") from exc


def _clock_now(clock: Callable[[], datetime]) -> str:
    now = clock()
    if now.tzinfo is None:
        raise RatifierQueueRuntimeError("injected clock must be timezone-aware")
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def run_once(
    candidate_path: Path | str,
    state_path: Path | str,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> RatifierQueueState:
    """Fold one supplied snapshot and atomically replace the durable queue state."""
    state_file = Path(state_path)
    state_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = state_file.with_name(f".{state_file.name}.lock")
    try:
        lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except OSError as exc:
        raise RatifierQueueRuntimeError("ratifier queue lock cannot be opened safely") from exc
    try:
        lock_mode = os.fstat(lock_fd).st_mode
        if not stat.S_ISREG(lock_mode) or lock_mode & 0o077:
            raise RatifierQueueRuntimeError("ratifier queue lock is not an owner-only regular file")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RatifierQueueRuntimeError("ratifier queue concurrent writer refused") from exc
        persisted = load_state(state_file)
        observed = load_candidate_document(candidate_path)
        checked_at = _clock_now(clock)
        updated: list[RatifierCandidate] = []
        for candidate, facts in observed:
            prior = persisted.get(dedup_identity(candidate))
            if prior is not None:
                candidate = replace(
                    candidate,
                    attestation_state=prior.attestation_state,
                    last_checked_at=prior.last_checked_at,
                    checked_count=prior.checked_count,
                )
            updated.append(replace(drive_attestation(candidate, facts), last_checked_at=checked_at))
        queue_state = compute_queue_state(updated)
        _atomic_write_state(state_file, queue_state.candidates, checked_at)
        return queue_state
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def summary(queue_state: RatifierQueueState) -> dict[str, object]:
    """Return a compact, non-actuating controller-consumable projection."""
    return {
        "candidate_count": len(queue_state.entries),
        "attested_count": sum(entry.status == "ATTESTED" for entry in queue_state.entries),
        "entries": [
            {
                "pr_number": entry.candidate.pr_number,
                "head_sha": entry.candidate.head_sha,
                "dedup_identity": dedup_identity(entry.candidate),
                "status": entry.status,
                "reason": entry.reason,
                "checked_count": entry.candidate.checked_count,
                "last_checked_at": entry.candidate.last_checked_at,
            }
            for entry in queue_state.entries
        ],
        "human": render_queue(queue_state),
    }
