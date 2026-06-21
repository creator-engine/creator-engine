"""S2 (ce-ops#157) — the mint-broker user->installation binding check (the SECURITY CRUX).

A pasted ``installation_id`` is UNTRUSTED (GitHub explicitly warns it is spoofable). Before the
broker mints anything it must PROVE the caller controls the claimed installation: it calls
``GET /user/installations`` with the caller's own ``ghu_`` token and asserts the claimed id is in
the returned list. If not, it raises :class:`BindingRefused` — the cross-tenant spoof is denied.

These tests hammer BOTH the allow case AND the cross-tenant refusal case (a caller pasting an id
that belongs to a different account). Injectable transport; ZERO live network.
"""

from __future__ import annotations

import json
import socket
import subprocess
import urllib.request

import pytest

from mint_broker.binding import BindingRefused, BindingTransportError, assert_user_controls_installation

_GHU = "ghu_callerfaketoken000"


def _installations_body(*ids):
    return json.dumps({"installations": [{"id": i, "account": {"login": f"acct{i}"}} for i in ids]})


def _transport(status=200, body=None, calls=None):
    def transport(method, url, headers, req_body):
        if calls is not None:
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": req_body})
        return status, (body if body is not None else _installations_body(111, 222, 333))

    return transport


# ---------------------------------------------------------------------------
# allow: the caller's token lists the claimed installation
# ---------------------------------------------------------------------------
def test_allows_when_installation_is_in_the_users_list():
    # returns None / does not raise → bound
    assert_user_controls_installation(_GHU, installation_id=222, transport=_transport())


def test_uses_the_caller_token_as_bearer_on_the_user_endpoint():
    calls: list[dict] = []
    assert_user_controls_installation(_GHU, installation_id=111, transport=_transport(calls=calls))
    assert len(calls) == 1
    call = calls[0]
    assert call["method"] == "GET"
    assert call["url"].startswith("https://api.github.com/user/installations")
    assert call["headers"]["Authorization"] == f"Bearer {_GHU}"
    assert call["headers"]["Accept"] == "application/vnd.github+json"


# ---------------------------------------------------------------------------
# REFUSE: the cross-tenant spoof — a pasted id the caller does NOT control
# ---------------------------------------------------------------------------
def test_refuses_cross_tenant_id_not_in_the_users_list():
    # The caller controls 111/222/333 but pastes 999 (someone else's installation).
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(_GHU, installation_id=999, transport=_transport())


def test_refuses_when_the_user_has_no_installations():
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            _GHU, installation_id=222, transport=_transport(body=_installations_body())
        )


def test_refuses_a_zero_or_negative_installation_id():
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(_GHU, installation_id=0, transport=_transport())
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(_GHU, installation_id=-5, transport=_transport())


def test_refuses_an_empty_caller_token():
    with pytest.raises(BindingRefused):
        assert_user_controls_installation("", installation_id=222, transport=_transport())


# ---------------------------------------------------------------------------
# fail-closed transport / parsing
# ---------------------------------------------------------------------------
def test_non_2xx_is_a_transport_error_and_redacts_a_leaked_token():
    leak = "ghu_leaked_token_in_body_0000000000"
    body = json.dumps({"message": f"Bad credentials ({leak})"})
    with pytest.raises(BindingTransportError) as ei:
        assert_user_controls_installation(
            _GHU, installation_id=222, transport=_transport(status=401, body=body)
        )
    assert leak not in str(ei.value)


def test_unparseable_body_is_a_transport_error():
    with pytest.raises(BindingTransportError):
        assert_user_controls_installation(
            _GHU, installation_id=222, transport=_transport(body="<<not json>>")
        )


def test_handles_a_bare_list_response_shape():
    # Some GitHub list endpoints return a bare array; the binding tolerates both shapes.
    bare = json.dumps([{"id": 7, "account": {"login": "x"}}])
    assert_user_controls_installation(_GHU, installation_id=7, transport=_transport(body=bare))
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(_GHU, installation_id=8, transport=_transport(body=bare))


def test_zero_live_network(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("binding must use the injected transport, not live network")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    assert_user_controls_installation(_GHU, installation_id=111, transport=_transport())
