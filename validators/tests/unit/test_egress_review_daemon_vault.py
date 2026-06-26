"""Unit tests for ce-ops#268: vault signer + AppRole login wiring in the SELF-REVIEW broker.

Mirrors ``test_egress_broker_daemon_vault.py`` (the merged self-PUSH broker tests, ce-ops#267).
These tests cover:
(a) A secret_ref seat builds a vault-backed signer (mock AppRole login + vault fetch +
    openssl runner — ZERO live network/crypto).
(b) The AppRole login supplier POSTs the right endpoint and returns the parsed client_token
    (mock urlopen).
(c) A missing-vault-env secret_ref seat fails closed (refuses; never falls back to disk).
(d) A pem_path seat still builds the openssl signer via make_signer_for_seat.
(e) The secret_id, role_id, and token NEVER appear in any raised error message or log output.

ZERO live network calls; ZERO live openssl calls; ZERO live vault calls.
"""
from __future__ import annotations

import io
import json
import subprocess
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import ce_egress_self_review_broker as broker
from egress_broker.config import SeatAppConfig, VaultSecretRef
from egress_broker.minter import EgressSignerError, VaultKvConfig, make_signer_for_seat

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

_FAKE_PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEAFAKEKEYDATA==\n"
    "-----END RSA PRIVATE KEY-----\n"
)

_VAULT_REF = VaultSecretRef(mount="ce-kv", path="forge/dev-3", field="private_key")

_SECRET_ID = "SUPER_SECRET_ID_MUST_NOT_LEAK"
_ROLE_ID = "test-role-id-0000-1111"
_FAKE_TOKEN = "bao.TOKEN_MUST_NOT_LEAK"


def _seat_with_secret_ref() -> SeatAppConfig:
    return SeatAppConfig(
        seat_id="dev-3",
        app_id="99999",
        app_owner="ce-dev-3",
        pem_path=None,
        installation_id=12345,
        secret_ref=_VAULT_REF,
    )


def _seat_with_pem_path() -> SeatAppConfig:
    return SeatAppConfig(
        seat_id="dev-4",
        app_id="4085526",
        app_owner="cedev4vps-coder",
        pem_path="/dev/shm/ce-dev4/ce-forge-dev4.pem",
        installation_id=None,
        secret_ref=None,
    )


def _ok_runner(argv: list[str], *, input: bytes = b"", capture_output: bool = False, pass_fds=()) -> Any:
    """Mock openssl runner: always returns a synthetic signature."""
    return subprocess.CompletedProcess(argv, 0, stdout=b"MOCKSIG::" + input[:4], stderr=b"")


def _vault_env(
    *,
    bao_addr: str = "https://bao.example.internal:8200",
    bao_cacert: str | None = None,
    role_id: str = _ROLE_ID,
    secret_id: str = _SECRET_ID,
) -> dict[str, str]:
    """Return a fake env dict with all required vault vars set."""
    env: dict[str, str] = {
        "BAO_ADDR": bao_addr,
        "BROKER_APPROLE_ROLE_ID": role_id,
        "BROKER_APPROLE_SECRET_ID": secret_id,
    }
    if bao_cacert is not None:
        env["BAO_CACERT"] = bao_cacert
    return env


@contextmanager
def _mock_urlopen(token: str = _FAKE_TOKEN):
    """Context manager: patch urllib.request.urlopen to return a successful AppRole response."""
    resp = MagicMock()
    resp.__enter__ = lambda s: resp
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.return_value = json.dumps(
        {"auth": {"client_token": token, "accessor": "acc-xxx", "lease_duration": 3600}}
    ).encode("utf-8")
    with patch("ce_egress_self_review_broker.urllib.request.urlopen", return_value=resp):
        yield resp


# ---------------------------------------------------------------------------
# (a) secret_ref seat builds a vault-backed signer (zero live I/O)
# ---------------------------------------------------------------------------

class TestSecretRefSeatBuildsVaultSigner:
    """A seat with secret_ref must produce a callable signer via the vault path."""

    def test_vault_backed_signer_is_callable(self):
        """_build_signer returns a callable when the seat has secret_ref and env vars are set."""
        seat = _seat_with_secret_ref()
        env = _vault_env()

        with _mock_urlopen():
            # _build_signer must NOT call urlopen at construction time — urlopen is invoked
            # only on the first sign() via the token_supplier.
            signer = broker._build_signer(seat, env=env)

        assert callable(signer), "_build_signer must return a callable signer"

    def test_vault_backed_signer_produces_signature_with_mock_fetcher(self):
        """Signing with a vault-backed signer (mocked AppRole login + vault fetch) works end-to-end."""
        seat = _seat_with_secret_ref()
        env = _vault_env()

        # Construct via make_signer_for_seat with a mock fetcher + runner to exercise the
        # sign path without live openssl/vault.
        def _mock_fetcher(_ref):
            return _FAKE_PEM

        with _mock_urlopen():
            vcfg = VaultKvConfig(
                address=env["BAO_ADDR"],
                token_supplier=broker._approle_token_supplier(
                    _ROLE_ID, _SECRET_ID, env["BAO_ADDR"], None
                ),
                ca_bundle=None,
                verify_tls=True,
            )
            signer = make_signer_for_seat(
                seat, vault_config=vcfg, vault_fetcher=_mock_fetcher, runner=_ok_runner
            )

        sig = signer(b"test-payload")
        assert isinstance(sig, bytes) and sig, "vault-backed signer must produce a non-empty bytes signature"


