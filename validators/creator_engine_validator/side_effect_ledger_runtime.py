"""Side-Effect Ledger runtime (`ce ledger record` / `ce ledger verify`).

Implements the runtime named in the v1.0 traceability matrix:

* ``RV1-040`` — append-only Side-Effect Ledger records with a per-lane hash
  chain, classified by mutation taxonomy, redaction enforced before write.
* ``RV1-041`` — ``record`` appends one classified entry bound to a live
  Active-Work Ledger claim; ``verify`` validates the chain and replays it
  deterministically.
* ``RV1-042`` — records never store secret values; secret-shaped fields are
  refused before any write.

This module reuses the **already-landed** Side-Effect Ledger substrate
(``checks/side_effect_ledger.py`` + ``schemas/side-effect-ledger.schema.yaml``,
PCO-055..PCO-063) and the Active-Work Ledger claim validator. It performs NO
GitHub/git/tracker/CI/deploy/provider/MCP/plugin/container/network mutation, no
pane spawning, and no automatic side-effect observation. Runtime records are
authored as deterministic stdlib ``json`` bytes (``sort_keys=True``,
newline-terminated) per the Option B format split; the YAML schema/examples are
unchanged in serialization.

Prose contract: ``docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md``.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from .checks.active_work_ledger_schema import validate_active_work_ledger_record
from .checks.side_effect_ledger import (
    CODE_REDACTION_SAFE,
    KIND_VALUE,
    validate_side_effect_ledger_record,
)
from .loader import LoaderError, load_yaml

# Genesis sentinel: the first record in a (controller_id, lane_id) chain has no
# predecessor, so its ``previous_record_sha256`` is the all-zero SHA256.
GENESIS_SHA = "0" * 64

HEAD_FILENAME = "_head.json"
HEAD_KIND = "side-effect-ledger-head"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LedgerRuntimeError(Exception):
    """Base class for Side-Effect Ledger runtime errors. Carries a ``code``."""

    code = "G4-LEDGER-ERROR"


class LedgerRecordError(LedgerRuntimeError):
    code = "G4-RECORD-ERROR"


class SecretMaterialRefused(LedgerRecordError):
    code = "G4-SECRET-REFUSED"


class DetailsNotObject(LedgerRecordError):
    code = "G4-DETAILS-NOT-OBJECT"


class ClaimBindingError(LedgerRecordError):
    code = "G4-CLAIM-BINDING"


class RecordCollision(LedgerRecordError):
    code = "G4-RECORD-COLLISION"


class InvalidRecord(LedgerRecordError):
    code = "G4-INVALID-RECORD"


class LedgerVerifyError(LedgerRuntimeError):
    code = "G4-VERIFY-ERROR"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecordResult:
    record_path: Path
    head_path: Path
    record: dict[str, Any]
    sequence: int
    record_sha256: str
    previous_record_sha256: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    summary: dict[str, Any]
    errors: tuple[str, ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


def _canonical_bytes(record: dict[str, Any]) -> str:
    """Deterministic record serialization: sorted keys, newline-terminated."""
    return json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now_str(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_day(occurred_at: str, fallback: datetime) -> str:
    """Best-effort UTC day for grouping; falls back to the record write day."""
    if isinstance(occurred_at, str) and not occurred_at.startswith(("commit:", "source-controlled:")):
        text = occurred_at[:-1] + "+00:00" if occurred_at.endswith("Z") else occurred_at
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = None
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC).date().isoformat()
    return fallback.astimezone(UTC).date().isoformat() if fallback.tzinfo else fallback.date().isoformat()


def _lane_root(side_effect_ledger_root: Path, controller_id: str, lane_id: str) -> Path:
    return side_effect_ledger_root / controller_id / lane_id


def _head_path(side_effect_ledger_root: Path, controller_id: str, lane_id: str) -> Path:
    return _lane_root(side_effect_ledger_root, controller_id, lane_id) / HEAD_FILENAME


def _read_head(head_path: Path) -> dict[str, Any] | None:
    if not head_path.is_file():
        return None
    try:
        data = json.loads(head_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerRecordError(f"head manifest at {head_path} is unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerRecordError(f"head manifest at {head_path} is not a JSON object")
    return data


@contextmanager
def _work_unit_lane_lock(root: Path, controller_id: str, lane_id: str):
    """Serialize CE603 read-project-append reservations for one ledger lane."""
    import fcntl

    lock_path = _lane_root(root, controller_id, lane_id) / ".work-unit-reservation.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# ce ledger record
# ---------------------------------------------------------------------------


def record(
    *,
    controller_id: str,
    lane_id: str,
    claim_ref: str,
    effect_id: str,
    effect_kind: str,
    effect_status: str,
    summary: str,
    occurred_at: str,
    repo_root: Path | str,
    side_effect_ledger_root: Path | str,
    active_work_ledger_root: Path | str,
    actor_role: str | None = None,
    pane_ref: str | None = None,
    subject_ref: str | None = None,
    subject_git_sha: str | None = None,
    evidence_refs: Sequence[str] | None = None,
    redactions: Sequence[str] | None = None,
    details: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> RecordResult:
    """Append one redaction-safe Side-Effect Ledger runtime record.

    Every refusal (secret material, bad details, unbound/invalid claim,
    invalid record, file collision) raises **before any record/head write**, so
    a refused call leaves the ledger byte-identical.
    """
    side_effect_ledger_root = Path(side_effect_ledger_root)
    active_work_ledger_root = Path(active_work_ledger_root)

    # 1. details must be a JSON object (reject arrays/scalars) — before any work.
    if details is not None and not isinstance(details, dict):
        raise DetailsNotObject("details must be a JSON object (not an array or scalar)")

    # 2. Bind to a live, matching Active-Work Ledger claim — before any write.
    _require_live_claim(active_work_ledger_root, claim_ref, controller_id, lane_id)

    # 3. Read the current chain head for this (controller_id, lane_id).
    head_path = _head_path(side_effect_ledger_root, controller_id, lane_id)
    head = _read_head(head_path)
    if head is None:
        lane_root = _lane_root(side_effect_ledger_root, controller_id, lane_id)
        if any(lane_root.rglob("*.json")):
            raise LedgerRecordError(
                f"headless populated lane at {lane_root}; refusing ambiguous append"
            )
        sequence = 1
        previous_sha = GENESIS_SHA
    else:
        sequence = int(head.get("sequence", 0)) + 1
        previous_sha = str(head.get("head_sha256", GENESIS_SHA))

    # 4. Build the record (deterministic field set).
    record_timestamp = _utc_now_str(now)
    payload: dict[str, Any] = {
        "kind": KIND_VALUE,
        "record_type": "side_effect",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "claim_ref": claim_ref,
        "effect_id": effect_id,
        "effect_kind": effect_kind,
        "effect_status": effect_status,
        "occurred_at": occurred_at,
        "record_timestamp": record_timestamp,
        "summary": summary,
        "sequence": sequence,
        "previous_record_sha256": previous_sha,
    }
    if actor_role is not None:
        payload["actor_role"] = actor_role
    if pane_ref is not None:
        payload["pane_ref"] = pane_ref
    if subject_ref is not None:
        payload["subject_ref"] = subject_ref
    if subject_git_sha is not None:
        payload["subject_git_sha"] = subject_git_sha
    if evidence_refs:
        payload["evidence_refs"] = list(evidence_refs)
    if redactions:
        payload["redactions"] = list(redactions)
    if details is not None:
        payload["details"] = details

    # 5. Validate via the landed substrate; refuse secret material / invalid shape.
    errors = validate_side_effect_ledger_record(payload, head_path)
    if any(error.code == CODE_REDACTION_SAFE for error in errors):
        raise SecretMaterialRefused(
            "record contains secret-shaped material; refusing before write: "
            + "; ".join(e.format() for e in errors if e.code == CODE_REDACTION_SAFE)
        )
    if errors:
        raise InvalidRecord(
            "record fails Side-Effect Ledger validation: " + "; ".join(e.format() for e in errors)
        )

    # 6. Resolve the deterministic target path; never overwrite.
    day = _utc_day(occurred_at, now or datetime.now(UTC))
    record_path = _lane_root(side_effect_ledger_root, controller_id, lane_id) / day / f"{sequence:06d}-{effect_id}.json"
    if record_path.exists():
        raise RecordCollision(f"record already exists, refusing to overwrite: {record_path}")

    # --- Side effects begin here (record file, then head manifest) ---
    text = _canonical_bytes(payload)
    record_sha256 = _sha256_text(text)
    _atomic_write(record_path, text)

    head_payload = {
        "kind": HEAD_KIND,
        "controller_id": controller_id,
        "lane_id": lane_id,
        "sequence": sequence,
        "record_count": sequence,
        "head_sha256": record_sha256,
        "last_record_ref": record_path.relative_to(side_effect_ledger_root).as_posix(),
    }
    _atomic_write(head_path, json.dumps(head_payload, sort_keys=True, indent=2) + "\n")

    return RecordResult(
        record_path=record_path,
        head_path=head_path,
        record=payload,
        sequence=sequence,
        record_sha256=record_sha256,
        previous_record_sha256=previous_sha,
    )


def record_work_unit_reservation(*, receipt: dict[str, Any], **record_kwargs: Any) -> RecordResult:
    """Atomically append one CE603 reservation through the sole record writer."""
    if not isinstance(receipt, dict):
        raise DetailsNotObject("work-unit receipt must be a JSON object")
    root = Path(record_kwargs["side_effect_ledger_root"])
    controller_id = str(record_kwargs["controller_id"])
    lane_id = str(record_kwargs["lane_id"])
    with _work_unit_lane_lock(root, controller_id, lane_id):
        return _record_work_unit_reservation(receipt=receipt, record_kwargs=record_kwargs)


def _record_work_unit_reservation(*, receipt: dict[str, Any], record_kwargs: dict[str, Any]) -> RecordResult:
    """Build and append the ledger record; caller owns the lane lock."""
    details = dict(record_kwargs.pop("details", {}) or {})
    # Ledger details allow scalar values and reject token-shaped strings. Store
    # canonical receipt bytes as bounded hex fragments; recovery reassembles it.
    encoded = _canonical_bytes(receipt).rstrip("\n").encode("utf-8").hex()
    for index in range(0, len(encoded), 30):
        details[f"work_unit_receipt_part_{index // 30:03d}"] = encoded[index:index + 30]
    receipt_id = str(receipt.get("receipt_id") or "unknown")
    record_kwargs.update(
        effect_id=f"work-unit-reservation-{receipt_id[:32]}",
        effect_kind="tracked_file_change",
        effect_status="succeeded",
        summary="Recorded CE603 work-unit reservation.",
        details=details,
    )
    return record(**record_kwargs)


def _durable_work_unit_receipts(root: Path, controller_id: str, lane_id: str) -> tuple[dict[str, Any], ...]:
    """Read CE603 receipts already committed to this lane's append-only ledger."""
    lane_root = _lane_root(root, controller_id, lane_id)
    receipts: list[dict[str, Any]] = []
    for path in sorted(lane_root.rglob("*.json")) if lane_root.exists() else ():
        if path.name == HEAD_FILENAME:
            continue
        try:
            record_data = json.loads(path.read_text(encoding="utf-8"))
            details = record_data.get("details", {})
            fragments = [details[key] for key in sorted(details) if key.startswith("work_unit_receipt_part_")]
            serialized = bytes.fromhex("".join(fragments)).decode("utf-8") if fragments and all(isinstance(value, str) for value in fragments) else ""
            receipt = json.loads(serialized) if serialized else None
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(receipt, dict):
            receipts.append(receipt)
    return tuple(receipts)


