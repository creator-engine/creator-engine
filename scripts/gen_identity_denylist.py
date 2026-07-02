#!/usr/bin/env python3
"""Generate the hashed CE-internal identity denylist artifact.

The source registry is private and must be supplied explicitly via
``--registry``. This generator stores only SHA-256 digests of normalized
identifier values in the committed artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_RELATIVE = Path("validators/creator_engine_validator/data/identity_denylist.generated.yaml")
MIN_TOKEN_LENGTH = 3
SKIP_VALUES = frozenset({"TODO_VERIFY"})


@dataclass(frozen=True)
class Candidate:
    value: str
    category: str


def _iter_mapping_items(data: dict[str, Any], key: str) -> Iterable[dict[str, Any]]:
    raw = data.get(key, [])
    if not isinstance(raw, list):
        return ()
    return (item for item in raw if isinstance(item, dict))


def _candidate(value: Any, category: str) -> Candidate | None:
    if not isinstance(value, str):
        return None
    normalized = value.casefold()
    if value in SKIP_VALUES or len(normalized) < MIN_TOKEN_LENGTH:
        return None
    return Candidate(value=value, category=category)


def _field_candidate(item: dict[str, Any], key: str, category: str) -> Candidate | None:
    return _candidate(item.get(key), category)


def _list_candidates(item: dict[str, Any], key: str, category: str) -> Iterable[Candidate]:
    raw = item.get(key, [])
    if not isinstance(raw, list):
        return ()
    return tuple(candidate for value in raw if (candidate := _candidate(value, category)) is not None)


def derive_candidates(registry: dict[str, Any]) -> tuple[Candidate, ...]:
    candidates: list[Candidate] = []

    for repo in _iter_mapping_items(registry, "repos"):
        candidates.extend(
            candidate
            for candidate in (
                _field_candidate(repo, "name", "repo-name"),
                _field_candidate(repo, "owner", "repo-owner"),
            )
            if candidate is not None
        )

    for account in _iter_mapping_items(registry, "accounts"):
        candidates.extend(
            candidate
            for candidate in (
                _field_candidate(account, "login", "account-login"),
                _field_candidate(account, "owning_seat", "account-owning-seat"),
                _field_candidate(account, "host", "account-host"),
            )
            if candidate is not None
        )

    for host in _iter_mapping_items(registry, "host_topology"):
        candidates.extend(
            candidate
            for candidate in (
                _field_candidate(host, "name", "host-topology-name"),
                _field_candidate(host, "host", "host-topology-host"),
            )
            if candidate is not None
        )
        candidates.extend(_list_candidates(host, "users", "host-topology-user"))

    for signing_key in _iter_mapping_items(registry, "signing_keys"):
        candidates.extend(
            candidate
            for candidate in (
                _field_candidate(signing_key, "custody_seat", "signing-key-custody-seat"),
                _field_candidate(signing_key, "custody_host", "signing-key-custody-host"),
            )
            if candidate is not None
        )

    for entry in _iter_mapping_items(registry, "authoring_review_matrix"):
        seat = _field_candidate(entry, "seat", "authoring-review-seat")
        if seat is not None:
            candidates.append(seat)
        candidates.extend(_list_candidates(entry, "authors_as", "authoring-review-author"))
        candidates.extend(_list_candidates(entry, "may_review", "authoring-review-reviewer"))

    return tuple(candidates)


def _artifact_doc(candidates: Sequence[Candidate]) -> dict[str, Any]:
    by_digest: dict[str, dict[str, Any]] = {}
    categories_by_digest: defaultdict[str, set[str]] = defaultdict(set)

    for candidate in candidates:
        normalized = candidate.value.casefold()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        by_digest.setdefault(digest, {"sha256": digest, "length": len(normalized)})
        categories_by_digest[digest].add(candidate.category)

    entries = [
        {**entry, "categories": sorted(categories_by_digest[digest])}
        for digest, entry in by_digest.items()
    ]
    entries.sort(key=lambda entry: (entry["length"], entry["sha256"]))
    return {
        "version": 1,
        "generated_by": "scripts/gen_identity_denylist.py",
        "source": "identity-registry",
        "normalization": "casefold",
        "token_lengths": sorted({entry["length"] for entry in entries}),
        "entries": entries,
    }


def render(registry_path: Path) -> str:
    with registry_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"identity registry must be a mapping: {registry_path}")
    doc = _artifact_doc(derive_candidates(data))
    if not doc["entries"]:
        raise ValueError("identity registry produced an empty denylist")
    return yaml.safe_dump(doc, sort_keys=False)


def write(registry_path: Path, artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(render(registry_path), encoding="utf-8")


def check(registry_path: Path, artifact_path: Path) -> bool:
    expected = render(registry_path)
    try:
        committed = artifact_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return committed == expected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path, help="path to infra/identity-registry.yaml")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify the committed artifact is current")
    mode.add_argument("--write", action="store_true", help="rewrite the committed artifact")
    parser.add_argument(
        "--artifact",
        type=Path,
        default=_REPO_ROOT / ARTIFACT_RELATIVE,
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = args.registry
    if not registry.is_file():
        print(f"identity registry is missing: {registry}", file=sys.stderr)
        return 2
    artifact = args.artifact
    try:
        if args.write:
            write(registry, artifact)
            return 0
        if check(registry, artifact):
            return 0
        print(
            "identity denylist artifact is stale; run "
            f"`{Path(__file__).name} --registry <path> --write` with ce-ops access",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI must fail closed with context
        print(f"failed to generate identity denylist: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
