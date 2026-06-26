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
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..grading_policy import approval_policy_sha

if TYPE_CHECKING:
    from ..secret_identity import SecretIdentityBackend, SecretRequest

MARKER_PREFIX = "ce-approval-capability:"
CAPABILITY_VERSION = "v1"
DEFAULT_APPROVAL_CAPABILITY_SECRET_ENV = "CE_APPROVAL_CAPABILITY_SECRET"
DEFAULT_APPROVAL_WALL_STATE_RELATIVE = Path("approval-capability-wall") / "state.json"
APPROVAL_WALL_ARMED = "armed"
APPROVAL_WALL_DORMANT = "dormant"
APPROVAL_WALL_MISCONFIGURED = "misconfigured"

SecretSupplier = Callable[[], bytes | str | None]
MaterializedSecretReader = Callable[[str], bytes | str | None]
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


class ApprovalCapabilityIssuerError(Exception):
    """Approval capability issuance failed before signing."""


@dataclass(frozen=True)
class ApprovalCapabilityIssuer:
    """Pure/offline controller-side approval capability issuer.

    The issuer never discovers secrets itself. Callers must inject a supplier;
    unavailable, empty, or failing suppliers refuse issuance before marker
    creation.
    """

    secret_supplier: SecretSupplier = field(repr=False)
    now: Clock
    policy_sha: str
    ttl_seconds: int

    def mint(
        self,
        *,
        repo: str,
        pr_number: int,
        head_sha: str,
        approved_by: str,
    ) -> str:
        if self.ttl_seconds <= 0:
            raise ApprovalCapabilityIssuerError("ttl_seconds must be positive")
        secret = _issuer_secret_bytes(self.secret_supplier)
        issued_at = int(self.now())
        claims = ApprovalCapabilityClaims(
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            approved_by=approved_by,
            issued_at=issued_at,
            expires_at=issued_at + self.ttl_seconds,
            policy_sha=self.policy_sha,
        )
        if ApprovalCapabilityClaims.from_payload(claims.to_payload()) is None:
            raise ApprovalCapabilityIssuerError("invalid approval capability claims")
        return issue_approval_capability(claims, secret)


class ApprovalWallStateError(Exception):
    """Durable approval-wall state could not be loaded or written safely."""


@dataclass(frozen=True)
class ApprovalWallState:
    """Value-free durable state for enforce-when-armed wall posture."""

    armed: bool = False

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ApprovalWallState":
        armed = payload.get("armed", False)
        if not isinstance(armed, bool):
            raise ApprovalWallStateError("approval wall state field 'armed' must be boolean")
        return cls(armed=armed)

    def to_payload(self) -> dict[str, Any]:
        return {"armed": self.armed}


@dataclass(frozen=True)
class ApprovalWallConfig:
    """Secret-free approval wall runtime configuration."""

    secret_supplier: SecretSupplier | None = None
    state_path: Path | None = None
    now: Clock | None = None
    policy_sha: str | None = None


@dataclass(frozen=True)
class ApprovalWallRuntime:
    """Resolved approval wall posture plus verifier when enforcement is armed."""

    status: str
    verifier: "ApprovalCapabilityVerifier | None" = None
    reason: str = ""
    state_path: Path | None = None

    @property
    def armed(self) -> bool:
        return self.status == APPROVAL_WALL_ARMED

    @property
    def dormant(self) -> bool:
        return self.status == APPROVAL_WALL_DORMANT

    @property
    def misconfigured(self) -> bool:
        return self.status == APPROVAL_WALL_MISCONFIGURED


def approval_wall_state_path(root: str | Path = ".ce/state") -> Path:
    """Return the default durable wall-state path below a v3 local-state root."""

    return Path(root) / DEFAULT_APPROVAL_WALL_STATE_RELATIVE


def approval_wall_secret_supplier_from_env(
    *,
    env_name: str = DEFAULT_APPROVAL_CAPABILITY_SECRET_ENV,
    environ: Mapping[str, str] | None = None,
    backend_supplier: SecretSupplier | None = None,
) -> SecretSupplier:
    """Build the wall secret supplier.

    The env var is an offline bootstrap fallback. ``backend_supplier`` is the
    injectable SecretIdentityBackend/OpenBao bridge point: production may pass a
    materializer-backed callable, while tests keep it local and network-free.
    """

    env = environ

    def supply() -> bytes | str | None:
        source = env if env is not None else {}
        value = source.get(env_name) if env is not None else None
        if env is None:
            import os

            value = os.environ.get(env_name)
        if value:
            return value
        if backend_supplier is not None:
            return backend_supplier()
        return None

    return supply


