"""CE support-agent product-lens corpus — allowlist + confidentiality intersection (P0.1).

The `ce ask` support agent (CE_SUPPORT_AGENT_PLAN_20260627.md) grounds ONLY on a
curated product-lens slice of the public docs. This module owns the
*eligibility* rule for that slice and is the single source of truth for "which
files the support agent may load".

Eligibility is an INTERSECTION (plan §2c/§2d, defense-in-depth layer 1):

    eligible(doc) := product_lens(doc) AND confidentiality_clean(doc)

* ``product_lens`` is declared in the checked-in manifest
  ``support_corpus_allowlist.yaml`` (the §2a "Serve" list).
* ``confidentiality_clean`` is decided by the single-sourced #571/#306 guard
  ``public_docs_confidentiality.py`` — REUSED, never forked. A file is clean iff
  it has no forbidden-pattern offenses, is not on the guard's ``KNOWN_PENDING``
  debt ratchet, and is not a net-new file in an internal guarded tree
  (``docs/operations/**`` / ``docs/delivery/**``).

The corpus is therefore provably a subset of the confidentiality-clean public
surface: *you cannot leak what you never loaded.* The build fails closed if a
product-lens-listed entry is not confidentiality-clean, so the manifest can
never silently widen the corpus past the wall.
"""
from __future__ import annotations

from dataclasses import dataclass
import fnmatch
from pathlib import Path

import yaml

from . import public_docs_confidentiality as confidentiality
from .reporting import CheckResult, ValidationError, make_error

CHECK_NAME = "support_corpus"
CONTRACT = "validators/creator_engine_validator/support_corpus_allowlist.yaml"

_SELF = Path(__file__).resolve()
MANIFEST_FILENAME = "support_corpus_allowlist.yaml"


def repo_root() -> Path:
    """Repo root: three parents up from this module (mirrors the guard's rule)."""
    return _SELF.parents[2]


def manifest_path() -> Path:
    return _SELF.parent / MANIFEST_FILENAME


@dataclass(frozen=True)
class CorpusEligibility:
    """Result of intersecting the product-lens allowlist with the conf. guard.

    * ``eligible``   — product-lens AND confidentiality-clean AND present.
    * ``rejected``   — product-lens but NOT confidentiality-clean (fail-closed).
    * ``missing``    — product-lens glob/path that matched nothing in the tree
                       (skipped, not an error; docs land over time).
    """

    eligible: tuple[str, ...]
    rejected: tuple[tuple[str, str], ...]  # (rel, reason)
    missing: tuple[str, ...]


def load_manifest(*, path: Path | None = None) -> dict:
    p = path or manifest_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):  # pragma: no cover - corrupt manifest
        raise ValueError(f"support corpus manifest is not a mapping: {p}")
    return data


def product_lens_patterns(*, manifest: dict | None = None) -> list[str]:
    """The flat, ordered, de-duplicated list of product-lens serve patterns."""
    man = manifest if manifest is not None else load_manifest()
    patterns: list[str] = []
    seen: set[str] = set()
    for family in (man.get("families") or {}).values():
        for entry in (family or {}).get("serve") or []:
            rel = str(entry).strip()
            if rel and rel not in seen:
                seen.add(rel)
                patterns.append(rel)
    return patterns


def _expand_pattern(pattern: str, *, root: Path) -> list[str]:
    """Expand one manifest entry against the working tree (repo-root-relative)."""
    if any(ch in pattern for ch in "*?[]"):
        matches = [
            p.resolve().relative_to(root).as_posix()
            for p in sorted(root.glob(pattern))
            if p.is_file()
        ]
        return matches
    candidate = (root / pattern)
    return [pattern] if candidate.is_file() else []


