"""Live gh feed adapter for report-only stale ticket reconciliation."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from creator_engine_validator.ticket_reconcile import (
    MergedPullRequest,
    OpenTicket,
    reconcile_stale_tickets,
    render_json,
    render_report,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


class TicketReconcileFeedError(RuntimeError):
    """Operational failure while collecting live reconciliation inputs."""


def collect_inputs(
    ticket_repo: str,
    pr_repo: str,
    since_days: int,
    runner: Runner = subprocess.run,
) -> tuple[list[OpenTicket], list[MergedPullRequest]]:
    """Collect open tickets and recently merged PRs through ``gh``."""

    since_date = _since_date(since_days)
    issue_command = [
        "gh",
        "issue",
        "list",
        "--repo",
        ticket_repo,
        "--state",
        "open",
        "--json",
        "number,title,labels",
        "--limit",
        "1000",
    ]
    pr_command = [
        "gh",
        "pr",
        "list",
        "--repo",
        pr_repo,
        "--state",
        "merged",
        "--search",
        f"merged:>={since_date.isoformat()}",
        "--json",
        "number,title,headRefName,body",
        "--limit",
        "1000",
    ]

    issues, issue_stderr = _run_gh_json(issue_command, runner=runner)
    prs, pr_stderr = _run_gh_json(pr_command, runner=runner)
    return (
        _parse_with_command_context(issues, issue_command, issue_stderr, _parse_tickets),
        _parse_with_command_context(prs, pr_command, pr_stderr, _parse_prs),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ticket-repo",
        required=True,
        help="qualified ticket repository",
    )
    parser.add_argument("--pr-repo", required=True, help="qualified pull request repository")
    parser.add_argument(
        "--since-days",
        required=True,
        type=_non_negative_int,
        help="merged PR lookback window in days",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON",
    )
    args = parser.parse_args(argv)

    try:
        tickets, prs = collect_inputs(args.ticket_repo, args.pr_repo, args.since_days)
        matches = reconcile_stale_tickets(tickets, prs, ticket_repo=args.ticket_repo)
    except TicketReconcileFeedError as exc:
        print(f"ticket-reconcile-feed: {exc}", file=sys.stderr)
        return 2

    output = render_json(matches) if args.json_output else render_report(matches)
    if output:
        print(output)
    return 0


def _run_gh_json(command: list[str], *, runner: Runner) -> tuple[Any, str]:
    try:
        completed = runner(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise TicketReconcileFeedError(_format_failure(command, str(exc))) from exc

    stderr = str(getattr(completed, "stderr", "") or "")
    if getattr(completed, "returncode", 1) != 0:
        raise TicketReconcileFeedError(_format_failure(command, stderr))

    stdout = str(getattr(completed, "stdout", "") or "")
    try:
        return json.loads(stdout), stderr
    except json.JSONDecodeError as exc:
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason=f"malformed JSON: {exc.msg}")
        ) from exc


def _parse_with_command_context(
    data: Any,
    command: Sequence[str],
    stderr: str,
    parser: Callable[[Any], list[OpenTicket] | list[MergedPullRequest]],
) -> list[OpenTicket] | list[MergedPullRequest]:
    try:
        return parser(data)
    except TicketReconcileFeedError as exc:
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason=str(exc))
        ) from exc


def _parse_tickets(data: Any) -> list[OpenTicket]:
    if not isinstance(data, list):
        raise TicketReconcileFeedError("malformed gh issue output: expected a list")
    return [_parse_ticket(item, index) for index, item in enumerate(data)]


def _parse_ticket(item: Any, index: int) -> OpenTicket:
    if not isinstance(item, Mapping):
        raise TicketReconcileFeedError(
            f"malformed gh issue output at index {index}: expected object"
        )
    if "number" not in item or "title" not in item or "labels" not in item:
        raise TicketReconcileFeedError(
            f"malformed gh issue output at index {index}: missing number/title/labels"
        )
    if not isinstance(item["labels"], list):
        raise TicketReconcileFeedError(
            f"malformed gh issue output at index {index}: labels must be a list"
        )
    return OpenTicket(
        number=_positive_int(item["number"], f"issue[{index}].number"),
        title=_text(item["title"]),
    )


def _parse_prs(data: Any) -> list[MergedPullRequest]:
    if not isinstance(data, list):
        raise TicketReconcileFeedError("malformed gh pr output: expected a list")
    return [_parse_pr(item, index) for index, item in enumerate(data)]


def _parse_pr(item: Any, index: int) -> MergedPullRequest:
    if not isinstance(item, Mapping):
        raise TicketReconcileFeedError(f"malformed gh pr output at index {index}: expected object")
    if (
        "number" not in item
        or "title" not in item
        or "headRefName" not in item
        or "body" not in item
    ):
        raise TicketReconcileFeedError(
            f"malformed gh pr output at index {index}: missing number/title/headRefName/body"
        )
    return MergedPullRequest(
        number=_positive_int(item["number"], f"pr[{index}].number"),
        title=_text(item["title"]),
        head_branch=_text(item["headRefName"]),
        body=_text(item["body"]),
    )


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise TicketReconcileFeedError(
            f"malformed gh output: {field} must be a positive integer"
        )
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise TicketReconcileFeedError(
            f"malformed gh output: {field} must be a positive integer"
        ) from exc
    if number <= 0:
        raise TicketReconcileFeedError(
            f"malformed gh output: {field} must be a positive integer"
        )
    return number


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _since_date(since_days: int) -> dt.date:
    if since_days < 0:
        raise TicketReconcileFeedError("since_days must be non-negative")
    return dt.date.today() - dt.timedelta(days=since_days)


def _format_failure(command: Sequence[str], stderr: str, *, reason: str | None = None) -> str:
    parts = [f"command: {shlex.join(command)}"]
    if reason:
        parts.append(reason)
    parts.append(f"stderr: {stderr.strip() or '<empty>'}")
    return "; ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
