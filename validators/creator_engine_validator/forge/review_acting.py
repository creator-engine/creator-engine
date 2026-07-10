"""Default-OFF review-pickup acting: post comments only.

This module posts PR comments only through ``issues/{number}/comments`` and
never calls ``pulls/{number}/reviews``.  It has no approval or merge authority;
the only required token scope is ``issues:write``.  A reviewer-spawn command is
an explicit Operator configuration, not a module default.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..pickup_search import GhRunner


ACTING_ENABLED_ENV = "CE_REVIEW_ACTING_ENABLED"
ACTING_SPAWN_COMMAND_ENV = "CE_REVIEW_ACTING_SPAWN_CMD"
LogSink = Callable[[Mapping[str, Any]], None]


class SpawnerUnconfigured(RuntimeError):
    """Raised when an armed acting pass lacks its Operator spawn template."""


@dataclass(frozen=True)
class ActingContext:
    repo: str
    pr_number: int
    head_sha: str
    url: str
    title: str
    assigned_reviewer: str


Spawner = Callable[[ActingContext, GhRunner], str]


@dataclass(frozen=True)
class ActingPassResult:
    commented: tuple[dict[str, Any], ...] = ()
    skipped_dedup: tuple[dict[str, Any], ...] = ()
    failed: tuple[dict[str, Any], ...] = ()


def is_acting_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return True only when ``CE_REVIEW_ACTING_ENABLED=1``. Default OFF."""
    values = os.environ if env is None else env
    return values.get(ACTING_ENABLED_ENV) == "1"


def _ledger_path(path: Path | str) -> Path:
    return Path(path)


def load_acting_ledger(path: Path | str) -> list[dict[str, Any]]:
    """Read the tolerant append-only acting ledger; a missing file is empty."""
    ledger_path = _ledger_path(path)
    if not ledger_path.is_file():
        return []
    records: list[dict[str, Any]] = []
    try:
        text = ledger_path.read_text(encoding="utf-8")
    except OSError:
        return records
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def append_acting_ledger(path: Path | str, record: Mapping[str, Any]) -> None:
    """Append one JSONL acting ledger record."""
    ledger_path = _ledger_path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), sort_keys=True) + "\n")


def acting_ledger_key(repo: str, pr_number: int) -> tuple[str, str, str]:
    """Return the durable dedup identity for one PR comment."""
    return (f"review-acting:{repo}:{pr_number}", f"{repo}:{pr_number}", "comment_posted")


def acting_ledger_keys(records: Iterable[Mapping[str, Any]]) -> set[tuple[str, str, str]]:
    """Fold acting ledger records into their durable dedup keys."""
    keys: set[tuple[str, str, str]] = set()
    for record in records:
        if not isinstance(record, Mapping):
            continue
        keys.add((
            str(record.get("thread_id") or ""),
            str(record.get("item_id") or ""),
            str(record.get("action") or ""),
        ))
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
        timeout=180,
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
    seen = acting_ledger_keys(load_acting_ledger(acting_ledger_path))
    commented: list[dict[str, Any]] = []
    skipped_dedup: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    spawn = spawner or default_spawner

    for item in items:
        ctx = _context_from_item(item)
        key = acting_ledger_key(ctx.repo, ctx.pr_number)
        if key in seen:
            skipped_dedup.append(dict(item))
            continue

        try:
            verdict = spawn(ctx, gh_runner)
        except SpawnerUnconfigured as exc:
            record = _failure_record(ctx, "spawner_unconfigured", exc, clock=clock)
            _log(log_sink, "review_acting_spawner_unconfigured", record)
            append_acting_ledger(acting_ledger_path, record)
            failed.append(record)
            continue
        except Exception as exc:
            record = _failure_record(ctx, "spawn_failed", exc, clock=clock)
            _log(log_sink, "review_acting_spawn_failed", record)
            append_acting_ledger(acting_ledger_path, record)
            failed.append(record)
            continue

        comment_url = post_pr_comment(ctx.repo, ctx.pr_number, verdict, gh_runner=gh_runner)
        if comment_url is None:
            record = _failure_record(ctx, "comment_failed", RuntimeError("comment POST failed"), clock=clock)
            _log(log_sink, "review_acting_comment_failed", record)
            append_acting_ledger(acting_ledger_path, record)
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
