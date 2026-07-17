from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ticket_reconcile_feed as feed

_TICKET_REPO = "synthetic-org/synthetic-ops"
_PR_REPO = "synthetic-org/synthetic-code"
_NOW = dt.datetime(2026, 7, 17, 12, 0, tzinfo=dt.timezone.utc)
_WORKFLOW = (
    Path(__file__).resolve().parents[3]
    / ".github/workflows/ce-ops-stale-ticket-reconcile.yml"
)


def _page(nodes, *, has_next=False, cursor=None):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": has_next, "endCursor": cursor}}


class FakeGraphqlRunner:
    def __init__(self, issue_pages, pr_pages):
        self.pages = {"issues": list(issue_pages), "pullRequests": list(pr_pages)}
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, command, **kwargs):
        command = list(command)
        self.calls.append((command, kwargs))
        query = next(value[6:] for value in command if value.startswith("query="))
        connection = "issues" if "issues(first:" in query else "pullRequests"
        page = self.pages[connection].pop(0)
        payload = {
            "data": {
                "repository": {connection: page},
                "rateLimit": {"remaining": 99},
            }
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")


def _pr(number: int, merged_at: str, *, branch: str | None = None, body: str = ""):
    return {
        "number": number,
        "title": f"PR {number}",
        "headRefName": branch or f"ce-{number}-change",
        "body": body,
        "mergedAt": merged_at,
    }


def test_complete_cursor_traversal_and_local_utc_date_filter_avoid_search_ceiling():
    runner = FakeGraphqlRunner(
        [
            _page([{"number": 518, "title": "one"}], has_next=True, cursor="I1"),
            _page([{"number": 519, "title": "two"}]),
        ],
        [
            _page([_pr(90, "2025-07-17T11:59:59Z")], has_next=True, cursor="P1"),
            _page(
                [
                    _pr(91, "2025-07-17T12:00:00Z"),
                    _pr(92, "2026-07-17T12:00:00+00:00"),
                ]
            ),
        ],
    )

    tickets, prs = feed.collect_inputs(
        _TICKET_REPO, _PR_REPO, 365, runner=runner, now=_NOW
    )

    assert [ticket.number for ticket in tickets] == [518, 519]
    assert [pr.number for pr in prs] == [91, 92]
    commands = [call[0] for call in runner.calls]
    assert len(commands) == 4
    assert all("--search" not in command and "--limit" not in command for command in commands)
    assert any("cursor=I1" in command for command in commands)
    assert any("cursor=P1" in command for command in commands)
    assert all(
        "pageInfo" in next(value[6:] for value in command if value.startswith("query="))
        for command in commands
    )


@pytest.mark.parametrize(
    "page, reason",
    [
        ({"nodes": [], "pageInfo": {}}, "malformed GraphQL pageInfo"),
        (_page([], has_next=True, cursor=None), "incomplete GraphQL pagination"),
        ({"nodes": "wrong", "pageInfo": {"hasNextPage": False}}, "malformed GraphQL connection"),
    ],
)
def test_malformed_or_incomplete_page_fails_closed(page, reason):
    runner = FakeGraphqlRunner([page], [_page([])])

    with pytest.raises(feed.TicketReconcileFeedError, match=reason):
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 1, runner=runner, now=_NOW)


def test_repeated_cursor_fails_closed():
    runner = FakeGraphqlRunner(
        [_page([], has_next=True, cursor="same"), _page([], has_next=True, cursor="same")],
        [_page([])],
    )

    with pytest.raises(feed.TicketReconcileFeedError, match="incomplete GraphQL pagination"):
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 1, runner=runner, now=_NOW)


def test_graphql_rate_limit_and_authentication_fail_closed():
    def rate_limited(command, **_kwargs):
        payload = {
            "data": {
                "repository": {"issues": _page([])},
                "rateLimit": {"remaining": 0},
            }
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    with pytest.raises(feed.TicketReconcileFeedError, match="rate limit exhausted"):
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 1, runner=rate_limited, now=_NOW)

    def unauthorized(command, **_kwargs):
        payload = {"errors": [{"type": "FORBIDDEN", "message": "denied"}]}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    with pytest.raises(feed.TicketReconcileFeedError, match="authentication/rate-limit"):
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 1, runner=unauthorized, now=_NOW)


def test_nonzero_and_malformed_json_fail_closed_without_leaking_token():
    secret = "ghp_top_secret_value"

    def failed(command, **_kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr=f"denied {secret}")

    with pytest.raises(feed.TicketReconcileFeedError) as excinfo:
        feed.collect_inputs(
            _TICKET_REPO,
            _PR_REPO,
            1,
            runner=failed,
            now=_NOW,
            ticket_token=secret,
        )
    assert secret not in str(excinfo.value)
    assert "<redacted>" in str(excinfo.value)

    def malformed(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="{", stderr="context")

    with pytest.raises(feed.TicketReconcileFeedError, match="malformed JSON"):
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 1, runner=malformed, now=_NOW)


