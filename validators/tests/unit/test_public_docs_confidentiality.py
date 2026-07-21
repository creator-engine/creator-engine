"""Confidentiality guard for the PUBLIC docs surface (CI merge gate).

The rule itself — which paths count as public, the forbidden patterns, the
``KNOWN_PENDING`` debt-ratchet allowlist, and the offense formatter — lives in
ONE place: :mod:`creator_engine_validator.public_docs_confidentiality`. This
test is a THIN caller of that module so there is no second copy of the rule to
drift. The same module also backs the fast ``scan-public-docs-confidentiality``
CLI check that also runs in the optional ``ce validate-pr`` diagnostic; this
test remains the authoritative required-CI caller.

The repository is public (it is the source of record for ``creator-engine.dev``),
so the README and the served ``docs/`` tree must never leak confidential
``ce-ops#NNN`` ticket references or internal host/network identifiers.

This test file is excluded from the scan by the module: it (like the module)
necessarily names the very patterns it forbids.
"""
from __future__ import annotations

import re
from pathlib import Path

from creator_engine_validator import public_docs_confidentiality as guard

_REPO_ROOT = guard.repo_root()
_DOCS_ROOT = _REPO_ROOT / "docs"
_README = _REPO_ROOT / "README.md"
_SELF = Path(__file__).resolve()

# Read the allowlist from the single source of truth so the test asserts
# against exactly what the CLI check enforces.
_KNOWN_PENDING = guard.KNOWN_PENDING


def _offenses(path: Path, *, repo_root: Path = _REPO_ROOT) -> list[str]:
    return guard.offenses(path, repo_root=repo_root)


def test_offenses_reports_planted_confidential_ticket_ref(tmp_path: Path):
    doc = tmp_path / "README.md"
    doc.write_text("Public prose must not mention ce-ops#123.\n", encoding="utf-8")

    hits = _offenses(doc, repo_root=tmp_path)

    assert len(hits) == 1
    assert "README.md:1 [confidential ce-ops# ticket reference]" in hits[0]


def test_offenses_reports_planted_private_repo_url(tmp_path: Path):
    """The URL form of a ce-ops private-repo link must also be flagged."""
    doc = tmp_path / "README.md"
    doc.write_text(
        "See https://github.com/creator-engine/ce-ops/issues/341 for details.\n",
        encoding="utf-8",
    )

    hits = _offenses(doc, repo_root=tmp_path)

    assert len(hits) == 1
    assert "README.md:1 [confidential ce-ops private-repo URL]" in hits[0]


def test_offenses_reports_planted_skynet_codename(tmp_path: Path):
    """The confidential internal codename 'skynet' must be flagged in any casing."""
    doc = tmp_path / "README.md"
    doc.write_text("Ratified in the CEO-Mode/skynet discussion.\n", encoding="utf-8")

    hits = _offenses(doc, repo_root=tmp_path)

    assert len(hits) == 1
    assert "README.md:1 [confidential internal codename skynet]" in hits[0]


def test_offenses_reports_planted_ce_ops_hyphen_ticket_ref(tmp_path: Path):
    """The hyphen form 'ce-ops-341' must be flagged (misses the existing # pattern)."""
    doc = tmp_path / "README.md"
    doc.write_text("tag: ce-ops-341\n", encoding="utf-8")

    hits = _offenses(doc, repo_root=tmp_path)

    assert len(hits) == 1
    assert "README.md:1 [confidential ce-ops hyphen ticket ref]" in hits[0]


def test_ce_ops_adr_hyphen_form_not_flagged_by_numeric_pattern(tmp_path: Path):
    """'ce-ops-adr-0003' must NOT be flagged by the numeric ce-ops-\\d+ pattern.

    The pattern requires digits immediately after 'ce-ops-'; 'adr' is not a digit,
    so ADR-ref slugs using this form are safe from false positives.
    """
    doc = tmp_path / "README.md"
    doc.write_text("tag: ce-ops-adr-0003\n", encoding="utf-8")

    hits = _offenses(doc, repo_root=tmp_path)

    # Only expect zero hits from the ce-ops-\d+ pattern; other patterns should
    # also not fire on this clean descriptor string.
    assert hits == []