# ---------------------------------------------------------------------------
# (b) AppRole login supplier — correct endpoint + token parsing
# ---------------------------------------------------------------------------

class TestAppRoleTokenSupplier:
    """_approle_token_supplier posts to the right URL and returns the client_token."""

    def test_posts_to_correct_endpoint(self):
        """The supplier POSTs to {bao_addr}/v1/auth/approle/login."""
        bao_addr = "https://bao.example.internal:8200"
        captured_requests: list[Any] = []

        resp = MagicMock()
        resp.__enter__ = lambda s: resp
        resp.__exit__ = MagicMock(return_value=False)
        resp.read.return_value = json.dumps(
            {"auth": {"client_token": _FAKE_TOKEN}}
        ).encode("utf-8")

        def fake_urlopen(req, *, timeout=None, context=None):
            captured_requests.append(req)
            return resp

        with patch("ce_egress_self_review_broker.urllib.request.urlopen", side_effect=fake_urlopen):
            supplier = broker._approle_token_supplier(_ROLE_ID, _SECRET_ID, bao_addr, None)
            token = supplier()

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert req.get_full_url() == f"{bao_addr}/v1/auth/approle/login"
        assert req.get_method() == "POST"
        assert token == _FAKE_TOKEN

    def test_returns_parsed_client_token(self):
        """The supplier returns exactly the client_token from the response."""
        with _mock_urlopen(token="bao.SPECIAL_TOKEN"):
            supplier = broker._approle_token_supplier(
                _ROLE_ID, _SECRET_ID, "https://bao.example.internal:8200", None
            )
            token = supplier()
        assert token == "bao.SPECIAL_TOKEN"

    def test_posts_role_id_and_secret_id_in_body(self):
        """The supplier sends role_id and secret_id in the JSON POST body."""
        captured_bodies: list[bytes] = []

        resp = MagicMock()
        resp.__enter__ = lambda s: resp
        resp.__exit__ = MagicMock(return_value=False)
        resp.read.return_value = json.dumps({"auth": {"client_token": _FAKE_TOKEN}}).encode("utf-8")

        def fake_urlopen(req, *, timeout=None, context=None):
            captured_bodies.append(req.data)
            return resp

        with patch("ce_egress_self_review_broker.urllib.request.urlopen", side_effect=fake_urlopen):
            supplier = broker._approle_token_supplier(
                _ROLE_ID, _SECRET_ID, "https://bao.example.internal:8200", None
            )
            supplier()

        body = json.loads(captured_bodies[0].decode("utf-8"))
        assert body["role_id"] == _ROLE_ID
        assert body["secret_id"] == _SECRET_ID

    def test_raises_on_http_error(self):
        """An HTTP error from the vault raises EgressSignerError (fail-closed)."""
        import urllib.error
        with patch(
            "ce_egress_self_review_broker.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://bao.example.internal:8200/v1/auth/approle/login",
                403, "Forbidden", {}, None
            ),
        ):
            supplier = broker._approle_token_supplier(
                _ROLE_ID, _SECRET_ID, "https://bao.example.internal:8200", None
            )
            with pytest.raises(EgressSignerError, match="403"):
                supplier()

    def test_raises_on_transport_error(self):
        """A network-level error raises EgressSignerError (fail-closed)."""
        import urllib.error
        with patch(
            "ce_egress_self_review_broker.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            supplier = broker._approle_token_supplier(
                _ROLE_ID, _SECRET_ID, "https://bao.example.internal:8200", None
            )
            with pytest.raises(EgressSignerError, match="transport error"):
                supplier()

    def test_raises_on_missing_client_token(self):
        """A response without auth.client_token raises EgressSignerError."""
        resp = MagicMock()
        resp.__enter__ = lambda s: resp
        resp.__exit__ = MagicMock(return_value=False)
        resp.read.return_value = json.dumps({"auth": {}}).encode("utf-8")
        with patch("ce_egress_self_review_broker.urllib.request.urlopen", return_value=resp):
            supplier = broker._approle_token_supplier(
                _ROLE_ID, _SECRET_ID, "https://bao.example.internal:8200", None
            )
            with pytest.raises(EgressSignerError, match="client_token"):
                supplier()


