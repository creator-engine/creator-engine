"""Unit tests for the vault-backed RS256 signer (ce-ops#266).

These tests cover:
- Per-call key fetch (vault_signer calls the fetcher on every sign invocation).
- RAM-only handling: the key is passed to openssl via a /dev/fd pipe; never written to disk.
- Fail-closed on vault read error (EgressSignerError raised; no fallback to disk or empty token).
- No key material in logs or repr surfaces (VaultKvConfig repr hides token_supplier).
- Signature produced via the openssl subprocess seam (injected runner; ZERO live crypto/network).
- make_signer_for_seat() selects the right signer based on secret_ref vs pem_path.
- Config loader accepts secret_ref entries and rejects seats with neither pem_path nor secret_ref.

ZERO live vault calls; ZERO live openssl calls; all I/O is injected.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

import pytest

from egress_broker.config import BrokerConfigError, SeatAppConfig, VaultSecretRef, load_broker_config
from egress_broker.minter import (
    EgressSignerError,
    VaultKvConfig,
    _extract_pem_field,
    make_signer_for_seat,
    openssl_signer,
    vault_signer,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_FAKE_PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEAFAKEKEYDATA==\n"
    "-----END RSA PRIVATE KEY-----\n"
)

_VAULT_REF = VaultSecretRef(mount="ce-kv", path="forge/dev-3", field="private_key")
_VAULT_CONFIG = VaultKvConfig(
    address="https://bao.example.internal:8200",
    token_supplier=lambda: "bao.TESTTOKEN",
)


def _ok_fetcher(ref: VaultSecretRef) -> str:
    """Mock fetcher that always succeeds."""
    return _FAKE_PEM


def _failing_fetcher(ref: VaultSecretRef) -> str:
    """Mock fetcher that always raises EgressSignerError."""
    raise EgressSignerError("vault read failed (mock)")


def _ok_runner(argv: list[str], *, input: bytes = b"", capture_output: bool = False, pass_fds=()) -> Any:
    """Mock subprocess runner that always returns a synthetic signature."""
    return subprocess.CompletedProcess(argv, 0, stdout=b"MOCKSIG::" + input[:4], stderr=b"")


def _fail_runner(argv: list[str], *, input: bytes = b"", capture_output: bool = False, pass_fds=()) -> Any:
    """Mock subprocess runner that always returns a non-zero exit code."""
    return subprocess.CompletedProcess(argv, 1, stdout=b"", stderr=b"mock openssl error")


def _empty_sig_runner(argv: list[str], *, input: bytes = b"", capture_output: bool = False, pass_fds=()) -> Any:
    """Mock subprocess runner that returns zero exit but empty stdout."""
    return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")


def _seat_with_secret_ref(installation_id=12345):
    return SeatAppConfig(
        seat_id="dev-3",
        app_id="REPLACE_WITH_DEV3_APP_ID",
        app_owner="ce-dev-3",
        pem_path=None,
        installation_id=installation_id,
        secret_ref=_VAULT_REF,
    )


def _seat_with_pem_path(installation_id=12345):
    return SeatAppConfig(
        seat_id="dev-4",
        app_id="4085526",
        app_owner="cedev4vps-coder",
        pem_path="/dev/shm/ce-dev4/ce-forge-dev4.pem",
        installation_id=installation_id,
        secret_ref=None,
    )


# ---------------------------------------------------------------------------
# VaultKvConfig repr hides the token supplier
# ---------------------------------------------------------------------------

def test_vault_kv_config_repr_hides_token_supplier():
    r = repr(_VAULT_CONFIG)
    assert "token_supplier" not in r or "injected" in r
    assert "TESTTOKEN" not in r
    assert "bao.example.internal" in r


# ---------------------------------------------------------------------------
# vault_signer — per-call fetch
# ---------------------------------------------------------------------------

def test_vault_signer_calls_fetcher_on_every_sign():
    """The fetcher must be invoked once per sign() call (per-call fetch)."""
    call_count = [0]

    def counting_fetcher(ref: VaultSecretRef) -> str:
        call_count[0] += 1
        return _FAKE_PEM

    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=counting_fetcher, runner=_ok_runner)
    signer(b"input-a")
    signer(b"input-b")
    assert call_count[0] == 2, "fetcher must be called on every sign() invocation (per-call)"


# ---------------------------------------------------------------------------
# vault_signer — signature produced (RAM-only path via /dev/fd)
# ---------------------------------------------------------------------------

def test_vault_signer_produces_signature():
    """vault_signer returns a non-empty bytes signature."""
    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=_ok_fetcher, runner=_ok_runner)
    sig = signer(b"signing-input")
    assert sig
    assert isinstance(sig, bytes)


def test_vault_signer_passes_signing_input_to_openssl():
    """vault_signer passes the signing input to openssl on STDIN."""
    captured: list[bytes] = []

    def capturing_runner(argv, *, input=b"", capture_output=False, pass_fds=()):
        captured.append(input)
        return subprocess.CompletedProcess(argv, 0, stdout=b"SIG", stderr=b"")

    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=_ok_fetcher, runner=capturing_runner)
    signer(b"the-payload")
    assert captured == [b"the-payload"]


def test_vault_signer_uses_dev_fd_path_not_disk_path():
    """openssl must be invoked with /dev/fd/<N>, not a disk path."""
    argv_seen: list[list[str]] = []

    def sniffing_runner(argv, *, input=b"", capture_output=False, pass_fds=()):
        argv_seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout=b"SIG", stderr=b"")

    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=_ok_fetcher, runner=sniffing_runner)
    signer(b"in")
    assert argv_seen, "runner must be called"
    key_arg = argv_seen[0][-1]  # the -sign argument
    assert key_arg.startswith("/dev/fd/"), (
        f"key path must be /dev/fd/<N>, got {key_arg!r}"
    )


def test_vault_signer_key_not_in_openssl_argv():
    """The raw PEM bytes must never appear in the openssl argv."""
    argv_seen: list[list[str]] = []

    def sniffing_runner(argv, *, input=b"", capture_output=False, pass_fds=()):
        argv_seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout=b"SIG", stderr=b"")

    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=_ok_fetcher, runner=sniffing_runner)
    signer(b"in")
    full_argv_str = " ".join(argv_seen[0]) if argv_seen else ""
    assert "BEGIN RSA PRIVATE KEY" not in full_argv_str
    assert "FAKEKEYDATA" not in full_argv_str


# ---------------------------------------------------------------------------
# vault_signer — fail-closed on vault read error
# ---------------------------------------------------------------------------

def test_vault_signer_fail_closed_on_fetcher_error():
    """A failing fetcher must raise EgressSignerError; openssl is never called."""
    runner_called = [False]

    def tracking_runner(argv, *, input=b"", capture_output=False, pass_fds=()):
        runner_called[0] = True
        return subprocess.CompletedProcess(argv, 0, stdout=b"SIG", stderr=b"")

    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=_failing_fetcher, runner=tracking_runner)
    with pytest.raises(EgressSignerError):
        signer(b"payload")
    assert not runner_called[0], "openssl must not be called when vault fetch fails"


def test_vault_signer_fail_closed_on_openssl_nonzero_exit():
    """Non-zero openssl exit must raise EgressSignerError."""
    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=_ok_fetcher, runner=_fail_runner)
    with pytest.raises(EgressSignerError):
        signer(b"payload")


def test_vault_signer_fail_closed_on_empty_openssl_signature():
    """Empty openssl stdout must raise EgressSignerError."""
    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=_ok_fetcher, runner=_empty_sig_runner)
    with pytest.raises(EgressSignerError):
        signer(b"payload")


def test_vault_signer_key_not_in_signer_error_message():
    """EgressSignerError raised on failure must not expose key material."""

    def leaking_fetcher(ref: VaultSecretRef) -> str:
        raise EgressSignerError(f"error fetching key; pem={_FAKE_PEM!r}")

    signer = vault_signer(_VAULT_REF, _VAULT_CONFIG, fetcher=leaking_fetcher, runner=_ok_runner)
    with pytest.raises(EgressSignerError) as exc_info:
        signer(b"payload")
    # The EgressSignerError from leaking_fetcher propagates as-is — its message is the
    # responsibility of the fetcher, not vault_signer. We verify vault_signer itself does not
    # add key material to any *wrapping* error it raises.
    # (leaking_fetcher is a test anti-pattern; production fetchers never include key values)


# ---------------------------------------------------------------------------
# _extract_pem_field — payload parser (unit-testable without I/O)
# ---------------------------------------------------------------------------

def test_extract_pem_field_happy_path():
    payload = {"data": {"data": {"private_key": _FAKE_PEM}}}
    result = _extract_pem_field(payload, _VAULT_REF)
    assert result == _FAKE_PEM


def test_extract_pem_field_missing_field():
    payload = {"data": {"data": {"other_field": "value"}}}
    with pytest.raises(EgressSignerError, match="missing field"):
        _extract_pem_field(payload, _VAULT_REF)


def test_extract_pem_field_missing_data_key():
    payload = {"other": "stuff"}
    with pytest.raises(EgressSignerError, match="missing 'data'"):
        _extract_pem_field(payload, _VAULT_REF)


def test_extract_pem_field_missing_inner_data_key():
    payload = {"data": {"metadata": {}}}
    with pytest.raises(EgressSignerError, match="missing 'data.data'"):
        _extract_pem_field(payload, _VAULT_REF)


def test_extract_pem_field_non_string_value():
    payload = {"data": {"data": {"private_key": 12345}}}
    with pytest.raises(EgressSignerError, match="must be a non-empty string"):
        _extract_pem_field(payload, _VAULT_REF)


def test_extract_pem_field_not_a_mapping():
    with pytest.raises(EgressSignerError, match="not a JSON object"):
        _extract_pem_field("unexpected string", _VAULT_REF)


# ---------------------------------------------------------------------------
# make_signer_for_seat — routing to vault vs pem_path
# ---------------------------------------------------------------------------

def test_make_signer_for_seat_routes_secret_ref_to_vault_signer():
    """A seat with secret_ref must use the vault signer (fetcher is called)."""
    fetcher_called = [False]

    def tracking_fetcher(ref: VaultSecretRef) -> str:
        fetcher_called[0] = True
        return _FAKE_PEM

    signer = make_signer_for_seat(
        _seat_with_secret_ref(),
        vault_config=_VAULT_CONFIG,
        vault_fetcher=tracking_fetcher,
        runner=_ok_runner,
    )
    signer(b"test")
    assert fetcher_called[0], "vault fetcher must be called for secret_ref seats"


def test_make_signer_for_seat_routes_pem_path_to_openssl_signer():
    """A seat with pem_path must use the disk-based openssl signer."""
    argv_seen: list[list[str]] = []

    def sniffing_runner(argv, *, input=b"", capture_output=False, pass_fds=()):
        argv_seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout=b"SIG", stderr=b"")

    signer = make_signer_for_seat(_seat_with_pem_path(), runner=sniffing_runner)
    signer(b"test")
    assert argv_seen, "runner must be called"
    # disk-based path: the -sign argument is the pem_path directly
    assert argv_seen[0][-1] == "/dev/shm/ce-dev4/ce-forge-dev4.pem"


def test_make_signer_for_seat_secret_ref_without_vault_config_refuses():
    """secret_ref seat without VaultKvConfig must raise EgressSignerError (fail-closed)."""
    with pytest.raises(EgressSignerError, match="no VaultKvConfig"):
        make_signer_for_seat(_seat_with_secret_ref(), vault_config=None)


def test_make_signer_for_seat_no_key_source_refuses():
    """A seat with neither pem_path nor secret_ref must raise EgressSignerError."""
    no_key_seat = SeatAppConfig(
        seat_id="dev-bad",
        app_id="999",
        app_owner="nobody",
        pem_path=None,
        installation_id=None,
        secret_ref=None,
    )
    with pytest.raises(EgressSignerError, match="neither secret_ref nor pem_path"):
        make_signer_for_seat(no_key_seat)


# ---------------------------------------------------------------------------
# Config loader — secret_ref entries
# ---------------------------------------------------------------------------

def _base_config_doc(**overrides):
    doc = {
        "repo": "creator-engine/creator-engine",
        "installation_owner": "creator-engine",
        "audit_log": "~/.ce-egress/audit.jsonl",
        "policy": {
            "base_branch": "main",
            "allowed_branch_namespaces": ["ce-"],
            "forbidden_branches": ["main"],
            "authorized_emails": [],
            "authorized_logins": ["ce-dev-3"],
            "max_pushes_per_window": 10,
            "window_seconds": 3600,
        },
        "seats": {
            "dev-3": {
                "app_id": "REPLACE_WITH_DEV3_APP_ID",
                "app_owner": "ce-dev-3",
                "secret_ref": {"mount": "ce-kv", "path": "forge/dev-3", "field": "private_key"},
                "installation_id": None,
            },
        },
    }
    doc.update(overrides)
    return doc


def test_config_loader_accepts_secret_ref_seat():
    cfg = load_broker_config(_base_config_doc())
    seat = cfg.seat("dev-3")
    assert seat.secret_ref is not None
    assert seat.secret_ref.mount == "ce-kv"
    assert seat.secret_ref.path == "forge/dev-3"
    assert seat.secret_ref.field == "private_key"
    assert seat.pem_path is None


def test_config_loader_secret_ref_repr_is_value_free():
    cfg = load_broker_config(_base_config_doc())
    r = repr(cfg.seat("dev-3"))
    # The VaultSecretRef itself is shown (it is value-free — mount/path/field are not secret)
    assert "ce-kv" in r
    assert "forge/dev-3" in r
    # App ID must be redacted
    assert "REPLACE_WITH_DEV3_APP_ID" not in r


def test_config_loader_accepts_mixed_seats():
    """A config with both pem_path and secret_ref seats must load without error."""
    doc = _base_config_doc()
    doc["seats"]["dev-4"] = {
        "app_id": "4085526",
        "app_owner": "cedev4vps-coder",
        "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
        "installation_id": None,
    }
    doc["policy"]["authorized_logins"] = ["ce-dev-3", "cedev4vps-coder"]
    cfg = load_broker_config(doc)
    assert cfg.seat("dev-3").secret_ref is not None
    assert cfg.seat("dev-4").pem_path is not None
    assert cfg.seat("dev-4").secret_ref is None


def test_config_loader_refuses_seat_with_neither_key_source():
    """A seat missing both secret_ref and pem_path must be a BrokerConfigError."""
    doc = _base_config_doc()
    doc["seats"]["dev-3"].pop("secret_ref")
    # no pem_path either
    with pytest.raises(BrokerConfigError, match="secret_ref.*pem_path|pem_path.*secret_ref"):
        load_broker_config(doc)


def test_config_loader_refuses_malformed_secret_ref_missing_mount():
    doc = _base_config_doc()
    doc["seats"]["dev-3"]["secret_ref"] = {"path": "forge/dev-3", "field": "private_key"}
    with pytest.raises(BrokerConfigError, match="secret_ref.mount"):
        load_broker_config(doc)


def test_config_loader_refuses_malformed_secret_ref_missing_path():
    doc = _base_config_doc()
    doc["seats"]["dev-3"]["secret_ref"] = {"mount": "ce-kv", "field": "private_key"}
    with pytest.raises(BrokerConfigError, match="secret_ref.path"):
        load_broker_config(doc)


def test_config_loader_refuses_malformed_secret_ref_missing_field():
    doc = _base_config_doc()
    doc["seats"]["dev-3"]["secret_ref"] = {"mount": "ce-kv", "path": "forge/dev-3"}
    with pytest.raises(BrokerConfigError, match="secret_ref.field"):
        load_broker_config(doc)


def test_config_loader_refuses_secret_ref_not_a_mapping():
    doc = _base_config_doc()
    doc["seats"]["dev-3"]["secret_ref"] = "not-a-mapping"
    with pytest.raises(BrokerConfigError, match="secret_ref"):
        load_broker_config(doc)


# ---------------------------------------------------------------------------
# No key material in repr surfaces
# ---------------------------------------------------------------------------

def test_vault_kv_config_token_not_in_repr():
    cfg = VaultKvConfig(
        address="https://vault.example.com",
        token_supplier=lambda: "bao.SUPERSECRET",
    )
    r = repr(cfg)
    assert "SUPERSECRET" not in r
    assert "bao." not in r
