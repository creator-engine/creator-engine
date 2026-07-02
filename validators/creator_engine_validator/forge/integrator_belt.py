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

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from base64 import b64decode
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from ..pickup_payload_schema import (
    AuditSink as ConveyorDiscoveryAuditSink,
    ConveyorDiscoveryPayload,
    validate_discovery_payload,
)
from ._redact import redact_gh_stderr
from .approval_capability import (
    APPROVAL_WALL_ARMED,
    APPROVAL_WALL_DORMANT,
    APPROVAL_WALL_MISCONFIGURED,
    ApprovalCapabilityVerifier,
    ApprovalWallRuntime,
    MARKER_PREFIX,
    extract_approval_capability_marker,
)
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
from .search_rate_limiter import (
    SearchRateLimiter,
    call_with_search_api_headroom,
    default_search_rate_limiter,
)

GitSpawn = Callable[[Sequence[str], str | None, Mapping[str, str] | None], subprocess.CompletedProcess]
LogSink = Callable[[Mapping[str, Any]], None]

DEFAULT_TOKEN_ENV = "GH_TOKEN"
DEFAULT_WORK_ROOT = ".ce/integrator-belt"
DEFAULT_INTERVAL_SECONDS = 60.0
DEFAULT_DAEMON_SEARCH_LIMIT = 50
DEFAULT_GOVERNANCE_CHECK = "Validate governance artifacts"
DEFAULT_TEST_CHECK_KEYWORDS = ("test", "pytest", "unit")
DEFAULT_APPROVAL_SETTLE_SECONDS = 0.0
DEFAULT_SWEEP_REPO = "creator-engine/creator-engine"
DEFAULT_QUEUE_BRANCH = "main"
DEFAULT_SWEEP_FIRST = 100


class IntegratorBeltError(Exception):
    """Bad input or refused live belt action."""


class SearchApiRateLimited(ForgeConfigError):
    """GitHub GraphQL search exhausted rate-limit retries."""

    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


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
    latest_at: str | None = None

    @property
    def success(self) -> bool:
        return self.state == "SUCCESS"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "state": self.state, "kind": self.kind}
        if self.latest_at:
            payload["latest_at"] = self.latest_at
        return payload


@dataclass(frozen=True)
class DaemonApprovalWitness:
    """One current approval signal observed for a PR head."""

    reviewer_login: str
    commit_oid: str
    state: str = "APPROVED"
    review_id: str = ""

    @property
    def approved(self) -> bool:
        return self.state == "APPROVED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer_login": self.reviewer_login,
            "commit_oid": self.commit_oid,
            "state": self.state,
            "review_id": self.review_id,
        }


@dataclass(frozen=True)
class DaemonPullRequest:
    """Secret-free daemon candidate read from GitHub."""

    repo: str
    pr_number: int
    title: str
    url: str
    body: str
    head_ref: str
    head_sha: str
    base_ref: str
    review_decision: str | None
    approving_review_commits: tuple[str, ...]
    approving_reviewers: tuple[str, ...]
    approval_capability_present: bool
    approval_capability_marker: str | None
    mergeable: str | None
    merge_state_status: str | None
    rollup_state: str | None
    checks: tuple[DaemonStatusCheck, ...]
    changed_paths: tuple[str, ...]
    files_complete: bool
    checks_complete: bool
    is_draft: bool
    approval_witnesses: tuple[DaemonApprovalWitness, ...] = ()

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
            "approving_reviewers": list(self.approving_reviewers),
            "approval_capability_present": self.approval_capability_present,
            "mergeable": self.mergeable,
            "merge_state_status": self.merge_state_status,
            "rollup_state": self.rollup_state,
            "checks": [check.to_dict() for check in self.checks],
            "changed_paths": list(self.changed_paths),
            "files_complete": self.files_complete,
            "checks_complete": self.checks_complete,
            "is_draft": self.is_draft,
            "approval_witnesses": [witness.to_dict() for witness in self.approval_witnesses],
        }


ApprovalMarkerIssuer = Callable[[DaemonPullRequest, DaemonApprovalWitness], str]
PrBodyUpdater = Callable[[DaemonPullRequest, str], subprocess.CompletedProcess]


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
class DaemonGateEvaluation:
    """Gate outcome before path-set sequencing."""

    refusal_reason: str | None = None
    evidence: tuple[str, ...] = ()


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
class StrandedPullRequest:
    """One open PR plus the author needed for independent-approval checks."""

    pr: DaemonPullRequest
    author_login: str


@dataclass(frozen=True)
class StrandedSweepDecision:
    """One conveyor stranded-sweep enqueue/skip decision."""

    status: str
    reason: str
    repo: str
    pr_number: int
    head_sha: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class StrandedSweepResult:
    """Result of one conveyor stranded-PR sweep."""

    decisions: tuple[StrandedSweepDecision, ...]
    dry_run: bool

    @property
    def enqueue_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.status == "enqueue")

    @property
    def skip_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.status == "skip")

    @property
    def failed_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.reason == "enqueue_failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "enqueue_count": self.enqueue_count,
            "skip_count": self.skip_count,
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


@dataclass(frozen=True)
class MergeQueueDequeueResult:
    """Secret-free result for the emergency merge-queue dequeue primitive."""

    repo: str
    pr_number: int
    disabled_auto_merge: bool
    converted_to_draft: bool
    evidence: tuple[str, ...] = ()
    queued: bool = False
    dequeued: bool = False

    @property
    def ok(self) -> bool:
        return (self.dequeued or not self.queued) and all(
            not item.startswith("draft_returncode=") or item == "draft_returncode=0"
            for item in self.evidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "disabled_auto_merge": self.disabled_auto_merge,
            "converted_to_draft": self.converted_to_draft,
            "queued": self.queued,
            "dequeued": self.dequeued,
            "evidence": list(self.evidence),
        }


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