def reserve_work_unit_reservation(
    *, cap: int, run_id: str, attempt_id: str, reservation_id: str, requested: int,
    policy_sha256: str, recorded_at: str, **record_kwargs: Any,
):
    """Reserve and durably append under one lane lock, never exposing a race window."""
    from .runner import work_unit_cap

    root = Path(record_kwargs["side_effect_ledger_root"])
    controller_id = str(record_kwargs["controller_id"])
    lane_id = str(record_kwargs["lane_id"])
    with _work_unit_lane_lock(root, controller_id, lane_id):
        decision = work_unit_cap.reserve(
            _durable_work_unit_receipts(root, controller_id, lane_id), cap=cap, run_id=run_id,
            attempt_id=attempt_id, reservation_id=reservation_id, requested=requested,
            policy_sha256=policy_sha256, recorded_at=recorded_at,
        )
        if not decision.allowed or not decision.persist:
            return decision
        _record_work_unit_reservation(receipt=decision.receipt, record_kwargs=record_kwargs)
        return decision


def _require_live_claim(
    active_work_ledger_root: Path, claim_ref: str, controller_id: str, lane_id: str
) -> None:
    claim_path = active_work_ledger_root / claim_ref
    if not claim_path.is_file():
        raise ClaimBindingError(
            f"no Active-Work Ledger claim at {claim_path}; allocate a lane before recording"
        )
    try:
        claim = load_yaml(claim_path)
    except LoaderError as exc:
        raise ClaimBindingError(f"claim at {claim_path} is unreadable: {exc}") from exc
    if not isinstance(claim, dict):
        raise ClaimBindingError(f"claim at {claim_path} is not a mapping")
    claim_errors = validate_active_work_ledger_record(claim, claim_path)
    if claim_errors:
        raise ClaimBindingError(
            f"claim at {claim_path} fails schema validation: "
            + "; ".join(e.format() for e in claim_errors)
        )
    if claim.get("controller_id") != controller_id or claim.get("lane_id") != lane_id:
        raise ClaimBindingError(
            f"claim at {claim_path} names {claim.get('controller_id')!r}/{claim.get('lane_id')!r}, "
            f"expected {controller_id!r}/{lane_id!r}"
        )
    if claim.get("released_at"):
        raise ClaimBindingError(f"claim at {claim_path} is released; allocate a fresh lane")