# ---------------------------------------------------------------------------
# (c) Missing vault env — secret_ref seat fails closed
# ---------------------------------------------------------------------------

class TestMissingVaultEnvFailsClosed:
    """A secret_ref seat with any missing vault env var must refuse to start."""

    def test_missing_bao_addr_raises_startup_error(self):
        seat = _seat_with_secret_ref()
        env = _vault_env()
        del env["BAO_ADDR"]
        with pytest.raises(broker._BrokerStartupError, match="BAO_ADDR"):
            broker._build_signer(seat, env=env)

    def test_missing_role_id_raises_startup_error(self):
        seat = _seat_with_secret_ref()
        env = _vault_env()
        del env["BROKER_APPROLE_ROLE_ID"]
        with pytest.raises(broker._BrokerStartupError, match="BROKER_APPROLE_ROLE_ID"):
            broker._build_signer(seat, env=env)

    def test_missing_secret_id_raises_startup_error(self):
        seat = _seat_with_secret_ref()
        env = _vault_env()
        del env["BROKER_APPROLE_SECRET_ID"]
        with pytest.raises(broker._BrokerStartupError, match="BROKER_APPROLE_SECRET_ID"):
            broker._build_signer(seat, env=env)

    def test_all_missing_raises_startup_error_listing_all(self):
        seat = _seat_with_secret_ref()
        env: dict[str, str] = {}
        with pytest.raises(broker._BrokerStartupError) as exc_info:
            broker._build_signer(seat, env=env)
        msg = str(exc_info.value)
        assert "BAO_ADDR" in msg
        assert "BROKER_APPROLE_ROLE_ID" in msg
        assert "BROKER_APPROLE_SECRET_ID" in msg

    def test_fallback_vault_addr_accepted(self):
        """VAULT_ADDR is accepted as a fallback for BAO_ADDR."""
        seat = _seat_with_secret_ref()
        env = _vault_env()
        del env["BAO_ADDR"]
        env["VAULT_ADDR"] = "https://vault.example.internal:8200"
        with _mock_urlopen():
            signer = broker._build_signer(seat, env=env)
        assert callable(signer)

    def test_does_not_fall_back_to_pem_path_when_secret_ref_set(self):
        """A secret_ref seat with missing vault vars must NEVER silently use pem_path."""
        seat = SeatAppConfig(
            seat_id="dev-3",
            app_id="99999",
            app_owner="ce-dev-3",
            pem_path="/dev/shm/ce-dev3/pem.pem",  # also has pem_path
            installation_id=None,
            secret_ref=_VAULT_REF,
        )
        env: dict[str, str] = {}  # no vault vars
        with pytest.raises(broker._BrokerStartupError):
            broker._build_signer(seat, env=env)


# ---------------------------------------------------------------------------
# (d) pem_path seat still builds an openssl signer
# ---------------------------------------------------------------------------

class TestPemPathSeatBuildsOpensslSigner:
    """A seat with pem_path (no secret_ref) must still produce a working openssl signer."""

    def test_pem_path_seat_returns_callable_signer(self):
        seat = _seat_with_pem_path()
        env: dict[str, str] = {}  # no vault vars needed
        signer = broker._build_signer(seat, env=env)
        assert callable(signer), "_build_signer for pem_path seat must return a callable"

    def test_pem_path_signer_invokes_openssl(self):
        """The pem_path signer calls openssl with the correct pem_path."""
        seat = _seat_with_pem_path()
        captured: list[list[str]] = []

        def capturing_runner(argv, *, input=b"", capture_output=False, pass_fds=()):
            captured.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, stdout=b"MOCKSIG", stderr=b"")

        signer = make_signer_for_seat(seat, vault_config=None, runner=capturing_runner)
        sig = signer(b"payload")
        assert sig == b"MOCKSIG"
        assert len(captured) == 1
        assert seat.pem_path in captured[0]


# ---------------------------------------------------------------------------
# (e) No secret_id / token leakage in error messages or log output
# ---------------------------------------------------------------------------

