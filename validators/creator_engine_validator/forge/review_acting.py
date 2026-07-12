"""Default-OFF review-pickup acting: post comments only.

This module posts PR comments only through ``issues/{number}/comments`` and
never calls ``pulls/{number}/reviews``.  It has no approval or merge authority;
the only required token scope is ``issues:write``.  A reviewer-spawn command is
an explicit Operator configuration, not a module default.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review_spawn_provider import ProviderPolicy

from ..pickup_search import GhRunner


ACTING_ENABLED_ENV = "CE_REVIEW_ACTING_ENABLED"
ACTING_SPAWN_COMMAND_ENV = "CE_REVIEW_ACTING_SPAWN_CMD"
LogSink = Callable[[Mapping[str, Any]], None]


class SpawnerUnconfigured(RuntimeError):
    """Raised when an armed acting pass lacks its Operator spawn template."""


class ActingLedgerUnreadable(RuntimeError):
    """Raised when durable acting state cannot be read safely."""


@dataclass(frozen=True)
class ActingContext:
    repo: str
    pr_number: int
    head_sha: str
    url: str
    title: str
    assigned_reviewer: str
    author: str


Spawner = Callable[[ActingContext, GhRunner], str]

# A comment POST can succeed after its client loses the response.  Never retry a
# submission for which that outcome is possible: a later operator pass may
# inspect the forge, but this actor must not emit a duplicate comment.
MAX_ATTEMPTS_PER_CLAIM = 3

_REPO_IDENTITY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_HEAD_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_LEDGER_ACTIONS = frozenset({
    "attempt_claimed",
    "comment_submission_started",
    "comment_posted",
    "retry_exhausted",
    "spawner_unconfigured",
    "spawn_failed",
    "reviewer_authority_invalid",
    "live_claim_mismatch",
    "comment_failed",
    # M2 provider outcome vocabulary.  These remain durable, fail-closed
    # evidence when an acting adapter is later wired behind the S3 seam.
    "SPAWN_REFUSED",
    "SPAWN_FAILED",
    "TIMEOUT",
    "STALE_HEAD",
    "MALFORMED_RESULT",
    "PARTIAL_OUTPUT",
    "REVIEWER_EXIT_NONZERO",
    "UNCERTAIN_COMMENT",
})


@dataclass(frozen=True)
class ActingPassResult:
    commented: tuple[dict[str, Any], ...] = ()
    skipped_dedup: tuple[dict[str, Any], ...] = ()
    failed: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class _ClaimState:
    """Fail-closed fold of durable state for one immutable PR head."""

    max_attempt: int = 0
    comment_posted: bool = False
    submission_started: bool = False
    retry_exhausted: bool = False


def is_acting_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return True only when ``CE_REVIEW_ACTING_ENABLED=1``. Default OFF."""
    values = os.environ if env is None else env
    return values.get(ACTING_ENABLED_ENV) == "1"


def _ledger_path(path: Path | str) -> Path:
    return Path(path)


def load_acting_ledger(path: Path | str) -> list[dict[str, Any]]:
    """Read the append-only acting ledger; only a missing file is empty.

    A corrupt or unreadable ledger is not equivalent to an empty one: doing so
    could lose durable submission evidence and permit a duplicate comment.
    """
    ledger_path = _ledger_path(path)
    try:
        exists = ledger_path.exists()
    except OSError as exc:
        raise ActingLedgerUnreadable("acting ledger cannot be inspected") from exc
    if not exists:
        return []
    try:
        is_file = ledger_path.is_file()
    except OSError as exc:
        raise ActingLedgerUnreadable("acting ledger cannot be inspected") from exc
    if not is_file:
        raise ActingLedgerUnreadable("acting ledger is not a regular file")
    records: list[dict[str, Any]] = []
    try:
        text = ledger_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActingLedgerUnreadable("acting ledger cannot be read") from exc
    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise ActingLedgerUnreadable(
                f"acting ledger contains invalid JSON at record {line_number}"
            ) from exc
        if not isinstance(record, dict):
            raise ActingLedgerUnreadable(
                f"acting ledger contains a non-object record at record {line_number}"
            )
        records.append(_validate_ledger_record(record, line_number))
    return records


