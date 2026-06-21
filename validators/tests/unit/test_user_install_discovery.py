"""S1 (ce-ops#157) — user-side install discovery via GitHub OAuth device flow.

The shared-App self-serve flow has no PEM on the user's disk; the user proves which App
installation is theirs by authenticating with the OAuth **device flow** and listing
``GET /user/installations``. ``forge.user_install_discovery``:

1. ``POST /login/device/code`` → ``(device_code, user_code, verification_uri, interval)``;
2. poll ``POST /login/oauth/access_token`` (grant_type
   ``urn:ietf:params:oauth:grant-type:device_code``) until a ``ghu_`` token, honouring the
   ``authorization_pending`` / ``slow_down`` back-off and failing closed on a hard error;
3. ``GET /user/installations`` with that user token and return the installation id whose
   ``account.login`` == the repo owner.

Injectable ``transport`` seam (same shape as ``app_jwt_runner.Transport``) and an injectable
``sleep`` so the poll back-off is deterministic; tests inject fakes and perform ZERO live
network. Fail-closed: no install for the owner → refusal.
"""

from __future__ import annotations

import json
import socket
import subprocess
import urllib.request

import pytest

from creator_engine_validator.forge.user_install_discovery import (
    DeviceFlowError,
    UserInstallDiscoveryError,
    discover_user_installation_id,
    request_device_code,
)

_CLIENT_ID = "Iv1.testclient"


def _device_code_body(**over):
    base = {
        "device_code": "DEV-CODE-123",
        "user_code": "WXYZ-1234",
        "verification_uri": "https://github.com/login/device",
        "expires_in": 900,
        "interval": 5,
    }
    base.update(over)
    return json.dumps(base)


def _installations_body(*pairs):
    return json.dumps(
        {"installations": [{"id": iid, "account": {"login": login}} for login, iid in pairs]}
    )


class _FakeTransport:
    """Scripts the device-code POST, the token-poll POSTs, and the installations GET."""

    def __init__(self, *, token_steps, installations=None, device_status=200, device_body=None):
        # token_steps: list of (status, body) the access_token poll returns, in order.
        self._token_steps = list(token_steps)
        self._installations = installations
        self._device_status = device_status
        self._device_body = device_body
        self.calls: list[dict] = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        if url.endswith("/login/device/code"):
            return self._device_status, (self._device_body or _device_code_body())
        if url.endswith("/login/oauth/access_token"):
            return self._token_steps.pop(0)
        if "/user/installations" in url:
            return 200, (
                self._installations
                if self._installations is not None
                else _installations_body(("arad-owner", 555))
            )
        raise AssertionError(f"unexpected url {url}")


_TOKEN_OK = (200, json.dumps({"access_token": "ghu_userfaketoken000", "token_type": "bearer"}))


def _sleeps(record):
    def sleep(seconds):
        record.append(seconds)

    return sleep


# ---------------------------------------------------------------------------
# device-code request
# ---------------------------------------------------------------------------
def test_request_device_code_returns_user_facing_fields():
    t = _FakeTransport(token_steps=[])
    grant = request_device_code(_CLIENT_ID, transport=t)
    assert grant.device_code == "DEV-CODE-123"
    assert grant.user_code == "WXYZ-1234"
    assert grant.verification_uri == "https://github.com/login/device"
    assert grant.interval == 5
    # POSTed to the device-code endpoint with an Accept: application/json header.
    call = t.calls[0]
    assert call["method"] == "POST"
    assert call["url"].endswith("/login/device/code")
    assert call["headers"]["Accept"] == "application/json"


def test_request_device_code_non_2xx_is_refused():
    t = _FakeTransport(token_steps=[], device_status=500, device_body="boom")
    with pytest.raises(DeviceFlowError):
        request_device_code(_CLIENT_ID, transport=t)


def test_request_device_code_missing_device_code_is_refused():
    t = _FakeTransport(token_steps=[], device_body=json.dumps({"user_code": "X"}))
    with pytest.raises(DeviceFlowError):
        request_device_code(_CLIENT_ID, transport=t)


# ---------------------------------------------------------------------------
# end-to-end discovery (device code -> poll -> installations)
# ---------------------------------------------------------------------------
def test_discovers_installation_for_repo_owner():
    t = _FakeTransport(
        token_steps=[_TOKEN_OK],
        installations=_installations_body(("arad-owner", 555)),
    )
    iid = discover_user_installation_id(
        _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
    )
    assert iid == 555


