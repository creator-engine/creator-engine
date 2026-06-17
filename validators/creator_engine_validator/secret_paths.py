"""Credential / secret path classification — the single source of truth.

A tiny, dependency-free predicate that labels a filesystem path as
credential-shaped (``.env``, private keys, ``~/.ssh`` / ``~/.aws`` stores, …)
WITHOUT ever reading the file. It returns a *category label* (never the file's
contents), so callers can deny or audit a credential-store access by shape
alone.

This lives in the **shared** version line on purpose. The classification was
originally defined inside the v1 ``hook_check`` Read gate; it is hoisted here so
the v3 runner filesystem-mediation layer (``fs_mediation``) can reuse the exact
same predicate as a fail-closed configuration guard. v1 ``hook_check`` and the
v3 runner both import from this shared module, so neither re-derives the rule
set and the version boundary (``version_boundary`` check) stays intact — a v1
module importing a *shared* module and a v3 module importing a *shared* module
are both allowed; only a v1↔v3 import would be a violation.

Scope discipline: this module never opens, reads, or echoes any path's bytes.
It classifies the path string alone.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

# Exact basenames that name a credential/token store outright.
SECRET_EXACT_NAMES = frozenset(
    {"credentials", "credentials.json", ".netrc", ".npmrc", ".pypirc", ".pgpass", ".htpasswd"}
)
# Private SSH key basenames (the matching ``.pub`` is intentionally NOT secret).
SECRET_KEY_NAMES = frozenset({"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"})
# Suffixes that name private-key / certificate / keystore material.
SECRET_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".keystore", ".jks"})
# Path components that name a credential-store directory.
SECRET_DIR_PARTS = frozenset({"secrets", ".ssh", ".gnupg", ".aws"})

#: The credential *rule classes* this predicate recognizes — descriptive
#: identifiers (NOT the function's variable return labels, which include the
#: literal basename for exact/key-name matches). Anchored to the rule taxonomy
#: above so a capability declaration can enumerate which credential shapes are
#: recognized without re-stating the rules. Consumed by ``fs_mediation``
#: capability objects as a stable, machine-readable inventory.
CREDENTIAL_PATH_RULE_CLASSES: tuple[str, ...] = (
    "dotenv",
    "exact-credential-store-name",
    "ssh-private-key-name",
    "private-key-or-cert-suffix",
    "credential-store-directory",
    "credential-or-secret-in-name",
)


def is_secret_path(file_path: Any) -> str | None:
    """Return a *category label* when ``file_path`` looks like a credential /
    token store, else ``None``.

    The returned label names the matched rule class (e.g. ``".env"`` or
    ``"private-key/cert"``); it is never the file's contents — this module
    never reads the file.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        return None
    p = PurePosixPath(file_path.strip())
    name = p.name
    lowered = name.lower()
    if name == ".env" or name.startswith(".env."):
        return ".env"
    if name in SECRET_EXACT_NAMES or name in SECRET_KEY_NAMES:
        return name
    if p.suffix in SECRET_SUFFIXES:
        return "private-key/cert"
    if set(p.parts) & SECRET_DIR_PARTS:
        return "credential-store-directory"
    if "credential" in lowered or "secret" in lowered:
        return "credential-like-name"
    return None
