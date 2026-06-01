"""Connector runtime (``ce connector``): read-only (G2.005.1/.3) + write (G2.005.2).

Turns the merged G2.005.0 connector substrate (``checks/connector_substrate.py`` +
``schemas/connector.schema.yaml`` + ``schemas/mission-brief.schema.yaml``) into a
local, daemonless ``ce connector`` surface. G2.005.1 added **read-only** source-host
access (``verify``/``plan``/``fetch``); G2.005.2 adds the **write** path
(``write-plan``/``submit``) bounded to the non-privileged ``tracker_mirror`` verb set
and executed only under CE ``operating_mode: strict``; G2.005.3 adds **read-only
tracker** adapters (Jira + GitLab, REST) selected by a runtime ``provider`` (default
``github``) — Linear/GraphQL and tracker writes are deferred.

Read floors (enforced before any request):

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

Write floors (G2.005.2; enforced before any request):

* **CE ``operating_mode: strict`` only.** A write executes only when BOTH the
  connector and the Mission-Brief carry ``operating_mode: strict``; ``auto`` and
  ``transcendence`` are refused (:class:`ModeRefused`). This is the autonomy mode
  the gate enforces, distinct from the batch strict-mode governance cadence.
* **``tracker_mirror``-bounded; non-privileged.** Only the bounded write verbs
  ``issue-create``/``issue-update``/``pr-comment`` are permitted; a ``read_only``
  connector/brief routed to the write path is refused (:class:`ReadOnlyRefused`),
  any verb outside the set is refused (``G2-CONN-SCOPE``), and the Mission-Brief
  must declare the ``tracker_mirror`` mutation class.
* **Credential REQUIRED by reference.** Unlike reads, a write REQUIRES a present
  credential resolved by reference; an absent/``none`` credential fails closed
  before any request (``G2-CONN-CREDENTIAL-MISSING``). The value is never stored,
  printed, logged, or committed, and never appears in a write-receipt.
* **Network only through an injectable seam.** The default
  :class:`UrllibGitHubWriteClient` (``POST`` for ``issue-create``/``pr-comment``,
  ``PATCH`` for ``issue-update``) reaches the network only via an injectable
  ``opener``; tests inject a fake opener so the suite is network-free, and both it
  and :class:`NullWriteClient` fail closed offline. One bounded mutation per
  ``submit`` (no batching, no auto-retry that could double-write).

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
# G2.005.3 tracker read providers (REST). Jira Cloud is per-tenant, so its default is a
# placeholder; real use passes `--base-url`. GitLab SaaS has a fixed API root.
DEFAULT_GITLAB_API_BASE = "https://gitlab.com/api/v4"
DEFAULT_JIRA_API_BASE = "https://example.atlassian.net/rest/api/3"
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


class ModeRefused(ConnectorRuntimeError):
    """A write was requested under a non-strict CE operating_mode (G2.005.2 is strict-only)."""

    code = "G2-CONN-MODE-REFUSED"


class ReadOnlyRefused(ConnectorRuntimeError):
    """A read_only-scope connector/brief was routed to the write path (use ce connector fetch)."""

    code = "G2-CONN-READONLY-REFUSED"


class ProviderError(ConnectorRuntimeError):
    """An unknown connector provider was requested (G2.005.3 supports github/jira/gitlab)."""

    code = "G2-CONN-PROVIDER"


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

    def auth_header_for(self, *, header: str = "Authorization", scheme: str = "Bearer") -> dict[str, str]:
        """Provider-specific auth header for request construction only (G2.005.3).

        ``scheme`` empty or ``"raw"`` sets the bare value (e.g. GitLab ``PRIVATE-TOKEN``);
        otherwise ``{header: "{scheme} {value}"}``. Like :meth:`auth_header`, the value
        is used only to build the request and is never logged or returned.
        """
        if self.present and self._value:
            if not scheme or scheme == "raw":
                return {header: self._value}
            return {header: f"{scheme} {self._value}"}
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
# G2.005.3 tracker read adapters (REST: Jira + GitLab) — same injectable seam
# ---------------------------------------------------------------------------


def _rest_get(opener: Opener, url: str, headers: dict[str, str]) -> ReadResponse:
    """Shared GET over the injectable opener; fails closed on transport / bad JSON."""
    request = urllib.request.Request(url, method="GET", headers=headers)
    try:
        response = opener(request)
        raw = response.read()
        status = getattr(response, "status", None) or response.getcode()
    except (urllib.error.URLError, OSError) as exc:
        raise ConnectorNetworkError(f"read request failed (fail-closed): {exc}") from exc
    try:
        body = json.loads(raw.decode("utf-8")) if raw else None
    except (ValueError, UnicodeDecodeError) as exc:
        raise ConnectorNetworkError(f"read response was not valid JSON: {exc}") from exc
    return ReadResponse(status=int(status), body=body)


class UrllibJiraReadClient:
    """Read-only Jira (Cloud) REST adapter. GET only; no write method exists.

    Auth is a Bearer header derived from the resolved credential (Jira OAuth 2.0 /
    bearer token); the per-tenant base is supplied via ``base_url``. Reaches the
    network only via the injected ``opener``; fails closed offline (``G2-CONN-NETWORK``).
    """

    name = "urllib-jira"

    def __init__(self, *, base_url: str = DEFAULT_JIRA_API_BASE, opener: Opener | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._opener = opener or _default_opener()

    def get(self, resource: str, *, credential: CredentialHandle) -> ReadResponse:
        url = f"{self.base_url}/{str(resource).lstrip('/')}"
        headers = {"Accept": "application/json", "User-Agent": "creator-engine-ce-connector"}
        headers.update(credential.auth_header())  # Bearer; constructed here, never logged
        return _rest_get(self._opener, url, headers)


class UrllibGitLabReadClient:
    """Read-only GitLab REST (``/api/v4``) adapter. GET only; no write method exists.

    Auth is GitLab's native ``PRIVATE-TOKEN`` header derived from the resolved
    credential. Reaches the network only via the injected ``opener``; fails closed
    offline (``G2-CONN-NETWORK``).
    """

    name = "urllib-gitlab"

    def __init__(self, *, base_url: str = DEFAULT_GITLAB_API_BASE, opener: Opener | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._opener = opener or _default_opener()

    def get(self, resource: str, *, credential: CredentialHandle) -> ReadResponse:
        url = f"{self.base_url}/{str(resource).lstrip('/')}"
        headers = {"Accept": "application/json", "User-Agent": "creator-engine-ce-connector"}
        headers.update(credential.auth_header_for(header="PRIVATE-TOKEN", scheme="raw"))  # never logged
        return _rest_get(self._opener, url, headers)


# Provider registry for the default read adapter. `github` reproduces the G2.005.1
# behavior exactly; `jira`/`gitlab` are the G2.005.3 read-only tracker adapters.
PROVIDER_READ_CLIENTS: dict[str, type] = {
    "github": UrllibGitHubReadClient,
    "jira": UrllibJiraReadClient,
    "gitlab": UrllibGitLabReadClient,
}
DEFAULT_PROVIDER = "github"


def _read_client_for(provider: str, *, base_url: str | None, opener: Opener | None) -> ReadClient:
    """Select the default read adapter for ``provider``; unknown provider fails closed."""
    key = str(provider or DEFAULT_PROVIDER).strip().lower()
    adapter_cls = PROVIDER_READ_CLIENTS.get(key)
    if adapter_cls is None:
        raise ProviderError(f"unknown provider {provider!r}; supported: {sorted(PROVIDER_READ_CLIENTS)}")
    kwargs: dict[str, Any] = {"opener": opener}
    if base_url is not None:
        kwargs["base_url"] = base_url
    return adapter_cls(**kwargs)


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
    base_url: str | None = None,
    provider: str = DEFAULT_PROVIDER,
) -> ReadReceipt:
    """Execute one read-only GET via the read client and return a redaction-safe receipt.

    Refuses before any request on a write scope / non-read verb / missing read
    plan. The credential is resolved by reference and used only to build the
    request. If no client is given, the default adapter for ``provider``
    (``github``/``jira``/``gitlab``, default ``github``) is selected from
    :data:`PROVIDER_READ_CLIENTS` (with the injected ``opener`` when provided, and
    ``base_url`` overriding the provider default); an unknown provider fails closed
    (``G2-CONN-PROVIDER``) and offline/transport failures fail closed.
    """
    connector = load_connector(connector_path)
    mission_brief = load_mission_brief(mission_brief_path)
    read_plan = build_read_plan(connector, mission_brief)  # raises on write/scope before any request
    if not isinstance(resource, str) or not resource.strip():
        raise ConnectorScopeError("fetch requires a non-empty read resource path")
    credential = resolve_credential(connector)
    active_client = client or _read_client_for(provider, base_url=base_url, opener=opener)
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


# ===========================================================================
# G2.005.2 — write path (strict operating_mode; tracker_mirror-bounded)
# ===========================================================================

STRICT_MODE = "strict"
WRITE_RECEIPT_KIND = "connector-write-receipt"

# Bounded tracker_mirror write verbs → HTTP method. The adapter exposes exactly
# these and nothing else; an unknown verb never reaches a request.
WRITE_METHODS = {"issue-create": "POST", "issue-update": "PATCH", "pr-comment": "POST"}


# ---------------------------------------------------------------------------
# Write plan (offline; strict-mode + tracker_mirror enforcement)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WritePlan:
    connector_id: str
    connector_kind: str
    provider_class: str
    capability_scope: str
    write_verbs: tuple[str, ...]
    operating_mode: str
    assignment_ref: str
    credential_ref_name: str


def build_write_plan(connector: dict[str, Any], mission_brief: dict[str, Any]) -> WritePlan:
    """Build a bounded write plan, refusing before any request.

    Enforces (in order): a ``write`` capability scope (a ``read_only`` connector is
    refused and routed back to the read runtime); verbs bounded to the
    ``tracker_mirror`` set; CE ``operating_mode: strict`` on BOTH the connector and
    the Mission-Brief; a Mission-Brief ``write`` capability scope that declares the
    ``tracker_mirror`` mutation class. No privileged verb/class can reach here (the
    G2.005.0 validator already rejects them on load).
    """
    cap = connector.get("capability") if isinstance(connector.get("capability"), dict) else {}
    scope = conn_check._normalize_token(cap.get("scope", ""))
    if scope == "read_only":
        raise ReadOnlyRefused(
            "the write runtime requires a write-scope connector; a read_only connector is refused "
            "(use `ce connector fetch`)"
        )
    if scope != "write":
        raise ConnectorValidationError(f"connector capability.scope must be 'write' for the write runtime, got {scope!r}")
    verbs = cap.get("verbs") if isinstance(cap.get("verbs"), list) else []
    if not verbs:
        raise ConnectorScopeError("write connector declares no capability verbs")
    for v in verbs:
        if str(v) not in conn_check.TRACKER_MIRROR_VERBS:
            raise ConnectorScopeError(
                f"verb {v!r} is not a tracker_mirror write verb; the write runtime accepts only "
                f"{sorted(conn_check.TRACKER_MIRROR_VERBS)}"
            )
    conn_mode = conn_check._normalize_token(connector.get("operating_mode", ""))
    if conn_mode != STRICT_MODE:
        raise ModeRefused(
            f"connector operating_mode must be {STRICT_MODE!r} for the write runtime; "
            f"{conn_mode!r} (auto/transcendence) is refused"
        )
    mb_scope = conn_check._normalize_token(mission_brief.get("capability_scope", ""))
    if mb_scope == "read_only":
        raise ReadOnlyRefused("Mission-Brief capability_scope is read_only; the write runtime is refused")
    if mb_scope != "write":
        raise ConnectorValidationError(f"Mission-Brief capability_scope must be 'write' for the write runtime, got {mb_scope!r}")
    mb_mode = conn_check._normalize_token(mission_brief.get("operating_mode", ""))
    if mb_mode != STRICT_MODE:
        raise ModeRefused(
            f"Mission-Brief operating_mode must be {STRICT_MODE!r} for the write runtime; "
            f"{mb_mode!r} (auto/transcendence) is refused"
        )
    classes = mission_brief.get("declared_mutation_classes")
    classes = classes if isinstance(classes, list) else []
    if "tracker_mirror" not in {conn_check._normalize_token(c) for c in classes}:
        raise ConnectorScopeError("Mission-Brief does not declare the tracker_mirror mutation class; write refused")
    cred = connector.get("credential_ref") if isinstance(connector.get("credential_ref"), dict) else {}
    return WritePlan(
        connector_id=str(connector.get("connector_id")),
        connector_kind=str(connector.get("connector_kind")),
        provider_class=str(connector.get("provider_class")),
        capability_scope=scope,
        write_verbs=tuple(str(v) for v in verbs),
        operating_mode=conn_mode,
        assignment_ref=str(mission_brief.get("assignment_ref")),
        credential_ref_name=str(cred.get("ref_name", "")),
    )


# ---------------------------------------------------------------------------
# Write client seam (injectable; default urllib GitHub adapter, network-guarded)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WriteResponse:
    status: int
    body: Any


class WriteClient(Protocol):
    def submit(self, verb: str, resource: str, payload: dict[str, Any], *, credential: CredentialHandle) -> WriteResponse: ...


class NullWriteClient:
    """Fails closed: used when no client is provided so `submit` never silently no-ops."""

    name = "null"

    def submit(self, verb: str, resource: str, payload: dict[str, Any], *, credential: CredentialHandle) -> WriteResponse:
        raise ConnectorNetworkError("no write client configured; the write runtime fails closed offline")


class UrllibGitHubWriteClient:
    """Default write adapter over stdlib urllib. Bounded to the tracker_mirror verbs.

    ``POST`` for ``issue-create``/``pr-comment``, ``PATCH`` for ``issue-update``; no
    other method is constructed. A present credential is REQUIRED (anonymous writes
    fail closed before any request). The literal network call goes through the
    injected ``opener`` (default :func:`urllib.request.urlopen`), so tests inject a
    fake opener and never touch the network. Any transport error fails closed with
    ``G2-CONN-NETWORK``.
    """

    name = "urllib-github"

    def __init__(self, *, base_url: str = DEFAULT_GITHUB_API_BASE, opener: Opener | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._opener = opener or _default_opener()

    def submit(self, verb: str, resource: str, payload: dict[str, Any], *, credential: CredentialHandle) -> WriteResponse:
        method = WRITE_METHODS.get(str(verb))
        if method is None:
            raise ConnectorScopeError(f"verb {verb!r} is not a tracker_mirror write verb")
        if not credential.present:  # defense-in-depth; submit() already fails closed before here
            raise CredentialMissing("a write requires a present credential; anonymous/absent fails closed")
        url = f"{self.base_url}/{str(resource).lstrip('/')}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "creator-engine-ce-connector",
        }
        headers.update(credential.auth_header())  # constructed here; never logged
        data = json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(url, method=method, headers=headers, data=data)
        try:
            response = self._opener(request)
            raw = response.read()
            status = getattr(response, "status", None) or response.getcode()
        except (urllib.error.URLError, OSError) as exc:
            raise ConnectorNetworkError(f"write request failed (fail-closed): {exc}") from exc
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except (ValueError, UnicodeDecodeError) as exc:
            raise ConnectorNetworkError(f"write response was not valid JSON: {exc}") from exc
        return WriteResponse(status=int(status), body=body)


# ---------------------------------------------------------------------------
# Write-receipt (redaction-safe; never carries a credential)
# ---------------------------------------------------------------------------


def normalize_write_result(body: Any) -> dict[str, Any]:
    """Bounded, redaction-safe view of a write response object (no credential/secret)."""
    if isinstance(body, dict):
        return {k: body[k] for k in _NORMALIZED_FIELDS if k in body}
    return {}


@dataclass(frozen=True)
class WriteReceipt:
    kind: str
    schema_version: str
    connector_id: str
    assignment_ref: str
    verb: str
    resource: str
    operating_mode: str
    credential_ref_name: str
    status: int
    result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "connector_id": self.connector_id,
            "assignment_ref": self.assignment_ref,
            "verb": self.verb,
            "resource": self.resource,
            "operating_mode": self.operating_mode,
            "credential_ref_name": self.credential_ref_name,
            "status": self.status,
            "result": dict(self.result),
        }


# ---------------------------------------------------------------------------
# ce connector write-plan / submit
# ---------------------------------------------------------------------------


def write_plan(*, connector_path: Path | str, mission_brief_path: Path | str) -> WritePlan:
    """Validate a write-scope connector + Mission-Brief and confirm a write plan builds. Offline."""
    connector = load_connector(connector_path)
    mission_brief = load_mission_brief(mission_brief_path)
    return build_write_plan(connector, mission_brief)


def submit(
    *,
    connector_path: Path | str,
    mission_brief_path: Path | str,
    verb: str,
    resource: str,
    payload: dict[str, Any] | None = None,
    client: WriteClient | None = None,
    opener: Opener | None = None,
    base_url: str = DEFAULT_GITHUB_API_BASE,
) -> WriteReceipt:
    """Execute one bounded ``tracker_mirror`` write and return a redaction-safe receipt.

    Refuses before any request on a read_only scope, a non-strict ``operating_mode``,
    a verb outside the connector's bounded set, an empty resource, or an absent
    credential. The credential is resolved by reference and used only to build the
    request. If no client is given, the default urllib adapter is used (with the
    injected ``opener`` when provided); offline/transport failures fail closed.
    """
    connector = load_connector(connector_path)
    mission_brief = load_mission_brief(mission_brief_path)
    plan = build_write_plan(connector, mission_brief)  # raises on scope/mode/verbset before any request
    if str(verb) not in plan.write_verbs:
        raise ConnectorScopeError(
            f"verb {verb!r} is not permitted by this connector; allowed: {sorted(plan.write_verbs)}"
        )
    if not isinstance(resource, str) or not resource.strip():
        raise ConnectorScopeError("submit requires a non-empty write resource path")
    credential = resolve_credential(connector)
    if not credential.present:
        raise CredentialMissing(
            "a write requires a present credential resolved by reference; an absent/none credential fails closed"
        )
    active_client = client or UrllibGitHubWriteClient(base_url=base_url, opener=opener)
    response = active_client.submit(str(verb), resource, payload or {}, credential=credential)
    return WriteReceipt(
        kind=WRITE_RECEIPT_KIND,
        schema_version=SCHEMA_VERSION,
        connector_id=plan.connector_id,
        assignment_ref=plan.assignment_ref,
        verb=str(verb),
        resource=resource,
        operating_mode=plan.operating_mode,
        credential_ref_name=plan.credential_ref_name,
        status=response.status,
        result=normalize_write_result(response.body),
    )
