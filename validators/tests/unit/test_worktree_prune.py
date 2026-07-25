from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from creator_engine_validator import ce_cli, worktree_prune


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _set_old(path: Path, *, hours: float = 96.0) -> None:
    ts = time.time() - (hours * 3600)
    for current, dirnames, filenames in os.walk(path, topdown=False):
        current_path = Path(current)
        for name in filenames:
            os.utime(current_path / name, (ts, ts))
        for name in dirnames:
            os.utime(current_path / name, (ts, ts))
        os.utime(current_path, (ts, ts))


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.email", "ce@example.invalid")
    _git(repo, "config", "user.name", "CE Test")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")

    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, stdout=subprocess.PIPE)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "main")
    return repo


def _add_worktree(repo: Path, tmp_path: Path, name: str, branch: str) -> Path:
    path = tmp_path / name
    _git(repo, "worktree", "add", "-b", branch, str(path), "origin/main")
    return path


def _by_path(result: worktree_prune.WorktreePruneResult) -> dict[Path, worktree_prune.WorktreeVerdict]:
    return {entry.path: entry for entry in result.entries}


def test_scan_classifies_clean_dirty_unpushed_and_orphaned_worktrees(tmp_path: Path):
    repo = _make_repo(tmp_path)
    extra_root = tmp_path / "extra"
    extra_root.mkdir()

    clean = _add_worktree(repo, tmp_path, "wt-clean", "clean-merged")
    dirty = _add_worktree(repo, tmp_path, "wt-dirty", "dirty-local")
    unpushed = _add_worktree(repo, tmp_path, "wt-unpushed", "unpushed-local")
    (dirty / "README.md").write_text("dirty\n", encoding="utf-8")
    (unpushed / "feature.txt").write_text("new content\n", encoding="utf-8")
    _git(unpushed, "add", "feature.txt")
    _git(unpushed, "commit", "-m", "unpushed content")

    orphan = extra_root / "orphan-empty"
    orphan.mkdir()
    (orphan / ".git").write_text(f"gitdir: {tmp_path / 'missing-gitdir'}\n", encoding="utf-8")

    for path in (clean, dirty, unpushed, orphan):
        _set_old(path)

    result = worktree_prune.scan_worktrees(
        repo,
        extra_roots=[extra_root],
        age_hours=72,
    )
    entries = _by_path(result)

    assert entries[clean.resolve()].verdict == "PRUNABLE"
    assert entries[clean.resolve()].reason == "merged"
    assert entries[dirty.resolve()].verdict == "REPORT_ONLY"
    assert entries[dirty.resolve()].reason == "dirty"
    assert entries[unpushed.resolve()].verdict == "REPORT_ONLY"
    assert entries[unpushed.resolve()].reason == "not-on-origin"
    assert entries[orphan.resolve()].verdict == "PRUNABLE"
    assert entries[orphan.resolve()].reason == "orphan-empty"
    assert entries[repo.resolve()].reason == "active-worktree"


def test_apply_removes_only_prunable_worktrees_and_appends_audit(tmp_path: Path):
    repo = _make_repo(tmp_path)
    extra_root = tmp_path / "extra"
    extra_root.mkdir()
    clean = _add_worktree(repo, tmp_path, "wt-clean", "clean-merged")
    dirty = _add_worktree(repo, tmp_path, "wt-dirty", "dirty-local")
    (dirty / "README.md").write_text("dirty\n", encoding="utf-8")
    orphan = extra_root / "orphan-empty"
    orphan.mkdir()
    (orphan / ".git").write_text(f"gitdir: {tmp_path / 'missing-gitdir'}\n", encoding="utf-8")
    for path in (clean, dirty, orphan):
        _set_old(path)

    state_root = tmp_path / "state"
    result = worktree_prune.apply_prune(
        repo,
        extra_roots=[extra_root],
        age_hours=72,
        state_root=state_root,
    )
    entries = _by_path(result)

    assert entries[clean.resolve()].removed is True
    assert not clean.exists()
    assert entries[dirty.resolve()].removed is False
    assert dirty.exists()
    assert entries[orphan.resolve()].removed is True
    assert not orphan.exists()
    audit_lines = (state_root / worktree_prune.AUDIT_FILENAME).read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 2
    records = [json.loads(line) for line in audit_lines]
    assert {record["path"] for record in records} == {str(clean.resolve()), str(orphan.resolve())}
    assert all(record["verdict"] == "PRUNABLE" for record in records)


