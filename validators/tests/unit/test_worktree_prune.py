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
    assert entries[unpushed.resolve()].reason == "unpushed-commits"
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
