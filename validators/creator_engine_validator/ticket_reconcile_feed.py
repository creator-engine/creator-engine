"""Complete, report-only GitHub feed for stale ticket reconciliation."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from creator_engine_validator.ticket_reconcile import (
    MergedPullRequest,
    OpenTicket,
    reconcile_stale_tickets,
    render_json,
    render_report,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]
ReferenceParser = Callable[[str, str], Sequence[int]]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PARSER_PATH = _REPO_ROOT / "tools" / "ce-ops-autoclose" / "parse_issue_refs.py"
_TOKEN_ENV_NAMES = frozenset(
    {"GH_TOKEN", "GITHUB_TOKEN", "CE_OPS_READ_TOKEN", "CE_PR_READ_TOKEN"}
)

_ISSUES_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, after: $cursor, states: OPEN, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes { number title }
    }
  }
  rateLimit { remaining }
}
""".strip()

_PRS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(
      first: 100
      after: $cursor
      states: MERGED
      orderBy: {field: CREATED_AT, direction: ASC}
    ) {
      pageInfo { hasNextPage endCursor }
      nodes { number title headRefName body mergedAt }
    }
  }
  rateLimit { remaining }
}
""".strip()


class TicketReconcileFeedError(RuntimeError):
    """Operational failure while collecting live reconciliation inputs."""


def collect_inputs(
    ticket_repo: str,
    pr_repo: str,
    since_days: int,
    runner: Runner = subprocess.run,
    *,
    now: dt.datetime | None = None,
    ticket_token: str | None = None,
    pr_token: str | None = None,
) -> tuple[list[OpenTicket], list[MergedPullRequest]]:
    """Collect complete open-ticket and merged-PR repository connections.

    GitHub search is deliberately not used: its result ceiling cannot prove a
    complete advisory pass.  Every connection page is validated before any
    candidates are returned, then merged PRs are filtered locally against the
    injected UTC clock.
    """

    if since_days < 0:
        raise TicketReconcileFeedError("since_days must be non-negative")
    instant = now if now is not None else dt.datetime.now(dt.timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise TicketReconcileFeedError("now must be timezone-aware")
    cutoff = instant.astimezone(dt.timezone.utc) - dt.timedelta(days=since_days)

    tickets = _collect_tickets(ticket_repo, runner=runner, token=ticket_token)
    prs_with_dates = _collect_prs(pr_repo, runner=runner, token=pr_token)
    prs = [pr for pr, merged_at in prs_with_dates if merged_at >= cutoff]
    return tickets, prs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticket-repo", required=True, help="qualified ticket repository")
    parser.add_argument("--pr-repo", required=True, help="qualified pull request repository")
    parser.add_argument(
        "--since-days",
        required=True,
        type=_non_negative_int,
        help="merged PR lookback window in days",
    )
    parser.add_argument(
        "--ticket-token-env",
        default="CE_OPS_READ_TOKEN",
        help="environment variable holding the ticket-repository read token",
    )
    parser.add_argument(
        "--pr-token-env",
        default="CE_PR_READ_TOKEN",
        help="environment variable holding the PR-repository read token",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="emit normalized JSON"
    )
    args = parser.parse_args(argv)

    try:
        ticket_token = _required_token(args.ticket_token_env)
        pr_token = _required_token(args.pr_token_env)
        tickets, prs = collect_inputs(
            args.ticket_repo,
            args.pr_repo,
            args.since_days,
            ticket_token=ticket_token,
            pr_token=pr_token,
        )
        matches = reconcile_stale_tickets(
            tickets,
            prs,
            ticket_repo=args.ticket_repo,
            reference_numbers=_parse_reference_numbers,
        )
    except (TicketReconcileFeedError, TypeError, ValueError) as exc:
        print(f"ticket-reconcile-feed: {exc}", file=sys.stderr)
        return 2

    output = render_json(matches) if args.json_output else render_report(matches)
    if output:
        print(output)
    return 0


def _collect_tickets(repo: str, *, runner: Runner, token: str | None) -> list[OpenTicket]:
    nodes = _collect_connection(
        repo,
        connection_name="issues",
        query=_ISSUES_QUERY,
        runner=runner,
        token=token,
    )
    return [_parse_ticket(node, index) for index, node in enumerate(nodes)]


def _collect_prs(
    repo: str, *, runner: Runner, token: str | None
) -> list[tuple[MergedPullRequest, dt.datetime]]:
    nodes = _collect_connection(
        repo,
        connection_name="pullRequests",
        query=_PRS_QUERY,
        runner=runner,
        token=token,
    )
    return [_parse_pr(node, index) for index, node in enumerate(nodes)]


def _collect_connection(
    repo: str,
    *,
    connection_name: str,
    query: str,
    runner: Runner,
    token: str | None,
) -> list[Any]:
    owner, name = _split_repo(repo)
    cursor: str | None = None
    seen_cursors: set[str] = set()
    nodes: list[Any] = []

    while True:
        command = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
        ]
        if cursor is not None:
            command.extend(["-F", f"cursor={cursor}"])
        payload, stderr = _run_gh_json(command, runner=runner, token=token)
        connection = _extract_connection(
            payload,
            connection_name=connection_name,
            command=command,
            stderr=stderr,
            token=token,
        )
        page_nodes = connection.get("nodes")
        page_info = connection.get("pageInfo")
        if not isinstance(page_nodes, list) or not isinstance(page_info, Mapping):
            raise TicketReconcileFeedError(
                _format_failure(command, stderr, reason="malformed GraphQL connection")
            )
        has_next = page_info.get("hasNextPage")
        end_cursor = page_info.get("endCursor")
        if not isinstance(has_next, bool):
            raise TicketReconcileFeedError(
                _format_failure(command, stderr, reason="malformed GraphQL pageInfo")
            )

        nodes.extend(page_nodes)
        if not has_next:
            break
        if not isinstance(end_cursor, str) or not end_cursor or end_cursor in seen_cursors:
            raise TicketReconcileFeedError(
                _format_failure(command, stderr, reason="incomplete GraphQL pagination")
            )
        seen_cursors.add(end_cursor)
        cursor = end_cursor

    return nodes


def _run_gh_json(
    command: list[str], *, runner: Runner, token: str | None
) -> tuple[Any, str]:
    kwargs: dict[str, Any] = {"capture_output": True, "text": True, "check": False}
    if token is not None:
        kwargs["env"] = _scoped_gh_env(token)
    try:
        completed = runner(command, **kwargs)
    except OSError as exc:
        raise TicketReconcileFeedError(_format_failure(command, str(exc))) from exc

    stderr = _redact(str(getattr(completed, "stderr", "") or ""), token)
    if getattr(completed, "returncode", 1) != 0:
        raise TicketReconcileFeedError(_format_failure(command, stderr))

    stdout = str(getattr(completed, "stdout", "") or "")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason=f"malformed JSON: {exc.msg}")
        ) from exc
    if not isinstance(payload, Mapping):
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="malformed GraphQL response")
        )
    errors = payload.get("errors")
    if errors:
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="GraphQL authentication/rate-limit error")
        )
    return payload, stderr


def _extract_connection(
    payload: Mapping[str, Any],
    *,
    connection_name: str,
    command: Sequence[str],
    stderr: str,
    token: str | None,
) -> Mapping[str, Any]:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="malformed GraphQL data")
        )
    rate_limit = data.get("rateLimit")
    if not isinstance(rate_limit, Mapping) or not isinstance(rate_limit.get("remaining"), int):
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="malformed GraphQL rateLimit")
        )
    if rate_limit["remaining"] <= 0:
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="GraphQL rate limit exhausted")
        )
    repository = data.get("repository")
    if not isinstance(repository, Mapping):
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="repository unavailable or unauthorized")
        )
    connection = repository.get(connection_name)
    if not isinstance(connection, Mapping):
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="malformed GraphQL repository response")
        )
    return connection


def _parse_ticket(item: Any, index: int) -> OpenTicket:
    if not isinstance(item, Mapping) or "number" not in item or "title" not in item:
        raise TicketReconcileFeedError(f"malformed issue node at index {index}")
    return OpenTicket(
        number=_positive_int(item["number"], f"issue[{index}].number"),
        title=_text(item["title"]),
    )


def _parse_pr(item: Any, index: int) -> tuple[MergedPullRequest, dt.datetime]:
    required = {"number", "title", "headRefName", "body", "mergedAt"}
    if not isinstance(item, Mapping) or not required.issubset(item):
        raise TicketReconcileFeedError(f"malformed pull request node at index {index}")
    merged_at = _parse_utc_timestamp(item["mergedAt"], f"pr[{index}].mergedAt")
    return (
        MergedPullRequest(
            number=_positive_int(item["number"], f"pr[{index}].number"),
            title=_text(item["title"]),
            head_branch=_text(item["headRefName"]),
            body=_text(item["body"]),
        ),
        merged_at,
    )


def _parse_utc_timestamp(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise TicketReconcileFeedError(f"malformed GraphQL output: {field} must be a timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TicketReconcileFeedError(
            f"malformed GraphQL output: {field} must be a timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TicketReconcileFeedError(f"malformed GraphQL output: {field} must include timezone")
    return parsed.astimezone(dt.timezone.utc)


@lru_cache(maxsize=1)
def _load_reference_parser(path: Path = _PARSER_PATH) -> ReferenceParser:
    """Load the shared parser once using the production file-loader seam."""

    if not path.is_file():
        raise TicketReconcileFeedError(f"canonical reference parser absent: {path}")
    try:
        spec = importlib.util.spec_from_file_location("ce_ops_parse_issue_refs", path)
        if spec is None or spec.loader is None:
            raise ImportError("parser module spec has no loader")
        module: ModuleType = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        parser = getattr(module, "parse_all_refs")
    except Exception as exc:
        raise TicketReconcileFeedError(f"canonical reference parser load failed: {exc}") from exc
    if not callable(parser):
        raise TicketReconcileFeedError("canonical reference parser has no parse_all_refs callable")
    return parser


def _parse_reference_numbers(title: str, body: str) -> Sequence[int]:
    try:
        values = _load_reference_parser()(title, body)
    except TicketReconcileFeedError:
        raise
    except Exception as exc:
        raise TicketReconcileFeedError(f"canonical reference parser failed: {exc}") from exc
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TicketReconcileFeedError("canonical reference parser returned malformed output")
    return values


def _required_token(env_name: str) -> str:
    token = os.environ.get(env_name, "")
    if not token:
        raise TicketReconcileFeedError(f"required read token environment is absent: {env_name}")
    return token


def _scoped_gh_env(token: str) -> dict[str, str]:
    child = dict(os.environ)
    for name in _TOKEN_ENV_NAMES:
        child.pop(name, None)
    child["GH_TOKEN"] = token
    return child


def _split_repo(repo: str) -> tuple[str, str]:
    parts = repo.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise TicketReconcileFeedError("repository must be qualified as owner/name")
    return parts[0], parts[1]


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise TicketReconcileFeedError(f"malformed GraphQL output: {field} must be positive")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise TicketReconcileFeedError(
            f"malformed GraphQL output: {field} must be positive"
        ) from exc
    if number <= 0:
        raise TicketReconcileFeedError(f"malformed GraphQL output: {field} must be positive")
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


def _redact(value: str, token: str | None) -> str:
    return value.replace(token, "<redacted>") if token else value


def _format_failure(command: Sequence[str], stderr: str, *, reason: str | None = None) -> str:
    parts = [f"command: {shlex.join(command)}"]
    if reason:
        parts.append(reason)
    parts.append(f"stderr: {stderr.strip() or '<empty>'}")
    return "; ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
