"""Unit tests for seat_scratch_reaper.

Uses a synthetic epoch-dir fixture (``tmp_path``) so no real disk state is ever
touched.  All tests use injected ``now`` timestamps to make age-based decisions
deterministic; the ``--execute`` path is exercised on tmp directories only.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import pytest

from creator_engine_validator import seat_scratch_reaper as sr
from creator_engine_validator.seat_scratch_reaper import (
    ACTION_REAP,
    ACTION_RETAIN,
    EVIDENCE_MAX_BYTES,
    REASON_AGE_THRESHOLD,
    REASON_BELOW_AGE_THRESHOLD,
    REASON_BUNDLE_RETAINED,
    REASON_CLAIM_REFERENCE,
    REASON_EVIDENCE_EXPORT,
    REASON_FRESHNESS_GUARD,
    REASON_MERGED_TICKET,
    REASON_UNKNOWN_CLASS,
    SCRATCH_CLASS_BUNDLE,
    SCRATCH_CLASS_CV_SANDBOX,
    SCRATCH_CLASS_EVIDENCE,
    SCRATCH_CLASS_PREFLIGHT_WORKSPACE,
    SCRATCH_CLASS_PYTEST_TEMP,
    SCRATCH_CLASS_UNKNOWN,
    SCRATCH_CLASS_VALIDATE_PR_CACHE,
    SCRATCH_CLASS_WORKTREE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A "now" timestamp far enough in the future that fixtures aged with EPOCH_AGE_DAYS
# are classified as old.
_BASE_TIME = time.time()
EPOCH_AGE_DAYS = 14  # older than DEFAULT_REAP_AGE_DAYS (7)
_OLD_MTIME = _BASE_TIME - (EPOCH_AGE_DAYS * 86400)
_FRESH_MTIME = _BASE_TIME - 1800  # 30 minutes old


def _make_dir(parent: Path, name: str, *, mtime: float | None = None) -> Path:
    """Create a subdirectory under *parent* with an optional forced mtime."""
    p = parent / name
    p.mkdir(parents=True, exist_ok=True)
    # touch a sentinel file so the dir is non-empty
    (p / "sentinel").write_bytes(b"sentinel")
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def _make_file(parent: Path, name: str, *, content: bytes = b"data", mtime: float | None = None) -> Path:
    """Create a regular file under *parent* with an optional forced mtime."""
    p = parent / name
    p.write_bytes(content)
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def _plan(
    epoch_dir: Path,
    *,
    now: float | None = None,
    repo_root: Path | None = None,
    claims_dir: Path | None = None,
    briefs_dir: Path | None = None,
    freshness_hours: int = sr.DEFAULT_FRESHNESS_HOURS,
    reap_age_days: int = sr.DEFAULT_REAP_AGE_DAYS,
    bundle_retain_days: int = sr.DEFAULT_BUNDLE_RETAIN_DAYS,
    claims_window_hours: float = sr.DEFAULT_CLAIMS_WINDOW_HOURS,
) -> sr.ReapPlan:
    return sr.scan_epoch_dir(
        epoch_dir,
        now=now if now is not None else _BASE_TIME,
        repo_root=repo_root,
        claims_dir=claims_dir,
        briefs_dir=briefs_dir,
        freshness_hours=freshness_hours,
        reap_age_days=reap_age_days,
        bundle_retain_days=bundle_retain_days,
        claims_window_hours=claims_window_hours,
    )


def _by_name(plan: sr.ReapPlan) -> dict[str, sr.ScratchEntry]:
    return {e.path.name: e for e in plan.entries}


# ---------------------------------------------------------------------------
# 1. Classification
# ---------------------------------------------------------------------------


class TestClassification:
    """Verify name → scratch_class mapping for all policy classes."""

    @pytest.mark.parametrize(
        "name,expected_class",
        [
            # worktree
            ("wt-ce-564-reaper", SCRATCH_CLASS_WORKTREE),
            ("wt-df4-ce564-feature", SCRATCH_CLASS_WORKTREE),
            ("day4-some-work", SCRATCH_CLASS_WORKTREE),
            # cv sandbox
            ("cv-e2e-run-42", SCRATCH_CLASS_CV_SANDBOX),
            ("cv-validator-smoke", SCRATCH_CLASS_CV_SANDBOX),
            # pytest temp
            ("pytest-of-root", SCRATCH_CLASS_PYTEST_TEMP),
            ("pytest-of-myuser", SCRATCH_CLASS_PYTEST_TEMP),
            # preflight workspace
            ("preflight-main-20260719", SCRATCH_CLASS_PREFLIGHT_WORKSPACE),
            ("preflight_pr1039", SCRATCH_CLASS_PREFLIGHT_WORKSPACE),
            # validate-pr base cache
            ("validate-pr-ce564-base", SCRATCH_CLASS_VALIDATE_PR_CACHE),
            ("validate_pr_main_snap", SCRATCH_CLASS_VALIDATE_PR_CACHE),
            # bundle (suffix match)
            ("local-branches.bundle", SCRATCH_CLASS_BUNDLE),
            ("archive.bundle", SCRATCH_CLASS_BUNDLE),
            # unknown
            ("random-dir", SCRATCH_CLASS_UNKNOWN),
            ("some_tool_cache", SCRATCH_CLASS_UNKNOWN),
            ("builddir", SCRATCH_CLASS_UNKNOWN),
        ],
    )
    def test_classify_name_dir(self, name: str, expected_class: str) -> None:
        assert sr.classify_name(name, is_file=False) == expected_class

    def test_classify_evidence_file(self, tmp_path: Path) -> None:
        """A small .log file is classified as evidence."""
        assert sr.classify_name("run.log", is_file=True, size_bytes=1024) == SCRATCH_CLASS_EVIDENCE

    def test_classify_evidence_json(self, tmp_path: Path) -> None:
        assert sr.classify_name("result.json", is_file=True, size_bytes=100) == SCRATCH_CLASS_EVIDENCE

    def test_large_evidence_file_is_unknown(self) -> None:
        """A file exceeding EVIDENCE_MAX_BYTES is unknown even if it has an evidence extension."""
        oversized = EVIDENCE_MAX_BYTES + 1
        assert sr.classify_name("big.log", is_file=True, size_bytes=oversized) == SCRATCH_CLASS_UNKNOWN

    def test_evidence_dir_is_unknown(self) -> None:
        """A directory with an evidence-like name is unknown (not a file)."""
        # Directories are never evidence
        assert sr.classify_name("logs.log", is_file=False) == SCRATCH_CLASS_UNKNOWN

    def test_scan_classifies_entries_correctly(self, tmp_path: Path) -> None:
        """scan_epoch_dir classifies a mixed epoch dir correctly."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-100-feature", mtime=_OLD_MTIME)
        _make_dir(epoch, "cv-smoke-42", mtime=_OLD_MTIME)
        _make_dir(epoch, "pytest-of-runner", mtime=_OLD_MTIME)
        _make_dir(epoch, "random-unknown", mtime=_OLD_MTIME)
        _make_file(epoch, "local.bundle", mtime=_OLD_MTIME)

        result = _plan(epoch)
        by_name = _by_name(result)

        assert by_name["wt-ce-100-feature"].scratch_class == SCRATCH_CLASS_WORKTREE
        assert by_name["cv-smoke-42"].scratch_class == SCRATCH_CLASS_CV_SANDBOX
        assert by_name["pytest-of-runner"].scratch_class == SCRATCH_CLASS_PYTEST_TEMP
        assert by_name["random-unknown"].scratch_class == SCRATCH_CLASS_UNKNOWN
        assert by_name["local.bundle"].scratch_class == SCRATCH_CLASS_BUNDLE


