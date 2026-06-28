"""Single source of truth for the PUBLIC-docs confidentiality rule.

The repository is public (it is the source of record for ``creator-engine.dev``),
so the README and the served ``docs/`` tree must never leak two classes of
content:

1. **Confidential ``ce-ops#NNN`` ticket references.** The ``ce-ops`` tracker is
   a private, internal issue tracker. Its ticket numbers must never appear in
   any public doc.
2. **Internal host / network identifiers.** Tailnet hostnames, seat-login
   markers, the internal VPS IP, and the hosting-provider name are internal
   fleet topology and must never appear in any public doc.

This module owns the rule (the public-doc file set, the forbidden patterns, the
``KNOWN_PENDING`` debt-ratchet allowlist, and the offense formatter). It is the
ONE place the rule lives. Two callers reuse it without forking it:

* the CI test ``test_public_docs_confidentiality.py`` (fail-closed merge gate),
* the fast standalone CLI check ``scan-public-docs-confidentiality`` that runs
  in ``ce validate-pr`` so a leak is caught BEFORE push, not only at CI.

The ``KNOWN_PENDING`` allowlist is a *debt ratchet*: it enumerates the files
that still carry internal references pending the separate redact/relocate
cleanup. New leaks are blocked immediately (any file not on the list that
introduces an offender fails), and the list may only shrink — a cleaned/removed
allowlisted file must be dropped from it.

This module file itself is excluded from the scan: it necessarily names the very
patterns it forbids.
"""
from __future__ import annotations

import re
from pathlib import Path

from .reporting import CheckResult, ValidationError, make_error

CHECK_NAME = "public_docs_confidentiality"
CONTRACT = "validators/tests/unit/test_public_docs_confidentiality.py"

# The standing reminder, surfaced verbatim in the failure remediation so a seat
# that triggers the guard learns the rule at the point of failure.
REMINDER = (
    "If you touch docs/**, run the confidentiality guard before push; "
    "ZERO ce-ops# refs in public docs."
)

# Forbidden patterns in any public doc. Keep each pattern's human label for
# debuggable failure output.
FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("confidential ce-ops# ticket reference", re.compile(r"ce-ops#\d+")),
    ("internal seat-login marker", re.compile(r"\bce-dev-\d+\b")),
    ("internal tailnet hostname", re.compile(r"\.tailf3cfef\.ts\.net")),
    ("internal VPS IP", re.compile(r"100\.72\.252\.20")),
    ("internal hosting-provider name", re.compile(r"Hetzner")),
)

