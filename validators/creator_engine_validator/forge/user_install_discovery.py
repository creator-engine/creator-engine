"""User-side install discovery via the GitHub OAuth device flow (ce-ops#157, S1).

The shared-App self-serve onboarding has NO App PEM on the user's disk. To learn which App
installation is the user's — without trusting a pasted, spoofable ``installation_id`` — the
user authenticates with the GitHub OAuth **device flow** and we list their installations:

1. :func:`request_device_code` — ``POST /login/device/code`` returns a ``user_code`` the user
   types at ``verification_uri`` plus the ``device_code`` + poll ``interval``.
2. :func:`discover_user_installation_id` polls ``POST /login/oauth/access_token`` (grant_type
   ``urn:ietf:params:oauth:grant-type:device_code``) until GitHub returns a ``ghu_`` user token,
   honouring the ``authorization_pending`` / ``slow_down`` back-off and failing closed on a hard
   error (``access_denied`` / ``expired_token`` / unknown). It then GETs ``/user/installations``
   with that token and returns the id of the installation whose ``account.login`` is the repo
   owner (case-insensitively) — fail-closed if the user controls no such installation.

Network only behind an injectable ``transport`` seam — identical in shape to
``forge.app_jwt_runner.Transport`` (``(method, url, headers, body) -> (status, text)``) — and an
injectable ``sleep`` so the poll back-off is deterministic in tests. Importing this module
performs no I/O and registers no validator check.

Secret hygiene: the ``ghu_`` user token lives in the ``Authorization: Bearer`` header and the
in-process flow ONLY — never the argv, a log / ``print`` / disk, or an exception (``redact_gh_stderr``
masks any token-shaped material the API echoes back into an error body).

Defensive only — proves the caller controls an installation before any mint; never offensive.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from ._redact import redact_gh_stderr

#: HTTPS transport seam: ``(method, url, headers, body) -> (status_code, response_body_text)``.
#: Identical to ``app_jwt_runner.Transport`` so one fake can drive every leg in a test.
Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, str]"]

_GITHUB = "https://github.com"
_API_ROOT = "https://api.github.com"
_API_VERSION = "2022-11-28"
_ACCEPT_API = "application/vnd.github+json"
_ACCEPT_JSON = "application/json"
_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
#: The OAuth scope a device-flow user token needs to list its own App installations.
_SCOPE = "read:user"
#: Default poll ceiling — a defensive backstop so a never-authorized flow fails closed rather
#: than spinning forever (device codes also expire server-side, but we never rely on that alone).
_DEFAULT_MAX_POLL_ATTEMPTS = 180


class DeviceFlowError(Exception):
    """The OAuth device flow failed (request / poll / hard error / timeout) — fail-closed."""


class UserInstallDiscoveryError(Exception):
    """The user controls no App installation for the repo owner — a fail-closed refusal."""


@dataclass(frozen=True)
class DeviceCodeGrant:
    """The user-facing device-flow grant. The ``device_code`` is the poll handle (secret-ish)."""

    device_code: str
    user_code: str
    verification_uri: str
    interval: int
    expires_in: int

    def __repr__(self) -> str:  # keep the device_code out of incidental log surfaces
        return (
            f"DeviceCodeGrant(user_code={self.user_code!r}, "
            f"verification_uri={self.verification_uri!r}, interval={self.interval}, "
            f"device_code=<redacted>)"
        )

    __str__ = __repr__


def _default_transport(  # pragma: no cover - the lone live HTTPS shell; tests inject a fake
    method: str, url: str, headers: dict[str, str], body: str | None
) -> tuple[int, str]:
    data = body.encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _form_body(fields: dict[str, str]) -> str:
    return urllib.parse.urlencode(fields)


def _parse_json(body: str) -> dict | None:
    try:
        parsed = json.loads(body or "")
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def request_device_code(
    client_id: str, *, transport: Transport | None = None
) -> DeviceCodeGrant:
    """``POST /login/device/code`` → a :class:`DeviceCodeGrant` (fail-closed).

    Raises :class:`DeviceFlowError` on a non-2xx, an unparseable body, or a response missing the
    ``device_code`` / ``user_code`` (a device flow we could not drive is a refusal, not a guess).
    """
    if not (client_id or "").strip():
        raise DeviceFlowError("client_id is required to start the device flow")
    _transport = transport or _default_transport
    headers = {"Accept": _ACCEPT_JSON, "Content-Type": "application/x-www-form-urlencoded"}
    status, body = _transport(
        "POST", f"{_GITHUB}/login/device/code", headers,
        _form_body({"client_id": client_id, "scope": _SCOPE}),
    )
    if not (200 <= status < 300):
        raise DeviceFlowError(
            f"device-code request failed (HTTP {status}): {redact_gh_stderr(body) or 'unknown error'}"
        )
    parsed = _parse_json(body)
    if parsed is None:
        raise DeviceFlowError("device-code response was not valid JSON")
    device_code = str(parsed.get("device_code") or "")
    user_code = str(parsed.get("user_code") or "")
    verification_uri = str(parsed.get("verification_uri") or "")
    if not device_code or not user_code:
        raise DeviceFlowError("device-code response missing device_code / user_code")
    try:
        interval = int(parsed.get("interval", 5))
    except (TypeError, ValueError):
        interval = 5
    try:
        expires_in = int(parsed.get("expires_in", 900))
    except (TypeError, ValueError):
        expires_in = 900
    return DeviceCodeGrant(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        interval=max(1, interval),
        expires_in=expires_in,
    )


def _poll_for_user_token(
    client_id: str,
    grant: DeviceCodeGrant,
    *,
    transport: Transport,
    sleep: Callable[[float], None],
    max_poll_attempts: int,
) -> str:
    """Poll the access-token endpoint until a ``ghu_`` token; honour back-off; fail-closed."""
    interval = max(1, grant.interval)
    headers = {"Accept": _ACCEPT_JSON, "Content-Type": "application/x-www-form-urlencoded"}
    fields = {
        "client_id": client_id,
        "device_code": grant.device_code,
        "grant_type": _DEVICE_GRANT,
    }
    for _attempt in range(max(1, max_poll_attempts)):
        sleep(interval)
        status, body = transport(
            "POST", f"{_GITHUB}/login/oauth/access_token", dict(headers), _form_body(fields)
        )
        parsed = _parse_json(body)
        if parsed is None:
            # transport/JSON hiccup: back off and retry (never leak the body)
            continue
        token = str(parsed.get("access_token") or "")
        if token:
            return token
        error = str(parsed.get("error") or "")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            try:
                interval = max(interval, int(parsed.get("interval", interval + 5)))
            except (TypeError, ValueError):
                interval += 5
            continue
        # access_denied / expired_token / unsupported_grant_type / anything else → fail closed.
        raise DeviceFlowError(
            f"device-flow authorization failed: {error or 'no access_token returned'}"
        )
    raise DeviceFlowError(
        f"device-flow authorization not completed after {max_poll_attempts} polls (fail-closed)"
    )


def _select_installation_for_owner(payload: object, owner: str) -> int:
    """Return the installation id whose ``account.login`` == ``owner`` (fail-closed)."""
    # ``GET /user/installations`` wraps the list in ``{"installations": [...]}``.
    entries: object
    if isinstance(payload, dict):
        entries = payload.get("installations")
    else:
        entries = payload
    if not isinstance(entries, list):
        raise UserInstallDiscoveryError("user installations response was not a list")
    target = owner.strip().lower()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        account = entry.get("account") or {}
        login = str(account.get("login") or "").strip().lower() if isinstance(account, dict) else ""
        if login == target and entry.get("id") is not None:
            try:
                iid = int(entry["id"])
            except (TypeError, ValueError):
                continue
            if iid > 0:
                return iid
    raise UserInstallDiscoveryError(
        f"the authenticated user controls no App installation for owner {owner!r} "
        "(install the App on that account/org first)"
    )


def discover_user_installation_id(
    client_id: str,
    *,
    repo: str,
    transport: Transport | None = None,
    sleep: Callable[[float], None] | None = None,
    max_poll_attempts: int = _DEFAULT_MAX_POLL_ATTEMPTS,
) -> int:
    """Drive the device flow + ``GET /user/installations`` → the install id for ``repo``'s owner.

    ``repo`` is ``owner/name``; the returned installation is the one whose account login matches
    ``owner`` — proving (via the user's own OAuth token, NOT a pasted id) that the caller
    controls it. Raises :class:`DeviceFlowError` on a flow failure and
    :class:`UserInstallDiscoveryError` when the user controls no matching installation. The
    ``ghu_`` user token never appears in any return value, log, or exception.
    """
    owner = (repo or "").split("/", 1)[0].strip()
    if not owner:
        raise UserInstallDiscoveryError("repo must be in owner/name form to discover an installation")
    _transport = transport or _default_transport
    _sleep = sleep or __import__("time").sleep

    grant = request_device_code(client_id, transport=_transport)
    user_token = _poll_for_user_token(
        client_id, grant, transport=_transport, sleep=_sleep, max_poll_attempts=max_poll_attempts
    )

    headers = {
        "Authorization": f"Bearer {user_token}",
        "Accept": _ACCEPT_API,
        "X-GitHub-Api-Version": _API_VERSION,
    }
    status, body = _transport("GET", f"{_API_ROOT}/user/installations?per_page=100", headers, None)
    if not (200 <= status < 300):
        raise UserInstallDiscoveryError(
            f"could not list the user's installations (HTTP {status}): "
            f"{redact_gh_stderr(body) or 'unknown error'}"
        )
    parsed = _parse_json(body)
    if parsed is None:
        # ``/user/installations`` returns an object; a bare list is also tolerated.
        try:
            arr = json.loads(body or "")
        except (json.JSONDecodeError, ValueError):
            raise UserInstallDiscoveryError("user installations response was not valid JSON") from None
        return _select_installation_for_owner(arr, owner)
    return _select_installation_for_owner(parsed, owner)
