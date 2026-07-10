from __future__ import annotations

import json
import subprocess
from datetime import date, timedelta

import pytest

from creator_engine_validator import ticket_reconcile_feed as feed

_TICKET_REPO = "synthetic-org/synthetic-ops"
_PR_REPO = "synthetic-org/synthetic-code"


class FakeGhRunner:
    def __init__(self, issue_payload, pr_payload, *, pr_rc=0, pr_stderr=""):
        self.issue_payload = issue_payload
        self.pr_payload = pr_payload
        self.pr_rc = pr_rc
        self.pr_stderr = pr_stderr
        self.calls: list[list[str]] = []

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))
        assert kwargs == {"capture_output": True, "text": True, "check": False}
        if command[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(self.issue_payload),
                stderr="",
            )
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                self.pr_rc,
                stdout=json.dumps(self.pr_payload),
                stderr=self.pr_stderr,
            )
        raise AssertionError(f"unexpected command: {command}")


def test_happy_path_collects_live_shapes_and_renders_report_lines():
    runner = FakeGhRunner(
        issue_payload=[{"number": 518, "title": "reconcile feed", "labels": [{"name": "bug"}]}],
        pr_payload=[
            {
                "number": 91,
                "title": "synthetic-ops#518 live adapter",
                "headRefName": "user/ce-518-reconcile-feed",
                "body": "Report-only sweep for synthetic-org/synthetic-ops#518.",
            }
        ],
    )

    tickets, prs = feed.collect_inputs(_TICKET_REPO, _PR_REPO, 14, runner=runner)
    matches = feed.reconcile_stale_tickets(tickets, prs, ticket_repo=_TICKET_REPO)

    assert feed.render_report(matches) == (
        "STALE-OPEN synthetic-ops#518 <- PR#91 (branch+ticket-ref)"
    )


def test_gh_failure_fails_closed_with_command_and_stderr():
    runner = FakeGhRunner(
        issue_payload=[],
        pr_payload=[],
        pr_rc=1,
        pr_stderr="rate limit exceeded",
    )

    with pytest.raises(feed.TicketReconcileFeedError) as excinfo:
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 7, runner=runner)

    message = str(excinfo.value)
    assert "command: gh pr list" in message
    assert "--repo synthetic-org/synthetic-code" in message
    assert "stderr: rate limit exceeded" in message


def test_json_mode_prints_machine_readable_payload(monkeypatch, capsys):
    def fake_collect(ticket_repo, pr_repo, since_days):
        assert (ticket_repo, pr_repo, since_days) == (_TICKET_REPO, _PR_REPO, 3)
        return (
            [feed.OpenTicket(number=519, title="json")],
            [
                feed.MergedPullRequest(
                    number=92,
                    title="json",
                    head_branch="ce-519-json",
                    body="",
                )
            ],
        )

    monkeypatch.setattr(feed, "collect_inputs", fake_collect)

    assert (
        feed.main(
            [
                "--ticket-repo",
                _TICKET_REPO,
                "--pr-repo",
                _PR_REPO,
                "--since-days",
                "3",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["matches"][0]["report_line"] == "STALE-OPEN synthetic-ops#519 <- PR#92 (branch)"


def test_since_days_is_reflected_in_merged_pr_search_window():
    runner = FakeGhRunner(issue_payload=[], pr_payload=[])

    feed.collect_inputs(_TICKET_REPO, _PR_REPO, 11, runner=runner)

    pr_command = runner.calls[1]
    search_value = pr_command[pr_command.index("--search") + 1]
    assert search_value == (
        f"merged:>={(date.today() - timedelta(days=11)).isoformat()}"
    )
    assert "--state" in pr_command
    assert "merged" in pr_command


def test_empty_successful_sweep_is_silent_and_exit_zero(monkeypatch, capsys):
    monkeypatch.setattr(feed, "collect_inputs", lambda *_args: ([], []))

    assert (
        feed.main(
            [
                "--ticket-repo",
                _TICKET_REPO,
                "--pr-repo",
                _PR_REPO,
                "--since-days",
                "30",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_malformed_gh_json_fails_closed_with_command_and_stderr():
    def malformed_runner(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="{", stderr="parse context")

    with pytest.raises(feed.TicketReconcileFeedError) as excinfo:
        feed.collect_inputs(_TICKET_REPO, _PR_REPO, 1, runner=malformed_runner)

    message = str(excinfo.value)
    assert "command: gh issue list" in message
    assert "malformed JSON" in message
    assert "stderr: parse context" in message