# ---------------------------------------------------------------------------
# ce ledger verify
# ---------------------------------------------------------------------------


@dataclass
class _LoadedRecord:
    path: Path
    rel: str
    record: dict[str, Any]
    file_sha256: str


def verify(
    *,
    side_effect_ledger_root: Path | str,
    active_work_ledger_root: Path | str | None = None,
    controller_id: str | None = None,
    lane_id: str | None = None,
) -> VerifyResult:
    """Validate every runtime record + hash chain and emit a replay summary.

    Detects schema violations, broken previous-record links, sequence gaps
    (including deleted intermediate records), head/manifest drift, and (when an
    Active-Work Ledger root is provided) unbound or mismatched claims. The
    replay summary is deterministic for a given on-disk ledger.
    """
    side_effect_ledger_root = Path(side_effect_ledger_root)
    awl_root = Path(active_work_ledger_root) if active_work_ledger_root is not None else None
    errors: list[str] = []

    loaded, load_errors = _load_records(side_effect_ledger_root, controller_id, lane_id)
    errors.extend(load_errors)

    # Group by (controller_id, lane_id).
    groups: dict[tuple[str, str], list[_LoadedRecord]] = {}
    for item in loaded:
        key = (str(item.record.get("controller_id")), str(item.record.get("lane_id")))
        groups.setdefault(key, []).append(item)

    chains: list[dict[str, Any]] = []
    for key in sorted(groups):
        chain_summary, chain_errors = _verify_chain(
            side_effect_ledger_root, key[0], key[1], groups[key], awl_root
        )
        chains.append(chain_summary)
        errors.extend(chain_errors)

    summary = _build_summary(chains, errors)
    return VerifyResult(ok=not errors, summary=summary, errors=tuple(errors))


