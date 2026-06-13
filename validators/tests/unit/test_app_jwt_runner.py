"""Unit tests for the v3 G-3.7.1 App-JWT mint seam.

``forge.app_jwt_runner`` supplies the App-authenticated runner ``mint_scoped_token`` needs: it
mints a short-lived RS256 GitHub App JWT (behind an injectable signer) and issues the
installation-token POST with ``Authorization: Bearer <JWT>`` (behind an injectable HTTPS
transport), returning a ``GhRunner``-shaped ``(argv, input_text) -> CompletedProcess`` so
``mint_scoped_token`` consumes it byte-unchanged.

Doc-grounded contract (current GitHub-App docs): ``gh`` cannot authenticate as a GitHub App
via a JWT (it sends ``Authorization: token``; App auth requires ``Bearer``), so the mint leg
is a direct-HTTPS Bearer adapter, NOT a ``gh`` shell. The App private key never enters this
module — it lives only behind the injected signer. These tests inject fakes and perform ZERO
live network / subprocess / crypto.
"""

import base64
import json
import socket
import subprocess
import urllib.request

import pytest

from creator_engine_validator.forge import ForgeConfigRefused
from creator_engine_validator.forge.app_jwt_runner import app_jwt_gh_runner, build_app_jwt

_CLIENT_ID = "Iv1.fakeclientid"
_NOW = 1_700_000_000  # fixed injected clock


def _fake_signer(calls=None):
    """A deterministic RS256 stand-in: records the signing input, returns recognizable bytes."""
    def signer(signing_input: bytes) -> bytes:
        if calls is not None:
            calls.append(signing_input)
        return b"FAKE_SIG::" + signing_input[:6]
    return signer


def _fake_transport(status=201, body=None, calls=None):
    """A fake HTTPS transport recording every (method, url, headers, body)."""
    def transport(method, url, headers, req_body):
        if calls is not None:
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": req_body})
        payload = body if body is not None else json.dumps({"token": "ghs_fake", "expires_at": "2026-06-06T13:00:00Z"})
        return status, payload
    return transport


def _b64url_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


_MINT_ARGV = ["gh", "api", "-X", "POST", "app/installations/77/access_tokens", "--input", "-"]
_MINT_BODY = json.dumps({"repositories": ["r"], "permissions": {"contents": "read"}})


# ---------------------------------------------------------------------------
# JWT assembly — RS256 header, doc-correct claims, signer over the signing input
# ---------------------------------------------------------------------------
def test_build_app_jwt_assembles_rs256_claims_and_signs_signing_input():
    sig_calls: list[bytes] = []
    jwt = build_app_jwt(_CLIENT_ID, signer=_fake_signer(sig_calls), now=lambda: _NOW)
    h_seg, p_seg, s_seg = jwt.split(".")
    header = json.loads(_b64url_decode(h_seg))
    payload = json.loads(_b64url_decode(p_seg))
    assert header == {"alg": "RS256", "typ": "JWT"}
    assert payload["iss"] == _CLIENT_ID
    assert payload["iat"] == _NOW - 60          # 60s in the past (clock drift)
    assert payload["exp"] == _NOW + 540         # <= 10min ceiling, 60s margin
    assert 0 < payload["exp"] - payload["iat"] <= 600
    # the signer was handed EXACTLY the "<b64h>.<b64p>" signing input, and the 3rd
    # segment is the base64url of its return
    assert sig_calls == [f"{h_seg}.{p_seg}".encode("ascii")]
    assert _b64url_decode(s_seg) == b"FAKE_SIG::" + f"{h_seg}.{p_seg}".encode("ascii")[:6]


# ---------------------------------------------------------------------------
# The mint runner authenticates with Bearer; the JWT never reaches argv/stdout/stderr
# ---------------------------------------------------------------------------
def test_runner_uses_bearer_and_keeps_jwt_out_of_argv_and_output():
    tx_calls: list[dict] = []
    runner = app_jwt_gh_runner(
        _CLIENT_ID, signer=_fake_signer(), transport=_fake_transport(calls=tx_calls), now=lambda: _NOW
    )
    proc = runner(_MINT_ARGV, _MINT_BODY)
    expected_jwt = build_app_jwt(_CLIENT_ID, signer=_fake_signer(), now=lambda: _NOW)

    assert len(tx_calls) == 1
    call = tx_calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://api.github.com/app/installations/77/access_tokens"
    assert call["headers"]["Authorization"] == f"Bearer {expected_jwt}"  # Bearer, NOT token
    assert call["headers"]["Accept"] == "application/vnd.github+json"
    assert "X-GitHub-Api-Version" in call["headers"]
    assert call["body"] == _MINT_BODY
    # the JWT is in the header ONLY — never the argv, stdout, or stderr
    assert isinstance(proc, subprocess.CompletedProcess)
    assert expected_jwt not in " ".join(proc.args)
    assert expected_jwt not in (proc.stdout or "")
    assert expected_jwt not in (proc.stderr or "")
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# A FRESH JWT is minted per call (no reuse/caching)
# ---------------------------------------------------------------------------
def test_fresh_jwt_per_call():
    ticks = [_NOW, _NOW + 5]
    clock = lambda: ticks.pop(0)
    sig_calls: list[bytes] = []
    tx_calls: list[dict] = []
    runner = app_jwt_gh_runner(
        _CLIENT_ID, signer=_fake_signer(sig_calls), transport=_fake_transport(calls=tx_calls), now=clock
    )
    runner(_MINT_ARGV, _MINT_BODY)
    runner(_MINT_ARGV, _MINT_BODY)
    assert len(sig_calls) == 2  # the signer fired once per call
    assert tx_calls[0]["headers"]["Authorization"] != tx_calls[1]["headers"]["Authorization"]


