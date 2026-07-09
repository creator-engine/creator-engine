"""Approver-ref minting and verification for client-bound ratification."""
from __future__ import annotations

import hashlib
import hmac
import re

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def mint_approver_ref(
    client_id: str,
    ratified_prompt_sha: str,
    gesture_salt: str | None = None,
) -> str:
    """Return a 64-hex approver_ref bound to the given client identity."""
    if not client_id:
        raise ValueError("client_id must be non-empty")
    if not _SHA256_HEX_RE.fullmatch(ratified_prompt_sha):
        raise ValueError("ratified_prompt_sha must be 64 lowercase hex chars")

    salt = gesture_salt or ""
    payload = f"{client_id}:{ratified_prompt_sha}:{salt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_approver_ref(
    approver_ref: str,
    client_id: str,
    ratified_prompt_sha: str,
    gesture_salt: str | None = None,
) -> bool:
    """Return True iff approver_ref matches the expected derivation."""
    if not isinstance(approver_ref, str):
        return False
    try:
        expected = mint_approver_ref(client_id, ratified_prompt_sha, gesture_salt)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(approver_ref.encode("utf-8"), expected.encode("utf-8"))