def _validate_ledger_record(record: dict[str, Any], line_number: int) -> dict[str, Any]:
    """Validate one durable record before it can influence future acting.

    The ledger is submission evidence.  A syntactically valid but ambiguous
    record is therefore unsafe to ignore: it could make a prior submission
    disappear during folding and permit a duplicate comment.
    """
    action = record.get("action")
    if not isinstance(action, str) or action not in _LEDGER_ACTIONS:
        raise ActingLedgerUnreadable(
            f"acting ledger contains an unsupported record at record {line_number}"
        )
    repo = record.get("repo")
    pr_number = record.get("pr_number")
    head_sha = record.get("head_sha")
    if (
        not isinstance(repo, str)
        or not _REPO_IDENTITY.fullmatch(repo)
        or isinstance(pr_number, bool)
        or not isinstance(pr_number, int)
        or pr_number <= 0
        or not isinstance(head_sha, str)
        or not _HEAD_SHA.fullmatch(head_sha)
    ):
        raise ActingLedgerUnreadable(
            f"acting ledger contains malformed durable evidence at record {line_number}"
        )

    normalized = dict(record)
    normalized["head_sha"] = head_sha.lower()
    if action == "attempt_claimed":
        attempt = record.get("attempt")
        reviewer = record.get("assigned_reviewer")
        if (
            isinstance(attempt, bool)
            or not isinstance(attempt, int)
            or attempt <= 0
            or not isinstance(reviewer, str)
            or not reviewer.strip()
        ):
            raise ActingLedgerUnreadable(
                f"acting ledger contains malformed claim evidence at record {line_number}"
            )
    elif action == "comment_submission_started":
        reviewer = record.get("assigned_reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ActingLedgerUnreadable(
                f"acting ledger contains malformed submission evidence at record {line_number}"
            )
    return normalized


def append_acting_ledger(path: Path | str, record: Mapping[str, Any]) -> None:
    """Append one JSONL acting ledger record."""
    ledger_path = _ledger_path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), sort_keys=True) + "\n")


def acting_ledger_key(repo: str, pr_number: int, head_sha: str) -> tuple[str, str, str]:
    """Return the durable dedup identity for one immutable PR head comment."""
    return (
        f"review-acting:{repo}:{pr_number}:{head_sha}",
        f"{repo}:{pr_number}:{head_sha}",
        "comment_posted",
    )


def acting_ledger_keys(records: Iterable[Mapping[str, Any]]) -> set[tuple[str, str, str]]:
    """Fold acting ledger records into their durable dedup keys."""
    keys: set[tuple[str, str, str]] = set()
    for record in records:
        if not isinstance(record, Mapping):
            continue
        if record.get("action") != "comment_posted":
            continue
        repo = str(record.get("repo") or "")
        head_sha = str(record.get("head_sha") or "")
        try:
            pr_number = int(record.get("pr_number"))
        except (TypeError, ValueError):
            continue
        if repo and head_sha:
            keys.add(acting_ledger_key(repo, pr_number, head_sha))
    return keys


def post_pr_comment(repo: str, pr_number: int, body: str, *, gh_runner: GhRunner) -> str | None:
    """POST to the Issues comments endpoint and return its ``html_url`` on success."""
    try:
        proc = gh_runner(
            [
                "gh", "api", "--method", "POST",
                f"repos/{repo}/issues/{pr_number}/comments", "--input", "-",
            ],
            json.dumps({"body": body}),
        )
    except Exception:
        return None
    if getattr(proc, "returncode", 1) != 0:
        return None
    try:
        payload = json.loads((getattr(proc, "stdout", "") or "").strip())
    except (TypeError, ValueError):
        return None
    url = payload.get("html_url") if isinstance(payload, Mapping) else None
    return str(url) if url else None


