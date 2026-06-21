"""S2 (ce-ops#157) — the mint-broker user->installation binding check (the SECURITY CRUX).

A pasted ``installation_id`` is UNTRUSTED (GitHub explicitly warns it is spoofable). Before the
broker mints anything it must PROVE the caller controls the claimed installation and that the
installation covers the requested repository: it calls GitHub's user-installation endpoints with
the caller's own ``ghu_`` token and checks both bindings. If either check fails, it raises
:class:`BindingRefused` — the cross-tenant spoof is denied.

These tests hammer BOTH the allow case AND the cross-tenant refusal case (a caller pasting an id
that belongs to a different account). Injectable transport; ZERO live network.
"""

from __future__ import annotations

import json
import socket
import subprocess
import urllib.request

import pytest

from mint_broker.binding import (
    BindingRefused,
    BindingTransportError,
    assert_user_controls_installation,
)

_GHU = "ghu_callerfaketoken000"
_REPO = "arad-owner/mythos"


def _installations_body(*ids):
    return json.dumps({"installations": [{"id": i, "account": {"login": f"acct{i}"}} for i in ids]})


def _repositories_body(*full_names):
    return json.dumps(
        {"repositories": [{"id": i + 1, "full_name": name} for i, name in enumerate(full_names)]}
    )


def _transport(status=200, body=None, repo_status=200, repo_body=None, calls=None):
    def transport(method, url, headers, req_body):
        if calls is not None:
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": req_body})
        if "/repositories" in url:
            return repo_status, (repo_body if repo_body is not None else _repositories_body(_REPO))
        return status, (body if body is not None else _installations_body(111, 222, 333))

    return transport


# ---------------------------------------------------------------------------
# allow: the caller's token lists the claimed installation
# ---------------------------------------------------------------------------
def test_allows_when_installation_is_in_the_users_list():
    # returns None / does not raise → bound
    assert_user_controls_installation(
        _GHU,
        installation_id=222,
        repo_full_name=_REPO,
        transport=_transport(),
    )


def test_uses_the_caller_token_as_bearer_on_the_user_endpoint():
    calls: list[dict] = []
    assert_user_controls_installation(
        _GHU,
        installation_id=111,
        repo_full_name=_REPO,
        transport=_transport(calls=calls),
    )
    assert len(calls) == 2
    installation_call, repo_call = calls
    assert installation_call["method"] == "GET"
    assert installation_call["url"].startswith("https://api.github.com/user/installations")
    assert repo_call["method"] == "GET"
    assert repo_call["url"].startswith("https://api.github.com/user/installations/111/repositories")
    for call in calls:
        assert call["headers"]["Authorization"] == f"Bearer {_GHU}"
        assert call["headers"]["Accept"] == "application/vnd.github+json"


# ---------------------------------------------------------------------------
# REFUSE: the cross-tenant spoof — a pasted id the caller does NOT control
# ---------------------------------------------------------------------------
def test_refuses_cross_tenant_id_not_in_the_users_list():
    # The caller controls 111/222/333 but pastes 999 (someone else's installation).
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            _GHU,
            installation_id=999,
            repo_full_name=_REPO,
            transport=_transport(),
        )


def test_refuses_when_the_user_has_no_installations():
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            _GHU,
            installation_id=222,
            repo_full_name=_REPO,
            transport=_transport(body=_installations_body()),
        )


def test_refuses_same_name_repo_in_a_different_owner_for_a_controlled_installation():
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            _GHU,
            installation_id=222,
            repo_full_name="victim-owner/mythos",
            transport=_transport(repo_body=_repositories_body("attacker-owner/mythos")),
        )


def test_refuses_a_zero_or_negative_installation_id():
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            _GHU,
            installation_id=0,
            repo_full_name=_REPO,
            transport=_transport(),
        )
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            _GHU,
            installation_id=-5,
            repo_full_name=_REPO,
            transport=_transport(),
        )


def test_refuses_an_empty_caller_token():
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            "",
            installation_id=222,
            repo_full_name=_REPO,
            transport=_transport(),
        )


# ---------------------------------------------------------------------------
# fail-closed transport / parsing
# ---------------------------------------------------------------------------
def test_non_2xx_is_a_transport_error_and_redacts_a_leaked_token():
    leak = "ghu_leaked_token_in_body_0000000000"
    body = json.dumps({"message": f"Bad credentials ({leak})"})
    with pytest.raises(BindingTransportError) as ei:
        assert_user_controls_installation(
            _GHU,
            installation_id=222,
            repo_full_name=_REPO,
            transport=_transport(status=401, body=body),
        )
    assert leak not in str(ei.value)


def test_unparseable_body_is_a_transport_error():
    with pytest.raises(BindingTransportError):
        assert_user_controls_installation(
            _GHU,
            installation_id=222,
            repo_full_name=_REPO,
            transport=_transport(body="<<not json>>"),
        )


def test_repository_lookup_transport_exception_is_wrapped():
    def transport(method, url, headers, req_body):
        if "/repositories" in url:
            raise TimeoutError("github timed out")
        return 200, _installations_body(222)

    with pytest.raises(BindingTransportError) as ei:
        assert_user_controls_installation(
            _GHU,
            installation_id=222,
            repo_full_name=_REPO,
            transport=transport,
        )
    assert "github timed out" in str(ei.value)


def test_handles_a_bare_list_response_shape():
    # Some GitHub list endpoints return a bare array; the binding tolerates both shapes.
    bare = json.dumps([{"id": 7, "account": {"login": "x"}}])
    assert_user_controls_installation(
        _GHU,
        installation_id=7,
        repo_full_name=_REPO,
        transport=_transport(body=bare),
    )
    with pytest.raises(BindingRefused):
        assert_user_controls_installation(
            _GHU,
            installation_id=8,
            repo_full_name=_REPO,
            transport=_transport(body=bare),
        )


def test_zero_live_network(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("binding must use the injected transport, not live network")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    assert_user_controls_installation(
        _GHU,
        installation_id=111,
        repo_full_name=_REPO,
        transport=_transport(),
    )
