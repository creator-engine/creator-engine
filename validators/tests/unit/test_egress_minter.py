"""Unit tests for the generalized per-App egress minter + the openssl RS256 signer.

``egress_broker.minter`` generalizes the existing ``mint-forge-token`` pattern across the
per-dev Apps: given a :class:`~egress_broker.config.SeatAppConfig`, it discovers the
installation id when absent (dev-4), authenticates AS that App with a short-lived JWT, and
mints a least-privilege installation token through the frozen ``forge.scoped_token`` +
``forge.app_jwt_runner`` seams. The App private key never enters the process — it stays behind
the ``openssl dgst -sha256 -sign`` signer. These tests inject fakes; ZERO live crypto/network.
"""

import json
import subprocess

import pytest

from creator_engine_validator.forge.scoped_token import ScopedToken
from egress_broker.config import SeatAppConfig
from egress_broker.minter import openssl_signer, mint_egress_token

_NOW = 1_700_000_000
_PERMS = {"contents": "write", "pull_requests": "write"}
_ESC = (("contents", "write"),)


def _signer(signing_input: bytes) -> bytes:
    return b"SIG::" + signing_input[:6]


def _seat(installation_id=None):
    return SeatAppConfig(
        seat_id="dev-4",
        app_id="4085526",
        app_owner="cedev4vps-coder",
        pem_path="/dev/shm/ce-dev4/ce-forge-dev4.pem",
        installation_id=installation_id,
    )


def _transport(*, token="ghs_minted", installations=None, calls=None):
    """One fake serving BOTH the discovery GET and the mint POST, keyed on the URL/method."""
    def transport(method, url, headers, body):
        if calls is not None:
            calls.append({"method": method, "url": url})
        if method == "GET" and "app/installations" in url:
            insts = installations if installations is not None else [
                {"id": 555, "account": {"login": "creator-engine"}}
            ]
            return 200, json.dumps(insts)
        if method == "POST" and url.endswith("/access_tokens"):
            return 201, json.dumps({"token": token, "expires_at": "2026-06-20T13:00:00Z"})
        raise AssertionError(f"unexpected request {method} {url}")

    return transport


def _mint(seat, **over):
    kwargs = dict(
        repo="creator-engine/creator-engine",
        installation_owner="creator-engine",
        signer=_signer,
        run_id="egress-dev-4-aaaaaaaaaaaa",
        policy_sha="a" * 64,
        permissions=_PERMS,
        escalation_authority=_ESC,
        ttl_seconds=900,
        secret_name="forge_egress_push",
        now=lambda: _NOW,
    )
    kwargs.update(over)
    return mint_egress_token(seat, **kwargs)


# ---------------------------------------------------------------------------
# openssl signer — PEM read by openssl (never enters the process)
# ---------------------------------------------------------------------------
def test_openssl_signer_signs_via_stdin_and_keeps_pem_out_of_process():
    calls = []

    def runner(argv, input=None, capture_output=False):
        calls.append((list(argv), input))
        return subprocess.CompletedProcess(argv, 0, stdout=b"RAWSIG")

    sig = openssl_signer("/dev/shm/ce-dev4/ce-forge-dev4.pem", runner=runner)(b"signing-input")
    assert sig == b"RAWSIG"
    argv, stdin = calls[0]
    assert argv == ["openssl", "dgst", "-sha256", "-sign", "/dev/shm/ce-dev4/ce-forge-dev4.pem"]
    assert stdin == b"signing-input"  # the signing input is on STDIN; the PEM is only a path


def test_openssl_signer_nonzero_exit_refuses():
    def runner(argv, input=None, capture_output=False):
        return subprocess.CompletedProcess(argv, 1, stdout=b"", stderr=b"bad key")

    with pytest.raises(Exception):
        openssl_signer("/x.pem", runner=runner)(b"in")


def test_openssl_signer_empty_signature_refuses():
    def runner(argv, input=None, capture_output=False):
        return subprocess.CompletedProcess(argv, 0, stdout=b"")

    with pytest.raises(Exception):
        openssl_signer("/x.pem", runner=runner)(b"in")


# ---------------------------------------------------------------------------
# Mint with a recorded installation id — discovery is skipped
# ---------------------------------------------------------------------------
def test_mint_with_recorded_installation_skips_discovery():
    calls: list[dict] = []
    token = _mint(_seat(installation_id=4242), transport=_transport(calls=calls))
    assert isinstance(token, ScopedToken)
    assert token.value == "ghs_minted"
    # only the mint POST was made — no discovery GET
    assert [c["method"] for c in calls] == ["POST"]
    assert calls[0]["url"].endswith("/app/installations/4242/access_tokens")


# ---------------------------------------------------------------------------
# Mint with NO installation id — discover first, then mint (the dev-4 case)
# ---------------------------------------------------------------------------
def test_mint_without_installation_discovers_then_mints():
    calls: list[dict] = []
    token = _mint(_seat(installation_id=None), transport=_transport(calls=calls))
    assert token.value == "ghs_minted"
    assert [c["method"] for c in calls] == ["GET", "POST"]
    assert "app/installations" in calls[0]["url"]
    assert calls[1]["url"].endswith("/app/installations/555/access_tokens")  # discovered id 555


def test_minted_token_value_is_redacted_in_repr():
    token = _mint(_seat(installation_id=4242), transport=_transport(token="ghs_secret_value"))
    assert "ghs_secret_value" not in repr(token)
    assert "<redacted>" in repr(token)


# ---------------------------------------------------------------------------
# The mint requests EXACTLY the least-privilege subset (delegated to scoped_token)
# ---------------------------------------------------------------------------
def test_mint_refuses_an_out_of_ceiling_permission():
    from creator_engine_validator.forge.scoped_token import TokenMintRefused

    # admin:write is escalation-gated with no bound authority → the frozen minter refuses
    with pytest.raises(TokenMintRefused):
        _mint(_seat(installation_id=1), permissions={"administration": "write"}, escalation_authority=())


def test_discovery_failure_propagates_before_any_mint():
    from egress_broker.installation import InstallationDiscoveryError

    # no installation for the org → discovery refuses, mint never happens
    tx = _transport(installations=[{"id": 1, "account": {"login": "someone-else"}}])
    with pytest.raises(InstallationDiscoveryError):
        _mint(_seat(installation_id=None), transport=tx)
