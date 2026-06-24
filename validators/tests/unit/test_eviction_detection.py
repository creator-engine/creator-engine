"""Unit tests for ce-ops#216 Unit 1 eviction detection.

The integrator detector is read-only and ephemeral: a bounded Search API poll
discovers open PR candidates, then a single GraphQL PR-state read supplies the
review/check/merge evidence used to emit a deterministic ``repair-needed`` event.
"""

import json
import subprocess
import urllib.parse

import pytest

from creator_engine_validator.forge.eviction_detection import (
    EvictionDetectionError,
    RepairNeededEvent,
    build_candidate_queries,
    detect_repair_needed,
    poll_repair_needed,
)


def _state(
    *,
    pr_number=17,
    head_sha="c" * 40,
    review_decision="APPROVED",
    rollup_state="SUCCESS",
    merge_state_status="DIRTY",
    mergeable="MERGEABLE",
):
    from creator_engine_validator.forge.change_status import PullRequestState

    return PullRequestState(
        pr_number=pr_number,
        branch="ce/run-1",
        base="main",
        head_sha=head_sha,
        base_sha="b" * 40,
        review_decision=review_decision,
        approved=(review_decision == "APPROVED"),
        rollup_state=rollup_state,
        all_green=(rollup_state == "SUCCESS"),
        merge_state_status=merge_state_status,
        mergeable=mergeable,
        up_to_date=(merge_state_status != "BEHIND"),
        eligible=(review_decision == "APPROVED" and rollup_state == "SUCCESS" and mergeable == "MERGEABLE"),
    )


def test_detect_repair_needed_emits_structured_dirty_event():
    event = detect_repair_needed(
        repo="creator-engine/creator-engine",
        state=_state(),
        detected_at="2026-06-23T12:00:00Z",
    )

    assert isinstance(event, RepairNeededEvent)
    assert event.to_dict() == {
        "event_type": "repair-needed",
        "repo": "creator-engine/creator-engine",
        "pr_number": 17,
        "head_sha": "c" * 40,
        "merge_state_status": "DIRTY",
        "mergeable": "MERGEABLE",
        "reason": "dirty",
        "detected_at": "2026-06-23T12:00:00Z",
        "evidence": {
            "review_decision": "APPROVED",
            "approved": True,
            "rollup_state": "SUCCESS",
            "all_green": True,
        },
    }


def test_detect_repair_needed_recognizes_behind_and_preserves_exact_state():
    event = detect_repair_needed(
        repo="creator-engine/creator-engine",
        state=_state(merge_state_status="BEHIND"),
    )

    assert event is not None
    assert event.reason == "behind"
    assert event.merge_state_status == "BEHIND"
    assert event.mergeable == "MERGEABLE"
    assert "detected_at" not in event.to_dict()


def test_detect_repair_needed_recognizes_conflicting_mergeable_state():
    event = detect_repair_needed(
        repo="creator-engine/creator-engine",
        state=_state(merge_state_status="CLEAN", mergeable="CONFLICTING"),
    )

    assert event is not None
    assert event.reason == "conflicting"
    assert event.merge_state_status == "CLEAN"
    assert event.mergeable == "CONFLICTING"


def test_detect_repair_needed_only_emits_for_approved_green_repair_states():
    clean = _state(merge_state_status="CLEAN", mergeable="MERGEABLE")
    pending = _state(rollup_state="PENDING", merge_state_status="DIRTY")
    failed = _state(rollup_state="FAILURE", merge_state_status="DIRTY")
    unapproved = _state(review_decision="REVIEW_REQUIRED", merge_state_status="DIRTY")
    unrelated = _state(merge_state_status="BLOCKED", mergeable="MERGEABLE")

    assert detect_repair_needed(repo="creator-engine/creator-engine", state=clean) is None
    assert detect_repair_needed(repo="creator-engine/creator-engine", state=pending) is None
    assert detect_repair_needed(repo="creator-engine/creator-engine", state=failed) is None
    assert detect_repair_needed(repo="creator-engine/creator-engine", state=unapproved) is None
    assert detect_repair_needed(repo="creator-engine/creator-engine", state=unrelated) is None


def _search_body(*hits):
    return json.dumps({"total_count": len(hits), "items": list(hits)})


def _search_hit(repo="creator-engine/creator-engine", number=17):
    return {
        "repository_url": f"https://api.github.com/repos/{repo}",
        "html_url": f"https://github.com/{repo}/pull/{number}",
        "number": number,
        "title": "candidate",
        "updated_at": "2026-06-23T00:00:00Z",
        "pull_request": {"url": f"https://api.github.com/repos/{repo}/pulls/{number}"},
    }


def test_build_candidate_queries_refuses_unscoped_search_fail_closed():
    with pytest.raises(EvictionDetectionError, match="explicit repo or org scope"):
        build_candidate_queries()


def test_build_candidate_queries_declares_repo_scope():
    specs = build_candidate_queries(repo="creator-engine/creator-engine")
    assert len(specs) == 1
    spec = specs[0]
    assert spec.reason == "approved_green_pr"
    assert spec.query == "is:open is:pull-request review:approved status:success repo:creator-engine/creator-engine"
    assert spec.scope.kind == "repo"
    assert spec.scope.value == "creator-engine/creator-engine"


def test_build_candidate_queries_declares_org_scope():
    specs = build_candidate_queries(org="creator-engine")
    assert specs[0].query == "is:open is:pull-request review:approved status:success org:creator-engine"
    assert specs[0].scope.kind == "org"
    assert specs[0].scope.value == "creator-engine"


def test_poll_repair_needed_uses_search_candidates_then_pr_state():
    calls = []

    def transport(method, url, headers, body):
        calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["q"][0]
        assert query == "is:open is:pull-request review:approved status:success repo:creator-engine/creator-engine"
        return 200, {"X-RateLimit-Remaining": "29"}, _search_body(_search_hit())

    def gh_runner(argv, input_text=None):
        joined = " ".join(argv)
        assert "graphql" in joined
        assert "pullRequest" in joined
        payload = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "number": 17,
                        "headRefName": "ce/run-1",
                        "baseRefName": "main",
                        "headRefOid": "d" * 40,
                        "baseRefOid": "b" * 40,
                        "reviewDecision": "APPROVED",
                        "mergeStateStatus": "BEHIND",
                        "mergeable": "MERGEABLE",
                        "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]},
                    }
                }
            }
        }
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

    result = poll_repair_needed(
        token="ghp_fake",
        transport=transport,
        gh_runner=gh_runner,
        repo="creator-engine/creator-engine",
        detected_at="2026-06-23T12:00:00Z",
    )

    assert len(calls) == 1
    assert calls[0]["headers"]["Authorization"] == "Bearer ghp_fake"
    assert result.rate_limit == {"remaining": 29}
    assert [event.to_dict()["reason"] for event in result.events] == ["behind"]
    assert result.events[0].head_sha == "d" * 40
