"""S5 (ce-ops#157) — the ``LiveForgeConfig.token_minter`` seam.

The shared-App mint-broker path mints the scoped installation token in a STANDING service
rather than in the driver process (no PEM on the user's disk). To support both topologies the
driver gains a ``token_minter`` seam: a ``Callable[[TokenRequest], ScopedToken]`` that, when
set, the driver uses to obtain its read/write token instead of the local
``app_jwt_gh_runner`` → ``mint_scoped_token`` (local-signer) path.

Invariants exercised here (TDD, ZERO live network / crypto):

* ``token_minter`` set → the driver mints THROUGH the seam and NEVER touches the local signer
  (so a config with no PEM/signer still works — the broker holds the key);
* ``token_minter`` is given the SAME ``TokenRequest`` the local path would build (repo /
  installation / permissions / ttl / escalation authority / policy_sha) — the ceiling is
  identical regardless of who mints;
* ``signer`` set + no ``token_minter`` → byte-identical to today (the local path is unchanged);
* both legs (READ via ``_reader``, WRITE via ``_writer``) honour the seam.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from creator_engine_validator import onboard_apply_live
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest

_REPO = "creator-engine/creator-engine"


def _scoped(value: str = "ghs_from_broker", *, secret_name: str = "x") -> ScopedToken:
    return ScopedToken(
        run_id="r",
        repo=_REPO,
        policy_sha="a" * 64,
        secret_name=secret_name,
        permissions=(("contents", "read"),),
        expires_at="2026-06-21T15:00:00Z",
        token_ref=f"{_REPO}@broker",
        value=value,
    )


class _RecordingMinter:
    """A fake ``token_minter`` that records every request and returns a canned token."""

    def __init__(self) -> None:
        self.requests: list[TokenRequest] = []

    def __call__(self, request: TokenRequest) -> ScopedToken:
        self.requests.append(request)
        return _scoped(secret_name=request.secret_name)


def _exploding_signer(_signing_input: bytes) -> bytes:  # pragma: no cover - must never run
    raise AssertionError("token_minter set → the local signer must never be used")


def _exploding_transport(*_a: Any, **_k: Any):  # pragma: no cover - must never run
    raise AssertionError("token_minter set → the local app-JWT mint transport must never be used")


def _spawn(argv, input_text, env):
    # Authenticated-gh subprocess: only the revoke (DELETE installation/token) is reached in
    # these seam tests; succeed silently. The token rides in GH_TOKEN, never the argv.
    return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# READ leg via the seam
# ---------------------------------------------------------------------------
def test_reader_uses_token_minter_seam_and_not_the_local_signer():
    minter = _RecordingMinter()
    config = onboard_apply_live.LiveForgeConfig(
        repo=_REPO,
        installation_id=140271364,
        app_client_id="Iv1.testclient",
        signer=None,  # no PEM/signer — the broker holds the key
        policy_sha="a" * 64,
        run_id="onboard-broker-test",
        token_minter=minter,
        transport=_exploding_transport,
        spawn=_spawn,
    )
    driver = onboard_apply_live.LiveForgeApplyDriver(config)
    runner = driver._reader()  # mints lazily through the seam
    assert runner is not None
    assert len(minter.requests) == 1
    req = minter.requests[0]
    assert req.repo == _REPO
    assert req.installation_id == 140271364
    assert req.permissions == onboard_apply_live.PHASE1_PERMISSIONS
    assert req.secret_name == onboard_apply_live.FORGE_READ_SECRET_NAME
    assert req.requested_ttl_seconds == onboard_apply_live.FORGE_READ_TTL_SECONDS
    assert req.escalation_authority == onboard_apply_live.PHASE1_ESCALATION_AUTHORITY
    assert req.policy_sha == "a" * 64
    driver.close()


def test_reader_seam_caches_the_token():
    minter = _RecordingMinter()
    config = onboard_apply_live.LiveForgeConfig(
        repo=_REPO,
        installation_id=1,
        app_client_id="Iv1.testclient",
        signer=None,
        policy_sha="a" * 64,
        run_id="r",
        token_minter=minter,
        spawn=_spawn,
    )
    driver = onboard_apply_live.LiveForgeApplyDriver(config)
    first = driver._reader()
    second = driver._reader()
    assert first is second
    assert len(minter.requests) == 1  # minted exactly once
    driver.close()


def test_token_minter_set_never_invokes_local_signer():
    minter = _RecordingMinter()
    config = onboard_apply_live.LiveForgeConfig(
        repo=_REPO,
        installation_id=1,
        app_client_id="Iv1.testclient",
        signer=_exploding_signer,  # present but must NOT be called when a minter is set
        policy_sha="a" * 64,
        run_id="r",
        token_minter=minter,
        transport=_exploding_transport,
        spawn=_spawn,
    )
    driver = onboard_apply_live.LiveForgeApplyDriver(config)
    driver._reader()  # would raise via _exploding_signer/_transport if the local path ran
    driver.close()


# ---------------------------------------------------------------------------
# WRITE leg via the seam (adoption driver)
# ---------------------------------------------------------------------------
def test_writer_uses_token_minter_seam_with_the_write_ceiling():
    minter = _RecordingMinter()
    config = onboard_apply_live.LiveForgeConfig(
        repo=_REPO,
        installation_id=99,
        app_client_id="Iv1.testclient",
        signer=None,
        policy_sha="b" * 64,
        run_id="adopt",
        token_minter=minter,
        transport=_exploding_transport,
        spawn=_spawn,
    )
    driver = onboard_apply_live.LiveForgeAdoptionDriver(config)
    runner = driver._writer()
    assert runner is not None
    assert len(minter.requests) == 1
    req = minter.requests[0]
    assert req.permissions == onboard_apply_live.ADOPTION_WRITE_PERMISSIONS
    assert req.secret_name == onboard_apply_live.FORGE_WRITE_SECRET_NAME
    assert req.escalation_authority == onboard_apply_live.ADOPTION_ESCALATION_AUTHORITY
    assert req.requested_ttl_seconds == onboard_apply_live.FORGE_WRITE_TTL_SECONDS
    driver.close()


# ---------------------------------------------------------------------------
# Back-compat: signer set + no minter == today's local path (unchanged)
# ---------------------------------------------------------------------------
def test_local_signer_path_unchanged_when_no_minter():
    """With ``token_minter=None`` the driver mints via the local signer+transport (as today)."""
    minted = "ghs_local_minted"
    calls: dict[str, int] = {"transport": 0, "signer": 0}

    def signer(_signing_input: bytes) -> bytes:
        calls["signer"] += 1
        return b"sig"

    def transport(method, url, headers, body):
        calls["transport"] += 1
        assert headers.get("Authorization", "").startswith("Bearer ")
        return 201, (
            '{"token": "%s", "expires_at": "2026-06-21T15:00:00Z", '
            '"permissions": {"metadata": "read"}}' % minted
        )

    config = onboard_apply_live.LiveForgeConfig(
        repo=_REPO,
        installation_id=7,
        app_client_id="Iv1.testclient",
        signer=signer,
        policy_sha="a" * 64,
        run_id="r",
        token_minter=None,  # the unchanged local path
        transport=transport,
        spawn=_spawn,
    )
    driver = onboard_apply_live.LiveForgeApplyDriver(config)
    runner = driver._reader()
    assert runner is not None
    assert calls["transport"] == 1  # the local mint POST happened
    assert calls["signer"] >= 1  # the local App-JWT was signed
    driver.close()
