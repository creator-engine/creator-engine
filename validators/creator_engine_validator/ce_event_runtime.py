"""G2.003.1 CE-event runtime (``ce event {sign,verify,append,replay,index}``).

Turns the **already-landed** G2.003.0 CE-event *block* substrate
(``checks/ce_event_block.py`` + ``schemas/ce-event-block.schema.yaml``) into an
executable, local, daemonless, network-free ``ce event`` surface. It mirrors the
established v1 runtime gates (``side_effect_ledger_runtime`` append-only hash
chain + head manifest; ``fanin_runtime`` deterministic content hash + read-only
``git check-ignore`` guard) and reuses the landed validator for every shape
decision, so a runtime-produced block is byte-for-byte the same artifact the
``ce_event_block`` validator already accepts.

Floors preserved (G2.003.0 carries over unchanged):

* **No cryptography / no key custody.** ``signature`` stays a shape-only mapping
  whose ``value`` is ``reserved-inactive`` (FR-004). This runtime introduces no
  signing, verification keys, key rotation, or credential handling.
* **Operator-only privileged floor.** ``agent_ratifier`` / ``source`` may not
  emit; the canonical non-ratifying role set is reused from the validator
  (FR-005). The runtime records operating-mode *context* only and activates no
  autonomy.
* **State boundary.** Active event state lands only under the **ignored**
  ``.ce/ce-events/spool/<stream>/`` root; targeting ``.hermes/ce-events`` is
  refused (write-freeze, FR-008).

Every refusal is raised **before any write**, so a refused call leaves the spool
byte-identical. The transport seam (default :class:`FilesystemTransport`,
local/git-file semantics) is injectable so the append/verify path is unit
testable with a fake and the default never makes a network call.

Prose contract: ``docs/operations/CE_EVENT_PROTOCOL.md``.
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

from .checks import ce_event_block as block_check
from .git_worktree import find_enclosing_git_worktree
from .schema import validate_with_schema

# The block schema lives at the repo root; resolve it package-relatively so the
# runtime self-validates regardless of the caller's working directory.
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "ce-event-block.schema.yaml"
PROSE_CONTRACT = "docs/operations/CE_EVENT_PROTOCOL.md"

HEAD_FILENAME = "_head.json"
HEAD_KIND = "ce-event-chain-head"
INDEX_KIND = "ce-event-index"
REPLAY_KIND = "ce-event-replay"
SCHEMA_VERSION = "1"

SIGNATURE_SCHEME = "reserved-shape-only"
SIGNATURE_VALUE = "reserved-inactive"
DEFAULT_KEY_ID = "operator-reserved"

_STREAM_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

GitRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess"]


# ---------------------------------------------------------------------------
# Errors (each carries a stable code; all refusals raise BEFORE any write)
# ---------------------------------------------------------------------------


class CeEventRuntimeError(Exception):
    """Base class for CE-event runtime errors. Carries a ``code``."""

    code = "G2-EVENT-ERROR"


class CeEventAppendError(CeEventRuntimeError):
    code = "G2-EVENT-APPEND-ERROR"


class RoleFloorRefused(CeEventAppendError):
    code = "G2-EVENT-ROLE-FLOOR"


class ModeInvalid(CeEventAppendError):
    code = "G2-EVENT-MODE-INVALID"


class SignatureReserved(CeEventAppendError):
    code = "G2-EVENT-SIGNATURE-RESERVED"


class WriteFreezeRefused(CeEventAppendError):
    code = "G2-EVENT-WRITE-FREEZE"


class EventRootNotIgnored(CeEventAppendError):
    code = "G2-EVENT-ROOT-NOT-IGNORED"


class ChainLinkError(CeEventAppendError):
    code = "G2-EVENT-CHAIN-LINK"


class CeEventVerifyError(CeEventRuntimeError):
    code = "G2-EVENT-VERIFY-ERROR"


class CeEventReplayError(CeEventRuntimeError):
    code = "G2-EVENT-REPLAY-ERROR"


class CeEventIndexError(CeEventRuntimeError):
    code = "G2-EVENT-INDEX-ERROR"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppendResult:
    block_path: Path
    head_path: Path
    block: dict[str, Any]
    stream: str
    sequence: int
    content_hash: str
    parent_hash: str | None


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    stream: str
    summary: dict[str, Any]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ReplayResult:
    stream: str
    content_hash: str
    blocks: tuple[dict[str, Any], ...]
    projection: dict[str, Any]


@dataclass(frozen=True)
class IndexResult:
    stream: str
    content_hash: str
    index: dict[str, Any]


# ---------------------------------------------------------------------------
# Canonical serialization + hashing (deterministic stdlib JSON)
# ---------------------------------------------------------------------------


def _json_bytes(obj: Any) -> str:
    """Deterministic record serialization: sorted keys, newline-terminated."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _content_hash_of(payload_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(payload_without_hash).encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


