"""Worktree Lease schema validation (PCO Slice 2A / PCO-024).

Validates Worktree Lease records against
``schemas/worktree-lease.schema.yaml``.

Scope discipline — Slice 2A is **record/validate only**:

* this check validates one record at a time against the schema;
* it MUST NOT cross-check lease/lease overlap, lease/claim coverage,
  or any other cross-record invariant beyond the structural per-record
  shape. The Slice 1/2 ``active_work_ledger_conflicts`` check is
  additively extended with the lease-aware predicates (``PCO-021``,
  ``PCO-022``, ``PCO-023``), gated on the discovery of at least one
  valid lease record in the scanned tree so that trees with zero
  lease records preserve Slice 1/2 behavior unchanged.

PCO-024 adds signature validation for ``schema_version: "2"`` lease
records. Signature errors are separate from schema errors (``PCO-020``)
so that ``active_work_ledger_conflicts`` can still detect structural
lease/claim conflicts using schema-valid-but-unsigned or
schema-valid-but-bad-signature leases without cascading errors.

Signing payload: compact JSON with sorted keys of the lease record
dict with ``worktree_lease_signature`` removed, encoded as UTF-8.
Canonicalization identifier: ``creator-engine/worktree-lease-signature/v1``.

PCO-024 failure modes (all cite this check):

* malformed signature bytes (not valid unpadded base64url or wrong length);
* missing or unknown controller-key record for the ``key_ref``;
* revoked controller-key record;
* ``key_ref`` / ``controller_id`` binding mismatch;
* Ed25519 signature verification failure.

A file is treated as a candidate Worktree Lease record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."`` (atomic-write
  temp files are skipped, mirroring the Slice 0 ledger discipline);
* the loaded YAML is a mapping whose ``kind`` field equals
  ``worktree-lease-record``.

Failures cite ``PCO-020`` (Worktree Lease record contract) and the
prose contract at ``docs/operations/WORKTREE_LEASE_PROTOCOL.md``.
Non-schema structural failures (file not a YAML mapping) cite
``worktree_lease_invalid_record`` to keep schema violations distinct
from structural pre-validation failures, mirroring the distinction
used by ``active_work_ledger_schema``.

See:
  - ``docs/operations/WORKTREE_LEASE_PROTOCOL.md``
  - ``docs/architecture/parallel-controller-orchestration.md``
  - ``schemas/worktree-lease.schema.yaml``
"""

from __future__ import annotations

import base64
import binascii
import ctypes
import ctypes.util
import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "worktree_lease_schema"
CONTRACT = "docs/operations/WORKTREE_LEASE_PROTOCOL.md"
SCHEMA = "schemas/worktree-lease.schema.yaml"
KIND_VALUE = "worktree-lease-record"
CODE_SCHEMA = "PCO-020"
CODE_SIGNATURE = "PCO-024"
CODE_INVALID = "worktree_lease_invalid_record"

_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Lazy-loaded libsodium handle.
_libsodium: ctypes.CDLL | None = None
_libsodium_load_error: str | None = None


def _get_libsodium() -> ctypes.CDLL | None:
    global _libsodium, _libsodium_load_error
    if _libsodium is not None:
        return _libsodium
    if _libsodium_load_error is not None:
        return None
    lib_path = ctypes.util.find_library("sodium")
    if not lib_path:
        _libsodium_load_error = "libsodium not found on this system"
        return None
    try:
        _libsodium = ctypes.CDLL(lib_path)
        return _libsodium
    except OSError as exc:
        _libsodium_load_error = f"libsodium could not be loaded: {exc}"
        return None


def _decode_base64url(value: str) -> bytes:
    if "=" in value or not _BASE64URL_RE.fullmatch(value):
        raise ValueError(f"not valid unpadded base64url")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"base64url decode failed: {exc}") from exc


