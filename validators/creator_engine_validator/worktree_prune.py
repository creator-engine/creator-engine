"""Fail-safe stale git worktree pruning.

The runtime is deliberately conservative: a worktree is removable only when it
is clean, old, and either already merged to ``origin/main`` or has no content
delta against ``origin/main...HEAD``. Broken orphan directories are removable
only when their payload is empty apart from the broken ``.git`` pointer.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

DEFAULT_EXTRA_ROOT = Path("/var/tmp")
DEFAULT_AGE_HOURS = 72.0
AUDIT_FILENAME = "worktree-prune.jsonl"


class WorktreePruneError(RuntimeError):
    """Raised when the scanner cannot run from the requested repository."""


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class WorktreeCandidate:
    path: Path
    kind: str
    branch: str | None = None
    head: str | None = None
    gitdir: Path | None = None
    primary: bool = False
    registered: bool = False


@dataclass
class WorktreeVerdict:
    path: Path
    branch: str | None
    tip_sha: str | None
    kind: str
    verdict: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    removed: bool = False
    removal_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "branch": self.branch,
            "tip_sha": self.tip_sha,
            "kind": self.kind,
            "verdict": self.verdict,
            "reason": self.reason,
            "evidence": self.evidence,
            "removed": self.removed,
            "removal_error": self.removal_error,
        }


@dataclass
class WorktreePruneResult:
    repo_root: Path
    age_hours: float
    applied: bool
    entries: list[WorktreeVerdict]
    audit_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_root": str(self.repo_root),
            "age_hours": self.age_hours,
            "applied": self.applied,
            "audit_path": str(self.audit_path) if self.audit_path else None,
            "entries": [entry.to_dict() for entry in self.entries],
            "summary": {
                "total": len(self.entries),
                "prunable": sum(1 for entry in self.entries if entry.verdict == "PRUNABLE"),
                "removed": sum(1 for entry in self.entries if entry.removed),
                "errors": sum(1 for entry in self.entries if entry.removal_error),
            },
        }


def _run_git(repo: Path, args: Sequence[str]) -> GitResult:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return GitResult(completed.returncode, completed.stdout, completed.stderr)


def _resolve_repo_root(repo_root: Path | str) -> Path:
    repo = Path(repo_root).resolve()
    result = _run_git(repo, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise WorktreePruneError(result.stderr.strip() or f"not a git repository: {repo}")
    return Path(result.stdout.strip()).resolve()


def _parse_worktree_porcelain(text: str) -> list[WorktreeCandidate]:
    candidates: list[WorktreeCandidate] = []
    current: dict[str, Any] = {}

    def flush() -> None:
        if "worktree" not in current:
            current.clear()
            return
        branch = current.get("branch")
        if isinstance(branch, str) and branch.startswith("refs/heads/"):
            branch = branch.removeprefix("refs/heads/")
        candidate = WorktreeCandidate(
            path=Path(current["worktree"]).resolve(),
            kind="registered",
            branch=branch,
            head=current.get("HEAD"),
            primary=len(candidates) == 0,
            registered=True,
        )
        candidates.append(candidate)
        current.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        if not line:
            flush()
            continue
        key, _, value = line.partition(" ")
        current[key] = value if value else True
    flush()
    return candidates


def discover_registered_worktrees(repo_root: Path | str) -> list[WorktreeCandidate]:
    repo = _resolve_repo_root(repo_root)
    result = _run_git(repo, ["worktree", "list", "--porcelain"])
    if result.returncode != 0:
        raise WorktreePruneError(result.stderr.strip() or "git worktree list failed")
    return _parse_worktree_porcelain(result.stdout)


def _gitdir_from_file(git_file: Path) -> Path | None:
    try:
        text = git_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    prefix = "gitdir:"
    if not text.lower().startswith(prefix):
        return None
    raw = text[len(prefix):].strip()
    target = Path(raw)
    if not target.is_absolute():
        target = (git_file.parent / target).resolve()
    return target


def discover_orphan_dirs(extra_roots: Sequence[Path | str]) -> list[WorktreeCandidate]:
    candidates: list[WorktreeCandidate] = []
    seen: set[Path] = set()
    for root_like in extra_roots:
        root = Path(root_like)
        if not root.exists() or not root.is_dir():
            continue
        for current, dirnames, filenames in os.walk(root):
            current_path = Path(current)
            dirnames[:] = [
                name
                for name in dirnames
                if name not in {".git", ".hg", ".svn", "__pycache__", "node_modules"}
            ]
            if ".git" not in filenames:
                continue
            git_file = current_path / ".git"
            gitdir = _gitdir_from_file(git_file)
            if gitdir is None or gitdir.exists():
                continue
            resolved = current_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(
                WorktreeCandidate(
                    path=resolved,
                    kind="orphan",
                    gitdir=gitdir,
                    registered=False,
                )
            )
            dirnames[:] = []
    return candidates


def discover_worktrees(
    repo_root: Path | str,
    extra_roots: Sequence[Path | str] = (DEFAULT_EXTRA_ROOT,),
) -> list[WorktreeCandidate]:
    registered = discover_registered_worktrees(repo_root)
    seen = {candidate.path for candidate in registered}
    discovered = list(registered)
    for candidate in discover_orphan_dirs(extra_roots):
        if candidate.path not in seen:
            discovered.append(candidate)
            seen.add(candidate.path)
    return discovered


def _newest_mtime(path: Path) -> float | None:
    if not path.exists():
        return None
    newest = path.stat().st_mtime
    for current, dirnames, filenames in os.walk(path):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        current_path = Path(current)
        try:
            newest = max(newest, current_path.stat().st_mtime)
        except OSError:
            continue
        for name in filenames:
            file_path = current_path / name
            try:
                newest = max(newest, file_path.stat().st_mtime)
            except OSError:
                continue
    return newest


def _age_evidence(path: Path, age_hours: float, now: float | None) -> tuple[bool, dict[str, Any]]:
    newest = _newest_mtime(path)
    if newest is None:
        return False, {"exists": False}
    now_ts = datetime.now(timezone.utc).timestamp() if now is None else now
    observed_age_hours = max(0.0, (now_ts - newest) / 3600.0)
    return observed_age_hours >= age_hours, {
        "newest_mtime": datetime.fromtimestamp(newest, tz=timezone.utc).isoformat(),
        "age_hours": round(observed_age_hours, 3),
        "age_threshold_hours": age_hours,
    }


def _status_clean(path: Path) -> tuple[bool, dict[str, Any], str | None]:
    result = _run_git(path, ["status", "--porcelain", "--untracked-files=all"])
    evidence = {
        "status_returncode": result.returncode,
        "status_entries": [line for line in result.stdout.splitlines() if line],
    }
    if result.returncode != 0:
        evidence["status_stderr"] = result.stderr.strip()
        return False, evidence, "unknown-state"
    if evidence["status_entries"]:
        return False, evidence, "dirty"
    return True, evidence, None


def _head_safety(path: Path) -> tuple[bool, dict[str, Any], str | None]:
    head = _run_git(path, ["rev-parse", "HEAD"])
    evidence: dict[str, Any] = {"head_returncode": head.returncode}
    if head.returncode != 0:
        evidence["head_stderr"] = head.stderr.strip()
        return False, evidence, "unknown-state"
    evidence["tip_sha"] = head.stdout.strip()

    origin = _run_git(path, ["rev-parse", "--verify", "origin/main"])
    evidence["origin_main_returncode"] = origin.returncode
    if origin.returncode != 0:
        evidence["origin_main_stderr"] = origin.stderr.strip()
        return False, evidence, "unknown-state"
    evidence["origin_main_sha"] = origin.stdout.strip()

    ancestor = _run_git(path, ["merge-base", "--is-ancestor", "HEAD", "origin/main"])
    evidence["head_ancestor_origin_main"] = ancestor.returncode == 0
    evidence["ancestor_returncode"] = ancestor.returncode

    content = _run_git(path, ["diff", "--quiet", "origin/main...HEAD", "--"])
    evidence["empty_tip_content_vs_origin_main"] = content.returncode == 0
    evidence["content_diff_returncode"] = content.returncode
    if content.returncode not in (0, 1):
        evidence["content_diff_stderr"] = content.stderr.strip()
        return False, evidence, "unknown-state"

    if ancestor.returncode == 0 or content.returncode == 0:
        return True, evidence, None
    if ancestor.returncode == 1:
        return False, evidence, "unpushed-commits"

    evidence["ancestor_stderr"] = ancestor.stderr.strip()
    return False, evidence, "unknown-state"


def _orphan_payload_files(path: Path) -> list[str]:
    payload: list[str] = []
    for current, dirnames, filenames in os.walk(path):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        current_path = Path(current)
        for name in filenames:
            file_path = current_path / name
            if file_path == path / ".git":
                continue
            payload.append(str(file_path.relative_to(path)))
    return sorted(payload)


def classify_candidate(
    candidate: WorktreeCandidate,
    *,
    age_hours: float = DEFAULT_AGE_HOURS,
    now: float | None = None,
    active_worktree: Path | None = None,
) -> WorktreeVerdict:
    evidence: dict[str, Any] = {
        "registered": candidate.registered,
        "primary": candidate.primary,
        "active_worktree": str(active_worktree) if active_worktree is not None else None,
    }
    if candidate.gitdir is not None:
        evidence["gitdir"] = str(candidate.gitdir)

    old_enough, age_info = _age_evidence(candidate.path, age_hours, now)
    evidence.update(age_info)
    if not candidate.path.exists():
        return WorktreeVerdict(
            candidate.path, candidate.branch, candidate.head, candidate.kind,
            "REPORT_ONLY", "unknown-state", evidence,
        )
    if active_worktree is not None and candidate.path == active_worktree:
        return WorktreeVerdict(
            candidate.path, candidate.branch, candidate.head, candidate.kind,
            "REPORT_ONLY", "active-worktree", evidence,
        )
    if candidate.primary:
        return WorktreeVerdict(
            candidate.path, candidate.branch, candidate.head, candidate.kind,
            "REPORT_ONLY", "primary-worktree", evidence,
        )
    if not old_enough:
        return WorktreeVerdict(
            candidate.path, candidate.branch, candidate.head, candidate.kind,
            "REPORT_ONLY", "too-new", evidence,
        )

    if candidate.kind == "orphan":
        payload_files = _orphan_payload_files(candidate.path)
        evidence["payload_files"] = payload_files
        evidence["broken_gitdir"] = candidate.gitdir is not None and not candidate.gitdir.exists()
        if payload_files:
            return WorktreeVerdict(
                candidate.path, candidate.branch, candidate.head, candidate.kind,
                "REPORT_ONLY", "unknown-state", evidence,
            )
        return WorktreeVerdict(
            candidate.path, candidate.branch, candidate.head, candidate.kind,
            "PRUNABLE", "orphan-empty", evidence,
        )

    clean, status_evidence, status_reason = _status_clean(candidate.path)
    evidence.update(status_evidence)
    if not clean:
        return WorktreeVerdict(
            candidate.path, candidate.branch, candidate.head, candidate.kind,
            "REPORT_ONLY", status_reason or "unknown-state", evidence,
        )

    safe_head, head_evidence, head_reason = _head_safety(candidate.path)
    evidence.update(head_evidence)
    tip_sha = head_evidence.get("tip_sha") or candidate.head
    if not safe_head:
        return WorktreeVerdict(
            candidate.path, candidate.branch, tip_sha, candidate.kind,
            "REPORT_ONLY", head_reason or "unknown-state", evidence,
        )

    reason = (
        "merged"
        if evidence.get("head_ancestor_origin_main")
        else "empty-tip-content"
    )
    return WorktreeVerdict(
        candidate.path, candidate.branch, tip_sha, candidate.kind,
        "PRUNABLE", reason, evidence,
    )


def scan_worktrees(
    repo_root: Path | str = ".",
    *,
    extra_roots: Sequence[Path | str] = (DEFAULT_EXTRA_ROOT,),
    age_hours: float = DEFAULT_AGE_HOURS,
    now: float | None = None,
) -> WorktreePruneResult:
    repo = _resolve_repo_root(repo_root)
    entries = [
        classify_candidate(candidate, age_hours=age_hours, now=now, active_worktree=repo)
        for candidate in discover_worktrees(repo, extra_roots)
    ]
    entries.sort(key=lambda entry: str(entry.path))
    return WorktreePruneResult(repo_root=repo, age_hours=age_hours, applied=False, entries=entries)


def _surviving_git_context(result: WorktreePruneResult) -> Path:
    if result.repo_root.exists():
        return result.repo_root
    for entry in result.entries:
        if entry.kind == "registered" and entry.verdict != "PRUNABLE" and entry.path.exists():
            return entry.path
    raise WorktreePruneError("no surviving git worktree context for worktree prune")


def _append_audit(state_root: Path, entry: WorktreeVerdict) -> Path:
    state_root.mkdir(parents=True, exist_ok=True)
    audit_path = state_root / AUDIT_FILENAME
    record = {
        "record_type": "worktree_prune_removal",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "path": str(entry.path),
        "branch": entry.branch,
        "tip_sha": entry.tip_sha,
        "kind": entry.kind,
        "verdict": entry.verdict,
        "reason": entry.reason,
        "evidence": entry.evidence,
    }
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return audit_path


def apply_prune(
    repo_root: Path | str = ".",
    *,
    extra_roots: Sequence[Path | str] = (DEFAULT_EXTRA_ROOT,),
    age_hours: float = DEFAULT_AGE_HOURS,
    state_root: Path | str | None = None,
    now: float | None = None,
) -> WorktreePruneResult:
    result = scan_worktrees(repo_root, extra_roots=extra_roots, age_hours=age_hours, now=now)
    result.applied = True
    audit_root = Path(state_root) if state_root is not None else result.repo_root / ".ce" / "state"
    audit_path: Path | None = None
    prune_context = _surviving_git_context(result)
    removed_registered = False

    for entry in result.entries:
        if entry.verdict != "PRUNABLE":
            continue
        try:
            if entry.kind == "registered":
                remove = _run_git(prune_context, ["worktree", "remove", str(entry.path)])
                if remove.returncode != 0:
                    raise WorktreePruneError(remove.stderr.strip() or remove.stdout.strip())
                removed_registered = True
            elif entry.kind == "orphan":
                shutil.rmtree(entry.path)
            else:
                raise WorktreePruneError(f"unsupported candidate kind: {entry.kind}")
        except Exception as exc:  # pragma: no cover - exercised via CLI return path
            entry.removal_error = str(exc)
            continue
        entry.removed = True
        audit_path = _append_audit(audit_root, entry)

    if removed_registered:
        prune = _run_git(prune_context, ["worktree", "prune"])
        if prune.returncode != 0:
            raise WorktreePruneError(prune.stderr.strip() or prune.stdout.strip())

    result.audit_path = audit_path
    return result