def parse_conveyor_discovery_payload(
    payload: Mapping[str, Any],
    *,
    audit_sink: ConveyorDiscoveryAuditSink | None = None,
) -> ConveyorDiscoveryPayload:
    """Validate an ADR-0004 conveyor discovery payload before daemon dispatch."""

    return validate_discovery_payload(payload, audit_sink=audit_sink, source="integrator_belt")


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
    rate_limiter: SearchRateLimiter | None = None,
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
    _rate_limiter = rate_limiter
    if _rate_limiter is None and poller is None and transport is None:
        _rate_limiter = default_search_rate_limiter()
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
            rate_limiter=_rate_limiter,
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
    approval_verifier: ApprovalCapabilityVerifier | None = None,
    approval_wall: ApprovalWallRuntime | None = None,
    sleep: Callable[[float], None] = time.sleep,
    log_sink: LogSink | None = None,
    rate_limiter: SearchRateLimiter | None = None,
    authorized_reviewers: Sequence[str] | None = None,
    approval_marker_issuer: ApprovalMarkerIssuer | None = None,
    pr_body_updater: PrBodyUpdater | None = None,
    approval_settle_seconds: float = DEFAULT_APPROVAL_SETTLE_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> DaemonLoopResult:
    """Run the supervised autonomous merge daemon.

    ``once=True`` performs a single pass. ``once=False`` loops until interrupted
    by the caller/process supervisor.
    """

    if interval_seconds < 0:
        raise IntegratorBeltError("interval_seconds must be >= 0")
    if approval_settle_seconds < 0:
        raise IntegratorBeltError("approval_settle_seconds must be >= 0")
    runner = gh_runner_with_token(token, gh_runner)
    _rate_limiter = rate_limiter
    if _rate_limiter is None and gh_runner is None:
        _rate_limiter = default_search_rate_limiter()
    ticks: list[DaemonLoopTick] = []
    approval_settle_seen: set[str] = set()
    approval_settle_ready_at: dict[str, float] = {}
    index = 1
    while True:
        _log(log_sink, "daemon_pass_start", index=index, repo=repo, org=org, dry_run=dry_run)
        try:
            result = run_daemon_pass(
                token=token,
                repo=repo,
                org=org,
                dry_run=dry_run,
                gh_runner=runner,
                approval_verifier=approval_verifier,
                approval_wall=approval_wall,
                log_sink=log_sink,
                rate_limiter=_rate_limiter,
                sleep=sleep,
                approval_settle_seen=approval_settle_seen,
                approval_settle_ready_at=approval_settle_ready_at,
                approval_settle_seconds=approval_settle_seconds,
                clock=clock,
                authorized_reviewers=authorized_reviewers,
                approval_marker_issuer=approval_marker_issuer,
                pr_body_updater=pr_body_updater,
            )
        except SearchApiRateLimited as exc:
            _log(
                log_sink,
                "daemon_rate_limited",
                index=index,
                retry_after_seconds=exc.retry_after_seconds,
                dry_run=dry_run,
            )
            result = DaemonPassResult(decisions=(), dry_run=dry_run)
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
    approval_verifier: ApprovalCapabilityVerifier | None = None,
    approval_wall: ApprovalWallRuntime | None = None,
    log_sink: LogSink | None = None,
    candidates: Sequence[DaemonPullRequest] | None = None,
    rate_limiter: SearchRateLimiter | None = None,
    sleep: Callable[[float], None] = time.sleep,
    approval_settle_seen: set[str] | None = None,
    approval_settle_ready_at: dict[str, float] | None = None,
    approval_settle_seconds: float = DEFAULT_APPROVAL_SETTLE_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    authorized_reviewers: Sequence[str] | None = None,
    approval_marker_issuer: ApprovalMarkerIssuer | None = None,
    pr_body_updater: PrBodyUpdater | None = None,
) -> DaemonPassResult:
    """Discover, evaluate, sequence, and enqueue eligible PRs for merge queue."""

    del token  # auth is carried only by the injected runner environment
    if repo and org:
        raise IntegratorBeltError("repo and org are mutually exclusive")
    if not repo and not org:
        raise IntegratorBeltError("run_daemon_pass refuses an unscoped daemon; supply repo or org")
    if approval_settle_seconds < 0:
        raise IntegratorBeltError("approval_settle_seconds must be >= 0")
    runner = gh_runner or _default_gh_runner
    settle_seen = approval_settle_seen if approval_settle_seen is not None else set()
    settle_ready_at = approval_settle_ready_at if approval_settle_ready_at is not None else {}
    authorized = _normalize_authorized_reviewers(authorized_reviewers)
    prs = tuple(candidates) if candidates is not None else discover_daemon_candidates(
        repo=repo,
        org=org,
        gh_runner=runner,
        rate_limiter=rate_limiter,
        sleep=sleep,
    )
    decisions: list[DaemonDecision] = []
    selected_paths: dict[str, set[str]] = {}
    for pr in sorted(prs, key=lambda item: (item.repo, item.pr_number)):
        gate = _daemon_gate_evaluation(
            pr,
            approval_verifier=approval_verifier,
            approval_wall=approval_wall,
        )
        mint_needed = _approval_marker_mint_needed(
            gate,
            approval_verifier,
            approval_wall,
            approval_marker_issuer,
        )
        if mint_needed:
            non_wall_gate = _daemon_non_wall_gate(pr)
            if non_wall_gate.refusal_reason is not None:
                gate = non_wall_gate
                mint_needed = False
            else:
                gate = DaemonGateEvaluation(None, non_wall_gate.evidence)
        if gate.refusal_reason is not None:
            _clear_approval_settle_for_pr(settle_seen, pr, settle_ready_at)
            decision = _decision(pr, "skip", gate.refusal_reason, evidence=gate.evidence)
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        approval_witness = _current_approval_witness(pr)
        if approval_witness is None:
            decision = _decision(pr, "skip", "approval_reviewer_unconfirmed")
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        approval_key = _approval_settle_key(pr, approval_witness)
        if approval_key not in settle_seen:
            settle_seen.add(approval_key)
            if approval_settle_seconds:
                settle_ready_at[approval_key] = clock() + approval_settle_seconds
            decision = _decision(
                pr,
                "defer",
                "approval_settle_pending",
                evidence=(
                    f"reviewer={approval_witness.reviewer_login}",
                    f"head_sha={pr.head_sha}",
                ),
            )
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        ready_at = settle_ready_at.get(approval_key)
        if ready_at is not None:
            now = clock()
            remaining = max(ready_at - now, 0.0)
            if remaining:
                sleep(remaining)
                now = clock()
            if now < ready_at:
                decision = _decision(
                    pr,
                    "defer",
                    "approval_settle_pending",
                    evidence=(
                        f"reviewer={approval_witness.reviewer_login}",
                        f"head_sha={pr.head_sha}",
                        f"settle_remaining_seconds={ready_at - now:.3f}",
                    ),
                )
                decisions.append(decision)
                _log_daemon_decision(log_sink, decision)
                continue
            settle_ready_at.pop(approval_key, None)
        authorized_witness, authorization_refusal = _authorized_approval_witness(pr, authorized)
        if authorized_witness is None:
            decision = _decision(
                pr,
                "skip",
                authorization_refusal,
                evidence=(f"reviewer={approval_witness.reviewer_login}",),
            )
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        approval_witness = authorized_witness
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
            if mint_needed:
                decision = _decision(
                    pr,
                    "defer",
                    "approval_capability_mint_dry_run",
                    path_set=path_set,
                    path_set_source=path_source,
                    evidence=(
                        *gate.evidence,
                        "dry_run=true",
                        f"reviewer={approval_witness.reviewer_login}",
                    ),
                )
                decisions.append(decision)
                _log_daemon_decision(log_sink, decision)
                continue
            decision = _decision(
                pr,
                "enqueue",
                "eligible_dry_run",
                path_set=path_set,
                path_set_source=path_source,
                evidence=(*gate.evidence, "dry_run=true"),
            )
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        reverified, reverify_reason, reverify_evidence = _reverify_approval_before_enqueue(
            pr, runner, approval_witness
        )
        if not reverified:
            decision = _decision(
                pr,
                "skip",
                reverify_reason,
                path_set=path_set,
                path_set_source=path_source,
                evidence=reverify_evidence,
            )
            decisions.append(decision)
            _log_daemon_decision(log_sink, decision)
            continue
        if mint_needed:
            minted, mint_reason, mint_evidence = _mint_approval_marker_before_enqueue(
                pr,
                runner,
                approval_witness,
                issuer=approval_marker_issuer,
                body_updater=pr_body_updater,
            )
            decision = _decision(
                pr,
                "defer" if minted else "skip",
                mint_reason,
                path_set=path_set,
                path_set_source=path_source,
                evidence=(*gate.evidence, *reverify_evidence, *mint_evidence),
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
                *gate.evidence,
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
    rate_limiter: SearchRateLimiter | None = None,
    sleep: Callable[[float], None] = time.sleep,
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
    operation = lambda: _gh_graphql(
        runner,
        _DAEMON_SEARCH_QUERY,
        {"searchQuery": search, "first": first},
        purpose="discover daemon PR candidates",
    )
    if rate_limiter is not None:
        parsed = call_with_search_api_headroom(
            operation,
            limiter=rate_limiter,
            is_rate_limited=lambda exc: isinstance(exc, SearchApiRateLimited),
            retry_after_seconds=lambda exc: (
                exc.retry_after_seconds if isinstance(exc, SearchApiRateLimited) else None
            ),
            sleep=sleep,
        )
    else:
        parsed = operation()
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


def run_stranded_sweep(
    *,
    repo: str = DEFAULT_SWEEP_REPO,
    queue_branch: str = DEFAULT_QUEUE_BRANCH,
    dry_run: bool = False,
    gh_runner: GhRunner | None = None,
    log_sink: LogSink | None = None,
    candidates: Sequence[StrandedPullRequest] | None = None,
    queued: set[tuple[str, int]] | None = None,
) -> StrandedSweepResult:
    """Enqueue approved+green open PRs that are not already in the merge queue."""

    _split_repo(repo)
    if not queue_branch.strip():
        raise IntegratorBeltError("queue_branch is required")
    runner = gh_runner or _default_gh_runner
    if candidates is None or queued is None:
        discovered_candidates, discovered_queued = discover_stranded_candidates(
            repo=repo,
            queue_branch=queue_branch,
            gh_runner=runner,
        )
        if candidates is None:
            candidates = discovered_candidates
        if queued is None:
            queued = discovered_queued

    decisions: list[StrandedSweepDecision] = []
    _log(log_sink, "stranded_sweep_start", repo=repo, queue_branch=queue_branch, dry_run=dry_run)
    for candidate in sorted(candidates, key=lambda item: (item.pr.repo, item.pr.pr_number)):
        decision = _sweep_candidate(candidate, queued, runner, dry_run=dry_run)
        decisions.append(decision)
        _log(log_sink, "stranded_sweep_decision", **decision.to_dict())
    result = StrandedSweepResult(decisions=tuple(decisions), dry_run=dry_run)
    _log(
        log_sink,
        "stranded_sweep_complete",
        enqueue_count=result.enqueue_count,
        skip_count=result.skip_count,
        failed_count=result.failed_count,
    )
    return result


def discover_stranded_candidates(
    *,
    repo: str = DEFAULT_SWEEP_REPO,
    queue_branch: str = DEFAULT_QUEUE_BRANCH,
    gh_runner: GhRunner | None = None,
    first: int = DEFAULT_SWEEP_FIRST,
) -> tuple[tuple[StrandedPullRequest, ...], set[tuple[str, int]]]:
    """Read open PRs and current merge-queue membership in one GraphQL call."""

    owner, name = _split_repo(repo)
    if first < 1 or first > 100:
        raise IntegratorBeltError("first must be between 1 and 100")
    if queue_branch != DEFAULT_QUEUE_BRANCH:
        raise IntegratorBeltError("only the main merge queue is supported by this sweep")
    runner = gh_runner or _default_gh_runner
    parsed = _gh_graphql(
        runner,
        _STRANDED_SWEEP_QUERY,
        {"owner": owner, "name": name, "first": first},
        purpose=f"discover stranded PRs for {repo}",
    )
    repository = ((parsed.get("data") or {}).get("repository") or {})
    if not isinstance(repository, Mapping):
        raise ForgeConfigError(f"unexpected stranded sweep response for {repo}")
    return _parse_sweep_repository(repository)


_DAEMON_SEARCH_QUERY = (
    "query($searchQuery:String!,$first:Int!){"
    "search(type:ISSUE,query:$searchQuery,first:$first){pageInfo{hasNextPage endCursor}nodes{"
    "... on PullRequest{"
    "number title url body isDraft reviewDecision mergeable mergeStateStatus headRefName headRefOid baseRefName "
    "repository{nameWithOwner} "
    "latestOpinionatedReviews(first:20){nodes{id state author{login} commit{oid}}} "
    "commits(last:1){nodes{commit{oid statusCheckRollup{state contexts(first:100){"
    "pageInfo{hasNextPage} nodes{__typename "
    "... on CheckRun{name conclusion status completedAt startedAt} "
    "... on StatusContext{context state updatedAt createdAt}"
    "}}}}}} "
    "files(first:100){pageInfo{hasNextPage}nodes{path}}"
    "}}}}"
)


# Exact queued-membership query used by the sweep:
# repository(owner:$owner,name:$name){mergeQueue{entries(first:100,branch:"main"){...}}}
_STRANDED_SWEEP_QUERY = (
    "query($owner:String!,$name:String!,$first:Int!){"
    "repository(owner:$owner,name:$name){"
    "mergeQueue{entries(first:100,branch:\"main\"){pageInfo{hasNextPage}nodes{"
    "pullRequest{number repository{nameWithOwner}}"
    "}}} "
    "pullRequests(first:$first,states:OPEN,orderBy:{field:UPDATED_AT,direction:DESC}){"
    "pageInfo{hasNextPage endCursor}nodes{"
    "number title url body isDraft reviewDecision mergeable mergeStateStatus headRefName headRefOid baseRefName "
    "author{login} repository{nameWithOwner} "
    "latestOpinionatedReviews(first:20){nodes{id state author{login} commit{oid}}} "
    "commits(last:1){nodes{commit{oid statusCheckRollup{state contexts(first:100){"
    "pageInfo{hasNextPage} nodes{__typename "
    "... on CheckRun{name conclusion status completedAt startedAt} "
    "... on StatusContext{context state updatedAt createdAt}"
    "}}}}}} "
    "files(first:100){pageInfo{hasNextPage}nodes{path}}"
    "}}"
    "}}"
    "}"
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
    # GitHub's ``latestReviews`` is EMPTY for reviewers who were never formally
    # *requested* (e.g. a controller running ``gh pr review --approve``); the
    # approval + its commit oid live in ``latestOpinionatedReviews`` instead.
    reviews = (
        (node.get("latestOpinionatedReviews") or {})
        if isinstance(node.get("latestOpinionatedReviews"), dict)
        else {}
    )
    approval_witnesses = _parse_approval_witnesses(reviews)
    approving = tuple(
        witness.commit_oid.lower()
        for witness in approval_witnesses
        if witness.approved and witness.commit_oid
    )
    approving_reviewers = tuple(
        sorted(
            {
                str((review.get("author") or {}).get("login") or "")
                for review in reviews.get("nodes") or ()
                if isinstance(review, dict)
                and review.get("state") == "APPROVED"
                and ((review.get("author") or {}).get("login"))
            }
        )
    )
    body = str(node.get("body") or "")
    approval_marker = extract_approval_capability_marker(body)
    return DaemonPullRequest(
        repo=repo,
        pr_number=number,
        title=str(node.get("title") or ""),
        url=str(node.get("url") or ""),
        body=body,
        head_ref=_required_str(node, "headRefName"),
        head_sha=head_sha,
        base_ref=_required_str(node, "baseRefName"),
        review_decision=node.get("reviewDecision") if isinstance(node.get("reviewDecision"), str) else None,
        approving_review_commits=approving,
        approving_reviewers=approving_reviewers,
        approval_capability_present=approval_marker is not None,
        approval_capability_marker=approval_marker,
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
        approval_witnesses=approval_witnesses,
    )


def _sweep_candidate(
    candidate: StrandedPullRequest,
    queued: set[tuple[str, int]],
    runner: GhRunner,
    *,
    dry_run: bool,
) -> StrandedSweepDecision:
    pr = candidate.pr
    queued_key = (pr.repo, pr.pr_number)
    if queued_key in queued:
        return _stranded_decision(
            pr, "skip", "already_queued", "merge_queue_entries_checked=true"
        )
    refusal, evidence = _stranded_gate_refusal(candidate)
    if refusal is not None:
        return _stranded_decision(pr, "skip", refusal, *evidence)
    witness = _current_approval_witness(pr)
    if witness is None:
        return _stranded_decision(pr, "skip", "approval_reviewer_unconfirmed")
    if dry_run:
        return _stranded_decision(
            pr,
            "enqueue",
            "eligible_dry_run",
            "merge_queue_entries_checked=true",
            "dry_run=true",
        )
    reverified, reverify_reason, reverify_evidence = _reverify_approval_before_enqueue(
        pr,
        runner,
        witness,
    )
    if not reverified:
        return _stranded_decision(pr, "skip", reverify_reason, *reverify_evidence)
    enqueue = _enqueue_merge_queue(pr, runner)
    return _stranded_decision(
        pr,
        "enqueue" if enqueue.returncode == 0 else "skip",
        "stranded_enqueued" if enqueue.returncode == 0 else "enqueue_failed",
        "merge_queue_entries_checked=true",
        "gh_pr_merge_auto=true",
        f"returncode={enqueue.returncode}",
        f"stderr={redact_gh_stderr(enqueue.stderr or '')}",
    )


def _stranded_gate_refusal(candidate: StrandedPullRequest) -> tuple[str | None, tuple[str, ...]]:
    pr = candidate.pr
    if pr.merge_state_status != "CLEAN":
        return "merge_state_not_clean", (f"merge_state_status={pr.merge_state_status or ''}",)
    if pr.rollup_state != "SUCCESS":
        return "required_checks_not_success", (f"rollup_state={pr.rollup_state or ''}",)
    witness = _current_approval_witness(pr)
    if witness is None:
        return "approval_reviewer_unconfirmed", ()
    if candidate.author_login and witness.reviewer_login.lower() == candidate.author_login.lower():
        return "approval_not_independent", (f"reviewer={witness.reviewer_login}",)
    gate = _daemon_non_wall_gate(pr, evidence=("approval_wall: not armed",))
    if gate.refusal_reason is not None:
        return gate.refusal_reason, gate.evidence
    return None, gate.evidence


def _parse_sweep_repository(
    repository: Mapping[str, Any]
) -> tuple[tuple[StrandedPullRequest, ...], set[tuple[str, int]]]:
    raw_prs = repository.get("pullRequests")
    if not isinstance(raw_prs, Mapping):
        raise ForgeConfigError("stranded sweep response missing pullRequests")
    if ((raw_prs.get("pageInfo") or {}).get("hasNextPage")) is True:
        raise ForgeConfigError("stranded sweep returned more than one PR page; narrow scope")
    raw_queue = repository.get("mergeQueue")
    if not isinstance(raw_queue, Mapping):
        raise ForgeConfigError("stranded sweep response missing mergeQueue")
    raw_entries = raw_queue.get("entries")
    if not isinstance(raw_entries, Mapping):
        raise ForgeConfigError("stranded sweep response missing mergeQueue entries")
    if ((raw_entries.get("pageInfo") or {}).get("hasNextPage")) is True:
        raise ForgeConfigError("merge queue entries returned more than one page; narrow scope")

    queued = _stranded_queued_numbers(raw_entries.get("nodes") or ())
    candidates: list[StrandedPullRequest] = []
    for node in raw_prs.get("nodes") or ():
        if not isinstance(node, Mapping):
            continue
        author = str(((node.get("author") or {}).get("login") or "")).strip()
        candidates.append(StrandedPullRequest(pr=_parse_daemon_pr(node), author_login=author))
    return tuple(candidates), queued


def _stranded_queued_numbers(nodes: Sequence[Any]) -> set[tuple[str, int]]:
    queued: set[tuple[str, int]] = set()
    for entry in nodes:
        if not isinstance(entry, Mapping):
            continue
        pr = entry.get("pullRequest")
        if not isinstance(pr, Mapping):
            continue
        repo = str(((pr.get("repository") or {}).get("nameWithOwner") or "")).strip()
        number = pr.get("number")
        if repo and isinstance(number, int):
            queued.add((repo, number))
    return queued


def _stranded_decision(
    pr: DaemonPullRequest,
    status: str,
    reason: str,
    *evidence: str,
) -> StrandedSweepDecision:
    return StrandedSweepDecision(
        status=status,
        reason=reason,
        repo=pr.repo,
        pr_number=pr.pr_number,
        head_sha=pr.head_sha,
        evidence=tuple(item for item in evidence if item),
    )


def _parse_approval_witnesses(reviews: Mapping[str, Any]) -> tuple[DaemonApprovalWitness, ...]:
    witnesses: list[DaemonApprovalWitness] = []
    for review in reviews.get("nodes") or ():
        if not isinstance(review, dict):
            continue
        reviewer = str(((review.get("author") or {}).get("login") or "")).strip()
        commit_oid = str(((review.get("commit") or {}).get("oid") or "")).lower()
        state = str(review.get("state") or "")
        if not reviewer or not commit_oid:
            continue
        witnesses.append(
            DaemonApprovalWitness(
                reviewer_login=reviewer,
                commit_oid=commit_oid,
                state=state,
                review_id=str(review.get("id") or ""),
            )
        )
    return tuple(witnesses)


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
            latest_at=_first_timestamp(raw, "completedAt", "startedAt", "updatedAt"),
        )
    if kind == "StatusContext":
        return DaemonStatusCheck(
            name=str(raw.get("context") or ""),
            state=str(raw.get("state") or "UNKNOWN"),
            kind=kind,
            latest_at=_first_timestamp(raw, "updatedAt", "createdAt"),
        )
    return DaemonStatusCheck(
        name=str(raw.get("name") or raw.get("context") or ""),
        state="UNKNOWN",
        kind=kind,
        latest_at=_first_timestamp(raw, "updatedAt", "createdAt", "completedAt", "startedAt"),
    )


def _first_timestamp(raw: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _daemon_gate_refusal(
    pr: DaemonPullRequest,
    *,
    approval_verifier: ApprovalCapabilityVerifier | None = None,
    approval_wall: ApprovalWallRuntime | None = None,
) -> str | None:
    return _daemon_gate_evaluation(
        pr,
        approval_verifier=approval_verifier,
        approval_wall=approval_wall,
    ).refusal_reason


def _daemon_gate_evaluation(
    pr: DaemonPullRequest,
    *,
    approval_verifier: ApprovalCapabilityVerifier | None = None,
    approval_wall: ApprovalWallRuntime | None = None,
) -> DaemonGateEvaluation:
    if pr.is_draft:
        return DaemonGateEvaluation("draft_pr")
    if pr.review_decision != "APPROVED":
        return DaemonGateEvaluation("review_not_approved")
    if pr.head_sha.lower() not in pr.approving_review_commits:
        return DaemonGateEvaluation("approval_not_current_head")
    if _current_approval_witness(pr) is None:
        return DaemonGateEvaluation("approval_reviewer_unconfirmed")
    wall_status = APPROVAL_WALL_ARMED if approval_verifier is not None else APPROVAL_WALL_DORMANT
    verifier = approval_verifier
    wall_reason = ""
    if approval_wall is not None:
        wall_status = approval_wall.status
        verifier = approval_wall.verifier
        wall_reason = approval_wall.reason
    if wall_status == APPROVAL_WALL_DORMANT:
        evidence = ("approval_wall: not armed",)
        return _daemon_non_wall_gate(pr, evidence=evidence)
    if wall_status == APPROVAL_WALL_MISCONFIGURED:
        evidence = ("approval_wall: misconfigured",)
        if wall_reason:
            evidence = (*evidence, f"approval_wall_reason={wall_reason}")
        return DaemonGateEvaluation("approval_wall_misconfigured", evidence)
    if not pr.approval_capability_marker:
        return DaemonGateEvaluation("approval_capability_missing")
    if verifier is None:
        return DaemonGateEvaluation(
            "approval_capability_invalid",
            ("approval_capability_reason=verifier_unavailable",),
        )
    capability = verifier.verify(
        pr.approval_capability_marker,
        repo=pr.repo,
        pr_number=pr.pr_number,
        head_sha=pr.head_sha,
        approved_by_candidates=pr.approving_reviewers,
    )
    if not capability.valid:
        return DaemonGateEvaluation(
            "approval_capability_invalid",
            (f"approval_capability_reason={capability.reason}",),
        )
    return _daemon_non_wall_gate(pr)


def _daemon_non_wall_gate(
    pr: DaemonPullRequest,
    *,
    evidence: tuple[str, ...] = (),
) -> DaemonGateEvaluation:
    if pr.mergeable != "MERGEABLE":
        return DaemonGateEvaluation("not_mergeable", evidence)
    if not pr.files_complete:
        return DaemonGateEvaluation("changed_files_incomplete", evidence)
    if not pr.checks_complete:
        return DaemonGateEvaluation("status_checks_incomplete", evidence)
    latest_required_checks = _latest_required_checks(pr.checks)
    governance = latest_required_checks.get(DEFAULT_GOVERNANCE_CHECK)
    if governance is None:
        return DaemonGateEvaluation("governance_check_missing", evidence)
    if not governance.success:
        return DaemonGateEvaluation("governance_check_not_success", evidence)
    tests = tuple(check for check in latest_required_checks.values() if _is_test_check(check.name))
    if any(not check.success for check in tests):
        return DaemonGateEvaluation("test_check_not_success", evidence)
    if pr.rollup_state != "SUCCESS" and pr.merge_state_status != "CLEAN":
        return DaemonGateEvaluation("rollup_not_success", evidence)
    return DaemonGateEvaluation(None, evidence)


def _current_approval_witnesses(pr: DaemonPullRequest) -> tuple[DaemonApprovalWitness, ...]:
    head_sha = pr.head_sha.lower()
    current = (
        witness
        for witness in pr.approval_witnesses
        if witness.approved
        and witness.commit_oid.lower() == head_sha
        and witness.reviewer_login.strip()
    )
    return tuple(sorted(current, key=lambda witness: (witness.reviewer_login.lower(), witness.review_id)))


def _current_approval_witness(pr: DaemonPullRequest) -> DaemonApprovalWitness | None:
    current = _current_approval_witnesses(pr)
    return current[0] if current else None


def _normalize_authorized_reviewers(reviewers: Sequence[str] | None) -> frozenset[str] | None:
    if reviewers is None:
        return None
    normalized = frozenset(
        reviewer.strip().lower()
        for reviewer in reviewers
        if isinstance(reviewer, str) and reviewer.strip()
    )
    return normalized


def _authorized_approval_witness(
    pr: DaemonPullRequest, authorized_reviewers: frozenset[str] | None
) -> tuple[DaemonApprovalWitness | None, str]:
    if not authorized_reviewers:
        return None, "authorized_reviewers_missing"
    for witness in _current_approval_witnesses(pr):
        if witness.reviewer_login.lower() in authorized_reviewers:
            return witness, ""
    return None, "approval_reviewer_unauthorized"


def _approval_settle_key(pr: DaemonPullRequest, witness: DaemonApprovalWitness) -> str:
    review_part = witness.review_id or witness.reviewer_login.lower()
    return f"{pr.repo}#{pr.pr_number}:{pr.head_sha.lower()}:{review_part}"


def _clear_approval_settle_for_pr(
    keys: set[str],
    pr: DaemonPullRequest,
    ready_at: dict[str, float] | None = None,
) -> None:
    prefix = f"{pr.repo}#{pr.pr_number}:"
    for key in tuple(keys):
        if key.startswith(prefix):
            keys.discard(key)
            if ready_at is not None:
                ready_at.pop(key, None)


def _latest_required_checks(checks: Sequence[DaemonStatusCheck]) -> dict[str, DaemonStatusCheck]:
    latest: dict[str, tuple[DaemonStatusCheck, datetime | None, int]] = {}
    for observed_order, check in enumerate(checks):
        if check.name == DEFAULT_GOVERNANCE_CHECK or _is_test_check(check.name):
            timestamp = _parse_check_timestamp(check.latest_at)
            current = latest.get(check.name)
            if current is None or _check_is_later(timestamp, observed_order, current):
                latest[check.name] = (check, timestamp, observed_order)
    return {name: check for name, (check, _timestamp, _order) in latest.items()}


def _check_is_later(
    candidate_timestamp: datetime | None,
    candidate_order: int,
    current: tuple[DaemonStatusCheck, datetime | None, int],
) -> bool:
    _current_check, current_timestamp, current_order = current
    if (
        candidate_timestamp is not None
        and current_timestamp is not None
        and candidate_timestamp != current_timestamp
    ):
        return candidate_timestamp > current_timestamp
    return candidate_order > current_order


def _parse_check_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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


def _approval_marker_mint_needed(
    gate: DaemonGateEvaluation,
    approval_verifier: ApprovalCapabilityVerifier | None,
    approval_wall: ApprovalWallRuntime | None,
    approval_marker_issuer: ApprovalMarkerIssuer | None,
) -> bool:
    if gate.refusal_reason != "approval_capability_missing":
        return False
    if approval_marker_issuer is None:
        return False
    if approval_wall is not None:
        return approval_wall.status == APPROVAL_WALL_ARMED
    return approval_verifier is not None


def _mint_approval_marker_before_enqueue(
    pr: DaemonPullRequest,
    runner: GhRunner,
    witness: DaemonApprovalWitness,
    *,
    issuer: ApprovalMarkerIssuer | None,
    body_updater: PrBodyUpdater | None = None,
) -> tuple[bool, str, tuple[str, ...]]:
    if issuer is None:
        return (
            False,
            "approval_capability_issuer_unavailable",
            (f"reviewer={witness.reviewer_login}",),
        )
    try:
        marker = issuer(pr, witness)
    except Exception as exc:
        return (
            False,
            "approval_capability_mint_failed",
            (
                f"reviewer={witness.reviewer_login}",
                f"error={redact_gh_stderr(str(exc))}",
            ),
        )
    normalized = extract_approval_capability_marker(marker)
    if normalized is None:
        return (
            False,
            "approval_capability_mint_failed",
            (f"reviewer={witness.reviewer_login}", "error=issuer_returned_invalid_marker"),
        )
    updated_body = _upsert_approval_capability_marker(pr.body, normalized)
    updater = body_updater or (lambda candidate, body: _update_pr_body(candidate, body, runner))
    try:
        update = updater(pr, updated_body)
    except Exception as exc:
        return (
            False,
            "approval_capability_body_update_failed",
            (
                f"reviewer={witness.reviewer_login}",
                f"error={redact_gh_stderr(str(exc))}",
            ),
        )
    if update.returncode != 0:
        return (
            False,
            "approval_capability_body_update_failed",
            (
                f"reviewer={witness.reviewer_login}",
                f"returncode={update.returncode}",
                f"stderr={redact_gh_stderr(update.stderr or '')}",
            ),
        )
    return (
        True,
        "approval_capability_minted",
        (
            f"reviewer={witness.reviewer_login}",
            "approval_capability_marker_upserted=true",
            f"returncode={update.returncode}",
        ),
    )


def _upsert_approval_capability_marker(body: str | None, marker: str) -> str:
    normalized = extract_approval_capability_marker(marker)
    if normalized is None:
        raise IntegratorBeltError("approval capability marker is malformed")
    kept = [
        line
        for line in (body or "").splitlines()
        if not line.strip().startswith(MARKER_PREFIX)
    ]
    while kept and kept[-1] == "":
        kept.pop()
    if kept:
        return "\n".join((*kept, "", normalized)) + "\n"
    return f"{normalized}\n"


def _update_pr_body(
    pr: DaemonPullRequest, body: str, runner: GhRunner
) -> subprocess.CompletedProcess:
    return runner(
        [
            "gh",
            "api",
            "-X",
            "PATCH",
            f"/repos/{pr.repo}/pulls/{pr.pr_number}",
            "--input",
            "-",
        ],
        json.dumps({"body": body}, sort_keys=True),
    )


_DAEMON_APPROVAL_REVERIFY_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!){"
    "repository(owner:$owner,name:$name){pullRequest(number:$number){"
    "reviewDecision headRefOid "
    "latestOpinionatedReviews(first:20){nodes{id state author{login} commit{oid}}}"
    "}}}"
)

_MERGE_QUEUE_DEQUEUE_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!){"
    "repository(owner:$owner,name:$name){"
    "pullRequest(number:$number){id number}"
    "mergeQueue{entries(first:100){pageInfo{hasNextPage}nodes{"
    "pullRequest{id number repository{nameWithOwner}}"
    "}}}"
    "}}"
)

