"""CE secret/identity backend seam (ce-ops#113, Wave 2 Phase 1/2).

This module defines the value-free interface CE uses to broker secrets and
identity metadata through OpenBao or compatible backends. It deliberately does
no I/O on import and registers no validator check.

Phase 1 provides frozen value objects, a tiny registry, and an inert fake
backend for tests. Phase 2 adds a CI-pure OpenBao adapter whose HTTP/materialize
operations are entirely injected by the caller, so unit tests make no live
OpenBao calls.
"""

from __future__ import annotations

import abc
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit


class SecretIdentityError(Exception):
    """Base class for secret-identity backend errors."""


class SecretIdentityRefused(SecretIdentityError):
    """A request was refused before secret materialization."""


class SecretBackendTransportError(SecretIdentityError):
    """A backend transport/token error was converted to a value-free failure."""


class SecretMaterializationError(SecretIdentityError):
    """A materializer failure was converted to a value-free failure."""


class AuditUnavailable(SecretIdentityRefused):
    """The backend audit preflight failed, so issuance must fail closed."""


class UnknownBackend(SecretIdentityError):
    """No secret-identity backend is registered under the requested key."""


class BackendAlreadyRegistered(SecretIdentityError):
    """A secret-identity backend key was registered twice."""


@dataclass(frozen=True)
class SecretRef:
    """Logical pointer to a secret field; never contains the secret value."""

    backend: str
    mount: str
    path: str
    field: str
    version: int | None
    purpose: str
    owner_ref: str
    policy_sha: str

    def to_record(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "mount": self.mount,
            "path": self.path,
            "field": self.field,
            "version": self.version,
            "purpose": self.purpose,
            "owner_ref": self.owner_ref,
            "policy_sha": self.policy_sha,
        }


@dataclass(frozen=True)
class SecretRequest:
    """Request to issue/materialize one logical secret for one governed run."""

    run_id: str
    seat_id: str
    repo: str
    secret_ref: SecretRef
    ttl_seconds: int
    delivery: str
    requested_capabilities: tuple[str, ...]
    audit_context: Mapping[str, str] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "seat_id": self.seat_id,
            "repo": self.repo,
            "secret_ref": self.secret_ref.to_record(),
            "ttl_seconds": self.ttl_seconds,
            "delivery": self.delivery,
            "requested_capabilities": list(self.requested_capabilities),
            "audit_context": dict(self.audit_context),
        }


@dataclass(frozen=True)
class SecretGrant:
    """Value-free grant metadata for a secret request."""

    grant_id: str
    run_id: str
    seat_id: str
    secret_ref: SecretRef
    lease_id: str | None
    token_accessor_ref: str | None
    issued_at: str
    expires_at: str
    delivery_ref: str | None
    audit_ref: str
    revoked_at: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "run_id": self.run_id,
            "seat_id": self.seat_id,
            "secret_ref": self.secret_ref.to_record(),
            "lease_id": self.lease_id,
            "token_accessor_ref": self.token_accessor_ref,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "delivery_ref": self.delivery_ref,
            "audit_ref": self.audit_ref,
            "revoked_at": self.revoked_at,
        }


@dataclass(frozen=True)
class SecretZeroRequest:
    """Request for a one-use wrapped AppRole SecretID for one dev seat."""

    run_id: str
    requester_seat_id: str
    seat_id: str
    role_name: str
    delivery_ref: str
    wrap_ttl_seconds: int
    secret_id_ttl_seconds: int
    secret_id_num_uses: int = 1
    delivery: str = "broker-channel"
    auth_mount: str = "approle"
    audit_context: Mapping[str, str] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "requester_seat_id": self.requester_seat_id,
            "seat_id": self.seat_id,
            "role_name": self.role_name,
            "delivery_ref": self.delivery_ref,
            "wrap_ttl_seconds": self.wrap_ttl_seconds,
            "secret_id_ttl_seconds": self.secret_id_ttl_seconds,
            "secret_id_num_uses": self.secret_id_num_uses,
            "delivery": self.delivery,
            "auth_mount": self.auth_mount,
            "audit_context": dict(self.audit_context),
        }


@dataclass(frozen=True)
class SecretZeroGrant:
    """Value-free metadata for a delivered secret-zero wrapping token."""

    grant_id: str
    run_id: str
    requester_seat_id: str
    seat_id: str
    role_name: str
    auth_mount: str
    issued_at: str
    expires_at: str
    delivery_ref: str
    wrap_accessor_ref: str | None
    wrapped_accessor_ref: str | None
    audit_ref: str
    revoked_at: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "run_id": self.run_id,
            "requester_seat_id": self.requester_seat_id,
            "seat_id": self.seat_id,
            "role_name": self.role_name,
            "auth_mount": self.auth_mount,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "delivery_ref": self.delivery_ref,
            "wrap_accessor_ref": self.wrap_accessor_ref,
            "wrapped_accessor_ref": self.wrapped_accessor_ref,
            "audit_ref": self.audit_ref,
            "revoked_at": self.revoked_at,
        }


@dataclass(frozen=True)
class SecretZeroPayload:
    """In-memory secret-zero payload handed to an injected delivery channel."""

    seat_id: str
    requester_seat_id: str
    role_name: str
    auth_mount: str
    role_id: str = field(repr=False)
    wrapping_token: str = field(repr=False)
    wrap_expires_at: str
    wrap_accessor_ref: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "seat_id": self.seat_id,
            "requester_seat_id": self.requester_seat_id,
            "role_name": self.role_name,
            "auth_mount": self.auth_mount,
            "role_id_ref": f"openbao-role-id:{self.auth_mount}:{self.role_name}",
            "wrap_expires_at": self.wrap_expires_at,
            "wrap_accessor_ref": self.wrap_accessor_ref,
        }


@dataclass(frozen=True)
class WrappedSecretZeroRetrieval:
    """Seat-side in-memory inputs for unwrapping and logging in to AppRole."""

    seat_id: str
    role_name: str
    role_id_supplier: Callable[[], str] = field(repr=False)
    wrapping_token_supplier: Callable[[], str] = field(repr=False)
    auth_mount: str = "approle"


@dataclass(frozen=True)
class OpenBaoAppRoleSession:
    """In-memory OpenBao AppRole session; token is intentionally repr-hidden."""

    seat_id: str
    role_name: str
    auth_mount: str
    token: str = field(repr=False)
    token_accessor_ref: str | None
    secret_id_accessor_ref: str | None
    lease_duration_seconds: int | None
    audit_ref: str

    def token_supplier(self) -> str:
        return self.token

    def as_openbao_config(
        self,
        *,
        address: str,
        kv_mount: str = "ce-kv",
        verify_tls: bool = True,
    ) -> "OpenBaoConfig":
        return OpenBaoConfig(
            address=address,
            token_supplier=self.token_supplier,
            kv_mount=kv_mount,
            verify_tls=verify_tls,
        )