# ---------------------------------------------------------------------------
# End-to-end: feed the runner to mint_scoped_token; a ~520-char ghs_ token flows opaque
# ---------------------------------------------------------------------------
def test_end_to_end_into_mint_scoped_token_opaque():
    from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest, mint_scoped_token

    long_token = "ghs_" + "x" * 516  # ~520-char stateless installation token (opaque)
    body = json.dumps({"token": long_token, "expires_at": "2026-06-06T13:00:00Z"})
    runner = app_jwt_gh_runner(
        _CLIENT_ID, signer=_fake_signer(), transport=_fake_transport(status=201, body=body), now=lambda: _NOW
    )
    request = TokenRequest(
        repo="creator-engine/creator-engine",
        installation_id=77,
        run_id="run-1",
        policy_sha="a" * 64,
        permissions={"contents": "read", "pull_requests": "write"},
        secret_name="model-provider-key",
        requested_ttl_seconds=600,
    )
    token = mint_scoped_token(request, gh_runner=runner)
    assert isinstance(token, ScopedToken)
    assert token.value == long_token            # verbatim — no length/format assumption
    assert long_token not in repr(token) and "<redacted>" in repr(token)


# ---------------------------------------------------------------------------
# Non-2xx mint surfaces as a ForgeConfigError with the leaked token redacted
# ---------------------------------------------------------------------------
def test_non_2xx_mint_error_is_redacted():
    from creator_engine_validator.forge import ForgeConfigError
    from creator_engine_validator.forge.scoped_token import TokenRequest, mint_scoped_token

    leak = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
    body = f'{{"message":"Bad credentials (token {leak})"}}'
    runner = app_jwt_gh_runner(
        _CLIENT_ID, signer=_fake_signer(), transport=_fake_transport(status=401, body=body), now=lambda: _NOW
    )
    request = TokenRequest(
        repo="creator-engine/creator-engine", installation_id=77, run_id="run-1",
        policy_sha="a" * 64, permissions={"contents": "read"},
        secret_name="k", requested_ttl_seconds=600,
    )
    with pytest.raises(ForgeConfigError) as ei:
        mint_scoped_token(request, gh_runner=runner)
    msg = str(ei.value)
    assert leak not in msg
    assert "<redacted>" in msg


# ---------------------------------------------------------------------------
# Refusals — value-free, BEFORE any signer/transport call
# ---------------------------------------------------------------------------
def test_refuses_empty_client_id():
    with pytest.raises(ForgeConfigRefused):
        app_jwt_gh_runner("", signer=_fake_signer())


def test_refuses_non_mint_argv():
    sig_calls: list[bytes] = []
    tx_calls: list[dict] = []
    runner = app_jwt_gh_runner(
        _CLIENT_ID, signer=_fake_signer(sig_calls), transport=_fake_transport(calls=tx_calls), now=lambda: _NOW
    )
    # a GET / a non-mint path must be refused (this is a single-purpose mint adapter)
    with pytest.raises(ForgeConfigRefused):
        runner(["gh", "api", "-X", "GET", "repos/o/r/installation"], None)
    with pytest.raises(ForgeConfigRefused):
        runner(["gh", "api", "-X", "POST", "repos/o/r/pulls", "--input", "-"], "{}")
    assert sig_calls == [] and tx_calls == []  # refused before any signer/transport call


# ---------------------------------------------------------------------------
# Zero-live — only the injected fakes are ever the transport/signer
# ---------------------------------------------------------------------------
def test_zero_live_network(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("app_jwt_gh_runner must use the injected fakes, not a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    runner = app_jwt_gh_runner(_CLIENT_ID, signer=_fake_signer(), transport=_fake_transport(), now=lambda: _NOW)
    proc = runner(_MINT_ARGV, _MINT_BODY)
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# Purity — a pure-stdlib seam registers no check and adds no backend
# ---------------------------------------------------------------------------
def test_app_jwt_runner_registers_no_check_and_no_backend():
    from creator_engine_validator.checks import registered_checks
    from creator_engine_validator.runner import available_backends

    assert len(registered_checks()) == 53  # G-6 added ce_scope; v3.5-C A-C1..A-C4 added decision_record + storage_tier_finding + peer_authority + forge_claim_dedup; v3.5-E.3 E3-G1 added install_answers; ce-ops#26 added seat_event
    assert available_backends() == ("gvisor-proxy", "local-noop", "openshell", "os-native")  # +openshell (v3.5-A.2a)