# ---------------------------------------------------------------------------
# Read-only git-ignore guard (the spool must never reach the tracked tree)
# ---------------------------------------------------------------------------


def _default_git_runner(argv: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), check=False, capture_output=True, text=True)


def _detect_repo_root(path: Path) -> Path | None:
    return find_enclosing_git_worktree(path)


def _is_inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


def _require_ignored_spool_root(
    spool_root: Path, stream_dir: Path, repo_root: Path | None, runner: GitRunner
) -> None:
    enclosing = repo_root if repo_root is not None else _detect_repo_root(spool_root)
    if enclosing is None or not _is_inside(spool_root, enclosing):
        return
    # Probe a representative file path *under* the spool, not the bare directory:
    # a `dir/` ignore pattern reliably matches a contained path even before the
    # directory exists on disk, whereas the not-yet-created directory itself does
    # not match. The head manifest is the canonical representative write target.
    probe = stream_dir / HEAD_FILENAME
    proc = runner(["git", "-C", str(enclosing), "check-ignore", "-q", "--", str(probe)])
    if proc.returncode != 0:
        raise EventRootNotIgnored(
            f"spool root {spool_root} is inside repo {enclosing} but is not git-ignored; "
            "CE-event runtime state must live under an ignored path (e.g. .ce/ce-events/spool/)"
        )


# ---------------------------------------------------------------------------
# Transport seam — default local filesystem/"git" semantics, no network
# ---------------------------------------------------------------------------


class Transport(Protocol):
    """Injectable append/read seam. The default is local files synced by ordinary
    git (no CE network call). Network transports are explicitly deferred."""

    def head(self, stream_dir: Path) -> dict[str, Any] | None: ...
    def write_block(self, stream_dir: Path, seq: int, block_id: str, block: dict[str, Any]) -> Path: ...
    def write_head(self, stream_dir: Path, head: dict[str, Any]) -> Path: ...
    def read_blocks(self, stream_dir: Path) -> list[tuple[Path, dict[str, Any]]]: ...