def test_poll_honours_authorization_pending_then_succeeds():
    record: list = []
    t = _FakeTransport(
        token_steps=[
            (200, json.dumps({"error": "authorization_pending"})),
            (200, json.dumps({"error": "authorization_pending"})),
            _TOKEN_OK,
        ],
        installations=_installations_body(("arad-owner", 9)),
    )
    iid = discover_user_installation_id(
        _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=_sleeps(record)
    )
    assert iid == 9
    # backed off between polls (interval-derived); at least one sleep happened.
    assert record and all(s > 0 for s in record)


def test_poll_slow_down_increases_the_interval():
    record: list = []
    t = _FakeTransport(
        token_steps=[
            (200, json.dumps({"error": "slow_down", "interval": 10})),
            _TOKEN_OK,
        ],
    )
    discover_user_installation_id(
        _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=_sleeps(record)
    )
    assert record and record[-1] >= 10  # honoured the larger interval


def test_poll_hard_error_is_refused():
    t = _FakeTransport(token_steps=[(200, json.dumps({"error": "access_denied"}))])
    with pytest.raises(DeviceFlowError):
        discover_user_installation_id(
            _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
        )


def test_poll_expired_token_is_refused():
    t = _FakeTransport(token_steps=[(200, json.dumps({"error": "expired_token"}))])
    with pytest.raises(DeviceFlowError):
        discover_user_installation_id(
            _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
        )


def test_poll_gives_up_after_max_attempts():
    # Always pending → must fail closed rather than spin forever.
    t = _FakeTransport(
        token_steps=[(200, json.dumps({"error": "authorization_pending"}))] * 1000
    )
    with pytest.raises(DeviceFlowError):
        discover_user_installation_id(
            _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None, max_poll_attempts=3
        )


# ---------------------------------------------------------------------------
# installation matching
# ---------------------------------------------------------------------------
def test_no_installation_for_owner_is_fail_closed():
    t = _FakeTransport(
        token_steps=[_TOKEN_OK],
        installations=_installations_body(("someone-else", 1)),
    )
    with pytest.raises(UserInstallDiscoveryError):
        discover_user_installation_id(
            _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
        )


def test_owner_match_is_case_insensitive():
    t = _FakeTransport(
        token_steps=[_TOKEN_OK],
        installations=_installations_body(("Arad-Owner", 77)),
    )
    iid = discover_user_installation_id(
        _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
    )
    assert iid == 77


def test_picks_matching_owner_among_several():
    t = _FakeTransport(
        token_steps=[_TOKEN_OK],
        installations=_installations_body(("a", 1), ("arad-owner", 42), ("c", 3)),
    )
    iid = discover_user_installation_id(
        _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
    )
    assert iid == 42


def test_installations_non_2xx_is_refused():
    class T(_FakeTransport):
        def __call__(self, method, url, headers, body):
            if "/user/installations" in url:
                self.calls.append({"url": url})
                return 401, json.dumps({"message": "Bad credentials"})
            return super().__call__(method, url, headers, body)

    t = T(token_steps=[_TOKEN_OK])
    with pytest.raises(UserInstallDiscoveryError):
        discover_user_installation_id(
            _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
        )


def test_user_token_never_in_an_error_message():
    leak = "ghu_userfaketoken000"
    t = _FakeTransport(
        token_steps=[(200, json.dumps({"access_token": leak, "token_type": "bearer"}))],
        installations=json.dumps({"message": f"Bad ({leak})"}),
    )

    # Force the installations leg to error so the redaction path is exercised.
    class T(_FakeTransport):
        def __call__(self, method, url, headers, body):
            if "/user/installations" in url:
                return 403, json.dumps({"message": f"forbidden {leak}"})
            return super().__call__(method, url, headers, body)

    t2 = T(token_steps=[(200, json.dumps({"access_token": leak, "token_type": "bearer"}))])
    with pytest.raises(UserInstallDiscoveryError) as ei:
        discover_user_installation_id(
            _CLIENT_ID, repo="arad-owner/mythos", transport=t2, sleep=lambda _s: None
        )
    assert leak not in str(ei.value)


def test_empty_repo_is_refused():
    t = _FakeTransport(token_steps=[_TOKEN_OK])
    with pytest.raises(UserInstallDiscoveryError):
        discover_user_installation_id(_CLIENT_ID, repo="", transport=t, sleep=lambda _s: None)


def test_zero_live_network(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("discovery must use the injected transport, not live network")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    t = _FakeTransport(token_steps=[_TOKEN_OK])
    iid = discover_user_installation_id(
        _CLIENT_ID, repo="arad-owner/mythos", transport=t, sleep=lambda _s: None
    )
    assert iid == 555