# Public-doc file extensions we scan. The served docs tree carries markdown,
# html, plain config/scanner fragments, key material, and svg assets — all of
# which are published verbatim, so all are in scope.
SCAN_SUFFIXES = {
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
KNOWN_PENDING: frozenset[str] = frozenset(
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
# ``docs/operations/**`` and ``docs/delivery/**`` are internal operating/
# delivery surfaces that currently live in the public docs tree. These explicit
# allowlists are a debt ratchet: current files are listed so the guard passes
# today, but future net-new files in either tree fail until they are moved out
# or deliberately added here. The guard also fails on stale entries (a listed
# file that no longer exists), so the lists may only shrink as files leave.
KNOWN_OPERATIONS_EXCEPTIONS: frozenset[str] = frozenset(
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
        "docs/operations/PRESS_MERGE_BUNDLE.md",
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

KNOWN_DELIVERY_EXCEPTIONS: frozenset[str] = frozenset(
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

# Internal public-doc trees guarded against net-new files, paired with their
# debt-ratchet exception allowlists.
INTERNAL_GUARDED_TREES: tuple[tuple[str, frozenset[str]], ...] = (
    ("docs/operations", KNOWN_OPERATIONS_EXCEPTIONS),
    ("docs/delivery", KNOWN_DELIVERY_EXCEPTIONS),
)

# This module file must not be scanned: it names the forbidden patterns by
# design.
_SELF = Path(__file__).resolve()


def repo_root() -> Path:
    """Repo root: three parents up from this module.

    ``validators/creator_engine_validator/public_docs_confidentiality.py`` ->
    ``<repo>``.
    """
    return _SELF.parents[2]


def public_doc_files(*, repo_root: Path | None = None) -> list[Path]:
    """All scanned public-doc files: README plus ``docs/**`` of scanned suffixes."""
    root = (repo_root or globals()["repo_root"]()).resolve()
    files: list[Path] = []
    readme = root / "README.md"
    if readme.is_file():
        files.append(readme)
    docs_root = root / "docs"
    for path in sorted(docs_root.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() == _SELF:
            continue
        if path.suffix.lower() in SCAN_SUFFIXES:
            files.append(path)
    return files


def display_rel(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def offenses(path: Path, *, repo_root: Path) -> list[str]:
    """Return ``"<rel>:<line> [<label>] <line-text>"`` for each offending line."""
    rel = display_rel(path, repo_root=repo_root)
    hits: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary-ish file; decode leniently so we still catch ascii leaks.
        text = path.read_bytes().decode("utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in FORBIDDEN_PATTERNS:
            if pattern.search(line):
                hits.append(f"{rel}:{lineno} [{label}] {line.strip()}")
    return hits


def scan_offenses(*, repo_root: Path | None = None) -> list[str]:
    """Scan the whole public-doc surface, honouring ``KNOWN_PENDING``.

    Returns one formatted line per non-allowlisted offending line.
    """
    root = (repo_root or globals()["repo_root"]()).resolve()
    offenders: list[str] = []
    for path in public_doc_files(repo_root=root):
        rel = path.resolve().relative_to(root).as_posix()
        if rel in KNOWN_PENDING:
            continue
        offenders.extend(offenses(path, repo_root=root))
    return offenders


def internal_tree_files(root: Path, *, repo_root: Path) -> frozenset[str]:
    """All files below an internal public-doc tree, repo-root relative."""
    if not root.exists():
        return frozenset()
    return frozenset(
        display_rel(path, repo_root=repo_root)
        for path in root.rglob("*")
        if path.is_file()
    )


def internal_tree_violations(*, repo_root: Path | None = None) -> tuple[list[str], list[str]]:
    """Return ``(unreviewed, stale_exceptions)`` for the guarded internal trees.

    ``unreviewed`` are net-new files in ``docs/operations/**`` or
    ``docs/delivery/**`` not on the exception ratchet (these must be moved out
    of the served tree or deliberately added). ``stale_exceptions`` are listed
    files that no longer exist (these must be removed so the list only shrinks).
    """
    root = (repo_root or globals()["repo_root"]()).resolve()
    unreviewed: list[str] = []
    stale: list[str] = []
    for root_rel, known_exceptions in INTERNAL_GUARDED_TREES:
        actual = internal_tree_files(root / root_rel, repo_root=root)
        unreviewed.extend(sorted(actual - known_exceptions))
        stale.extend(sorted(known_exceptions - actual))
    return unreviewed, stale


def run(paths: list[Path] | None = None) -> CheckResult:
    """Standalone-check entrypoint for the CLI.

    ``paths`` is accepted for signature parity with other checks; the rule
    always scans the canonical public-doc surface rooted at the repo root, so
    the argument is advisory only (the first path, if a repo root, is used).
    """
    root: Path | None = None
    if paths:
        first = paths[0].resolve()
        if (first / "docs").is_dir() or (first / ".git").exists():
            root = first
    errors: list[ValidationError] = []

    # 1) Confidential ce-ops# / internal-host pattern scan.
    for line in scan_offenses(repo_root=root):
        rel = line.split(":", 1)[0]
        errors.append(
            make_error(
                code="CE-CONFIDENTIALITY",
                path=rel,
                field="public-doc line",
                message=(
                    f"public doc leaks a confidential/internal reference: {line}. "
                    "Remove the reference (product-lens rewrite). "
                    f"{REMINDER}"
                ),
                contract=CONTRACT,
            )
        )

    # 2) Internal-tree guard (ce-ops#283): no net-new docs/operations or
    #    docs/delivery files in the public tree, and no stale ratchet entries.
    unreviewed, stale = internal_tree_violations(repo_root=root)
    for rel in unreviewed:
        errors.append(
            make_error(
                code="CE-INTERNAL-TREE",
                path=rel,
                field="net-new internal file",
                message=(
                    "net-new internal file in the public docs tree; move it out "
                    "of the served docs tree, or deliberately add it to the "
                    "ce-ops#283 exception ratchet. "
                    f"{REMINDER}"
                ),
                contract=CONTRACT,
            )
        )
    for rel in stale:
        errors.append(
            make_error(
                code="CE-INTERNAL-TREE",
                path=rel,
                field="stale exception",
                message=(
                    "exception ratchet lists a file that no longer exists; the "
                    "list may only shrink, so remove this stale entry."
                ),
                contract=CONTRACT,
            )
        )
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