def _live_claim_matches(ctx: ActingContext, gh_runner: GhRunner) -> bool:
    """Re-read the PR immediately before POST and require its claimed identity.

    The endpoint is target-repository scoped, but validate the response too so a
    substituted runner or malformed API response cannot redirect an acting pass.
    """
    try:
        proc = gh_runner(["gh", "api", f"repos/{ctx.repo}/pulls/{ctx.pr_number}"])
    except Exception:
        return False
    if getattr(proc, "returncode", 1) != 0:
        return False
    try:
        payload = json.loads((getattr(proc, "stdout", "") or "").strip())
    except (TypeError, ValueError):
        return False
    if not isinstance(payload, Mapping):
        return False
    base = payload.get("base")
    base_repo = base.get("repo") if isinstance(base, Mapping) else None
    return (
        payload.get("number") == ctx.pr_number
        and isinstance(base_repo, Mapping)
        and str(base_repo.get("full_name") or "") == ctx.repo
        and isinstance(payload.get("head"), Mapping)
        and str(payload["head"].get("sha") or "") == ctx.head_sha
    )


def _reviewer_verdict(output: str, ctx: ActingContext) -> str | None:
    """Return a verdict only from reviewer-bound, claim-bound evidence.

    Spawn output is deliberately data, not a free-form comment.  The reviewer
    must identify itself and supply authority for this exact repository, PR and
    head.  Anything malformed, stale, or self-assigned fails closed.
    """
    try:
        evidence = json.loads(output)
    except (TypeError, ValueError):
        return None
    if not isinstance(evidence, Mapping):
        return None
    verdict = evidence.get("verdict")
    reviewer = str(evidence.get("reviewer") or "")
    authority = evidence.get("reviewer_authority")
    # Dual-support transition: legacy evidence carries ``reviewer_authority``
    # directly; M2 emits a versioned envelope with the same binding mapping.
    if authority is None and evidence.get("version") == 1:
        authority = evidence.get("authority")
    if verdict not in {"COMMENT", "REQUEST_CHANGES"} or not isinstance(authority, Mapping):
        return None
    if not ctx.assigned_reviewer or not ctx.author or reviewer != ctx.assigned_reviewer:
        return None
    if reviewer == ctx.author:
        return None
    if str(authority.get("actor") or "") != ctx.assigned_reviewer:
        return None
    try:
        authority_pr = int(authority.get("pr_number"))
    except (TypeError, ValueError):
        return None
    if (
        str(authority.get("repo") or "") != ctx.repo
        or authority_pr != ctx.pr_number
        or str(authority.get("head_sha") or "") != ctx.head_sha
    ):
        return None
    return verdict


