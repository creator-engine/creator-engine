"""Host-side substrate branch publish gate.

Contained seats author commits locally; this host-side chokepoint verifies that
one local branch can be published to ``origin`` as a fast-forward-only update,
checks the branch HEAD attribution against a configured seat identity, then
pushes through host git/gh credentials. It never accepts a token argument and
never injects a sandbox credential into the child environment.
"""
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ._redact import redact_gh_stderr
from .change_push import _GH_CREDENTIAL_ARGS, _default_spawn, _https_remote_url, _is_ancestor

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_UNSAFE_REF_CHARS = re.compile(r"[\000-\037\177 ~^:?*\\[]")

GitSpawn = Callable[[Sequence[str], str | None, dict[str, str]], subprocess.CompletedProcess]


class PublishBranchRefused(Exception):
    """A publish request was refused before or instead of a branch push."""

    code = "CE-PUBLISH-BRANCH-REFUSED"


def default_git_runner(
    argv: Sequence[str], input_text: str | None, env: dict[str, str]
) -> subprocess.CompletedProcess:
    """Default live git runner; tests and policy wrappers should inject a fake."""

    return _default_spawn(argv, input_text, env)


@dataclass(frozen=True)
class SeatIdentityExpectation:
    """Minimal configurable seat identity check for the branch HEAD commit."""

    author_name: str | None = None
    author_email: str | None = None
    committer_name: str | None = None
    committer_email: str | None = None

    @property
    def empty(self) -> bool:
        return not any(
            (self.author_name, self.author_email, self.committer_name, self.committer_email)
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "author_name": self.author_name,
            "author_email": self.author_email,
            "committer_name": self.committer_name,
            "committer_email": self.committer_email,
        }


@dataclass(frozen=True)
class CommitIdentity:
    """Observed author/committer identity on a git commit."""

    commit: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str

    def to_dict(self) -> dict[str, str]:
        return {
            "commit": self.commit,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "committer_name": self.committer_name,
            "committer_email": self.committer_email,
        }


@dataclass(frozen=True)
class PublishBranchResult:
    """Secret-free host publish outcome."""

    repo: str
    branch: str
    remote_url: str | None
    local_head: str | None
    remote_head: str | None
    expected_identity: SeatIdentityExpectation
    observed_identity: CommitIdentity | None
    verified: bool
    changed: bool
    up_to_date: bool
    applied: bool
    pushed: bool
    refusal_reason: str | None
    evidence: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.refusal_reason is None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "repo": self.repo,
            "branch": self.branch,
            "remote_url": self.remote_url,
            "local_head": self.local_head,
            "remote_head": self.remote_head,
            "expected_identity": self.expected_identity.to_dict(),
            "observed_identity": (
                self.observed_identity.to_dict() if self.observed_identity is not None else None
            ),
            "verified": self.verified,
            "changed": self.changed,
            "up_to_date": self.up_to_date,
            "applied": self.applied,
            "pushed": self.pushed,
            "refusal_reason": self.refusal_reason,
            "evidence": list(self.evidence),
        }


