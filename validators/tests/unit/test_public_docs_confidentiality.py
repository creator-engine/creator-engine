"""Confidentiality guard for the PUBLIC docs surface.

The repository is public (it is the source of record for `creator-engine.dev`),
so the README and the served `docs/` tree must never leak two classes of
content:

1. **Confidential ``ce-ops#NNN`` ticket references.** The ``ce-ops`` tracker is
   a private, internal issue tracker. Its ticket numbers must never appear in
   any public doc.
2. **Internal host / network identifiers.** Tailnet hostnames, seat-login
   markers, the internal VPS IP, and the hosting-provider name are internal
   fleet topology and must never appear in any public doc.

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
    ("internal seat-login marker", re.compile(r"\bce-dev-\d+\b")),
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
        "docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml",
        "docs/guide/contributing-to-ce.md",
        "docs/keys/ce-root-v1",
        "docs/security/ce234-approval-capability-wall.md",
    }
)

# Internal-tree guard exceptions (ce-ops#283).
#
# docs/operations/** and docs/delivery/** are internal operating/delivery
# surfaces that currently live in the public docs tree. These explicit
# allowlists are a debt ratchet: current files are listed so the guard passes
# today, but future net-new files in either tree fail until they are moved or
# deliberately added here.
_KNOWN_OPERATIONS_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md",
        "docs/operations/AGENT_NATIVE_BOOTSTRAP.md",
        "docs/operations/AUTHOR_A_CE_VALID_PR.md",
        "docs/operations/CE_EVENT_PROTOCOL.md",
        "docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md",
        "docs/operations/CLAUDE_CODE_HOOK_PACK.md",
        "docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md",
        "docs/operations/COMPLETION_REPORT_PROTOCOL.md",
        "docs/operations/CONNECTOR_PROTOCOL.md",
        "docs/operations/CONTAINED_CONTROLLER_PARITY_ACCEPTANCE.md",
        "docs/operations/CONTROLLER_BOUNDARY_POLICY.md",
        "docs/operations/CONTROLLER_IDENTITY_PROTOCOL.md",
        "docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md",
        "docs/operations/DISTRIBUTED_IDENTITY_PROTOCOL.md",
        "docs/operations/EVIDENCE_FAN_IN_PROTOCOL.md",
        "docs/operations/EXTENSION_HOOK_CONTRACT.md",
        "docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md",
        "docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md",
        "docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md",
        "docs/operations/HARNESS_SEAT_CONTRACT.md",
        "docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md",
        "docs/operations/HERDR_OPERATOR_REACH_PLANE.md",
        "docs/operations/INSTALLED_CE_DOGFOOD_MIGRATION.md",
        "docs/operations/INTEGRATION_QUEUE_DRY_RUN.md",
        "docs/operations/NO_COPY_PASTE_PATTERN.md",
        "docs/operations/ONBOARD_APPLY_PROTOCOL.md",
        "docs/operations/PANE_REGISTRY_PROTOCOL.md",
        "docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md",
        "docs/operations/PCL_PROTOCOL.md",
        "docs/operations/PCO_FANIN_PROTOCOL.md",
        "docs/operations/REVIEWER_TRIAGE.md",
        "docs/operations/REVIEWER_VENUE_AUTHORITY.md",
        "docs/operations/REVIEW_GATE_REVIEWER_VENUE_DESIGN.md",
        "docs/operations/ROLE_BOUNDARY_FAILSAFE_STAGE_1_DESIGN.md",
        "docs/operations/ROOT_WORKTREE_INVARIANT.md",
        "docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md",
        "docs/operations/SEAT_REAPER_PROTOCOL.md",
        "docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md",
        "docs/operations/STATE_BOUNDARY_PROTOCOL.md",
        "docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md",
        "docs/operations/WORKER_CONTAINER_PROTOCOL.md",
        "docs/operations/WORKER_HOST_READINESS.md",
        "docs/operations/WORKTREE_ALLOCATOR_PROTOCOL.md",
        "docs/operations/WORKTREE_LEASE_PROTOCOL.md",
        "docs/operations/session-continuity-protocol.md",
    }
)

_KNOWN_DELIVERY_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md",
        "docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md",
        "docs/delivery/DEFINITION_OF_DONE.md",
        "docs/delivery/DEFINITION_OF_READY.md",
        "docs/delivery/DEPLOYMENT_APPROVAL_POLICY.md",
        "docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md",
        "docs/delivery/MERGE_APPROVAL_CHECKLIST.md",
        "docs/delivery/NEXT_TASK_PROTOCOL.md",
        "docs/delivery/README.md",
        "docs/delivery/RELEASE_CANDIDATE_CHECKLIST.md",
        "docs/delivery/RELEASE_DEPLOY_GOVERNANCE.md",
        "docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md",
        "docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md",
        "docs/delivery/REVIEW_GATE.md",
        "docs/delivery/ROLLBACK_AND_POST_RELEASE_EVIDENCE.md",
        "docs/delivery/SCOPE_AUDIT_CHECKLIST.md",
        "docs/delivery/VERSIONING_AND_RELEASE_POLICY.md",
        "docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md",
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


def _display_rel(path: Path, *, repo_root: Path = _REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _internal_tree_files(root: Path) -> frozenset[str]:
    """All files below an internal public-doc tree, repo-root relative."""
    if not root.exists():
        return frozenset()
    return frozenset(_display_rel(path) for path in root.rglob("*") if path.is_file())


def _offenses(path: Path, *, repo_root: Path = _REPO_ROOT) -> list[str]:
    """Return ``"<rel>:<line> [<label>] <line-text>"`` for each offending line."""
    rel = _display_rel(path, repo_root=repo_root)
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


def test_offenses_reports_planted_confidential_ticket_ref(tmp_path: Path):
    doc = tmp_path / "README.md"
    doc.write_text("Public prose must not mention ce-ops#123.\n", encoding="utf-8")

    hits = _offenses(doc, repo_root=tmp_path)

    assert len(hits) == 1
    assert "README.md:1 [confidential ce-ops# ticket reference]" in hits[0]


def test_offenses_accepts_clean_temp_doc(tmp_path: Path):
    doc = tmp_path / "docs" / "clean.md"
    doc.parent.mkdir()
    doc.write_text("Public prose with no internal ticket, seat, or host markers.\n", encoding="utf-8")

    assert _offenses(doc, repo_root=tmp_path) == []


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


def test_public_docs_internal_trees_have_only_known_exceptions():
    """No new docs/operations or docs/delivery files may enter public docs."""
    guarded_trees = (
        ("docs/operations", _KNOWN_OPERATIONS_EXCEPTIONS),
        ("docs/delivery", _KNOWN_DELIVERY_EXCEPTIONS),
    )
    unreviewed: list[str] = []
    stale_exceptions: list[str] = []

    for root_rel, known_exceptions in guarded_trees:
        actual = _internal_tree_files(_REPO_ROOT / root_rel)
        unreviewed.extend(sorted(actual - known_exceptions))
        stale_exceptions.extend(sorted(known_exceptions - actual))

    assert not unreviewed and not stale_exceptions, (
        "Public docs contain internal operations/delivery files outside the "
        "explicit exception ratchet, or the ratchet lists files that no longer "
        "exist. Move net-new internal files out of the served docs tree, or "
        "add them deliberately to _KNOWN_OPERATIONS_EXCEPTIONS / "
        "_KNOWN_DELIVERY_EXCEPTIONS. Remove stale entries when files leave "
        "these trees.\nUnreviewed files:\n  "
        + ("\n  ".join(unreviewed) if unreviewed else "<none>")
        + "\nStale exceptions:\n  "
        + ("\n  ".join(stale_exceptions) if stale_exceptions else "<none>")
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
