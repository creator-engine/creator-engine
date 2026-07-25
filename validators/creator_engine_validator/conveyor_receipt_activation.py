"""Explicit, operator-only migration for a legacy conveyor receipt ledger.

This module is deliberately not called by discovery or the daemon.  Normal
operation continues to reject an unversioned ledger; migration is a separately
reviewed plan followed by an explicit apply bound to that plan's digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import conveyor_discovery as receipt


class ReceiptActivationRefused(ValueError):
    """An operator activation request cannot be proven safe to perform."""


@dataclass(frozen=True)
class ReceiptActivationPlan:
    state_path: Path
    legacy_device: int
    legacy_inode: int
    legacy_sha256: str
    migrated_receipts: tuple[dict[str, Any], ...]
    sha256: str

    @property
    def backup_name(self) -> str:
        return f".{self.state_path.name}.legacy-{self.sha256}.bak"


def _plan_digest(path: Path, metadata: os.stat_result, raw: bytes, entries: tuple[dict[str, Any], ...]) -> str:
    payload = {
        "legacy_device": metadata.st_dev,
        "legacy_inode": metadata.st_ino,
        "legacy_sha256": hashlib.sha256(raw).hexdigest(),
        "migrated_receipts": list(entries),
        "state_path": str(path),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _legacy_entries(raw: bytes) -> tuple[dict[str, Any], ...]:
    """Validate the old shape only on the explicit operator activation path."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptActivationRefused("legacy_receipt_unreadable") from exc
    if not isinstance(data, Mapping) or set(data) != {"processed"} or not isinstance(data["processed"], list):
        raise ReceiptActivationRefused("legacy_receipt_shape_invalid")
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in data["processed"]:
        if not isinstance(item, Mapping):
            raise ReceiptActivationRefused("legacy_receipt_entry_invalid")
        seat_id, branch, sha = (item.get(name) for name in ("seat_id", "branch", "sha"))
        if not all(isinstance(value, str) and value for value in (seat_id, branch, sha)) or receipt.SHA_PATTERN.fullmatch(sha) is None:
            raise ReceiptActivationRefused("legacy_receipt_entry_invalid")
        key = (seat_id, branch, sha)
        if key in seen:
            raise ReceiptActivationRefused("legacy_receipt_entry_duplicate")
        seen.add(key)
        # Historical ``processed`` records have no outcome marker.  Conservatively
        # seal each as failed so an old handled tuple can never be claimed again.
        entries.append({"seat_id": seat_id, "branch": branch, "sha": sha, "state": "failed", "completion_sealed": True})
    return tuple(sorted(entries, key=lambda item: (item["seat_id"], item["branch"], item["sha"])))


def _read_legacy(location: receipt._SecureReceiptDirectory) -> tuple[bytes, os.stat_result]:
    try:
        fd, metadata = receipt._open_verified_file(location, location.ledger_name, os.O_RDONLY)
    except (OSError, receipt.ReceiptPersistenceError) as exc:
        raise ReceiptActivationRefused("legacy_receipt_unavailable") from exc
    try:
        raw = receipt._read_all(fd)
        current = receipt._stat_at(location.fd, location.ledger_name)
        if not receipt._same_inode(metadata, current):
            raise ReceiptActivationRefused("legacy_receipt_changed")
    finally:
        close_error = receipt._close_fd(fd)
        if close_error is not None:
            raise ReceiptActivationRefused("legacy_receipt_close_failed") from close_error
    return raw, metadata


def _plan_locked(state_path: Path, location: receipt._SecureReceiptDirectory) -> ReceiptActivationPlan:
    raw, metadata = _read_legacy(location)
    entries = _legacy_entries(raw)
    return ReceiptActivationPlan(
        state_path=state_path,
        legacy_device=metadata.st_dev,
        legacy_inode=metadata.st_ino,
        legacy_sha256=hashlib.sha256(raw).hexdigest(),
        migrated_receipts=entries,
        sha256=_plan_digest(state_path, metadata, raw, entries),
    )


def plan(state_path: str | Path) -> ReceiptActivationPlan:
    path = receipt.normalize_receipt_state_path(state_path)
    with receipt._locked_receipt_directory(path) as (location, _lock_fd, _lock_metadata):
        return _plan_locked(path, location)


def _write_backup(location: receipt._SecureReceiptDirectory, name: str, raw: bytes) -> os.stat_result:
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | receipt._OPEN_FILE_FLAGS, 0o600, dir_fd=location.fd)
    except FileExistsError:
        # A retry may follow an interruption after the durable placeholder was
        # written but before the legacy name was replaced.  Resume only when the
        # existing private backup proves byte-identical to this reviewed plan.
        try:
            existing_fd, metadata = receipt._open_verified_file(location, name, os.O_RDONLY)
        except (OSError, receipt.ReceiptPersistenceError) as inspect_exc:
            raise ReceiptActivationRefused("legacy_backup_exists") from inspect_exc
        try:
            if receipt._read_all(existing_fd) != raw:
                raise ReceiptActivationRefused("legacy_backup_exists")
        finally:
            close_error = receipt._close_fd(existing_fd)
            if close_error is not None:
                raise ReceiptActivationRefused("legacy_backup_close_failed") from close_error
        return metadata
    try:
        receipt._validate_named_file(location, name, fd, exact_mode=None)
        os.fchmod(fd, 0o600)
        metadata = receipt._validate_named_file(location, name, fd)
        receipt._write_all(fd, raw)
        os.fsync(fd)
        receipt._validate_named_file(location, name, fd, expected=metadata)
    except (OSError, receipt.ReceiptPersistenceError) as exc:
        raise ReceiptActivationRefused("legacy_backup_write_failed") from exc
    finally:
        close_error = receipt._close_fd(fd)
        if close_error is not None:
            raise ReceiptActivationRefused("legacy_backup_close_failed") from close_error
    try:
        os.fsync(location.fd)
    except OSError as exc:
        raise ReceiptActivationRefused("legacy_backup_durability_unproven") from exc
    return metadata


