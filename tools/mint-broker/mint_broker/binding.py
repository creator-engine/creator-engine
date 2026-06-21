"""The mint-broker user->installation binding check (ce-ops#157, S2) — the SECURITY CRUX.

The broker is internet-facing and mints scoped installation tokens for shared-App users. The
``installation_id`` a caller sends is UNTRUSTED — GitHub explicitly warns it is spoofable, so a
hostile caller could paste a DIFFERENT tenant's installation id and try to mint a token for a
repo they don't control. This module is the gate that stops that:

:func:`assert_user_controls_installation` calls ``GET /user/installations`` with the CALLER'S
OWN ``ghu_`` token (obtained via the S1 device flow on the user's machine) and asserts the
claimed ``installation_id`` is in the list GitHub returns FOR THAT USER. If it isn't — the
cross-tenant spoof — it raises :class:`BindingRefused`. The id is only ever trusted because the
user's own authenticated token vouches for it.

Distinct failure types so the service can map them to the right HTTP status:

* :class:`BindingRefused` — the caller does NOT control the installation (a 403 — the deny path).
* :class:`BindingTransportError` — the user-installations call errored / was unparseable (a 502;
  fail-closed, never "allow on error").

Network only behind an injectable ``transport`` seam (same shape as the forge mint seams); tests
inject a fake and perform ZERO live network. The caller's ``ghu_`` token lives in the
``Authorization: Bearer`` header ONLY — never an argv, a log, or an exception (``redact_gh_stderr``
masks any token-shaped material the API echoes back).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from creator_engine_validator.forge._redact import redact_gh_stderr

#: HTTPS transport seam: ``(method, url, headers, body) -> (status_code, response_body_text)``.
Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, str]"]

_API_ROOT = "https://api.github.com"
_API_VERSION = "2022-11-28"
_ACCEPT = "application/vnd.github+json"
_USER_INSTALLATIONS = "user/installations?per_page=100"


class BindingRefused(Exception):
    """The caller does NOT control the claimed installation — the cross-tenant spoof is denied."""


class BindingTransportError(Exception):
    """The user-installations lookup errored / was unparseable — fail-closed (never allow)."""


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


def _installation_ids(payload: object) -> set[int]:
    """Extract the installation ids from a ``{"installations":[...]}`` or bare-list response."""
    entries: object
    if isinstance(payload, dict):
        entries = payload.get("installations")
    else:
        entries = payload
    ids: set[int] = set()
    if not isinstance(entries, list):
        raise BindingTransportError("user installations response was not a list")
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") is None:
            continue
        try:
            iid = int(entry["id"])
        except (TypeError, ValueError):
            continue
        if iid > 0:
            ids.add(iid)
    return ids


def assert_user_controls_installation(
    caller_user_token: str,
    *,
    installation_id: int,
    transport: Transport | None = None,
) -> None:
    """Refuse unless the caller's ``ghu_`` token proves it controls ``installation_id``.

    Calls ``GET /user/installations`` AS the caller and asserts the claimed id is in that user's
    list. Raises :class:`BindingRefused` for the spoof (id absent / not controlled, or a
    non-positive id / empty token) and :class:`BindingTransportError` on a non-2xx or unparseable
    response (fail-closed — an error never means "allow"). Returns ``None`` when bound.
    """
    if not (caller_user_token or "").strip():
        raise BindingRefused("a caller user token is required to bind an installation (fail-closed)")
    if not isinstance(installation_id, int) or installation_id <= 0:
        raise BindingRefused(
            f"installation_id {installation_id!r} must be a positive integer (a pasted id is untrusted)"
        )
    _transport = transport or _default_transport
    headers = {
        "Authorization": f"Bearer {caller_user_token}",
        "Accept": _ACCEPT,
        "X-GitHub-Api-Version": _API_VERSION,
    }
    status, body = _transport("GET", f"{_API_ROOT}/{_USER_INSTALLATIONS}", headers, None)
    if not (200 <= status < 300):
        raise BindingTransportError(
            f"could not list the caller's installations (HTTP {status}): "
            f"{redact_gh_stderr(body) or 'unknown error'}"
        )
    try:
        parsed = json.loads(body or "")
    except (json.JSONDecodeError, ValueError) as exc:
        raise BindingTransportError(f"user installations response was not valid JSON: {exc}") from None

    controlled = _installation_ids(parsed)
    if installation_id not in controlled:
        # The cross-tenant spoof: the caller pasted an id its OWN token does not vouch for.
        raise BindingRefused(
            f"the caller does not control installation {installation_id} "
            "(it is not in the authenticated user's installations) — refusing to mint"
        )