def test_ticket_and_pr_credentials_are_isolated_in_child_environments(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ambient")
    monkeypatch.setenv("GITHUB_TOKEN", "also-ambient")
    monkeypatch.setenv("CE_OPS_READ_TOKEN", "parent-ticket")
    monkeypatch.setenv("CE_PR_READ_TOKEN", "parent-pr")
    runner = FakeGraphqlRunner([_page([])], [_page([])])

    feed.collect_inputs(
        _TICKET_REPO,
        _PR_REPO,
        1,
        runner=runner,
        now=_NOW,
        ticket_token="ticket-only",
        pr_token="pr-only",
    )

    ticket_env = runner.calls[0][1]["env"]
    pr_env = runner.calls[1][1]["env"]
    assert ticket_env["GH_TOKEN"] == "ticket-only"
    assert pr_env["GH_TOKEN"] == "pr-only"
    for child_env in (ticket_env, pr_env):
        assert "GITHUB_TOKEN" not in child_env
        assert "CE_OPS_READ_TOKEN" not in child_env
        assert "CE_PR_READ_TOKEN" not in child_env
    assert all("ticket-only" not in " ".join(call[0]) for call in runner.calls)
    assert all("pr-only" not in " ".join(call[0]) for call in runner.calls)


def test_parser_loader_uses_dynamic_file_seam_and_fails_closed(tmp_path, monkeypatch):
    parser_path = tmp_path / "parse_issue_refs.py"
    parser_path.write_text("def parse_all_refs(title, body):\n    return [7]\n", encoding="utf-8")

    parser = feed._load_reference_parser(parser_path)
    assert parser("title", "body") == [7]
    assert feed._load_reference_parser(parser_path) is parser

    with pytest.raises(feed.TicketReconcileFeedError, match="parser absent"):
        feed._load_reference_parser(tmp_path / "missing.py")

    broken_path = tmp_path / "broken.py"
    broken_path.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    with pytest.raises(feed.TicketReconcileFeedError, match="parser load failed"):
        feed._load_reference_parser(broken_path)

    def broken_parser(*_args):
        raise RuntimeError("bad parse")

    monkeypatch.setattr(feed, "_load_reference_parser", lambda: broken_parser)
    with pytest.raises(feed.TicketReconcileFeedError, match="parser failed"):
        feed._parse_reference_numbers("title", "body")


def test_production_parser_visibility_matches_title_closing_and_bare_body_contract():
    feed._load_reference_parser.cache_clear()

    assert feed._parse_reference_numbers("feat: ce-518 canonical", "") == [518]
    assert feed._parse_reference_numbers("unrelated", "Closes ce-ops#519") == [519]
    assert feed._parse_reference_numbers("unrelated", "Context only: ce-ops#520") == []


@pytest.mark.parametrize(
    "issue_nodes,pr_nodes,reason",
    [
        ([{"number": 1}], [], "malformed issue node"),
        ([], [{"number": 2}], "malformed pull request node"),
        ([], [_pr(2, "not-a-date")], "must be a timestamp"),
    ],
)
def test_malformed_nodes_fail_closed(issue_nodes, pr_nodes, reason):
    runner = FakeGraphqlRunner([_page(issue_nodes)], [_page(pr_nodes)])

    with pytest.raises(feed.TicketReconcileFeedError, match=reason):
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 1, runner=runner, now=_NOW)


def test_complete_zero_match_json_is_valid_and_raw_pr_body_is_not_emitted(monkeypatch, capsys):
    monkeypatch.setenv("CE_OPS_READ_TOKEN", "ticket")
    monkeypatch.setenv("CE_PR_READ_TOKEN", "pr")
    monkeypatch.setattr(
        feed,
        "collect_inputs",
        lambda *_args, **_kwargs: (
            [feed.OpenTicket(number=518)],
            [feed.MergedPullRequest(number=90, head_branch="unrelated", body="RAW-SECRET-BODY")],
        ),
    )
    monkeypatch.setattr(feed, "_parse_reference_numbers", lambda _title, _body: [])

    assert (
        feed.main(
            [
                "--ticket-repo",
                _TICKET_REPO,
                "--pr-repo",
                _PR_REPO,
                "--since-days",
                "365",
                "--json",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"matches": []}
    assert "RAW-SECRET-BODY" not in captured.out + captured.err


def test_missing_token_fails_before_collection(monkeypatch, capsys):
    monkeypatch.delenv("CE_OPS_READ_TOKEN", raising=False)
    monkeypatch.setenv("CE_PR_READ_TOKEN", "pr")

    assert (
        feed.main(
            [
                "--ticket-repo",
                _TICKET_REPO,
                "--pr-repo",
                _PR_REPO,
                "--since-days",
                "1",
                "--json",
            ]
        )
        == 2
    )
    assert "required read token environment is absent" in capsys.readouterr().err


def test_workflow_is_daily_manual_dry_run_only_and_fail_closed_for_artifacts():
    text = _WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    trigger = workflow.get("on", workflow.get(True))
    assert set(trigger) == {"schedule", "workflow_dispatch"}
    assert trigger["schedule"] == [{"cron": "17 3 * * *"}]
    assert trigger["workflow_dispatch"] is None
    assert workflow["permissions"] == {"contents": "read", "pull-requests": "read"}

    job = workflow["jobs"]["stale-ticket-reconcile"]
    checkout = job["steps"][0]
    assert checkout["with"]["persist-credentials"] is False
    scan = next(step for step in job["steps"] if step["name"] == "Build complete advisory")
    assert scan["env"] == {
        "CE_OPS_READ_TOKEN": "${{ secrets.CE_OPS_READ_TOKEN }}",
        "CE_PR_READ_TOKEN": "${{ github.token }}",
    }
    assert "--json" in scan["run"] and "> \"${report}\"" in scan["run"]
    upload = next(step for step in job["steps"] if step["name"] == "Upload advisory")
    assert upload["if"] == "${{ success() }}"
    assert upload["with"]["if-no-files-found"] == "error"

    lowered = text.lower()
    for forbidden in (
        "issues: write",
        "pull-requests: write",
        "gh issue close",
        "gh issue comment",
        "gh issue edit",
        "gh pr review",
        "gh pr merge",
        "--apply",
    ):
        assert forbidden not in lowered