def _load_records(
    side_effect_ledger_root: Path, controller_id: str | None, lane_id: str | None
) -> tuple[list[_LoadedRecord], list[str]]:
    loaded: list[_LoadedRecord] = []
    errors: list[str] = []
    if not side_effect_ledger_root.exists():
        return loaded, [f"side-effect ledger root does not exist: {side_effect_ledger_root}"]
    for path in sorted(side_effect_ledger_root.rglob("*.json")):
        if path.name == HEAD_FILENAME:
            continue
        rel = path.relative_to(side_effect_ledger_root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{rel}: unreadable runtime record: {exc}")
            continue
        if not isinstance(data, dict) or data.get("kind") != KIND_VALUE:
            errors.append(f"{rel}: not a Side-Effect Ledger record")
            continue
        if controller_id is not None and data.get("controller_id") != controller_id:
            continue
        if lane_id is not None and data.get("lane_id") != lane_id:
            continue
        record_errors = validate_side_effect_ledger_record(data, path)
        for err in record_errors:
            errors.append(f"{rel}: {err.format()}")
        loaded.append(_LoadedRecord(path=path, rel=rel, record=data, file_sha256=_sha256_file(path)))
    return loaded, errors


def _verify_chain(
    side_effect_ledger_root: Path,
    controller_id: str,
    lane_id: str,
    records: list[_LoadedRecord],
    awl_root: Path | None,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    ordered = sorted(records, key=lambda item: int(item.record.get("sequence", 0)))

    # Sequence must be contiguous 1..N.
    for index, item in enumerate(ordered):
        expected = index + 1
        actual = item.record.get("sequence")
        if actual != expected:
            errors.append(
                f"{controller_id}/{lane_id}: sequence break at {item.rel}: "
                f"expected {expected}, found {actual} (tampered or deleted record?)"
            )

    # Hash-chain links: genesis sentinel then previous-file-bytes binding.
    for index, item in enumerate(ordered):
        previous = item.record.get("previous_record_sha256")
        expected = GENESIS_SHA if index == 0 else ordered[index - 1].file_sha256
        if previous != expected:
            errors.append(
                f"{controller_id}/{lane_id}: hash-chain link broken at {item.rel}: "
                f"previous_record_sha256={previous} != {expected}"
            )

    # Claim binding when an Active-Work Ledger root is provided.
    if awl_root is not None:
        for item in ordered:
            errors.extend(_claim_binding_error(awl_root, item))

    # Head / manifest must match the last record.
    head_path = _head_path(side_effect_ledger_root, controller_id, lane_id)
    if ordered:
        last = ordered[-1]
        head = None
        if head_path.is_file():
            try:
                head = json.loads(head_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                errors.append(f"{controller_id}/{lane_id}: head manifest unreadable: {exc}")
        if not isinstance(head, dict):
            errors.append(f"{controller_id}/{lane_id}: missing or invalid head manifest at {head_path}")
        else:
            if head.get("head_sha256") != last.file_sha256:
                errors.append(
                    f"{controller_id}/{lane_id}: head_sha256 {head.get('head_sha256')} "
                    f"does not match last record {last.rel} ({last.file_sha256})"
                )
            if head.get("sequence") != last.record.get("sequence"):
                errors.append(
                    f"{controller_id}/{lane_id}: head sequence {head.get('sequence')} "
                    f"does not match last record sequence {last.record.get('sequence')}"
                )

    return _chain_summary(controller_id, lane_id, ordered), errors


def _claim_binding_error(awl_root: Path, item: _LoadedRecord) -> list[str]:
    claim_ref = item.record.get("claim_ref")
    if not isinstance(claim_ref, str) or not claim_ref:
        return [f"{item.rel}: missing claim_ref"]
    claim_path = awl_root / claim_ref
    if not claim_path.is_file():
        return [f"{item.rel}: claim_ref {claim_ref} does not resolve under {awl_root}"]
    try:
        claim = load_yaml(claim_path)
    except LoaderError as exc:
        return [f"{item.rel}: claim {claim_ref} unreadable: {exc}"]
    if not isinstance(claim, dict):
        return [f"{item.rel}: claim {claim_ref} is not a mapping"]
    if validate_active_work_ledger_record(claim, claim_path):
        return [f"{item.rel}: claim {claim_ref} fails Active-Work Ledger validation"]
    if claim.get("controller_id") != item.record.get("controller_id") or claim.get("lane_id") != item.record.get("lane_id"):
        return [f"{item.rel}: claim {claim_ref} controller_id/lane_id does not match the record"]
    return []


def _chain_summary(controller_id: str, lane_id: str, ordered: list[_LoadedRecord]) -> dict[str, Any]:
    kind_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for item in ordered:
        kind = str(item.record.get("effect_kind"))
        status = str(item.record.get("effect_status"))
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
    head_sha256 = ordered[-1].file_sha256 if ordered else None
    return {
        "controller_id": controller_id,
        "lane_id": lane_id,
        "record_count": len(ordered),
        "first_record_ref": ordered[0].rel if ordered else None,
        "last_record_ref": ordered[-1].rel if ordered else None,
        "head_sha256": head_sha256,
        "effect_kind_counts": dict(sorted(kind_counts.items())),
        "effect_status_counts": dict(sorted(status_counts.items())),
    }


def _build_summary(chains: list[dict[str, Any]], errors: Iterable[str]) -> dict[str, Any]:
    total_kinds: dict[str, int] = {}
    total_statuses: dict[str, int] = {}
    record_count = 0
    for chain in chains:
        record_count += chain["record_count"]
        for kind, count in chain["effect_kind_counts"].items():
            total_kinds[kind] = total_kinds.get(kind, 0) + count
        for status, count in chain["effect_status_counts"].items():
            total_statuses[status] = total_statuses.get(status, 0) + count
    errors = list(errors)
    return {
        "ok": not errors,
        "record_count": record_count,
        "chains": chains,
        "effect_kind_counts": dict(sorted(total_kinds.items())),
        "effect_status_counts": dict(sorted(total_statuses.items())),
        "errors": errors,
    }
