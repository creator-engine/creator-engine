"""The mint-broker ``POST /v1/token`` handler (ce-ops#157, S4) — bind, ceiling, mint, audit.

This is the standing shared-App broker's mint endpoint, factored as a pure
:func:`handle_token_request` (request mapping -> response mapping) so it is fully testable with
no HTTP server and zero live network. For each request, in this deliberate order:

1. **Validate the shape** — repo (``owner/name``), positive installation_id, non-empty
   permissions, a caller ``ghu_`` token (a malformed request is a ``400``, never a mint).
2. **Reject out-of-ceiling permissions BEFORE any GitHub call** (G3). The config's
   ``permits()`` is the gate: an ``administration:write`` / unknown-scope / over-level request
   is a ``403`` with reason ``out_of_ceiling`` and NO binding call, NO mint call. The standing
   broker can never even *attempt* an admin mint.
3. **Binding check** (S2) — the caller's ``ghu_`` token must control the claimed installation
   and that installation must cover the requested repo; a spoof is a ``403``
   (``binding_refused``) with NOTHING minted.
4. **Mint** via the frozen ``app_jwt_gh_runner`` -> ``mint_scoped_token`` composition (the
   shared-App key stays behind the injected openssl ``signer``); a transport failure is a
   ``502`` (fail-closed).
5. **Audit** — one secret-free ``egress_broker.audit`` record on EVERY decision (allow or deny).

The minted ``ghs_`` value appears ONLY in the success response (the caller needs it) — never in
the audit log; the caller's ``ghu_`` token never appears in the response or the audit at all.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from creator_engine_validator.forge.app_jwt_runner import Signer, app_jwt_gh_runner
from creator_engine_validator.forge.github_repo_config import ForgeConfigError, ForgeConfigRefused
from creator_engine_validator.forge.scoped_token import (
    TokenMintRefused,
    TokenRequest,
    mint_scoped_token,
)
from egress_broker.audit import append_audit

from mint_broker.binding import BindingRefused, BindingTransportError
from mint_broker.config import MintBrokerConfig

#: The binding-check seam: ``(caller_user_token, *, installation_id, repo_full_name) -> None``.
BindingCheck = Callable[..., None]

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
#: The mint TTL ceiling for a broker-issued token (well under GitHub's 1h cap).
_MINT_TTL_SECONDS = 600
_SECRET_NAME = "shared_app_broker_mint"


def _audit(config: MintBrokerConfig, record: Mapping[str, Any]) -> None:
    """Append one secret-free audit record (best-effort; an audit failure never leaks a secret)."""
    if not config.audit_log:
        return
    try:
        append_audit(config.audit_log, record)
    except Exception:  # noqa: BLE001 — never let an audit error surface a secret or 500 the mint
        pass


def _deny(
    config: MintBrokerConfig, *, status: int, reason: str, repo: str, installation_id: Any
) -> dict[str, Any]:
    _audit(
        config,
        {
            "decision": "deny",
            "reason": reason,
            "repo": repo,
            "installation_id": installation_id if isinstance(installation_id, int) else None,
        },
    )
    return {"status": status, "reason": reason}


def handle_token_request(
    request: Mapping[str, Any],
    *,
    config: MintBrokerConfig,
    binding_check: BindingCheck,
    signer: Signer,
    transport: Any = None,
) -> dict[str, Any]:
    """Handle a ``POST /v1/token`` request; return a response mapping (no exception escapes).

    ``request`` carries ``installation_id``, ``repo`` (``owner/name``), ``permissions``
    (``{scope: level}``), and ``caller_user_token`` (the user's ``ghu_`` from the S1 device flow).
    Returns ``{"status": 200, "token", "expires_at", ...}`` on success, or
    ``{"status": <4xx/5xx>, "reason"}`` on a validation/ceiling/binding/transport refusal. Every
    decision is audited (secret-free).
    """
    repo = str(request.get("repo") or "")
    raw_iid = request.get("installation_id")
    permissions_raw = request.get("permissions")
    caller_token = str(request.get("caller_user_token") or "")

    # 1. shape validation (a malformed request never reaches binding or mint) ----------------
    if not _REPO_RE.match(repo):
        return _deny(config, status=400, reason="bad_repo", repo=repo, installation_id=None)
    try:
        installation_id = int(raw_iid)
    except (TypeError, ValueError):
        return _deny(config, status=400, reason="bad_installation_id", repo=repo, installation_id=None)
    if installation_id <= 0:
        return _deny(config, status=400, reason="bad_installation_id", repo=repo, installation_id=None)
    if not caller_token:
        return _deny(config, status=400, reason="missing_caller_token", repo=repo, installation_id=installation_id)
    if not isinstance(permissions_raw, Mapping) or not permissions_raw:
        return _deny(config, status=400, reason="missing_permissions", repo=repo, installation_id=installation_id)
    permissions = {str(k): str(v) for k, v in permissions_raw.items()}

    # 2. CEILING check BEFORE any GitHub call (G3 — never attempt an admin/over-ceiling mint) -
    if not config.permits(permissions):
        return _deny(config, status=403, reason="out_of_ceiling", repo=repo, installation_id=installation_id)

    # 3. binding check (S2) — the caller must control the installation+repo pair -------------
    try:
        binding_check(caller_token, installation_id=installation_id, repo_full_name=repo)
    except BindingRefused:
        return _deny(config, status=403, reason="binding_refused", repo=repo, installation_id=installation_id)
    except BindingTransportError:
        return _deny(config, status=502, reason="binding_transport_error", repo=repo, installation_id=installation_id)

    # 4. mint via the frozen App-JWT -> scoped-token composition (key behind the signer) ------
    try:
        mint_runner = app_jwt_gh_runner(config.app_client_id, signer=signer, transport=transport)
        token = mint_scoped_token(
            TokenRequest(
                repo=repo,
                installation_id=installation_id,
                run_id=f"mint-broker:{repo}",
                policy_sha="0" * 64,  # broker policy ref placeholder; the ceiling is config.permits
                permissions=permissions,
                secret_name=_SECRET_NAME,
                requested_ttl_seconds=_MINT_TTL_SECONDS,
                escalation_authority=tuple(
                    (s, l) for s, l in permissions.items() if l == "write"
                ),
            ),
            gh_runner=mint_runner,
        )
    except (TokenMintRefused, ForgeConfigRefused):
        # The frozen minter's own ceiling refused (defence-in-depth behind config.permits).
        return _deny(config, status=403, reason="mint_refused", repo=repo, installation_id=installation_id)
    except ForgeConfigError:
        return _deny(config, status=502, reason="mint_transport_error", repo=repo, installation_id=installation_id)

    # 5. audit the allow (secret-free — the minted value is NOT recorded) --------------------
    _audit(
        config,
        {
            "decision": "allow",
            "repo": repo,
            "installation_id": installation_id,
            "permissions": [list(p) for p in token.permissions],
            "expires_at": token.expires_at,
        },
    )
    return {
        "status": 200,
        "token": token.value,
        "expires_at": token.expires_at,
        "permissions": [list(p) for p in token.permissions],
        "repo": repo,
    }