def _verify_ed25519(sig: bytes, msg: bytes, pk: bytes) -> bool | None:
    """Verify an Ed25519 detached signature via libsodium.

    Returns True on success, False on failure, None if libsodium unavailable.
    """
    lib = _get_libsodium()
    if lib is None:
        return None
    func = lib.crypto_sign_ed25519_verify_detached
    func.restype = ctypes.c_int
    func.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulonglong, ctypes.c_char_p]
    ret = func(sig, msg, ctypes.c_ulonglong(len(msg)), pk)
    return ret == 0


def _canonical_signing_payload(record: dict[str, Any]) -> bytes:
    payload = {k: v for k, v in record.items() if k != "worktree_lease_signature"}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    if "schemas" in parts or "templates" in parts:
        return True
    return False


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_lease(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_worktree_lease_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Worktree Lease files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
                and not _is_under_excluded(p)
                and not _is_tmp_artifact(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if not _record_is_lease(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_worktree_lease_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the Worktree Lease schema (PCO-020).

    Schema validation only. No signature or cross-record checks.
    Used by active_work_ledger_conflicts to gate PCO-021/022/023 predicates.
    """
    errors = validate_with_schema(
        record,
        SCHEMA,
        path,
        code=CODE_SCHEMA,
        contract=CONTRACT,
    )
    return list(errors)


def _build_key_lookup(paths: list[Path]) -> dict[str, tuple[Path, dict[str, Any]]]:
    """Discover controller-key records reachable from paths and index by key_ref.

    Resolution is deterministic and fail-closed:

    * Each key is indexed only by its path relative to an explicit scan root or
      to the parent directory of a discovered lease file (the "package root").
      No arbitrary ``tenants/...`` suffix matching is performed.
    * If the same ``key_ref`` string resolves to two distinct physical files
      (ambiguous), neither entry is included in the returned lookup so that
      ``validate_lease_signature`` fails closed with PCO-024 rather than
      silently picking one.
    """
    from .controller_key_schema import iter_controller_key_records

    # Collect explicit scan roots.
    roots: list[Path] = []
    for raw in paths:
        p = Path(raw)
        root = p if p.is_dir() else p.parent
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved not in roots:
            roots.append(resolved)

    # Also add each lease file's parent directory so that a key_ref like
    # ``tenants/T/controllers/C.key.yaml`` resolves correctly when the scan
    # root is a parent of the lease package (e.g. ``examples/well-formed/``).
    for lease_path in iter_worktree_lease_records(list(paths)):
        try:
            lease_dir = lease_path.resolve().parent
        except OSError:
            continue
        if lease_dir not in roots:
            roots.append(lease_dir)

    # Build a raw map: key_ref -> list of distinct resolved key paths.
    raw: dict[str, list[tuple[Path, Path]]] = {}
    for key_path in iter_controller_key_records(paths):
        try:
            resolved_key = key_path.resolve()
        except OSError:
            continue
        for root in roots:
            try:
                rel = resolved_key.relative_to(root)
                key_ref = rel.as_posix()
            except ValueError:
                continue
            bucket = raw.setdefault(key_ref, [])
            if not any(r == resolved_key for _, r in bucket):
                bucket.append((key_path, resolved_key))

    # Finalise: omit ambiguous entries so callers fail closed.
    lookup: dict[str, tuple[Path, dict[str, Any]]] = {}
    for key_ref, entries in raw.items():
        if len(entries) > 1:
            continue
        orig_path, _ = entries[0]
        try:
            key_record = load_yaml(orig_path)
        except LoaderError:
            continue
        if not isinstance(key_record, dict):
            continue
        lookup[key_ref] = (orig_path, key_record)

    return lookup


def validate_lease_signature(
    record: dict[str, Any],
    path: Path,
    key_lookup: dict[str, tuple[Path, dict[str, Any]]],
) -> list[ValidationError]:
    """Validate PCO-024 signature for a schema_version "2" lease record.

    Only applies to records where schema_version == "2" and
    worktree_lease_signature is a mapping (schema validation owns the
    structural check before this is called).

    Returns PCO-024 errors only; schema errors remain PCO-020.
    """
    if record.get("schema_version") != "2":
        return []
    sig_obj = record.get("worktree_lease_signature")
    if not isinstance(sig_obj, dict):
        return []

    errors: list[ValidationError] = []

    key_ref = sig_obj.get("key_ref")
    if not isinstance(key_ref, str) or not key_ref:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                "PCO-024: worktree_lease_signature.key_ref is required",
                CONTRACT,
            )
        )
        return errors

    key_entry = key_lookup.get(key_ref)
    if key_entry is None:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                f"PCO-024: controller-key record not found for key_ref {key_ref!r}",
                CONTRACT,
            )
        )
        return errors

    _key_path, key_record = key_entry

    # Require PCO-025-valid key record before trusting its public key.
    from .controller_key_schema import validate_controller_key_record as _validate_key
    if _validate_key(key_record, _key_path):
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                f"PCO-024: controller-key record for key_ref {key_ref!r} is not PCO-025-valid",
                CONTRACT,
            )
        )
        return errors

    lease_controller_id = str(record.get("controller_id", ""))
    key_controller_id = str(key_record.get("controller_id", ""))
    if key_controller_id != lease_controller_id:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                (
                    f"PCO-024: key_ref controller_id {key_controller_id!r} does not "
                    f"match lease controller_id {lease_controller_id!r}"
                ),
                CONTRACT,
            )
        )
        return errors

    if key_record.get("status") == "revoked":
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                f"PCO-024: controller-key {key_ref!r} is revoked",
                CONTRACT,
            )
        )
        return errors

    sig_value = sig_obj.get("value")
    if not isinstance(sig_value, str) or not sig_value:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/value",
                "PCO-024: worktree_lease_signature.value is required",
                CONTRACT,
            )
        )
        return errors

    try:
        sig_bytes = _decode_base64url(sig_value)
    except ValueError:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/value",
                "PCO-024: signature value is not valid unpadded base64url",
                CONTRACT,
            )
        )
        return errors

    if len(sig_bytes) != 64:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/value",
                f"PCO-024: ed25519 signature must decode to 64 bytes, got {len(sig_bytes)}",
                CONTRACT,
            )
        )
        return errors

    pk_obj = key_record.get("public_key") if isinstance(key_record.get("public_key"), dict) else {}
    pk_value = pk_obj.get("value") if isinstance(pk_obj, dict) else None
    if not isinstance(pk_value, str) or not pk_value:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                "PCO-024: controller-key public_key.value is missing",
                CONTRACT,
            )
        )
        return errors

    try:
        pk_bytes = _decode_base64url(pk_value)
    except ValueError:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                "PCO-024: controller-key public_key.value is not valid unpadded base64url",
                CONTRACT,
            )
        )
        return errors

    if len(pk_bytes) != 32:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/key_ref",
                f"PCO-024: ed25519 public key must be 32 bytes, got {len(pk_bytes)}",
                CONTRACT,
            )
        )
        return errors

    try:
        payload_bytes = _canonical_signing_payload(record)
    except (TypeError, ValueError) as exc:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/",
                f"PCO-024: lease record contains non-JSON-serializable value: {exc}",
                CONTRACT,
            )
        )
        return errors
    verified = _verify_ed25519(sig_bytes, payload_bytes, pk_bytes)

    if verified is None:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/value",
                "PCO-024: Ed25519 signature could not be verified (libsodium unavailable)",
                CONTRACT,
            )
        )
    elif not verified:
        errors.append(
            make_error(
                CODE_SIGNATURE,
                path,
                "/worktree_lease_signature/value",
                "PCO-024: Ed25519 signature verification failed",
                CONTRACT,
            )
        )

    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_SIGNATURE])
def run(paths: Iterable[Path]) -> CheckResult:
    path_list = list(paths)
    key_lookup = _build_key_lookup(path_list)
    errors: list[ValidationError] = []
    for record_path in iter_worktree_lease_records(path_list):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(
                make_error(
                    CODE_INVALID,
                    record_path,
                    "/",
                    "worktree-lease record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        schema_errors = validate_worktree_lease_record(record, record_path)
        errors.extend(schema_errors)
        if not schema_errors:
            errors.extend(validate_lease_signature(record, record_path, key_lookup))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
