"""Single-use, exact-payload review submission receipts.

The authority intentionally has no ambient secret fallback.  A host broker must
provide a purpose-separated key supplier (normally a SecretIdentityBackend
materialization seam); unavailable key/state/clock means no review write.
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .reviewer_terminal import ReviewerTerminal, ReviewerTerminalRefused, require_reviewed_terminal

if TYPE_CHECKING:
    from ..secret_identity import SecretIdentityBackend, SecretRequest


REVIEW_SUBMISSION_RECEIPT_SECRET_PURPOSE = "review_submission_receipt"
MaterializedSecretReader = Callable[[str], bytes | str | None]


class ReviewReceiptRefused(ValueError):
    """Receipt issuance or consumption failed closed."""


@dataclass(frozen=True)
class ReviewSubmissionReceipt:
    nonce: str
    terminal_digest: str
    body_digest: str
    repository: str
    pr_number: int
    head_sha: str
    reviewer: str
    event: str
    issued_at: int
    expires_at: int
    mac: str

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class ReviewSubmissionReceiptAuthority:
    """Host-only receipt issuer/consumer with durable consume-before-mint state."""

    def __init__(self, *, state_root: Path | str, key_supplier: Callable[[], bytes | None],
                 now: Callable[[], float] = time.time) -> None:
        self.state_root = Path(state_root)
        self.key_supplier = key_supplier
        self.now = now

    def issue(self, terminal: ReviewerTerminal | Mapping[str, Any] | str, *, ttl_seconds: int) -> ReviewSubmissionReceipt:
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not 0 < ttl_seconds <= 300:
            raise ReviewReceiptRefused("receipt TTL must be positive and at most 300 seconds")
        try:
            checked = require_reviewed_terminal(terminal)
        except ReviewerTerminalRefused as exc:
            raise ReviewReceiptRefused("review terminal is not receipt-eligible") from exc
        now = self._clock()
        key = self._key()
        record = checked.record
        unsigned = {
            "nonce": secrets.token_urlsafe(24), "terminal_digest": checked.digest,
            "body_digest": hashlib.sha256(checked.canonical_body.encode()).hexdigest(),
            "repository": record["repository"], "pr_number": record["pr_number"],
            "head_sha": record["head_sha"], "reviewer": record["reviewer"],
            "event": record["verdict"], "issued_at": now, "expires_at": now + ttl_seconds,
        }
        return ReviewSubmissionReceipt(**unsigned, mac=_mac(key, unsigned))

    def consume(self, receipt: ReviewSubmissionReceipt | Mapping[str, Any], *, terminal: ReviewerTerminal | Mapping[str, Any] | str,
                repository: str, pr_number: int, head_sha: str, event: str) -> None:
        rec = _receipt(receipt)
        try:
            checked = require_reviewed_terminal(terminal, repository=repository, pr_number=pr_number,
                                                head_sha=head_sha, event=event)
        except ReviewerTerminalRefused as exc:
            raise ReviewReceiptRefused("review terminal is not receipt-eligible") from exc
        now = self._clock()
        if rec.expires_at < now or rec.issued_at > now:
            raise ReviewReceiptRefused("receipt is expired or clock is invalid")
        if rec.expires_at - rec.issued_at > 300:
            raise ReviewReceiptRefused("receipt TTL exceeds maximum")
        expected = {"terminal_digest": checked.digest,
                    "body_digest": hashlib.sha256(checked.canonical_body.encode()).hexdigest(),
                    "repository": repository, "pr_number": pr_number, "head_sha": head_sha,
                    "reviewer": checked.record["reviewer"], "event": event}
        for key, value in expected.items():
            if getattr(rec, key) != value:
                raise ReviewReceiptRefused(f"receipt {key} binding mismatch")
        unsigned = {k: v for k, v in rec.as_dict().items() if k != "mac"}
        if not hmac.compare_digest(rec.mac, _mac(self._key(), unsigned)):
            raise ReviewReceiptRefused("receipt authentication failed")
        self._consume_nonce(rec)

    def _key(self) -> bytes:
        try:
            key = self.key_supplier()
        except Exception as exc:
            raise ReviewReceiptRefused("receipt key backend unavailable") from exc
        if not isinstance(key, bytes) or len(key) < 32:
            raise ReviewReceiptRefused("receipt key backend unavailable")
        return key

    def _clock(self) -> int:
        try:
            now = self.now()
        except Exception as exc:
            raise ReviewReceiptRefused("receipt clock unavailable") from exc
        if not isinstance(now, (int, float)) or now <= 0:
            raise ReviewReceiptRefused("receipt clock unavailable")
        return int(now)

    def _consume_nonce(self, receipt: ReviewSubmissionReceipt) -> None:
        root = self.state_root
        try:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if (root.stat().st_mode & 0o777) != 0o700:
                raise ReviewReceiptRefused("receipt state root is not mode 0700")
            lock_path = root / ".receipt.lock"
            with lock_path.open("a+", encoding="utf-8") as lock:
                os.chmod(lock_path, 0o600)
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                marker = root / f"{receipt.nonce}.consumed"
                # O_EXCL is the durable replay decision and is deliberately made
                # before a caller is allowed to mint a credential or transport.
                fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    os.write(fd, json.dumps({"nonce": receipt.nonce, "expires_at": receipt.expires_at}, sort_keys=True).encode())
                    os.fsync(fd)
                finally:
                    os.close(fd)
                directory_fd = os.open(root, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except FileExistsError as exc:
            raise ReviewReceiptRefused("receipt replay refused") from exc
        except ReviewReceiptRefused:
            raise
        except OSError as exc:
            raise ReviewReceiptRefused("receipt state unavailable") from exc


def receipt_key_supplier_from_secret_identity_backend(
    *,
    backend: "SecretIdentityBackend",
    request: "SecretRequest",
    target_ref: str,
    value_reader: MaterializedSecretReader,
    collect_audit: bool = True,
) -> Callable[[], bytes | str | None]:
    """Build the host-only, purpose-separated receipt-key supplier.

    This mirrors the existing SecretIdentityBackend/OpenBao materialization
    discipline without provisioning or reading any credential at import time.
    The caller must request the dedicated receipt purpose; using the shared
    approval-wall secret is refused before any backend operation.
    """
    if request.secret_ref.purpose != REVIEW_SUBMISSION_RECEIPT_SECRET_PURPOSE:
        raise ReviewReceiptRefused("review receipt key must use its dedicated secret purpose")

    def supply() -> bytes | str | None:
        grant = None
        materialized = None
        try:
            backend.validate_config()
            grant = backend.issue(request)
            materialized = backend.materialize(grant, target_ref)
            if collect_audit:
                backend.collect_audit(materialized)
            return value_reader(target_ref)
        except Exception as exc:
            raise ReviewReceiptRefused("receipt key backend unavailable") from exc
        finally:
            if materialized is not None or grant is not None:
                try:
                    revoked = backend.revoke(materialized or grant)
                    if collect_audit:
                        backend.collect_audit(revoked)
                except Exception as exc:
                    raise ReviewReceiptRefused("receipt key backend revoke failed") from exc

    return supply


def _mac(key: bytes, record: Mapping[str, Any]) -> str:
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def _receipt(value: ReviewSubmissionReceipt | Mapping[str, Any]) -> ReviewSubmissionReceipt:
    if isinstance(value, ReviewSubmissionReceipt):
        return value
    try:
        if not isinstance(value, Mapping) or set(value) != set(ReviewSubmissionReceipt.__dataclass_fields__):
            raise ValueError
        return ReviewSubmissionReceipt(**dict(value))
    except (TypeError, ValueError) as exc:
        raise ReviewReceiptRefused("receipt shape is invalid") from exc