@dataclass(frozen=True)
class IdentityDescriptor:
    """Value-free identity metadata for a CE seat."""

    identity_ref: str
    seat_id: str
    human_id: str | None
    github_login_ref: str | None
    email_ref: str | None
    reviewer_persona_ref: str | None
    policy_refs: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        return {
            "identity_ref": self.identity_ref,
            "seat_id": self.seat_id,
            "human_id": self.human_id,
            "github_login_ref": self.github_login_ref,
            "email_ref": self.email_ref,
            "reviewer_persona_ref": self.reviewer_persona_ref,
            "policy_refs": list(self.policy_refs),
        }


class SecretIdentityBackend(Protocol):
    """Backend protocol shared by fake/OpenBao/Vault-compatible providers."""

    backend_key: str

    def validate_config(self) -> None:
        """Refuse when backend config or audit posture is unsafe."""

    def resolve_identity(self, seat_id: str) -> IdentityDescriptor:
        """Return value-free identity metadata for one CE seat."""

    def issue(self, request: SecretRequest) -> SecretGrant:
        """Create a value-free grant for a logical secret request."""

    def issue_secret_zero(self, request: SecretZeroRequest) -> SecretZeroGrant:
        """Create a value-free secret-zero grant for one seat."""

    def materialize(self, grant: SecretGrant, target_ref: str) -> SecretGrant:
        """Expose the value to ``target_ref`` without returning it to CE records."""

    def revoke(self, grant: SecretGrant) -> SecretGrant:
        """Revoke/release a grant and return value-free metadata."""

    def collect_audit(self, grant: SecretGrant) -> Mapping[str, str]:
        """Return audit correlation metadata only."""


BackendFactory = Callable[[], SecretIdentityBackend]
_REGISTRY: dict[str, BackendFactory] = {}


def register_backend(key: str, factory: BackendFactory) -> None:
    if key in _REGISTRY:
        raise BackendAlreadyRegistered(f"a secret-identity backend is already registered under {key!r}")
    _REGISTRY[key] = factory


def get_backend(key: str) -> SecretIdentityBackend:
    try:
        factory = _REGISTRY[key]
    except KeyError:
        available = ", ".join(available_backends()) or "(none)"
        raise UnknownBackend(
            f"no secret-identity backend registered under {key!r}; available: {available}"
        ) from None
    return factory()


def available_backends() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


_MAX_TTL_SECONDS = 3600
_POLICY_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_CONTROLLER_KEY_RE = re.compile(r"controller.{0,10}key", re.IGNORECASE)
_DELIVERY_MODES = frozenset({"file", "env", "socket", "none"})
_DEFAULT_ALLOWED_CAPABILITIES = frozenset({"read"})
_MAX_SECRET_ZERO_TTL_SECONDS = 600
_SECRET_ZERO_DELIVERY_MODES = frozenset({"broker-channel", "unix-socket", "stdin-once", "memory"})
_SEAT_ID_RE = re.compile(r"^dev-[1-9][0-9]*$")
_APPROLE_MOUNT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_LOCAL_SOURCE_REF_RE = re.compile(r"^host-local-ref:[A-Za-z0-9][A-Za-z0-9./:@-]{0,127}$")
_INLINE_SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\b(?:hvs|hvb|bao)\.[A-Za-z0-9_-]{16,}\b"),
    re.compile(
        r"\b(?:password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*=\s*\S{4,}",
        re.IGNORECASE,
    ),
)
_CapabilitySet = set[str] | frozenset[str] | tuple[str, ...]
_CapabilityPolicy = Mapping[SecretRef, _CapabilitySet]
_RefPredicate = Callable[[SecretRef], bool]
DEFAULT_APPROVAL_WALL_SECRET_BACKEND = "openbao"
DEFAULT_APPROVAL_WALL_SECRET_MOUNT = "ce-kv"
DEFAULT_APPROVAL_WALL_SECRET_PATH = "forge/approval-capability/wall"
DEFAULT_APPROVAL_WALL_SECRET_FIELD = "signing_secret"
DEFAULT_APPROVAL_WALL_SECRET_PURPOSE = "approval-capability-wall"
DEFAULT_APPROVAL_WALL_SECRET_OWNER_REF = "controller:integrator"
DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_BACKEND = DEFAULT_APPROVAL_WALL_SECRET_BACKEND
DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_MOUNT = DEFAULT_APPROVAL_WALL_SECRET_MOUNT
DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_PATH = "forge/ce-dev-" "2/gh-token"
DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_FIELD = "token"
DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_PURPOSE = "review-pickup-token"
DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_OWNER_REF = "controller:reviewer"
DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_TTL_SECONDS = 300
_OPENBAO_APPROVAL_WALL_PATH = DEFAULT_APPROVAL_WALL_SECRET_PATH
_OPENBAO_APPROVAL_WALL_FIELD = DEFAULT_APPROVAL_WALL_SECRET_FIELD
_OPENBAO_APPROVAL_WALL_PURPOSE = DEFAULT_APPROVAL_WALL_SECRET_PURPOSE
_OPENBAO_APPROVAL_WALL_OWNER_REF = DEFAULT_APPROVAL_WALL_SECRET_OWNER_REF


def _ref_names_controller_key(ref: SecretRef) -> bool:
    fields = (ref.backend, ref.mount, ref.path, ref.field, ref.purpose, ref.owner_ref)
    return any(_CONTROLLER_KEY_RE.search(value) for value in fields)


def _looks_like_inline_secret_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in _INLINE_SECRET_VALUE_PATTERNS)


def _validate_ref_shape(
    ref: SecretRef,
    *,
    backend_key: str | None = None,
    kv_mount: str | None = None,
) -> None:
    text_fields = {
        "backend": ref.backend,
        "mount": ref.mount,
        "path": ref.path,
        "field": ref.field,
        "purpose": ref.purpose,
        "owner_ref": ref.owner_ref,
        "policy_sha": ref.policy_sha,
    }
    for field_name, value in text_fields.items():
        if not isinstance(value, str) or not value.strip():
            raise SecretIdentityRefused(f"secret_ref.{field_name} must be a non-empty reference string")
        if _looks_like_inline_secret_value(value):
            raise SecretIdentityRefused(
                f"secret_ref.{field_name} must be a value-free reference, not inline secret material"
            )
    if not _POLICY_SHA_RE.fullmatch(ref.policy_sha):
        raise SecretIdentityRefused("secret_ref.policy_sha must be a lowercase 64-hex digest")
    if ref.version is not None and ref.version <= 0:
        raise SecretIdentityRefused("secret_ref.version must be positive when set")
    if backend_key is not None and ref.backend != backend_key:
        raise SecretIdentityRefused(
            f"secret_ref backend {ref.backend!r} is not bound to {backend_key!r}"
        )
    if kv_mount is not None and ref.mount != kv_mount:
        raise SecretIdentityRefused(
            f"secret_ref mount {ref.mount!r} is not bound to configured mount {kv_mount!r}"
        )
    if _ref_names_controller_key(ref):
        raise SecretIdentityRefused("controller-key secret classes are forbidden")