class TestNoSecretLeakage:
    """secret_id, token, and role_id must never appear in raised error messages."""

    def test_http_error_message_does_not_contain_secret_id(self):
        """An HTTP 403 error from the login endpoint must not include the secret_id."""
        import urllib.error
        with patch(
            "ce_egress_self_review_broker.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://bao.example.internal:8200/v1/auth/approle/login",
                403, "Forbidden", {}, None,
            ),
        ):
            supplier = broker._approle_token_supplier(
                _ROLE_ID, _SECRET_ID, "https://bao.example.internal:8200", None
            )
            with pytest.raises(EgressSignerError) as exc_info:
                supplier()
        msg = str(exc_info.value)
        assert _SECRET_ID not in msg, f"secret_id must not appear in error: {msg}"

    def test_http_error_message_does_not_contain_token(self):
        """An empty-token error must not include the token value."""
        resp = MagicMock()
        resp.__enter__ = lambda s: resp
        resp.__exit__ = MagicMock(return_value=False)
        resp.read.return_value = json.dumps({"auth": {}}).encode("utf-8")
        with patch("ce_egress_self_review_broker.urllib.request.urlopen", return_value=resp):
            supplier = broker._approle_token_supplier(
                _ROLE_ID, _SECRET_ID, "https://bao.example.internal:8200", None
            )
            with pytest.raises(EgressSignerError) as exc_info:
                supplier()
        msg = str(exc_info.value)
        assert _FAKE_TOKEN not in msg
        assert _SECRET_ID not in msg

    def test_startup_error_does_not_contain_secret_id(self):
        """The startup error for a missing vault env must not include the secret_id."""
        seat = _seat_with_secret_ref()
        env = {"BROKER_APPROLE_SECRET_ID": _SECRET_ID}  # missing addr + role_id
        with pytest.raises(broker._BrokerStartupError) as exc_info:
            broker._build_signer(seat, env=env)
        msg = str(exc_info.value)
        assert _SECRET_ID not in msg, f"secret_id must not appear in startup error: {msg}"

    def test_log_output_contains_only_safe_info(self, capsys):
        """Startup log lines must only contain seat_id and 'vault-backed'/'pem-backed'."""
        # vault-backed seat
        seat_vault = _seat_with_secret_ref()
        env = _vault_env()
        with _mock_urlopen():
            broker._build_signer(seat_vault, env=env)
        stderr = capsys.readouterr().err
        assert "vault-backed" in stderr
        assert _SECRET_ID not in stderr
        assert _ROLE_ID not in stderr
        assert _FAKE_TOKEN not in stderr
        assert "dev-3" in stderr

        # pem-backed seat
        seat_pem = _seat_with_pem_path()
        broker._build_signer(seat_pem, env={})
        stderr2 = capsys.readouterr().err
        assert "pem-backed" in stderr2
        assert "dev-4" in stderr2


# ---------------------------------------------------------------------------
# Integration: submit_self_review routes the vault fail-closed into a refusal
# ---------------------------------------------------------------------------

class TestSubmitSelfReviewVaultRouting:
    """submit_self_review with a secret_ref seat + missing vault env refuses fail-closed."""

    def _vault_config(self):
        from egress_broker.config import load_broker_config
        return load_broker_config(
            {
                "repo": "creator-engine/creator-engine",
                "installation_owner": "creator-engine",
                "audit_log": "",
                "policy": {
                    "base_branch": "main",
                    "allowed_branch_namespaces": ["ce-"],
                    "forbidden_branches": [],
                    "authorized_emails": [],
                    "authorized_logins": ["cedev3vps-coder"],
                    "max_pushes_per_window": 10,
                    "window_seconds": 3600,
                },
                "seats": {
                    "dev-3": {
                        "app_id": "99999",
                        "app_owner": "ce-dev-3",
                        "secret_ref": {
                            "mount": "ce-kv",
                            "path": "forge/dev-3",
                            "field": "private_key",
                        },
                        "installation_id": 12345,
                    }
                },
            }
        )

    def test_secret_ref_seat_missing_env_refuses_fail_closed(self, monkeypatch):
        """A secret_ref seat with missing vault env yields a SelfReviewRefused (never posts)."""
        for var in ("BAO_ADDR", "VAULT_ADDR", "BROKER_APPROLE_ROLE_ID", "BROKER_APPROLE_SECRET_ID"):
            monkeypatch.delenv(var, raising=False)

        spawned: list[object] = []
        request = broker.SelfReviewRequest(
            seat_id="dev-3",
            pr_number=7,
            head_sha="a" * 40,
            event="COMMENT",
            body="x",
        )
        with pytest.raises(broker.SelfReviewRefused) as exc_info:
            broker.submit_self_review(
                request,
                config=self._vault_config(),
                resolve_id_fn=lambda seat: 1,
                mint_fn=lambda req: None,
                gh_spawn=lambda *a: spawned.append(a),
                resolve_author_fn=lambda repo, pr: "some-other-author",
            )
        assert spawned == []
        msg = str(exc_info.value)
        assert "BAO_ADDR" in msg
        assert _SECRET_ID not in msg