def test_apply_never_removes_invocation_linked_worktree(tmp_path: Path):
    repo = _make_repo(tmp_path)
    active = _add_worktree(repo, tmp_path, "wt-active", "active-merged")
    other = _add_worktree(repo, tmp_path, "wt-other", "other-merged")
    for path in (active, other):
        _set_old(path)

    state_root = tmp_path / "state"
    result = worktree_prune.apply_prune(
        active,
        extra_roots=[],
        age_hours=72,
        state_root=state_root,
    )
    entries = _by_path(result)

    assert entries[active.resolve()].verdict == "REPORT_ONLY"
    assert entries[active.resolve()].reason == "active-worktree"
    assert entries[active.resolve()].removed is False
    assert active.exists()
    assert entries[other.resolve()].verdict == "PRUNABLE"
    assert entries[other.resolve()].removed is True
    assert not other.exists()
    audit_lines = (state_root / worktree_prune.AUDIT_FILENAME).read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    assert json.loads(audit_lines[0])["path"] == str(other.resolve())


def test_apply_protects_cwd_worktree_when_repo_root_points_elsewhere(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path)
    scan_root = _add_worktree(repo, tmp_path, "wt-scan-root", "scan-root-merged")
    cwd_worktree = _add_worktree(repo, tmp_path, "wt-cwd", "cwd-merged")
    other = _add_worktree(repo, tmp_path, "wt-other", "other-merged")
    nested_cwd = cwd_worktree / "nested"
    nested_cwd.mkdir()
    for path in (scan_root, cwd_worktree, other):
        _set_old(path)
    monkeypatch.chdir(nested_cwd)

    state_root = tmp_path / "state"
    result = worktree_prune.apply_prune(
        scan_root,
        extra_roots=[],
        age_hours=72,
        state_root=state_root,
    )
    entries = _by_path(result)

    assert entries[scan_root.resolve()].verdict == "REPORT_ONLY"
    assert entries[scan_root.resolve()].reason == "active-worktree"
    assert scan_root.exists()
    assert entries[cwd_worktree.resolve()].verdict == "REPORT_ONLY"
    assert entries[cwd_worktree.resolve()].reason == "active-worktree"
    assert entries[cwd_worktree.resolve()].removed is False
    assert cwd_worktree.exists()
    assert entries[other.resolve()].verdict == "PRUNABLE"
    assert entries[other.resolve()].removed is True
    assert not other.exists()


def test_scan_classifies_diverged_empty_tip_content_as_prunable(tmp_path: Path):
    repo = _make_repo(tmp_path)
    empty_tip = _add_worktree(repo, tmp_path, "wt-empty-tip", "empty-tip")
    _git(empty_tip, "commit", "--allow-empty", "-m", "empty branch tip")
    _git(repo, "commit", "--allow-empty", "-m", "empty main tip")
    _git(repo, "push", "origin", "main")
    _git(empty_tip, "fetch", "origin", "main")
    _set_old(empty_tip)

    result = worktree_prune.scan_worktrees(repo, extra_roots=[], age_hours=72)
    entry = _by_path(result)[empty_tip.resolve()]

    assert entry.verdict == "PRUNABLE"
    assert entry.reason == "empty-tip-content"
    assert entry.evidence["head_ancestor_origin_main"] is False
    assert entry.evidence["empty_tip_content_vs_origin_main"] is True


def test_scan_keeps_diverged_non_empty_tip_content_report_only(tmp_path: Path):
    repo = _make_repo(tmp_path)
    non_empty = _add_worktree(repo, tmp_path, "wt-non-empty-tip", "non-empty-tip")
    (non_empty / "feature.txt").write_text("branch content\n", encoding="utf-8")
    _git(non_empty, "add", "feature.txt")
    _git(non_empty, "commit", "-m", "non-empty branch tip")
    _git(repo, "commit", "--allow-empty", "-m", "empty main tip")
    _git(repo, "push", "origin", "main")
    _git(non_empty, "fetch", "origin", "main")
    _set_old(non_empty)

    result = worktree_prune.scan_worktrees(repo, extra_roots=[], age_hours=72)
    entry = _by_path(result)[non_empty.resolve()]

    assert entry.verdict == "REPORT_ONLY"
    assert entry.reason == "not-on-origin"
    assert entry.evidence["head_ancestor_origin_main"] is False
    assert entry.evidence["empty_tip_content_vs_origin_main"] is False


def test_scan_prunes_main_ancestor_tip(tmp_path: Path):
    repo = _make_repo(tmp_path)
    merged = _add_worktree(repo, tmp_path, "wt-main-ancestor", "main-ancestor")
    _set_old(merged)

    result = worktree_prune.scan_worktrees(repo, extra_roots=[], age_hours=72)
    entry = _by_path(result)[merged.resolve()]

    assert entry.verdict == "PRUNABLE"
    assert entry.reason == "merged"
    assert entry.evidence["head_ancestor_origin_main"] is True