def _claim_state(records: Iterable[Mapping[str, Any]], ctx: ActingContext) -> _ClaimState:
    """Fold one identity's append-only sequence without permitting ambiguity.

    A ledger is durable evidence, not a best-effort activity log.  Claims use
    their recorded attempt value (never their record count), and any sequence
    that could hide a prior action is rejected before an actor can spawn or use
    GitHub.  An interrupted claim is intentionally allowed to be superseded by
    a higher claim: a process can crash after persisting its claim but before it
    records its outcome.
    """
    matching = [
        record
        for record in records
        if str(record.get("repo") or "") == ctx.repo
        and record.get("pr_number") == ctx.pr_number
        and str(record.get("head_sha") or "") == ctx.head_sha
    ]
    max_attempt = 0
    open_claim = False
    submission_started = False
    retry_exhausted = False
    comment_posted = False

    outcome_actions = frozenset({
        "spawner_unconfigured",
        "spawn_failed",
        "reviewer_authority_invalid",
        "live_claim_mismatch",
        # M2 provider terminal-attempt vocabulary. These records are emitted
        # by the sequenced provider adapter, so fold them before it can write
        # durable evidence.
        "SPAWN_REFUSED",
        "SPAWN_FAILED",
        "TIMEOUT",
        "STALE_HEAD",
        "MALFORMED_RESULT",
        "PARTIAL_OUTPUT",
        "REVIEWER_EXIT_NONZERO",
    })
    for record in matching:
        action = record["action"]
        if comment_posted or retry_exhausted:
            raise ActingLedgerUnreadable("acting ledger contains an impossible durable sequence")

        if action == "attempt_claimed":
            attempt = record["attempt"]
            if attempt > MAX_ATTEMPTS_PER_CLAIM or attempt <= max_attempt:
                raise ActingLedgerUnreadable("acting ledger contains an inconsistent claim sequence")
            max_attempt = attempt
            # A prior worker may have crashed after this append.  A later,
            # strictly higher claim is the only retry shape that can be folded.
            open_claim = True
            continue

        if action in outcome_actions:
            if not open_claim or submission_started:
                raise ActingLedgerUnreadable("acting ledger contains an impossible durable sequence")
            open_claim = False
            continue

        if action == "UNCERTAIN_COMMENT":
            # The comment may already have reached the forge. Preserve this
            # durable no-duplicate state for controller reconciliation.
            if not open_claim or submission_started:
                raise ActingLedgerUnreadable("acting ledger contains an impossible durable sequence")
            open_claim = False
            submission_started = True
            continue

        if action == "comment_submission_started":
            if not open_claim or submission_started:
                raise ActingLedgerUnreadable("acting ledger contains an impossible durable sequence")
            open_claim = False
            submission_started = True
            continue

        if action == "comment_failed":
            if not submission_started:
                raise ActingLedgerUnreadable("acting ledger contains an impossible durable sequence")
            continue

        if action == "comment_posted":
            # Older durable posted evidence predates the submission-start
            # marker.  It remains terminal, but cannot be mixed with claims
            # without that marker because that would hide a missing POST step.
            if max_attempt and not submission_started:
                raise ActingLedgerUnreadable("acting ledger contains an impossible durable sequence")
            comment_posted = True
            continue

        if action == "retry_exhausted":
            if max_attempt != MAX_ATTEMPTS_PER_CLAIM:
                raise ActingLedgerUnreadable("acting ledger contains an inconsistent retry sequence")
            open_claim = False
            retry_exhausted = True
            continue

        raise ActingLedgerUnreadable("acting ledger contains an impossible durable sequence")

    return _ClaimState(
        max_attempt=max_attempt,
        comment_posted=comment_posted,
        submission_started=submission_started,
        retry_exhausted=retry_exhausted,
    )


def _claim_record(ctx: ActingContext, attempt: int, *, clock: Callable[[], datetime | str] | None) -> dict[str, Any]:
    return {
        "kind": "ce-review-acting",
        "thread_id": f"review-acting:{ctx.repo}:{ctx.pr_number}",
        "item_id": f"{ctx.repo}:{ctx.pr_number}",
        "action": "attempt_claimed",
        "repo": ctx.repo,
        "pr_number": ctx.pr_number,
        "head_sha": ctx.head_sha,
        "assigned_reviewer": ctx.assigned_reviewer,
        "attempt": attempt,
        "ts": _timestamp(clock),
    }