_DEQUEUE_PULL_REQUEST_MUTATION = (
    "mutation($id:ID!){"
    "dequeuePullRequest(input:{id:$id}){"
    "mergeQueueEntry{pullRequest{number repository{nameWithOwner}}}"
    "}}"
)


def _reverify_approval_before_enqueue(
    pr: DaemonPullRequest,
    runner: GhRunner,
    expected: DaemonApprovalWitness,
) -> tuple[bool, str, tuple[str, ...]]:
    try:
        owner, name = _split_repo(pr.repo)
        parsed = _gh_graphql(
            runner,
            _DAEMON_APPROVAL_REVERIFY_QUERY,
            {"owner": owner, "name": name, "number": pr.pr_number},
            purpose=f"reverify approval for {pr.repo}#{pr.pr_number}",
        )
    except (ForgeConfigError, IntegratorBeltError) as exc:
        return (
            False,
            "approval_reverify_failed",
            (f"error={redact_gh_stderr(str(exc))}",),
        )
    live_pr = ((parsed.get("data") or {}).get("repository") or {}).get("pullRequest")
    if not isinstance(live_pr, dict):
        return False, "approval_reverify_failed", ("error=unexpected_response",)
    if str(live_pr.get("headRefOid") or "").lower() != pr.head_sha.lower():
        return (
            False,
            "approval_reverify_failed",
            (
                "head_moved=true",
                f"expected_head={pr.head_sha}",
                f"live_head={str(live_pr.get('headRefOid') or '')}",
            ),
        )
    if live_pr.get("reviewDecision") != "APPROVED":
        return (
            False,
            "approval_not_reconfirmed",
            (f"review_decision={live_pr.get('reviewDecision') or ''}",),
        )
    witnesses = _parse_approval_witnesses(
        live_pr.get("latestOpinionatedReviews")
        if isinstance(live_pr.get("latestOpinionatedReviews"), dict)
        else {}
    )
    for witness in witnesses:
        if (
            witness.approved
            and witness.reviewer_login == expected.reviewer_login
            and witness.commit_oid.lower() == pr.head_sha.lower()
            and (not expected.review_id or witness.review_id == expected.review_id)
        ):
            return (
                True,
                "approval_reverified",
                (
                    "approval_reverified=true",
                    f"reviewer={expected.reviewer_login}",
                    f"review_id={expected.review_id}",
                ),
            )
    return (
        False,
        "approval_not_reconfirmed",
        (
            f"reviewer={expected.reviewer_login}",
            f"review_id={expected.review_id}",
            "approval_reverified=false",
        ),
    )


