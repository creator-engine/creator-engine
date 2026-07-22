"""Complete, report-only GitHub feed for stale ticket reconciliation."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from creator_engine_validator.issue_refs import parse_all_refs
from creator_engine_validator.ticket_reconcile import (
    MergedPullRequest,
    OpenTicket,
    reconcile_stale_tickets,
    render_json,
    render_report,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]
_SCOPED_GH_ENV_EXCLUSIONS = frozenset(
    {
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "CE_OPS_READ_TOKEN",
        "CE_PR_READ_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GH_DEBUG",
        "GH_HOST",
        "GH_CONFIG_DIR",
        "GITHUB_API_URL",
    }
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
    ticket_token_env: str | None = None,
    pr_token_env: str | None = None,
) -> tuple[list[OpenTicket], list[MergedPullRequest]]:
    """Collect complete open-ticket and merged-PR repository connections.

    GitHub search is deliberately not used: its result ceiling cannot prove a
    complete advisory pass.  Every connection page is validated before any
    candidates are returned, then merged PRs are filtered locally against the
    injected UTC clock.
    """

    ticket_token, pr_token = _validate_token_pair(ticket_token, pr_token)
    if since_days < 0:
        raise TicketReconcileFeedError("since_days must be non-negative")
    instant = now if now is not None else dt.datetime.now(dt.timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise TicketReconcileFeedError("now must be timezone-aware")
    cutoff = instant.astimezone(dt.timezone.utc) - dt.timedelta(days=since_days)

    try:
        token_source_names = (ticket_token_env, pr_token_env)
        tickets = _collect_tickets(
            ticket_repo,
            runner=runner,
            token=ticket_token,
            token_source_names=token_source_names,
        )
        prs_with_dates = _collect_prs(
            pr_repo,
            runner=runner,
            token=pr_token,
            token_source_names=token_source_names,
        )
    except TicketReconcileFeedError as exc:
        raise TicketReconcileFeedError(
            _redact_tokens(str(exc), (ticket_token, pr_token))
        ) from None
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
            ticket_token_env=args.ticket_token_env,
            pr_token_env=args.pr_token_env,
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


def _collect_tickets(
    repo: str,
    *,
    runner: Runner,
    token: str,
    token_source_names: Sequence[str | None],
) -> list[OpenTicket]:
    nodes = _collect_connection(
        repo,
        connection_name="issues",
        query=_ISSUES_QUERY,
        runner=runner,
        token=token,
        token_source_names=token_source_names,
    )
    return [_parse_ticket(node, index) for index, node in enumerate(nodes)]


def _collect_prs(
    repo: str,
    *,
    runner: Runner,
    token: str,
    token_source_names: Sequence[str | None],
) -> list[tuple[MergedPullRequest, dt.datetime]]:
    nodes = _collect_connection(
        repo,
        connection_name="pullRequests",
        query=_PRS_QUERY,
        runner=runner,
        token=token,
        token_source_names=token_source_names,
    )
    return [_parse_pr(node, index) for index, node in enumerate(nodes)]


def _collect_connection(
    repo: str,
    *,
    connection_name: str,
    query: str,
    runner: Runner,
    token: str,
    token_source_names: Sequence[str | None],
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
        payload, stderr = _run_gh_json(
            command,
            runner=runner,
            token=token,
            token_source_names=token_source_names,
        )
        connection = _extract_connection(
            payload,
            connection_name=connection_name,
            command=command,
            stderr=stderr,
        )
        page_nodes = connection.get("nodes")
        page_info = connection.get("pageInfo")
        if not isinstance(page_nodes, list) or not isinstance(page_info, Mapping):
            raise TicketReconcileFeedError(
                _format_failure(command, stderr, reason="malformed GraphQL connection")
            )
        has_next = page_info.get("hasNextPage")
        end_cursor = page_info.get("endCursor")
        if type(has_next) is not bool or not (
            end_cursor is None or type(end_cursor) is str
        ):
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
    command: list[str],
    *,
    runner: Runner,
    token: str,
    token_source_names: Sequence[str | None],
) -> tuple[Any, str]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "check": False,
        "env": _scoped_gh_env(token, token_source_names=token_source_names),
    }
    try:
        completed = runner(command, **kwargs)
    except OSError as exc:
        raise TicketReconcileFeedError(
            _format_failure(command, _redact(str(exc), token))
        ) from None

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
) -> Mapping[str, Any]:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise TicketReconcileFeedError(
            _format_failure(command, stderr, reason="malformed GraphQL data")
        )
    rate_limit = data.get("rateLimit")
    if (
        not isinstance(rate_limit, Mapping)
        or type(rate_limit.get("remaining")) is not int
    ):
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
        title=_required_text(item["title"], f"issue[{index}].title"),
    )


def _parse_pr(item: Any, index: int) -> tuple[MergedPullRequest, dt.datetime]:
    required = {"number", "title", "headRefName", "body", "mergedAt"}
    if not isinstance(item, Mapping) or not required.issubset(item):
        raise TicketReconcileFeedError(f"malformed pull request node at index {index}")
    merged_at = _parse_utc_timestamp(item["mergedAt"], f"pr[{index}].mergedAt")
    return (
        MergedPullRequest(
            number=_positive_int(item["number"], f"pr[{index}].number"),
            title=_required_text(item["title"], f"pr[{index}].title"),
            head_branch=_required_text(item["headRefName"], f"pr[{index}].headRefName"),
            body=_required_text(item["body"], f"pr[{index}].body"),
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


def _parse_reference_numbers(title: str, body: str) -> Sequence[int]:
    try:
        values = parse_all_refs(title, body)
    except Exception:
        raise TicketReconcileFeedError("canonical reference parser failed") from None
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TicketReconcileFeedError("canonical reference parser returned malformed output")
    if any(type(value) is not int or value <= 0 for value in values):
        raise TicketReconcileFeedError("canonical reference parser returned malformed output")
    return values


def _required_token(env_name: str) -> str:
    token = os.environ.get(env_name, "")
    if not token:
        raise TicketReconcileFeedError(f"required read token environment is absent: {env_name}")
    return token


def _validate_token_pair(ticket_token: Any, pr_token: Any) -> tuple[str, str]:
    if (
        type(ticket_token) is not str
        or not ticket_token.strip()
        or type(pr_token) is not str
        or not pr_token.strip()
        or ticket_token == pr_token
    ):
        raise TicketReconcileFeedError(
            "ticket and PR read tokens must be nonempty and distinct"
        )
    return ticket_token, pr_token


def _is_app_key_var(name: str) -> bool:
    """Return whether *name* could carry a GitHub App private key."""

    upper = name.upper()
    return upper.endswith("_PEM") or "PRIVATE_KEY" in upper or "APP_KEY" in upper


def _scoped_gh_env(
    token: str, *, token_source_names: Sequence[str | None] = ()
) -> dict[str, str]:
    child = dict(os.environ)
    for name in (*_SCOPED_GH_ENV_EXCLUSIONS, *token_source_names):
        if name is not None:
            child.pop(name, None)
    for name in [name for name in child if _is_app_key_var(name)]:
        child.pop(name, None)
    child["GH_TOKEN"] = token
    return child


def _split_repo(repo: str) -> tuple[str, str]:
    parts = repo.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise TicketReconcileFeedError("repository must be qualified as owner/name")
    return parts[0], parts[1]


def _positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise TicketReconcileFeedError(f"malformed GraphQL output: {field} must be positive")
    return value


def _required_text(value: Any, field: str) -> str:
    if type(value) is not str:
        raise TicketReconcileFeedError(
            f"malformed GraphQL output: {field} must be text"
        )
    return value


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


def _redact_tokens(value: str, tokens: Sequence[str]) -> str:
    for token in sorted(tokens, key=len, reverse=True):
        value = value.replace(token, "<redacted>")
    return value


def _format_failure(command: Sequence[str], stderr: str, *, reason: str | None = None) -> str:
    parts = [f"command: {shlex.join(command)}"]
    if reason:
        parts.append(reason)
    parts.append(f"stderr: {stderr.strip() or '<empty>'}")
    return "; ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
