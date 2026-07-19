"""Dispatch-receipt build/validate/write library (ce-ops#615, slice 1).

Provides a transport-agnostic receipt substrate for CE fleet dispatch.
Watchers call :func:`verify_receipt` to assert seat activation instead of
inferring it from scrollback; each failure carries a typed ``gap_class`` so
callers can distinguish:

  * ``dispatch-without-transport`` — brief pointer issued, arrival in-seat
    not confirmed (``transport_verified_at`` absent).
  * ``receipt-without-activation``  — receipt written but seat may not be
    processing: ``activation.separate_enter`` is ``False`` (the combined
    send-keys form silently drops Enter on many tmux builds) OR
    ``post_check`` is absent (no working-state probe performed).

This module is classified **shared** (not v1 or v3-specific) so both the
v1 ``ce`` kernel and a future v3 orchestrator surface can consume it without
creating a new cross-boundary edge (see ``_versions.py`` ratchet).

Boundary: no credential, token, secret, or raw account value ever enters a
receipt. Path refs, SHA256 digests, timestamps, and observable UI strings
(model_effort_line) are the only data categories this module handles.

Prose contract: ``docs/operations/DISPATCH_RECEIPT_PROTOCOL.md`` (to be
authored in slice 2 alongside transport integration).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schema import validate_with_schema

# ---------------------------------------------------------------------------
# Schema / storage constants
# ---------------------------------------------------------------------------

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "dispatch-receipt.v1.schema.yaml"
)
PROSE_CONTRACT = "docs/operations/DISPATCH_RECEIPT_PROTOCOL.md"

KIND = "ce.dispatch-receipt"
SCHEMA_VERSION = "1"

#: Default sub-directory under the CE state root for dispatch receipts.
RECEIPTS_SUBDIR = "dispatch-receipts"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# ---------------------------------------------------------------------------
# Gap-class constants (stable strings; callers match on these)
# ---------------------------------------------------------------------------

GAP_DISPATCH_WITHOUT_TRANSPORT = "dispatch-without-transport"
"""Brief pointer issued but in-seat arrival not confirmed."""

GAP_RECEIPT_WITHOUT_ACTIVATION = "receipt-without-activation"
"""Receipt written but seat activation is not asserted."""


# ---------------------------------------------------------------------------
# Error hierarchy (all refusals raise before any write)
# ---------------------------------------------------------------------------


class DispatchReceiptError(ValueError):
    """Base class for dispatch-receipt errors. Carries a ``code``."""

    code = "CE615-RECEIPT-ERROR"


class ReceiptBuildError(DispatchReceiptError):
    """Raised when a receipt cannot be built due to invalid inputs."""

    code = "CE615-BUILD-ERROR"


class ReceiptSchemaError(DispatchReceiptError):
    """Raised when a receipt fails schema validation."""

    code = "CE615-SCHEMA-ERROR"


class ReceiptWriteError(DispatchReceiptError):
    """Raised when the receipt cannot be written to disk."""

    code = "CE615-WRITE-ERROR"


# ---------------------------------------------------------------------------
# Typed failure (returned by verify_receipt; never raises)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReceiptFailure:
    """One typed activation-gap failure found by :func:`verify_receipt`."""

    gap_class: str
    """One of the ``GAP_*`` module-level constants."""

    field: str
    """The receipt field (or path within the receipt) that is absent or invalid."""

    message: str
    """Human-readable description of the failure."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    """Return the lowercase hex SHA256 digest of *path*."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Receipt builder
# ---------------------------------------------------------------------------


