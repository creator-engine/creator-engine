"""Unit tests for the v3 G-2.2 forge-native scoped-token minter.

``mint_scoped_token`` mints a JIT, least-privilege, time-boxed GitHub App installation
access token scoped to a single repo + an explicit permission subset, and refuses an
over-broad / un-time-boxed request BEFORE any forge call. ``revoke_scoped_token`` releases
the credential the instant the run no longer needs it. All forge I/O goes through an
injectable ``GhRunner``; these tests inject a fake runner returning canned ``gh api`` JSON
and perform ZERO live mint / network / subprocess.
"""

import json
import subprocess

import pytest

from creator_engine_validator.forge import ForgeConfigError
from creator_engine_validator.forge.scoped_token import (
    MAX_TTL_SECONDS,
    ScopedToken,
    TokenMintRefused,
    TokenRequest,
    mint_scoped_token,
    revoke_scoped_token,
)

_POLICY_SHA = "a" * 64
_REPO = "creator-engine/creator-engine"


def _request(**overrides) -> TokenRequest:
    base = dict(
        repo=_REPO,
        installation_id=42,
        run_id="run-1",
        policy_sha=_POLICY_SHA,
        permissions={"contents": "read", "pull_requests": "write"},
        secret_name="model-provider-key",
        requested_ttl_seconds=600,
    )
    base.update(overrides)
    return TokenRequest(**base)


def _fake_runner(*, token="ghs_minted_secret", expires_at="2026-06-03T15:00:00Z", mint_rc=0, revoke_rc=0, err="boom"):
    """A GhRunner that answers the mint POST and the revoke DELETE from canned data.

    ``err`` is the stderr returned on a non-zero exit (override it to a token-bearing
    stderr to exercise the G-3.7.0b redaction of an exception message).
    """
    calls: list[list[str]] = []
    inputs: list[str | None] = []

    def run(argv, input_text=None):
        calls.append(list(argv))
        inputs.append(input_text)
        if "DELETE" in argv:
            return subprocess.CompletedProcess(argv, revoke_rc, stdout="", stderr="" if revoke_rc == 0 else err)
        payload = {"token": token, "expires_at": expires_at}
        return subprocess.CompletedProcess(
            argv, mint_rc,
            stdout=json.dumps(payload) if mint_rc == 0 else "",
            stderr="" if mint_rc == 0 else err,
        )

    run.calls = calls  # type: ignore[attr-defined]
    run.inputs = inputs  # type: ignore[attr-defined]
    return run


# ---------------------------------------------------------------------------
# Happy mint — scoped to one repo + an explicit least-privilege permission set
# ---------------------------------------------------------------------------
def test_mint_scopes_to_single_repo_and_explicit_permissions():
    runner = _fake_runner()
    token = mint_scoped_token(_request(), gh_runner=runner)
    assert isinstance(token, ScopedToken)
    assert token.expires_at == "2026-06-03T15:00:00Z"
    assert token.run_id == "run-1" and token.policy_sha == _POLICY_SHA
    assert token.secret_name == "model-provider-key"
    assert token.permissions == (("contents", "read"), ("pull_requests", "write"))
    argv = runner.calls[0]
    assert argv[:4] == ["gh", "api", "-X", "POST"]
    assert argv[4] == "app/installations/42/access_tokens"
    body = json.loads(runner.inputs[0])
    assert body == {
        "repositories": ["creator-engine"],
        "permissions": {"contents": "read", "pull_requests": "write"},
    }


# ---------------------------------------------------------------------------
# Least-privilege + time-box guardrails — refuse BEFORE any forge call
# ---------------------------------------------------------------------------
def test_refuses_admin_permission_level_before_any_call():
    runner = _fake_runner()
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(permissions={"contents": "admin"}), gh_runner=runner)
    assert runner.calls == []


def test_refuses_forbidden_scope_before_any_call():
    runner = _fake_runner()
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(permissions={"administration": "read"}), gh_runner=runner)
    assert runner.calls == []


def test_refuses_empty_permissions_before_any_call():
    runner = _fake_runner()
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(permissions={}), gh_runner=runner)
    assert runner.calls == []


def test_refuses_ttl_over_one_hour_before_any_call():
    runner = _fake_runner()
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(requested_ttl_seconds=MAX_TTL_SECONDS + 1), gh_runner=runner)
    assert runner.calls == []


def test_refuses_non_positive_ttl_before_any_call():
    runner = _fake_runner()
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(requested_ttl_seconds=0), gh_runner=runner)
    assert runner.calls == []