def test_scan_prunes_tip_reachable_only_from_non_main_origin_ref(tmp_path: Path):
    repo = _make_repo(tmp_path)
    archived = _add_worktree(repo, tmp_path, "wt-origin-archive", "origin-archive")
    (archived / "archive.txt").write_text("durably archived\n", encoding="utf-8")
    _git(archived, "add", "archive.txt")
    _git(archived, "commit", "-m", "archived tip")
    _git(archived, "push", "origin", "HEAD:refs/heads/archive/seat-scratch/test-tip")
    _git(
        archived,
        "fetch",
        "origin",
        "refs/heads/archive/seat-scratch/test-tip:refs/remotes/origin/archive/seat-scratch/test-tip",
    )
    _set_old(archived)

    result = worktree_prune.scan_worktrees(repo, extra_roots=[], age_hours=72)
    entry = _by_path(result)[archived.resolve()]

    assert entry.verdict == "PRUNABLE"
    assert entry.reason == "reachable-on-origin"
    assert entry.evidence["head_ancestor_origin_main"] is False
    assert entry.evidence["origin_reachable_ref"] == (
        "refs/remotes/origin/archive/seat-scratch/test-tip"
    )


def test_scan_refuses_tip_not_reachable_from_any_origin_ref(tmp_path: Path):
    repo = _make_repo(tmp_path)
    local_only = _add_worktree(repo, tmp_path, "wt-local-only", "local-only")
    (local_only / "local-only.txt").write_text("not archived\n", encoding="utf-8")
    _git(local_only, "add", "local-only.txt")
    _git(local_only, "commit", "-m", "local-only tip")
    _set_old(local_only)

    result = worktree_prune.scan_worktrees(repo, extra_roots=[], age_hours=72)
    entry = _by_path(result)[local_only.resolve()]

    assert entry.verdict == "REPORT_ONLY"
    assert entry.reason == "not-on-origin"
    assert "origin_reachable_ref" not in entry.evidence


def test_scan_refuses_when_origin_ref_reachability_probe_fails(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path)
    local_only = _add_worktree(repo, tmp_path, "wt-probe-failure", "probe-failure")
    (local_only / "local-only.txt").write_text("not archived\n", encoding="utf-8")
    _git(local_only, "add", "local-only.txt")
    _git(local_only, "commit", "-m", "local-only tip")
    _set_old(local_only)

    original_run_git = worktree_prune._run_git

    def failed_ref_list(path: Path, args):
        if args[:1] == ["for-each-ref"]:
            return worktree_prune.GitResult(2, "", "simulated ref-list failure")
        return original_run_git(path, args)

    monkeypatch.setattr(worktree_prune, "_run_git", failed_ref_list)

    result = worktree_prune.scan_worktrees(repo, extra_roots=[], age_hours=72)
    entry = _by_path(result)[local_only.resolve()]

    assert entry.verdict == "REPORT_ONLY"
    assert entry.reason == "unknown-state"
    assert entry.evidence["origin_ref_list_returncode"] == 2
    assert entry.evidence["origin_ref_list_stderr"] == "simulated ref-list failure"


def test_scan_reports_locked_registered_worktree_explicitly(tmp_path: Path):
    repo = _make_repo(tmp_path)
    locked = _add_worktree(repo, tmp_path, "wt-locked", "locked-merged")
    _git(repo, "worktree", "lock", "--reason", "in use", str(locked))
    _set_old(locked)

    result = worktree_prune.scan_worktrees(repo, extra_roots=[], age_hours=72)
    entry = _by_path(result)[locked.resolve()]

    assert entry.verdict == "REPORT_ONLY"
    assert entry.reason == "locked"
    assert entry.evidence["locked"] is True
    assert entry.evidence["lock_reason"] == "in use"


def test_cli_worktree_prune_json_dry_run(tmp_path: Path, monkeypatch, capsys):
    repo = _make_repo(tmp_path)
    clean = _add_worktree(repo, tmp_path, "wt-clean", "clean-merged")
    _set_old(clean)
    monkeypatch.chdir(repo)

    rc = ce_cli.main([
        "worker",
        "worktree-prune",
        "--no-default-extra-root",
        "--age-hours",
        "72",
        "--json",
    ])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    by_path = {entry["path"]: entry for entry in payload["entries"]}
    assert by_path[str(clean.resolve())]["verdict"] == "PRUNABLE"
    assert by_path[str(clean.resolve())]["reason"] == "merged"
    assert payload["summary"]["removed"] == 0