def dequeue_merge_queue(
    *,
    repo: str,
    pr_number: int,
    gh_runner: GhRunner | None = None,
    convert_to_draft: bool = False,
) -> MergeQueueDequeueResult:
    """Emergency primitive for evicting a PR from GitHub's merge queue."""

    owner, name = _split_repo(repo)
    if pr_number < 1:
        raise IntegratorBeltError("pr_number must be >= 1")
    runner = gh_runner or _default_gh_runner
    parsed = _gh_graphql(
        runner,
        _MERGE_QUEUE_DEQUEUE_QUERY,
        {"owner": owner, "name": name, "number": pr_number},
        purpose=f"read merge queue membership for {repo}#{pr_number}",
    )
    repository = (parsed.get("data") or {}).get("repository")
    if not isinstance(repository, dict):
        raise IntegratorBeltError(f"pull request does not exist: {repo}#{pr_number}")
    pull_request = repository.get("pullRequest")
    if not isinstance(pull_request, dict) or not pull_request.get("id"):
        raise IntegratorBeltError(f"pull request does not exist: {repo}#{pr_number}")
    pull_request_id = str(pull_request["id"])
    merge_queue = repository.get("mergeQueue")
    entries: dict[str, Any] = {}
    nodes: list[Any] = []
    if merge_queue is not None:
        if not isinstance(merge_queue, dict):
            raise ForgeConfigError(f"unexpected merge queue response for {repo}#{pr_number}")
        raw_entries = merge_queue.get("entries")
        if not isinstance(raw_entries, dict):
            raise ForgeConfigError(f"unexpected merge queue response for {repo}#{pr_number}")
        entries = raw_entries
        raw_nodes = entries.get("nodes")
        if not isinstance(raw_nodes, list):
            raise ForgeConfigError(f"unexpected merge queue response for {repo}#{pr_number}")
        nodes = raw_nodes
    queued = any(
        isinstance(node, dict)
        and isinstance(node.get("pullRequest"), dict)
        and str(node["pullRequest"].get("id") or "") == pull_request_id
        for node in nodes
    )
    if not queued and isinstance(entries.get("pageInfo"), dict) and entries["pageInfo"].get("hasNextPage"):
        raise ForgeConfigError(
            f"merge queue membership for {repo}#{pr_number} spans more than 100 entries"
        )
    evidence = [
        "merge_queue_membership_checked=true",
        f"queued={str(queued).lower()}",
    ]
    if not queued:
        return MergeQueueDequeueResult(
            repo=repo,
            pr_number=pr_number,
            disabled_auto_merge=False,
            converted_to_draft=False,
            queued=False,
            dequeued=False,
            evidence=tuple((*evidence, "dequeue_noop=not_queued")),
        )
    mutation = _gh_graphql(
        runner,
        _DEQUEUE_PULL_REQUEST_MUTATION,
        {"id": pull_request_id},
        purpose=f"dequeue pull request {repo}#{pr_number}",
    )
    if mutation.get("errors"):
        raise ForgeConfigError(f"could not dequeue pull request {repo}#{pr_number}: GraphQL returned errors")
    evidence.append("dequeue_pull_request=true")
    converted = False
    if convert_to_draft:
        draft = runner(["gh", "pr", "ready", str(pr_number), "--repo", repo, "--undo"], None)
        converted = draft.returncode == 0
        evidence.extend(
            [
                "gh_pr_ready_undo=true",
                f"draft_returncode={draft.returncode}",
                f"draft_stderr={redact_gh_stderr(draft.stderr or '')}",
            ]
        )
    return MergeQueueDequeueResult(
        repo=repo,
        pr_number=pr_number,
        disabled_auto_merge=True,
        converted_to_draft=converted,
        queued=True,
        dequeued=True,
        evidence=tuple(evidence),
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
        stderr = redact_gh_stderr(proc.stderr or "")
        if _is_search_rate_limit_error(stderr):
            raise SearchApiRateLimited(
                f"could not {purpose}: GitHub Search API rate-limited; retry later",
                retry_after_seconds=_retry_after_from_text(stderr),
            )
        raise ForgeConfigError(
            f"could not {purpose}: {stderr or 'unknown error'}"
        )
    try:
        parsed = json.loads((proc.stdout or "").strip() or "{}")
    except (TypeError, ValueError) as exc:
        raise ForgeConfigError(f"could not {purpose}: unparseable JSON response") from exc
    if not isinstance(parsed, dict):
        raise ForgeConfigError(f"could not {purpose}: unexpected JSON response")
    return parsed


def _is_search_rate_limit_error(text: str) -> bool:
    lowered = text.lower()
    return (
        "http 429" in lowered
        or "status code 429" in lowered
        or "rate limit" in lowered
        or "secondary rate limit" in lowered
        or "api rate limit exceeded" in lowered
    )


def _retry_after_from_text(text: str) -> int | None:
    match = re.search(r"(?i)retry-after\s*[:=]\s*(\d+)", text)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


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


def _build_module_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m creator_engine_validator.forge.integrator_belt")
    sub = parser.add_subparsers(dest="command", required=True)
    sweep = sub.add_parser("stranded-sweep", help="enqueue approved+green PRs stranded outside merge queue")
    sweep.add_argument("--repo", default=DEFAULT_SWEEP_REPO, help="owner/name repository scope")
    sweep.add_argument("--queue-branch", default=DEFAULT_QUEUE_BRANCH, dest="queue_branch", help="merge queue branch")
    sweep.add_argument("--token-env", default=DEFAULT_TOKEN_ENV, help="env var containing the GitHub token")
    sweep.add_argument("--dry-run", action="store_true", help="log eligible PRs without enqueueing")
    sweep.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    return parser


def _cmd_stranded_sweep(args: argparse.Namespace) -> int:
    try:
        token = token_from_env(args.token_env)
        result = run_stranded_sweep(
            repo=args.repo,
            queue_branch=args.queue_branch,
            dry_run=bool(getattr(args, "dry_run", False)),
            gh_runner=gh_runner_with_token(token),
            log_sink=JsonLineLogger(sys.stderr),
        )
    except IntegratorBeltError as exc:
        print(f"ERROR: stranded-sweep refused: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive fail-closed module CLI
        print(f"ERROR: stranded-sweep failed closed: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(
            "stranded-sweep: "
            f"enqueue={result.enqueue_count} skip={result.skip_count} failed={result.failed_count}"
        )
    return 0 if result.failed_count == 0 else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_module_parser()
    args = parser.parse_args(argv)
    if args.command == "stranded-sweep":
        return _cmd_stranded_sweep(args)
    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover - module CLI edge
    raise SystemExit(main())