def test_refuses_non_hex_policy_sha_before_any_call():
    runner = _fake_runner()
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(policy_sha="not-a-64-hex-digest"), gh_runner=runner)
    assert runner.calls == []


def test_refuses_malformed_repo_and_bad_installation():
    runner = _fake_runner()
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(repo="no-slash"), gh_runner=runner)
    with pytest.raises(TokenMintRefused):
        mint_scoped_token(_request(installation_id=0), gh_runner=runner)
    assert runner.calls == []


# ---------------------------------------------------------------------------
# Transport failure is distinct from a policy refusal
# ---------------------------------------------------------------------------
def test_mint_transport_failure_raises_forge_config_error():
    runner = _fake_runner(mint_rc=1)
    with pytest.raises(ForgeConfigError):
        mint_scoped_token(_request(), gh_runner=runner)


# ---------------------------------------------------------------------------
# Revoke — early revocation (don't wait out the <=1h ttl)
# ---------------------------------------------------------------------------
def test_revoke_issues_delete_and_returns_true():
    runner = _fake_runner()
    token = mint_scoped_token(_request(), gh_runner=runner)
    assert revoke_scoped_token(token, gh_runner=runner) is True
    assert runner.calls[-1] == ["gh", "api", "-X", "DELETE", "installation/token"]


def test_revoke_transport_failure_raises_forge_config_error():
    runner = _fake_runner(revoke_rc=1)
    token = mint_scoped_token(_request(), gh_runner=runner)
    with pytest.raises(ForgeConfigError):
        revoke_scoped_token(token, gh_runner=runner)


# ---------------------------------------------------------------------------
# Secret hygiene — the value is usable but never leaks in a repr/str
# ---------------------------------------------------------------------------
def test_token_value_is_redacted_from_repr_and_str():
    token = mint_scoped_token(_request(), gh_runner=_fake_runner(token="ghs_super_secret"))
    assert token.value == "ghs_super_secret"  # available to the revoker, never displayed
    assert "ghs_super_secret" not in repr(token)
    assert "ghs_super_secret" not in str(token)
    assert "<redacted>" in repr(token)


# ---------------------------------------------------------------------------
# G-3.7.0b — a leaked credential in gh stderr is masked in the raised exception
# ---------------------------------------------------------------------------
_LEAK_TOKEN = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
_LEAK_STDERR = f"HTTP 401: Bad credentials (token {_LEAK_TOKEN})"


def test_mint_error_message_redacts_leaked_token():
    runner = _fake_runner(mint_rc=1, err=_LEAK_STDERR)
    with pytest.raises(ForgeConfigError) as ei:
        mint_scoped_token(_request(), gh_runner=runner)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg
    assert "<redacted>" in msg
    assert _REPO in msg  # the non-secret identifier remains for diagnosis


def test_revoke_error_message_redacts_leaked_token():
    runner = _fake_runner(revoke_rc=1, err=_LEAK_STDERR)
    token = mint_scoped_token(_request(), gh_runner=runner)
    with pytest.raises(ForgeConfigError) as ei:
        revoke_scoped_token(token, gh_runner=runner)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg
    assert "<redacted>" in msg


# ---------------------------------------------------------------------------
# G-3.7.0b — opaque token: a ~520-char ghs_APPID_JWT round-trips mint VERBATIM
# (no length/format assumption), and is still redacted from repr/str.
# ---------------------------------------------------------------------------
def test_mint_treats_token_as_opaque_no_length_or_format_assumption():
    long_tok = "ghs_654321_eyJ" + "Q" * 240 + "." + "Z" * 240 + ".abcDEF12"
    assert len(long_tok) > 500  # the stateless installation-token brownout shape
    token = mint_scoped_token(_request(), gh_runner=_fake_runner(token=long_tok))
    assert token.value == long_tok  # verbatim — no truncation / format mangling
    assert long_tok not in repr(token) and long_tok not in str(token)
    assert "<redacted>" in repr(token)


# ---------------------------------------------------------------------------
# Zero live network — only the injected runner is ever the transport
# ---------------------------------------------------------------------------
def test_zero_live_network(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("mint/revoke must not touch a live forge")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    runner = _fake_runner()
    token = mint_scoped_token(_request(), gh_runner=runner)
    assert revoke_scoped_token(token, gh_runner=runner) is True
    assert len(runner.calls) == 2  # mint + revoke; the injected fake was the only transport
