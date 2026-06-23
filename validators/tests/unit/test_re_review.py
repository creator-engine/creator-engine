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


# ---- pagination: complete-history guarantee (ce-ops#151, fail-closed) ----

def _page_of(n, *, start_id, state, commit, who):
    return [
        {"id": start_id + i, "state": state, "commit_id": commit, "user": {"login": who}}
        for i in range(n)
    ]


class PagedRunner:
    """Returns canned pages keyed by the ``page=`` query param.

    Models GitHub's real paginated ``/reviews`` endpoint: a full page (== per_page)
    signals "more pages follow"; a short/empty page is terminal.
    """

    def __init__(self, pages):
        self._pages = pages  # dict[int, list[dict]]
        self.requested_pages: list[int] = []
        self.dismissals: list[tuple[str, str | None]] = []

    def __call__(self, argv, input_text=None):
        joined = " ".join(argv)
        if "dismissals" in joined:
            self.dismissals.append((joined, input_text))
            return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")
        if "/reviews" in joined:
            # extract page=N
            page = 1
            for part in joined.replace("&", " ").split():
                if part.startswith("page="):
                    page = int(part.split("=", 1)[1])
            self.requested_pages.append(page)
            payload = self._pages.get(page, [])
            if isinstance(payload, str):
                return subprocess.CompletedProcess(argv, 0, stdout=payload, stderr="")
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected call")


def test_list_reviews_walks_all_pages():
    # A full first page (per_page items) MUST trigger a second-page fetch; the
    # later page carries the fresh approval that supersedes the page-1 CR.
    per = rr._REVIEWS_PER_PAGE
    pages = {
        1: _page_of(per, start_id=1000, state="CHANGES_REQUESTED", commit="old1", who="ce-dev-3"),
        2: [{"id": 99, "state": "APPROVED", "commit_id": HEAD, "user": {"login": "ce-dev-1"}}],
    }
    runner = PagedRunner(pages)
    reviews = rr.list_reviews("o/r", 7, gh_runner=runner)
    assert len(reviews) == per + 1
    assert runner.requested_pages == [1, 2]  # walked past the full first page
    assert reviews[-1].reviewer == "ce-dev-1"


def test_list_reviews_allows_empty_json_array_terminal_page():
    per = rr._REVIEWS_PER_PAGE
    pages = {
        1: _page_of(per, start_id=1500, state="COMMENTED", commit="old1", who="bot"),
        2: [],
    }
    runner = PagedRunner(pages)
    reviews = rr.list_reviews("o/r", 7, gh_runner=runner)
    assert len(reviews) == per
    assert runner.requested_pages == [1, 2]


def test_reconcile_sees_later_page_objection_not_dismissed():
    # Regression: a stale CR on page 1 must NOT be dismissed when the reviewer's
    # OWN later (live) objection lives on page 2 — incomplete state must not
    # leak into apply=True. With full pagination ce-dev-3's effective state is a
    # live CR on head → CURRENT, nothing dismissed.
    per = rr._REVIEWS_PER_PAGE
    page1 = _page_of(per, start_id=2000, state="CHANGES_REQUESTED", commit="old1", who="filler")
    page1[0] = {"id": 2000, "state": "CHANGES_REQUESTED", "commit_id": "old1", "user": {"login": "ce-dev-3"}}
    pages = {
        1: page1,
        2: [{"id": 50, "state": "CHANGES_REQUESTED", "commit_id": HEAD, "user": {"login": "ce-dev-3"}}],
    }
    runner = PagedRunner(pages)
    report = rr.reconcile_reviews("o/r", 7, HEAD, gh_runner=runner, apply=True)
    by = {v.review.reviewer: v for v in report.verdicts}
    assert by["ce-dev-3"].verdict == rr.CURRENT  # live objection on head, complete history
    assert report.dismissed == ()


def test_reconcile_apply_fails_closed_on_empty_later_page_stdout_without_dismiss():
    per = rr._REVIEWS_PER_PAGE
    page1 = _page_of(per, start_id=3000, state="COMMENTED", commit="old1", who="bot")
    page1[0] = {"id": 3000, "state": "CHANGES_REQUESTED", "commit_id": "old1", "user": {"login": "ce-dev-3"}}
    page1[1] = {"id": 3001, "state": "APPROVED", "commit_id": HEAD, "user": {"login": "ce-dev-1"}}
    runner = PagedRunner({1: page1, 2: ""})
    with pytest.raises(ForgeConfigError, match="empty stdout"):
        rr.reconcile_reviews("o/r", 7, HEAD, gh_runner=runner, apply=True)
    assert runner.requested_pages == [1, 2]
    assert runner.dismissals == []


def test_reconcile_apply_fails_closed_on_non_json_later_page_stdout_without_dismiss():
    per = rr._REVIEWS_PER_PAGE
    page1 = _page_of(per, start_id=4000, state="COMMENTED", commit="old1", who="bot")
    page1[0] = {"id": 4000, "state": "CHANGES_REQUESTED", "commit_id": "old1", "user": {"login": "ce-dev-3"}}
    page1[1] = {"id": 4001, "state": "APPROVED", "commit_id": HEAD, "user": {"login": "ce-dev-1"}}
    runner = PagedRunner({1: page1, 2: "not json"})
    with pytest.raises(ForgeConfigError, match="non-JSON stdout"):
        rr.reconcile_reviews("o/r", 7, HEAD, gh_runner=runner, apply=True)
    assert runner.requested_pages == [1, 2]
    assert runner.dismissals == []


def test_list_reviews_fails_closed_when_page_ceiling_exceeded(monkeypatch):
    # An endpoint that never returns a short page cannot be proven complete →
    # fail closed rather than dismiss from partial state.
    monkeypatch.setattr(rr, "_MAX_REVIEW_PAGES", 3)
    per = rr._REVIEWS_PER_PAGE
    full = _page_of(per, start_id=1, state="COMMENTED", commit="x", who="bot")
    runner = PagedRunner({p: full for p in range(1, 10)})  # every page is full
    with pytest.raises(ForgeConfigError):
        rr.list_reviews("o/r", 7, gh_runner=runner)


def test_list_reviews_non_array_body_fails_closed():
    class BadShape:
        def __call__(self, argv, input_text=None):
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"message": "x"}), stderr="")
    with pytest.raises(ForgeConfigError):
        rr.list_reviews("o/r", 7, gh_runner=BadShape())