def approval_wall_secret_supplier_from_secret_identity_backend(
    *,
    backend: "SecretIdentityBackend",
    request: "SecretRequest",
    target_ref: str,
    value_reader: MaterializedSecretReader,
    collect_audit: bool = True,
    revoke_after_read: bool = True,
) -> SecretSupplier:
    """Build a supplier from the SecretIdentityBackend/OpenBao seam.

    ``backend`` is expected to satisfy ``SecretIdentityBackend`` and ``request``
    to be a ``SecretRequest``. The backend only returns value-free grants; the
    injected ``value_reader`` is the sole path that reads the materialized value
    from ``target_ref``. This keeps OpenBao/live I/O outside this module and
    keeps durable grant/audit/state records secret-free.
    """

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
        finally:
            if revoke_after_read and (materialized is not None or grant is not None):
                revoked = backend.revoke(materialized or grant)
                if collect_audit:
                    backend.collect_audit(revoked)

    return supply


def resolve_approval_wall(config: ApprovalWallConfig) -> ApprovalWallRuntime:
    """Resolve dormant/armed/misconfigured posture without exposing secrets."""

    state = ApprovalWallState()
    if config.state_path is not None:
        try:
            state = load_approval_wall_state(config.state_path)
        except ApprovalWallStateError as exc:
            return ApprovalWallRuntime(
                APPROVAL_WALL_MISCONFIGURED,
                reason=f"state_unreadable: {exc}",
                state_path=config.state_path,
            )

    secret = _secret_bytes(config.secret_supplier) if config.secret_supplier is not None else None
    if state.armed and not secret:
        return ApprovalWallRuntime(
            APPROVAL_WALL_MISCONFIGURED,
            reason="armed_state_without_secret",
            state_path=config.state_path,
        )
    if secret:
        if config.state_path is not None and not state.armed:
            try:
                save_approval_wall_state(config.state_path, ApprovalWallState(armed=True))
            except ApprovalWallStateError as exc:
                return ApprovalWallRuntime(
                    APPROVAL_WALL_MISCONFIGURED,
                    reason=f"state_unwritable: {exc}",
                    state_path=config.state_path,
                )
        return ApprovalWallRuntime(
            APPROVAL_WALL_ARMED,
            verifier=ApprovalCapabilityVerifier(lambda: secret, now=config.now, policy_sha=config.policy_sha),
            reason="secret_configured",
            state_path=config.state_path,
        )
    return ApprovalWallRuntime(APPROVAL_WALL_DORMANT, reason="secret_not_configured", state_path=config.state_path)


def approval_wall_verifier_from_env(
    *,
    state_root: str | Path = ".ce/state",
    secret_env: str = DEFAULT_APPROVAL_CAPABILITY_SECRET_ENV,
    environ: Mapping[str, str] | None = None,
    backend_supplier: SecretSupplier | None = None,
    now: Clock | None = None,
    policy_sha: str | None = None,
) -> ApprovalWallRuntime:
    """Resolve the daemon wall using env bootstrap plus an injectable backend hook."""

    return resolve_approval_wall(
        ApprovalWallConfig(
            secret_supplier=approval_wall_secret_supplier_from_env(
                env_name=secret_env,
                environ=environ,
                backend_supplier=backend_supplier,
            ),
            state_path=approval_wall_state_path(state_root),
            now=now,
            policy_sha=policy_sha,
        )
    )


def load_approval_wall_state(path: str | Path) -> ApprovalWallState:
    state_path = Path(path)
    if not state_path.exists():
        return ApprovalWallState()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApprovalWallStateError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise ApprovalWallStateError("approval wall state must be a JSON object")
    return ApprovalWallState.from_payload(payload)


def save_approval_wall_state(path: str | Path, state: ApprovalWallState) -> None:
    state_path = Path(path)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_name(f".{state_path.name}.tmp")
        tmp.write_text(json.dumps(state.to_payload(), sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(state_path)
    except OSError as exc:
        raise ApprovalWallStateError(str(exc)) from exc


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


def approval_capability_policy_sha(
    *,
    run_mode: str,
    risk_tier: str,
    policy_material: Mapping[str, Any] | None = None,
) -> str:
    """Derive the approval-wall policy digest bound to mode and risk tier."""

    return approval_policy_sha(
        run_mode=run_mode,
        risk_tier=risk_tier,
        policy_material=policy_material,
    )


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


def _issuer_secret_bytes(supplier: SecretSupplier) -> bytes:
    try:
        value = supplier()
    except Exception as exc:
        raise ApprovalCapabilityIssuerError("approval capability secret unavailable") from exc
    if value is None:
        raise ApprovalCapabilityIssuerError("approval capability secret unavailable")
    secret = _coerce_secret(value)
    if not secret:
        raise ApprovalCapabilityIssuerError("approval capability secret unavailable")
    return secret


def _coerce_secret(value: bytes | str) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _with_padding(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")
