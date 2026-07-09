"""Dry-run observation layer for controller review pickup.

This module wraps ``forge.review_pickup`` in advisory mode. It emits named JSONL
decisions for controller inspection and adds an Operator-held gate without
performing GitHub write operations.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from .review_pickup import (
    DEFAULT_REVIEW_PICKUP_PER_PAGE,
    LogSink,
    poll_review_pickup,
)
from ..pickup_search import GhRunner, PickupError, PickupRateLimited, Transport


class WouldAssignDecision(TypedDict):
    event: str
    repo: str
    pr: int
    head_sha: str
    assigned_reviewer: str
    reason: str
    ts: str


class WouldSkipDecision(TypedDict):
    event: str
    repo: str
    pr: int
    head_sha: str | None
    skip_reason: str
    ts: str


DryRunDecision = WouldAssignDecision | WouldSkipDecision


class _SkippedRecord(TypedDict):
    repo: NotRequired[str]
    number: NotRequired[int]
    pr: NotRequired[int]
    head_sha: NotRequired[str | None]
    reason: NotRequired[str]


def is_operator_held(
    repo: str,
    pr_number: int,
    gh_runner: GhRunner,
    *,
    held_label: str = "awaiting-operator",
    held_list_path: str | Path | None = None,
    log_sink: LogSink | None = None,
) -> bool:
    """Return whether a PR is held out of autonomous review routing."""

    if _label_check_matches(repo, pr_number, gh_runner, held_label=held_label, log_sink=log_sink):
        return True
    if held_list_path is not None and _held_list_matches(repo, pr_number, Path(held_list_path)):
        return True
    return False


def run_dry_run_pass(
    *,
    token: str,
    reviewer_seats: Sequence[str],
    gh_runner: GhRunner,
    transport: Transport | None = None,
    repo: str | None = None,
    org: str | None = None,
    per_page: int = DEFAULT_REVIEW_PICKUP_PER_PAGE,
    held_label: str = "awaiting-operator",
    held_list_path: str | Path | None = None,
    feed_path: str | Path | None = None,
    log_sink: LogSink | None = None,
    rate_limiter: Any = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime | str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run one read-only review-pickup pass and emit WOULD_* decisions."""

    result = poll_review_pickup(
        token=token,
        reviewer_seats=reviewer_seats,
        gh_runner=gh_runner,
        transport=transport,
        repo=repo,
        org=org,
        per_page=per_page,
        apply=False,
        dry_run=True,
        log_sink=log_sink,
        rate_limiter=rate_limiter,
        sleep=sleep,
    )

    would_assign: list[dict[str, Any]] = []
    would_skip: list[dict[str, Any]] = []

    for item in result.items:
        ts = _timestamp(clock)
        item_repo = str(item.get("repo") or "")
        number = int(item.get("number") or item.get("pr") or 0)
        head_sha = str(item.get("head_sha") or "")
        if is_operator_held(
            item_repo,
            number,
            gh_runner,
            held_label=held_label,
            held_list_path=held_list_path,
            log_sink=log_sink,
        ):
            would_skip.append({
                "event": "WOULD_SKIP",
                "repo": item_repo,
                "pr": number,
                "head_sha": head_sha,
                "skip_reason": "operator_held",
                "ts": ts,
            })
            continue
        would_assign.append({
            "event": "WOULD_ASSIGN",
            "repo": item_repo,
            "pr": number,
            "head_sha": head_sha,
            "assigned_reviewer": str(item.get("assigned_reviewer") or ""),
            "reason": str(item.get("reason") or ""),
            "ts": ts,
        })

    for entry in result.skipped:
        would_skip.append(_skip_decision(entry, clock=clock))

    if feed_path is not None:
        feed = Path(feed_path)
        for decision in [*would_assign, *would_skip]:
            append_dry_run_decision(feed, decision)

    return would_assign, would_skip