def _read_head(head_path: Path) -> dict[str, Any] | None:
    if not head_path.is_file():
        return None
    try:
        data = json.loads(head_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ChainLinkError(f"head manifest at {head_path} is unreadable: {exc}") from exc
    if not isinstance(data, dict) or "sequence" not in data or "head_content_hash" not in data:
        raise ChainLinkError(f"head manifest at {head_path} is malformed; cannot safely link a new block")
    return data


class FilesystemTransport:
    """Default transport: append-only local writes (atomic temp + rename)."""

    name = "local"

    def head(self, stream_dir: Path) -> dict[str, Any] | None:
        return _read_head(stream_dir / HEAD_FILENAME)

    def write_block(self, stream_dir: Path, seq: int, block_id: str, block: dict[str, Any]) -> Path:
        path = stream_dir / f"{seq:06d}-{block_id}.json"
        if path.exists():
            raise CeEventAppendError(f"CE-event block already exists, refusing to overwrite: {path}")
        _atomic_write(path, _json_bytes(block))
        return path

    def write_head(self, stream_dir: Path, head: dict[str, Any]) -> Path:
        path = stream_dir / HEAD_FILENAME
        _atomic_write(path, _json_bytes(head))
        return path

    def read_blocks(self, stream_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
        out: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(stream_dir.glob("*.json")):
            if path.name == HEAD_FILENAME:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append((path, data))
        return out


# ---------------------------------------------------------------------------
# Block construction + shared floor checks (reuse the landed validator)
# ---------------------------------------------------------------------------


def _check_role_floor(emitting_role: str) -> None:
    role = block_check._normalize_token(emitting_role)
    if role in block_check.FORBIDDEN_ACTIVE_ROLES or role not in block_check.EMITTING_ROLES:
        raise RoleFloorRefused(
            f"emitting_role {emitting_role!r} must be a canonical non-ratifying role; "
            "agent_ratifier/source are reserved-inactive and may not emit CE-event blocks"
        )


def _check_mode(operating_mode: str) -> None:
    if block_check._normalize_token(operating_mode) not in block_check.OPERATING_MODES:
        raise ModeInvalid(
            f"operating_mode {operating_mode!r} must be one of "
            f"{sorted(block_check.OPERATING_MODES)} (context only; no activation)"
        )


def _check_write_freeze(event: Any) -> None:
    if block_check._subtree_contains_hermes_event_write(event):
        raise WriteFreezeRefused(
            "CE-event runtime must not target .hermes/ce-events as active v2 state; "
            "the canonical home is the ignored .ce/ce-events/ zone"
        )


def _check_signature_value(signature_value: str) -> None:
    if block_check._normalize_token(signature_value) not in {"reserved_inactive"}:
        raise SignatureReserved(
            f"signature value {signature_value!r} must stay reserved-inactive in G2.003.x; "
            "cryptographic signing and key custody are deferred"
        )


def _signature(key_id: str) -> dict[str, str]:
    return {"scheme": SIGNATURE_SCHEME, "key_id": key_id, "value": SIGNATURE_VALUE}


def _build_block(
    *,
    block_id: str,
    sequence: int,
    parent_hash: str | None,
    emitting_role: str,
    operating_mode: str,
    recorded_at: str,
    event: dict[str, Any],
    key_id: str,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "block_id": block_id,
        "sequence": sequence,
        "parent_hash": parent_hash,
        "emitting_role": emitting_role,
        "operating_mode": operating_mode,
        "recorded_at": recorded_at,
        "event": event,
    }
    # content_hash excludes content_hash + signature (G2.003.0 canonical rule).
    block["content_hash"] = block_check._canonical_hash(block)
    block["signature"] = _signature(key_id)
    return block


def _self_validate_block(block: dict[str, Any]) -> None:
    errors = validate_with_schema(
        {"ce_event_block": block},
        SCHEMA_PATH,
        "<ce-event-runtime>",
        code=block_check.CODE_SCHEMA,
        contract=PROSE_CONTRACT,
    )
    if errors:
        raise CeEventAppendError(
            "produced CE-event block fails the landed ce_event_block schema: "
            + "; ".join(err.format() for err in errors)
        )


# ---------------------------------------------------------------------------
# ce event sign
# ---------------------------------------------------------------------------


def sign(*, block: dict[str, Any], key_id: str | None = None, signature_value: str = SIGNATURE_VALUE) -> dict[str, Any]:
    """Return a copy of ``block`` with a shape-only signature + canonical content
    hash. No cryptography: the value stays ``reserved-inactive`` or the call is
    refused. An incoming non-reserved signature value is also refused."""
    if not isinstance(block, dict):
        raise CeEventAppendError("sign requires a CE-event block mapping")
    _check_signature_value(signature_value)
    existing = block.get("signature")
    if isinstance(existing, dict) and "value" in existing:
        _check_signature_value(str(existing.get("value")))
    resolved_key = key_id or (existing.get("key_id") if isinstance(existing, dict) else None) or DEFAULT_KEY_ID

    material = {k: v for k, v in block.items() if k not in {"content_hash", "signature"}}
    signed = dict(material)
    signed["content_hash"] = block_check._canonical_hash(signed)
    signed["signature"] = _signature(str(resolved_key))
    return signed


# ---------------------------------------------------------------------------
# ce event append
# ---------------------------------------------------------------------------


def append(
    *,
    stream: str,
    event_root: Path | str,
    block_id: str,
    emitting_role: str,
    operating_mode: str,
    event: dict[str, Any],
    recorded_at: str,
    repo_root: Path | str | None = None,
    transport: Transport | None = None,
    git_runner: GitRunner | None = None,
    key_id: str = DEFAULT_KEY_ID,
    signature_value: str = SIGNATURE_VALUE,
) -> AppendResult:
    """Append one shape-only-signed CE-event block to a local chain.

    Computes ``parent_hash`` from the current head, assigns the monotonic
    ``sequence`` (``0`` for genesis), computes ``content_hash`` with the exact
    G2.003.0 canonical rule, self-validates against the landed block schema, then
    atomically writes the block + head manifest under the ignored spool. Every
    refusal raises **before any write**, leaving the spool byte-identical.
    """
    if not isinstance(stream, str) or not _STREAM_RE.match(stream):
        raise CeEventAppendError(f"stream {stream!r} must match {_STREAM_RE.pattern}")
    if not isinstance(event, dict):
        raise CeEventAppendError("event must be a mapping with kind/subject/summary")

    transport = transport or FilesystemTransport()
    runner = git_runner or _default_git_runner

    # 1. Floor checks — all before any read/build/write.
    _check_role_floor(emitting_role)
    _check_mode(operating_mode)
    _check_signature_value(signature_value)
    _check_write_freeze(event)

    spool_root = Path(event_root) / "spool"
    stream_dir = spool_root / stream

    # 2. The spool root must be git-ignored when inside a repository.
    _require_ignored_spool_root(spool_root, stream_dir, Path(repo_root) if repo_root else None, runner)

    # 3. Resolve sequence + parent_hash from the head (raises on a corrupt head).
    head = transport.head(stream_dir)
    if head is None:
        sequence = 0
        parent_hash: str | None = None
    else:
        sequence = int(head["sequence"]) + 1
        parent_hash = str(head["head_content_hash"])

    # 4. Build the canonical block + self-validate against the landed schema.
    block = _build_block(
        block_id=block_id,
        sequence=sequence,
        parent_hash=parent_hash,
        emitting_role=emitting_role,
        operating_mode=operating_mode,
        recorded_at=recorded_at,
        event=event,
        key_id=key_id,
    )
    _self_validate_block(block)

    # --- Side effects begin here (block file, then head manifest) ---
    block_path = transport.write_block(stream_dir, sequence, block_id, block)
    head_payload = {
        "kind": HEAD_KIND,
        "schema_version": SCHEMA_VERSION,
        "stream": stream,
        "sequence": sequence,
        "block_count": sequence + 1,
        "head_block_id": block_id,
        "head_content_hash": block["content_hash"],
        "last_block_ref": _safe_relpath(block_path, event_root),
    }
    head_path = transport.write_head(stream_dir, head_payload)

    return AppendResult(
        block_path=block_path,
        head_path=head_path,
        block=block,
        stream=stream,
        sequence=sequence,
        content_hash=block["content_hash"],
        parent_hash=parent_hash,
    )


def _safe_relpath(path: Path, root: Path | str) -> str:
    try:
        return Path(path).relative_to(Path(root)).as_posix()
    except ValueError:
        return Path(path).as_posix()


# ---------------------------------------------------------------------------
# Shared read path for verify / replay / index
# ---------------------------------------------------------------------------


def _load_chain(stream: str, event_root: Path | str, transport: Transport) -> tuple[Path, list[dict[str, Any]]]:
    stream_dir = Path(event_root) / "spool" / stream
    if not stream_dir.is_dir():
        raise CeEventRuntimeError(f"no CE-event stream at {stream_dir}")
    pairs = transport.read_blocks(stream_dir)
    blocks = [data for _path, data in pairs]
    return stream_dir, blocks


# ---------------------------------------------------------------------------
# ce event verify — reuses the landed validator for shape + chain invariants
# ---------------------------------------------------------------------------


def verify(*, stream: str, event_root: Path | str, transport: Transport | None = None) -> VerifyResult:
    """Validate an on-disk chain: shape (delegated to ``ce_event_block``), content
    addressing, hash-chain linkage, role floor, operating-mode enum, signature
    shape, write-freeze, and head-manifest agreement. Deterministic; read-only."""
    transport = transport or FilesystemTransport()
    stream_dir = Path(event_root) / "spool" / stream
    errors: list[str] = []
    if not stream_dir.is_dir():
        return VerifyResult(
            ok=False, stream=stream, summary={"block_count": 0},
            errors=(f"no CE-event stream at {stream_dir}",),
        )

    pairs = transport.read_blocks(stream_dir)
    blocks = [data for _p, data in pairs]

    # Shape: reuse the landed block schema for every block.
    for idx, block in enumerate(blocks):
        for err in validate_with_schema(
            {"ce_event_block": block}, SCHEMA_PATH, f"{stream}#{idx}",
            code=block_check.CODE_SCHEMA, contract=PROSE_CONTRACT,
        ):
            errors.append(err.format())

    # Content addressing, chain linkage, role floor, mode, signature, write-freeze:
    # reuse the validator's own per-chain block predicates verbatim.
    for err in block_check._validate_blocks(blocks, stream_dir, root_key="ce_event_chain"):
        errors.append(err.format())

    # Head-manifest agreement (runtime-specific; the block validator is unaware).
    head_errors, head = _verify_head(stream_dir, blocks)
    errors.extend(head_errors)

    summary = {
        "stream": stream,
        "block_count": len(blocks),
        "head_content_hash": head.get("head_content_hash") if head else None,
        "head_sequence": head.get("sequence") if head else None,
        "errors": errors,
    }
    return VerifyResult(ok=not errors, stream=stream, summary=summary, errors=tuple(errors))


def _verify_head(stream_dir: Path, blocks: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    head_path = stream_dir / HEAD_FILENAME
    head: dict[str, Any] | None = None
    if head_path.is_file():
        try:
            head = json.loads(head_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"head manifest unreadable: {exc}")
            return errors, None
    if not blocks:
        return errors, head
    if not isinstance(head, dict):
        errors.append(f"missing or invalid head manifest at {head_path}")
        return errors, None
    last = blocks[-1]
    if head.get("head_content_hash") != last.get("content_hash"):
        errors.append(
            f"head_content_hash {head.get('head_content_hash')} does not match last block "
            f"content_hash {last.get('content_hash')}"
        )
    if head.get("sequence") != last.get("sequence"):
        errors.append(
            f"head sequence {head.get('sequence')} does not match last block sequence "
            f"{last.get('sequence')}"
        )
    return errors, head


# ---------------------------------------------------------------------------
# ce event replay — deterministic ordered read-only projection
# ---------------------------------------------------------------------------


def replay(*, stream: str, event_root: Path | str, transport: Transport | None = None) -> ReplayResult:
    transport = transport or FilesystemTransport()
    _stream_dir, blocks = _load_chain(stream, event_root, transport)
    ordered = sorted(blocks, key=lambda b: int(b.get("sequence", 0)))
    projection = {
        "kind": REPLAY_KIND,
        "schema_version": SCHEMA_VERSION,
        "stream": stream,
        "block_count": len(ordered),
        "blocks": [
            {
                "sequence": b.get("sequence"),
                "block_id": b.get("block_id"),
                "parent_hash": b.get("parent_hash"),
                "content_hash": b.get("content_hash"),
                "emitting_role": b.get("emitting_role"),
                "operating_mode": b.get("operating_mode"),
                "event_kind": (b.get("event") or {}).get("kind"),
                "subject": (b.get("event") or {}).get("subject"),
            }
            for b in ordered
        ],
    }
    return ReplayResult(
        stream=stream,
        content_hash=_content_hash_of(projection),
        blocks=tuple(ordered),
        projection=projection,
    )


# ---------------------------------------------------------------------------
# ce event index — deterministic content-hashed read-only index
# ---------------------------------------------------------------------------


def index(*, stream: str, event_root: Path | str, transport: Transport | None = None) -> IndexResult:
    transport = transport or FilesystemTransport()
    _stream_dir, blocks = _load_chain(stream, event_root, transport)
    ordered = sorted(blocks, key=lambda b: int(b.get("sequence", 0)))

    kind_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    mode_counts: dict[str, int] = {}
    for b in ordered:
        kind = str((b.get("event") or {}).get("kind"))
        role = str(b.get("emitting_role"))
        mode = str(b.get("operating_mode"))
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        role_counts[role] = role_counts.get(role, 0) + 1
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    index_doc = {
        "kind": INDEX_KIND,
        "schema_version": SCHEMA_VERSION,
        "stream": stream,
        "block_count": len(ordered),
        "genesis_content_hash": ordered[0].get("content_hash") if ordered else None,
        "head_content_hash": ordered[-1].get("content_hash") if ordered else None,
        "head_sequence": ordered[-1].get("sequence") if ordered else None,
        "event_kind_counts": dict(sorted(kind_counts.items())),
        "emitting_role_counts": dict(sorted(role_counts.items())),
        "operating_mode_counts": dict(sorted(mode_counts.items())),
    }
    return IndexResult(stream=stream, content_hash=_content_hash_of(index_doc), index=index_doc)
