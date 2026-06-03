"""CE v3 forge-native scoped-token minting (G-2.2) — JIT least-privilege per-run credential.

The G-2.0/G-2.1 orchestrator gate refuses to provision unless a run is ratified. Once a
run IS authorized, G-2.2 gives it a *just-in-time*, *least-privilege*, *time-boxed*,
audited per-run credential rather than a long-lived ambient token: :func:`mint_scoped_token`
mints a GitHub App **installation access token** scoped to a single repository and an
explicitly-listed permission subset, and :func:`revoke_scoped_token` releases it the instant
the run no longer needs it (defense-in-depth beyond its <=1h ceiling).

This is the 2026 ephemeral credential-broker pattern: the orchestrator requests a credential
scoped to exactly the task + resource + window, the minter validates the request against a
least-privilege ceiling BEFORE issuance, and the credential is revoked immediately after use
— a 2-minute run must not hold a 60-minute token.

Defensive invariants (deliberate, load-bearing):

* **Refuse over-broad / un-time-boxed requests BEFORE any forge call.** :func:`mint_scoped_token`
  raises :class:`TokenMintRefused` (a ``ForgeConfigRefused``) on an empty permission set, an
  ``admin``/forbidden scope, a ttl outside ``0 < t <= MAX_TTL_SECONDS`` (the GitHub 1h
  ceiling), a non-64-hex ``policy_sha``, a malformed ``repo``, or a non-positive
  ``installation_id`` — refuse-before-side-effect, mirroring the G-1.0 deny discipline.
* **Secret hygiene.** The minted token VALUE is redacted from :class:`ScopedToken`'s
  ``repr``/``str``, is never logged, and never enters an evidence record (only the secret
  name / scope / expiry / a non-secret correlation ref are attestable).
* **Network only behind an injectable runner.** All GitHub I/O goes through a ``GhRunner``
  (``gh api`` by default) callers inject; tests use a fake and perform ZERO live mint, and
  importing this module performs no I/O and registers no validator check.

Like the rest of ``forge/`` this reuses ``GhRunner`` / ``ForgeConfigError`` /
``ForgeConfigRefused`` from the byte-unchanged G-iii ``github_repo_config`` module. It does
NOT import the orchestrator: the orchestrator owns a value-free ``MintedCredential`` port
type and consumes minting only through an injected ``token_minter`` closure (the closure maps
this module's value-bearing :class:`ScopedToken` to that port type and arranges revocation),
so the orchestrator stays pure and never holds the secret.

Defensive only — least-privilege credentials for our own sandboxed runs; never offensive
(no exfiltration, no token-theft tradecraft, no detection evasion).
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner

#: GitHub installation access tokens live at most one hour; we never request more.
MAX_TTL_SECONDS = 3600
#: Least-privilege permission levels a per-run credential may request (never ``admin``).
ALLOWED_PERMISSION_LEVELS = ("read", "write")
#: Permission scopes a per-run sandbox credential must never request (admin / org-wide).
FORBIDDEN_SCOPES = frozenset({"administration", "organization_administration", "secrets"})

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_POLICY_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class TokenMintRefused(ForgeConfigRefused):
    """A scoped-token request was refused on a least-privilege / time-box precondition.

    Raised BEFORE any forge call when the request is over-broad (empty / ``admin`` /
    forbidden permissions), not time-boxed (ttl outside ``0 < t <= MAX_TTL_SECONDS``), or
    not bound to a valid policy / repo / installation. A *policy* refusal — distinct from a
    *transport* :class:`ForgeConfigError`.
    """

    code = "V3-FORGE-TOKEN-REFUSED"


@dataclass(frozen=True)
class TokenRequest:
    """A request to mint a JIT, least-privilege, time-boxed per-run credential.

    ``repo`` is ``owner/name``; ``installation_id`` the GitHub App installation to mint
    from; ``run_id`` the run this credential authorizes; ``policy_sha`` the 64-hex digest
    binding issuance to the runtime-policy in force; ``permissions`` the explicit
    least-privilege subset (e.g. ``{"contents": "read", "pull_requests": "write"}`` — never
    the installation's full grant); ``secret_name`` the logical secret this credential
    satisfies (the orchestrator gates it against the policy ``secret_allowlist``);
    ``requested_ttl_seconds`` the declared time-box ceiling (``<= MAX_TTL_SECONDS``).
    """

    repo: str
    installation_id: int
    run_id: str
    policy_sha: str
    permissions: Mapping[str, str]
    secret_name: str
    requested_ttl_seconds: int


@dataclass(frozen=True)
class ScopedToken:
    """A minted per-run credential. The secret ``value`` is redacted from ``repr``/``str``.

    Only ``run_id`` / ``repo`` / ``policy_sha`` / ``secret_name`` / ``permissions`` /
    ``expires_at`` / ``token_ref`` are attestable; ``value`` is the live secret used to
    authenticate (and to revoke) and MUST never be logged or written to the evidence spine.
    """

    run_id: str
    repo: str
    policy_sha: str
    secret_name: str
    permissions: tuple[tuple[str, str], ...]
    expires_at: str
    token_ref: str
    value: str

    def __repr__(self) -> str:  # never leak the secret in a repr/str
        return (
            f"ScopedToken(run_id={self.run_id!r}, repo={self.repo!r}, "
            f"secret_name={self.secret_name!r}, expires_at={self.expires_at!r}, "
            f"token_ref={self.token_ref!r}, value=<redacted>)"
        )

    __str__ = __repr__


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - requires a live gh + GitHub App
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_api_method(
    runner: GhRunner, method: str, path: str, body: dict | None = None
) -> tuple[int, object, str]:
    """Invoke ``gh api -X <METHOD> <path>`` (JSON body via ``--input -``).

    Returns ``(returncode, parsed_json|None, stderr)``. Never raises on a non-zero exit or
    unparseable stdout. Mirrors the ``github_repo_config`` / ``plan_approval`` ``gh api``
    idiom locally so those frozen modules stay byte-unchanged.
    """
    argv = ["gh", "api", "-X", method, path]
    input_text: str | None = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    parsed: object = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _validate_request(request: TokenRequest) -> None:
    """Refuse an over-broad / un-time-boxed / unbound request BEFORE any forge call."""
    perms = request.permissions
    if not perms:
        raise TokenMintRefused(
            "a scoped token must request an explicit least-privilege permission set "
            "(empty set = refuse; never inherit the installation's full grant)"
        )
    for scope, level in perms.items():
        if scope in FORBIDDEN_SCOPES:
            raise TokenMintRefused(
                f"permission scope {scope!r} is forbidden for a per-run sandbox credential"
            )
        if level not in ALLOWED_PERMISSION_LEVELS:
            raise TokenMintRefused(
                f"permission level {level!r} for {scope!r} is not least-privilege "
                f"(allowed: {', '.join(ALLOWED_PERMISSION_LEVELS)})"
            )
    if not 0 < request.requested_ttl_seconds <= MAX_TTL_SECONDS:
        raise TokenMintRefused(
            f"requested_ttl_seconds {request.requested_ttl_seconds} is not time-boxed in "
            f"0 < t <= {MAX_TTL_SECONDS} (a per-run credential must be short-lived)"
        )
    if not _POLICY_SHA_RE.match(request.policy_sha or ""):
        raise TokenMintRefused(f"policy_sha {request.policy_sha!r} is not a 64-hex digest")
    if not _REPO_RE.match(request.repo or ""):
        raise TokenMintRefused(f"repo {request.repo!r} is not in owner/name form")
    if request.installation_id <= 0:
        raise TokenMintRefused(f"installation_id {request.installation_id} must be positive")


def mint_scoped_token(request: TokenRequest, *, gh_runner: GhRunner | None = None) -> ScopedToken:
    """Mint a JIT, least-privilege, time-boxed installation token for one run.

    Validates the request against the least-privilege / time-box ceiling FIRST (raising
    :class:`TokenMintRefused` before any forge call), then mints a GitHub App installation
    access token scoped to the single repo + the explicit ``permissions`` subset through the
    injected ``gh_runner``. A transport failure (the mint call errored or returned no token)
    raises :class:`ForgeConfigError`. The returned :class:`ScopedToken` holds the live value
    (redacted from its repr); only its non-secret metadata is attestable.
    """
    _validate_request(request)
    runner = gh_runner or _default_gh_runner
    repo_name = request.repo.split("/", 1)[1]
    body = {"repositories": [repo_name], "permissions": dict(request.permissions)}
    code, parsed, stderr = _gh_api_method(
        runner, "POST", f"app/installations/{request.installation_id}/access_tokens", body
    )
    if code != 0 or not isinstance(parsed, dict) or not parsed.get("token"):
        raise ForgeConfigError(
            f"could not mint scoped token for {request.repo} "
            f"(installation {request.installation_id}): {stderr.strip() or 'unknown error'}"
        )
    expires_at = str(parsed.get("expires_at") or "")
    permissions = tuple(sorted((str(k), str(v)) for k, v in request.permissions.items()))
    return ScopedToken(
        run_id=request.run_id,
        repo=request.repo,
        policy_sha=request.policy_sha,
        secret_name=request.secret_name,
        permissions=permissions,
        expires_at=expires_at,
        token_ref=f"{request.repo}@{expires_at}",
        value=str(parsed["token"]),
    )


def revoke_scoped_token(token: ScopedToken, *, gh_runner: GhRunner | None = None) -> bool:
    """Revoke a minted scoped token via ``DELETE /installation/token``; return ``True``.

    Defense-in-depth: release the credential the instant the run no longer needs it rather
    than waiting out its (<=1h) ttl — closing the over-exposure window. The DELETE is
    authenticated AS the token being revoked; the injected ``gh_runner`` supplies that auth
    (e.g. via the subprocess env), so the secret never appears in the argv. A transport
    failure raises :class:`ForgeConfigError`.
    """
    runner = gh_runner or _default_gh_runner
    code, _parsed, stderr = _gh_api_method(runner, "DELETE", "installation/token")
    if code != 0:
        raise ForgeConfigError(
            f"could not revoke scoped token for {token.repo} (run {token.run_id}): "
            f"{stderr.strip() or 'unknown error'}"
        )
    return True
