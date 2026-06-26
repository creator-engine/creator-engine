import json
import subprocess

import pytest

from creator_engine_validator import v3_cli
from creator_engine_validator.forge import controller_inbox


def _cp(argv, payload, returncode=0, stderr=""):
    return subprocess.CompletedProcess(argv, returncode, stdout=json.dumps(payload), stderr=stderr)


def _pr(
    number,
    *,
    repo="o/r",
    title=None,
    author="author-a",
    review="REVIEW_REQUIRED",
    merge="CLEAN",
    checks="SUCCESS",
    requested=None,
    labels=None,
    body="",
    draft=False,
    queue_numbers=(),
):
    return {
        "number": number,
        "title": title or f"PR {number}",
        "url": f"https://github.com/{repo}/pull/{number}",
        "body": body,
        "isDraft": draft,
        "reviewDecision": review,
        "mergeStateStatus": merge,
        "mergeable": "MERGEABLE",
        "author": {"login": author},
        "repository": {
            "nameWithOwner": repo,
            "mergeQueue": {
                "entries": {
                    "pageInfo": {"hasNextPage": False},
                    "nodes": [
                        {"pullRequest": {"number": queued, "repository": {"nameWithOwner": repo}}}
                        for queued in queue_numbers
                    ],
                }
            },
        },
        "labels": {"nodes": [{"name": label} for label in labels or ()]},
        "requestedReviewers": {"nodes": [{"login": login} for login in requested or ()]},
        "commits": {"nodes": [{"commit": {"oid": "a" * 40, "statusCheckRollup": {"state": checks}}}]},
    }


def _payload(*prs):
    return {
        "data": {
            "search": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": list(prs),
            }
        }
    }


class FakeGh:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, argv, input_text=None):
        self.calls.append((list(argv), input_text))
        return _cp(argv, self.payload)


def test_controller_inbox_classifies_all_buckets_and_uses_merge_queue_entries():
    fake = FakeGh(
        _payload(
            _pr(1, title="needs controller review", requested=["ce-dev-2"]),
            _pr(2, title="self-authored review", author="ce-dev-2", requested=["ce-dev-2"]),
            _pr(3, title="approved green clean unqueued", review="APPROVED"),
            _pr(4, title="approved green clean queued", review="APPROVED", queue_numbers=[4]),
            _pr(5, title="behind branch", review="APPROVED", merge="BEHIND"),
            _pr(6, title="dirty branch", review="APPROVED", merge="DIRTY"),
            _pr(7, title="body hold", body="Plan ready.\n\nAWAITING-OPERATOR: confirm"),
            _pr(8, title="label hold", labels=["hold"]),
        )
    )

    result = controller_inbox.collect_controller_inbox(
        repo="o/r",
        controller_login="ce-dev-2",
        gh_runner=fake,
    )

    assert result.counts == {
        "needs_review": 1,
        "stranded": 1,
        "needs_rebase": 2,
        "awaiting_operator": 2,
    }
    assert [pr.number for pr in result.buckets["needs_review"]] == [1]
    assert [pr.number for pr in result.buckets["stranded"]] == [3]
    assert [pr.number for pr in result.buckets["needs_rebase"]] == [5, 6]
    assert [pr.number for pr in result.buckets["awaiting_operator"]] == [7, 8]
    assert result.buckets["stranded"][0].queued is False

    argv = fake.calls[0][0]
    query_arg = next(item for item in argv if item.startswith("query="))
    assert "repository{nameWithOwner mergeQueue{entries" in query_arg
    assert "commits(last:1){nodes{commit{oid statusCheckRollup{state}}}} mergeQueue" not in query_arg
    assert "autoMergeRequest" not in query_arg
    assert "searchQuery=repo:o/r is:pr is:open" in argv


def test_controller_inbox_refuses_unscoped_and_bad_repo():
    with pytest.raises(controller_inbox.ControllerInboxError, match="unscoped"):
        controller_inbox.collect_controller_inbox(gh_runner=FakeGh(_payload()))
    with pytest.raises(controller_inbox.ControllerInboxError, match="owner/name"):
        controller_inbox.collect_controller_inbox(repo="not-a-repo", gh_runner=FakeGh(_payload()))


def test_controller_inbox_table_is_stable():
    result = controller_inbox.ControllerInboxResult(
        scope=controller_inbox.InboxScope("repo", "o/r"),
        controller_login="ce-dev-2",
        buckets=controller_inbox.classify_pull_requests(
            [
                controller_inbox.InboxPullRequest(
                    repo="o/r",
                    number=9,
                    title="Needs review",
                    url="https://github.com/o/r/pull/9",
                    author="author-a",
                    review_decision="REVIEW_REQUIRED",
                    merge_state_status="CLEAN",
                    rollup_state="SUCCESS",
                    is_draft=False,
                    labels=(),
                    requested_reviewers=("ce-dev-2",),
                    queued=False,
                    hold_marker=False,
                )
            ],
            controller_login="ce-dev-2",
        ),
    )

    assert controller_inbox.format_table(result).splitlines() == [
        "BUCKET       PR    AUTHOR   REVIEW          MERGE CHECKS  QUEUED TITLE       ",
        "------------ ----- -------- --------------- ----- ------- ------ ------------",
        "needs_review o/r#9 author-a REVIEW_REQUIRED CLEAN SUCCESS no     Needs review",
    ]


def test_controller_inbox_cli_json(monkeypatch, capsys):
    captured = {}

    def fake_collect(**kwargs):
        captured.update(kwargs)
        return controller_inbox.ControllerInboxResult(
            scope=controller_inbox.InboxScope("repo", "o/r"),
            controller_login=kwargs["controller_login"],
            buckets={bucket: () for bucket in controller_inbox.BUCKET_ORDER},
        )

    monkeypatch.setattr(v3_cli.controller_inbox, "token_from_env", lambda name: "ghp_fake")
    monkeypatch.setattr(v3_cli.controller_inbox, "gh_runner_with_token", lambda token: "runner")
    monkeypatch.setattr(v3_cli.controller_inbox, "collect_controller_inbox", fake_collect)

    ret = v3_cli.main([
        "inbox",
        "--repo", "o/r",
        "--controller-login", "ce-controller",
        "--json",
    ])

    assert ret == 0
    assert captured["repo"] == "o/r"
    assert captured["org"] is None
    assert captured["controller_login"] == "ce-controller"
    assert captured["gh_runner"] == "runner"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "controller_inbox"
    assert payload["counts"]["stranded"] == 0


def test_controller_inbox_alias(monkeypatch, capsys):
    monkeypatch.setattr(v3_cli.controller_inbox, "token_from_env", lambda name: "ghp_fake")
    monkeypatch.setattr(v3_cli.controller_inbox, "gh_runner_with_token", lambda token: "runner")
    monkeypatch.setattr(
        v3_cli.controller_inbox,
        "collect_controller_inbox",
        lambda **kwargs: controller_inbox.ControllerInboxResult(
            scope=controller_inbox.InboxScope("repo", kwargs["repo"]),
            controller_login=kwargs["controller_login"],
            buckets={bucket: () for bucket in controller_inbox.BUCKET_ORDER},
        ),
    )

    assert v3_cli.main(["controller-inbox", "--repo", "o/r"]) == 0
    assert "inbox read-only: 0 item(s)" in capsys.readouterr().out