def publish_branch(
    branch: str,
    *,
    repo: str | None = None,
    source_dir: str = ".",
    expected_identity: SeatIdentityExpectation,
    apply: bool = True,
    spawn: GitSpawn | None = None,
) -> PublishBranchResult:
    """Verify and optionally publish ``branch`` through host-side git credentials.

    ``apply=True`` performs the push after all verification gates pass. With
    ``apply=False`` the function reads local/remote state and returns the would
    publish result without mutating the remote.
    """

    runner = spawn or default_git_runner
    branch = (branch or "").strip()
    repo_value = (repo or "").strip()
    remote_url: str | None = None
    local_head: str | None = None
    remote_head: str | None = None
    observed: CommitIdentity | None = None

    def refused(reason: str, *evidence: str, pushed: bool = False) -> PublishBranchResult:
        return PublishBranchResult(
            repo=repo_value,
            branch=branch,
            remote_url=remote_url,
            local_head=local_head,
            remote_head=remote_head,
            expected_identity=expected_identity,
            observed_identity=observed,
            verified=False,
            changed=False,
            up_to_date=False,
            applied=False,
            pushed=pushed,
            refusal_reason=reason,
            evidence=_evidence(evidence),
        )

    bad_branch = _branch_refusal(branch)
    if bad_branch is not None:
        return refused("malformed_branch", bad_branch)
    if expected_identity.empty:
        return refused(
            "missing_identity_expectation",
            "provide at least one --expect-author-* or --expect-committer-* value",
        )

    if not repo_value:
        repo_value = _repo_from_origin(runner, source_dir) or ""
    if not _REPO_RE.match(repo_value):
        return refused("malformed_repo", f"repo={repo_value!r} is not owner/name")
    remote_url = _https_remote_url(repo_value)

    local_head = _local_branch_head(runner, source_dir, branch)
    if local_head is None:
        return refused("missing_local_branch", f"refs/heads/{branch} not found")
    if not _valid_sha(local_head):
        return refused("ambiguous_local_head", f"local_head={local_head!r} is not a git SHA")

    current_head = _git_stdout(runner, source_dir, ["rev-parse", "--verify", "HEAD"])
    if not _valid_sha(current_head or ""):
        return refused("ambiguous_head", "could not resolve current HEAD")
    if current_head.lower() != local_head.lower():
        return refused(
            "head_not_local_branch",
            f"HEAD={current_head}",
            f"branch_head={local_head}",
        )

    dirty = _git_stdout(runner, source_dir, ["status", "--porcelain"])
    if dirty is None:
        return refused("ambiguous_worktree", "could not read worktree status")
    if dirty.strip():
        return refused("dirty_worktree", "worktree has uncommitted changes")

    observed = _commit_identity(runner, source_dir, local_head)
    if observed is None:
        return refused("ambiguous_commit_identity", f"could not read commit identity for {local_head}")
    identity_mismatches = _identity_mismatches(expected_identity, observed)
    if identity_mismatches:
        return refused("head_identity_mismatch", *identity_mismatches)

    remote_head = _ls_remote(runner, source_dir, remote_url, branch)
    if remote_head == "":
        return refused("remote_read_failed", f"could not read remote ref refs/heads/{branch}")
    if remote_head is not None and not _valid_sha(remote_head):
        return refused("ambiguous_remote_head", f"remote_head={remote_head!r} is not a git SHA")
    if remote_head is not None and remote_head.lower() == local_head.lower():
        return PublishBranchResult(
            repo=repo_value,
            branch=branch,
            remote_url=remote_url,
            local_head=local_head.lower(),
            remote_head=remote_head.lower(),
            expected_identity=expected_identity,
            observed_identity=observed,
            verified=True,
            changed=False,
            up_to_date=True,
            applied=apply,
            pushed=False,
            refusal_reason=None,
            evidence=("remote already equals local head",),
        )
    if remote_head is not None and not _is_ancestor(runner, source_dir, remote_head, local_head):
        return refused(
            "non_fast_forward",
            f"remote_head={remote_head.lower()} is not an ancestor of local_head={local_head.lower()}",
        )

    if not apply:
        return PublishBranchResult(
            repo=repo_value,
            branch=branch,
            remote_url=remote_url,
            local_head=local_head.lower(),
            remote_head=remote_head.lower() if remote_head else None,
            expected_identity=expected_identity,
            observed_identity=observed,
            verified=True,
            changed=True,
            up_to_date=False,
            applied=False,
            pushed=False,
            refusal_reason=None,
            evidence=("publish verification passed", "dry_run=true"),
        )

    push_error = _push(runner, source_dir, remote_url, branch)
    if push_error is not None:
        reason = "remote_moved_before_push" if "non-fast-forward" in push_error else "push_failed"
        return refused(reason, push_error)

    post_push_remote = _ls_remote(runner, source_dir, remote_url, branch)
    if post_push_remote is None or post_push_remote.lower() != local_head.lower():
        return refused(
            "post_push_verification_failed",
            f"expected_remote_head={local_head.lower()}",
            f"actual_remote_head={post_push_remote}",
            pushed=True,
        )

    return PublishBranchResult(
        repo=repo_value,
        branch=branch,
        remote_url=remote_url,
        local_head=local_head.lower(),
        remote_head=post_push_remote.lower(),
        expected_identity=expected_identity,
        observed_identity=observed,
        verified=True,
        changed=True,
        up_to_date=False,
        applied=True,
        pushed=True,
        refusal_reason=None,
        evidence=("publish verification passed", "push=fast_forward_or_create"),
    )


