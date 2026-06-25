"""Confidentiality guard for the PUBLIC docs surface.

The repository is public (it is the source of record for `creator-engine.dev`),
so the README and the served `docs/` tree must never leak two classes of
content:

1. **Confidential ``ce-ops#NNN`` ticket references.** The ``ce-ops`` tracker is
   a private, internal issue tracker. Its ticket numbers must never appear in
   any public doc.
2. **Internal host / network identifiers.** Tailnet hostnames, the internal VPS
   IP, and the hosting-provider name are internal fleet topology and must never
   appear in any public doc.

The guard scans the public doc surface (``README.md`` plus ``docs/**``) and
fails the build, listing every offending file and line, if a forbidden pattern
is found in any file that is not on the explicit, shrinking allowlist below.

The allowlist (``_KNOWN_PENDING``) is a *debt ratchet*: it enumerates the files
that still carry internal references pending the separate redact/relocate
cleanup. New leaks are blocked immediately (any file not on the list that
introduces an offender fails the build), and the list may only shrink — as a
file is cleaned it must be removed from the allowlist (a file on the allowlist
that no longer offends also fails the build, so the list cannot rot stale).

This test file itself is excluded from the scan: it necessarily names the very
patterns it forbids.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCS_ROOT = _REPO_ROOT / "docs"
_README = _REPO_ROOT / "README.md"

# This test file must not be scanned: it names the forbidden patterns by design.
_SELF = Path(__file__).resolve()

# Forbidden patterns in any public doc. Keep each pattern's human label for
# debuggable failure output.
_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("confidential ce-ops# ticket reference", re.compile(r"ce-ops#\d+")),
    ("internal tailnet hostname", re.compile(r"\.tailf3cfef\.ts\.net")),
    ("internal VPS IP", re.compile(r"100\.72\.252\.20")),
    ("internal hosting-provider name", re.compile(r"Hetzner")),
)

# Public-doc file extensions we scan. The served docs tree carries markdown,
# html, plain config/scanner fragments, key material, and svg assets — all of
# which are published verbatim, so all are in scope.
_SCAN_SUFFIXES = {
    ".md",
    ".html",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".svg",
    ".sh",
}

# Files that still carry internal references pending the separate
# redact/relocate cleanup. This list may ONLY shrink. Paths are repo-root
# relative, POSIX-separated.
_KNOWN_PENDING: frozenset[str] = frozenset(
    {
        "docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md",
        "docs/architecture/cockpit.md",
        "docs/architecture/egress-broker.md",
        "docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md",
        "docs/architecture/seat-sentinel-contract.md",
        "docs/architecture/tasks-handoff-contract.md",
        "docs/architecture/work-claim-locks.md",
        "docs/assets/ce-logo-v2-weldarm.svg",
        "docs/contracts/brownfield-adoption.md",
        "docs/contracts/computer-use-authority-envelope.md",
        "docs/contracts/computer-use-worker-harness.md",
        "docs/contracts/devops-privileged-action-broker.md",
        "docs/contracts/installer.md",
        "docs/contracts/orchestrator.md",
        "docs/contracts/plain-join.md",
        "docs/contracts/playbook-format.md",
        "docs/contracts/README.md",
        "docs/contracts/runtime-policy.md",
        "docs/decisions/0005-openbao-secret-identity-backend.md",
        "docs/decisions/ADR-0007-egress-gateway-publish-broker.md",
        "docs/decisions/ADR-0008-web-control-ui.md",
        "docs/decisions/ADR-0009-bounded-work-units-small-batches.md",
        "docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md",
        "docs/decisions/ADR-0011-devops-privileged-action-broker.md",
        "docs/decisions/ADR-0012-openbao-micro-unit-standup.md",
        "docs/design/controller-bootstrap-injection.md",
        "docs/design/controller-bootstrap-ssot.json",
        "docs/devops/openbao-approval-wall-arming.md",
        "docs/devops/openbao-operator-bringup.md",
        "docs/devops/openbao-production-golive.md",
        "docs/devops/openbao/provision-openbao.sh",
        "docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml",
        "docs/guide/contributing-to-ce.md",
        "docs/keys/ce-root-v1",
        "docs/operations/CONTAINED_LAUNCH_PROOF.md",
        "docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md",
        "docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md",
        "docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md",
        "docs/operations/MERGE_QUEUE_ENABLEMENT_RUNBOOK.md",
        "docs/operations/ONBOARD_APPLY_PROTOCOL.md",
        "docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md",
        "docs/operations/REVIEWER_TRIAGE.md",
        "docs/operations/SEAT_REAPER_PROTOCOL.md",
        "docs/operations/SWITCH_OPENAI_ACCOUNT.md",
        "docs/security/ce234-approval-capability-wall.md",
    }
)


def _public_doc_files() -> list[Path]:
    """All scanned public-doc files: README plus docs/** of scanned suffixes."""
    files: list[Path] = []
    if _README.is_file():
        files.append(_README)
    for path in sorted(_DOCS_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() == _SELF:
            continue
        if path.suffix.lower() in _SCAN_SUFFIXES:
            files.append(path)
    return files


def _offenses(path: Path) -> list[str]:
    """Return ``"<rel>:<line> [<label>] <line-text>"`` for each offending line."""
    rel = path.resolve().relative_to(_REPO_ROOT).as_posix()
    hits: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary-ish file; decode leniently so we still catch ascii leaks.
        text = path.read_bytes().decode("utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(line):
                hits.append(f"{rel}:{lineno} [{label}] {line.strip()}")
    return hits


# --------------------------------------------------------------------------
# Dangling internal-doc link guard (ce-ops#249).
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


def test_public_docs_contain_no_confidential_or_internal_references():
    """No NON-allowlisted public doc may leak a forbidden internal reference."""
    offenders: list[str] = []
    for path in _public_doc_files():
        rel = path.resolve().relative_to(_REPO_ROOT).as_posix()
        if rel in _KNOWN_PENDING:
            continue
        offenders.extend(_offenses(path))

    assert not offenders, (
        "Public docs leak confidential ce-ops# or internal host identifiers. "
        "Remove the reference (product-lens rewrite), or — only for the separate "
        "redact/relocate program — add the file to _KNOWN_PENDING. Offending "
        "lines:\n  " + "\n  ".join(offenders)
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
    be dropped from ``_KNOWN_PENDING`` so the list cannot rot with stale entries.
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
        "_KNOWN_PENDING has stale entries; the allowlist may only shrink. "
        "Remove these now-clean/absent files from _KNOWN_PENDING:\n  "
        + "\n  ".join(stale)
    )
