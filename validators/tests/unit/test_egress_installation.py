"""Unit tests for egress-broker installation-id discovery.

dev-4's App env records NO ``installation_id`` (dev-2's does), so the broker must discover it:
authenticate AS the App with a short-lived RS256 JWT and ``GET /app/installations``, then pick
the installation whose account is the org (``creator-engine``). ``egress_broker.installation``
does this behind the same injectable HTTPS ``transport`` seam the mint leg uses. These tests
inject fakes and run ZERO live network / crypto.

Fail-closed: a non-2xx response, an unparseable body, or no installation for the owner is a
:class:`InstallationDiscoveryError` — the broker never guesses an id. The JWT lives in the
``Authorization: Bearer`` header only — never the argv, a log, or the error message.
"""

import json
import socket
import subprocess
import urllib.request

import pytest

from egress_broker.installation import InstallationDiscoveryError, discover_installation_id

_APP_ID = "4085526"
_NOW = 1_700_000_000


def _signer(signing_input: bytes) -> bytes:
    return b"SIG::" + signing_input[:6]


def _installations_body(*pairs):
    return json.dumps([{"id": iid, "account": {"login": login}} for login, iid in pairs])


def _transport(status=200, body=None, calls=None):
    def transport(method, url, headers, req_body):
        if calls is not None:
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": req_body})
        payload = body if body is not None else _installations_body(("creator-engine", 12345678))
        return status, payload

    return transport


def test_discovers_installation_for_the_owner():
    iid = discover_installation_id(
        _APP_ID, signer=_signer, owner="creator-engine", transport=_transport(), now=lambda: _NOW
    )
    assert iid == 12345678


def test_picks_the_matching_owner_among_several():
    body = _installations_body(("someone-else", 1), ("creator-engine", 42), ("third", 3))
    iid = discover_installation_id(
        _APP_ID, signer=_signer, owner="creator-engine", transport=_transport(body=body), now=lambda: _NOW
    )
    assert iid == 42


def test_owner_match_is_case_insensitive():
    body = _installations_body(("Creator-Engine", 7))
    iid = discover_installation_id(
        _APP_ID, signer=_signer, owner="creator-engine", transport=_transport(body=body), now=lambda: _NOW
    )
    assert iid == 7


def test_uses_app_jwt_bearer_on_the_installations_endpoint():
    calls: list[dict] = []
    discover_installation_id(
        _APP_ID, signer=_signer, owner="creator-engine", transport=_transport(calls=calls), now=lambda: _NOW
    )
    assert len(calls) == 1
    call = calls[0]
    assert call["method"] == "GET"
    assert call["url"].startswith("https://api.github.com/app/installations")
    assert call["headers"]["Authorization"].startswith("Bearer ")
    assert call["headers"]["Accept"] == "application/vnd.github+json"
    assert "X-GitHub-Api-Version" in call["headers"]


def test_no_installation_for_owner_is_refused():
    body = _installations_body(("not-us", 1))
    with pytest.raises(InstallationDiscoveryError):
        discover_installation_id(
            _APP_ID, signer=_signer, owner="creator-engine", transport=_transport(body=body), now=lambda: _NOW
        )


def test_non_2xx_is_refused_and_redacted():
    leak = "ghs_leak_0123456789ABCDEFGHIJKLMNOPQRST"
    body = json.dumps({"message": f"Bad credentials ({leak})"})
    with pytest.raises(InstallationDiscoveryError) as ei:
        discover_installation_id(
            _APP_ID, signer=_signer, owner="creator-engine",
            transport=_transport(status=401, body=body), now=lambda: _NOW,
        )
    assert leak not in str(ei.value)


def test_unparseable_body_is_refused():
    with pytest.raises(InstallationDiscoveryError):
        discover_installation_id(
            _APP_ID, signer=_signer, owner="creator-engine",
            transport=_transport(body="<<not json>>"), now=lambda: _NOW,
        )


def test_empty_app_id_is_refused():
    with pytest.raises(InstallationDiscoveryError):
        discover_installation_id("", signer=_signer, owner="creator-engine", transport=_transport())


def test_zero_live_network(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("discovery must use the injected transport, not live network")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    iid = discover_installation_id(
        _APP_ID, signer=_signer, owner="creator-engine", transport=_transport(), now=lambda: _NOW
    )
    assert iid == 12345678