def validate_secret_ref(
    ref: SecretRef,
    *,
    backend_key: str | None = None,
    kv_mount: str | None = None,
) -> None:
    """Validate that a SecretRef is shaped as a value-free reference."""

    _validate_ref_shape(ref, backend_key=backend_key, kv_mount=kv_mount)


def _normalize_allowed_capabilities(
    allowed_refs: set[SecretRef],
    allowed_capabilities: _CapabilityPolicy | None,
) -> dict[SecretRef, frozenset[str]]:
    normalized: dict[SecretRef, frozenset[str]] = {}
    for ref in allowed_refs:
        normalized[ref] = _DEFAULT_ALLOWED_CAPABILITIES
    for ref, capabilities in (allowed_capabilities or {}).items():
        normalized[ref] = frozenset(capabilities)
    return normalized


def _validate_request_shape(
    request: SecretRequest,
    *,
    backend_key: str | None = None,
    kv_mount: str | None = None,
) -> None:
    if request.ttl_seconds <= 0:
        raise SecretIdentityRefused("ttl_seconds must be positive")
    if request.ttl_seconds > _MAX_TTL_SECONDS:
        raise SecretIdentityRefused(f"ttl_seconds must be <= {_MAX_TTL_SECONDS}")
    if request.delivery not in _DELIVERY_MODES:
        raise SecretIdentityRefused(f"unsupported delivery mode {request.delivery!r}")
    if not _REPO_RE.fullmatch(request.repo):
        raise SecretIdentityRefused(f"repo {request.repo!r} is not in owner/name form")
    if not request.requested_capabilities:
        raise SecretIdentityRefused("requested_capabilities must not be empty")
    if any(
        not isinstance(capability, str) or not capability.strip()
        for capability in request.requested_capabilities
    ):
        raise SecretIdentityRefused(
            "requested_capabilities must contain non-empty capability names"
        )
    _validate_ref_shape(request.secret_ref, backend_key=backend_key, kv_mount=kv_mount)


def _validate_runtime_policy_binding(
    request: SecretRequest,
    *,
    allowed_refs: set[SecretRef],
    allowed_capabilities: Mapping[SecretRef, frozenset[str]],
    allowed_ref_predicates: tuple[_RefPredicate, ...] = (),
) -> None:
    exact_ref_allowed = request.secret_ref in allowed_refs
    predicate_ref_allowed = any(
        predicate(request.secret_ref) for predicate in allowed_ref_predicates
    )
    if not exact_ref_allowed and not predicate_ref_allowed:
        raise SecretIdentityRefused(
            f"secret_ref {request.secret_ref.mount}/{request.secret_ref.path} is not allowed"
        )
    requested = frozenset(request.requested_capabilities)
    allowed = allowed_capabilities.get(request.secret_ref, frozenset())
    if predicate_ref_allowed:
        allowed = allowed | _DEFAULT_ALLOWED_CAPABILITIES
    if not requested <= allowed:
        denied = ", ".join(sorted(requested - allowed)) or "(none)"
        raise SecretIdentityRefused(
            f"requested capabilities are not allowed by policy: {denied}"
        )


def _validate_local_source_ref(source_ref: object) -> str:
    if not isinstance(source_ref, str) or not source_ref:
        raise SecretIdentityRefused("local source refs must be non-empty strings")
    if not _LOCAL_SOURCE_REF_RE.fullmatch(source_ref):
        raise SecretIdentityRefused(
            "local source refs must be value-free host-local-ref references"
        )
    return source_ref


def _validate_secret_zero_common(seat_id: str, role_name: str, auth_mount: str) -> None:
    if not _SEAT_ID_RE.fullmatch(seat_id):
        raise SecretIdentityRefused(f"seat_id {seat_id!r} is not a concrete dev seat")
    expected_role = f"ce-{seat_id}"
    if role_name != expected_role:
        raise SecretIdentityRefused(
            f"role_name {role_name!r} is not bound to seat {seat_id!r}; expected {expected_role!r}"
        )
    if not _APPROLE_MOUNT_RE.fullmatch(auth_mount):
        raise SecretIdentityRefused(f"auth_mount {auth_mount!r} is not a simple AppRole mount")


def _normalize_secret_zero_delivery_ref(delivery_ref: str) -> str:
    return delivery_ref.strip()


def _secret_zero_ref_scheme_ok(delivery_ref: str, delivery: str) -> bool:
    scheme = urlsplit(_normalize_secret_zero_delivery_ref(delivery_ref)).scheme.lower()
    return scheme in _SECRET_ZERO_DELIVERY_MODES and scheme == delivery


def _validate_secret_zero_request(
    request: SecretZeroRequest,
    *,
    allowed_seats: set[str],
) -> None:
    if not request.run_id.strip():
        raise SecretIdentityRefused("run_id must not be empty")
    if not _SEAT_ID_RE.fullmatch(request.requester_seat_id):
        raise SecretIdentityRefused(
            f"requester_seat_id {request.requester_seat_id!r} is not a concrete dev seat"
        )
    _validate_secret_zero_common(request.seat_id, request.role_name, request.auth_mount)
    if request.requester_seat_id != request.seat_id:
        raise SecretIdentityRefused(
            f"requester_seat_id {request.requester_seat_id!r} is not authorized "
            f"for requested seat {request.seat_id!r}"
        )
    if request.seat_id not in allowed_seats:
        allowed = ", ".join(sorted(allowed_seats)) or "(none)"
        raise SecretIdentityRefused(
            f"seat {request.seat_id!r} is not enabled for secret-zero; allowed: {allowed}"
        )
    if request.delivery not in _SECRET_ZERO_DELIVERY_MODES:
        raise SecretIdentityRefused(f"unsupported secret-zero delivery mode {request.delivery!r}")
    delivery_ref = _normalize_secret_zero_delivery_ref(request.delivery_ref)
    if not delivery_ref:
        raise SecretIdentityRefused("delivery_ref must not be empty")
    if not _secret_zero_ref_scheme_ok(delivery_ref, request.delivery):
        allowed = ", ".join(sorted(_SECRET_ZERO_DELIVERY_MODES))
        raise SecretIdentityRefused(
            "secret-zero delivery_ref scheme must match delivery "
            f"and be one of: {allowed}"
        )
    if request.wrap_ttl_seconds <= 0 or request.wrap_ttl_seconds > _MAX_SECRET_ZERO_TTL_SECONDS:
        raise SecretIdentityRefused(
            f"wrap_ttl_seconds must be between 1 and {_MAX_SECRET_ZERO_TTL_SECONDS}"
        )
    if request.secret_id_ttl_seconds <= 0 or request.secret_id_ttl_seconds > _MAX_SECRET_ZERO_TTL_SECONDS:
        raise SecretIdentityRefused(
            f"secret_id_ttl_seconds must be between 1 and {_MAX_SECRET_ZERO_TTL_SECONDS}"
        )
    if request.secret_id_num_uses != 1:
        raise SecretIdentityRefused("secret-zero SecretIDs must be single-use")