def run_dry_run_loop(
    *,
    token: str,
    reviewer_seats: Sequence[str],
    gh_runner: GhRunner,
    transport: Transport | None = None,
    repo: str | None = None,
    org: str | None = None,
    per_page: int = DEFAULT_REVIEW_PICKUP_PER_PAGE,
    held_label: str = "awaiting-operator",
    held_list_path: str | Path | None = None,
    feed_path: str | Path | None = None,
    log_sink: LogSink | None = None,
    rate_limiter: Any = None,
    interval: float = 120.0,
    iterations: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime | str] | None = None,
) -> list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    """Run dry-run passes in bounded or daemon mode."""

    if iterations is not None and iterations < 1:
        raise PickupError("review dry-run loop requires iterations >= 1")
    if iterations is None and interval <= 0:
        raise PickupError("review dry-run loop requires interval > 0")

    passes: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
    index = 0
    while iterations is None or index < iterations:
        index += 1
        try:
            passes.append(run_dry_run_pass(
                token=token,
                reviewer_seats=reviewer_seats,
                gh_runner=gh_runner,
                transport=transport,
                repo=repo,
                org=org,
                per_page=per_page,
                held_label=held_label,
                held_list_path=held_list_path,
                feed_path=feed_path,
                log_sink=log_sink,
                rate_limiter=rate_limiter,
                sleep=sleep,
                clock=clock,
            ))
        except PickupRateLimited as exc:
            _log_event(
                log_sink,
                "review_dry_run_rate_limited",
                index=index,
                **exc.to_payload(),
            )
        if iterations is not None and index >= iterations:
            break
        sleep(interval)
    return passes


def append_dry_run_decision(path: str | Path, decision: Mapping[str, Any]) -> None:
    """Append one JSONL dry-run decision."""

    feed_path = Path(path)
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    with feed_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(decision), sort_keys=True) + "\n")


def _label_check_matches(
    repo: str,
    pr_number: int,
    gh_runner: GhRunner,
    *,
    held_label: str,
    log_sink: LogSink | None,
) -> bool:
    path = f"repos/{repo}/issues/{pr_number}/labels"
    proc = gh_runner(["gh", "api", "--method", "GET", path], None)
    if getattr(proc, "returncode", 1) != 0:
        _log_event(
            log_sink,
            "review_dry_run_operator_label_read_failed",
            repo=repo,
            pr=pr_number,
            stderr=(getattr(proc, "stderr", "") or "").strip()[:200],
        )
        return False
    raw = (getattr(proc, "stdout", "") or "").strip()
    try:
        labels = json.loads(raw) if raw else []
    except json.JSONDecodeError as exc:
        _log_event(
            log_sink,
            "review_dry_run_operator_label_read_failed",
            repo=repo,
            pr=pr_number,
            error=str(exc),
        )
        return False
    if not isinstance(labels, list):
        _log_event(
            log_sink,
            "review_dry_run_operator_label_read_failed",
            repo=repo,
            pr=pr_number,
            error="labels payload was not a list",
        )
        return False
    return any(isinstance(label, Mapping) and label.get("name") == held_label for label in labels)


def _held_list_matches(repo: str, pr_number: int, held_list_path: Path) -> bool:
    if not held_list_path.exists():
        return False
    try:
        lines = held_list_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.isdigit() and int(line) == pr_number:
            return True
        if "#" not in line:
            continue
        listed_repo, raw_number = line.rsplit("#", 1)
        if listed_repo == repo and raw_number.isdigit() and int(raw_number) == pr_number:
            return True
    return False


def _skip_decision(
    entry: Mapping[str, Any],
    *,
    clock: Callable[[], datetime | str] | None,
) -> dict[str, Any]:
    number = entry.get("number", entry.get("pr"))
    return {
        "event": "WOULD_SKIP",
        "repo": str(entry.get("repo") or ""),
        "pr": int(number or 0),
        "head_sha": entry.get("head_sha"),
        "skip_reason": str(entry.get("reason") or "pickup_refused"),
        "ts": _timestamp(clock),
    }


def _timestamp(clock: Callable[[], datetime | str] | None = None) -> str:
    value = clock() if clock is not None else datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise PickupError("review dry-run clock returned no timestamp")


def _log_event(log_sink: LogSink | None, event: str, **fields: Any) -> None:
    if log_sink is None:
        return
    payload = {"event": event, **{k: v for k, v in fields.items() if v is not None}}
    log_sink(payload)
