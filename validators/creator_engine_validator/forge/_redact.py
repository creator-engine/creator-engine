"""Mask credential-shaped material in a ``gh`` subprocess's stderr.

Defense-in-depth (belt-and-suspenders). A scoped / installation token lives ONLY in the
child ``gh`` process env (``GH_TOKEN``) and must never reach the process's stderr: the forge
ops pass no secret on the argv, and the G-3.7.0a child-env scrubber strips the debug/redirect
vars that could make ``gh`` echo an ``Authorization`` header. This helper is the SECONDARY
net for the residual case where ``gh`` nonetheless emits a token, a JWT, or an
``Authorization`` header into its stderr — because that stderr is interpolated verbatim into
a :class:`ForgeConfigError` message that may be logged or surfaced into the runtime-evidence
chain. :func:`redact_gh_stderr` masks the credential shapes there first, while preserving the
rest of the message for diagnosis.

Pure stdlib (``re`` only); performs no I/O and registers nothing on import. It makes NO
length / format assumption about a token — GitHub App installation tokens are opaque,
~520-char ``ghs_`` JWTs (the stateless ``ghs_<appid>_<jwt>`` brownout shape) — so the token
matcher is prefix-anchored and length-unbounded.
"""

from __future__ import annotations

import re

_REDACTED = "<redacted>"

# GitHub token prefixes (ghp_/gho_/ghu_/ghs_/ghr_ and fine-grained github_pat_) followed by
# the opaque body. No length cap: classic PATs are 40 chars, ``ghs_`` installation tokens are
# ~520. The charset admits ``_ . -`` so a stateless ``ghs_<appid>_eyJ….….…`` JWT body
# (base64url + JWT ``.`` separators) is consumed WHOLE — never partially masked.
_GH_TOKEN = re.compile(r"\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_.\-]+")
# A three-segment base64url JWT (``eyJ…``) standing on its own (App JWT / token JWT).
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2}")
# An ``Authorization:`` header echo — mask the ENTIRE header value (Basic / Bearer / token).
_AUTH_HEADER = re.compile(r"(?i)\bauthorization\s*:\s*[^\r\n]+")
# A bare ``Bearer <credential>`` outside a header line — require a token-length body so the
# ordinary English word "bearer" in prose is not over-masked.
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=\-]{16,}")


def redact_gh_stderr(text: str) -> str:
    """Return ``text`` stripped, with token / JWT / ``Authorization``-header material masked.

    Non-credential text (HTTP statuses, repo slugs, git SHAs, free-form ``gh`` error prose)
    is preserved verbatim — the matchers key only on the ``gh*_`` / ``github_pat_`` / ``eyJ…``
    / ``Authorization:`` / ``Bearer <token>`` shapes, never on plain hex or identifiers. An
    empty / whitespace-only input returns the empty string, so a caller's
    ``redact_gh_stderr(stderr) or 'unknown error'`` fallback still fires.
    """
    if not text:
        return ""
    masked = text.strip()
    # Mask whole Authorization-header values first (covers Basic/Bearer/token blobs), then
    # any standalone token / JWT / bearer credential elsewhere in the message.
    masked = _AUTH_HEADER.sub(f"Authorization: {_REDACTED}", masked)
    masked = _GH_TOKEN.sub(_REDACTED, masked)
    masked = _JWT.sub(_REDACTED, masked)
    masked = _BEARER.sub(_REDACTED, masked)
    return masked