def default_spawner(ctx: ActingContext, gh_runner: GhRunner) -> str:
    """Run the Operator-configured reviewer-spawn template and return stdout.

    The template is parsed before placeholder substitution, so substituted
    values remain individual argv entries and never enter a shell.
    """
    del gh_runner  # The callback shape remains injectable and compatible with custom spawners.
    template = os.environ.get(ACTING_SPAWN_COMMAND_ENV, "").strip()
    if not template:
        raise SpawnerUnconfigured(f"{ACTING_SPAWN_COMMAND_ENV} is not configured")
    values = {
        "repo": ctx.repo,
        "number": str(ctx.pr_number),
        "head_sha": ctx.head_sha,
        "url": ctx.url,
        "assigned_reviewer": ctx.assigned_reviewer,
        "author": ctx.author,
    }
    try:
        argv = [part.format_map(values) for part in shlex.split(template)]
    except (KeyError, ValueError) as exc:
        raise RuntimeError(f"invalid {ACTING_SPAWN_COMMAND_ENV} template: {exc}") from exc
    if not argv:
        raise SpawnerUnconfigured(f"{ACTING_SPAWN_COMMAND_ENV} is not configured")
    proc = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=ProviderPolicy.from_env().timeout_seconds,
        shell=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip()[:200]
        raise RuntimeError(f"reviewer spawn exited {proc.returncode}: {detail}")
    return (proc.stdout or "").strip()


def run_acting_pass(
    *,
    items: Sequence[Mapping[str, Any]],
    gh_runner: GhRunner,
    acting_ledger_path: Path | str,
    log_sink: LogSink | None = None,
    spawner: Spawner | None = None,
    clock: Callable[[], datetime | str] | None = None,
) -> ActingPassResult:
    """Spawn reviewers and post their verdicts, continuing after per-item failures."""
    try:
        records = load_acting_ledger(acting_ledger_path)
    except ActingLedgerUnreadable as exc:
        failed = tuple(
            _failure_record(_context_from_item(item), "ledger_unreadable", exc, clock=clock)
            for item in items
        )
        for record in failed:
            _log(log_sink, "review_acting_ledger_unreadable", record)
        return ActingPassResult(failed=failed)
    seen = acting_ledger_keys(records)
    commented: list[dict[str, Any]] = []
    skipped_dedup: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    spawn = spawner or default_spawner

    for item in items:
        ctx = _context_from_item(item)
        key = acting_ledger_key(ctx.repo, ctx.pr_number, ctx.head_sha)
        try:
            state = _claim_state(records, ctx)
        except ActingLedgerUnreadable as exc:
            record = _failure_record(ctx, "ledger_unreadable", exc, clock=clock)
            _log(log_sink, "review_acting_ledger_unreadable", record)
            failed.append(record)
            continue

        if state.comment_posted or key in seen:
            skipped_dedup.append(dict(item))
            continue

        if state.submission_started:
            record = _failure_record(
                ctx, "comment_submission_uncertain",
                RuntimeError("a prior comment submission may have succeeded; refusing duplicate"), clock=clock,
            )
            _log(log_sink, "review_acting_comment_submission_uncertain", record)
            failed.append(record)
            continue

        if state.retry_exhausted or state.max_attempt >= MAX_ATTEMPTS_PER_CLAIM:
            record = _failure_record(
                ctx, "retry_exhausted",
                RuntimeError(f"retry limit {MAX_ATTEMPTS_PER_CLAIM} reached"), clock=clock,
            )
            _log(log_sink, "review_acting_retry_exhausted", record)
            if not any(
                existing.get("action") == "retry_exhausted"
                and str(existing.get("repo") or "") == ctx.repo
                and existing.get("pr_number") == ctx.pr_number
                and str(existing.get("head_sha") or "") == ctx.head_sha
                for existing in records
            ):
                append_acting_ledger(acting_ledger_path, record)
                records.append(record)
            failed.append(record)
            continue

        claim = _claim_record(ctx, state.max_attempt + 1, clock=clock)
        append_acting_ledger(acting_ledger_path, claim)
        records.append(claim)

        try:
            output = spawn(ctx, gh_runner)
        except SpawnerUnconfigured as exc:
            record = _failure_record(ctx, "spawner_unconfigured", exc, clock=clock)
            _log(log_sink, "review_acting_spawner_unconfigured", record)
            append_acting_ledger(acting_ledger_path, record)
            records.append(record)
            failed.append(record)
            continue
        except Exception as exc:
            record = _failure_record(ctx, "spawn_failed", exc, clock=clock)
            _log(log_sink, "review_acting_spawn_failed", record)
            append_acting_ledger(acting_ledger_path, record)
            records.append(record)
            failed.append(record)
            continue

        verdict = _reviewer_verdict(output, ctx)
        if verdict is None:
            record = _failure_record(
                ctx, "reviewer_authority_invalid",
                RuntimeError("reviewer output lacks valid claim-bound authority"), clock=clock,
            )
            _log(log_sink, "review_acting_reviewer_authority_invalid", record)
            append_acting_ledger(acting_ledger_path, record)
            records.append(record)
            failed.append(record)
            continue

        if not _live_claim_matches(ctx, gh_runner):
            record = _failure_record(
                ctx, "live_claim_mismatch",
                RuntimeError("live PR no longer matches the claimed repo, number, and head"), clock=clock,
            )
            _log(log_sink, "review_acting_live_claim_mismatch", record)
            append_acting_ledger(acting_ledger_path, record)
            records.append(record)
            failed.append(record)
            continue

        submission = _failure_record(
            ctx, "comment_submission_started", RuntimeError("comment submission in progress"), clock=clock,
        )
        submission.pop("error")
        append_acting_ledger(acting_ledger_path, submission)
        records.append(submission)

        comment_url = post_pr_comment(ctx.repo, ctx.pr_number, verdict, gh_runner=gh_runner)
        if comment_url is None:
            record = _failure_record(ctx, "comment_failed", RuntimeError("comment POST failed"), clock=clock)
            _log(log_sink, "review_acting_comment_failed", record)
            append_acting_ledger(acting_ledger_path, record)
            records.append(record)
            failed.append(record)
            continue

        record = {
            "kind": "ce-review-acting",
            "thread_id": key[0],
            "item_id": key[1],
            "action": key[2],
            "repo": ctx.repo,
            "pr_number": ctx.pr_number,
            "head_sha": ctx.head_sha,
            "assigned_reviewer": ctx.assigned_reviewer,
            "comment_url": comment_url,
            "ts": _timestamp(clock),
        }
        append_acting_ledger(acting_ledger_path, record)
        records.append(record)
        seen.add(key)
        commented.append(record)

    return ActingPassResult(
        commented=tuple(commented),
        skipped_dedup=tuple(skipped_dedup),
        failed=tuple(failed),
    )


