"""Runtime CE-internal identity denylist loader and matcher.

The generated artifact is intentionally gitignored runtime data. Public
checkouts normally do not have it; workers with ce-ops registry access generate
it locally before running registry-backed fleet-manifest checks.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .loader import load_yaml

ARTIFACT_RELATIVE = Path("data/identity_denylist.generated.yaml")
ARTIFACT_ENV = "CE_IDENTITY_DENYLIST_PATH"
NORMALIZATION = "casefold"
ALLOWED_CATEGORIES = frozenset(
    {
        "legacy-internal-literal",
        "repo-name",
        "repo-owner",
        "account-login",
        "account-owning-seat",
        "account-host",
        "host-topology-name",
        "host-topology-host",
        "host-topology-user",
        "signing-key-custody-seat",
        "signing-key-custody-host",
        "authoring-review-seat",
        "authoring-review-author",
        "authoring-review-reviewer",
    }
)
_TOP_LEVEL_KEYS = frozenset({"version", "generated_by", "source", "normalization", "entries"})
_ENTRY_KEYS = frozenset({"token", "categories"})
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class DenylistEntry:
    token: str
    normalized: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class IdentityDenylist:
    entries: tuple[DenylistEntry, ...]


@dataclass(frozen=True)
class DenylistMatch:
    categories: tuple[str, ...]


class IdentityDenylistError(ValueError):
    """Raised when the generated identity denylist is malformed."""


class IdentityDenylistUnavailable(FileNotFoundError):
    """Raised when the runtime identity denylist artifact is absent."""


def normalize_token(value: str) -> str:
    return value.casefold()


def runtime_artifact_path() -> Path:
    override = os.environ.get(ARTIFACT_ENV)
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / ARTIFACT_RELATIVE


def load_identity_denylist(path: Path | None = None, *, required: bool = True) -> IdentityDenylist | None:
    artifact = path if path is not None else runtime_artifact_path()
    if not artifact.is_file():
        if required:
            raise IdentityDenylistUnavailable(f"{artifact}: runtime identity denylist artifact is absent")
        return None
    data = load_yaml(artifact)
    return parse_identity_denylist(data, artifact)


def parse_identity_denylist(data: Any, path: Path | str = ARTIFACT_RELATIVE) -> IdentityDenylist:
    if not isinstance(data, dict):
        raise IdentityDenylistError(f"{path}: identity denylist artifact must be a mapping")
    unknown_keys = sorted(set(data) - _TOP_LEVEL_KEYS)
    if unknown_keys:
        raise IdentityDenylistError(f"{path}: unsupported identity denylist keys: {unknown_keys}")
    if data.get("version") != 1:
        raise IdentityDenylistError(f"{path}: unsupported identity denylist version")
    if data.get("normalization") != NORMALIZATION:
        raise IdentityDenylistError(f"{path}: identity denylist normalization must be {NORMALIZATION!r}")

    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise IdentityDenylistError(f"{path}: entries must be a non-empty list")

    entries: list[DenylistEntry] = []
    seen_tokens: set[str] = set()
    for index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            raise IdentityDenylistError(f"{path}: entries[{index}] must be a mapping")
        if set(raw) != _ENTRY_KEYS:
            raise IdentityDenylistError(f"{path}: entries[{index}] must contain only token, categories")
        token = raw["token"]
        categories = raw["categories"]
        if not isinstance(token, str) or not token:
            raise IdentityDenylistError(f"{path}: entries[{index}].token must be a non-empty string")
        normalized = normalize_token(token)
        if _HASH_RE.fullmatch(normalized):
            raise IdentityDenylistError(f"{path}: entries[{index}].token must not be a digest")
        if normalized in seen_tokens:
            raise IdentityDenylistError(f"{path}: duplicate token in entries[{index}]")
        seen_tokens.add(normalized)
        if not isinstance(categories, list) or not categories:
            raise IdentityDenylistError(f"{path}: entries[{index}].categories must be a non-empty list")
        category_tuple = tuple(categories)
        if any(not isinstance(category, str) for category in category_tuple):
            raise IdentityDenylistError(f"{path}: entries[{index}].categories must be strings")
        unknown = sorted(set(category_tuple) - ALLOWED_CATEGORIES)
        if unknown:
            raise IdentityDenylistError(f"{path}: entries[{index}] has unknown categories: {unknown}")
        if tuple(sorted(set(category_tuple))) != category_tuple:
            raise IdentityDenylistError(f"{path}: entries[{index}].categories must be unique and sorted")
        entries.append(DenylistEntry(token=token, normalized=normalized, categories=category_tuple))

    entries.sort(key=lambda entry: (entry.normalized, entry.categories))
    return IdentityDenylist(entries=tuple(entries))


def find_identity_matches(value: str, denylist: IdentityDenylist) -> tuple[DenylistMatch, ...]:
    normalized = normalize_token(value)
    matches: dict[str, DenylistMatch] = {}
    for entry in denylist.entries:
        if entry.normalized not in normalized:
            continue
        if entry.normalized in matches:
            continue
        matches[entry.normalized] = DenylistMatch(entry.categories)
    return tuple(matches.values())


def iter_entry_categories(entries: Iterable[DenylistEntry]) -> tuple[str, ...]:
    return tuple(sorted({category for entry in entries for category in entry.categories}))