def _repo_from_origin(spawn: GitSpawn, source_dir: str) -> str | None:
    remote = _git_stdout(spawn, source_dir, ["remote", "get-url", "origin"])
    if not remote:
        return None
    remote = remote.strip()
    patterns = (
        r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
        r"^https?://[^/]*github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.search(pattern, remote)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return None


def _branch_refusal(branch: str) -> str | None:
    if not branch:
        return "branch must be non-empty"
    if branch.startswith("-"):
        return "branch must not start with '-'"
    if branch.startswith("/") or branch.endswith("/") or "//" in branch:
        return "branch must be a relative ref path without empty components"
    if branch.endswith(".") or branch.endswith(".lock"):
        return "branch must not end with '.' or '.lock'"
    if branch == "@" or "@{" in branch or ".." in branch:
        return "branch contains forbidden ref syntax"
    if _UNSAFE_REF_CHARS.search(branch):
        return "branch contains unsafe ref characters"
    if any(part.startswith(".") or part.endswith(".lock") for part in branch.split("/")):
        return "branch contains an unsafe ref path component"
    return None


def _local_branch_head(spawn: GitSpawn, source_dir: str, branch: str) -> str | None:
    return _git_stdout(
        spawn,
        source_dir,
        ["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
    )


def _commit_identity(spawn: GitSpawn, source_dir: str, commit: str) -> CommitIdentity | None:
    out = _git_stdout(
        spawn,
        source_dir,
        ["show", "-s", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce", commit],
    )
    if out is None:
        return None
    parts = out.split("\x00")
    if len(parts) != 5 or not _valid_sha(parts[0]):
        return None
    return CommitIdentity(
        commit=parts[0].lower(),
        author_name=parts[1],
        author_email=parts[2],
        committer_name=parts[3],
        committer_email=parts[4],
    )


def _identity_mismatches(
    expected: SeatIdentityExpectation, observed: CommitIdentity
) -> tuple[str, ...]:
    mismatches: list[str] = []
    for field in ("author_name", "committer_name"):
        exp = getattr(expected, field)
        if exp is not None and exp != getattr(observed, field):
            mismatches.append(f"{field}: expected={exp!r} actual={getattr(observed, field)!r}")
    for field in ("author_email", "committer_email"):
        exp = getattr(expected, field)
        actual = getattr(observed, field)
        if exp is not None and exp.lower() != actual.lower():
            mismatches.append(f"{field}: expected={exp!r} actual={actual!r}")
    return tuple(mismatches)


def _ls_remote(spawn: GitSpawn, source_dir: str, url: str, branch: str) -> str | None:
    proc = spawn(
        ["git", "-C", str(source_dir), *_GH_CREDENTIAL_ARGS, "ls-remote", url, f"refs/heads/{branch}"],
        None,
        _host_git_env(),
    )
    if getattr(proc, "returncode", 1) != 0:
        return ""
    out = (getattr(proc, "stdout", "") or "").strip()
    if not out:
        return None
    lines = [line for line in out.splitlines() if line.strip()]
    if len(lines) != 1:
        return "ambiguous"
    return lines[0].split("\t", 1)[0].split()[0].strip() or "ambiguous"


def _push(spawn: GitSpawn, source_dir: str, url: str, branch: str) -> str | None:
    proc = spawn(
        [
            "git",
            "-C",
            str(source_dir),
            *_GH_CREDENTIAL_ARGS,
            "push",
            url,
            f"refs/heads/{branch}:refs/heads/{branch}",
        ],
        None,
        _host_git_env(),
    )
    if getattr(proc, "returncode", 1) == 0:
        return None
    return redact_gh_stderr(getattr(proc, "stderr", "") or "") or "unknown push error"


def _git_stdout(spawn: GitSpawn, source_dir: str, args: Sequence[str]) -> str | None:
    proc = spawn(["git", "-C", str(source_dir), *args], None, _host_git_env())
    if getattr(proc, "returncode", 1) != 0:
        return None
    return (getattr(proc, "stdout", "") or "").strip()


def _host_git_env() -> dict[str, str]:
    """Return the host child environment without adding credential values."""

    return dict(os.environ)


def _valid_sha(value: str) -> bool:
    return bool(_SHA_RE.fullmatch((value or "").strip()))


def _evidence(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(redact_gh_stderr(str(item)) for item in items)
