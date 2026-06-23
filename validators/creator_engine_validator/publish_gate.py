"""Host-side substrate publish gate for contained CE seats.

Contained seats author and commit inside the sandbox, but they do not receive
push credentials. This module is the host-side chokepoint: verify a committed
branch, apply a fail-closed policy, push through host git credentials, then
record the publish to the Side-Effect Ledger.
"""
from __future__ import annotations

import os
import re
import subprocess
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from . import side_effect_ledger_runtime

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_UNSAFE_REF_CHARS = re.compile(r"[\000-\037\177 ~^:?*\\[]")
_GH_CREDENTIAL_ARGS = ("-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential")

GitRunner = Callable[[Sequence[str], str | None, dict[str, str]], subprocess.CompletedProcess]


@dataclass(frozen=True)
class SeatIdentityExpectation:
    author_name: str | None = None
    author_email: str | None = None
    committer_name: str | None = None
    committer_email: str | None = None

    @property
    def empty(self) -> bool:
        return not any((self.author_name, self.author_email, self.committer_name, self.committer_email))

    def to_dict(self) -> dict[str, str | None]:
        return {
            "author_name": self.author_name,
            "author_email": self.author_email,
            "committer_name": self.committer_name,
            "committer_email": self.committer_email,
        }


@dataclass(frozen=True)
class CommitIdentity:
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
class PublishLedgerContext:
    controller_id: str
    lane_id: str
    claim_ref: str
    repo_root: str | Path
    side_effect_ledger_root: str | Path
    active_work_ledger_root: str | Path
    actor: str
    seat_id: str
    actor_role: str = "controller"
    now: datetime | None = None


@dataclass(frozen=True)
class PublishPolicyRequest:
    repo: str
    branch: str
    local_head: str
    remote_head: str | None
    attribution: str
    actor: str
    seat_id: str
    force: bool
    fast_forward: bool | None
    phase: str


@dataclass(frozen=True)
class PublishPolicyVerdict:
    allowed: bool
    reason: str | None = None
    policy_name: str = "default_publish_policy"


class PublishPolicy(Protocol):
    def evaluate(self, request: PublishPolicyRequest) -> PublishPolicyVerdict:
        """Return a policy verdict for one host publish request."""


@dataclass(frozen=True)
class DefaultPublishPolicy:
    policy_name: str = "default_publish_policy"

    def evaluate(self, request: PublishPolicyRequest) -> PublishPolicyVerdict:
        if request.force:
            return PublishPolicyVerdict(False, "force_push_refused", self.policy_name)
        if not request.actor.strip() or not request.seat_id.strip() or not request.attribution.strip():
            return PublishPolicyVerdict(False, "missing_publish_attribution", self.policy_name)
        if request.fast_forward is False:
            return PublishPolicyVerdict(False, "non_fast_forward", self.policy_name)
        return PublishPolicyVerdict(True, None, self.policy_name)


@dataclass(frozen=True)
class PublishBranchResult:
    repo: str
    branch: str
    remote_url: str | None
    local_head: str | None
    remote_head: str | None
    expected_identity: SeatIdentityExpectation
    observed_identity: CommitIdentity | None
    policy_verdict: str
    policy_name: str
    verified: bool
    changed: bool
    up_to_date: bool
    applied: bool
    pushed: bool
    ledger_record_path: str | None
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
            "observed_identity": self.observed_identity.to_dict() if self.observed_identity else None,
            "policy_verdict": self.policy_verdict,
            "policy_name": self.policy_name,
            "verified": self.verified,
            "changed": self.changed,
            "up_to_date": self.up_to_date,
            "applied": self.applied,
            "pushed": self.pushed,
            "ledger_record_path": self.ledger_record_path,
            "refusal_reason": self.refusal_reason,
            "evidence": list(self.evidence),
        }