def apply(state_path: str | Path, *, accept_plan_sha: str) -> ReceiptActivationPlan:
    path = receipt.normalize_receipt_state_path(state_path)
    with receipt._locked_receipt_directory(path) as (location, _lock_fd, _lock_metadata):
        current = _plan_locked(path, location)
        if accept_plan_sha != current.sha256:
            raise ReceiptActivationRefused("activation_plan_changed")
        raw, legacy_metadata = _read_legacy(location)
        if (legacy_metadata.st_dev, legacy_metadata.st_ino, hashlib.sha256(raw).hexdigest()) != (current.legacy_device, current.legacy_inode, current.legacy_sha256):
            raise ReceiptActivationRefused("legacy_receipt_changed")
        backup_metadata = _write_backup(location, current.backup_name, raw)
        try:
            location.rewalk()
            if not receipt._name_matches_inode(location, location.ledger_name, legacy_metadata):
                raise ReceiptActivationRefused("legacy_receipt_changed")
            os.replace(location.ledger_name, current.backup_name, src_dir_fd=location.fd, dst_dir_fd=location.fd)
            # The backup name was pre-created only to prove safe bytes; publication
            # replaces it atomically with the legacy inode after the final identity check.
            if not receipt._name_matches_inode(location, current.backup_name, legacy_metadata):
                raise ReceiptActivationRefused("legacy_backup_identity_unproven")
            os.fsync(location.fd)
            receipt._write_receipt_state(location, list(current.migrated_receipts), None)
        except BaseException:
            # Before v1 publication, restore the legacy name rather than leaving a
            # daemon-visible missing ledger.  ``expected=None`` means the ledger
            # name is absent; any ambiguous publication remains fail-closed.
            try:
                if receipt._name_matches_inode(location, current.backup_name, legacy_metadata) and receipt._ledger_matches_expected(location, None):
                    os.replace(current.backup_name, location.ledger_name, src_dir_fd=location.fd, dst_dir_fd=location.fd)
                    os.fsync(location.fd)
            except BaseException:
                pass
            raise
        # The pre-created backup inode is replaced by the legacy inode above.
        del backup_metadata
        return current


def rollback(state_path: str | Path, *, accept_plan_sha: str) -> None:
    """Explicitly restore the durable legacy backup after reviewing its plan SHA."""
    path = receipt.normalize_receipt_state_path(state_path)
    backup_name = f".{path.name}.legacy-{accept_plan_sha}.bak"
    with receipt._locked_receipt_directory(path) as (location, _lock_fd, _lock_metadata):
        try:
            backup_fd, backup_metadata = receipt._open_verified_file(location, backup_name, os.O_RDONLY)
        except (OSError, receipt.ReceiptPersistenceError) as exc:
            raise ReceiptActivationRefused("legacy_backup_unavailable") from exc
        try:
            raw = receipt._read_all(backup_fd)
            migrated_receipts = _legacy_entries(raw)
            try:
                current_receipts = receipt._receipt_entries(receipt._read_receipt_state(location)[0])
            except ValueError as exc:
                raise ReceiptActivationRefused("rollback_receipt_state_invalid") from exc
            if tuple(current_receipts) != migrated_receipts:
                raise ReceiptActivationRefused("rollback_receipt_state_diverged")
            if not receipt._name_matches_inode(location, backup_name, backup_metadata):
                raise ReceiptActivationRefused("legacy_backup_changed")
            location.rewalk()
            os.replace(backup_name, location.ledger_name, src_dir_fd=location.fd, dst_dir_fd=location.fd)
            os.fsync(location.fd)
        except (OSError, receipt.ReceiptPersistenceError) as exc:
            raise ReceiptActivationRefused("legacy_rollback_failed") from exc
        finally:
            close_error = receipt._close_fd(backup_fd)
            if close_error is not None:
                raise ReceiptActivationRefused("legacy_backup_close_failed") from close_error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_path")
    parser.add_argument("action", choices=("plan", "apply", "rollback"))
    parser.add_argument("--accept-plan-sha")
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            result = plan(args.state_path)
            print(json.dumps({"plan_sha256": result.sha256, "receipt_count": len(result.migrated_receipts)}, sort_keys=True))
        elif args.action == "apply":
            if not args.accept_plan_sha:
                raise ReceiptActivationRefused("activation_plan_sha_required")
            result = apply(args.state_path, accept_plan_sha=args.accept_plan_sha)
            print(json.dumps({"applied_plan_sha256": result.sha256, "receipt_count": len(result.migrated_receipts)}, sort_keys=True))
        else:
            if not args.accept_plan_sha:
                raise ReceiptActivationRefused("activation_plan_sha_required")
            rollback(args.state_path, accept_plan_sha=args.accept_plan_sha)
            print(json.dumps({"rolled_back_plan_sha256": args.accept_plan_sha}, sort_keys=True))
    except (ReceiptActivationRefused, receipt.ReceiptPersistenceError) as exc:
        print(f"conveyor-receipt-activation: {exc}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