def _openbao_request_value_free(
    runner: "OpenBaoRunner",
    request: "OpenBaoRequest",
    label: str,
) -> "OpenBaoResponse":
    try:
        return runner(request)
    except SecretIdentityError:
        raise
    except Exception:
        raise SecretBackendTransportError(
            f"OpenBao {label} request failed; backend value redacted"
        ) from None


def _expect_openbao_mapping(response: "OpenBaoResponse", label: str) -> Mapping[str, Any]:
    if response.status < 200 or response.status >= 300 or not isinstance(response.json, Mapping):
        raise SecretIdentityRefused(f"OpenBao {label} failed with HTTP {response.status}")
    return response.json


def redeem_wrapped_secret_zero(
    config: WrappedSecretZeroRetrieval,
    *,
    runner: "OpenBaoRunner",
) -> OpenBaoAppRoleSession:
    """Seat-side unwrap/login for a delivered one-use AppRole SecretID."""

    _validate_secret_zero_common(config.seat_id, config.role_name, config.auth_mount)
    wrapping_token = config.wrapping_token_supplier()
    role_id = config.role_id_supplier()
    if not wrapping_token or not role_id:
        raise SecretIdentityRefused("secret-zero suppliers returned empty values")

    unwrap_response = _openbao_request_value_free(
        runner,
        OpenBaoRequest("POST", "/v1/sys/wrapping/unwrap", token=wrapping_token),
        "wrapping unwrap",
    )
    unwrap_payload = _expect_openbao_mapping(unwrap_response, "wrapping unwrap")
    unwrap_data = unwrap_payload.get("data")
    if not isinstance(unwrap_data, Mapping) or not isinstance(unwrap_data.get("secret_id"), str):
        raise SecretIdentityRefused("OpenBao wrapping unwrap response missing SecretID")
    secret_id = unwrap_data["secret_id"]
    secret_id_accessor = unwrap_data.get("secret_id_accessor")

    login_response = _openbao_request_value_free(
        runner,
        OpenBaoRequest(
            "POST",
            f"/v1/auth/{config.auth_mount}/login",
            token="",
            json={"role_id": role_id, "secret_id": secret_id},
        ),
        "AppRole login",
    )
    secret_id = ""
    login_payload = _expect_openbao_mapping(login_response, "AppRole login")
    auth = login_payload.get("auth")
    if not isinstance(auth, Mapping) or not isinstance(auth.get("client_token"), str):
        raise SecretIdentityRefused("OpenBao AppRole login response missing client token")
    lease_duration = auth.get("lease_duration")
    return OpenBaoAppRoleSession(
        seat_id=config.seat_id,
        role_name=config.role_name,
        auth_mount=config.auth_mount,
        token=auth["client_token"],
        token_accessor_ref=auth.get("accessor") if isinstance(auth.get("accessor"), str) else None,
        secret_id_accessor_ref=secret_id_accessor if isinstance(secret_id_accessor, str) else None,
        lease_duration_seconds=lease_duration if isinstance(lease_duration, int) else None,
        audit_ref=f"openbao-secret-zero:{config.seat_id}:{config.auth_mount}/{config.role_name}",
    )


