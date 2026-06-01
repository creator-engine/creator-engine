"""G2.005.1 GitHub connector read-only runtime (``ce connector``).

Turns the merged G2.005.0 connector substrate (``checks/connector_substrate.py`` +
``schemas/connector.schema.yaml`` + ``schemas/mission-brief.schema.yaml``) into a
local, daemonless ``ce connector`` surface for **read-only** source-host access.

Floors (enforced before any request):

* **Read-only only.** Only GET reads are performed; a `write` capability scope or
  any non-read verb is refused (writes are G2.005.2). The adapter exposes no write.
* **Credential by reference.** The credential is resolved from
  ``credential_ref`` (env var name) at call time, used only to build the request
  Authorization header, and is NEVER stored in a record, printed, logged, or
  committed. ``CredentialHandle`` masks its value in ``repr``.
* **Network only through an injectable seam.** The default
  :class:`UrllibGitHubReadClient` reaches the network only via an injectable
  ``opener``; tests inject a fake opener so the suite is network-free, and the
  default fails closed (``G2-CONN-NETWORK``) when offline or when no client is
  given (:class:`NullReadClient`).
* **Reuse the landed validator.** Connector descriptors and Mission-Briefs are
  validated via the G2.005.0 ``connector_substrate`` check; this runtime imports no
  CE-event/PCL/distributed-identity code.

Prose contract: ``docs/operations/CONNECTOR_PROTOCOL.md``.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .checks import connector_substrate as conn_check
from .loader import LoaderError, load_yaml

DEFAULT_GITHUB_API_BASE = "https://api.github.com"
PROSE_CONTRACT = "docs/operations/CONNECTOR_PROTOCOL.md"
RECEIPT_KIND = "connector-read-receipt"
SCHEMA_VERSION = "1"

# Bounded set of response fields a read-receipt may carry (redaction-safe; never a
# credential or token). Anything else is dropped during normalization.
_NORMALIZED_FIELDS = ("id", "number", "title", "state", "html_url", "name", "full_name", "updated_at")


# ---------------------------------------------------------------------------
# Errors (stable codes; all refusals raise BEFORE any request)
# ---------------------------------------------------------------------------


class ConnectorRuntimeError(Exception):
    code = "G2-CONN-ERROR"


class ConnectorValidationError(ConnectorRuntimeError):
    code = "G2-CONN-VALIDATION"


class WriteRefused(ConnectorRuntimeError):
    code = "G2-CONN-WRITE-REFUSED"


class ConnectorScopeError(ConnectorRuntimeError):
    code = "G2-CONN-SCOPE"


class CredentialMissing(ConnectorRuntimeError):
    code = "G2-CONN-CREDENTIAL-MISSING"


class ConnectorNetworkError(ConnectorRuntimeError):
    code = "G2-CONN-NETWORK"


# ---------------------------------------------------------------------------
# Credential handle — resolved BY REFERENCE; value never serialized/printed
# ---------------------------------------------------------------------------


@dataclass
class CredentialHandle:
    present: bool
    ref_kind: str
    ref_name: str
    _value: str | None = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:  # never expose the value
        return f"CredentialHandle(ref_kind={self.ref_kind!r}, ref_name={self.ref_name!r}, present={self.present})"

    __str__ = __repr__

    def auth_header(self) -> dict[str, str]:
        """Authorization header for request construction only. Never logged/returned to the user."""
        if self.present and self._value:
            return {"Authorization": f"Bearer {self._value}"}
        return {}


def resolve_credential(connector: dict[str, Any]) -> CredentialHandle:
    """Resolve the credential reference WITHOUT exposing the value.

    `none` → no credential (anonymous read). `env_var_name` → read the named env
    var at call time. `secret_manager_ref` → not integrated in this gate; resolves
    as absent (fetch fails closed). The raw value, if any, is held only in the
    handle for request construction and is never serialized.
    """
    cred = connector.get("credential_ref")
    if not isinstance(cred, dict):
        raise ConnectorValidationError("connector credential_ref must be a {ref_kind, ref_name} reference")
    ref_kind = str(cred.get("ref_kind"))
    ref_name = str(cred.get("ref_name"))
    if ref_kind == "none":
        return CredentialHandle(present=False, ref_kind=ref_kind, ref_name=ref_name)
    if ref_kind == "env_var_name":
        value = os.environ.get(ref_name)
        return CredentialHandle(present=bool(value), ref_kind=ref_kind, ref_name=ref_name, _value=value)
    # secret_manager_ref and any other kind: by-reference only; resolution deferred.
    return CredentialHandle(present=False, ref_kind=ref_kind, ref_name=ref_name)


# ---------------------------------------------------------------------------
# Read plan (offline; read-only enforcement)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadPlan:
    connector_id: str
    connector_kind: str
    provider_class: str
    capability_scope: str
    read_verbs: tuple[str, ...]
    assignment_ref: str
    credential_ref_name: str


def build_read_plan(connector: dict[str, Any], mission_brief: dict[str, Any]) -> ReadPlan:
    cap = connector.get("capability") if isinstance(connector.get("capability"), dict) else {}
    scope = conn_check._normalize_token(cap.get("scope", ""))
    if scope != "read_only":
        raise WriteRefused(
            "G2.005.1 is a read-only runtime; a connector with capability.scope != read_only is refused "
            "(write is G2.005.2)"
        )
    verbs = cap.get("verbs") if isinstance(cap.get("verbs"), list) else []
    for v in verbs:
        if str(v) not in conn_check.READ_VERBS:
            raise ConnectorScopeError(f"verb {v!r} is not a read verb; read-only runtime accepts only {sorted(conn_check.READ_VERBS)}")
    mb_scope = conn_check._normalize_token(mission_brief.get("capability_scope", ""))
    if mb_scope != "read_only":
        raise WriteRefused("Mission-Brief capability_scope must be read_only for the read-only runtime")
    cred = connector.get("credential_ref") if isinstance(connector.get("credential_ref"), dict) else {}
    return ReadPlan(
        connector_id=str(connector.get("connector_id")),
        connector_kind=str(connector.get("connector_kind")),
        provider_class=str(connector.get("provider_class")),
        capability_scope=scope,
        read_verbs=tuple(str(v) for v in verbs),
        assignment_ref=str(mission_brief.get("assignment_ref")),
        credential_ref_name=str(cred.get("ref_name", "")),
    )


# ---------------------------------------------------------------------------
# Read client seam (injectable; default urllib GitHub adapter, network-guarded)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadResponse:
    status: int
    body: Any


Opener = Callable[[urllib.request.Request], Any]


class ReadClient(Protocol):
    def get(self, resource: str, *, credential: CredentialHandle) -> ReadResponse: ...


def _default_opener() -> Opener:
    # Indirection so tests can monkeypatch the opener without a network call.
    return urllib.request.urlopen


class NullReadClient:
    """Fails closed: used when no client is provided so `fetch` never silently no-ops."""

    name = "null"

    def get(self, resource: str, *, credential: CredentialHandle) -> ReadResponse:
        raise ConnectorNetworkError("no read client configured; the read-only runtime fails closed offline")


class UrllibGitHubReadClient:
    """Default read-only adapter over stdlib urllib. GET only; no write method exists.

    The literal network call goes through the injected ``opener`` (default
    :func:`urllib.request.urlopen`), so tests inject a fake opener and never touch
    the network. Any transport error fails closed with ``G2-CONN-NETWORK``.
    """

    name = "urllib-github"

    def __init__(self, *, base_url: str = DEFAULT_GITHUB_API_BASE, opener: Opener | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._opener = opener or _default_opener()

    def get(self, resource: str, *, credential: CredentialHandle) -> ReadResponse:
        url = f"{self.base_url}/{str(resource).lstrip('/')}"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "creator-engine-ce-connector"}
        headers.update(credential.auth_header())  # constructed here; never logged
        request = urllib.request.Request(url, method="GET", headers=headers)
        try:
            response = self._opener(request)
            raw = response.read()
            status = getattr(response, "status", None) or response.getcode()
        except (urllib.error.URLError, OSError) as exc:
            raise ConnectorNetworkError(f"read request failed (fail-closed): {exc}") from exc
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except (ValueError, UnicodeDecodeError) as exc:
            raise ConnectorNetworkError(f"read response was not valid JSON: {exc}") from exc
        return ReadResponse(status=int(status), body=body)


# ---------------------------------------------------------------------------
# Normalization + receipt (redaction-safe; never carries a credential)
# ---------------------------------------------------------------------------


def normalize_results(body: Any) -> list[dict[str, Any]]:
    items = body if isinstance(body, list) else [body] if isinstance(body, dict) else []
    out: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            out.append({k: item[k] for k in _NORMALIZED_FIELDS if k in item})
    return out


@dataclass(frozen=True)
class ReadReceipt:
    kind: str
    schema_version: str
    connector_id: str
    assignment_ref: str
    resource: str
    credential_ref_name: str
    status: int
    result_count: int
    results: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "connector_id": self.connector_id,
            "assignment_ref": self.assignment_ref,
            "resource": self.resource,
            "credential_ref_name": self.credential_ref_name,
            "status": self.status,
            "result_count": self.result_count,
            "results": list(self.results),
        }


# ---------------------------------------------------------------------------
# Loading + validation (reuse the landed G2.005.0 validator)
# ---------------------------------------------------------------------------


def _load_validated(path: Path | str, key: str, validate) -> dict[str, Any]:
    errors = validate(Path(path))
    if errors:
        raise ConnectorValidationError(
            f"{key} at {path} fails the G2.005.0 validator: " + "; ".join(e.format() for e in errors)
        )
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        raise ConnectorValidationError(str(exc)) from exc
    record = data.get(key) if isinstance(data, dict) else None
    if not isinstance(record, dict):
        raise ConnectorValidationError(f"{path} does not declare a {key} mapping")
    return record


def load_connector(path: Path | str) -> dict[str, Any]:
    return _load_validated(path, "connector", conn_check.validate_connector_file)


def load_mission_brief(path: Path | str) -> dict[str, Any]:
    return _load_validated(path, "mission_brief", conn_check.validate_mission_brief_file)


# ---------------------------------------------------------------------------
# ce connector verify / plan / fetch
# ---------------------------------------------------------------------------


def verify(*, connector_path: Path | str, mission_brief_path: Path | str) -> ReadPlan:
    """Validate a connector + Mission-Brief pair and confirm a read plan builds. Offline."""
    connector = load_connector(connector_path)
    mission_brief = load_mission_brief(mission_brief_path)
    return build_read_plan(connector, mission_brief)


def plan(*, connector_path: Path | str, mission_brief_path: Path | str) -> ReadPlan:
    """Alias of verify that emphasizes the read-plan artifact. Offline."""
    return verify(connector_path=connector_path, mission_brief_path=mission_brief_path)


def fetch(
    *,
    connector_path: Path | str,
    mission_brief_path: Path | str,
    resource: str,
    client: ReadClient | None = None,
    opener: Opener | None = None,
    base_url: str = DEFAULT_GITHUB_API_BASE,
) -> ReadReceipt:
    """Execute one read-only GET via the read client and return a redaction-safe receipt.

    Refuses before any request on a write scope / non-read verb / missing read
    plan. The credential is resolved by reference and used only to build the
    request. If no client is given, the default urllib adapter is used (with the
    injected ``opener`` when provided); offline/transport failures fail closed.
    """
    connector = load_connector(connector_path)
    mission_brief = load_mission_brief(mission_brief_path)
    read_plan = build_read_plan(connector, mission_brief)  # raises on write/scope before any request
    if not isinstance(resource, str) or not resource.strip():
        raise ConnectorScopeError("fetch requires a non-empty read resource path")
    credential = resolve_credential(connector)
    active_client = client or UrllibGitHubReadClient(base_url=base_url, opener=opener)
    response = active_client.get(resource, credential=credential)
    results = normalize_results(response.body)
    return ReadReceipt(
        kind=RECEIPT_KIND,
        schema_version=SCHEMA_VERSION,
        connector_id=read_plan.connector_id,
        assignment_ref=read_plan.assignment_ref,
        resource=resource,
        credential_ref_name=read_plan.credential_ref_name,
        status=response.status,
        result_count=len(results),
        results=tuple(results),
    )
