"""OpenBao Phase 3 deployment/bootstrap helpers (ce-ops#113).

This module implements the ratified B.1-B.5 P3 gate without provisioning shared
or production infrastructure. Production/controller-pilot work is represented as
explicit operator-required steps. Local/ephemeral tests can use the stdlib HTTP
runner against a disposable OpenBao process.

No function in this module imports validator checks or performs I/O on import.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .secret_identity import (
    OpenBaoConfig,
    OpenBaoRequest,
    OpenBaoResponse,
    OpenBaoRunner,
    SecretBackendTransportError,
    SecretIdentityError,
    SecretIdentityRefused,
    SecretRef,
)


class OperatorActionRequired(SecretIdentityRefused):
    """A P3 action is irreversible/operator-side and must not be executed here."""


_LOCAL_LOOPBACK_PREFIXES = ("http://127.", "http://localhost:", "https://127.", "https://localhost:")
_FORBIDDEN_GOVERNANCE_MARKERS = (
    "ce-root-v1",
    "signing/roots",
    "release-signing",
    "attestation",
    "ratification",
    "controller-key",
    "private-key-root",
)


@dataclass(frozen=True)
class OpenBaoDeploymentConfig:
    """Value-free P3 deployment posture; does not carry OpenBao tokens."""

    profile: str
    host_ref: str
    address: str
    ca_bundle_ref: str | None
    network_exposure: str
    allowed_secret_refs: tuple[SecretRef, ...]
    storage: str = "integrated"
    auth_method: str = "approle-response-wrapped"
    unseal_method: str = "shamir"
    backup_mode: str = "encrypted-snapshot-restore-tested"
    audit_fail_closed_probe: bool = True

    @classmethod
    def local_ephemeral(
        cls,
        *,
        address: str,
        allowed_secret_refs: tuple[SecretRef, ...],
    ) -> "OpenBaoDeploymentConfig":
        return cls(
            profile="local-ephemeral",
            host_ref="local-sandbox",
            address=address,
            ca_bundle_ref=None,
            network_exposure="local-loopback-only",
            allowed_secret_refs=allowed_secret_refs,
        )

    @classmethod
    def controller_pilot(
        cls,
        *,
        host_ref: str,
        address: str,
        ca_bundle_ref: str,
        allowed_secret_refs: tuple[SecretRef, ...],
    ) -> "OpenBaoDeploymentConfig":
        return cls(
            profile="controller-pilot",
            host_ref=host_ref,
            address=address,
            ca_bundle_ref=ca_bundle_ref,
            network_exposure="broker-network-only",
            allowed_secret_refs=allowed_secret_refs,
        )


@dataclass(frozen=True)
class OpenBaoDeploymentPlan:
    """A P3 plan split into local automation and operator-only actions."""

    profile: str
    ready_for_local_execution: bool
    automated_steps: tuple[str, ...]
    operator_required_steps: tuple[str, ...]
    record: Mapping[str, Any] = field(repr=False)

    def __repr__(self) -> str:
        return (
            f"OpenBaoDeploymentPlan(profile={self.profile!r}, "
            f"ready_for_local_execution={self.ready_for_local_execution!r}, "
            f"automated_steps={self.automated_steps!r}, "
            f"operator_required_steps={self.operator_required_steps!r}, "
            "record=<value-free>)"
        )

    __str__ = __repr__


def _ref_violates_p3_cotenancy(ref: SecretRef) -> bool:
    haystack = " ".join((ref.path, ref.field, ref.purpose, ref.owner_ref)).lower()
    return any(marker in haystack for marker in _FORBIDDEN_GOVERNANCE_MARKERS)


def _validate_deployment_config(config: OpenBaoDeploymentConfig) -> None:
    if config.storage != "integrated":
        raise SecretIdentityRefused("OpenBao P3 requires integrated storage")
    if config.auth_method != "approle-response-wrapped":
        raise SecretIdentityRefused("OpenBao P3 requires response-wrapped AppRole bootstrap")
    if config.unseal_method != "shamir":
        raise SecretIdentityRefused("OpenBao P3 requires Shamir unseal")
    if config.backup_mode != "encrypted-snapshot-restore-tested":
        raise SecretIdentityRefused("OpenBao P3 requires encrypted backup plus restore drill")
    if not config.audit_fail_closed_probe:
        raise SecretIdentityRefused("OpenBao P3 requires audit-fail-closed verification")
    for ref in config.allowed_secret_refs:
        if _ref_violates_p3_cotenancy(ref):
            raise SecretIdentityRefused(
                f"SecretRef {ref.mount}/{ref.path} is forbidden in the P3 runtime-token instance"
            )
    if config.profile == "local-ephemeral":
        if config.network_exposure != "local-loopback-only":
            raise SecretIdentityRefused("local OpenBao P3 tests must be loopback-only")
        if not config.address.startswith(_LOCAL_LOOPBACK_PREFIXES):
            raise SecretIdentityRefused("local OpenBao P3 address must be loopback-only")
        return
    if config.profile == "controller-pilot":
        if config.network_exposure != "broker-network-only":
            raise SecretIdentityRefused("controller OpenBao P3 must be broker-network-only")
        if not config.address.startswith("https://"):
            raise SecretIdentityRefused("controller OpenBao P3 must be TLS-only")
        if not config.ca_bundle_ref:
            raise SecretIdentityRefused("controller OpenBao P3 requires an explicit CA bundle ref")
        return
    raise SecretIdentityRefused(f"unsupported OpenBao P3 profile {config.profile!r}")


def build_p3_deployment_plan(config: OpenBaoDeploymentConfig) -> OpenBaoDeploymentPlan:
    """Build a P3 plan and flag irreversible Operator-side steps."""

    _validate_deployment_config(config)
    base_record: dict[str, Any] = {
        "profile": config.profile,
        "host_ref": config.host_ref,
        "address_ref": config.address,
        "secret_zero": {
            "method": "response-wrapped-approle",
            "steady_state_secretid_storage": "none",
            "operator_injection": "wrapping-token-at-broker-start",
        },
        "topology": {
            "storage": config.storage,
            "network_exposure": config.network_exposure,
            "auth_method": config.auth_method,
            "unseal_method": config.unseal_method,
        },
        "unseal": {
            "method": "shamir",
            "operator_only": True,
            "auto_unseal_deferred": True,
        },
        "backup_restore": {
            "mode": config.backup_mode,
            "encrypted_snapshot_required": True,
            "restore_test_required": True,
        },
        "emergency_revocation": {
            "operator_only": True,
            "steps": (
                "freeze-broker-issuance",
                "revoke-broker-tokens",
                "revoke-approle-secretids",
                "disable-broker-auth-mount-if-compromised",
                "revoke-dynamic-leases-and-github-installation-tokens",
                "rotate-imported-runtime-credentials-before-resume",
                "seal-openbao-on-host-compromise",
            ),
        },
        "cotenancy": {
            "allowed_refs": [
                f"{ref.mount}/{ref.path}:{ref.field}" for ref in config.allowed_secret_refs
            ],
            "governance_roots_allowed": False,
        },
        "audit": {"fail_closed_probe_required": True},
    }
    if config.profile == "local-ephemeral":
        return OpenBaoDeploymentPlan(
            profile=config.profile,
            ready_for_local_execution=True,
            automated_steps=(
                "start-local-openbao",
                "enable-file-audit-device",
                "configure-response-wrapped-approle",
                "run-audit-fail-closed-probe",
                "destroy-local-openbao",
            ),
            operator_required_steps=(),
            record=base_record,
        )
    return OpenBaoDeploymentPlan(
        profile=config.profile,
        ready_for_local_execution=False,
        automated_steps=("render-controller-runbook",),
        operator_required_steps=(
            "operator-provision-controller-vps",
            "operator-enable-tls-private-listener",
            "operator-unseal-shamir",
            "operator-inject-wrapping-token",
            "operator-backup-restore-drill",
            "operator-emergency-revocation-drill",
            "operator-ratify-production-cutover",
        ),
        record=base_record,
    )


@dataclass(frozen=True)
class WrappedAppRoleBootstrapConfig:
    """B.1 response-wrapped AppRole bootstrap input.

    Suppliers are callables so raw RoleID/wrapping token values are never present
    in the dataclass repr or record surfaces.
    """

    role_name: str
    role_id_supplier: Callable[[], str] = field(repr=False)
    wrapping_token_supplier: Callable[[], str] = field(repr=False)
    auth_mount: str = "approle"


@dataclass(frozen=True)
class OpenBaoBrokerSession:
    """In-memory broker session; token is intentionally repr-hidden."""

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
    ) -> OpenBaoConfig:
        return OpenBaoConfig(
            address=address,
            token_supplier=self.token_supplier,
            kv_mount=kv_mount,
            verify_tls=verify_tls,
        )


def _run_value_free(runner: OpenBaoRunner, request: OpenBaoRequest) -> OpenBaoResponse:
    try:
        return runner(request)
    except SecretIdentityError:
        raise
    except Exception:
        raise SecretBackendTransportError(
            "OpenBao bootstrap request failed; backend value redacted"
        )


def _expect_response_mapping(response: OpenBaoResponse, label: str) -> Mapping[str, Any]:
    if response.status < 200 or response.status >= 300 or not isinstance(response.json, Mapping):
        raise SecretIdentityRefused(f"OpenBao {label} failed with HTTP {response.status}")
    return response.json


def unwrap_wrapped_approle_secret_id(
    config: WrappedAppRoleBootstrapConfig,
    *,
    runner: OpenBaoRunner,
) -> OpenBaoBrokerSession:
    """Unwrap a one-use SecretID and log in as the broker AppRole."""

    wrapping_token = config.wrapping_token_supplier()
    role_id = config.role_id_supplier()
    if not wrapping_token or not role_id:
        raise SecretIdentityRefused("OpenBao AppRole bootstrap suppliers returned empty values")

    unwrap_response = _run_value_free(
        runner,
        OpenBaoRequest("POST", "/v1/sys/wrapping/unwrap", token=wrapping_token),
    )
    unwrap_payload = _expect_response_mapping(unwrap_response, "wrapping unwrap")
    unwrap_data = unwrap_payload.get("data")
    if not isinstance(unwrap_data, Mapping) or not isinstance(unwrap_data.get("secret_id"), str):
        raise SecretIdentityRefused("OpenBao wrapping unwrap response missing SecretID")
    secret_id = unwrap_data["secret_id"]
    secret_id_accessor = unwrap_data.get("secret_id_accessor")

    login_response = _run_value_free(
        runner,
        OpenBaoRequest(
            "POST",
            f"/v1/auth/{config.auth_mount}/login",
            token="",
            json={"role_id": role_id, "secret_id": secret_id},
        ),
    )
    secret_id = ""
    login_payload = _expect_response_mapping(login_response, "AppRole login")
    auth = login_payload.get("auth")
    if not isinstance(auth, Mapping) or not isinstance(auth.get("client_token"), str):
        raise SecretIdentityRefused("OpenBao AppRole login response missing broker token")
    lease_duration = auth.get("lease_duration")
    return OpenBaoBrokerSession(
        role_name=config.role_name,
        auth_mount=config.auth_mount,
        token=auth["client_token"],
        token_accessor_ref=auth.get("accessor") if isinstance(auth.get("accessor"), str) else None,
        secret_id_accessor_ref=secret_id_accessor if isinstance(secret_id_accessor, str) else None,
        lease_duration_seconds=lease_duration if isinstance(lease_duration, int) else None,
        audit_ref=f"openbao-bootstrap:{config.role_name}:{config.auth_mount}",
    )


HttpTransport = Callable[
    [str, str, Mapping[str, str], bytes | None, float, ssl.SSLContext | None],
    tuple[int, bytes],
]


@dataclass(frozen=True)
class OpenBaoHttpConfig:
    address: str
    timeout_seconds: float = 10.0
    verify_tls: bool = True
    ca_bundle: str | None = None


def _default_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float,
    ssl_context: ssl.SSLContext | None,
) -> tuple[int, bytes]:  # pragma: no cover - live path covered by integration tests
    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
        return response.status, response.read()


def make_openbao_http_runner(
    config: OpenBaoHttpConfig,
    *,
    transport: HttpTransport | None = None,
) -> OpenBaoRunner:
    """Return an injected-I/O runner for the existing OpenBao adapter."""

    base = config.address.rstrip("/")
    ssl_context: ssl.SSLContext | None = None
    if base.startswith("https://"):
        if config.verify_tls:
            ssl_context = ssl.create_default_context(cafile=config.ca_bundle)
        else:
            ssl_context = ssl._create_unverified_context()  # noqa: S323 - local dev opt-in only
    http_transport = transport or _default_transport

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        path = request.path if request.path.startswith("/") else f"/{request.path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if request.token:
            headers["X-Vault-Token"] = request.token
        body = None
        if request.json is not None:
            body = json.dumps(request.json, separators=(",", ":")).encode("utf-8")
        try:
            status, raw = http_transport(
                request.method,
                f"{base}{path}",
                headers,
                body,
                config.timeout_seconds,
                ssl_context,
            )
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
        except (urllib.error.URLError, OSError):
            raise SecretBackendTransportError(
                "OpenBao HTTP request failed; backend value redacted"
            )
        payload: Mapping[str, Any] | None = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                parsed = None
            if isinstance(parsed, Mapping):
                payload = parsed
        return OpenBaoResponse(status=status, json=payload)

    return runner


@dataclass(frozen=True)
class AuditFailClosedProbe:
    token_supplier: Callable[[], str] = field(repr=False)
    canary_path: str = "/v1/sys/health"


@dataclass(frozen=True)
class AuditFailClosedResult:
    before_status: int
    after_status: int
    fail_closed: bool
    audit_ref: str


def verify_audit_fail_closed(
    probe: AuditFailClosedProbe,
    *,
    runner: OpenBaoRunner,
    break_audit: Callable[[], None],
) -> AuditFailClosedResult:
    """Verify that a canary request fails once the audit sink is broken."""

    token = probe.token_supplier()
    if not token:
        raise SecretIdentityRefused("OpenBao audit probe token supplier returned an empty token")
    audit = runner(OpenBaoRequest("GET", "/v1/sys/audit", token=token))
    if audit.status != 200 or not audit.json:
        raise OperatorActionRequired("OpenBao audit device is not enabled for P3 verification")
    before = runner(OpenBaoRequest("GET", probe.canary_path, token=token))
    if before.status < 200 or before.status >= 300:
        raise SecretIdentityRefused(f"OpenBao audit canary failed before audit break: HTTP {before.status}")
    break_audit()
    after = runner(OpenBaoRequest("GET", probe.canary_path, token=token))
    return AuditFailClosedResult(
        before_status=before.status,
        after_status=after.status,
        fail_closed=after.status >= 400,
        audit_ref="openbao-audit-fail-closed-probe",
    )