def default_git_runner(
    argv: Sequence[str], input_text: str | None, env: dict[str, str]
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv),
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def publish_branch(
    branch: str,
    *,
    repo: str | None = None,
    repo_root: str | Path = ".",
    expected_identity: SeatIdentityExpectation,
    ledger_context: PublishLedgerContext | None = None,
    apply: bool = True,
    force: bool = False,
    policy: PublishPolicy | None = None,
    runner: GitRunner | None = None,
) -> PublishBranchResult:
    """Verify and optionally publish ``branch`` through host-side git credentials."""

    runner = runner or default_git_runner
    repo_root = Path(repo_root)
    branch = (branch or "").strip()
    repo_value = (repo or "").strip()
    remote_url: str | None = None
    local_head: str | None = None
    remote_head: str | None = None
    observed: CommitIdentity | None = None
    policy_name = getattr(policy or DefaultPublishPolicy(), "policy_name", "publish_policy")

    def refused(reason: str, *evidence: str, pushed: bool = False) -> PublishBranchResult:
        return PublishBranchResult(
            repo=repo_value,
            branch=branch,
            remote_url=remote_url,
            local_head=local_head,
            remote_head=remote_head,
            expected_identity=expected_identity,
            observed_identity=observed,
            policy_verdict="deny",
            policy_name=policy_name,
            verified=False,
            changed=False,
            up_to_date=False,
            applied=False,
            pushed=pushed,
            ledger_record_path=None,
            refusal_reason=reason,
            evidence=tuple(str(item) for item in evidence),
        )

    bad_branch = _branch_refusal(branch)
    if bad_branch:
        return refused("malformed_branch", bad_branch)
    if force:
        return refused("force_push_refused", "publish gate never accepts force")
    if expected_identity.empty:
        return refused("missing_identity_expectation", "expected seat commit identity is required")
    if apply and ledger_context is None:
        return refused("missing_ledger_context", "live publish requires side-effect ledger context")

    if not repo_value:
        repo_value = _repo_from_origin(runner, repo_root) or ""
    if not _REPO_RE.match(repo_value):
        return refused("malformed_repo", f"repo={repo_value!r} is not owner/name")
    remote_url = f"https://github.com/{repo_value}"

    local_head = _git_stdout(runner, repo_root, ["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"])
    if not local_head:
        return refused("missing_local_branch", f"refs/heads/{branch} not found")
    local_head = local_head.lower()
    if not _valid_sha(local_head):
        return refused("ambiguous_local_head", f"local_head={local_head!r} is not a git SHA")

    current_head = _git_stdout(runner, repo_root, ["rev-parse", "--verify", "HEAD"])
    if not _valid_sha(current_head or ""):
        return refused("ambiguous_head", "could not resolve current HEAD")
    if current_head.lower() != local_head:
        return refused("head_not_local_branch", f"HEAD={current_head}", f"branch_head={local_head}")

    status = _git_stdout(runner, repo_root, ["status", "--porcelain"])
    if status is None:
        return refused("ambiguous_worktree", "could not read worktree status")
    if status.strip():
        return refused("dirty_worktree", "worktree has uncommitted changes")

    observed = _commit_identity(runner, repo_root, local_head)
    if observed is None:
        return refused("ambiguous_commit_identity", f"could not read commit identity for {local_head}")
    mismatches = _identity_mismatches(expected_identity, observed)
    if mismatches:
        return refused("head_identity_mismatch", *mismatches)

    remote_head = _ls_remote(runner, repo_root, remote_url, branch)
    if remote_head == "":
        return refused("remote_read_failed", f"could not read refs/heads/{branch}")
    if remote_head is not None:
        remote_head = remote_head.lower()
        if not _valid_sha(remote_head):
            return refused("ambiguous_remote_head", f"remote_head={remote_head!r} is not a git SHA")
    fast_forward = None if remote_head is None or remote_head == local_head else _is_ancestor(
        runner, repo_root, remote_head, local_head
    )

    attribution = _attribution(observed)
    verdict = _evaluate_policy(
        policy or DefaultPublishPolicy(),
        PublishPolicyRequest(
            repo=repo_value,
            branch=branch,
            local_head=local_head,
            remote_head=remote_head,
            attribution=attribution,
            actor=ledger_context.actor if ledger_context else "host-substrate",
            seat_id=ledger_context.seat_id if ledger_context else "unknown-seat",
            force=force,
            fast_forward=fast_forward,
            phase="final",
        ),
    )
    policy_name = verdict.policy_name
    if not verdict.allowed:
        return refused(verdict.reason or "policy_refused")

    if remote_head == local_head:
        return PublishBranchResult(
            repo=repo_value,
            branch=branch,
            remote_url=remote_url,
            local_head=local_head,
            remote_head=remote_head,
            expected_identity=expected_identity,
            observed_identity=observed,
            policy_verdict="allow",
            policy_name=policy_name,
            verified=True,
            changed=False,
            up_to_date=True,
            applied=apply,
            pushed=False,
            ledger_record_path=None,
            refusal_reason=None,
            evidence=("remote already equals local head",),
        )

    if not apply:
        return PublishBranchResult(
            repo=repo_value,
            branch=branch,
            remote_url=remote_url,
            local_head=local_head,
            remote_head=remote_head,
            expected_identity=expected_identity,
            observed_identity=observed,
            policy_verdict="allow",
            policy_name=policy_name,
            verified=True,
            changed=True,
            up_to_date=False,
            applied=False,
            pushed=False,
            ledger_record_path=None,
            refusal_reason=None,
            evidence=("publish verification passed", "dry_run=true"),
        )

    push_error = _push(runner, repo_root, remote_url, branch)
    if push_error:
        reason = "remote_moved_before_push" if "non-fast-forward" in push_error else "push_failed"
        return refused(reason, push_error)

    post_push_remote = _ls_remote(runner, repo_root, remote_url, branch)
    if post_push_remote is None or post_push_remote.lower() != local_head:
        return refused(
            "post_push_verification_failed",
            f"expected_remote_head={local_head}",
            f"actual_remote_head={post_push_remote}",
            pushed=True,
        )

    record_path = _record_publish(
        context=ledger_context,
        repo=repo_value,
        branch=branch,
        sha=local_head,
        attribution=attribution,
        policy_name=policy_name,
        remote_head_before=remote_head,
    )
    return PublishBranchResult(
        repo=repo_value,
        branch=branch,
        remote_url=remote_url,
        local_head=local_head,
        remote_head=post_push_remote.lower(),
        expected_identity=expected_identity,
        observed_identity=observed,
        policy_verdict="allow",
        policy_name=policy_name,
        verified=True,
        changed=True,
        up_to_date=False,
        applied=True,
        pushed=True,
        ledger_record_path=str(record_path) if record_path else None,
        refusal_reason=None,
        evidence=("publish verification passed", "push=fast_forward_or_create"),
    )


