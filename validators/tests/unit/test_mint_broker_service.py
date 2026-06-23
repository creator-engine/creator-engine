"""S4 (ce-ops#157) — the mint-broker ``POST /v1/token`` handler.

The handler is the standing broker's mint endpoint. For each request it:

1. validates the request shape (repo, installation_id, permissions, caller token);
2. REJECTS any out-of-ceiling permission BEFORE any GitHub call (G3 — never even attempt an
   admin mint);
3. enforces the per-user rate cap;
4. runs the S2 binding check (the caller's ``ghu_`` must control the claimed installation);
5. mints via the frozen ``app_jwt_gh_runner`` -> ``mint_scoped_token`` composition with the
   shared-App key behind the openssl signer;
6. appends a secret-free audit record (reusing ``egress_broker.audit``).

The response carries the minted ``ghs_`` value + expiry; an audit/deny path returns a status
code and reason. Injectable binding + signer + transport + audit-path seams; ZERO live
network / crypto. The crux assertions: bound read+PR mints; ``administration:write`` is refused
PRE-CALL (no GitHub call made); an unbound caller gets 403 and NOTHING is minted.
"""

from __future__ import annotations

import json

import pytest

from mint_broker.binding import BindingRefused, BindingTransportError
from mint_broker.config import load_mint_broker_config
import mint_broker.service as service_mod
from mint_broker.service import handle_token_request

_MINTED = "ghs_broker_minted_value"


@pytest.fixture(autouse=True)
def _clear_rate_buckets():
    service_mod._RATE_BUCKETS.clear()
    yield
    service_mod._RATE_BUCKETS.clear()


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


def test_binding_check_receives_requested_repo_before_minting(tmp_path):
    cfg = _config(tmp_path)
    binding_calls: list[dict] = []

    def binding(caller_token, *, installation_id, repo_full_name):
        binding_calls.append(
            {
                "caller_token": caller_token,
                "installation_id": installation_id,
                "repo_full_name": repo_full_name,
            }
        )

    resp = handle_token_request(
        _request(repo="victim-owner/mythos"),
        config=cfg,
        binding_check=binding,
        signer=_signer,
        transport=_mint_transport(),
    )

    assert resp["status"] == 200
    assert binding_calls == [
        {
            "caller_token": "ghu_callerfaketoken000",
            "installation_id": 222,
            "repo_full_name": "victim-owner/mythos",
        }
    ]


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
# rate guard: configured per-user cap enforced before binding/minting
# ---------------------------------------------------------------------------
def test_rate_cap_refuses_repeated_mints_beyond_configured_limit(tmp_path):
    cfg = _config(tmp_path, per_user_rate_cap=2, rate_window_seconds=3600)
    mint_calls: list = []
    binding_calls: list = []

    def binding(*_a, **_k):
        binding_calls.append(1)

    first = handle_token_request(
        _request(),
        config=cfg,
        binding_check=binding,
        signer=_signer,
        transport=_mint_transport(calls=mint_calls),
    )
    second = handle_token_request(
        _request(),
        config=cfg,
        binding_check=binding,
        signer=_signer,
        transport=_mint_transport(calls=mint_calls),
    )
    third = handle_token_request(
        _request(),
        config=cfg,
        binding_check=binding,
        signer=_signer,
        transport=_mint_transport(calls=mint_calls),
    )

    assert first["status"] == 200
    assert second["status"] == 200
    assert third == {"status": 429, "reason": "rate_limited"}
    assert len(binding_calls) == 2
    assert len(mint_calls) == 2
    records = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [r["decision"] for r in records] == ["allow", "allow", "deny"]
    assert records[-1]["reason"] == "rate_limited"


def test_rate_cap_is_per_caller_token_identity(tmp_path):
    cfg = _config(tmp_path, per_user_rate_cap=1, rate_window_seconds=3600)

    first = handle_token_request(
        _request(caller_user_token="ghu_caller_one"),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    second_same_user = handle_token_request(
        _request(caller_user_token="ghu_caller_one"),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    other_user = handle_token_request(
        _request(caller_user_token="ghu_caller_two"),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )

    assert first["status"] == 200
    assert second_same_user == {"status": 429, "reason": "rate_limited"}
    assert other_user["status"] == 200


def test_rate_cap_window_expiry_allows_new_mint(tmp_path, monkeypatch):
    cfg = _config(tmp_path, per_user_rate_cap=1, rate_window_seconds=60)
    now = [100.0]
    monkeypatch.setattr(service_mod.time, "monotonic", lambda: now[0])

    first = handle_token_request(
        _request(),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    second = handle_token_request(
        _request(),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )
    now[0] = 161.0
    after_window = handle_token_request(
        _request(),
        config=cfg,
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport(),
    )

    assert first["status"] == 200
    assert second == {"status": 429, "reason": "rate_limited"}
    assert after_window["status"] == 200


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


def test_binding_transport_failure_is_502_and_audited(tmp_path):
    cfg = _config(tmp_path)
    calls: list = []

    def failing_binding(*_a, **_k):
        raise BindingTransportError("github timed out")

    resp = handle_token_request(
        _request(),
        config=cfg,
        binding_check=failing_binding,
        signer=_signer,
        transport=_mint_transport(calls=calls),
    )
    assert resp == {"status": 502, "reason": "binding_transport_error"}
    assert calls == []
    rec = json.loads((tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip())
    assert rec["decision"] == "deny"
    assert rec["reason"] == "binding_transport_error"


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
