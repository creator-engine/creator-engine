"""Seat-scratch space reaper — per-ticket worktree and sandbox retention policy (ce-ops#564).

Ratified retention policy (Operator, 2026-07-19 — ce-ops#564):

  RETAIN: anything referenced by an open claim or unharvested ledger entry
  (manifest-safe refusal is MANDATORY); anything with mtime within the
  freshness window (48 h default); anything with an unrecognised class
  (fail-closed to retain).

  REAP at 7 days or at merge-confirmation (changelog-fragment/pr-manifest
  presence on the local main checkout), whichever is earlier:
    * per-ticket worktrees (``wt-*``, ``day4-*``)
    * validation sandboxes (``cv-*``)
    * pytest temp trees (``pytest-of-*``)
    * preflight workspaces (``preflight-*`` / ``preflight_*``)
    * validate-pr base caches (``validate-pr-*`` / ``validate_pr_*``)

  BUNDLES: retained 30 days (independent class; ``*.bundle``).

  SMALL EVIDENCE FILES (<50 MB): exported to ``--evidence-root`` before any
  deletion and then retained; never deleted by this module.

  UNKNOWN CLASS: fail-closed to retain (never reap unrecognised entries).

Single-run lock: reap runs are serialised by an ``O_CREAT | O_EXCL`` lock
file.  ``--dry-run`` (the default) emits the plan and never acquires the lock.

Two-phase execution: (1) plan — classify every top-level entry in the epoch
dir and emit a TSV manifest; (2) delete — re-stat each entry to confirm its
mtime is unchanged before removing it (race guard).

Pre-reap evidence export: before the delete phase, small evidence files are
copied to ``<evidence-root>/<epoch-name>/`` and a sha256 manifest is written.

Usage (as wired in ``ce seat-scratch reap``):

    ce seat-scratch reap plan  <epoch-dir> [options]
    ce seat-scratch reap exec  <epoch-dir> --evidence-root <dir> [options]

The entry point is :func:`scan_epoch_dir` (returns a :class:`ReapPlan`) and
:func:`execute_reap` (executes a :class:`ReapPlan`).  The CLI layer in
``v3_cli`` owns the argument plumbing; this module is purely policy + I/O.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

# ---------------------------------------------------------------------------
# Scratch-class constants
# ---------------------------------------------------------------------------

SCRATCH_CLASS_WORKTREE = "worktree"
SCRATCH_CLASS_CV_SANDBOX = "cv_sandbox"
SCRATCH_CLASS_PYTEST_TEMP = "pytest_temp"
SCRATCH_CLASS_PREFLIGHT_WORKSPACE = "preflight_workspace"
SCRATCH_CLASS_VALIDATE_PR_CACHE = "validate_pr_cache"
SCRATCH_CLASS_BUNDLE = "bundle"
SCRATCH_CLASS_EVIDENCE = "evidence"
SCRATCH_CLASS_UNKNOWN = "unknown"

# Actions
ACTION_REAP = "reap"
ACTION_RETAIN = "retain"

# Retain/reap reasons (emitted in the TSV plan)
REASON_FRESHNESS_GUARD = "freshness_guard"
REASON_CLAIM_REFERENCE = "claim_reference"
REASON_UNKNOWN_CLASS = "unknown_class"
REASON_BELOW_AGE_THRESHOLD = "below_age_threshold"
REASON_MERGED_TICKET = "merged_ticket_detected"
REASON_AGE_THRESHOLD = "age_threshold_exceeded"
REASON_BUNDLE_RETAINED = "bundle_retained"
REASON_EVIDENCE_EXPORT = "evidence_export"

# Policy defaults (all overridable via CLI args)
DEFAULT_FRESHNESS_HOURS: int = 48
DEFAULT_REAP_AGE_DAYS: int = 7
DEFAULT_BUNDLE_RETAIN_DAYS: int = 30
DEFAULT_CLAIMS_WINDOW_HOURS: float = 24.0 * 7  # 7 days

#: Maximum file size eligible for evidence export.
EVIDENCE_MAX_BYTES: int = 50 * 1024 * 1024  # 50 MiB

# TSV
TSV_HEADER = "\t".join(["path", "size_bytes", "mtime_iso", "class", "reason", "action"])

# Filenames used by this module
LOCK_FILENAME = ".seat-scratch-reaper.lock"
MANIFEST_FILENAME = "evidence-manifest.json"

# ---------------------------------------------------------------------------
# Name-classification patterns (ordered most-specific to least-specific)
# ---------------------------------------------------------------------------

#: Compiled name-match patterns.  Evaluated in order; first match wins.
_CLASS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (SCRATCH_CLASS_CV_SANDBOX, re.compile(r"^cv-")),
    (SCRATCH_CLASS_PYTEST_TEMP, re.compile(r"^pytest-of-")),
    (SCRATCH_CLASS_PREFLIGHT_WORKSPACE, re.compile(r"^preflight[-_]")),
    (SCRATCH_CLASS_VALIDATE_PR_CACHE, re.compile(r"^validate-pr[-_]|^validate_pr[-_]")),
    (SCRATCH_CLASS_WORKTREE, re.compile(r"^wt-|^day4-")),
    (SCRATCH_CLASS_BUNDLE, re.compile(r"\.bundle$", re.IGNORECASE)),
]

#: Evidence file extensions — matched only when the entry is a regular file
#: whose size is below EVIDENCE_MAX_BYTES.
_EVIDENCE_EXT_RE = re.compile(
    r"\.(log|txt|json|jsonl|yaml|yml|md|sha256|tar\.gz|tgz)$",
    re.IGNORECASE,
)

# Ticket slug extraction — finds "ce-NNN" (with or without the hyphen) in a
# name so we can check for a matching changelog fragment / pr-manifest.
_TICKET_SLUG_RE = re.compile(r"\bce[-_]?(\d+)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScratchEntry:
    """Classification result for one top-level entry in an epoch dir."""

    path: Path
    size_bytes: int
    mtime: float  # float POSIX timestamp (st_mtime)
    scratch_class: str
    reason: str
    action: str  # ACTION_REAP | ACTION_RETAIN

    @property
    def mtime_iso(self) -> str:
        return datetime.fromtimestamp(self.mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    def to_tsv_row(self) -> str:
        return "\t".join(
            [
                str(self.path),
                str(self.size_bytes),
                self.mtime_iso,
                self.scratch_class,
                self.reason,
                self.action,
            ]
        )


@dataclass
class ReapPlan:
    """Full plan for one epoch dir: the TSV manifest before any deletion."""

    epoch_dir: Path
    entries: list[ScratchEntry] = field(default_factory=list)

    def tsv(self) -> str:
        rows = [TSV_HEADER] + [e.to_tsv_row() for e in self.entries]
        return "\n".join(rows) + "\n"

    @property
    def to_reap(self) -> list[ScratchEntry]:
        return [e for e in self.entries if e.action == ACTION_REAP]

    @property
    def to_retain(self) -> list[ScratchEntry]:
        return [e for e in self.entries if e.action == ACTION_RETAIN]


@dataclass
class ReapResult:
    """Outcome of executing a :class:`ReapPlan`."""

    planned: int
    reaped: int
    retained: int
    aborted: int  # entries skipped because re-stat detected mutation
    evidence_exported: list[str] = field(default_factory=list)
    manifest_path: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "planned": self.planned,
            "reaped": self.reaped,
            "retained": self.retained,
            "aborted": self.aborted,
            "evidence_exported": self.evidence_exported,
            "manifest_path": self.manifest_path,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ScratchReaperLockHeld(RuntimeError):
    """Raised when the reaper lock file is already present."""


# ---------------------------------------------------------------------------
# Name classification
# ---------------------------------------------------------------------------


def classify_name(name: str, *, is_file: bool = False, size_bytes: int = 0) -> str:
    """Map a top-level entry name to a :data:`SCRATCH_CLASS_*` constant.

    Order of precedence: cv_sandbox → pytest_temp → preflight_workspace →
    validate_pr_cache → worktree → bundle → evidence → unknown.
    """
    for scratch_class, pattern in _CLASS_PATTERNS:
        if pattern.search(name):
            return scratch_class
    # Evidence: only regular files below the size limit
    if is_file and size_bytes < EVIDENCE_MAX_BYTES and _EVIDENCE_EXT_RE.search(name):
        return SCRATCH_CLASS_EVIDENCE
    return SCRATCH_CLASS_UNKNOWN


# ---------------------------------------------------------------------------
# Merged-ticket detection
# ---------------------------------------------------------------------------


def _extract_ticket_slug(name: str) -> str | None:
    """Return the normalised ``ce-NNN`` slug from an entry name, or ``None``."""
    m = _TICKET_SLUG_RE.search(name)
    if m:
        return f"ce-{m.group(1)}"
    return None


def is_merged_ticket(name: str, repo_root: Path) -> bool:
    """Return ``True`` if a changelog fragment or pr-manifest exists for the ticket.

    A worktree/sandbox named ``wt-ce-564-reaper`` is considered merged when
    ``.ce/changelog/*ce-564*.md`` or ``.ce/pr-manifests/*ce-564*.md`` is
    present on the local main checkout.  This is the proven signal — git
    ``branch -r --merged`` is uninformative once the branch has been deleted.
    """
    slug = _extract_ticket_slug(name)
    if not slug:
        return False
    # Use both the hyphenated form and plain digits for robustness
    patterns = [f"*{slug}*.md", f"*{slug.replace('-', '')}*.md"]
    for dirname in (".ce/changelog", ".ce/pr-manifests"):
        d = repo_root / dirname
        if not d.is_dir():
            continue
        for pat in patterns:
            if any(d.glob(pat)):
                return True
    return False


# ---------------------------------------------------------------------------
# Reference guard (claims / briefs)
# ---------------------------------------------------------------------------


def _recent_files(directory: Path, window_hours: float) -> list[Path]:
    """Return files under *directory* whose mtime is within *window_hours*."""
    if not directory.is_dir():
        return []
    cutoff = time.time() - (window_hours * 3600)
    result: list[Path] = []
    try:
        for child in directory.iterdir():
            if not child.is_file():
                continue
            try:
                if child.stat().st_mtime >= cutoff:
                    result.append(child)
            except OSError:
                pass
    except OSError:
        pass
    return result


def is_claim_referenced(
    entry: Path,
    *,
    claims_dir: Path | None = None,
    briefs_dir: Path | None = None,
    window_hours: float = DEFAULT_CLAIMS_WINDOW_HOURS,
) -> bool:
    """Return ``True`` if the entry's name or absolute path appears in a recent claim or brief.

    "Recent" means the file was modified within *window_hours*.  Both exact
    name-match and full-path-match are checked so that claims recorded as
    relative paths and absolute paths both trigger the guard.
    """
    name = entry.name
    abs_path = str(entry.resolve())
    dirs = [d for d in (claims_dir, briefs_dir) if d is not None]
    for d in dirs:
        for f in _recent_files(d, window_hours):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if name in text or abs_path in text:
                return True
    return False


# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------


@contextmanager
def _acquire_lock(lock_path: Path) -> Generator[None, None, None]:
    """Acquire an exclusive lock file; raise :class:`ScratchReaperLockHeld` on contention."""
    try:
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ScratchReaperLockHeld(
            f"another reaper instance is running (lock: {lock_path})"
        ) from exc
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Evidence export (pre-reap)
# ---------------------------------------------------------------------------


def _export_evidence(
    entries: list[ScratchEntry],
    evidence_root: Path,
    epoch_name: str,
) -> tuple[list[str], str | None]:
    """Copy small evidence files to *evidence_root/<epoch_name>/* and write a sha256 manifest.

    Returns ``(exported_paths, manifest_path | None)``.
    """
    candidates = [
        e
        for e in entries
        if e.scratch_class == SCRATCH_CLASS_EVIDENCE and e.path.is_file()
    ]
    if not candidates:
        return [], None

    dest_dir = evidence_root / epoch_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict[str, Any]] = []
    exported: list[str] = []

    for entry in candidates:
        try:
            data = entry.path.read_bytes()
        except OSError:
            continue
        sha = hashlib.sha256(data).hexdigest()
        dest = dest_dir / entry.path.name
        dest.write_bytes(data)
        manifest_entries.append(
            {
                "source": str(entry.path),
                "dest": str(dest),
                "sha256": sha,
                "size_bytes": len(data),
            }
        )
        exported.append(str(dest))

    if not manifest_entries:
        return [], None

    manifest_path = dest_dir / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(
            {"epoch": epoch_name, "files": manifest_entries},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return exported, str(manifest_path)


# ---------------------------------------------------------------------------
# Scan (plan phase)
# ---------------------------------------------------------------------------


def scan_epoch_dir(
    epoch_dir: Path,
    *,
    now: float | None = None,
    repo_root: Path | None = None,
    claims_dir: Path | None = None,
    briefs_dir: Path | None = None,
    freshness_hours: int = DEFAULT_FRESHNESS_HOURS,
    reap_age_days: int = DEFAULT_REAP_AGE_DAYS,
    bundle_retain_days: int = DEFAULT_BUNDLE_RETAIN_DAYS,
    claims_window_hours: float = DEFAULT_CLAIMS_WINDOW_HOURS,
) -> ReapPlan:
    """Classify every top-level entry in *epoch_dir* and return a :class:`ReapPlan`.

    No entries are deleted here.  All policy decisions are deterministic given
    the same directory state and ``now`` timestamp, making this function
    suitable for tests with injected time.

    Policy ordering (evaluated top-to-bottom; first matching rule wins):

    1. **Freshness guard** — mtime within *freshness_hours* → retain.
    2. **Unknown class** — unrecognised name → retain (fail-closed).
    3. **Claim reference** — name/path appears in a recent claim or brief → retain.
    4. **Evidence class** — eligible evidence files → retain (exported pre-reap).
    5. **Bundle class** — bundle age ≤ *bundle_retain_days* → retain; else reap.
    6. **Merged-ticket detection** (reapable classes only) → reap immediately.
    7. **Age threshold** — older than *reap_age_days* → reap; else retain.
    """
    if now is None:
        now = time.time()

    entries: list[ScratchEntry] = []

    if not epoch_dir.is_dir():
        return ReapPlan(epoch_dir=epoch_dir, entries=entries)

    freshness_cutoff = now - (freshness_hours * 3600)
    reap_cutoff = now - (reap_age_days * 86400)
    bundle_cutoff = now - (bundle_retain_days * 86400)

    for child in sorted(epoch_dir.iterdir()):
        # Skip the lock file itself
        if child.name == LOCK_FILENAME:
            continue

        try:
            st = child.stat()
            mtime = st.st_mtime
            size = st.st_size
        except OSError:
            continue

        is_file = child.is_file()
        scratch_class = classify_name(child.name, is_file=is_file, size_bytes=size)

        def _entry(reason: str, action: str) -> ScratchEntry:
            return ScratchEntry(
                path=child,
                size_bytes=size,
                mtime=mtime,
                scratch_class=scratch_class,
                reason=reason,
                action=action,
            )

        # Rule 1: freshness guard
        if mtime > freshness_cutoff:
            entries.append(_entry(REASON_FRESHNESS_GUARD, ACTION_RETAIN))
            continue

        # Rule 2: unknown class — fail-closed
        if scratch_class == SCRATCH_CLASS_UNKNOWN:
            entries.append(_entry(REASON_UNKNOWN_CLASS, ACTION_RETAIN))
            continue

        # Rule 3: claim / brief reference guard
        if is_claim_referenced(
            child,
            claims_dir=claims_dir,
            briefs_dir=briefs_dir,
            window_hours=claims_window_hours,
        ):
            entries.append(_entry(REASON_CLAIM_REFERENCE, ACTION_RETAIN))
            continue

        # Rule 4: evidence class — retain (evidence export happens in execute phase)
        if scratch_class == SCRATCH_CLASS_EVIDENCE:
            entries.append(_entry(REASON_EVIDENCE_EXPORT, ACTION_RETAIN))
            continue

        # Rule 5: bundle class
        if scratch_class == SCRATCH_CLASS_BUNDLE:
            if mtime > bundle_cutoff:
                entries.append(_entry(REASON_BUNDLE_RETAINED, ACTION_RETAIN))
            else:
                entries.append(_entry(REASON_AGE_THRESHOLD, ACTION_REAP))
            continue

        # Rules 6–7: reapable scratch classes
        # Rule 6: merged-ticket detection
        if repo_root is not None and is_merged_ticket(child.name, repo_root):
            entries.append(_entry(REASON_MERGED_TICKET, ACTION_REAP))
            continue

        # Rule 7: age threshold
        if mtime <= reap_cutoff:
            entries.append(_entry(REASON_AGE_THRESHOLD, ACTION_REAP))
        else:
            entries.append(_entry(REASON_BELOW_AGE_THRESHOLD, ACTION_RETAIN))

    return ReapPlan(epoch_dir=epoch_dir, entries=entries)


# ---------------------------------------------------------------------------
# Execute (delete phase)
# ---------------------------------------------------------------------------


def execute_reap(
    plan: ReapPlan,
    *,
    evidence_root: Path | None = None,
    lock_path: Path | None = None,
    dry_run: bool = True,
) -> ReapResult:
    """Execute *plan*: export evidence then delete qualifying entries.

    When *dry_run* is ``True`` (the default), no lock is acquired and no files
    are deleted; the function returns a result with ``reaped=0`` that reflects
    what *would* happen.

    When *dry_run* is ``False``, a single-instance lock is acquired and the
    delete phase uses a re-stat guard: each entry's mtime is re-checked against
    the value recorded during the plan phase.  A changed mtime causes that
    entry to be skipped (``aborted``).
    """
    if dry_run:
        return ReapResult(
            planned=len(plan.entries),
            reaped=0,
            retained=len(plan.entries),
            aborted=0,
            evidence_exported=[],
            manifest_path=None,
            errors=[],
        )

    if lock_path is None:
        lock_path = plan.epoch_dir / LOCK_FILENAME

    with _acquire_lock(lock_path):
        return _execute_under_lock(plan, evidence_root=evidence_root)


def _execute_under_lock(
    plan: ReapPlan,
    *,
    evidence_root: Path | None,
) -> ReapResult:
    to_reap = plan.to_reap
    retained_count = len(plan.to_retain)

    # Evidence export before any deletion
    exported: list[str] = []
    manifest_path: str | None = None
    if evidence_root is not None:
        epoch_name = plan.epoch_dir.name
        exported, manifest_path = _export_evidence(plan.entries, evidence_root, epoch_name)

    reaped = 0
    aborted = 0
    errors: list[str] = []

    for entry in to_reap:
        # Re-stat guard: confirm mtime unchanged since plan phase
        try:
            current_stat = entry.path.stat()
            if current_stat.st_mtime != entry.mtime:
                aborted += 1
                errors.append(
                    f"re-stat mtime changed, skipping: {entry.path} "
                    f"(plan={entry.mtime}, current={current_stat.st_mtime})"
                )
                continue
        except FileNotFoundError:
            # Already gone (concurrent reap or external removal)
            aborted += 1
            errors.append(f"entry vanished before delete: {entry.path}")
            continue
        except OSError as exc:
            aborted += 1
            errors.append(f"re-stat failed, skipping: {entry.path}: {exc}")
            continue

        try:
            if entry.path.is_dir():
                shutil.rmtree(entry.path)
            else:
                entry.path.unlink()
            reaped += 1
        except OSError as exc:
            errors.append(f"delete failed: {entry.path}: {exc}")

    return ReapResult(
        planned=len(plan.entries),
        reaped=reaped,
        retained=retained_count,
        aborted=aborted,
        evidence_exported=exported,
        manifest_path=manifest_path,
        errors=errors,
    )