def _context_from_item(item: Mapping[str, Any]) -> ActingContext:
    return ActingContext(
        repo=str(item.get("repo") or ""),
        pr_number=int(item.get("number") or item.get("pr") or 0),
        head_sha=str(item.get("head_sha") or ""),
        url=str(item.get("url") or ""),
        title=str(item.get("title") or ""),
        assigned_reviewer=str(item.get("assigned_reviewer") or ""),
        author=str(item.get("author") or ""),
    )


def _failure_record(
    ctx: ActingContext,
    action: str,
    exc: BaseException,
    *,
    clock: Callable[[], datetime | str] | None,
) -> dict[str, Any]:
    return {
        "kind": "ce-review-acting",
        "thread_id": f"review-acting:{ctx.repo}:{ctx.pr_number}",
        "item_id": f"{ctx.repo}:{ctx.pr_number}",
        "action": action,
        "repo": ctx.repo,
        "pr_number": ctx.pr_number,
        "head_sha": ctx.head_sha,
        "assigned_reviewer": ctx.assigned_reviewer,
        "error": str(exc),
        "ts": _timestamp(clock),
    }


def _timestamp(clock: Callable[[], datetime | str] | None) -> str:
    now = clock() if clock is not None else datetime.now(timezone.utc)
    if isinstance(now, datetime):
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(now)


def _log(log_sink: LogSink | None, event: str, record: Mapping[str, Any]) -> None:
    if log_sink is not None:
        log_sink({"event": event, **record})
