"""CE v3 forge-native App-JWT mint seam (G-3.7.1) — the App-authenticated runner for ``mint_scoped_token``.

``mint_scoped_token`` (G-2.2) POSTs ``app/installations/{id}/access_tokens`` through an injected
``GhRunner`` and ASSUMES that runner authenticates AS the GitHub App. This module supplies that
runner. Per the current GitHub-App docs an App authenticates with a short-lived **RS256 JSON Web
Token** passed as ``Authorization: Bearer <JWT>``:

* JWT header ``{"alg":"RS256","typ":"JWT"}``; claims ``iss`` = the App's **client id**, ``iat`` set
  60s in the past (clock drift), ``exp`` no more than 10 minutes (600s) in the future.
* ``POST /app/installations/{id}/access_tokens`` with the Bearer JWT mints a (<=1h) installation
  access token (the ``mint_scoped_token`` result; the new stateless ``ghs_…`` format is ~520-char
  and opaque — we make no length/format assumption).

Crucially, ``gh``/``gh api`` **cannot** authenticate as an App via a JWT: it sends
``Authorization: token <GH_TOKEN>``, but App auth requires ``Bearer`` ("GitHub CLI only accepts
access tokens"), and putting the JWT in a ``gh api -H`` flag would leak it into the argv. So the
mint leg is a direct-HTTPS **Bearer adapter**: :func:`app_jwt_gh_runner` returns a ``GhRunner``-shaped
``(argv, input_text) -> CompletedProcess`` that parses ``mint_scoped_token``'s ``gh api`` argv, mints a
fresh JWT, and issues the request itself with the Bearer header — leaving ``mint_scoped_token``
byte-unchanged. (The *use* leg — installation token -> repo ops — keeps ``gh`` + ``GH_TOKEN`` via the
G-3.4 :func:`authenticated_gh_runner`, because an installation token IS an access token.)

Secret hygiene (deliberate, load-bearing):

* **The App private key NEVER enters this module.** RS256 signing is done by an injected ``signer``
  (host-side, a PEM held on tmpfs — wired in the later live gate); this module only assembles the
  signing input and base64url-joins the signature.
* **The JWT lives in the in-process Bearer header ONLY** — never the argv, the request body, a
  log / ``print`` / exception, the returned ``CompletedProcess`` (``args`` / ``stdout`` / ``stderr``),
  or disk. A mint error body is surfaced as ``stderr`` so the caller's ``redact_gh_stderr`` masks any
  token-shaped material in it.

Network only behind an injectable ``transport`` seam (a stdlib ``urllib`` HTTPS call by default);
tests inject fakes and perform ZERO live network / subprocess / crypto. Importing this module
performs no I/O and registers no validator check.

Defensive only — least-privilege credential minting for our own sandboxed runs; never offensive.
"""
from __future__ import annotations

import base64
import json
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence

from .github_repo_config import ForgeConfigRefused, GhRunner

#: RS256 signer: maps the JWT signing input ``b"<b64h>.<b64p>"`` to the raw signature bytes. The
#: GitHub App private key lives ONLY behind this seam (host-side); it never enters this module.
Signer = Callable[[bytes], bytes]
#: HTTPS transport: ``(method, url, headers, body) -> (status_code, response_body_text)``.
Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, str]"]

_API_ROOT = "https://api.github.com"
_API_VERSION = "2022-11-28"
_ACCEPT = "application/vnd.github+json"
_IAT_SKEW_SECONDS = 60   # iss the JWT 60s in the past to tolerate clock drift
_EXP_WINDOW_SECONDS = 540  # <= the 600s (10min) ceiling, with a 60s safety margin


