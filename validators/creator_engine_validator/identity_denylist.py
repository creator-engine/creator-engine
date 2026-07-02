"""Hashed CE-internal identity denylist loader and matcher."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .loader import load_yaml

ARTIFACT_RELATIVE = Path("data/identity_denylist.generated.yaml")
NORMALIZATION = "casefold"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
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


@dataclass(frozen=True)
class DenylistEntry:
    sha256: str
    length: int
    categories: tuple[str, ...]


@dataclass(frozen=True)
class IdentityDenylist:
    token_lengths: tuple[int, ...]
    entries: dict[str, DenylistEntry]


@dataclass(frozen=True)
class DenylistMatch:
    sha256: str
    length: int
    categories: tuple[str, ...]


class IdentityDenylistError(ValueError):
    """Raised when the generated identity denylist is absent or malformed."""


def normalize_token(value: str) -> str:
    return value.casefold()


def digest_token(value: str) -> str:
    return hashlib.sha256(normalize_token(value).encode("utf-8")).hexdigest()


def _package_data_path() -> Path:
    return Path(__file__).resolve().parent / ARTIFACT_RELATIVE


def load_identity_denylist(path: Path | None = None) -> IdentityDenylist:
    artifact = path if path is not None else _package_data_path()
    data = load_yaml(artifact)
    return parse_identity_denylist(data, artifact)


def parse_identity_denylist(data: Any, path: Path | str = ARTIFACT_RELATIVE) -> IdentityDenylist:
    if not isinstance(data, dict):
        raise IdentityDenylistError(f"{path}: identity denylist artifact must be a mapping")
    if data.get("version") != 1:
        raise IdentityDenylistError(f"{path}: unsupported identity denylist version")
    if data.get("normalization") != NORMALIZATION:
        raise IdentityDenylistError(f"{path}: identity denylist normalization must be {NORMALIZATION!r}")

    raw_lengths = data.get("token_lengths")
    if not isinstance(raw_lengths, list) or not raw_lengths:
        raise IdentityDenylistError(f"{path}: token_lengths must be a non-empty list")
    token_lengths = tuple(raw_lengths)
    if any(not isinstance(length, int) or length < 1 for length in token_lengths):
        raise IdentityDenylistError(f"{path}: token_lengths must contain positive integers")
    if tuple(sorted(set(token_lengths))) != token_lengths:
        raise IdentityDenylistError(f"{path}: token_lengths must be unique and sorted")

    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise IdentityDenylistError(f"{path}: entries must be a non-empty list")

    entries: dict[str, DenylistEntry] = {}
    for index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            raise IdentityDenylistError(f"{path}: entries[{index}] must be a mapping")
        if set(raw) != {"sha256", "length", "categories"}:
            raise IdentityDenylistError(
                f"{path}: entries[{index}] must contain only sha256, length, categories"
            )
        digest = raw["sha256"]
        length = raw["length"]
        categories = raw["categories"]
        if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
            raise IdentityDenylistError(f"{path}: entries[{index}].sha256 must be a SHA-256 hex digest")
        if digest in entries:
            raise IdentityDenylistError(f"{path}: duplicate digest in entries[{index}]")
        if not isinstance(length, int) or length < 1:
            raise IdentityDenylistError(f"{path}: entries[{index}].length must be a positive integer")
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
        entries[digest] = DenylistEntry(digest, length, category_tuple)

    entry_lengths = tuple(sorted({entry.length for entry in entries.values()}))
    if entry_lengths != token_lengths:
        raise IdentityDenylistError(f"{path}: token_lengths do not match entry lengths")
    return IdentityDenylist(token_lengths=token_lengths, entries=entries)


def find_identity_matches(value: str, denylist: IdentityDenylist) -> tuple[DenylistMatch, ...]:
    normalized = normalize_token(value)
    matches: dict[str, DenylistMatch] = {}
    for length in denylist.token_lengths:
        if length > len(normalized):
            continue
        for start in range(0, len(normalized) - length + 1):
            digest = hashlib.sha256(normalized[start : start + length].encode("utf-8")).hexdigest()
            entry = denylist.entries.get(digest)
            if entry is None or digest in matches:
                continue
            matches[digest] = DenylistMatch(digest, entry.length, entry.categories)
    return tuple(matches.values())


def iter_entry_categories(entries: Iterable[DenylistEntry]) -> tuple[str, ...]:
    return tuple(sorted({category for entry in entries for category in entry.categories}))
