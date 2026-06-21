"""The generalized per-App egress minter — installation-id discovery + least-privilege mint.

The brief's minter pattern (the existing ``mint-forge-token`` flow) is: build an RS256 App JWT
``{iat:now-60, exp:now+540, iss:app_id}``, ``POST /app/installations/{id}/access_tokens`` to
get a (~1h) installation token. This module GENERALIZES it across the per-dev Apps and adds the
missing leg — installation-id discovery when the config doesn't record one (dev-4):

1. resolve the installation id: use ``seat.installation_id`` if set, else
   :func:`~egress_broker.installation.discover_installation_id` (``GET /app/installations``
   filtered to the org);
2. mint a JIT, least-privilege, time-boxed installation token through the FROZEN seams —
   ``forge.app_jwt_runner.app_jwt_gh_runner`` (App-JWT Bearer mint adapter) feeding
   ``forge.scoped_token.mint_scoped_token`` (the ceiling-validated minter). The permission
   ceiling, redaction, and refuse-before-side-effect are all the existing, tested ones — this
   module only composes them per-App with discovery.

Secret hygiene (inherited from the frozen seams): the App PRIVATE KEY stays behind the
:func:`openssl_signer` ``openssl dgst -sha256 -sign`` subprocess (the PEM is only a path; the
key never enters this process); the JWT is header-only; the minted token value lives only in
the returned :class:`ScopedToken` (redacted from its repr). One injectable ``transport`` drives
both discovery and mint; tests use a fake and run ZERO live crypto/network.
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from typing import Any

from creator_engine_validator.forge.app_jwt_runner import Signer, app_jwt_gh_runner
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest, mint_scoped_token
from egress_broker.config import SeatAppConfig
from egress_broker.installation import Transport, discover_installation_id


class EgressSignerError(Exception):
    """The App private key could not produce an RS256 signature — fail-closed, refuse to mint."""


def openssl_signer(pem_path: str, *, runner: Callable[..., Any] = subprocess.run) -> Signer:
    """Return an RS256 :data:`~forge.app_jwt_runner.Signer` backed by ``openssl dgst -sha256 -sign``.

    Mirrors ``v3_forge_join.openssl_signer`` (re-defined locally so the broker is self-contained
    and pulls in none of the heavy v3 join graph): the signing input goes to openssl on STDIN and
    openssl reads the PEM itself, so the **App private key NEVER enters the broker process**. A
    non-zero exit or an empty signature is a fail-closed :class:`EgressSignerError`. ``runner`` is
    the injectable subprocess seam (CI fakes it → zero live openssl).
    """
    pem = str(pem_path)

    def sign(signing_input: bytes) -> bytes:
        proc = runner(
            ["openssl", "dgst", "-sha256", "-sign", pem], input=signing_input, capture_output=True
        )
        if getattr(proc, "returncode", 1) != 0:
            raise EgressSignerError(
                "openssl RS256 signing failed (the App private key is unreadable or invalid); "
                "refusing to mint"
            )
        signature = getattr(proc, "stdout", b"") or b""
        if not signature:
            raise EgressSignerError("openssl produced an empty RS256 signature; refusing to mint")
        return signature

    return sign


def resolve_installation_id(
    seat: SeatAppConfig,
    *,
    installation_owner: str,
    signer: Signer,
    transport: Transport | None = None,
    now: Callable[[], float] | None = None,
) -> int:
    """Return the seat's App installation id — the recorded one, else discover it (fail-closed)."""
    if seat.installation_id is not None:
        return seat.installation_id
    return discover_installation_id(
        seat.app_id, signer=signer, owner=installation_owner, transport=transport, now=now
    )


def mint_egress_token(
    seat: SeatAppConfig,
    *,
    repo: str,
    installation_owner: str,
    signer: Signer,
    run_id: str,
    policy_sha: str,
    permissions: Mapping[str, str],
    escalation_authority: tuple[tuple[str, str], ...],
    ttl_seconds: int,
    secret_name: str,
    transport: Transport | None = None,
    now: Callable[[], float] | None = None,
) -> ScopedToken:
    """Mint a JIT, least-privilege installation token for ``seat``'s App (discovering id if absent).

    Resolves the installation id (recorded or discovered), then mints through the frozen
    ``app_jwt_gh_runner`` → ``mint_scoped_token`` composition. The request is validated against
    the existing least-privilege ceiling (an out-of-ceiling permission raises ``TokenMintRefused``
    before any forge call). Returns a :class:`ScopedToken` whose value is redacted from its repr.
    """
    installation_id = resolve_installation_id(
        seat, installation_owner=installation_owner, signer=signer, transport=transport, now=now
    )
    app_runner = app_jwt_gh_runner(seat.app_id, signer=signer, transport=transport, now=now)
    request = TokenRequest(
        repo=repo,
        installation_id=installation_id,
        run_id=run_id,
        policy_sha=policy_sha,
        permissions=dict(permissions),
        secret_name=secret_name,
        requested_ttl_seconds=ttl_seconds,
        escalation_authority=escalation_authority,
    )
    return mint_scoped_token(request, gh_runner=app_runner)