class FakeSecretIdentityBackend:
    """Value-free fake backend for tests and CI-pure interface wiring."""

    backend_key = "fake"

    def __init__(
        self,
        *,
        identities: Mapping[str, IdentityDescriptor] | None = None,
        allowed_refs: set[SecretRef] | None = None,
        allowed_capabilities: _CapabilityPolicy | None = None,
        allowed_secret_zero_seats: tuple[str, ...] = ("dev-1", "dev-2", "dev-3", "dev-4"),
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._identities = dict(identities or {})
        self._allowed_refs = set(allowed_refs or set())
        self._allowed_capabilities = _normalize_allowed_capabilities(
            self._allowed_refs, allowed_capabilities
        )
        self._allowed_secret_zero_seats = set(allowed_secret_zero_seats)
        self._clock = clock
        self._counter = 0
        self._audit: dict[str, Mapping[str, str]] = {}

    def validate_config(self) -> None:
        return None

    def resolve_identity(self, seat_id: str) -> IdentityDescriptor:
        try:
            return self._identities[seat_id]
        except KeyError:
            raise SecretIdentityRefused(f"no identity descriptor for seat {seat_id!r}") from None

    def issue(self, request: SecretRequest) -> SecretGrant:
        _validate_request_shape(request)
        _validate_runtime_policy_binding(
            request,
            allowed_refs=self._allowed_refs,
            allowed_capabilities=self._allowed_capabilities,
        )
        self._counter += 1
        now = self._clock()
        grant = SecretGrant(
            grant_id=f"fake-grant-{request.run_id}-{self._counter:03d}",
            run_id=request.run_id,
            seat_id=request.seat_id,
            secret_ref=request.secret_ref,
            lease_id=None,
            token_accessor_ref=None,
            issued_at=_iso(now),
            expires_at=_iso(now + timedelta(seconds=request.ttl_seconds)),
            delivery_ref=None,
            audit_ref=f"fake-audit:{request.run_id}:{self._counter:03d}",
        )
        self._audit[grant.grant_id] = {
            "backend": self.backend_key,
            "grant_id": grant.grant_id,
            "audit_ref": grant.audit_ref,
        }
        return grant

    def issue_secret_zero(self, request: SecretZeroRequest) -> SecretZeroGrant:
        _validate_secret_zero_request(
            request,
            allowed_seats=self._allowed_secret_zero_seats,
        )
        self._counter += 1
        now = self._clock()
        grant = SecretZeroGrant(
            grant_id=f"fake-secret-zero-{request.run_id}-{self._counter:03d}",
            run_id=request.run_id,
            requester_seat_id=request.requester_seat_id,
            seat_id=request.seat_id,
            role_name=request.role_name,
            auth_mount=request.auth_mount,
            issued_at=_iso(now),
            expires_at=_iso(now + timedelta(seconds=request.wrap_ttl_seconds)),
            delivery_ref=_normalize_secret_zero_delivery_ref(request.delivery_ref),
            wrap_accessor_ref=None,
            wrapped_accessor_ref=None,
            audit_ref=f"fake-secret-zero-audit:{request.run_id}:{self._counter:03d}",
        )
        self._audit[grant.grant_id] = {
            "backend": self.backend_key,
            "grant_id": grant.grant_id,
            "audit_ref": grant.audit_ref,
            "requester_seat_id": request.requester_seat_id,
            "seat_id": request.seat_id,
        }
        return grant

    def materialize(self, grant: SecretGrant, target_ref: str) -> SecretGrant:
        if grant.revoked_at is not None:
            raise SecretIdentityRefused(f"grant {grant.grant_id!r} is already revoked")
        return replace(grant, delivery_ref=target_ref)

    def revoke(self, grant: SecretGrant) -> SecretGrant:
        if grant.revoked_at is not None:
            return grant
        return replace(grant, revoked_at=_iso(self._clock()))

    def collect_audit(self, grant: SecretGrant) -> Mapping[str, str]:
        return self._audit.get(
            grant.grant_id,
            {"backend": self.backend_key, "grant_id": grant.grant_id, "audit_ref": grant.audit_ref},
        )


LocalSecretMaterializer = Callable[[str, str], None]


class LocalSecretIdentityBackend:
    """Host-local compatibility backend with all materialization injected."""

    backend_key = "local"

    def __init__(
        self,
        *,
        identities: Mapping[str, IdentityDescriptor] | None = None,
        local_refs: Mapping[SecretRef, str] | None = None,
        allowed_capabilities: _CapabilityPolicy | None = None,
        materializer: LocalSecretMaterializer | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._identities = dict(identities or {})
        self._local_refs = dict(local_refs or {})
        self._allowed_refs = set(self._local_refs)
        self._allowed_capabilities = _normalize_allowed_capabilities(
            self._allowed_refs, allowed_capabilities
        )
        self._materializer = materializer
        self._clock = clock
        self._counter = 0
        self._audit: dict[str, Mapping[str, str]] = {}

    def validate_config(self) -> None:
        for ref, source_ref in self._local_refs.items():
            _validate_ref_shape(ref, backend_key=self.backend_key)
            _validate_local_source_ref(source_ref)

    def resolve_identity(self, seat_id: str) -> IdentityDescriptor:
        try:
            return self._identities[seat_id]
        except KeyError:
            raise SecretIdentityRefused(f"no identity descriptor for seat {seat_id!r}") from None

    def issue(self, request: SecretRequest) -> SecretGrant:
        _validate_request_shape(request, backend_key=self.backend_key)
        _validate_runtime_policy_binding(
            request,
            allowed_refs=self._allowed_refs,
            allowed_capabilities=self._allowed_capabilities,
        )
        self.validate_config()
        self._counter += 1
        now = self._clock()
        source_ref = _validate_local_source_ref(self._local_refs[request.secret_ref])
        grant = SecretGrant(
            grant_id=f"local-grant-{request.run_id}-{self._counter:03d}",
            run_id=request.run_id,
            seat_id=request.seat_id,
            secret_ref=request.secret_ref,
            lease_id=None,
            token_accessor_ref=None,
            issued_at=_iso(now),
            expires_at=_iso(now + timedelta(seconds=request.ttl_seconds)),
            delivery_ref=None,
            audit_ref=f"local-audit:{request.run_id}:{self._counter:03d}",
        )
        self._audit[grant.grant_id] = {
            "backend": self.backend_key,
            "grant_id": grant.grant_id,
            "audit_ref": grant.audit_ref,
            "source_ref": source_ref,
        }
        return grant

    def issue_secret_zero(self, _request: SecretZeroRequest) -> SecretZeroGrant:
        raise SecretIdentityRefused(
            f"{self.backend_key!r} backend cannot issue OpenBao secret-zero grants"
        )

    def materialize(self, grant: SecretGrant, target_ref: str) -> SecretGrant:
        if grant.revoked_at is not None:
            raise SecretIdentityRefused(f"grant {grant.grant_id!r} is already revoked")
        try:
            source_ref = _validate_local_source_ref(self._local_refs[grant.secret_ref])
        except KeyError:
            raise SecretIdentityRefused(
                f"local source ref missing for {grant.secret_ref.mount}/{grant.secret_ref.path}"
            ) from None
        if self._materializer is None:
            raise SecretIdentityRefused(
                "local secret materialization requires an injected materializer"
            )
        try:
            self._materializer(source_ref, target_ref)
        except Exception:
            raise SecretMaterializationError(
                "local secret materialization failed; backend value redacted"
            ) from None
        return replace(grant, delivery_ref=target_ref)

    def revoke(self, grant: SecretGrant) -> SecretGrant:
        if grant.revoked_at is not None:
            return grant
        return replace(grant, revoked_at=_iso(self._clock()))

    def collect_audit(self, grant: SecretGrant) -> Mapping[str, str]:
        return self._audit.get(
            grant.grant_id,
            {"backend": self.backend_key, "grant_id": grant.grant_id, "audit_ref": grant.audit_ref},
        )


@dataclass(frozen=True)
class OpenBaoConfig:
    """OpenBao adapter config. ``token_supplier`` owns secret-zero bootstrap."""

    address: str
    token_supplier: Callable[[], str]
    kv_mount: str = "ce-kv"
    verify_tls: bool = True


@dataclass(frozen=True)
class OpenBaoRequest:
    method: str
    path: str
    token: str = field(repr=False)
    json: Mapping[str, Any] | None = field(default=None, repr=False)
    wrap_ttl_seconds: int | None = None

    def __repr__(self) -> str:
        json_ref = "<redacted>" if self.json is not None else None
        wrap_ref = (
            f", wrap_ttl_seconds={self.wrap_ttl_seconds!r}"
            if self.wrap_ttl_seconds is not None
            else ""
        )
        return (
            f"OpenBaoRequest(method={self.method!r}, path={self.path!r}, "
            f"json={json_ref}{wrap_ref})"
        )

    __str__ = __repr__


class _RedactedMapping(Mapping[str, Any]):
    """Mapping proxy whose display surface never includes raw backend values."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data = dict(data)

    def __getitem__(self, key: str) -> Any:
        return _redacted_value(self._data[key])

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return "<redacted-json>"

    __str__ = __repr__


def _redacted_value(value: Any) -> Any:
    if isinstance(value, Mapping) and not isinstance(value, _RedactedMapping):
        return _RedactedMapping(value)
    return value


@dataclass(frozen=True)
class OpenBaoResponse:
    status: int
    json: Mapping[str, Any] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.json is not None and not isinstance(self.json, Mapping):
            raise TypeError("OpenBaoResponse.json must be a mapping or None")
        if self.json is not None and not isinstance(self.json, _RedactedMapping):
            object.__setattr__(self, "json", _RedactedMapping(self.json))

    def __repr__(self) -> str:
        json_ref = "<redacted>" if self.json is not None else None
        return f"OpenBaoResponse(status={self.status!r}, json={json_ref})"

    __str__ = __repr__


OpenBaoRunner = Callable[[OpenBaoRequest], OpenBaoResponse]
SecretMaterializer = Callable[[str, str], None]
SecretZeroDeliverer = Callable[[str, SecretZeroPayload], str]


def _file_target_path(target_ref: str) -> Path:
    if target_ref.startswith("env:"):
        raise SecretIdentityRefused("secret materialization target must be file-backed, not env")
    if target_ref.startswith("file://"):
        raw = target_ref.removeprefix("file://")
    elif target_ref.startswith("file:"):
        raw = target_ref.removeprefix("file:")
    else:
        raw = target_ref
    path = Path(raw)
    if not path.is_absolute():
        raise SecretIdentityRefused("secret materialization file target must be an absolute path")
    return path


def _default_file_secret_materializer(target_ref: str, value: str) -> None:
    path = _file_target_path(target_ref)
    if path.exists() and path.is_symlink():
        raise SecretMaterializationError("secret materialization target must not be a symlink")
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        raise SecretMaterializationError("secret materialization failed; backend value redacted") from None
    try:
        path.chmod(0o600)
    except OSError:
        raise SecretMaterializationError("secret materialization chmod failed; backend value redacted") from None


class _SecretIdentityBase(abc.ABC):
    backend_key: str

    @abc.abstractmethod
    def validate_config(self) -> None:
        raise NotImplementedError


class OpenBaoSecretIdentityBackend(_SecretIdentityBase):
    """CI-pure OpenBao adapter with all I/O injected by the caller."""

    backend_key = "openbao"

    def __init__(
        self,
        config: OpenBaoConfig,
        *,
        runner: OpenBaoRunner,
        materializer: SecretMaterializer | None = None,
        secret_zero_deliverer: SecretZeroDeliverer | None = None,
        allowed_refs: set[SecretRef] | None = None,
        allowed_capabilities: _CapabilityPolicy | None = None,
        allowed_ref_predicates: tuple[_RefPredicate, ...] = (),
        allow_unrestricted_refs: bool = False,
        allowed_secret_zero_seats: tuple[str, ...] = ("dev-1", "dev-2", "dev-3", "dev-4"),
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._config = config
        self._runner = runner
        self._materializer = materializer or _default_file_secret_materializer
        self._secret_zero_deliverer = secret_zero_deliverer
        if allowed_refs is None and allow_unrestricted_refs:
            self._allowed_refs = None
        else:
            self._allowed_refs = set(allowed_refs or set())
        self._allowed_capabilities = _normalize_allowed_capabilities(
            self._allowed_refs or set(), allowed_capabilities
        )
        self._allowed_ref_predicates = tuple(allowed_ref_predicates)
        self._allowed_secret_zero_seats = set(allowed_secret_zero_seats)
        self._clock = clock
        self._audit_checked = False
        self._audit: dict[str, Mapping[str, str]] = {}

    def validate_config(self) -> None:
        if self._config.verify_tls and not self._config.address.startswith("https://"):
            raise SecretIdentityRefused("OpenBao address must use https when verify_tls is enabled")
        health = self._request("GET", "/v1/sys/health")
        if health.status >= 500:
            raise SecretIdentityRefused(f"OpenBao health preflight failed with HTTP {health.status}")
        audit = self._request("GET", "/v1/sys/audit")
        if audit.status != 200 or not audit.json:
            raise AuditUnavailable("OpenBao audit preflight found no enabled audit device")
        self._audit_checked = True

    def resolve_identity(self, seat_id: str) -> IdentityDescriptor:
        raise SecretIdentityRefused(
            f"OpenBao identity resolution for seat {seat_id!r} is deferred to the identity substrate"
        )

    def issue(self, request: SecretRequest) -> SecretGrant:
        _validate_request_shape(
            request,
            backend_key=self.backend_key,
            kv_mount=self._config.kv_mount,
        )
        if self._allowed_refs is not None:
            _validate_runtime_policy_binding(
                request,
                allowed_refs=self._allowed_refs,
                allowed_capabilities=self._allowed_capabilities,
                allowed_ref_predicates=self._allowed_ref_predicates,
            )
        if not self._audit_checked:
            self.validate_config()
        now = self._clock()
        grant = SecretGrant(
            grant_id=(
                f"openbao:{request.run_id}:{self._config.kv_mount}:"
                f"{request.secret_ref.path}"
            ),
            run_id=request.run_id,
            seat_id=request.seat_id,
            secret_ref=request.secret_ref,
            lease_id=None,
            token_accessor_ref=None,
            issued_at=_iso(now),
            expires_at=_iso(now + timedelta(seconds=request.ttl_seconds)),
            delivery_ref=None,
            audit_ref=(
                f"openbao:{request.run_id}:{self._config.kv_mount}/"
                f"{request.secret_ref.path}"
            ),
        )
        self._audit[grant.grant_id] = {
            "backend": self.backend_key,
            "grant_id": grant.grant_id,
            "audit_ref": grant.audit_ref,
            "mount": self._config.kv_mount,
            "path": request.secret_ref.path,
        }
        return grant

    def issue_secret_zero(self, request: SecretZeroRequest) -> SecretZeroGrant:
        """Mint and deliver a short-lived wrapped SecretID for one dev AppRole."""

        _validate_secret_zero_request(
            request,
            allowed_seats=self._allowed_secret_zero_seats,
        )
        if self._secret_zero_deliverer is None:
            raise SecretIdentityRefused("secret-zero delivery requires an injected deliverer")
        if not self._audit_checked:
            self.validate_config()
        now = self._clock()
        role_id = self._read_approle_role_id(request.auth_mount, request.role_name)
        payload, wrapped_accessor_ref = self._create_wrapped_secret_id(
            request,
            role_id=role_id,
            now=now,
        )
        delivery_ref = self._deliver_secret_zero(
            _normalize_secret_zero_delivery_ref(request.delivery_ref),
            payload,
            delivery=request.delivery,
        )
        grant = SecretZeroGrant(
            grant_id=f"openbao-secret-zero:{request.run_id}:{request.seat_id}",
            run_id=request.run_id,
            requester_seat_id=request.requester_seat_id,
            seat_id=request.seat_id,
            role_name=request.role_name,
            auth_mount=request.auth_mount,
            issued_at=_iso(now),
            expires_at=payload.wrap_expires_at,
            delivery_ref=delivery_ref,
            wrap_accessor_ref=payload.wrap_accessor_ref,
            wrapped_accessor_ref=wrapped_accessor_ref,
            audit_ref=f"openbao-secret-zero:{request.run_id}:{request.auth_mount}/{request.role_name}",
        )
        self._audit[grant.grant_id] = {
            "backend": self.backend_key,
            "grant_id": grant.grant_id,
            "audit_ref": grant.audit_ref,
            "requester_seat_id": request.requester_seat_id,
            "seat_id": request.seat_id,
            "role_name": request.role_name,
        }
        return grant

    def materialize(self, grant: SecretGrant, target_ref: str) -> SecretGrant:
        if grant.revoked_at is not None:
            raise SecretIdentityRefused(f"grant {grant.grant_id!r} is already revoked")
        value = self._read_secret_field(grant.secret_ref)
        materializer_error: SecretMaterializationError | None = None
        try:
            self._materializer(target_ref, value)
        except SecretIdentityError:
            raise
        except Exception:
            materializer_error = SecretMaterializationError(
                "secret materialization failed; backend value redacted"
            )
        if materializer_error is not None:
            raise materializer_error
        return replace(grant, delivery_ref=target_ref)

    def revoke(self, grant: SecretGrant) -> SecretGrant:
        if grant.revoked_at is not None:
            return grant
        return replace(grant, revoked_at=_iso(self._clock()))

    def collect_audit(self, grant: SecretGrant) -> Mapping[str, str]:
        return self._audit.get(
            grant.grant_id,
            {
                "backend": self.backend_key,
                "grant_id": grant.grant_id,
                "audit_ref": grant.audit_ref,
                "mount": grant.secret_ref.mount,
                "path": grant.secret_ref.path,
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        json_body: Mapping[str, Any] | None = None,
        wrap_ttl_seconds: int | None = None,
    ) -> OpenBaoResponse:
        token_error: SecretBackendTransportError | None = None
        try:
            token = self._config.token_supplier()
        except Exception:
            token_error = SecretBackendTransportError(
                "OpenBao token supplier failed; backend value redacted"
            )
            token = ""
        if token_error is not None:
            raise token_error
        if not token:
            raise SecretIdentityRefused("OpenBao token supplier returned an empty token")
        request = OpenBaoRequest(
            method=method,
            path=path,
            token=token,
            json=json_body,
            wrap_ttl_seconds=wrap_ttl_seconds,
        )
        runner_error: SecretBackendTransportError | None = None
        try:
            return self._runner(request)
        except Exception:
            runner_error = SecretBackendTransportError(
                "OpenBao request failed; backend response value redacted"
            )
        if runner_error is not None:
            raise runner_error
        raise SecretBackendTransportError(
            "OpenBao request failed; backend response value redacted"
        )

    def _read_secret_field(self, ref: SecretRef) -> str:
        if ref.backend != self.backend_key:
            raise SecretIdentityRefused(f"SecretRef backend {ref.backend!r} is not openbao")
        if ref.mount != self._config.kv_mount:
            raise SecretIdentityRefused(
                f"SecretRef mount {ref.mount!r} is not bound to configured mount "
                f"{self._config.kv_mount!r}"
            )
        path = f"/v1/{self._config.kv_mount}/data/{ref.path}"
        if ref.version is not None:
            path = f"{path}?version={ref.version}"
        response = self._request("GET", path)
        if response.status != 200 or not isinstance(response.json, Mapping):
            raise SecretIdentityRefused(
                f"OpenBao secret read failed for {ref.mount}/{ref.path}: HTTP {response.status}"
            )
        data = response.json.get("data")
        if not isinstance(data, Mapping):
            raise SecretIdentityRefused(f"OpenBao secret response missing data for {ref.mount}/{ref.path}")
        fields = data.get("data")
        if not isinstance(fields, Mapping) or ref.field not in fields:
            raise SecretIdentityRefused(
                f"OpenBao secret response missing field {ref.field!r} for {ref.mount}/{ref.path}"
            )
        value = fields[ref.field]
        if not isinstance(value, str):
            raise SecretIdentityRefused(
                f"OpenBao secret field {ref.field!r} for {ref.mount}/{ref.path} must be a string"
            )
        return value

    def _read_approle_role_id(self, auth_mount: str, role_name: str) -> str:
        response = self._request(
            "GET",
            f"/v1/auth/{auth_mount}/role/{role_name}/role-id",
        )
        payload = _expect_openbao_mapping(response, "AppRole role-id read")
        data = payload.get("data")
        if not isinstance(data, Mapping) or not isinstance(data.get("role_id"), str):
            raise SecretIdentityRefused("OpenBao AppRole role-id response missing RoleID")
        return data["role_id"]

    def _create_wrapped_secret_id(
        self,
        request: SecretZeroRequest,
        *,
        role_id: str,
        now: datetime,
    ) -> tuple[SecretZeroPayload, str | None]:
        response = self._request(
            "POST",
            f"/v1/auth/{request.auth_mount}/role/{request.role_name}/secret-id",
            json_body={
                "ttl": f"{request.secret_id_ttl_seconds}s",
                "num_uses": request.secret_id_num_uses,
                "metadata": {
                    "run_id": request.run_id,
                    "requester_seat_id": request.requester_seat_id,
                    "seat_id": request.seat_id,
                    "broker": "creator-engine",
                },
            },
            wrap_ttl_seconds=request.wrap_ttl_seconds,
        )
        payload = _expect_openbao_mapping(response, "wrapped SecretID creation")
        data = payload.get("data")
        if isinstance(data, Mapping) and isinstance(data.get("secret_id"), str):
            raise SecretIdentityRefused("OpenBao returned an unwrapped SecretID to the broker")
        wrap_info = payload.get("wrap_info")
        if not isinstance(wrap_info, Mapping) or not isinstance(wrap_info.get("token"), str):
            raise SecretIdentityRefused("OpenBao wrapped SecretID response missing wrapping token")
        wrap_accessor = wrap_info.get("accessor")
        wrapped_accessor = wrap_info.get("wrapped_accessor")
        return (
            SecretZeroPayload(
                seat_id=request.seat_id,
                requester_seat_id=request.requester_seat_id,
                role_name=request.role_name,
                auth_mount=request.auth_mount,
                role_id=role_id,
                wrapping_token=wrap_info["token"],
                wrap_expires_at=_iso(now + timedelta(seconds=request.wrap_ttl_seconds)),
                wrap_accessor_ref=wrap_accessor if isinstance(wrap_accessor, str) else None,
            ),
            wrapped_accessor if isinstance(wrapped_accessor, str) else None,
        )

    def _deliver_secret_zero(
        self,
        target_ref: str,
        payload: SecretZeroPayload,
        *,
        delivery: str,
    ) -> str:
        assert self._secret_zero_deliverer is not None
        try:
            delivery_ref = self._secret_zero_deliverer(target_ref, payload)
        except Exception:
            raise SecretMaterializationError(
                "secret-zero delivery failed; payload value redacted"
            ) from None
        if not isinstance(delivery_ref, str):
            raise SecretMaterializationError("secret-zero deliverer returned an empty delivery ref")
        delivery_ref = _normalize_secret_zero_delivery_ref(delivery_ref)
        if not delivery_ref:
            raise SecretMaterializationError("secret-zero deliverer returned an empty delivery ref")
        if delivery_ref in {payload.role_id, payload.wrapping_token}:
            raise SecretMaterializationError("secret-zero deliverer returned a raw credential as delivery ref")
        if not _secret_zero_ref_scheme_ok(delivery_ref, delivery):
            raise SecretMaterializationError(
                "secret-zero deliverer returned a delivery ref whose scheme "
                "is not allowed or does not match delivery"
            )
        return delivery_ref


def _env_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_explicit_true(value: str | None, *, name: str) -> bool:
    if value is None or not value.strip():
        return False
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SecretIdentityRefused(
        f"{name} must be one of: 1, true, yes, on, 0, false, no, off"
    )


def _matches_openbao_approval_wall_ref(ref: SecretRef, *, kv_mount: str) -> bool:
    return (
        ref.backend == "openbao"
        and ref.mount == kv_mount
        and ref.path == _OPENBAO_APPROVAL_WALL_PATH
        and ref.field == _OPENBAO_APPROVAL_WALL_FIELD
        and ref.purpose == _OPENBAO_APPROVAL_WALL_PURPOSE
        and ref.owner_ref == _OPENBAO_APPROVAL_WALL_OWNER_REF
    )


def _parse_openbao_allowed_ref(raw_ref: str, *, kv_mount: str) -> SecretRef:
    parts: dict[str, str] = {}
    for part in raw_ref.split(";"):
        item = part.strip()
        if not item:
            raise SecretIdentityRefused(
                "CE_OPENBAO_ALLOWED_REFS contains an empty SecretRef field"
            )
        key, separator, value = item.partition("=")
        if not separator or not key.strip() or not value.strip():
            raise SecretIdentityRefused(
                "CE_OPENBAO_ALLOWED_REFS entries must use key=value SecretRef fields"
            )
        parts[key.strip()] = value.strip()

    required = {"path", "field", "purpose", "owner_ref", "policy_sha"}
    missing = sorted(required - set(parts))
    if missing:
        raise SecretIdentityRefused(
            "CE_OPENBAO_ALLOWED_REFS SecretRef missing fields: " + ", ".join(missing)
        )
    version: int | None
    raw_version = parts.get("version")
    if raw_version in (None, ""):
        version = None
    else:
        try:
            version = int(raw_version)
        except ValueError:
            raise SecretIdentityRefused(
                "CE_OPENBAO_ALLOWED_REFS SecretRef version must be an integer"
            ) from None

    ref = SecretRef(
        backend=parts.get("backend", "openbao"),
        mount=parts.get("mount", kv_mount),
        path=parts["path"],
        field=parts["field"],
        version=version,
        purpose=parts["purpose"],
        owner_ref=parts["owner_ref"],
        policy_sha=parts["policy_sha"],
    )
    validate_secret_ref(ref, backend_key="openbao", kv_mount=kv_mount)
    return ref


def _openbao_allowed_refs_from_env(
    environ: Mapping[str, str],
    *,
    kv_mount: str,
) -> set[SecretRef]:
    raw_allowed_refs = environ.get("CE_OPENBAO_ALLOWED_REFS")
    if raw_allowed_refs is None:
        return set()
    if not raw_allowed_refs.strip():
        return set()
    refs = set()
    for entry in raw_allowed_refs.split(","):
        if not entry.strip():
            raise SecretIdentityRefused(
                "CE_OPENBAO_ALLOWED_REFS contains an empty SecretRef entry"
            )
        refs.add(_parse_openbao_allowed_ref(entry, kv_mount=kv_mount))
    return refs


def _openbao_backend_from_env() -> OpenBaoSecretIdentityBackend:
    environ = os.environ
    address = environ.get("BAO_ADDR") or environ.get("OPENBAO_ADDR") or ""
    token_name = "BAO_TOKEN" if "BAO_TOKEN" in environ else "OPENBAO_TOKEN"
    kv_mount = environ.get("CE_OPENBAO_KV_MOUNT") or environ.get("OPENBAO_KV_MOUNT") or "ce-kv"
    verify_tls = _env_bool(
        environ.get("CE_OPENBAO_VERIFY_TLS") or environ.get("OPENBAO_VERIFY_TLS"),
        default=True,
    )
    ca_bundle = environ.get("BAO_CACERT") or environ.get("OPENBAO_CACERT")
    allow_unrestricted_refs = _env_explicit_true(
        environ.get("CE_OPENBAO_ALLOW_UNRESTRICTED_REFS"),
        name="CE_OPENBAO_ALLOW_UNRESTRICTED_REFS",
    )
    raw_allowed_refs = environ.get("CE_OPENBAO_ALLOWED_REFS")
    allowed_refs = (
        None
        if allow_unrestricted_refs
        else _openbao_allowed_refs_from_env(environ, kv_mount=kv_mount)
    )
    allowed_ref_predicates: tuple[_RefPredicate, ...] = ()
    if not allow_unrestricted_refs and raw_allowed_refs is None:
        allowed_ref_predicates = (
            lambda ref: _matches_openbao_approval_wall_ref(ref, kv_mount=kv_mount),
        )
    if allow_unrestricted_refs and raw_allowed_refs:
        raise SecretIdentityRefused(
            "CE_OPENBAO_ALLOW_UNRESTRICTED_REFS cannot be combined with CE_OPENBAO_ALLOWED_REFS"
        )

    from .openbao_p3 import OpenBaoHttpConfig, make_openbao_http_runner

    config = OpenBaoConfig(
        address=address,
        token_supplier=lambda: environ.get(token_name, ""),
        kv_mount=kv_mount,
        verify_tls=verify_tls,
    )
    runner = make_openbao_http_runner(
        OpenBaoHttpConfig(
            address=address,
            verify_tls=verify_tls,
            ca_bundle=ca_bundle,
        )
    )
    return OpenBaoSecretIdentityBackend(
        config,
        runner=runner,
        allowed_refs=allowed_refs,
        allowed_ref_predicates=allowed_ref_predicates,
        allow_unrestricted_refs=allow_unrestricted_refs,
    )


register_backend("openbao", _openbao_backend_from_env)
