"""Offline tests for the conveyor stranded-PR sweep."""

from __future__ import annotations

import json
import subprocess

from creator_engine_validator import ce_cli
from creator_engine_validator.forge import integrator_belt as stranded_sweep

REPO = "creator-engine/creator-engine"
PR = 258
HEAD = "a" * 40
APPROVER = "ce-reviewer"
AUTHOR = "ce-author"


class FakeGh:
    def __init__(self, *, node: dict, queued: bool = False):
        self.node = node
        self.queued = queued
        self.calls: list[list[str]] = []
        self.graphql_queries: list[str] = []

    def __call__(self, argv, input_text=None):
        del input_text
        self.calls.append(list(argv))
        if list(argv[:3]) == ["gh", "api", "graphql"]:
            query = _query_from_argv(argv)
            self.graphql_queries.append(query)
            assert "autoMergeRequest" not in query
            if "pullRequests(first:$first" in query:
                return _completed(_sweep_payload(self.node, queued=self.queued), argv)
            return _completed(_reverify_payload(self.node), argv)
        if list(argv[:3]) == ["gh", "pr", "merge"]:
            return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="unexpected call")

    @property
    def merge_calls(self) -> list[list[str]]:
        return [call for call in self.calls if call[:3] == ["gh", "pr", "merge"]]


def test_approved_clean_green_not_queued_is_enqueued_and_logged():
    runner = FakeGh(node=_pr_node())
    logs: list[dict] = []

    result = stranded_sweep.run_stranded_sweep(repo=REPO, gh_runner=runner, log_sink=logs.append)

    assert result.enqueue_count == 1
    assert result.failed_count == 0
    assert result.decisions[0].reason == "stranded_enqueued"
    assert runner.merge_calls == [
        ["gh", "pr", "merge", str(PR), "--repo", REPO, "--auto", "--match-head-commit", HEAD]
    ]
    assert any('mergeQueue{entries(first:100,branch:"main")' in q for q in runner.graphql_queries)
    assert [entry["action"] for entry in logs] == [
        "stranded_sweep_start",
        "stranded_sweep_decision",
        "stranded_sweep_complete",
    ]


def test_approved_clean_green_already_in_merge_queue_is_skipped():
    runner = FakeGh(node=_pr_node(), queued=True)

    result = stranded_sweep.run_stranded_sweep(repo=REPO, gh_runner=runner)

    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "already_queued"
    assert runner.merge_calls == []
    assert any('mergeQueue{entries(first:100,branch:"main")' in q for q in runner.graphql_queries)


def test_dirty_pr_is_skipped_without_enqueue():
    runner = FakeGh(node=_pr_node(merge_state_status="DIRTY"))

    result = stranded_sweep.run_stranded_sweep(repo=REPO, gh_runner=runner)

    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "merge_state_not_clean"
    assert "merge_state_status=DIRTY" in result.decisions[0].evidence
    assert runner.merge_calls == []


def test_failing_merge_group_check_is_skipped_without_enqueue():
    runner = FakeGh(
        node=_pr_node(
            rollup_state="FAILURE",
            checks=(
                _check("Validate governance artifacts", "SUCCESS"),
                _check("merge_group/check", "FAILURE"),
            ),
        )
    )

    result = stranded_sweep.run_stranded_sweep(repo=REPO, gh_runner=runner)

    assert result.enqueue_count == 0
    assert result.skip_count == 1
    assert result.decisions[0].reason == "required_checks_not_success"
    assert "rollup_state=FAILURE" in result.decisions[0].evidence
    assert runner.merge_calls == []


def test_ce_conveyor_sweep_bridges_to_v3_module_cli(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(argv, check=False):
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    monkeypatch.setattr(ce_cli.subprocess, "run", fake_run)

    rc = ce_cli.main(["conveyor", "sweep", "--repo", REPO, "--token-env", "TEST_TOKEN", "--json"])

    assert rc == 0
    assert calls == [
        [
            ce_cli.sys.executable,
            "-m",
            "creator_engine_validator.forge.integrator_belt",
            "stranded-sweep",
            "--repo",
            REPO,
            "--queue-branch",
            "main",
            "--token-env",
            "TEST_TOKEN",
            "--json",
        ]
    ]


def _query_from_argv(argv) -> str:
    for item in argv:
        if isinstance(item, str) and item.startswith("query="):
            return item.removeprefix("query=")
    return ""


def _completed(payload: dict, argv) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(list(argv), 0, stdout=json.dumps(payload), stderr="")


def _sweep_payload(node: dict, *, queued: bool) -> dict:
    queue_nodes = []
    if queued:
        queue_nodes.append({"pullRequest": {"number": PR, "repository": {"nameWithOwner": REPO}}})
    return {
        "data": {
            "repository": {
                "mergeQueue": {
                    "entries": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": queue_nodes,
                    }
                },
                "pullRequests": {
                    "pageInfo": {"hasNextPage": False},
                    "nodes": [node],
                },
            }
        }
    }


def _reverify_payload(node: dict) -> dict:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewDecision": node["reviewDecision"],
                    "headRefOid": node["headRefOid"],
                    "latestOpinionatedReviews": node["latestOpinionatedReviews"],
                }
            }
        }
    }


def _pr_node(
    *,
    merge_state_status: str = "CLEAN",
    rollup_state: str = "SUCCESS",
    checks: tuple[dict, ...] | None = None,
) -> dict:
    return {
        "number": PR,
        "title": "Stranded sweep test PR",
        "url": f"https://github.com/{REPO}/pull/{PR}",
        "body": "",
        "isDraft": False,
        "reviewDecision": "APPROVED",
        "mergeable": "MERGEABLE",
        "mergeStateStatus": merge_state_status,
        "headRefName": "ce258-stranded-pr-sweep",
        "headRefOid": HEAD,
        "baseRefName": "main",
        "author": {"login": AUTHOR},
        "repository": {"nameWithOwner": REPO},
        "latestOpinionatedReviews": {
            "nodes": [
                {
                    "id": "review-1",
                    "state": "APPROVED",
                    "author": {"login": APPROVER},
                    "commit": {"oid": HEAD},
                }
            ]
        },
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "oid": HEAD,
                        "statusCheckRollup": {
                            "state": rollup_state,
                            "contexts": {
                                "pageInfo": {"hasNextPage": False},
                                "nodes": list(
                                    checks
                                    or (
                                        _check("Validate governance artifacts", "SUCCESS"),
                                        _check("unit tests", "SUCCESS"),
                                    )
                                ),
                            },
                        },
                    }
                }
            ]
        },
        "files": {"pageInfo": {"hasNextPage": False}, "nodes": []},
    }


def _check(name: str, conclusion: str) -> dict:
    return {
        "__typename": "CheckRun",
        "name": name,
        "conclusion": conclusion,
        "status": "COMPLETED",
        "completedAt": "2026-06-26T00:00:00Z",
    }
