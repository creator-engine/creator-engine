"""G2.004.1 PCL runtime (``ce pcl {append,verify,replay,index,merge}``).

Turns the **already-landed** G2.004.0 PCL *record* substrate
(``checks/pcl_record.py`` + ``schemas/pcl-record.schema.yaml``) into an
executable, local, daemonless, network-free ``ce pcl`` surface. It mirrors the
landed ``ce_event_runtime`` (append-only hash chain + head manifest, injectable
transport, read-only ``git check-ignore`` guard) and reuses the landed validator
for every shape decision, so a runtime-produced record is byte-for-byte the same
artifact the ``pcl_record`` validator already accepts.

Floors preserved (G2.004.0 carries over unchanged):

* **No cryptography / no key custody.** ``signature`` stays a shape-only mapping
  whose ``value`` is ``reserved-inactive``. No signing, verification keys, or
  credential handling.
* **Operator-only privileged floor.** ``agent_ratifier`` / ``source`` may not
  emit; the canonical non-ratifying role set is reused from the validator. PCL
  records record operating-mode *context* only and never ratify.
* **Decoupling.** This runtime imports NO CE-event or distributed-identity code;
  CE-event references stay opaque 64-hex ``ce_event_content_hash`` pointers
  validated by the landed ``pcl_record`` check.

State boundary (G2.001.0 split — PCL differs from CE-events): the per-repo
authoritative **records** live under ``<pcl_root>/records/<ledger>/`` and are
**tracked-or-synced** (NOT git-ignored). Only the rebuildable **cache**
(``index``/``merge`` projections) lives under the git-ignored
``<pcl_root>/cache/<ledger>/``. Writing PCL state under a legacy ``.hermes/``
path is refused (write-freeze). Every refusal is raised **before any write**.

Prose contract: ``docs/operations/PCL_PROTOCOL.md``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from .checks import pcl_record as pcl_check
from .schema import validate_with_schema

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "pcl-record.schema.yaml"
PROSE_CONTRACT = "docs/operations/PCL_PROTOCOL.md"

HEAD_FILENAME = "_head.json"
HEAD_KIND = "pcl-chain-head"
INDEX_KIND = "pcl-index"
REPLAY_KIND = "pcl-replay"
MERGE_KIND = "pcl-merge-result"
SCHEMA_VERSION = "1"

RECORDS_SUBDIR = "records"
CACHE_SUBDIR = "cache"

SIGNATURE_SCHEME = "reserved-shape-only"
SIGNATURE_VALUE = "reserved-inactive"
DEFAULT_KEY_ID = "operator-reserved"

_LEDGER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

GitRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess"]


# ---------------------------------------------------------------------------
# Errors (each carries a stable code; all refusals raise BEFORE any write)
# ---------------------------------------------------------------------------


class PclRuntimeError(Exception):
    code = "G2-PCL-ERROR"


class PclAppendError(PclRuntimeError):
    code = "G2-PCL-APPEND-ERROR"


class RoleFloorRefused(PclAppendError):
    code = "G2-PCL-ROLE-FLOOR"


class ModeInvalid(PclAppendError):
    code = "G2-PCL-MODE-INVALID"


class RecordKindInvalid(PclAppendError):
    code = "G2-PCL-RECORD-KIND"


class SignatureReserved(PclAppendError):
    code = "G2-PCL-SIGNATURE-RESERVED"


class WriteFreezeRefused(PclAppendError):
    code = "G2-PCL-WRITE-FREEZE"


class ChainLinkError(PclAppendError):
    code = "G2-PCL-CHAIN-LINK"


class CacheNotIgnored(PclRuntimeError):
    code = "G2-PCL-CACHE-NOT-IGNORED"


class PclVerifyError(PclRuntimeError):
    code = "G2-PCL-VERIFY-ERROR"


class PclReplayError(PclRuntimeError):
    code = "G2-PCL-REPLAY-ERROR"


class PclIndexError(PclRuntimeError):
    code = "G2-PCL-INDEX-ERROR"


class PclMergeError(PclRuntimeError):
    code = "G2-PCL-MERGE-CONFLICT"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppendResult:
    record_path: Path
    head_path: Path
    record: dict[str, Any]
    ledger: str
    sequence: int
    content_hash: str
    parent_hash: str | None


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    ledger: str
    summary: dict[str, Any]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ReplayResult:
    ledger: str
    content_hash: str
    records: tuple[dict[str, Any], ...]
    projection: dict[str, Any]


@dataclass(frozen=True)
class IndexResult:
    ledger: str
    content_hash: str
    index: dict[str, Any]
    cache_path: Path | None


@dataclass(frozen=True)
class MergeResult:
    ok: bool
    target: str
    content_hash: str
    merged: dict[str, Any]
    conflicts: tuple[str, ...]
    cache_path: Path | None


# ---------------------------------------------------------------------------
# Canonical serialization + hashing
# ---------------------------------------------------------------------------


def _json_bytes(obj: Any) -> str:
    """Deterministic projection serialization: sorted keys, newline-terminated."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _projection_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(payload).encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