def test_offenses_accepts_clean_temp_doc(tmp_path: Path):
    doc = tmp_path / "docs" / "clean.md"
    doc.parent.mkdir()
    doc.write_text("Public prose with no internal ticket, seat, or host markers.\n", encoding="utf-8")

    assert _offenses(doc, repo_root=tmp_path) == []


# --------------------------------------------------------------------------
# Dangling internal-doc link guard (kept local: a distinct rule from the
# single-sourced confidentiality scan).
#
# The README and served docs/ tree must never advertise a relative link to a
# repo-relative path that no longer exists. A dead link both reads as careless
# and — when it points at a now-removed internal roadmap/strategy doc — keeps
# advertising the existence of internal material we deliberately deleted.
#
# We scan markdown links in the public doc surface (README.md + docs/**.md) and
# fail if any RELATIVE link target does not resolve to a file in the repo.
# Only relative links are checked: external (http/https), anchors (#...), and
# mailto: links are skipped. Targets are resolved relative to the directory of
# the containing file (or the repo root for site-absolute "/foo" links).
# --------------------------------------------------------------------------

# Markdown inline links: ](target) or ](target "title").
_MD_LINK = re.compile(r"\]\(([^)]+)\)")


def _doc_markdown_files() -> list[Path]:
    """README plus every markdown file under docs/** (excluding this test)."""
    files: list[Path] = []
    if _README.is_file():
        files.append(_README)
    for path in sorted(_DOCS_ROOT.rglob("*.md")):
        if path.resolve() == _SELF:
            continue
        if path.is_file():
            files.append(path)
    return files


def _is_relative_doc_link(target: str) -> bool:
    """True only for repo-relative links we should resolve to a file."""
    low = target.lower()
    if low.startswith(("http://", "https://", "mailto:")):
        return False
    if target.startswith("#") or not target:
        return False
    return True


def _dangling_links(path: Path) -> list[str]:
    """Return ``"<rel>:<line> -> <target>"`` for each dead relative link."""
    rel = path.resolve().relative_to(_REPO_ROOT).as_posix()
    dead: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _MD_LINK.finditer(line):
            raw = match.group(1).strip()
            # Strip an optional link title: ](path "Title").
            target = raw.split(" ", 1)[0] if " " in raw else raw
            if not _is_relative_doc_link(target):
                continue
            # Drop any anchor / query suffix before resolving the file path.
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue  # pure in-page anchor that slipped the prefix check
            if path_part.startswith("/"):
                resolved = _REPO_ROOT / path_part.lstrip("/")
            else:
                resolved = path.parent / path_part
            if not resolved.exists():
                dead.append(f"{rel}:{lineno} -> {target}")
    return dead


def test_public_docs_have_no_dangling_internal_doc_links():
    """No public doc may link to a repo-relative path that does not exist."""
    offenders: list[str] = []
    for path in _doc_markdown_files():
        offenders.extend(_dangling_links(path))

    assert not offenders, (
        "Public docs contain dangling relative links to nonexistent repo files. "
        "Remove the link (and the sentence, if it only existed to point there), "
        "or repoint it at the file's current location. Dead links:\n  "
        + "\n  ".join(offenders)
    )


def test_tracked_text_files_contain_no_new_confidential_or_internal_references():
    """No non-allowlisted tracked text file may leak a forbidden internal reference."""
    offenders = guard.scan_offenses(repo_root=_REPO_ROOT)

    assert not offenders, (
        "Tracked text files leak confidential ce-ops# or internal host identifiers. "
        "Remove the reference (product-lens rewrite), or — only for the separate "
        "redact/relocate program — add a narrow ALLOWED_OFFENSES entry. " + guard.REMINDER
        + " Offending lines:\n  " + "\n  ".join(offenders)
    )


def test_readme_is_clean_and_never_allowlisted():
    """The README is the product front door: it must always be clean."""
    assert "README.md" not in _KNOWN_PENDING, (
        "README.md must never be allowlisted; it must be kept clean directly."
    )
    offenders = _offenses(_README)
    assert not offenders, (
        "README.md leaks confidential ce-ops# or internal host identifiers:\n  "
        + "\n  ".join(offenders)
    )


