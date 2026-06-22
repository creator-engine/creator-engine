"""Tests for forge.re_review — rebase-aware stale-review reconciliation (ce-ops#151)."""
from __future__ import annotations

import json
import subprocess

import pytest

from creator_engine_validator.forge import re_review as rr
from creator_engine_validator.forge.github_repo_config import ForgeConfigError, ForgeConfigRefused

HEAD = "aaaa1111head"


def _r(rid, state, commit, who):
    return rr.Review(rid, state, commit, who)


# ---- pure classifier ----------------------------------------------------

def test_309_two_stale_crs_superseded_by_independent_approval_dismissed():
    reviews = [
        _r(1, "CHANGES_REQUESTED", "old1", "ce-dev-3"),
        _r(2, "CHANGES_REQUESTED", "old2", "ce-dev-4"),
        _r(3, "APPROVED", HEAD, "ce-dev-1"),
    ]
    by = {v.review.reviewer: v for v in rr.classify_reviews(reviews, HEAD)}
    assert by["ce-dev-3"].verdict == rr.DISMISS_SUPERSEDED
    assert by["ce-dev-3"].superseded_by == "ce-dev-1"
    assert by["ce-dev-4"].verdict == rr.DISMISS_SUPERSEDED
    assert by["ce-dev-1"].verdict == rr.CURRENT


def test_stale_cr_without_fresh_approval_is_re_request_not_dismiss():
    reviews = [_r(1, "CHANGES_REQUESTED", "old1", "ce-dev-3")]
    (v,) = rr.classify_reviews(reviews, HEAD)
    assert v.verdict == rr.RE_REQUEST_SCOPED
    assert v.superseded_by is None


def test_live_cr_on_head_is_current_never_touched():
    reviews = [_r(1, "CHANGES_REQUESTED", HEAD, "ce-dev-3")]
    (v,) = rr.classify_reviews(reviews, HEAD)
    assert v.verdict == rr.CURRENT


def test_own_approval_does_not_supersede_own_cr():
    # The fresh approval must come from a DIFFERENT reviewer.
    reviews = [
        _r(1, "CHANGES_REQUESTED", "old1", "ce-dev-3"),
        _r(2, "APPROVED", HEAD, "ce-dev-3"),  # same reviewer flipped → latest wins anyway
    ]
    (v,) = rr.classify_reviews(reviews, HEAD)
    # latest-per-reviewer: ce-dev-3's APPROVED on head supersedes its own CR → CURRENT
    assert v.verdict == rr.CURRENT


def test_distinct_approval_required_not_self():
    reviews = [
        _r(1, "CHANGES_REQUESTED", "old1", "ce-dev-3"),
        _r(2, "APPROVED", HEAD, "ce-dev-3"),
        _r(3, "CHANGES_REQUESTED", "old2", "ce-dev-4"),
    ]
    by = {v.review.reviewer: v for v in rr.classify_reviews(reviews, HEAD)}
    # ce-dev-4's CR is superseded by ce-dev-3's fresh approval on head
    assert by["ce-dev-4"].verdict == rr.DISMISS_SUPERSEDED
    assert by["ce-dev-4"].superseded_by == "ce-dev-3"


def test_latest_per_reviewer_reduction():
    # An earlier CR then a later APPROVED (same reviewer, both stale) → APPROVED wins
    reviews = [
        _r(1, "CHANGES_REQUESTED", "old1", "ce-dev-3"),
        _r(2, "APPROVED", "old2", "ce-dev-3"),
    ]
    (v,) = rr.classify_reviews(reviews, HEAD)
    assert v.review.review_id == 2
    assert v.verdict == rr.RE_REQUEST_SCOPED  # stale approval, no longer head


def test_dismissed_clears_prior_decision():
    reviews = [
        _r(1, "CHANGES_REQUESTED", "old1", "ce-dev-3"),
        _r(2, "DISMISSED", "old1", "ce-dev-3"),
    ]
    assert rr.classify_reviews(reviews, HEAD) == []


def test_commented_does_not_count_as_decision():
    reviews = [_r(1, "COMMENTED", "old1", "ce-dev-3")]
    assert rr.classify_reviews(reviews, HEAD) == []


def test_empty_head_fails_closed():
    with pytest.raises(ForgeConfigRefused):
        rr.classify_reviews([_r(1, "CHANGES_REQUESTED", "old1", "x")], "")


# ---- I/O behind the GhRunner seam --------------------------------------

class FakeRunner:
    """Records calls; returns canned reviews on GET, success on PUT dismissals."""

    def __init__(self, reviews_payload):
        self._reviews = reviews_payload
        self.dismissals: list[tuple[str, str | None]] = []

    def __call__(self, argv, input_text=None):
        joined = " ".join(argv)
        if "dismissals" in joined:
            self.dismissals.append((joined, input_text))
            return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")
        if "/reviews" in joined:
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self._reviews), stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected call")


def _payload():
    return [
        {"id": 11, "state": "CHANGES_REQUESTED", "commit_id": "old1", "user": {"login": "ce-dev-3"}},
        {"id": 22, "state": "APPROVED", "commit_id": HEAD, "user": {"login": "ce-dev-1"}},
    ]


def test_list_reviews_parses_shape():
    runner = FakeRunner(_payload())
    reviews = rr.list_reviews("o/r", 7, gh_runner=runner)
    assert reviews[0] == rr.Review(11, "CHANGES_REQUESTED", "old1", "ce-dev-3")
    assert reviews[1].reviewer == "ce-dev-1"


def test_reconcile_dry_run_dismisses_nothing():
    runner = FakeRunner(_payload())
    report = rr.reconcile_reviews("o/r", 7, HEAD, gh_runner=runner, apply=False)
    assert report.dismissed == ()
    assert runner.dismissals == []
    assert any(v.verdict == rr.DISMISS_SUPERSEDED for v in report.verdicts)


def test_reconcile_apply_dismisses_superseded_with_audit():
    runner = FakeRunner(_payload())
    report = rr.reconcile_reviews("o/r", 7, HEAD, gh_runner=runner, apply=True)
    assert report.dismissed == (11,)
    assert len(runner.dismissals) == 1
    joined, body = runner.dismissals[0]
    assert "reviews/11/dismissals" in joined
    assert "ce-ops#151" in (body or "")


def test_dismiss_review_empty_message_refused():
    runner = FakeRunner(_payload())
    with pytest.raises(ForgeConfigRefused):
        rr.dismiss_review("o/r", 7, 11, "   ", gh_runner=runner)


def test_gh_error_raises():
    class Boom:
        def __call__(self, argv, input_text=None):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")
    with pytest.raises(ForgeConfigError):
        rr.list_reviews("o/r", 7, gh_runner=Boom())