def _branch_refusal(branch: str) -> str | None:
    if not branch or branch.startswith("-"):
        return "branch must be non-empty and must not start with '-'"
    if branch.startswith("/") or branch.endswith("/") or "//" in branch:
        return "branch must be a relative ref path without empty components"
    if branch.endswith(".") or branch.endswith(".lock") or branch == "@" or "@{" in branch or ".." in branch:
        return "branch contains forbidden ref syntax"
    if _UNSAFE_REF_CHARS.search(branch):
        return "branch contains unsafe ref characters"
    if any(part.startswith(".") or part.endswith(".lock") for part in branch.split("/")):
        return "branch contains an unsafe ref path component"
    return None


def _repo_from_origin(runner: GitRunner, repo_root: Path) -> str | None:
    remote = _git_stdout(runner, repo_root, ["remote", "get-url", "origin"])
    if not remote:
        return None
    for pattern in (
        r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
        r"^https?://[^/]*github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$",
    ):
        match = re.search(pattern, remote.strip())
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return None


def _commit_identity(runner: GitRunner, repo_root: Path, commit: str) -> CommitIdentity | None:
    out = _git_stdout(runner, repo_root, ["show", "-s", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce", commit])
    if out is None:
        return None
    parts = out.split("\x00")
    if len(parts) != 5 or not _valid_sha(parts[0]):
        return None
    return CommitIdentity(parts[0].lower(), parts[1], parts[2], parts[3], parts[4])


def _identity_mismatches(expected: SeatIdentityExpectation, observed: CommitIdentity) -> tuple[str, ...]:
    mismatches: list[str] = []
    for field in ("author_name", "author_email", "committer_name", "committer_email"):
        expected_value = getattr(expected, field)
        if expected_value is not None and expected_value != getattr(observed, field):
            mismatches.append(f"{field}: expected {expected_value!r}, observed {getattr(observed, field)!r}")
    return tuple(mismatches)


def _ls_remote(runner: GitRunner, repo_root: Path, remote_url: str, branch: str) -> str | None:
    proc = _run_git(runner, repo_root, ["ls-remote", remote_url, f"refs/heads/{branch}"])
    if proc.returncode != 0:
        return ""
    text = (proc.stdout or "").strip()
    if not text:
        return None
    return text.split()[0]


def _is_ancestor(runner: GitRunner, repo_root: Path, ancestor: str, descendant: str) -> bool:
    proc = _run_git(runner, repo_root, ["merge-base", "--is-ancestor", ancestor, descendant])
    return proc.returncode == 0


def _push(runner: GitRunner, repo_root: Path, remote_url: str, branch: str) -> str | None:
    proc = _run_git(
        runner,
        repo_root,
        [*_GH_CREDENTIAL_ARGS, "push", remote_url, f"refs/heads/{branch}:refs/heads/{branch}"],
    )
    if proc.returncode == 0:
        return None
    return _redact(proc.stderr or proc.stdout or "unknown git push failure")


def _git_stdout(runner: GitRunner, repo_root: Path, args: Sequence[str]) -> str | None:
    proc = _run_git(runner, repo_root, args)
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip()


def _run_git(runner: GitRunner, repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    return runner(["git", "-C", str(repo_root), *args], None, env)


def _evaluate_policy(policy: PublishPolicy, request: PublishPolicyRequest) -> PublishPolicyVerdict:
    try:
        verdict = policy.evaluate(request)
    except Exception as exc:  # pragma: no cover - defensive policy boundary
        return PublishPolicyVerdict(False, f"policy_error:{type(exc).__name__}", "publish_policy")
    if not isinstance(verdict, PublishPolicyVerdict):
        return PublishPolicyVerdict(False, "malformed_policy_verdict", "publish_policy")
    if verdict.allowed and verdict.reason:
        return PublishPolicyVerdict(False, "allow_verdict_carried_refusal_reason", verdict.policy_name)
    if not verdict.allowed and not verdict.reason:
        return PublishPolicyVerdict(False, "missing_refusal_reason", verdict.policy_name)
    return verdict


def _record_publish(
    *,
    context: PublishLedgerContext | None,
    repo: str,
    branch: str,
    sha: str,
    attribution: str,
    policy_name: str,
    remote_head_before: str | None,
) -> Path | None:
    if context is None:
        return None
    result = side_effect_ledger_runtime.record(
        controller_id=context.controller_id,
        lane_id=context.lane_id,
        claim_ref=context.claim_ref,
        effect_id=f"publish-{uuid.uuid4().hex[:16]}",
        effect_kind="git_mutation",
        effect_status="succeeded",
        summary=f"Published {branch} through host substrate publish gate.",
        occurred_at=_utc_now_str(context.now),
        repo_root=context.repo_root,
        side_effect_ledger_root=context.side_effect_ledger_root,
        active_work_ledger_root=context.active_work_ledger_root,
        actor_role=context.actor_role,
        subject_ref=f"refs/heads/{branch}",
        subject_git_sha=sha,
        details={
            "event": "host_substrate_publish_gate",
            "repo": repo,
            "branch": branch,
            "actor": context.actor,
            "seat": context.seat_id,
            "attribution": attribution,
            "policy_name": policy_name,
            "policy_verdict": "allow",
            "remote_head_before": remote_head_before[:12] if remote_head_before else None,
            "sandbox_auth_env_required": False,
            "sandbox_auth_mount_required": False,
        },
        now=context.now,
    )
    return result.record_path


def _attribution(identity: CommitIdentity) -> str:
    return f"author={identity.author_name} <{identity.author_email}>; committer={identity.committer_name} <{identity.committer_email}>"


def _utc_now_str(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_sha(value: str) -> bool:
    return bool(_SHA_RE.fullmatch((value or "").strip()))


def _redact(value: str) -> str:
    return re.sub(r"(gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)", "<redacted>", value)