# ---------------------------------------------------------------------------
# Repo / ignore helpers
# ---------------------------------------------------------------------------


def _default_git_runner(argv: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), check=False, capture_output=True, text=True)


def _detect_repo_root(path: Path) -> Path | None:
    try:
        current = path.resolve()
    except OSError:
        current = path
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


def _has_hermes_segment(path: Path) -> bool:
    try:
        parts = path.resolve().parts
    except OSError:
        parts = path.parts
    return any(part == ".hermes" for part in parts)


def _require_records_root_not_legacy(records_root: Path) -> None:
    """PCL records are authoritative tracked-or-synced state; they MUST NOT be
    written under a legacy ``.hermes/`` path (write-freeze)."""
    if _has_hermes_segment(records_root):
        raise WriteFreezeRefused(
            f"PCL records root {records_root} targets a legacy .hermes/ path; active v2 PCL "
            "records must live under the tracked .ce/pcl/records/ home (not .hermes/pcl)"
        )


def _require_ignored_cache_root(cache_root: Path, cache_dir: Path, repo_root: Path | None, runner: GitRunner) -> None:
    """The rebuildable PCL cache (index/merge projections) MUST be git-ignored
    when inside a repository — records stay tracked, cache never does."""
    enclosing = repo_root if repo_root is not None else _detect_repo_root(cache_root)
    if enclosing is None or not _is_inside(cache_root, enclosing):
        return
    probe = cache_dir / "_probe.json"
    proc = runner(["git", "-C", str(enclosing), "check-ignore", "-q", "--", str(probe)])
    if proc.returncode != 0:
        raise CacheNotIgnored(
            f"PCL cache root {cache_root} is inside repo {enclosing} but is not git-ignored; "
            "rebuildable PCL index/merge projections must live under an ignored path "
            "(e.g. .ce/pcl/cache/)"
        )


# ---------------------------------------------------------------------------
# Transport seam — default local filesystem semantics, no network
# ---------------------------------------------------------------------------


class Transport(Protocol):
    def head(self, ledger_dir: Path) -> dict[str, Any] | None: ...
    def write_record(self, ledger_dir: Path, seq: int, record_id: str, record: dict[str, Any]) -> Path: ...
    def write_head(self, ledger_dir: Path, head: dict[str, Any]) -> Path: ...
    def read_records(self, ledger_dir: Path) -> list[tuple[Path, dict[str, Any]]]: ...


