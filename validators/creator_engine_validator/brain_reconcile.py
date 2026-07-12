"""Fail-closed, reviewable static-evidence ledger reconciliation.

This module deliberately changes no assertion semantics.  It only replaces an
explicitly selected static evidence digest and re-addresses the hash chain that
follows it.  The caller must separately accept the exact deterministic plan.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import brain_runtime
from .checks import ce_brain_drift
from .runtime_evidence_spine import CONTENT_HASH_FIELD, GENESIS_PREV_HASH, canonical_content_hash


class BrainReconcileRefused(brain_runtime.BrainRuntimeError):
    code = "CE-BRAIN-RECONCILE-REFUSED"


@dataclass(frozen=True)
class ReconcileResult:
    ledger_path: Path
    plan: dict[str, Any]
    written: bool
    persisted_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"ledger_path": str(self.ledger_path), "persisted_sha256": self.persisted_sha256,
                "plan": self.plan, "written": self.written}


def _stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(value: Any) -> str:
    return hashlib.sha256(_stable(value).encode("utf-8")).hexdigest()


def _under(root: Path, candidate: Path) -> Path:
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise BrainReconcileRefused("path must resolve beneath repository root") from exc
    return resolved


def _ledger(root: Path, ledger_path: str | Path | None) -> Path:
    raw = Path(ledger_path) if ledger_path is not None else root / ".ce" / "brain" / "assertions.yaml"
    if not raw.is_absolute():
        raw = root / raw
    return _under(root, raw)


def _evidence(root: Path, reference: Any) -> Path:
    if not isinstance(reference, str) or not reference or reference.startswith("probe:") or "://" in reference:
        raise BrainReconcileRefused("selected assertion must use a static local evidence_ref")
    raw = Path(reference.split("#", 1)[0])
    if raw.is_absolute() or ".." in raw.parts:
        raise BrainReconcileRefused("evidence_ref must be a repository-relative path")
    candidate = _under(root, root / raw)
    if not candidate.is_file():
        raise BrainReconcileRefused("evidence_ref must resolve to a regular file beneath repository root")
    return candidate


def _hash_slot(record: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    claim = record.get("claim")
    if not isinstance(claim, dict):
        raise BrainReconcileRefused("selected assertion claim must be a mapping")
    slots: list[tuple[dict[str, Any], str, str]] = []
    for owner, prefix in ((claim, ""), (claim.get("evidence"), "evidence.")):
        if not isinstance(owner, dict):
            continue
        for key in ce_brain_drift._HASH_CLAIM_KEYS:  # shared drift-contract vocabulary
            value = owner.get(key)
            digest = ce_brain_drift._normalize_claimed_hash(value)
            if digest is not None:
                slots.append((owner, key, digest))
            elif key in owner:
                raise BrainReconcileRefused(f"selected assertion has malformed {prefix}{key} digest")
    if len(slots) != 1:
        raise BrainReconcileRefused("selected assertion must have exactly one recognized SHA-256 claim field")
    return slots[0]


def _latest(records: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, record in enumerate(records):
        assertion_id = record.get("id")
        if isinstance(assertion_id, str):
            result[assertion_id] = index
    return result


def _readdress(records: list[dict[str, Any]], start: int) -> None:
    for index in range(start, len(records)):
        record = records[index]
        record["prev_hash"] = str(records[index - 1][CONTENT_HASH_FIELD]) if index else GENESIS_PREV_HASH
        record[CONTENT_HASH_FIELD] = canonical_content_hash(record)


def plan(*, repo_root: str | Path, assertion_ids: Iterable[str], ledger_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = _ledger(root, ledger_path)
    selected = list(assertion_ids)
    if not selected or any(not isinstance(item, str) or not item for item in selected):
        raise BrainReconcileRefused("one or more explicit assertion IDs are required")
    if len(set(selected)) != len(selected):
        raise BrainReconcileRefused("duplicate assertion IDs are refused")
    try:
        records = brain_runtime.load_records_from_path(path)
    except brain_runtime.BrainRuntimeError as exc:
        raise BrainReconcileRefused("ledger is malformed or has an invalid chain") from exc
    before = str(records[-1][CONTENT_HASH_FIELD]) if records else None
    latest = _latest(records)
    unknown = [item for item in selected if item not in latest]
    if unknown:
        raise BrainReconcileRefused("unknown assertion ID: " + ", ".join(sorted(unknown)))
    updated = copy.deepcopy(records)
    changes: list[dict[str, Any]] = []
    indexes: list[int] = []
    for assertion_id in selected:
        index = latest[assertion_id]
        record = updated[index]
        if record.get("status") != "active":
            raise BrainReconcileRefused(f"assertion {assertion_id} is not active")
        method = record.get("verification_method")
        if not isinstance(method, dict) or method.get("type") != "static":
            raise BrainReconcileRefused(f"assertion {assertion_id} is not static evidence")
        owner, key, old = _hash_slot(record)
        observed = hashlib.sha256(_evidence(root, record.get("evidence_ref")).read_bytes()).hexdigest()
        if old == observed:
            continue
        owner[key] = observed
        changes.append({"id": assertion_id, "old_sha256": old, "new_sha256": observed, "record_index": index})
        indexes.append(index)
    if indexes:
        _readdress(updated, min(indexes))
        errors = brain_runtime.validate_records(updated, path)
        if errors:
            raise BrainReconcileRefused("reconciled ledger failed validation: " + "; ".join(error.format() for error in errors))
    after = str(updated[-1][CONTENT_HASH_FIELD]) if updated else None
    payload: dict[str, Any] = {
        "affected_record_count": len(updated) - min(indexes) if indexes else 0,
        "changed_assertion_ids": [change["id"] for change in changes],
        "changes": changes,
        "ledger_head_after": after,
        "ledger_head_before": before,
        "ledger_path": str(path),
        "selected_assertion_ids": selected,
        "write_required": bool(changes),
    }
    payload["plan_sha256"] = _sha(payload)
    return payload


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def apply(*, repo_root: str | Path, assertion_ids: Iterable[str], accept_plan_sha: str, ledger_path: str | Path | None = None) -> ReconcileResult:
    current = plan(repo_root=repo_root, assertion_ids=assertion_ids, ledger_path=ledger_path)
    if not isinstance(accept_plan_sha, str) or current["plan_sha256"] != accept_plan_sha:
        raise BrainReconcileRefused("--accept-plan-sha must exactly match the freshly recomputed plan")
    path = Path(current["ledger_path"])
    if not current["write_required"]:
        return ReconcileResult(path, current, False, None)
    original = path.read_bytes()
    records = brain_runtime.load_records_from_path(path)
    root = Path(repo_root).resolve()
    latest = _latest(records)
    for change in current["changes"]:
        record = records[latest[change["id"]]]
        owner, key, _old = _hash_slot(record)
        owner[key] = change["new_sha256"]
    _readdress(records, min(change["record_index"] for change in current["changes"]))
    text = brain_runtime.serialize_ledger(records)
    try:
        _atomic_write(path, text)
        brain_runtime.load_records_from_path(path)
        drift = ce_brain_drift.verify_state_root(root / ".ce", context=ce_brain_drift.DriftContext(repo_root=root))
        if not drift.ok:
            raise BrainReconcileRefused("post-write brain drift verification failed")
    except Exception:
        _atomic_write(path, original.decode("utf-8"))
        raise
    return ReconcileResult(path, current, True, hashlib.sha256(path.read_bytes()).hexdigest())
