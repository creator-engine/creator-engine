"""Integrator merge-queue belt poller.

This module turns the ce-ops#216 library primitives into a witnessable
controller-side belt:

Search API poll -> repair-needed event -> deterministic resolver -> executor
race guard -> requeue/merge or controller escalation.

It is deliberately poll-based, idempotent, and fail-closed. Live git/GitHub
operations live behind injectable ``gh_runner`` / ``git_spawn`` seams so tests
stay offline.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from base64 import b64decode
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from ._redact import redact_gh_stderr
from .auto_merge import enable_auto_merge
from .change import ChangeRef
from .eviction_detection import RepairNeededEvent, RepairPollResult, Transport
from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner
from .integrator_executor import ExecutorPublishResult, ExecutorRefs
from .integrator_runner import (
    ConflictSnapshot,
    IntegratorRepairAdapter,
    IntegratorRunResult,
    RepairWorkItem,
    run_once,
)
from .merge import merge

GitSpawn = Callable[[Sequence[str], str | None, Mapping[str, str] | None], subprocess.CompletedProcess]
LogSink = Callable[[Mapping[str, Any]], None]

DEFAULT_TOKEN_ENV = "GH_TOKEN"
DEFAULT_WORK_ROOT = ".ce/integrator-belt"
DEFAULT_INTERVAL_SECONDS = 60.0
DEFAULT_DAEMON_SEARCH_LIMIT = 50
DEFAULT_GOVERNANCE_CHECK = "Validate governance artifacts"
DEFAULT_TEST_CHECK_KEYWORDS = ("test", "pytest", "unit")


class IntegratorBeltError(Exception):
    """Bad input or refused live belt action."""


@dataclass(frozen=True)
class BeltPollTick:
    """One witnessable poll-loop tick."""

    index: int
    result: IntegratorRunResult

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "result": self.result.to_dict()}


@dataclass(frozen=True)
class BeltPollLoopResult:
    """Aggregate result for a bounded poll loop."""

    ticks: tuple[BeltPollTick, ...]

    @property
    def executed_count(self) -> int:
        return sum(tick.result.executed_count for tick in self.ticks)

    @property
    def escalated_count(self) -> int:
        return sum(tick.result.escalated_count for tick in self.ticks)

    @property
    def refused_count(self) -> int:
        return sum(tick.result.refused_count for tick in self.ticks)

    @property
    def event_count(self) -> int:
        return sum(len(tick.result.poll.events) for tick in self.ticks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticks": [tick.to_dict() for tick in self.ticks],
            "event_count": self.event_count,
            "executed_count": self.executed_count,
            "escalated_count": self.escalated_count,
            "refused_count": self.refused_count,
        }


@dataclass(frozen=True)
class DaemonStatusCheck:
    """One status-check context observed on a PR head."""

    name: str
    state: str
    kind: str

    @property
    def success(self) -> bool:
        return self.state == "SUCCESS"

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "state": self.state, "kind": self.kind}


@dataclass(frozen=True)
class DaemonPullRequest:
    """Secret-free daemon candidate read from GitHub."""

    repo: str
    pr_number: int
    title: str
    url: str
    head_ref: str
    head_sha: str
    base_ref: str
    review_decision: str | None
    approving_review_commits: tuple[str, ...]
    mergeable: str | None
    merge_state_status: str | None
    rollup_state: str | None
    checks: tuple[DaemonStatusCheck, ...]
    changed_paths: tuple[str, ...]
    files_complete: bool
    checks_complete: bool
    is_draft: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "title": self.title,
            "url": self.url,
            "head_ref": self.head_ref,
            "head_sha": self.head_sha,
            "base_ref": self.base_ref,
            "review_decision": self.review_decision,
            "approving_review_commits": list(self.approving_review_commits),
            "mergeable": self.mergeable,
            "merge_state_status": self.merge_state_status,
            "rollup_state": self.rollup_state,
            "checks": [check.to_dict() for check in self.checks],
            "changed_paths": list(self.changed_paths),
            "files_complete": self.files_complete,
            "checks_complete": self.checks_complete,
            "is_draft": self.is_draft,
        }


@dataclass(frozen=True)
class DaemonDecision:
    """One daemon enqueue/skip/defer decision."""

    status: str
    reason: str
    repo: str
    pr_number: int
    head_sha: str
    path_set: tuple[str, ...] = ()
    path_set_source: str = ""
    overlap_with: str | None = None
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "reason": self.reason,
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "path_set": list(self.path_set),
            "path_set_source": self.path_set_source,
            "evidence": list(self.evidence),
        }
        if self.overlap_with:
            payload["overlap_with"] = self.overlap_with
        return payload


@dataclass(frozen=True)
class DaemonPassResult:
    """Result of one autonomous merge-daemon pass."""

    decisions: tuple[DaemonDecision, ...]
    dry_run: bool

    @property
    def enqueue_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.status == "enqueue")

    @property
    def skip_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.status == "skip")

    @property
    def defer_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.status == "defer")

    @property
    def failed_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.reason == "enqueue_failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "enqueue_count": self.enqueue_count,
            "skip_count": self.skip_count,
            "defer_count": self.defer_count,
            "failed_count": self.failed_count,
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


@dataclass(frozen=True)
class DaemonLoopTick:
    """One supervised daemon loop tick."""

    index: int
    result: DaemonPassResult

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "result": self.result.to_dict()}


@dataclass(frozen=True)
class DaemonLoopResult:
    """Aggregate result for supervised daemon modes."""

    ticks: tuple[DaemonLoopTick, ...]

    @property
    def enqueue_count(self) -> int:
        return sum(tick.result.enqueue_count for tick in self.ticks)

    @property
    def skip_count(self) -> int:
        return sum(tick.result.skip_count for tick in self.ticks)

    @property
    def defer_count(self) -> int:
        return sum(tick.result.defer_count for tick in self.ticks)

    @property
    def failed_count(self) -> int:
        return sum(tick.result.failed_count for tick in self.ticks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticks": [tick.to_dict() for tick in self.ticks],
            "enqueue_count": self.enqueue_count,
            "skip_count": self.skip_count,
            "defer_count": self.defer_count,
            "failed_count": self.failed_count,
        }


@dataclass(frozen=True)
class PullRequestIdentity:
    """Live PR refs needed by the repair adapter and executor race guard."""

    repo: str
    pr_number: int
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str
    head_repo: str


@dataclass(frozen=True)
class LiveActionRequest:
    """Belt-local live-action request. Structurally mirrors the v1 dry-run seam's
    request so the belt's injected runner is duck-typed across the v1/v3 boundary —
    the belt imports no v1 module."""

    action: str
    request: Path
    preview_root: Path
    repo_root: Path | None
    preview_id: str


@dataclass(frozen=True)
class LiveActionResult:
    """Belt-local secret-free live-action result (structurally mirrors the v1 seam)."""

    accepted: bool
    action: str
    refusal_reason: str | None = None
    evidence: tuple[str, ...] = ()


def token_from_env(name: str = DEFAULT_TOKEN_ENV) -> str:
    token = os.environ.get(name, "").strip()
    if not token:
        raise IntegratorBeltError(f"{name} is required for integrator belt polling")
    return token


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - live gh edge
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _default_git_spawn(
    argv: Sequence[str],
    input_text: str | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:  # pragma: no cover - live git edge
    return subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        env=dict(env or os.environ),
        timeout=120,
    )


def gh_runner_with_token(token: str, runner: GhRunner | None = None) -> GhRunner:
    base = runner or _default_gh_runner

    def run(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        old = os.environ.get("GH_TOKEN")
        os.environ["GH_TOKEN"] = token
        try:
            return base(argv, input_text)
        finally:
            if old is None:
                os.environ.pop("GH_TOKEN", None)
            else:
                os.environ["GH_TOKEN"] = old

    return run


def git_env_with_token(token: str) -> dict[str, str]:
    env = dict(os.environ)
    env["GH_TOKEN"] = token
    return env


def _log(log_sink: LogSink | None, action: str, **payload: Any) -> None:
    if log_sink is not None:
        log_sink({"action": action, **payload})


def run_poll_loop(
    *,
    token: str,
    repair_adapter: IntegratorRepairAdapter,
    repo: str | None = None,
    org: str | None = None,
    iterations: int = 1,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    transport: Transport | None = None,
    gh_runner: GhRunner | None = None,
    poller: Callable[..., RepairPollResult] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    detected_at: str | None = None,
    log_sink: LogSink | None = None,
) -> BeltPollLoopResult:
    """Run a bounded, witnessable integrator poll loop."""

    if iterations < 1:
        raise IntegratorBeltError("iterations must be >= 1")
    if interval_seconds < 0:
        raise IntegratorBeltError("interval_seconds must be >= 0")
    if repo and org:
        raise IntegratorBeltError("repo and org are mutually exclusive")
    if not repo and not org:
        # Fail closed: an unscoped poll would build a GitHub search across every
        # approved+green PR the token can see and then publish/requeue/merge them.
        # The belt must act only within an explicit repo or org scope (ce-ops#218 review).
        raise IntegratorBeltError(
            "run_poll_loop refuses an unscoped poll; supply repo or org "
            "(the belt must not act across every PR a token can see)"
        )

    ticks: list[BeltPollTick] = []
    for index in range(1, iterations + 1):
        _log(log_sink, "poll_start", index=index, repo=repo, org=org)
        result = run_once(
            token=token,
            repair_adapter=repair_adapter,
            repo=repo,
            org=org,
            transport=transport,
            gh_runner=gh_runner,
            poller=poller,
            detected_at=detected_at,
        )
        tick = BeltPollTick(index=index, result=result)
        ticks.append(tick)
        _log(
            log_sink,
            "poll_complete",
            index=index,
            event_count=len(result.poll.events),
            executed_count=result.executed_count,
            escalated_count=result.escalated_count,
            refused_count=result.refused_count,
        )
        for outcome in result.outcomes:
            _log(
                log_sink,
                "event_outcome",
                index=index,
                repo=outcome.event.repo,
                pr_number=outcome.event.pr_number,
                status=outcome.status,
                refusal_reason=outcome.refusal_reason,
                escalations=len(outcome.escalation_events),
            )
        if index != iterations and interval_seconds:
            sleep(interval_seconds)
    return BeltPollLoopResult(ticks=tuple(ticks))


def run_daemon_loop(
    *,
    token: str,
    repo: str | None = None,
    org: str | None = None,
    once: bool = True,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    dry_run: bool = False,
    gh_runner: GhRunner | None = None,
    sleep: Callable[[float], None] = time.sleep,
    log_sink: LogSink | None = None,
) -> DaemonLoopResult:
    """Run the supervised autonomous merge daemon.

    ``once=True`` performs a single pass. ``once=False`` loops until interrupted
    by the caller/process supervisor.
    """

    if interval_seconds < 0:
        raise IntegratorBeltError("interval_seconds must be >= 0")
    runner = gh_runner_with_token(token, gh_runner)
    ticks: list[DaemonLoopTick] = []
    index = 1
    while True:
        _log(log_sink, "daemon_pass_start", index=index, repo=repo, org=org, dry_run=dry_run)
        result = run_daemon_pass(
            token=token,
            repo=repo,
            org=org,
            dry_run=dry_run,
            gh_runner=runner,
            log_sink=log_sink,
        )
        tick = DaemonLoopTick(index=index, result=result)
        ticks = [tick] if not once else [*ticks, tick]
        _log(
            log_sink,
            "daemon_pass_complete",
            index=index,
            enqueue_count=result.enqueue_count,
            skip_count=result.skip_count,
            defer_count=result.defer_count,
            failed_count=result.failed_count,
        )
        if once:
            break
        if interval_seconds:
            sleep(interval_seconds)
        index += 1
    return DaemonLoopResult(ticks=tuple(ticks))


def run_daemon_pass(
    *,
    token: str,
    repo: str | None = None,
    org: str | None = None,
    dry_run: bool = False,
    gh_runner: GhRunner | None = None,
    log_sink: LogSink | None = None,
    candidates: Sequence[DaemonPullRequest] | None = None,
) -> DaemonPassResult:
    """Discover, evaluate, sequence, and enqueue eligible PRs for merge queue."""

    del token  # auth is carried only by the injected runner environment
    if repo and org:
        raise IntegratorBeltError("repo and org are mutually exclusive")
    if not repo and not org:
        raise IntegratorBeltError("run_daemon_pass refuses an unscoped daemon; supply repo or org")
    runner = gh_runner or _default_gh_runner
    prs = tuple(candidates) if candidates is not None else discover_daemon_candidates(
        repo=repo,
        org=org,
        gh_runner=runner,
    )
    decisions: list[DaemonDecision] = []
    selected_paths: dict[str, set[str]] = {}
    for pr in sorted(prs, key=lambda item: (item.repo, item.pr_number)):
        gate_reason = _daemon_gate_refusal(pr)
        if gate_reason is not None:
            decision = _decision(pr, "skip", gate_reason)
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        path_set, path_source, path_refusal = _daemon_path_set(pr, runner)
        if not path_set:
            decision = _decision(
                pr,
                "skip",
                path_refusal or "carrier_invalid",
                path_set_source=path_source,
            )
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        overlap = _first_overlap(path_set, selected_paths)
        if overlap is not None:
            owner, paths = overlap
            decision = _decision(
                pr,
                "defer",
                "path_overlap",
                path_set=path_set,
                path_set_source=path_source,
                overlap_with=owner,
                evidence=(f"overlap_paths={','.join(sorted(paths))}",),
            )
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        selected_paths[f"{pr.repo}#{pr.pr_number}"] = set(path_set)
        if dry_run:
            decision = _decision(
                pr,
                "enqueue",
                "eligible_dry_run",
                path_set=path_set,
                path_set_source=path_source,
                evidence=("dry_run=true",),
            )
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        enqueue = _enqueue_merge_queue(pr, runner)
        decision = _decision(
            pr,
            "enqueue" if enqueue.returncode == 0 else "skip",
            "eligible_enqueued" if enqueue.returncode == 0 else "enqueue_failed",
            path_set=path_set,
            path_set_source=path_source,
            evidence=(
                "gh_pr_merge_auto=true",
                f"returncode={enqueue.returncode}",
                f"stderr={redact_gh_stderr(enqueue.stderr or '')}",
            ),
        )
        decisions.append(decision)
        _log_daemon_decision(log_sink, decision)
    return DaemonPassResult(decisions=tuple(decisions), dry_run=dry_run)


def discover_daemon_candidates(
    *,
    repo: str | None = None,
    org: str | None = None,
    gh_runner: GhRunner | None = None,
    first: int = DEFAULT_DAEMON_SEARCH_LIMIT,
) -> tuple[DaemonPullRequest, ...]:
    """Read open PR candidates in a repo or org scope."""

    if repo and org:
        raise IntegratorBeltError("repo and org are mutually exclusive")
    if repo:
        _split_repo(repo)
        search = f"repo:{repo} is:pr is:open"
    elif org:
        if not org.strip() or any(ch.isspace() for ch in org):
            raise IntegratorBeltError(f"org scope is malformed: {org!r}")
        search = f"org:{org} is:pr is:open"
    else:
        raise IntegratorBeltError("discover_daemon_candidates refuses an unscoped search")
    if first < 1 or first > 100:
        raise IntegratorBeltError("first must be between 1 and 100")

    runner = gh_runner or _default_gh_runner
    parsed = _gh_graphql(
        runner,
        _DAEMON_SEARCH_QUERY,
        {"searchQuery": search, "first": first},
        purpose="discover daemon PR candidates",
    )
    search_node = ((parsed.get("data") or {}).get("search") or {})
    nodes = search_node.get("nodes")
    if not isinstance(nodes, list):
        raise ForgeConfigError("unexpected daemon candidate response")
    if ((search_node.get("pageInfo") or {}).get("hasNextPage")) is True:
        raise ForgeConfigError(
            "daemon candidate search returned more than one page; narrow --repo/--org scope"
        )
    out: list[DaemonPullRequest] = []
    for node in nodes:
        if isinstance(node, dict):
            out.append(_parse_daemon_pr(node))
    return tuple(out)


_DAEMON_SEARCH_QUERY = (
    "query($searchQuery:String!,$first:Int!){"
    "search(type:ISSUE,query:$searchQuery,first:$first){pageInfo{hasNextPage endCursor}nodes{"
    "... on PullRequest{"
    "number title url isDraft reviewDecision mergeable mergeStateStatus headRefName headRefOid baseRefName "
    "repository{nameWithOwner} "
    "latestReviews(first:20){nodes{state commit{oid}}} "
    "commits(last:1){nodes{commit{oid statusCheckRollup{state contexts(first:100){"
    "pageInfo{hasNextPage} nodes{__typename "
    "... on CheckRun{name conclusion status} "
    "... on StatusContext{context state}"
    "}}}}}} "
    "files(first:100){pageInfo{hasNextPage}nodes{path}}"
    "}}}}"
)


def _parse_daemon_pr(node: Mapping[str, Any]) -> DaemonPullRequest:
    repo = str((node.get("repository") or {}).get("nameWithOwner") or "")
    number = node.get("number")
    if not repo or not isinstance(number, int):
        raise ForgeConfigError("daemon candidate missing repo or number")
    head_sha = _required_str(node, "headRefOid")
    commit = _latest_commit_node(node)
    rollup = (commit.get("statusCheckRollup") or {}) if isinstance(commit, dict) else {}
    contexts = ((rollup.get("contexts") or {}) if isinstance(rollup, dict) else {})
    checks = tuple(_parse_status_check(raw) for raw in contexts.get("nodes") or ())
    files = (node.get("files") or {}) if isinstance(node.get("files"), dict) else {}
    reviews = (node.get("latestReviews") or {}) if isinstance(node.get("latestReviews"), dict) else {}
    approving = tuple(
        str(((review.get("commit") or {}).get("oid") or "")).lower()
        for review in reviews.get("nodes") or ()
        if isinstance(review, dict)
        and review.get("state") == "APPROVED"
        and ((review.get("commit") or {}).get("oid"))
    )
    return DaemonPullRequest(
        repo=repo,
        pr_number=number,
        title=str(node.get("title") or ""),
        url=str(node.get("url") or ""),
        head_ref=_required_str(node, "headRefName"),
        head_sha=head_sha,
        base_ref=_required_str(node, "baseRefName"),
        review_decision=node.get("reviewDecision") if isinstance(node.get("reviewDecision"), str) else None,
        approving_review_commits=approving,
        mergeable=node.get("mergeable") if isinstance(node.get("mergeable"), str) else None,
        merge_state_status=(
            node.get("mergeStateStatus") if isinstance(node.get("mergeStateStatus"), str) else None
        ),
        rollup_state=rollup.get("state") if isinstance(rollup.get("state"), str) else None,
        checks=checks,
        changed_paths=tuple(
            sorted(
                str(item.get("path"))
                for item in files.get("nodes") or ()
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            )
        ),
        files_complete=((files.get("pageInfo") or {}).get("hasNextPage") is not True),
        checks_complete=((contexts.get("pageInfo") or {}).get("hasNextPage") is not True),
        is_draft=bool(node.get("isDraft")),
    )


def _latest_commit_node(node: Mapping[str, Any]) -> Mapping[str, Any]:
    commits = node.get("commits") if isinstance(node.get("commits"), dict) else {}
    nodes = commits.get("nodes") if isinstance(commits, dict) else []
    if not nodes or not isinstance(nodes[0], dict):
        return {}
    commit = nodes[0].get("commit")
    return commit if isinstance(commit, dict) else {}


def _parse_status_check(raw: Any) -> DaemonStatusCheck:
    if not isinstance(raw, dict):
        return DaemonStatusCheck(name="", state="UNKNOWN", kind="unknown")
    kind = str(raw.get("__typename") or "unknown")
    if kind == "CheckRun":
        return DaemonStatusCheck(
            name=str(raw.get("name") or ""),
            state=str(raw.get("conclusion") or raw.get("status") or "UNKNOWN"),
            kind=kind,
        )
    if kind == "StatusContext":
        return DaemonStatusCheck(
            name=str(raw.get("context") or ""),
            state=str(raw.get("state") or "UNKNOWN"),
            kind=kind,
        )
    return DaemonStatusCheck(name=str(raw.get("name") or raw.get("context") or ""), state="UNKNOWN", kind=kind)


def _daemon_gate_refusal(pr: DaemonPullRequest) -> str | None:
    if pr.is_draft:
        return "draft_pr"
    if pr.review_decision != "APPROVED":
        return "review_not_approved"
    if pr.head_sha.lower() not in pr.approving_review_commits:
        return "approval_not_current_head"
    if pr.mergeable != "MERGEABLE":
        return "not_mergeable"
    if not pr.files_complete:
        return "changed_files_incomplete"
    if not pr.checks_complete:
        return "status_checks_incomplete"
    if pr.rollup_state != "SUCCESS":
        return "rollup_not_success"
    governance = _find_check(pr.checks, DEFAULT_GOVERNANCE_CHECK)
    if governance is None:
        return "governance_check_missing"
    if not governance.success:
        return "governance_check_not_success"
    tests = tuple(check for check in pr.checks if _is_test_check(check.name))
    if any(not check.success for check in tests):
        return "test_check_not_success"
    return None


def _find_check(checks: Sequence[DaemonStatusCheck], name: str) -> DaemonStatusCheck | None:
    for check in checks:
        if check.name == name:
            return check
    return None


def _is_test_check(name: str) -> bool:
    lower = name.lower()
    return any(keyword in lower for keyword in DEFAULT_TEST_CHECK_KEYWORDS)


def _daemon_path_set(
    pr: DaemonPullRequest, runner: GhRunner
) -> tuple[tuple[str, ...], str, str | None]:
    from ..checks import path_manifest_fidelity

    expected = (
        f"{path_manifest_fidelity.MANIFEST_DIR}/"
        f"{path_manifest_fidelity.branch_slug(pr.head_ref)}.md"
    )
    if expected not in pr.changed_paths:
        return (), expected, "carrier_missing"
    text = _read_file_at_ref(runner, pr.repo, expected, pr.head_sha)
    if text is None:
        return (), expected, "carrier_unreadable"
    identity = path_manifest_fidelity.parse_carrier(text)
    if identity is None or not identity.consistent or not identity.paths:
        return (), expected, "carrier_invalid"
    return identity.paths, "carrier", None


def _is_carrier_manifest_path(path: str) -> bool:
    return path.startswith(".ce/pr-manifests/") and path.endswith(".md")


def _read_file_at_ref(runner: GhRunner, repo: str, path: str, ref: str) -> str | None:
    quoted_path = quote(path, safe="/")
    proc = runner(
        [
            "gh",
            "api",
            f"/repos/{repo}/contents/{quoted_path}?ref={quote(ref, safe='')}",
            "-H",
            "Accept: application/vnd.github.raw",
        ],
        None,
    )
    if proc.returncode == 0:
        return proc.stdout or ""
    proc = runner(["gh", "api", f"/repos/{repo}/contents/{quoted_path}", "-f", f"ref={ref}"], None)
    if proc.returncode != 0:
        return None
    try:
        parsed = json.loads((proc.stdout or "").strip() or "{}")
    except (TypeError, ValueError):
        return None
    content = parsed.get("content") if isinstance(parsed, dict) else None
    if not isinstance(content, str):
        return None
    try:
        return b64decode(content.encode("ascii"), validate=False).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _first_overlap(
    path_set: Sequence[str], selected_paths: Mapping[str, set[str]]
) -> tuple[str, set[str]] | None:
    current = set(path_set)
    for owner, paths in selected_paths.items():
        overlap = current & paths
        if overlap:
            return owner, overlap
    return None


def _enqueue_merge_queue(pr: DaemonPullRequest, runner: GhRunner) -> subprocess.CompletedProcess:
    return runner(
        [
            "gh",
            "pr",
            "merge",
            str(pr.pr_number),
            "--repo",
            pr.repo,
            "--auto",
            "--match-head-commit",
            pr.head_sha,
        ],
        None,
    )


def _decision(
    pr: DaemonPullRequest,
    status: str,
    reason: str,
    *,
    path_set: Sequence[str] = (),
    path_set_source: str = "",
    overlap_with: str | None = None,
    evidence: Sequence[str] = (),
) -> DaemonDecision:
    return DaemonDecision(
        status=status,
        reason=reason,
        repo=pr.repo,
        pr_number=pr.pr_number,
        head_sha=pr.head_sha,
        path_set=tuple(sorted(set(path_set))),
        path_set_source=path_set_source,
        overlap_with=overlap_with,
        evidence=tuple(evidence),
    )


def _log_daemon_decision(log_sink: LogSink | None, decision: DaemonDecision) -> None:
    _log(log_sink, "daemon_decision", **decision.to_dict())


class LiveGitHubRepairAdapter:
    """Git/GitHub-backed repair adapter for the integrator runner.

    The adapter prepares a disposable workspace for the PR, attempts to merge
    the current base branch into the approved PR head, captures conflict-marker
    files for deterministic resolvers, then lets Unit 3 apply resolved content
    and push/requeue under its race guard.
    """

    def __init__(
        self,
        *,
        work_root: Path | str = DEFAULT_WORK_ROOT,
        publish_action: str = "enqueue",
        gh_runner: GhRunner | None = None,
        git_spawn: GitSpawn | None = None,
        git_env: Mapping[str, str] | None = None,
        log_sink: LogSink | None = None,
    ) -> None:
        if publish_action not in {"enqueue", "land", "merge"}:
            raise IntegratorBeltError(f"unknown publish action {publish_action!r}")
        self.work_root = Path(work_root)
        self.publish_action = publish_action
        self.gh_runner = gh_runner or _default_gh_runner
        self.git_spawn = git_spawn or _default_git_spawn
        self.git_env = dict(git_env or os.environ)
        self.log_sink = log_sink
        self._workspace: Path | None = None
        self._identity: PullRequestIdentity | None = None

    def repair_work_item(self, event: RepairNeededEvent) -> RepairWorkItem:
        identity = self._read_identity(event.repo, event.pr_number)
        if identity.head_repo != identity.repo:
            raise IntegratorBeltError(
                f"refusing fork repair for {identity.repo}#{identity.pr_number}: "
                f"head repo is {identity.head_repo!r}"
            )
        if identity.head_sha.lower() != event.head_sha.lower():
            raise IntegratorBeltError(
                f"PR head moved before repair: event={event.head_sha} live={identity.head_sha}"
            )
        workspace = self._prepare_workspace(identity)
        conflicts = self._attempt_base_merge(identity, workspace)
        self._workspace = workspace
        self._identity = identity
        _log(
            self.log_sink,
            "repair_workspace_ready",
            repo=identity.repo,
            pr_number=identity.pr_number,
            workspace=str(workspace),
            conflicts=len(conflicts),
        )
        return RepairWorkItem(
            expected_base_sha=identity.base_sha,
            conflicts=conflicts,
            executor_adapter=self,
        )

    def current_refs(self, repo: str, pr_number: int) -> ExecutorRefs:
        identity = self._read_identity(repo, pr_number)
        return ExecutorRefs(pr_head_sha=identity.head_sha, base_sha=identity.base_sha)

    def apply_resolved_content(self, repo: str, pr_number: int, files: dict[str, str]) -> tuple[str, ...]:
        workspace = self._require_workspace(repo, pr_number)
        applied: list[str] = []
        for path, content in sorted(files.items()):
            if not _safe_repo_path(path):
                raise IntegratorBeltError(f"refusing unsafe resolved path {path!r}")
            target = workspace / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self._git(workspace, ["add", "--", path], purpose=f"stage {path}")
            applied.append(path)
        if applied:
            self._git(
                workspace,
                ["commit", "--no-gpg-sign", "-m", f"chore: integrate base for PR #{pr_number}"],
                purpose="commit deterministic integrator repair",
            )
        _log(self.log_sink, "resolved_content_applied", repo=repo, pr_number=pr_number, paths=applied)
        return tuple(applied)

    def push_and_requeue(self, repo: str, pr_number: int) -> ExecutorPublishResult:
        workspace = self._require_workspace(repo, pr_number)
        identity = self._identity or self._read_identity(repo, pr_number)
        self._git(
            workspace,
            ["push", "origin", f"HEAD:refs/heads/{identity.head_ref}"],
            purpose="push repaired PR head",
        )
        current = self._read_identity(repo, pr_number)
        change = ChangeRef(
            repo=repo,
            branch=current.head_ref,
            base=current.base_ref,
            pr_number=pr_number,
            head_sha=current.head_sha,
            manifest_paths=(),
            plan_ref="integrator-belt",
            changed=False,
            applied=True,
            verified=True,
        )
        evidence = ["pushed_repair_head=true"]
        if self.publish_action == "merge":
            merged = merge(change, apply=True, gh_runner=self.gh_runner)
            evidence.append(f"merge_applied={merged.applied}")
            evidence.append(f"merged={merged.merged}")
            requeued = bool(merged.merged)
        else:
            queued = enable_auto_merge(change, apply=True, gh_runner=self.gh_runner)
            evidence.append(f"auto_merge_enabled={queued.enabled}")
            evidence.append(f"publish_action={self.publish_action}")
            requeued = bool(queued.enabled)
        _log(self.log_sink, "repair_published", repo=repo, pr_number=pr_number, evidence=evidence)
        return ExecutorPublishResult(pushed=True, requeued=requeued, evidence=tuple(evidence))

    def _read_identity(self, repo: str, pr_number: int) -> PullRequestIdentity:
        owner, name = _split_repo(repo)
        query = (
            "query($owner:String!,$name:String!,$number:Int!)"
            "{repository(owner:$owner,name:$name){pullRequest(number:$number)"
            "{baseRefName baseRefOid headRefName headRefOid headRepository{nameWithOwner}}}}"
        )
        parsed = _gh_graphql(
            self.gh_runner,
            query,
            {"owner": owner, "name": name, "number": pr_number},
            purpose=f"read PR identity for {repo}#{pr_number}",
        )
        pr = ((parsed.get("data") or {}).get("repository") or {}).get("pullRequest")
        if not isinstance(pr, dict):
            raise IntegratorBeltError(f"unexpected PR identity response for {repo}#{pr_number}")
        return PullRequestIdentity(
            repo=repo,
            pr_number=pr_number,
            base_ref=_required_str(pr, "baseRefName"),
            base_sha=_required_str(pr, "baseRefOid"),
            head_ref=_required_str(pr, "headRefName"),
            head_sha=_required_str(pr, "headRefOid"),
            head_repo=str((pr.get("headRepository") or {}).get("nameWithOwner") or ""),
        )

    def _prepare_workspace(self, identity: PullRequestIdentity) -> Path:
        root = self.work_root / _repo_slug(identity.repo) / f"pr-{identity.pr_number}-{identity.head_sha[:12]}"
        if root.exists():
            shutil.rmtree(root)
        root.parent.mkdir(parents=True, exist_ok=True)
        root.mkdir()
        self._git(root, ["init"], purpose="initialize repair workspace")
        self._git(root, ["config", "user.name", "CE Integrator"], purpose="configure git author name")
        self._git(root, ["config", "user.email", "integrator@creator-engine.invalid"], purpose="configure git author email")
        self._git(root, ["config", "credential.helper", ""], purpose="clear inherited git credential helper")
        self._git(
            root,
            ["config", "--add", "credential.helper", "!gh auth git-credential"],
            purpose="configure gh token credential helper",
        )
        self._git(root, ["remote", "add", "origin", f"https://github.com/{identity.repo}.git"], purpose="add origin")
        self._git(
            root,
            ["fetch", "--no-tags", "origin", f"refs/heads/{identity.base_ref}:refs/remotes/origin/{identity.base_ref}"],
            purpose="fetch base branch",
        )
        self._git(
            root,
            ["fetch", "--no-tags", "origin", f"pull/{identity.pr_number}/head:pr-{identity.pr_number}"],
            purpose="fetch PR head",
        )
        self._git(root, ["checkout", f"pr-{identity.pr_number}"], purpose="checkout PR head")
        return root

    def _attempt_base_merge(self, identity: PullRequestIdentity, workspace: Path) -> tuple[ConflictSnapshot, ...]:
        proc = self._git(
            workspace,
            ["merge", "--no-ff", "--no-commit", f"refs/remotes/origin/{identity.base_ref}"],
            purpose="merge base into PR head",
            allow_nonzero=True,
        )
        if proc.returncode == 0:
            return ()
        conflicted = self._git(
            workspace,
            ["diff", "--name-only", "--diff-filter=U"],
            purpose="list conflicted paths",
        ).stdout.splitlines()
        snapshots: list[ConflictSnapshot] = []
        for path in sorted(p for p in conflicted if p.strip()):
            if not _safe_repo_path(path):
                raise IntegratorBeltError(f"refusing unsafe conflicted path {path!r}")
            snapshots.append(
                ConflictSnapshot(path=path, conflicted_text=(workspace / path).read_text(encoding="utf-8"))
            )
        if not snapshots:
            raise IntegratorBeltError(
                "base merge failed but produced no conflicted paths; refusing ambiguous repair"
            )
        return tuple(snapshots)

    def _require_workspace(self, repo: str, pr_number: int) -> Path:
        if self._workspace is None or self._identity is None:
            raise IntegratorBeltError("repair workspace is not prepared")
        if self._identity.repo != repo or self._identity.pr_number != pr_number:
            raise IntegratorBeltError("executor requested a different PR than the prepared repair")
        return self._workspace

    def _git(
        self,
        cwd: Path,
        args: Sequence[str],
        *,
        purpose: str,
        allow_nonzero: bool = False,
    ) -> subprocess.CompletedProcess:
        argv = ["git", "-C", str(cwd), *args]
        _log(self.log_sink, "git", purpose=purpose, argv=_redacted_argv(argv))
        proc = self.git_spawn(argv, None, self.git_env)
        if proc.returncode != 0 and not allow_nonzero:
            raise ForgeConfigError(
                f"git failed while trying to {purpose}: {redact_gh_stderr(proc.stderr or '') or 'unknown error'}"
            )
        return proc


def make_live_action_runner(
    *,
    action: str,
    token: str,
    repo: str | None = None,
    org: str | None = None,
    work_root: Path | str = DEFAULT_WORK_ROOT,
    transport: Transport | None = None,
    gh_runner: GhRunner | None = None,
    git_spawn: GitSpawn | None = None,
    poller: Callable[..., RepairPollResult] | None = None,
    repair_adapter: IntegratorRepairAdapter | None = None,
    log_sink: LogSink | None = None,
):
    """Return a live-action runner. The returned ``run`` is duck-typed: the v1
    dry-run seam injects it and calls it with its own structurally-identical
    ``LiveActionRequest``; the belt itself imports no v1 module."""

    if action not in {"enqueue", "land", "merge"}:
        raise IntegratorBeltError(f"unknown live action {action!r}")

    effective_gh_runner = gh_runner_with_token(token, gh_runner)
    adapter = repair_adapter or LiveGitHubRepairAdapter(
        work_root=work_root,
        publish_action=action,
        gh_runner=effective_gh_runner,
        git_spawn=git_spawn,
        git_env=git_env_with_token(token),
        log_sink=log_sink,
    )

    def run(request: LiveActionRequest) -> LiveActionResult:
        if request.action != action:
            return LiveActionResult(False, request.action, "live_action_mismatch", (f"expected={action}",))
        try:
            result = run_poll_loop(
                token=token,
                repair_adapter=adapter,
                repo=repo,
                org=org,
                iterations=1,
                interval_seconds=0,
                transport=transport,
                gh_runner=effective_gh_runner,
                poller=poller,
                log_sink=log_sink,
        )
        except (ForgeConfigError, ForgeConfigRefused, IntegratorBeltError) as exc:
            return LiveActionResult(False, action, exc.__class__.__name__, (str(exc),))
        except Exception as exc:  # pragma: no cover - defensive fail-closed live seam
            return LiveActionResult(False, action, "unexpected_integrator_belt_error", (str(exc),))
        evidence = (
            f"events={result.event_count}",
            f"executed={result.executed_count}",
            f"escalated={result.escalated_count}",
            f"refused={result.refused_count}",
        )
        accepted = result.escalated_count == 0 and result.refused_count == 0
        reason = None if accepted else "integrator_belt_refused"
        return LiveActionResult(accepted, action, reason, evidence)

    return run


def _gh_graphql(runner: GhRunner, query: str, variables: dict[str, object], *, purpose: str) -> dict:
    argv = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        flag = "-f" if isinstance(value, str) else "-F"
        argv += [flag, f"{key}={value}"]
    proc = runner(argv, None)
    if proc.returncode != 0:
        raise ForgeConfigError(
            f"could not {purpose}: {redact_gh_stderr(proc.stderr or '') or 'unknown error'}"
        )
    try:
        parsed = json.loads((proc.stdout or "").strip() or "{}")
    except (TypeError, ValueError) as exc:
        raise ForgeConfigError(f"could not {purpose}: unparseable JSON response") from exc
    if not isinstance(parsed, dict):
        raise ForgeConfigError(f"could not {purpose}: unexpected JSON response")
    return parsed


def _split_repo(repo: str) -> tuple[str, str]:
    parts = (repo or "").split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise IntegratorBeltError(f"repo must be owner/name, got {repo!r}")
    return parts[0], parts[1]


def _repo_slug(repo: str) -> str:
    return repo.replace("/", "__")


def _required_str(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IntegratorBeltError(f"PR identity response missing {key}")
    return value


def _safe_repo_path(path: str) -> bool:
    pure = PurePosixPath(path)
    return bool(path.strip()) and not pure.is_absolute() and ".." not in pure.parts


def _redacted_argv(argv: Sequence[str]) -> list[str]:
    return [redact_gh_stderr(str(item)) for item in argv]


class JsonLineLogger:
    """Simple witness logger for CLI use."""

    def __init__(self, stream) -> None:
        self.stream = stream

    def __call__(self, payload: Mapping[str, Any]) -> None:
        print(json.dumps(dict(payload), sort_keys=True), file=self.stream)
