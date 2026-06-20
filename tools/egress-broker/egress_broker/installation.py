"""App-installation discovery — ``GET /app/installations`` filtered to the org owner.

The generalized minter needs an ``installation_id`` to mint from. dev-2's App config records
one; dev-4's does NOT — so the broker discovers it: authenticate AS the App with a short-lived
RS256 JWT (the frozen ``forge.app_jwt_runner.build_app_jwt`` seam — the App private key stays
behind the injected ``signer``) and ``GET /app/installations``, then select the installation
whose ``account.login`` is the org (``creator-engine``).

Reuses the same injectable HTTPS ``transport`` shape as the mint leg
(``(method, url, headers, body) -> (status, text)``), so one fake drives both discovery and
mint in a test and no live network is ever touched. Fail-closed: a non-2xx, an unparseable
body, or no installation for the owner is a :class:`InstallationDiscoveryError`. The JWT lives
in the ``Authorization: Bearer`` header ONLY — never the argv, a log, or the error message
(``redact_gh_stderr`` masks any token-shaped material the API echoes back).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from creator_engine_validator.forge._redact import redact_gh_stderr
from creator_engine_validator.forge.app_jwt_runner import Signer, build_app_jwt

#: HTTPS transport seam: ``(method, url, headers, body) -> (status_code, response_body_text)``
#: — identical to ``app_jwt_runner.Transport`` so the mint and discovery legs share one fake.
Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, str]"]

_API_ROOT = "https://api.github.com"
_API_VERSION = "2022-11-28"
_ACCEPT = "application/vnd.github+json"
#: One page of installations is ample (an App is installed on one — maybe two — accounts);
#: deeper pagination is a deferred edge documented in the broker design.
_INSTALLATIONS_PATH = "app/installations?per_page=100"


class InstallationDiscoveryError(Exception):
    """The App installation for the owner could not be discovered — a fail-closed refusal."""


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


def discover_installation_id(
    app_id: str,
    *,
    signer: Signer,
    owner: str,
    transport: Transport | None = None,
    now: Callable[[], float] | None = None,
) -> int:
    """Discover the App's installation id on ``owner`` via ``GET /app/installations`` (fail-closed).

    Mints a fresh App JWT (``build_app_jwt``; key stays behind ``signer``), GETs the App's
    installations with ``Authorization: Bearer <JWT>``, and returns the id of the installation
    whose ``account.login`` matches ``owner`` (case-insensitively). Raises
    :class:`InstallationDiscoveryError` on a non-2xx, an unparseable body, or no match — the
    broker never guesses an installation id.
    """
    if not (app_id or "").strip():
        raise InstallationDiscoveryError("app_id is required to discover an installation")
    if not (owner or "").strip():
        raise InstallationDiscoveryError("owner is required to filter installations")
    _transport = transport or _default_transport

    jwt = build_app_jwt(app_id, signer=signer, now=now)  # fresh; header-only
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Accept": _ACCEPT,
        "X-GitHub-Api-Version": _API_VERSION,
    }
    status, body = _transport("GET", f"{_API_ROOT}/{_INSTALLATIONS_PATH}", headers, None)
    if not (200 <= status < 300):
        raise InstallationDiscoveryError(
            f"could not list App installations (HTTP {status}): "
            f"{redact_gh_stderr(body) or 'unknown error'}"
        )
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise InstallationDiscoveryError(
            f"App installations response was not valid JSON: {exc}"
        ) from None
    if not isinstance(parsed, list):
        raise InstallationDiscoveryError("App installations response was not a JSON array")

    target = owner.strip().lower()
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        account = entry.get("account") or {}
        login = str(account.get("login") or "").strip().lower()
        if login == target and entry.get("id") is not None:
            try:
                iid = int(entry["id"])
            except (TypeError, ValueError):
                continue
            if iid > 0:
                return iid
    raise InstallationDiscoveryError(
        f"no App installation found for owner {owner!r} (the App may not be installed on the org)"
    )