def _confidentiality_clean(rel: str, *, root: Path) -> str | None:
    """Return None if confidentiality-clean, else a human reason it is rejected.

    Reuses the single-sourced #571/#306 guard primitives — no forked rules.
    """
    # Debt-ratchet: still carries internal refs pending redact/relocate.
    if rel in confidentiality.KNOWN_PENDING:
        return "on the confidentiality KNOWN_PENDING debt ratchet"
    # Internal guarded trees (docs/operations/**, docs/delivery/**) are internal
    # surfaces; even allowlisted entries there are not product-lens-servable.
    for tree_rel, _exceptions in confidentiality.INTERNAL_GUARDED_TREES:
        if rel == tree_rel or rel.startswith(tree_rel + "/"):
            return f"inside internal guarded tree {tree_rel}/**"
    # Forbidden-pattern scan (ce-ops#, seat logins, internal hosts/IP/provider).
    path = root / rel
    hits = confidentiality.offenses(path, repo_root=root)
    if hits:
        return f"leaks a confidential/internal reference: {hits[0]}"
    return None


def evaluate(*, repo_root: Path | None = None) -> CorpusEligibility:
    """Compute the eligible corpus = product-lens ∩ confidentiality-clean."""
    root = (repo_root or globals()["repo_root"]()).resolve()
    eligible: list[str] = []
    rejected: list[tuple[str, str]] = []
    missing: list[str] = []
    seen_eligible: set[str] = set()

    for pattern in product_lens_patterns():
        expanded = _expand_pattern(pattern, root=root)
        if not expanded:
            missing.append(pattern)
            continue
        for rel in expanded:
            reason = _confidentiality_clean(rel, root=root)
            if reason is not None:
                rejected.append((rel, reason))
            elif rel not in seen_eligible:
                seen_eligible.add(rel)
                eligible.append(rel)

    return CorpusEligibility(
        eligible=tuple(eligible),
        rejected=tuple(rejected),
        missing=tuple(missing),
    )


def corpus_roots() -> tuple[str, ...]:
    """Directory roots the support read-only profile restricts reads to.

    Derived from the manifest's static (non-glob) prefixes so the hook_check
    support profile (P0.3) and the corpus stay single-sourced. README and other
    top-level files resolve to the repo root; doc families resolve to their
    directory. Used as the read-allowlist roots, then narrowed per-file by
    ``evaluate()`` eligibility.
    """
    roots: set[str] = set()
    for pattern in product_lens_patterns():
        # Take the leading static path component (before any glob magic).
        parts = Path(pattern).parts
        static: list[str] = []
        for part in parts:
            if any(ch in part for ch in "*?[]"):
                break
            static.append(part)
        if len(static) <= 1:
            roots.add(".")  # top-level file (README.md, CONTRIBUTING.md, ...)
        else:
            roots.add(Path(*static[:-1]).as_posix())
    return tuple(sorted(roots))


def run(paths: list[Path] | None = None) -> CheckResult:
    """Standalone check: the product-lens corpus must be confidentiality-clean.

    Fails closed — any product-lens entry that is NOT confidentiality-clean is a
    CE-SUPPORT-CORPUS error (the manifest may not widen the corpus past the
    wall). ``missing`` entries are NOT errors (docs land over time).
    """
    root: Path | None = None
    if paths:
        first = paths[0].resolve()
        if (first / "docs").is_dir() or (first / ".git").exists():
            root = first

    result = evaluate(repo_root=root)
    errors: list[ValidationError] = []
    for rel, reason in result.rejected:
        errors.append(
            make_error(
                code="CE-SUPPORT-CORPUS",
                path=rel,
                field="product-lens corpus entry",
                message=(
                    "support-corpus allowlist lists a product-lens doc that is "
                    f"NOT confidentiality-clean ({reason}). The support corpus "
                    "must be a subset of the confidentiality-clean surface; "
                    "remove the entry from support_corpus_allowlist.yaml or clean "
                    "the doc. " + confidentiality.REMINDER
                ),
                contract=CONTRACT,
            )
        )
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
