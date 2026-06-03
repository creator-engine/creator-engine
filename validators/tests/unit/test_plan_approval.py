"""Unit tests for the v3 G-2.1 forge-native plan-approval resolver.

``plan_approved`` resolves the orchestrator's ``ApprovedPlan`` from the forge
(the source-of-truth): a plan-PR with an APPROVED review that is commit-pinned to
the PR head (re-asserting GitHub's stale-on-commit-change behaviour), submitted by
an independent reviewer who is NEITHER the PR author NOR the running seat (no
self-approval), with the PR body carrying ``ce-run-id`` / ``ce-policy-sha`` markers
that bind the approval to the exact run + runtime-policy in force.

All forge I/O goes through an injectable ``GhRunner``; these tests inject a fake
runner returning canned ``gh api`` JSON and perform ZERO live network/subprocess.
"""

import json
import subprocess

import pytest

from creator_engine_validator.forge import ForgeConfigError
from creator_engine_validator.forge.plan_approval import ApprovalQuery, plan_approved
from creator_engine_validator.orchestrator import ApprovedPlan

_POLICY_SHA = "a" * 64
_REPO = "creator-engine/creator-engine"
_HEAD = "f" * 40
_SEAT = "seat-agent"


def _query(run_id: str = "run-1", policy_sha: str = _POLICY_SHA) -> ApprovalQuery:
    return ApprovalQuery(repo=_REPO, pr_number=7, run_id=run_id, policy_sha=policy_sha)


def _pr(
    *,
    author: str = "author-alice",
    head: str = _HEAD,
    run_id: str = "run-1",
    policy_sha: str = _POLICY_SHA,
    body: str | None = None,
) -> dict:
    if body is None:
        body = f"plan PR\n\nce-run-id: {run_id}\nce-policy-sha: {policy_sha}\n"
    return {"user": {"login": author}, "head": {"sha": head}, "body": body}


def _review(login: str, state: str = "APPROVED", commit_id: str = _HEAD) -> dict:
    return {"state": state, "commit_id": commit_id, "user": {"login": login}}


def _fake_runner(pr_obj: dict, reviews: list, *, pr_rc: int = 0, reviews_rc: int = 0):
    """A GhRunner that answers the PR GET and the reviews GET from canned JSON."""
    calls: list[list[str]] = []

    def run(argv, input_text=None):
        calls.append(list(argv))
        path = argv[-1]
        if path.endswith("/reviews"):
            return subprocess.CompletedProcess(
                argv, reviews_rc, stdout=json.dumps(reviews), stderr="" if reviews_rc == 0 else "boom"
            )
        return subprocess.CompletedProcess(
            argv, pr_rc, stdout=json.dumps(pr_obj), stderr="" if pr_rc == 0 else "boom"
        )

    run.calls = calls  # type: ignore[attr-defined]
    return run


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_resolves_approved_plan_from_independent_commit_pinned_review():
    runner = _fake_runner(_pr(), [_review("reviewer-bob")])
    plan = plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner)
    assert isinstance(plan, ApprovedPlan)
    assert plan.run_id == "run-1"
    assert plan.policy_sha == _POLICY_SHA
    assert plan.approved_by == "reviewer-bob"
    assert plan.approval_ref == f"{_REPO}#7@{_HEAD}"


# ---------------------------------------------------------------------------
# Binding markers
# ---------------------------------------------------------------------------
def test_no_binding_markers_returns_none():
    runner = _fake_runner(_pr(body="plan PR with no markers"), [_review("reviewer-bob")])
    assert plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner) is None


def test_mismatched_run_id_marker_returns_none():
    runner = _fake_runner(_pr(run_id="other-run"), [_review("reviewer-bob")])
    assert plan_approved(_query(run_id="run-1"), seat_identity=_SEAT, gh_runner=runner) is None


def test_mismatched_policy_sha_marker_returns_none():
    runner = _fake_runner(_pr(policy_sha="b" * 64), [_review("reviewer-bob")])
    assert plan_approved(_query(policy_sha=_POLICY_SHA), seat_identity=_SEAT, gh_runner=runner) is None


# ---------------------------------------------------------------------------
# Review selection — commit-pin, no self-approval, must be APPROVED
# ---------------------------------------------------------------------------
def test_stale_review_off_head_commit_returns_none():
    runner = _fake_runner(_pr(), [_review("reviewer-bob", commit_id="0" * 40)])
    assert plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner) is None


def test_review_by_pr_author_returns_none():
    runner = _fake_runner(_pr(author="author-alice"), [_review("author-alice")])
    assert plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner) is None


def test_review_by_running_seat_returns_none():
    runner = _fake_runner(_pr(), [_review(_SEAT)])
    assert plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner) is None


def test_no_approved_review_returns_none():
    runner = _fake_runner(_pr(), [_review("reviewer-bob", state="COMMENTED")])
    assert plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner) is None


def test_latest_independent_approved_review_wins():
    reviews = [
        _review("reviewer-bob", state="CHANGES_REQUESTED"),
        _review("reviewer-carol"),
    ]
    plan = plan_approved(_query(), seat_identity=_SEAT, gh_runner=_fake_runner(_pr(), reviews))
    assert plan is not None and plan.approved_by == "reviewer-carol"


# ---------------------------------------------------------------------------
# Transport failure is distinct from "no valid approval"
# ---------------------------------------------------------------------------
def test_transport_failure_raises_forge_config_error():
    runner = _fake_runner(_pr(), [], pr_rc=1)
    with pytest.raises(ForgeConfigError):
        plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner)


# ---------------------------------------------------------------------------
# Zero live network — only the injected runner is ever the transport
# ---------------------------------------------------------------------------
def test_zero_live_network(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("plan_approved must not touch a live forge")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    runner = _fake_runner(_pr(), [_review("reviewer-bob")])
    plan = plan_approved(_query(), seat_identity=_SEAT, gh_runner=runner)
    assert plan is not None
    assert runner.calls  # the injected fake was the only transport