def _read_head(head_path: Path) -> dict[str, Any] | None:
    if not head_path.is_file():
        return None
    try:
        data = json.loads(head_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ChainLinkError(f"head manifest at {head_path} is unreadable: {exc}") from exc
    if not isinstance(data, dict) or "sequence" not in data or "head_content_hash" not in data:
        raise ChainLinkError(f"head manifest at {head_path} is malformed; cannot safely link a new record")
    return data


class FilesystemTransport:
    """Default transport: append-only local writes (atomic temp + rename)."""

    name = "local"

    def head(self, ledger_dir: Path) -> dict[str, Any] | None:
        return _read_head(ledger_dir / HEAD_FILENAME)

    def write_record(self, ledger_dir: Path, seq: int, record_id: str, record: dict[str, Any]) -> Path:
        path = ledger_dir / f"{seq:06d}-{record_id}.json"
        if path.exists():
            raise PclAppendError(f"PCL record already exists, refusing to overwrite: {path}")
        _atomic_write(path, _json_bytes(record))
        return path

    def write_head(self, ledger_dir: Path, head: dict[str, Any]) -> Path:
        path = ledger_dir / HEAD_FILENAME
        _atomic_write(path, _json_bytes(head))
        return path

    def read_records(self, ledger_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
        out: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(ledger_dir.glob("*.json")):
            if path.name == HEAD_FILENAME:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append((path, data))
        return out


# ---------------------------------------------------------------------------
# Shared floor checks (reuse the landed G2.004.0 validator verbatim)
# ---------------------------------------------------------------------------


def _check_role_floor(emitting_role: str) -> None:
    role = pcl_check._normalize_token(emitting_role)
    if role in pcl_check.FORBIDDEN_ACTIVE_ROLES or role not in pcl_check.EMITTING_ROLES:
        raise RoleFloorRefused(
            f"emitting_role {emitting_role!r} must be a canonical non-ratifying role; "
            "agent_ratifier/source are reserved-inactive and may not emit PCL records"
        )


def _check_mode(operating_mode: str) -> None:
    if pcl_check._normalize_token(operating_mode) not in pcl_check.OPERATING_MODES:
        raise ModeInvalid(
            f"operating_mode {operating_mode!r} must be one of "
            f"{sorted(pcl_check.OPERATING_MODES)} (context only; no activation)"
        )


def _check_record_kind(record_kind: str) -> None:
    if pcl_check._normalize_token(record_kind) not in pcl_check.RECORD_KINDS:
        raise RecordKindInvalid(
            f"record_kind {record_kind!r} must be one of {sorted(pcl_check.RECORD_KINDS)}"
        )


def _check_signature_value(signature_value: str) -> None:
    if pcl_check._normalize_token(signature_value) not in {"reserved_inactive"}:
        raise SignatureReserved(
            f"signature value {signature_value!r} must stay reserved-inactive in G2.004.x; "
            "cryptographic signing and key custody are deferred"
        )


def _check_body_write_freeze(body: Any) -> None:
    if pcl_check._subtree_contains_hermes_pcl_write(body):
        raise WriteFreezeRefused(
            "PCL record body must not target .hermes/pcl as active v2 state; "
            "the canonical home is the tracked .ce/pcl/records/ zone"
        )


def _signature(key_id: str) -> dict[str, str]:
    return {"scheme": SIGNATURE_SCHEME, "key_id": key_id, "value": SIGNATURE_VALUE}


def _build_record(
    *,
    record_id: str,
    record_kind: str,
    sequence: int,
    parent_hash: str | None,
    emitting_role: str,
    operating_mode: str,
    recorded_at: str,
    body: dict[str, Any],
    key_id: str,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_id": record_id,
        "record_kind": record_kind,
        "sequence": sequence,
        "parent_hash": parent_hash,
        "emitting_role": emitting_role,
        "operating_mode": operating_mode,
        "recorded_at": recorded_at,
        "body": body,
    }
    # content_hash excludes content_hash + signature (G2.004.0 canonical rule).
    record["content_hash"] = pcl_check._canonical_hash(record)
    record["signature"] = _signature(key_id)
    return record


def _self_validate_record(record: dict[str, Any], ledger_dir: Path) -> None:
    # Shape: reuse the landed record schema. Position-independent only — chain
    # linkage is a whole-chain property verified by `verify`, never asserted on a
    # single record (which `_validate_records` would treat as genesis).
    errors = validate_with_schema(
        {"pcl_record": record}, SCHEMA_PATH, "<pcl-runtime>",
        code=pcl_check.CODE_SCHEMA, contract=PROSE_CONTRACT,
    )
    if pcl_check._normalize_token(record.get("record_kind", "")) == pcl_check.EVENT_BLOCK_POINTER_KIND:
        errors.extend(pcl_check._validate_pointer(record, ledger_dir, ("pcl_record",)))
    if errors:
        raise PclAppendError(
            "produced PCL record fails the landed pcl_record contract: "
            + "; ".join(err.format() for err in errors)
        )


def _safe_relpath(path: Path, root: Path | str) -> str:
    try:
        return Path(path).relative_to(Path(root)).as_posix()
    except ValueError:
        return Path(path).as_posix()


# ---------------------------------------------------------------------------
# ce pcl append
# ---------------------------------------------------------------------------


def append(
    *,
    ledger: str,
    pcl_root: Path | str,
    record_id: str,
    record_kind: str,
    emitting_role: str,
    operating_mode: str,
    body: dict[str, Any],
    recorded_at: str,
    repo_root: Path | str | None = None,
    transport: Transport | None = None,
    key_id: str = DEFAULT_KEY_ID,
    signature_value: str = SIGNATURE_VALUE,
) -> AppendResult:
    """Append one shape-only-signed PCL record to a local authoritative chain.

    Computes ``parent_hash`` from the current head, assigns the monotonic
    ``sequence`` (``0`` for genesis), computes ``content_hash`` with the exact
    G2.004.0 canonical rule, self-validates against the landed record schema +
    semantic predicates, then atomically writes the record + head manifest under
    the tracked ``records/`` home. Every refusal raises **before any write**.
    """
    if not isinstance(ledger, str) or not _LEDGER_RE.match(ledger):
        raise PclAppendError(f"ledger {ledger!r} must match {_LEDGER_RE.pattern}")
    if not isinstance(body, dict):
        raise PclAppendError("body must be a mapping")

    transport = transport or FilesystemTransport()

    # 1. Floor checks — all before any read/build/write.
    _check_record_kind(record_kind)
    _check_role_floor(emitting_role)
    _check_mode(operating_mode)
    _check_signature_value(signature_value)
    _check_body_write_freeze(body)

    records_root = Path(pcl_root) / RECORDS_SUBDIR
    ledger_dir = records_root / ledger

    # 2. Records are authoritative tracked state; refuse a legacy .hermes/ target.
    _require_records_root_not_legacy(records_root)

    # 3. Resolve sequence + parent_hash from the head.
    head = transport.head(ledger_dir)
    if head is None:
        sequence = 0
        parent_hash: str | None = None
    else:
        sequence = int(head["sequence"]) + 1
        parent_hash = str(head["head_content_hash"])

    # 4. Build the canonical record + self-validate against the landed contract.
    record = _build_record(
        record_id=record_id,
        record_kind=record_kind,
        sequence=sequence,
        parent_hash=parent_hash,
        emitting_role=emitting_role,
        operating_mode=operating_mode,
        recorded_at=recorded_at,
        body=body,
        key_id=key_id,
    )
    _self_validate_record(record, ledger_dir)

    # --- Side effects begin here (record file, then head manifest) ---
    record_path = transport.write_record(ledger_dir, sequence, record_id, record)
    head_payload = {
        "kind": HEAD_KIND,
        "schema_version": SCHEMA_VERSION,
        "ledger": ledger,
        "sequence": sequence,
        "record_count": sequence + 1,
        "head_record_id": record_id,
        "head_content_hash": record["content_hash"],
        "last_record_ref": _safe_relpath(record_path, pcl_root),
    }
    head_path = transport.write_head(ledger_dir, head_payload)

    return AppendResult(
        record_path=record_path,
        head_path=head_path,
        record=record,
        ledger=ledger,
        sequence=sequence,
        content_hash=record["content_hash"],
        parent_hash=parent_hash,
    )


# ---------------------------------------------------------------------------
# Shared read path
# ---------------------------------------------------------------------------


def _load_chain(ledger: str, pcl_root: Path | str, transport: Transport) -> tuple[Path, list[dict[str, Any]]]:
    ledger_dir = Path(pcl_root) / RECORDS_SUBDIR / ledger
    if not ledger_dir.is_dir():
        raise PclRuntimeError(f"no PCL ledger at {ledger_dir}")
    pairs = transport.read_records(ledger_dir)
    return ledger_dir, [data for _path, data in pairs]


# ---------------------------------------------------------------------------
# ce pcl verify
# ---------------------------------------------------------------------------


def verify(*, ledger: str, pcl_root: Path | str, transport: Transport | None = None) -> VerifyResult:
    """Validate an on-disk PCL chain: shape (delegated to ``pcl_record``), content
    addressing, hash-chain linkage, role floor, operating-mode enum, signature
    shape, event-block-pointer shape, write-freeze, and head-manifest agreement."""
    transport = transport or FilesystemTransport()
    ledger_dir = Path(pcl_root) / RECORDS_SUBDIR / ledger
    if not ledger_dir.is_dir():
        return VerifyResult(
            ok=False, ledger=ledger, summary={"record_count": 0},
            errors=(f"no PCL ledger at {ledger_dir}",),
        )

    records = [data for _p, data in transport.read_records(ledger_dir)]
    errors: list[str] = []

    for idx, record in enumerate(records):
        for err in validate_with_schema(
            {"pcl_record": record}, SCHEMA_PATH, f"{ledger}#{idx}",
            code=pcl_check.CODE_SCHEMA, contract=PROSE_CONTRACT,
        ):
            errors.append(err.format())

    for err in pcl_check._validate_records(records, ledger_dir, root_key="pcl_chain"):
        errors.append(err.format())

    head_errors, head = _verify_head(ledger_dir, records)
    errors.extend(head_errors)

    summary = {
        "ledger": ledger,
        "record_count": len(records),
        "head_content_hash": head.get("head_content_hash") if head else None,
        "head_sequence": head.get("sequence") if head else None,
        "errors": errors,
    }
    return VerifyResult(ok=not errors, ledger=ledger, summary=summary, errors=tuple(errors))


def _verify_head(ledger_dir: Path, records: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    head_path = ledger_dir / HEAD_FILENAME
    head: dict[str, Any] | None = None
    if head_path.is_file():
        try:
            head = json.loads(head_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"head manifest unreadable: {exc}")
            return errors, None
    if not records:
        return errors, head
    if not isinstance(head, dict):
        errors.append(f"missing or invalid head manifest at {head_path}")
        return errors, None
    last = records[-1]
    if head.get("head_content_hash") != last.get("content_hash"):
        errors.append(
            f"head_content_hash {head.get('head_content_hash')} does not match last record "
            f"content_hash {last.get('content_hash')}"
        )
    if head.get("sequence") != last.get("sequence"):
        errors.append(
            f"head sequence {head.get('sequence')} does not match last record sequence {last.get('sequence')}"
        )
    return errors, head


# ---------------------------------------------------------------------------
# ce pcl replay
# ---------------------------------------------------------------------------


def replay(*, ledger: str, pcl_root: Path | str, transport: Transport | None = None) -> ReplayResult:
    transport = transport or FilesystemTransport()
    _ledger_dir, records = _load_chain(ledger, pcl_root, transport)
    ordered = sorted(records, key=lambda r: int(r.get("sequence", 0)))
    projection = {
        "kind": REPLAY_KIND,
        "schema_version": SCHEMA_VERSION,
        "ledger": ledger,
        "record_count": len(ordered),
        "records": [
            {
                "sequence": r.get("sequence"),
                "record_id": r.get("record_id"),
                "record_kind": r.get("record_kind"),
                "parent_hash": r.get("parent_hash"),
                "content_hash": r.get("content_hash"),
                "emitting_role": r.get("emitting_role"),
                "operating_mode": r.get("operating_mode"),
            }
            for r in ordered
        ],
    }
    return ReplayResult(
        ledger=ledger,
        content_hash=_projection_hash(projection),
        records=tuple(ordered),
        projection=projection,
    )


# ---------------------------------------------------------------------------
# ce pcl index (writes to the git-ignored cache)
# ---------------------------------------------------------------------------


def _build_index(ledger: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda r: int(r.get("sequence", 0)))
    kind_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    mode_counts: dict[str, int] = {}
    for r in ordered:
        kind = str(r.get("record_kind"))
        role = str(r.get("emitting_role"))
        mode = str(r.get("operating_mode"))
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        role_counts[role] = role_counts.get(role, 0) + 1
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    return {
        "kind": INDEX_KIND,
        "schema_version": SCHEMA_VERSION,
        "ledger": ledger,
        "record_count": len(ordered),
        "genesis_content_hash": ordered[0].get("content_hash") if ordered else None,
        "head_content_hash": ordered[-1].get("content_hash") if ordered else None,
        "head_sequence": ordered[-1].get("sequence") if ordered else None,
        "record_kind_counts": dict(sorted(kind_counts.items())),
        "emitting_role_counts": dict(sorted(role_counts.items())),
        "operating_mode_counts": dict(sorted(mode_counts.items())),
    }


def index(
    *,
    ledger: str,
    pcl_root: Path | str,
    transport: Transport | None = None,
    write_cache: bool = True,
    repo_root: Path | str | None = None,
    git_runner: GitRunner | None = None,
) -> IndexResult:
    transport = transport or FilesystemTransport()
    _ledger_dir, records = _load_chain(ledger, pcl_root, transport)
    index_doc = _build_index(ledger, records)
    content_hash = _projection_hash(index_doc)

    cache_path: Path | None = None
    if write_cache:
        cache_root = Path(pcl_root) / CACHE_SUBDIR
        cache_dir = cache_root / ledger
        runner = git_runner or _default_git_runner
        _require_ignored_cache_root(cache_root, cache_dir, Path(repo_root) if repo_root else None, runner)
        cache_path = cache_dir / "index.json"
        _atomic_write(cache_path, _json_bytes({**index_doc, "content_hash": content_hash}))
    return IndexResult(ledger=ledger, content_hash=content_hash, index=index_doc, cache_path=cache_path)


# ---------------------------------------------------------------------------
# ce pcl merge — deterministic, conflict-detecting, read-only projection
# ---------------------------------------------------------------------------


def merge(
    *,
    sources: Sequence[str],
    target: str,
    pcl_root: Path | str,
    transport: Transport | None = None,
    write_cache: bool = True,
    repo_root: Path | str | None = None,
    git_runner: GitRunner | None = None,
) -> MergeResult:
    """Deterministically combine two-or-more verified PCL ledger segments into a
    single ordered view, detecting forks. PCL never ratifies and ``merge`` never
    mutates authoritative records: it verifies each source, unions records by
    ``content_hash``, fails closed on any fork (two distinct records sharing a
    ``parent_hash``, or a ``sequence`` collision with differing content), and
    writes a read-only merge projection to the git-ignored cache."""
    transport = transport or FilesystemTransport()
    if len(sources) < 2:
        raise PclMergeError("merge requires at least two source ledgers")

    by_hash: dict[str, dict[str, Any]] = {}
    conflicts: list[str] = []

    for src in sources:
        result = verify(ledger=src, pcl_root=pcl_root, transport=transport)
        if not result.ok:
            raise PclMergeError(f"source ledger {src!r} does not verify; refusing to merge: {result.errors}")
        _ledger_dir, records = _load_chain(src, pcl_root, transport)
        for r in records:
            ch = str(r.get("content_hash"))
            existing = by_hash.get(ch)
            if existing is None:
                by_hash[ch] = r
            elif existing != r:
                conflicts.append(f"content_hash {ch} maps to two distinct records across sources")

    records_all = list(by_hash.values())

    # Fork detection: each parent_hash may be claimed by at most one child, and
    # each sequence by at most one content_hash.
    by_parent: dict[Any, set[str]] = {}
    by_seq: dict[int, set[str]] = {}
    for r in records_all:
        parent = r.get("parent_hash")
        ch = str(r.get("content_hash"))
        by_parent.setdefault(parent, set()).add(ch)
        by_seq.setdefault(int(r.get("sequence", 0)), set()).add(ch)
    for parent, children in sorted(by_parent.items(), key=lambda kv: str(kv[0])):
        if len(children) > 1:
            conflicts.append(f"fork: parent_hash {parent} has {len(children)} distinct children")
    for seq, hashes in sorted(by_seq.items()):
        if len(hashes) > 1:
            conflicts.append(f"fork: sequence {seq} claimed by {len(hashes)} distinct records")

    if conflicts:
        raise PclMergeError("PCL merge conflict (fail-closed); " + "; ".join(sorted(set(conflicts))))

    ordered = sorted(records_all, key=lambda r: int(r.get("sequence", 0)))
    merged_doc = {
        "kind": MERGE_KIND,
        "schema_version": SCHEMA_VERSION,
        "target": target,
        "sources": sorted(sources),
        "record_count": len(ordered),
        "head_content_hash": ordered[-1].get("content_hash") if ordered else None,
        "records": [
            {"sequence": r.get("sequence"), "record_id": r.get("record_id"), "content_hash": r.get("content_hash")}
            for r in ordered
        ],
    }
    content_hash = _projection_hash(merged_doc)

    cache_path: Path | None = None
    if write_cache:
        cache_root = Path(pcl_root) / CACHE_SUBDIR
        cache_dir = cache_root / target
        runner = git_runner or _default_git_runner
        _require_ignored_cache_root(cache_root, cache_dir, Path(repo_root) if repo_root else None, runner)
        cache_path = cache_dir / "merge.json"
        _atomic_write(cache_path, _json_bytes({**merged_doc, "content_hash": content_hash}))

    return MergeResult(
        ok=True, target=target, content_hash=content_hash, merged=merged_doc, conflicts=(), cache_path=cache_path,
    )