def build_receipt(
    *,
    brief_path: str,
    brief_sha256: str,
    transport_kind: str,
    transport_target: str,
    activation_method: str,
    activation_issued_at: str | None = None,
    separate_enter: bool,
    model_effort_line: str,
    dispatcher: str,
    work_unit: str,
    # Optional fields
    claim_path: str | None = None,
    claim_sha256: str | None = None,
    transport_verified_at: str | None = None,
    post_check_kind: str | None = None,
    post_check_verified_at: str | None = None,
    post_check_result: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """Build a validated dispatch-receipt dict.

    All required fields must be supplied. Optional fields (claim, transport
    verification, post-check) may be omitted and added later via
    :func:`patch_receipt`.

    :raises ReceiptBuildError: if required fields are missing or invalid.
    :raises ReceiptSchemaError: if the assembled record fails schema validation.
    :returns: A validated receipt dict ready for :func:`write_receipt`.
    """
    if not brief_path:
        raise ReceiptBuildError("brief_path is required")
    if not _HEX64_RE.match(brief_sha256 or ""):
        raise ReceiptBuildError("brief_sha256 must be a 64-character lowercase hex string")
    if not model_effort_line:
        raise ReceiptBuildError("model_effort_line is required (per 2026-07-19 Operator floor ruling)")
    if not dispatcher:
        raise ReceiptBuildError("dispatcher is required")
    if not work_unit:
        raise ReceiptBuildError("work_unit is required")

    # Validate optional claim pair consistency
    if (claim_path is None) != (claim_sha256 is None):
        raise ReceiptBuildError(
            "claim_path and claim_sha256 must both be supplied or both absent"
        )
    if claim_sha256 is not None and not _HEX64_RE.match(claim_sha256):
        raise ReceiptBuildError("claim_sha256 must be a 64-character lowercase hex string")

    # Validate optional post_check triple consistency
    post_check_fields = [post_check_kind, post_check_verified_at, post_check_result]
    if any(f is not None for f in post_check_fields) and any(
        f is None for f in post_check_fields
    ):
        raise ReceiptBuildError(
            "post_check_kind, post_check_verified_at, and post_check_result "
            "must all be supplied or all absent"
        )

    now = emitted_at or _utc_now()
    issued = activation_issued_at or now

    receipt: dict[str, Any] = {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "emitted_at": now,
        "brief_path": brief_path,
        "brief_sha256": brief_sha256,
        "transport": {
            "kind": transport_kind,
            "target": transport_target,
        },
        "activation": {
            "method": activation_method,
            "issued_at": issued,
            "separate_enter": separate_enter,
        },
        "model_effort_line": model_effort_line,
        "dispatcher": dispatcher,
        "work_unit": work_unit,
    }

    if claim_path is not None:
        receipt["claim_path"] = claim_path
        receipt["claim_sha256"] = claim_sha256

    if transport_verified_at is not None:
        receipt["transport_verified_at"] = transport_verified_at

    if post_check_kind is not None:
        receipt["post_check"] = {
            "kind": post_check_kind,
            "verified_at": post_check_verified_at,
            "result": post_check_result,
        }

    # Schema-validate before returning
    errors = validate_with_schema(
        receipt,
        SCHEMA_PATH,
        "<dispatch-receipt-builder>",
        code="CE615",
        contract=PROSE_CONTRACT,
    )
    if errors:
        messages = "; ".join(e.message for e in errors)
        raise ReceiptSchemaError(f"built receipt fails schema: {messages}")

    return receipt


def patch_receipt(
    receipt: dict[str, Any],
    *,
    transport_verified_at: str | None = None,
    post_check_kind: str | None = None,
    post_check_verified_at: str | None = None,
    post_check_result: str | None = None,
) -> dict[str, Any]:
    """Return a new receipt dict with additional post-dispatch fields filled in.

    This is the idiomatic pattern for a watcher: it receives the initial
    receipt (built at send time), then patches in ``transport_verified_at``
    and/or ``post_check`` once it has confirmed them.

    :returns: A new dict (the original is not mutated).
    :raises ReceiptBuildError: if post_check fields are partially supplied.
    :raises ReceiptSchemaError: if the patched record fails schema validation.
    """
    updated = dict(receipt)

    if transport_verified_at is not None:
        updated["transport_verified_at"] = transport_verified_at

    post_check_fields = [post_check_kind, post_check_verified_at, post_check_result]
    if any(f is not None for f in post_check_fields):
        if any(f is None for f in post_check_fields):
            raise ReceiptBuildError(
                "post_check_kind, post_check_verified_at, and post_check_result "
                "must all be supplied together"
            )
        updated["post_check"] = {
            "kind": post_check_kind,
            "verified_at": post_check_verified_at,
            "result": post_check_result,
        }

    errors = validate_with_schema(
        updated,
        SCHEMA_PATH,
        "<dispatch-receipt-patch>",
        code="CE615",
        contract=PROSE_CONTRACT,
    )
    if errors:
        messages = "; ".join(e.message for e in errors)
        raise ReceiptSchemaError(f"patched receipt fails schema: {messages}")

    return updated


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def receipt_filename(slug: str, ts: str | None = None) -> str:
    """Return the canonical receipt filename for a given slug and UTC stamp.

    The slug is typically derived from ``work_unit`` (e.g. ``ce-ops-615``).
    The timestamp is the receipt's ``emitted_at`` field, compacted to
    ``YYYYMMDDTHHMMSSZ``.
    """
    if ts is None:
        ts = _utc_now()
    compact_ts = ts.replace("-", "").replace(":", "")
    safe_slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    return f"{safe_slug}-{compact_ts}.json"


def write_receipt(
    receipt: dict[str, Any],
    *,
    state_root: str | Path = ".ce/state",
    slug: str | None = None,
    filename: str | None = None,
) -> Path:
    """Persist a receipt dict to ``.ce/state/dispatch-receipts/``.

    The write is append-safe: each call produces a new uniquely-named file.
    The directory is created if absent. The state root and receipts subdir
    must both be gitignored by the repository's ``.gitignore`` (not enforced
    here; this is a local-only runtime artifact).

    :param receipt: Validated receipt dict from :func:`build_receipt` or
        :func:`patch_receipt`.
    :param state_root: CE state root (default: ``.ce/state``).
    :param slug: Optional slug used to derive the filename. Defaults to
        ``receipt["work_unit"]``.
    :param filename: Override the entire filename (including extension). When
        supplied *slug* is ignored.
    :raises ReceiptWriteError: on any I/O failure.
    :returns: The absolute :class:`~pathlib.Path` the receipt was written to.
    """
    receipts_dir = Path(state_root) / RECEIPTS_SUBDIR
    try:
        receipts_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReceiptWriteError(
            f"cannot create receipts directory {receipts_dir}: {exc}"
        ) from exc

    if filename is None:
        effective_slug = slug or receipt.get("work_unit", "unknown")
        emitted_at = receipt.get("emitted_at", _utc_now())
        filename = receipt_filename(effective_slug, emitted_at)

    dest = receipts_dir / filename
    try:
        dest.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ReceiptWriteError(f"cannot write receipt to {dest}: {exc}") from exc

    return dest.resolve()


def read_receipt(path: str | Path) -> dict[str, Any]:
    """Read and schema-validate a receipt from disk.

    :raises FileNotFoundError: if the file does not exist.
    :raises ReceiptSchemaError: if the file fails schema validation.
    :returns: The receipt dict.
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    errors = validate_with_schema(
        raw,
        SCHEMA_PATH,
        str(p),
        code="CE615",
        contract=PROSE_CONTRACT,
    )
    if errors:
        messages = "; ".join(e.message for e in errors)
        raise ReceiptSchemaError(
            f"receipt at {p} fails schema validation: {messages}"
        )
    return raw


# ---------------------------------------------------------------------------
# Watcher verification
# ---------------------------------------------------------------------------


def verify_receipt(receipt: dict[str, Any]) -> list[ReceiptFailure]:
    """Return typed activation-gap failures for a receipt dict.

    A watcher calls this after receiving (or reading from disk) a receipt to
    assert activation rather than infer it from scrollback.

    The function is purely computational — no I/O, no network, no side
    effects. It can be called on any dict, not only one produced by
    :func:`build_receipt`.

    Gap classes detected:

    ``dispatch-without-transport``
        ``transport_verified_at`` is absent. The brief pointer was sent but
        in-seat arrival is not confirmed.

    ``receipt-without-activation``
        One or both of:
        - ``activation.separate_enter`` is ``False`` (the combined
          ``send-keys`` form silently drops Enter on many tmux builds).
        - ``post_check`` is absent (no working-state probe was performed).

    :returns: A list of :class:`ReceiptFailure` objects (empty = all clear).
    """
    failures: list[ReceiptFailure] = []

    # Gap 1: dispatch-without-transport
    if not receipt.get("transport_verified_at"):
        failures.append(
            ReceiptFailure(
                gap_class=GAP_DISPATCH_WITHOUT_TRANSPORT,
                field="transport_verified_at",
                message=(
                    "transport_verified_at is absent: brief pointer was issued "
                    "but in-seat arrival has not been confirmed"
                ),
            )
        )

    # Gap 2a: receipt-without-activation — separate_enter is False
    activation = receipt.get("activation") or {}
    if activation.get("separate_enter") is False:
        failures.append(
            ReceiptFailure(
                gap_class=GAP_RECEIPT_WITHOUT_ACTIVATION,
                field="activation.separate_enter",
                message=(
                    "activation.separate_enter is False: the combined send-keys "
                    "form was used, which silently drops Enter on many tmux "
                    "builds — seat may not have received the activation signal"
                ),
            )
        )

    # Gap 2b: receipt-without-activation — post_check absent
    if not receipt.get("post_check"):
        failures.append(
            ReceiptFailure(
                gap_class=GAP_RECEIPT_WITHOUT_ACTIVATION,
                field="post_check",
                message=(
                    "post_check is absent: no working-state probe was performed "
                    "after dispatch — activation cannot be asserted"
                ),
            )
        )

    return failures
