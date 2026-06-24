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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

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
DEFAULT_WORK_ROOT = ".hermes/integrator-belt"
DEFAULT_INTERVAL_SECONDS = 60.0


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
class PullRequestIdentity:
    """Live PR refs needed by the repair adapter and executor race guard."""

    repo: str
    pr_number: int
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str
    head_repo: str


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
    """Return an ``integration_queue_dry_run`` live-action runner."""

    from ..integration_queue_dry_run import LiveActionRequest, LiveActionResult

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