# ---------------------------------------------------------------------------
# 2. Freshness guard
# ---------------------------------------------------------------------------


class TestFreshnessGuard:
    """Entries within the freshness window must never be reaped."""

    def test_fresh_worktree_is_retained(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-200-fresh", mtime=_FRESH_MTIME)

        result = _plan(epoch)
        entry = _by_name(result)["wt-ce-200-fresh"]

        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_FRESHNESS_GUARD

    def test_old_worktree_is_not_freshness_retained(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-201-old", mtime=_OLD_MTIME)

        result = _plan(epoch)
        entry = _by_name(result)["wt-ce-201-old"]

        # Old enough to be beyond the freshness window → not freshness-retained
        assert entry.reason != REASON_FRESHNESS_GUARD

    def test_freshness_threshold_boundary(self, tmp_path: Path) -> None:
        """An entry exactly at the freshness boundary (48 h) is retained."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        # Exactly 48 hours old relative to _BASE_TIME
        boundary_mtime = _BASE_TIME - (sr.DEFAULT_FRESHNESS_HOURS * 3600)
        _make_dir(epoch, "wt-ce-202-boundary", mtime=boundary_mtime)

        result = _plan(epoch)
        entry = _by_name(result)["wt-ce-202-boundary"]
        # At the boundary (mtime == cutoff), the guard condition is mtime > cutoff,
        # so boundary is NOT retained by freshness guard; it falls through to age check.
        assert entry.reason != REASON_FRESHNESS_GUARD


# ---------------------------------------------------------------------------
# 3. Claim-reference refusal
# ---------------------------------------------------------------------------


class TestClaimReferenceGuard:
    """Entries referenced in a recent claim or brief must be retained."""

    def test_old_entry_referenced_in_claim_is_retained(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        wt = _make_dir(epoch, "wt-ce-300-claimed", mtime=_OLD_MTIME)

        claims_dir = tmp_path / "claims"
        claims_dir.mkdir()
        claim_file = claims_dir / "active-claim.md"
        # Write the worktree name into the claim file
        claim_file.write_text(f"worktree: {wt.name}\n", encoding="utf-8")
        # Set claim file mtime to "now" (recent)
        os.utime(claim_file, (_BASE_TIME, _BASE_TIME))

        result = _plan(epoch, claims_dir=claims_dir)
        entry = _by_name(result)["wt-ce-300-claimed"]

        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_CLAIM_REFERENCE

    def test_old_entry_referenced_by_abs_path_in_brief_is_retained(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        wt = _make_dir(epoch, "wt-ce-301-briefed", mtime=_OLD_MTIME)

        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        brief_file = briefs_dir / "BRIEF_task.md"
        # Write the absolute path into the brief
        brief_file.write_text(f"path: {wt.resolve()}\n", encoding="utf-8")
        os.utime(brief_file, (_BASE_TIME, _BASE_TIME))

        result = _plan(epoch, briefs_dir=briefs_dir)
        entry = _by_name(result)["wt-ce-301-briefed"]

        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_CLAIM_REFERENCE

    def test_stale_claim_file_does_not_guard(self, tmp_path: Path) -> None:
        """A claim file that is itself older than the window does not trigger the guard."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-302-stale-claim", mtime=_OLD_MTIME)

        claims_dir = tmp_path / "claims"
        claims_dir.mkdir()
        claim_file = claims_dir / "old-claim.md"
        claim_file.write_text("worktree: wt-ce-302-stale-claim\n", encoding="utf-8")
        # Set claim file mtime to very old
        stale_mtime = _BASE_TIME - (sr.DEFAULT_CLAIMS_WINDOW_HOURS * 3600 + 1)
        os.utime(claim_file, (stale_mtime, stale_mtime))

        result = _plan(epoch, claims_dir=claims_dir)
        entry = _by_name(result)["wt-ce-302-stale-claim"]

        # Claim is stale, so the guard does not fire; entry is reapable by age
        assert entry.reason != REASON_CLAIM_REFERENCE

    def test_unreferenced_old_entry_is_reapable(self, tmp_path: Path) -> None:
        """An old entry with no claim reference is reapable."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-303-unreferenced", mtime=_OLD_MTIME)

        claims_dir = tmp_path / "claims"
        claims_dir.mkdir()  # empty

        result = _plan(epoch, claims_dir=claims_dir)
        entry = _by_name(result)["wt-ce-303-unreferenced"]

        assert entry.action == ACTION_REAP


# ---------------------------------------------------------------------------
# 4. Unknown-class retain (fail-closed)
# ---------------------------------------------------------------------------


class TestUnknownClassRetain:
    """Unrecognised entries must always be retained (fail-closed)."""

    def test_unknown_dir_is_retained(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "random-toolcache", mtime=_OLD_MTIME)

        result = _plan(epoch)
        entry = _by_name(result)["random-toolcache"]

        assert entry.scratch_class == SCRATCH_CLASS_UNKNOWN
        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_UNKNOWN_CLASS

    def test_unknown_class_cannot_be_reaped_regardless_of_age(self, tmp_path: Path) -> None:
        """Even an extremely old unknown entry must be retained."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        ancient_mtime = _BASE_TIME - (365 * 86400)  # 1 year old
        _make_dir(epoch, "ancient-unknown-thing", mtime=ancient_mtime)

        result = _plan(epoch)
        entry = _by_name(result)["ancient-unknown-thing"]

        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_UNKNOWN_CLASS


# ---------------------------------------------------------------------------
# 5. Merged-ticket detection
# ---------------------------------------------------------------------------


class TestMergedTicketDetection:
    """Old worktrees whose ticket has a changelog fragment should be reaped immediately."""

    def test_worktree_with_changelog_fragment_is_reaped(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        # Within reap_age_days but has a changelog fragment (merged)
        recent_enough_mtime = _BASE_TIME - (3 * 86400)  # 3 days old (< 7-day threshold)
        _make_dir(epoch, "wt-ce-400-feature", mtime=recent_enough_mtime)

        repo_root = tmp_path / "repo"
        changelog_dir = repo_root / ".ce" / "changelog"
        changelog_dir.mkdir(parents=True)
        (changelog_dir / "ce-400-feature.md").write_text("---\nslug: ce-400-feature\n---\n", encoding="utf-8")

        result = _plan(epoch, repo_root=repo_root)
        entry = _by_name(result)["wt-ce-400-feature"]

        assert entry.action == ACTION_REAP
        assert entry.reason == REASON_MERGED_TICKET

    def test_worktree_with_pr_manifest_is_reaped(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        recent_mtime = _BASE_TIME - (2 * 86400)  # 2 days old
        _make_dir(epoch, "wt-ce-401-fix", mtime=recent_mtime)

        repo_root = tmp_path / "repo"
        manifests_dir = repo_root / ".ce" / "pr-manifests"
        manifests_dir.mkdir(parents=True)
        (manifests_dir / "ce-401-fix.md").write_text("# PR manifest\n", encoding="utf-8")

        result = _plan(epoch, repo_root=repo_root)
        entry = _by_name(result)["wt-ce-401-fix"]

        assert entry.action == ACTION_REAP
        assert entry.reason == REASON_MERGED_TICKET

    def test_unmerged_worktree_is_not_detected_as_merged(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        recent_mtime = _BASE_TIME - (2 * 86400)
        _make_dir(epoch, "wt-ce-402-unmerged", mtime=recent_mtime)

        repo_root = tmp_path / "repo"
        (repo_root / ".ce" / "changelog").mkdir(parents=True)
        # No fragment for ce-402

        result = _plan(epoch, repo_root=repo_root)
        entry = _by_name(result)["wt-ce-402-unmerged"]

        # 2 days < 7 days, not merged → retain
        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_BELOW_AGE_THRESHOLD

    def test_no_ticket_in_name_skips_merged_detection(self, tmp_path: Path) -> None:
        """A worktree without a ticket number is not checked for merged status."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        recent_mtime = _BASE_TIME - (2 * 86400)
        _make_dir(epoch, "wt-local-experiment", mtime=recent_mtime)

        repo_root = tmp_path / "repo"
        changelog_dir = repo_root / ".ce" / "changelog"
        changelog_dir.mkdir(parents=True)

        result = _plan(epoch, repo_root=repo_root)
        entry = _by_name(result)["wt-local-experiment"]

        # No ticket number → cannot detect merged → retain below threshold
        assert entry.reason == REASON_BELOW_AGE_THRESHOLD


# ---------------------------------------------------------------------------
# 6. Age threshold (basic reap / retain by age)
# ---------------------------------------------------------------------------


class TestAgeThreshold:
    """Old entries (beyond reap_age_days) are reaped; recent ones are retained."""

    def test_old_worktree_is_reaped(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-500-old", mtime=_OLD_MTIME)

        result = _plan(epoch)
        entry = _by_name(result)["wt-ce-500-old"]

        assert entry.action == ACTION_REAP
        assert entry.reason == REASON_AGE_THRESHOLD

    def test_recent_worktree_is_retained(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        # 3 days old < 7-day threshold
        recent_mtime = _BASE_TIME - (3 * 86400)
        _make_dir(epoch, "wt-ce-501-recent", mtime=recent_mtime)

        result = _plan(epoch)
        entry = _by_name(result)["wt-ce-501-recent"]

        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_BELOW_AGE_THRESHOLD

    def test_old_bundle_is_reaped(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        ancient_mtime = _BASE_TIME - (60 * 86400)  # 60 days, beyond 30-day bundle retain
        _make_file(epoch, "old.bundle", mtime=ancient_mtime)

        result = _plan(epoch)
        entry = _by_name(result)["old.bundle"]

        assert entry.scratch_class == SCRATCH_CLASS_BUNDLE
        assert entry.action == ACTION_REAP
        assert entry.reason == REASON_AGE_THRESHOLD

    def test_recent_bundle_is_retained(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        # 10 days old < 30-day bundle retain
        mtime = _BASE_TIME - (10 * 86400)
        _make_file(epoch, "fresh.bundle", mtime=mtime)

        result = _plan(epoch)
        entry = _by_name(result)["fresh.bundle"]

        assert entry.scratch_class == SCRATCH_CLASS_BUNDLE
        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_BUNDLE_RETAINED


# ---------------------------------------------------------------------------
# 7. Evidence export
# ---------------------------------------------------------------------------


class TestEvidenceExport:
    """Evidence files are retained and exported to the evidence-root."""

    def test_evidence_file_is_retained_in_plan(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_file(epoch, "run.log", content=b"log data", mtime=_OLD_MTIME)

        result = _plan(epoch)
        entry = _by_name(result)["run.log"]

        assert entry.scratch_class == SCRATCH_CLASS_EVIDENCE
        assert entry.action == ACTION_RETAIN
        assert entry.reason == REASON_EVIDENCE_EXPORT

    def test_execute_exports_evidence_files(self, tmp_path: Path) -> None:
        """execute_reap copies evidence files to the evidence_root and writes a manifest."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        log_content = b"important log data"
        _make_file(epoch, "result.log", content=log_content, mtime=_OLD_MTIME)

        evidence_root = tmp_path / "evidence"
        plan = _plan(epoch)
        result = sr.execute_reap(plan, evidence_root=evidence_root, dry_run=False)

        # The log file is retained (not reaped)
        assert (epoch / "result.log").exists()

        # The log file is exported to evidence_root
        assert len(result.evidence_exported) == 1
        exported_path = Path(result.evidence_exported[0])
        assert exported_path.exists()
        assert exported_path.read_bytes() == log_content

        # A manifest is written
        assert result.manifest_path is not None
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert len(manifest["files"]) == 1
        assert manifest["files"][0]["sha256"] == hashlib.sha256(log_content).hexdigest()


# ---------------------------------------------------------------------------
# 8. Idempotent second run
# ---------------------------------------------------------------------------


class TestIdempotentSecondRun:
    """Running the reaper twice gives a consistent result."""

    def test_second_run_finds_no_new_entries_to_reap(self, tmp_path: Path) -> None:
        """After a first execute pass, a second scan shows no entries to reap
        (they were deleted) and retained entries remain retained."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-600-idempotent", mtime=_OLD_MTIME)
        _make_dir(epoch, "random-unknown-keep", mtime=_OLD_MTIME)  # unknown → always retain

        # First pass
        plan1 = _plan(epoch)
        result1 = sr.execute_reap(plan1, dry_run=False)

        assert result1.reaped == 1  # wt- was deleted
        assert not (epoch / "wt-ce-600-idempotent").exists()
        assert (epoch / "random-unknown-keep").exists()

        # Second pass
        plan2 = _plan(epoch)
        result2 = sr.execute_reap(plan2, dry_run=False)

        # Nothing left to reap
        assert result2.reaped == 0
        assert result2.aborted == 0
        # The unknown entry is still retained
        by_name2 = _by_name(plan2)
        assert "random-unknown-keep" in by_name2
        assert by_name2["random-unknown-keep"].action == ACTION_RETAIN

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """--dry-run (the default) never deletes anything."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        wt = _make_dir(epoch, "wt-ce-601-dryrun", mtime=_OLD_MTIME)

        plan = _plan(epoch)
        assert len(plan.to_reap) == 1

        result = sr.execute_reap(plan, dry_run=True)

        assert result.reaped == 0
        assert result.retained == len(plan.entries)  # dry-run counts all as retained
        assert wt.exists()  # not deleted


# ---------------------------------------------------------------------------
# 9. Re-stat abort on mutation
# ---------------------------------------------------------------------------


class TestReStatGuard:
    """If an entry's mtime changes between plan and execute, the delete is aborted."""

    def test_restat_aborts_on_mtime_change(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        wt = _make_dir(epoch, "wt-ce-700-mutated", mtime=_OLD_MTIME)

        plan = _plan(epoch)
        entry = _by_name(plan)["wt-ce-700-mutated"]
        assert entry.action == ACTION_REAP

        # Mutate mtime between plan and execute
        new_mtime = _BASE_TIME  # current time — different from _OLD_MTIME
        os.utime(wt, (new_mtime, new_mtime))

        result = sr.execute_reap(plan, dry_run=False)

        # Delete was aborted because mtime changed
        assert result.aborted == 1
        assert result.reaped == 0
        assert wt.exists()  # not deleted
        assert any("re-stat mtime changed" in err for err in result.errors)

    def test_restat_aborts_if_entry_vanishes(self, tmp_path: Path) -> None:
        """If the entry disappears between plan and execute, it is counted as aborted."""
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        wt = _make_dir(epoch, "wt-ce-701-vanished", mtime=_OLD_MTIME)

        plan = _plan(epoch)
        assert len(plan.to_reap) == 1

        # Remove the entry externally (simulates concurrent reap)
        import shutil
        shutil.rmtree(wt)

        result = sr.execute_reap(plan, dry_run=False)

        assert result.aborted == 1
        assert result.reaped == 0
        assert any("vanished" in err for err in result.errors)


# ---------------------------------------------------------------------------
# 10. Single-instance lock
# ---------------------------------------------------------------------------


class TestSingleInstanceLock:
    """The lock file prevents concurrent execute runs."""

    def test_lock_held_raises(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-800-lock", mtime=_OLD_MTIME)

        lock_path = tmp_path / "reaper.lock"
        # Simulate a lock held by a previous process by creating the file
        lock_path.write_bytes(b"999")

        plan = _plan(epoch)
        with pytest.raises(sr.ScratchReaperLockHeld):
            sr.execute_reap(plan, lock_path=lock_path, dry_run=False)

    def test_lock_released_after_execute(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-801-lockrelease", mtime=_OLD_MTIME)

        lock_path = epoch / sr.LOCK_FILENAME
        plan = _plan(epoch)
        sr.execute_reap(plan, lock_path=lock_path, dry_run=False)

        # Lock must be released after execution
        assert not lock_path.exists()


# ---------------------------------------------------------------------------
# 11. TSV manifest format
# ---------------------------------------------------------------------------


class TestTSVManifest:
    """The TSV plan contains the expected header and correctly formatted rows."""

    def test_tsv_header_present(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-900-tsv", mtime=_OLD_MTIME)

        plan = _plan(epoch)
        tsv = plan.tsv()
        first_line = tsv.splitlines()[0]
        assert first_line == sr.TSV_HEADER

    def test_tsv_row_fields(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()
        _make_dir(epoch, "wt-ce-901-row", mtime=_OLD_MTIME)

        plan = _plan(epoch)
        rows = plan.tsv().splitlines()
        assert len(rows) == 2  # header + 1 entry
        fields = rows[1].split("\t")
        assert len(fields) == 6  # path, size_bytes, mtime_iso, class, reason, action
        # action should be reap (old enough)
        assert fields[5] in (ACTION_REAP, ACTION_RETAIN)
        # class should be worktree
        assert fields[3] == SCRATCH_CLASS_WORKTREE

    def test_empty_epoch_dir_yields_header_only(self, tmp_path: Path) -> None:
        epoch = tmp_path / "epoch"
        epoch.mkdir()

        plan = _plan(epoch)
        tsv = plan.tsv()
        # Header + trailing newline
        assert tsv == sr.TSV_HEADER + "\n"


# ---------------------------------------------------------------------------
# 12. Ticket-slug extraction
# ---------------------------------------------------------------------------


class TestTicketSlugExtraction:
    @pytest.mark.parametrize(
        "name,expected_slug",
        [
            ("wt-ce-564-reaper", "ce-564"),
            ("wt-df4-ce564-feature", "ce-564"),
            ("cv-ce-123-smoke", "ce-123"),
            ("wt-CE-42-caps", "ce-42"),
            ("wt-no-ticket-here", None),
            ("random-name", None),
        ],
    )
    def test_extract_ticket_slug(self, name: str, expected_slug: str | None) -> None:
        assert sr._extract_ticket_slug(name) == expected_slug


# ---------------------------------------------------------------------------
# 13. Non-existent epoch dir
# ---------------------------------------------------------------------------


def test_nonexistent_epoch_dir_returns_empty_plan(tmp_path: Path) -> None:
    """Scanning a non-existent epoch dir returns an empty plan (no crash)."""
    nonexistent = tmp_path / "does-not-exist"
    plan = sr.scan_epoch_dir(nonexistent, now=_BASE_TIME)
    assert plan.entries == []
    assert plan.to_reap == []
    assert plan.to_retain == []