def test_known_pending_allowlist_only_shrinks():
    """Every allowlisted file must still exist AND still offend.

    This keeps the debt ratchet honest: a cleaned file (or a removed file) must
    be dropped from ``KNOWN_PENDING`` so the list cannot rot with stale entries.
    """
    stale: list[str] = []
    for rel in sorted(_KNOWN_PENDING):
        path = _REPO_ROOT / rel
        if not path.is_file():
            stale.append(f"{rel} (file no longer exists)")
            continue
        if not _offenses(path):
            stale.append(f"{rel} (file is now clean)")

    assert not stale, (
        "KNOWN_PENDING has stale entries; the allowlist may only shrink. "
        "Remove these now-clean/absent files from KNOWN_PENDING:\n  "
        + "\n  ".join(stale)
    )


def test_allowed_offenses_allowlist_only_shrinks():
    """Every baseline offense entry must still exist AND still offend."""
    stale: list[str] = []
    for rel, label in sorted(guard.ALLOWED_OFFENSES):
        path = _REPO_ROOT / rel
        if not path.is_file():
            stale.append(f"{rel} [{label}] (file no longer exists)")
            continue
        actual = {guard._offense_key(hit) for hit in _offenses(path)}
        if (rel, label) not in actual:
            stale.append(f"{rel} [{label}] (file no longer has this offense)")

    assert not stale, (
        "ALLOWED_OFFENSES has stale entries; the allowlist may only shrink. "
        "Remove these now-clean/absent file/token-class entries:\n  "
        + "\n  ".join(stale)
    )


def test_public_docs_internal_trees_have_only_known_exceptions():
    """No new docs/operations or docs/delivery files may enter public docs.

    Thin caller of the single-sourced internal-tree guard (ce-ops#283).
    """
    unreviewed, stale_exceptions = guard.internal_tree_violations(repo_root=_REPO_ROOT)

    assert not unreviewed and not stale_exceptions, (
        "Public docs contain internal operations/delivery files outside the "
        "explicit exception ratchet, or the ratchet lists files that no longer "
        "exist. Move net-new internal files out of the served docs tree, or "
        "add them deliberately to KNOWN_OPERATIONS_EXCEPTIONS / "
        "KNOWN_DELIVERY_EXCEPTIONS. Remove stale entries when files leave "
        "these trees.\nUnreviewed files:\n  "
        + ("\n  ".join(unreviewed) if unreviewed else "<none>")
        + "\nStale exceptions:\n  "
        + ("\n  ".join(stale_exceptions) if stale_exceptions else "<none>")
    )


def test_custody_runbook_is_an_exact_operations_exception():
    """The custody runbook is admitted; an adjacent unlisted path is refused."""
    custody_runbook = "docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md"
    unlisted_neighbor = "docs/operations/MATERIALIZER_APPKEY_CUSTODY_NOTES.md"
    paths = set(guard.KNOWN_OPERATIONS_EXCEPTIONS | guard.KNOWN_DELIVERY_EXCEPTIONS)
    paths.update({custody_runbook, unlisted_neighbor})

    unreviewed, stale_exceptions = guard.internal_tree_violations_for_paths(paths)

    assert unreviewed == [unlisted_neighbor]
    assert stale_exceptions == []


def test_devops_docs_are_exact_operations_exceptions():
    """The DevOps mandate/runbook pair is admitted; an adjacent path is refused."""
    mandate = "docs/operations/CE_DEVOPS_AGENT_MANDATE.md"
    runbook = "docs/operations/CE_DEVOPS_RECOVERY_RUNBOOK.md"
    unlisted_neighbor = "docs/operations/CE_DEVOPS_AGENT_NOTES.md"
    paths = set(guard.KNOWN_OPERATIONS_EXCEPTIONS | guard.KNOWN_DELIVERY_EXCEPTIONS)
    paths.update({mandate, runbook, unlisted_neighbor})

    unreviewed, stale_exceptions = guard.internal_tree_violations_for_paths(paths)

    assert unreviewed == [unlisted_neighbor]
    assert stale_exceptions == []
