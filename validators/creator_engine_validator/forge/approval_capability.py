"""Approval capability marker signing and verification.

The integrator treats GitHub's raw ``reviewDecision == APPROVED`` as necessary
but not sufficient. A controller-only capability must also be present and valid.
This module is pure/offline: callers inject the secret supplier and clock.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

MARKER_PREFIX = "ce-approval-capability:"
CAPABILITY_VERSION = "v1"

SecretSupplier = Callable[[], bytes | str | None]
Clock = Callable[[], float]

_MARKER_RE = re.compile(
    rf"^\s*{re.escape(MARKER_PREFIX)}\s*({CAPABILITY_VERSION}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ApprovalCapabilityClaims:
    """Value-only capability claims bound to one PR head and approval policy."""

    repo: str
    pr_number: int
    head_sha: str
    approved_by: str
    issued_at: int
    expires_at: int
    policy_sha: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "approved_by": self.approved_by,
            "expires_at": self.expires_at,
            "head_sha": self.head_sha.lower(),
            "issued_at": self.issued_at,
            "policy_sha": self.policy_sha,
            "pr_number": self.pr_number,
            "repo": self.repo,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ApprovalCapabilityClaims | None":
        try:
            repo = payload["repo"]
            pr_number = payload["pr_number"]
            head_sha = payload["head_sha"]
            approved_by = payload["approved_by"]
            issued_at = payload["issued_at"]
            expires_at = payload["expires_at"]
            policy_sha = payload["policy_sha"]
        except KeyError:
            return None
        if not isinstance(repo, str) or not repo:
            return None
        if not isinstance(pr_number, int) or pr_number < 1:
            return None
        if not isinstance(head_sha, str) or not head_sha:
            return None
        if not isinstance(approved_by, str) or not approved_by:
            return None
        if not isinstance(issued_at, int) or not isinstance(expires_at, int):
            return None
        if expires_at <= issued_at:
            return None
        if not isinstance(policy_sha, str) or not policy_sha:
            return None
        return cls(
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha.lower(),
            approved_by=approved_by,
            issued_at=issued_at,
            expires_at=expires_at,
            policy_sha=policy_sha,
        )


@dataclass(frozen=True)
class ApprovalCapabilityVerification:
    """Secret-free verification outcome for logging/tests/audit."""

    valid: bool
    reason: str
    claims: ApprovalCapabilityClaims | None = None

    def to_audit_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {"valid": self.valid, "reason": self.reason}
        if self.claims is not None:
            record.update(self.claims.to_payload())
        return record


class ApprovalCapabilityVerifier:
    """Verify controller-minted approval capability markers."""

    def __init__(
        self,
        secret_supplier: SecretSupplier,
        *,
        now: Clock | None = None,
        policy_sha: str | None = None,
    ) -> None:
        self._secret_supplier = secret_supplier
        self._now = now or time.time
        self._policy_sha = policy_sha

    def verify(
        self,
        marker: str | None,
        *,
        repo: str,
        pr_number: int,
        head_sha: str,
        approved_by_candidates: Iterable[str] = (),
    ) -> ApprovalCapabilityVerification:
        if marker is None:
            return ApprovalCapabilityVerification(False, "missing")
        parsed = _parse_marker(marker)
        if parsed is None:
            return ApprovalCapabilityVerification(False, "malformed")
        payload_b64, signature = parsed
        secret = _secret_bytes(self._secret_supplier)
        if not secret:
            return ApprovalCapabilityVerification(False, "secret_unavailable")
        expected_signature = _signature(payload_b64, secret)
        if not hmac.compare_digest(signature, expected_signature):
            return ApprovalCapabilityVerification(False, "signature_mismatch")
        payload = _decode_payload(payload_b64)
        if payload is None:
            return ApprovalCapabilityVerification(False, "malformed")
        claims = ApprovalCapabilityClaims.from_payload(payload)
        if claims is None:
            return ApprovalCapabilityVerification(False, "malformed")
        if claims.repo != repo:
            return ApprovalCapabilityVerification(False, "repo_mismatch", claims)
        if claims.pr_number != pr_number:
            return ApprovalCapabilityVerification(False, "pr_mismatch", claims)
        if claims.head_sha.lower() != head_sha.lower():
            return ApprovalCapabilityVerification(False, "head_mismatch", claims)
        candidates = {candidate for candidate in approved_by_candidates if candidate}
        if candidates and claims.approved_by not in candidates:
            return ApprovalCapabilityVerification(False, "approver_mismatch", claims)
        if self._policy_sha is not None and claims.policy_sha != self._policy_sha:
            return ApprovalCapabilityVerification(False, "policy_mismatch", claims)
        now = int(self._now())
        if now < claims.issued_at:
            return ApprovalCapabilityVerification(False, "not_yet_valid", claims)
        if now >= claims.expires_at:
            return ApprovalCapabilityVerification(False, "expired", claims)
        return ApprovalCapabilityVerification(True, "valid", claims)


def issue_approval_capability(claims: ApprovalCapabilityClaims, secret: bytes | str) -> str:
    """Return a single PR-body/comment marker line for ``claims``."""

    secret_bytes = _coerce_secret(secret)
    payload_b64 = _b64url(
        json.dumps(claims.to_payload(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature = _signature(payload_b64, secret_bytes)
    return f"{MARKER_PREFIX} {CAPABILITY_VERSION}.{payload_b64}.{signature}"


def extract_approval_capability_marker(text: str | None) -> str | None:
    """Return the single marker in ``text``; fail closed on none or many."""

    if not text:
        return None
    matches = _MARKER_RE.findall(text)
    if len(matches) != 1:
        return None
    return f"{MARKER_PREFIX} {matches[0]}"


def _parse_marker(marker: str) -> tuple[str, str] | None:
    normalized = extract_approval_capability_marker(marker) or marker.strip()
    if not normalized.startswith(MARKER_PREFIX):
        return None
    token = normalized.removeprefix(MARKER_PREFIX).strip()
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != CAPABILITY_VERSION or not parts[1] or not parts[2]:
        return None
    return parts[1], parts[2]


def _decode_payload(payload_b64: str) -> dict[str, Any] | None:
    try:
        raw = base64.urlsafe_b64decode(_with_padding(payload_b64))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _signature(payload_b64: str, secret: bytes) -> str:
    return _b64url(hmac.new(secret, f"{CAPABILITY_VERSION}.{payload_b64}".encode("ascii"), hashlib.sha256).digest())


def _secret_bytes(supplier: SecretSupplier) -> bytes | None:
    try:
        value = supplier()
    except Exception:
        return None
    if value is None:
        return None
    return _coerce_secret(value)


def _coerce_secret(value: bytes | str) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _with_padding(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")
