"""S4 (ce-ops#157) — the mint-broker ``POST /v1/token`` handler.

The handler is the standing broker's mint endpoint. For each request it:

1. validates the request shape (repo, installation_id, permissions, caller token);
2. REJECTS any out-of-ceiling permission BEFORE any GitHub call (G3 — never even attempt an
   admin mint);
3. runs the S2 binding check (the caller's ``ghu_`` must control the claimed installation);
4. mints via the frozen ``app_jwt_gh_runner`` -> ``mint_scoped_token`` composition with the
   shared-App key behind the openssl signer;
5. appends a secret-free audit record (reusing ``egress_broker.audit``).

The response carries the minted ``ghs_`` value + expiry; an audit/deny path returns a status
code and reason. Injectable binding + signer + transport + audit-path seams; ZERO live
network / crypto. The crux assertions: bound read+PR mints; ``administration:write`` is refused
PRE-CALL (no GitHub call made); an unbound caller gets 403 and NOTHING is minted.
"""

from __future__ import annotations

import json

import pytest

from mint_broker.binding import BindingRefused
from mint_broker.config import load_mint_broker_config
from mint_broker.service import handle_token_request

_MINTED = "ghs_broker_minted_value"


def _config(tmp_path, **over):
    base = {
        "app_client_id": "Iv1.shared0000",
        "pem_path": str(tmp_path / "shared.pem"),
        "audit_log": str(tmp_path / "audit.jsonl"),
        "permission_ceiling": {
            "metadata": "read",
            "contents": "write",
            "pull_requests": "write",
        },
        "per_user_rate_cap": 30,
        "rate_window_seconds": 3600,
    }
    base.update(over)
    return load_mint_broker_config(base)


def _request(**over):
    base = {
        "installation_id": 222,
        "repo": "arad-owner/mythos",
        "permissions": {"contents": "write", "pull_requests": "write"},
        "caller_user_token": "ghu_callerfaketoken000",
    }
    base.update(over)
    return base


def _signer(_signing_input: bytes) -> bytes:
    return b"fake-rs256-sig"


def _allow_binding(*_a, **_k):
    return None  # bound


def _deny_binding(*_a, **_k):
    raise BindingRefused("not your installation")


def _mint_transport(calls=None):
    """The app-JWT mint transport: returns a minted installation token for the POST."""

    def transport(method, url, headers, body):
        if calls is not None:
            calls.append({"method": method, "url": url, "body": body})
        assert headers.get("Authorization", "").startswith("Bearer ")
        return 201, json.dumps(
            {
                "token": _MINTED,
                "expires_at": "2026-06-21T15:00:00Z",
                "permissions": {"contents": "write", "pull_requests": "write"},
            }
        )

    return transport


# ---------------------------------------------------------------------------
# happy path: bound, in-ceiling → mints
# ---------------------------------------------------------------------------
def test_bound_in_ceiling_mints_a_scoped_token(tmp_path):
    cfg = _config(tmp_path)
    resp = handle_token_request(
        _request(),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    assert resp["status"] == 200
    assert resp["token"] == _MINTED
    assert resp["expires_at"] == "2026-06-21T15:00:00Z"
    # an audit record was written (allow)
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["decision"] == "allow"
    assert _MINTED not in json.dumps(rec)  # secret-free audit


# ---------------------------------------------------------------------------
# G3 CRUX: out-of-ceiling permission refused BEFORE any GitHub call
# ---------------------------------------------------------------------------
def test_administration_write_is_refused_before_any_github_call(tmp_path):
    cfg = _config(tmp_path)
    calls: list = []
    binding_calls: list = []

    def binding(*a, **k):
        binding_calls.append(1)

    resp = handle_token_request(
        _request(permissions={"administration": "write"}),
        config=cfg,
        binding_check=binding,
        signer=_signer,
        transport=_mint_transport(calls=calls),
    )
    assert resp["status"] == 403
    assert "token" not in resp
    assert calls == []  # NO GitHub mint call was made
    assert binding_calls == []  # ceiling check fails BEFORE even binding
    rec = json.loads((tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip())
    assert rec["decision"] == "deny"
    assert rec["reason"] == "out_of_ceiling"


def test_out_of_ceiling_scope_is_refused(tmp_path):
    cfg = _config(tmp_path)
    calls: list = []
    resp = handle_token_request(
        _request(permissions={"secrets": "read"}),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(calls=calls),
    )
    assert resp["status"] == 403
    assert calls == []


# ---------------------------------------------------------------------------
# unbound caller: 403, nothing minted
# ---------------------------------------------------------------------------
def test_unbound_caller_is_403_and_nothing_minted(tmp_path):
    cfg = _config(tmp_path)
    calls: list = []
    resp = handle_token_request(
        _request(),
        config=cfg,
        binding_check=_deny_binding,
        signer=_signer,
        transport=_mint_transport(calls=calls),
    )
    assert resp["status"] == 403
    assert "token" not in resp
    assert calls == []  # binding refused BEFORE the mint
    rec = json.loads((tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip())
    assert rec["decision"] == "deny"
    assert rec["reason"] == "binding_refused"


# ---------------------------------------------------------------------------
# request validation
# ---------------------------------------------------------------------------
def test_missing_caller_token_is_400(tmp_path):
    cfg = _config(tmp_path)
    resp = handle_token_request(
        _request(caller_user_token=""),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    assert resp["status"] == 400


def test_bad_repo_is_400(tmp_path):
    cfg = _config(tmp_path)
    resp = handle_token_request(
        _request(repo="not-a-repo"),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    assert resp["status"] == 400


def test_non_positive_installation_id_is_400(tmp_path):
    cfg = _config(tmp_path)
    resp = handle_token_request(
        _request(installation_id=0),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    assert resp["status"] == 400


def test_empty_permissions_is_400(tmp_path):
    cfg = _config(tmp_path)
    resp = handle_token_request(
        _request(permissions={}),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    # empty set is out-of-ceiling per config.permits → refused (no GitHub call)
    assert resp["status"] in (400, 403)


# ---------------------------------------------------------------------------
# mint transport failure → 502, fail-closed
# ---------------------------------------------------------------------------
def test_mint_transport_failure_is_502(tmp_path):
    cfg = _config(tmp_path)

    def failing_transport(method, url, headers, body):
        return 500, json.dumps({"message": "github is down"})

    resp = handle_token_request(
        _request(),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=failing_transport,
    )
    assert resp["status"] == 502
    assert "token" not in resp


def test_caller_token_never_in_response_or_audit(tmp_path):
    cfg = _config(tmp_path)
    token = "ghu_callerfaketoken000"
    resp = handle_token_request(
        _request(caller_user_token=token),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    assert token not in json.dumps(resp)
    assert token not in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
