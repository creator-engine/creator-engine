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
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol


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
_CapabilitySet = set[str] | frozenset[str] | tuple[str, ...]
_CapabilityPolicy = Mapping[SecretRef, _CapabilitySet]


def _ref_names_controller_key(ref: SecretRef) -> bool:
    fields = (ref.backend, ref.mount, ref.path, ref.field, ref.purpose, ref.owner_ref)
    return any(_CONTROLLER_KEY_RE.search(value) for value in fields)


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
    if not _POLICY_SHA_RE.fullmatch(request.secret_ref.policy_sha):
        raise SecretIdentityRefused("secret_ref.policy_sha must be a lowercase 64-hex digest")
    if not request.requested_capabilities:
        raise SecretIdentityRefused("requested_capabilities must not be empty")
    if any(
        not isinstance(capability, str) or not capability.strip()
        for capability in request.requested_capabilities
    ):
        raise SecretIdentityRefused(
            "requested_capabilities must contain non-empty capability names"
        )
    if request.secret_ref.version is not None and request.secret_ref.version <= 0:
        raise SecretIdentityRefused("secret_ref.version must be positive when set")
    if backend_key is not None and request.secret_ref.backend != backend_key:
        raise SecretIdentityRefused(
            f"secret_ref backend {request.secret_ref.backend!r} is not bound to {backend_key!r}"
        )
    if kv_mount is not None and request.secret_ref.mount != kv_mount:
        raise SecretIdentityRefused(
            f"secret_ref mount {request.secret_ref.mount!r} is not bound to configured mount {kv_mount!r}"
        )
    if _ref_names_controller_key(request.secret_ref):
        raise SecretIdentityRefused("controller-key secret classes are forbidden")


def _validate_runtime_policy_binding(
    request: SecretRequest,
    *,
    allowed_refs: set[SecretRef],
    allowed_capabilities: Mapping[SecretRef, frozenset[str]],
) -> None:
    if request.secret_ref not in allowed_refs:
        raise SecretIdentityRefused(
            f"secret_ref {request.secret_ref.mount}/{request.secret_ref.path} is not allowed"
        )
    requested = frozenset(request.requested_capabilities)
    allowed = allowed_capabilities.get(request.secret_ref, frozenset())
    if not requested <= allowed:
        denied = ", ".join(sorted(requested - allowed)) or "(none)"
        raise SecretIdentityRefused(
            f"requested capabilities are not allowed by policy: {denied}"
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
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._identities = dict(identities or {})
        self._allowed_refs = set(allowed_refs or set())
        self._allowed_capabilities = _normalize_allowed_capabilities(
            self._allowed_refs, allowed_capabilities
        )
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

    def __repr__(self) -> str:
        json_ref = "<redacted>" if self.json is not None else None
        return (
            f"OpenBaoRequest(method={self.method!r}, path={self.path!r}, "
            f"json={json_ref})"
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
        allowed_refs: set[SecretRef] | None = None,
        allowed_capabilities: _CapabilityPolicy | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._config = config
        self._runner = runner
        self._materializer = materializer or (lambda _target_ref, _value: None)
        self._allowed_refs = set(allowed_refs or set())
        self._allowed_capabilities = _normalize_allowed_capabilities(
            self._allowed_refs, allowed_capabilities
        )
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
        _validate_runtime_policy_binding(
            request,
            allowed_refs=self._allowed_refs,
            allowed_capabilities=self._allowed_capabilities,
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

    def materialize(self, grant: SecretGrant, target_ref: str) -> SecretGrant:
        if grant.revoked_at is not None:
            raise SecretIdentityRefused(f"grant {grant.grant_id!r} is already revoked")
        value = self._read_secret_field(grant.secret_ref)
        materializer_error: SecretMaterializationError | None = None
        try:
            self._materializer(target_ref, value)
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
        self, method: str, path: str, json_body: Mapping[str, Any] | None = None
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
        request = OpenBaoRequest(method=method, path=path, token=token, json=json_body)
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