def _b64url(raw: bytes) -> str:
    """Unpadded base64url, per the JWT spec."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def build_app_jwt(client_id: str, *, signer: Signer, now: Callable[[], float] | None = None) -> str:
    """Assemble an RS256 GitHub App JWT ``<b64h>.<b64p>.<b64sig>`` (the App private key stays behind ``signer``).

    Claims per the GitHub-App docs: ``iss`` = the App ``client_id``; ``iat`` = now - 60s (clock
    drift); ``exp`` = now + 540s (under the 10-minute ceiling). ``now`` defaults to the wall clock
    evaluated AT CALL TIME (never at import). The ``signer`` performs the RS256 signature over the
    ``"<b64h>.<b64p>"`` signing input; this function only base64url-joins the result.
    """
    issued = int((now or time.time)())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"iss": client_id, "iat": issued - _IAT_SKEW_SECONDS, "exp": issued + _EXP_WINDOW_SECONDS}
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    )
    signature = signer(signing_input.encode("ascii"))
    return f"{signing_input}.{_b64url(signature)}"


def _default_transport(  # pragma: no cover - the lone live HTTPS shell; tests inject a fake
    method: str, url: str, headers: dict[str, str], body: str | None
) -> tuple[int, str]:
    data = body.encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _parse_mint_argv(argv: Sequence[str]) -> tuple[str, str]:
    """Extract ``(method, path)`` from ``mint_scoped_token``'s ``gh api`` argv; refuse any other shape.

    This is a single-purpose mint adapter: it serves only ``POST app/installations/{id}/access_tokens``.
    A non-mint argv is refused (value-free) rather than blindly forwarded.
    """
    items = list(argv)
    if items[:2] != ["gh", "api"] or "-X" not in items:
        raise ForgeConfigRefused("app_jwt_gh_runner serves only the gh-api installation-token mint call")
    i = items.index("-X")
    method = items[i + 1] if i + 1 < len(items) else ""
    path = items[i + 2] if i + 2 < len(items) else ""
    if method != "POST" or not (path.startswith("app/installations/") and path.endswith("/access_tokens")):
        raise ForgeConfigRefused(
            "app_jwt_gh_runner refuses a non-mint request "
            "(serves only POST app/installations/{id}/access_tokens)"
        )
    return method, path


def app_jwt_gh_runner(
    client_id: str, *, signer: Signer, transport: Transport | None = None, now: Callable[[], float] | None = None
) -> GhRunner:
    """Return a :data:`GhRunner` that mints installation tokens AS the App (Bearer JWT over HTTPS).

    The returned runner has the ``GhRunner`` shape ``(argv, input_text) -> CompletedProcess``. On each
    call it parses ``mint_scoped_token``'s ``gh api`` argv (refusing a non-mint shape), mints a FRESH
    short-lived App JWT via :func:`build_app_jwt`, and issues the request through ``transport`` (the live
    ``urllib`` HTTPS call by default) with ``Authorization: Bearer <JWT>``. A 2xx maps to
    ``returncode 0`` with the response body on ``stdout`` (the installation-token JSON ``mint_scoped_token``
    parses); a non-2xx maps to ``returncode 1`` with the response body on ``stderr`` (so the caller's
    ``redact_gh_stderr`` masks any token-shaped material). The JWT is in the Bearer header ONLY — never
    the argv, the body, a log, the returned process, or disk.

    Refuses at build time with :class:`ForgeConfigRefused` (value-free) if ``client_id`` is empty — a
    credential-less App-auth runner would silently fall back to ambient auth.
    """
    if not client_id:
        raise ForgeConfigRefused(
            "app_jwt_gh_runner requires a non-empty client_id "
            "(a credential-less App-auth runner would silently fall back to ambient auth)"
        )
    _transport = transport or _default_transport

    def runner(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        method, path = _parse_mint_argv(argv)
        jwt = build_app_jwt(client_id, signer=signer, now=now)  # fresh per call; JWT in the header only
        headers = {
            "Authorization": f"Bearer {jwt}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }
        status, resp_body = _transport(method, f"{_API_ROOT}/{path}", headers, input_text)
        ok = 200 <= status < 300
        return subprocess.CompletedProcess(
            list(argv),
            0 if ok else 1,
            stdout=resp_body if ok else "",
            stderr="" if ok else (resp_body or f"HTTP {status}"),
        )

    return runner
