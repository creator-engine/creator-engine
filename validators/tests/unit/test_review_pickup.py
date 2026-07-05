"""Unit tests for the ce-ops#188 controller review-pickup leg.

``creator_engine_validator.forge.review_pickup`` is the **v3** review half of the
belt: it routes awaiting-review PRs to distinct non-author reviewer seats and
reconciles objectively stale reviews via ``forge.re_review``. It shares the
read-only GitHub Search primitives with the v1 work-poller through the
boundary-neutral ``pickup_search`` core, so no v1<->v3 import edge is created.

These tests inject a fake HTTP transport + a fake ``gh`` runner and perform ZERO
live network / subprocess.
"""

import json
import subprocess
import urllib.parse

import pytest

from creator_engine_validator.search_rate_limiter import SearchRateLimiter
from creator_engine_validator.forge import review_pickup


# ---------------------------------------------------------------------------
# Fake Search API transport + the GitHub issues-search type-qualifier contract.
# ---------------------------------------------------------------------------


def _hit(*, repo="creator-engine/ce-ops", number=42, pr=True, title="x"):
    web_kind = "pull" if pr else "issues"
    hit = {
        "repository_url": f"https://api.github.com/repos/{repo}",
        "html_url": f"https://github.com/{repo}/{web_kind}/{number}",
        "number": number,
        "title": title,
        "updated_at": "2026-06-21T00:00:00Z",
    }
    if pr:
        hit["pull_request"] = {"url": f"https://api.github.com/repos/{repo}/pulls/{number}"}
    return hit


def _body(*hits):
    return json.dumps({"total_count": len(hits), "items": list(hits)})


def _assert_explicit_search_type(query):
    """Reject a Search ``q`` lacking exactly one ``is:pull-request``/``is:issue``.

    Offline stand-in for GitHub's issues-search ``HTTP 422`` ("Query must include
    'is:issue' or 'is:pull-request'") that the ce-ops#182 belt feed tripped live.
    """
    terms = query.split()
    type_terms = sum(term in {"is:pull-request", "is:issue"} for term in terms)
    assert type_terms == 1, (
        "search query must carry exactly one is:pull-request/is:issue type "
        f"qualifier (GitHub returns HTTP 422 otherwise); got {query!r}"
    )


def _fake_transport(responses, calls=None):
    seq = list(responses)

    def transport(method, url, headers, body):
        if calls is not None:
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("q", [""])[0]
        _assert_explicit_search_type(query)
        status, resp_headers, resp_body = seq.pop(0)
        return status, dict(resp_headers), resp_body

    return transport


def _test_limiter(tmp_path, clock=None):
    return SearchRateLimiter(
        tmp_path / "search-rate.json",
        rate_per_minute=6000,
        burst=1,
        jitter_seconds=0,
        clock=clock or (lambda: 0.0),
        random_float=lambda: 0.0,
    )


class _FakeReviewPickupForge:
    def __init__(
        self,
        *,
        author="author-a",
        head="h" * 40,
        requested=None,
        reviews=None,
        draft=False,
        combined_status=None,
        check_runs=None,
    ):
        self.author = author
        self.head = head
        self.requested = list(requested or [])
        self.reviews = list(reviews or [])
        self.draft = draft
        self.combined_status = combined_status if combined_status is not None else {"state": "success", "statuses": []}
        self.check_runs = check_runs if check_runs is not None else {"total_count": 0, "check_runs": []}
        self.review_requests: list[tuple[str, str | None]] = []
        self.dismissals: list[tuple[str, str | None]] = []

    def runner(self, argv, input_text=None):
        args = list(argv)
        method = "GET"
        path = ""
        i = 2
        while i < len(args):
            tok = args[i]
            if tok in ("--method", "-X"):
                method = args[i + 1]
                i += 2
                continue
            if tok in ("--input", "-f"):
                i += 2
                continue
            if not tok.startswith("-") and not path:
                path = tok
            i += 1
        bare_path = path.split("?", 1)[0]
        body = json.loads(input_text) if input_text else {}

        if bare_path.endswith("/requested_reviewers") and method == "POST":
            self.review_requests.append((path, input_text))
            for reviewer in body.get("reviewers", []):
                if reviewer not in self.requested:
                    self.requested.append(reviewer)
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({}), stderr="")
        if bare_path.endswith("/dismissals") and method == "PUT":
            self.dismissals.append((path, input_text))
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({}), stderr="")
        if bare_path.endswith("/status") and "/commits/" in bare_path and method == "GET":
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.combined_status), stderr="")
        if bare_path.endswith("/check-runs") and "/commits/" in bare_path and method == "GET":
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.check_runs), stderr="")
        if bare_path.endswith("/reviews") and method == "GET":
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.reviews), stderr="")
        if "/pulls/" in bare_path and method == "GET":
            payload = {
                "user": {"login": self.author},
                "head": {"sha": self.head},
                "requested_reviewers": [{"login": r} for r in self.requested],
                "draft": self.draft,
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr=f"unexpected {method} {path}")


def test_review_pickup_query_is_typed_and_scoped():
    spec = review_pickup.review_pickup_query(repo="o/r")
    assert spec.reason == "awaiting_review"
    assert spec.query == "is:open is:pull-request repo:o/r"
    assert spec.scope.kind == "repo"
    assert spec.scope.value == "o/r"
    _assert_explicit_search_type(spec.query)


def test_review_pickup_refuses_unscoped_query_fail_closed():
    # ce-ops#188 review: an unscoped review-pickup would request reviewers and
    # auto-dismiss stale reviews across every open PR a token can see. Both the
    # query builder and poll loop must fail closed when neither repo nor org is set.
    with pytest.raises(review_pickup.PickupError, match="unscoped"):
        review_pickup.review_pickup_query()
    forge = _FakeReviewPickupForge(author="ce-dev-2", head="a" * 40)
    with pytest.raises(review_pickup.PickupError, match="unscoped"):
        review_pickup.poll_review_pickup(
            token="ghp_fake",
            reviewer_seats=("ce-dev-3",),
            gh_runner=forge.runner,
            transport=_fake_transport([]),
            apply=True,
        )


def test_poll_review_pickup_routes_awaiting_pr_to_distinct_non_author():
    head = "a" * 40
    forge = _FakeReviewPickupForge(author="ce-dev-2", head=head)
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=7, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-2", "ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert len(result.items) == 1
    item = result.items[0]
    assert item["kind"] == "review_request"
    assert item["reason"] == "awaiting_review"
    assert item["author"] == "ce-dev-2"
    assert item["assigned_reviewer"] == "ce-dev-3"
    assert item["requested"] is True
    assert item["thread_id"] == f"review-pickup:o/r:review_request:7:{head[:12]}"
    assert len(forge.review_requests) == 1
    assert '"ce-dev-3"' in (forge.review_requests[0][1] or "")


def test_poll_review_pickup_retries_search_rate_limit(tmp_path):
    calls = []
    sleeps: list[float] = []
    now = {"value": 100.0}

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now["value"] += seconds

    transport = _fake_transport(
        [
            (429, {"Retry-After": "2"}, "{}"),
            (200, {"X-RateLimit-Remaining": "28"}, _body()),
        ],
        calls=calls,
    )
    forge = _FakeReviewPickupForge()

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["dev-2"],
        gh_runner=forge.runner,
        transport=transport,
        repo="creator-engine/ce-ops",
        rate_limiter=_test_limiter(tmp_path, clock=lambda: now["value"]),
        sleep=sleep,
    )

    assert result.items == ()
    assert result.rate_limit == {"remaining": 28}
    assert len(calls) == 2
    assert sleeps == [5.0]


def test_poll_review_pickup_never_routes_author_to_self():
    forge = _FakeReviewPickupForge(author="ce-dev-2")
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=6, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-2"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert result.items == ()
    assert result.skipped[0]["reason"] == "review_pickup_refused"
    assert "no distinct non-author reviewer" in result.skipped[0]["note"]
    assert forge.review_requests == []


def test_poll_review_pickup_spreads_multiple_prs_by_load():
    forge = _FakeReviewPickupForge(author="ce-dev-2")
    transport = _fake_transport([
        (200, {}, _body(
            _hit(repo="o/r", number=13, pr=True),
            _hit(repo="o/r", number=14, pr=True),
        )),
    ])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3", "ce-dev-4"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=False,
    )

    assert [item["assigned_reviewer"] for item in result.items] == ["ce-dev-3", "ce-dev-4"]
    assert forge.review_requests == []


def test_poll_review_pickup_skips_current_non_author_approval():
    head = "e" * 40
    reviews = [{"id": 33, "state": "APPROVED", "commit_id": head, "user": {"login": "ce-dev-3"}}]
    forge = _FakeReviewPickupForge(author="ce-dev-2", head=head, reviews=reviews)
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=15, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert result.items == ()
    assert result.skipped[0]["reason"] == "review_not_awaiting_pickup"
    assert forge.review_requests == []


def test_poll_review_pickup_skips_draft_pr_fail_closed():
    forge = _FakeReviewPickupForge(author="ce-dev-2", draft=True)
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=16, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert result.items == ()
    assert result.skipped[0]["reason"] == "draft_pull_request"
    assert forge.review_requests == []


def test_poll_review_pickup_skips_failed_ci_fail_closed():
    forge = _FakeReviewPickupForge(author="ce-dev-2", combined_status={"state": "failure", "statuses": []})
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=17, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert result.items == ()
    assert result.skipped[0]["reason"] == "ci_failed"
    assert forge.review_requests == []


def test_poll_review_pickup_dry_run_assigns_nothing():
    forge = _FakeReviewPickupForge(author="ce-dev-2")
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=18, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
        dry_run=True,
    )

    assert len(result.items) == 1
    assert result.items[0]["assigned_reviewer"] == "ce-dev-3"
    assert result.items[0]["requested"] is False
    assert result.items[0]["dry_run"] is True
    assert forge.review_requests == []


def test_run_review_pickup_loop_is_bounded_and_logs_decisions():
    forge = _FakeReviewPickupForge(author="ce-dev-2")
    transport = _fake_transport([
        (200, {}, _body(_hit(repo="o/r", number=19, pr=True))),
        (200, {}, _body(_hit(repo="o/r", number=20, pr=True))),
    ])
    sleeps: list[float] = []
    logs: list[dict] = []

    result = review_pickup.run_review_pickup_loop(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=False,
        dry_run=True,
        iterations=2,
        interval=5,
        sleep=sleeps.append,
        log_sink=logs.append,
    )

    assert len(result.passes) == 2
    assert result.item_count == 2
    assert sleeps == [5]
    assert [log["event"] for log in logs].count("review_pickup_decision") == 2
    assert forge.review_requests == []


def test_poll_review_pickup_reports_existing_non_author_request_without_duplicate_apply():
    forge = _FakeReviewPickupForge(author="ce-dev-2", requested=["ce-dev-3"])
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=8, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert len(result.items) == 1
    assert result.items[0]["reason"] == "review_already_requested"
    assert result.items[0]["assigned_reviewer"] == "ce-dev-3"
    assert result.items[0]["requested"] is False
    assert forge.review_requests == []


def test_awaiting_review_inbox_includes_ce_dev_2_requested_reviewer():
    forge = _FakeReviewPickupForge(author="author-a", requested=["ce-dev-2"])
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=21, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    inbox = review_pickup.build_awaiting_review_inbox(result, clock=lambda: "2026-06-25T00:00:00Z")
    assert inbox["record_count"] == 1
    assert inbox["records"][0] == {
        "pr": 21,
        "repo": "o/r",
        "author": "author-a",
        "head_sha": "h" * 40,
        "ci_state": {"combined": {"state": "success", "statuses": []}, "checks": {"total_count": 0, "check_runs": []}},
        "requested_at": "2026-06-21T00:00:00Z",
    }


def test_awaiting_review_inbox_includes_ce_dev_2_requested_with_failed_ci():
    forge = _FakeReviewPickupForge(
        author="author-a",
        requested=["ce-dev-2"],
        combined_status={"state": "failure", "statuses": [{"context": "unit", "state": "failure"}]},
    )
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=27, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert result.items == ()
    assert result.skipped[0]["reason"] == "ci_failed"
    inbox = review_pickup.build_awaiting_review_inbox(result, clock=lambda: "2026-06-25T00:00:00Z")
    assert inbox["record_count"] == 1
    assert inbox["records"][0]["pr"] == 27
    assert inbox["records"][0]["ci_state"]["combined"]["state"] == "failure"


def test_awaiting_review_inbox_filters_credentialless_requested_reviewers():
    forge = _FakeReviewPickupForge(author="author-a", requested=["ce-dev-3", "ce-dev-4"])
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=22, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3", "ce-dev-4"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    inbox = review_pickup.build_awaiting_review_inbox(result, clock=lambda: "2026-06-25T00:00:00Z")
    assert inbox["record_count"] == 0
    assert inbox["records"] == []


def test_awaiting_review_inbox_includes_mixed_requested_reviewers_when_ce_dev_2_requested():
    forge = _FakeReviewPickupForge(author="author-a", requested=["ce-dev-3", "ce-dev-2"])
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=23, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3", "ce-dev-4"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert result.items[0]["requested_reviewers"] == ["ce-dev-3", "ce-dev-2"]
    assert result.items[0]["assigned_reviewer"] == "ce-dev-3"
    inbox = review_pickup.build_awaiting_review_inbox(result, clock=lambda: "2026-06-25T00:00:00Z")
    assert inbox["record_count"] == 1
    assert inbox["records"][0]["pr"] == 23
    assert inbox["records"][0]["repo"] == "o/r"


def test_awaiting_review_inbox_excludes_current_ce_dev_2_approval():
    head = "g" * 40
    reviews = [{"id": 44, "state": "APPROVED", "commit_id": head, "user": {"login": "ce-dev-2"}}]
    forge = _FakeReviewPickupForge(author="author-a", head=head, requested=["ce-dev-2"], reviews=reviews)
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=24, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert result.items == ()
    inbox = review_pickup.build_awaiting_review_inbox(result, clock=lambda: "2026-06-25T00:00:00Z")
    assert inbox["records"] == []


def test_run_review_pickup_loop_writes_awaiting_review_inbox(tmp_path):
    forge = _FakeReviewPickupForge(author="author-a", requested=["ce-dev-2"])
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=25, pr=True)))])
    inbox_path = tmp_path / "controller-inbox" / "awaiting-review.json"

    review_pickup.run_review_pickup_loop(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=False,
        iterations=1,
        inbox_path=inbox_path,
        clock=lambda: "2026-06-25T00:00:00Z",
    )

    payload = json.loads(inbox_path.read_text(encoding="utf-8"))
    assert payload["controller_reviewer"] == "ce-dev-2"
    assert payload["record_count"] == 1
    assert payload["records"][0]["pr"] == 25


def test_run_review_pickup_loop_fails_closed_when_inbox_write_fails():
    forge = _FakeReviewPickupForge(author="author-a", requested=["ce-dev-2"])
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=26, pr=True)))])

    def broken_writer(path, content):
        raise OSError("disk full")

    with pytest.raises(review_pickup.PickupError, match="awaiting-review inbox"):
        review_pickup.run_review_pickup_loop(
            token="ghp_fake",
            reviewer_seats=["ce-dev-3"],
            gh_runner=forge.runner,
            transport=transport,
            repo="o/r",
            apply=False,
            iterations=1,
            inbox_path="ignored.json",
            inbox_writer=broken_writer,
        )


def test_run_review_pickup_loop_preserves_inbox_on_rate_limit(tmp_path):
    inbox_path = tmp_path / "controller-inbox" / "awaiting-review.json"
    inbox_path.parent.mkdir(parents=True)
    existing = {"records": [{"pr": 99, "repo": "o/r"}]}
    inbox_path.write_text(json.dumps(existing), encoding="utf-8")
    forge = _FakeReviewPickupForge(author="author-a", requested=["ce-dev-2"])

    result = review_pickup.run_review_pickup_loop(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=_fake_transport([(429, {"Retry-After": "60"}, "{}")]),
        repo="o/r",
        iterations=1,
        inbox_path=inbox_path,
    )

    assert result.passes[0].incomplete is True
    assert result.passes[0].rate_limit["status"] == 429
    assert json.loads(inbox_path.read_text(encoding="utf-8")) == existing


def test_run_review_pickup_loop_refreshes_supplier_and_runner_each_pass():
    supplied_tokens = iter(("tok-pass-1", "tok-pass-2"))
    runner_tokens = []
    auth_headers = []

    def token_supplier() -> str:
        return next(supplied_tokens)

    def gh_runner_factory(token: str):
        runner_tokens.append(token)

        def runner(argv, input_text=None):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected gh call")

        return runner

    def transport(method, url, headers, body):
        auth_headers.append(headers.get("Authorization"))
        return 200, {}, json.dumps({"total_count": 0, "items": []})

    result = review_pickup.run_review_pickup_loop(
        token="static-token",
        reviewer_seats=("reviewer-b",),
        gh_runner=lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1),
        token_supplier=token_supplier,
        gh_runner_factory=gh_runner_factory,
        transport=transport,
        repo="owner/repo",
        iterations=2,
        interval=0,
        sleep=lambda seconds: None,
    )

    assert len(result.passes) == 2
    assert all(not review_pass.incomplete for review_pass in result.passes)
    assert runner_tokens == ["tok-pass-1", "tok-pass-2"]
    assert auth_headers == ["Bearer tok-pass-1", "Bearer tok-pass-2"]


def test_run_review_pickup_loop_retries_after_supplier_failure():
    calls = {"count": 0}
    events = []
    sleeps = []

    def token_supplier() -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("backend unavailable")
        return "tok-pass-2"

    def gh_runner_factory(token: str):
        return lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1)

    result = review_pickup.run_review_pickup_loop(
        token="",
        reviewer_seats=("reviewer-b",),
        gh_runner=lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1),
        token_supplier=token_supplier,
        gh_runner_factory=gh_runner_factory,
        transport=lambda method, url, headers, body: (200, {}, json.dumps({"total_count": 0, "items": []})),
        repo="owner/repo",
        iterations=2,
        interval=0,
        sleep=sleeps.append,
        log_sink=events.append,
        max_consecutive_failures=2,
    )

    assert [review_pass.incomplete for review_pass in result.passes] == [True, False]
    assert sleeps == [0]
    incomplete = [event for event in events if event["event"] == "review_pickup_pass_incomplete"]
    assert incomplete[0]["reason"] == "token_supplier_failed"
    assert incomplete[0]["error_type"] == "RuntimeError"


def test_run_review_pickup_loop_retries_pickup_error_with_supplier():
    events = []

    result = review_pickup.run_review_pickup_loop(
        token="",
        reviewer_seats=(),
        gh_runner=lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1),
        token_supplier=lambda: "tok-pass",
        gh_runner_factory=lambda token: (
            lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1)
        ),
        transport=lambda method, url, headers, body: (200, {}, json.dumps({"total_count": 0, "items": []})),
        repo="owner/repo",
        iterations=2,
        interval=0,
        sleep=lambda seconds: None,
        log_sink=events.append,
        max_consecutive_failures=3,
    )

    assert [review_pass.incomplete for review_pass in result.passes] == [True, True]
    incomplete = [event for event in events if event["event"] == "review_pickup_pass_incomplete"]
    assert [event["reason"] for event in incomplete] == ["pickup_error", "pickup_error"]
    assert "requires at least one --seat reviewer" in incomplete[0]["note"]


def test_cev3_review_pickup_supplier_failures_return_nonzero(monkeypatch, capsys):
    from creator_engine_validator import v3_cli

    def token_supplier() -> str:
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(v3_cli, "_review_pickup_token_supplier_from_args", lambda args: token_supplier)

    code = v3_cli.main([
        "review-pickup",
        "--identity", "controller",
        "--repo", "o/r",
        "--seat", "ce-dev-3",
        "--once",
        "--pickup-token-max-consecutive-failures", "1",
        "--json",
    ])

    assert code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == "review_pickup_failed"
    assert "exiting for supervisor restart" in out["detail"]


def test_awaiting_review_inbox_paginates_past_routing_first_page():
    forge = _FakeReviewPickupForge(author="author-a", requested=["ce-dev-2"])
    transport = _fake_transport([
        (200, {}, _body(_hit(repo="o/r", number=28, pr=False))),
        (200, {}, _body(_hit(repo="o/r", number=29, pr=True))),
        (200, {}, _body()),
    ])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        per_page=1,
        apply=False,
    )

    assert result.items == ()
    inbox = review_pickup.build_awaiting_review_inbox(result, clock=lambda: "2026-06-25T00:00:00Z")
    assert inbox["record_count"] == 1
    assert inbox["records"][0]["pr"] == 29


def test_poll_review_pickup_dismisses_superseded_cr_and_rerequests_reviewer():
    head = "b" * 40
    reviews = [
        {"id": 11, "state": "CHANGES_REQUESTED", "commit_id": "old1", "user": {"login": "ce-dev-3"}},
        {"id": 22, "state": "APPROVED", "commit_id": head, "user": {"login": "ce-dev-4"}},
    ]
    forge = _FakeReviewPickupForge(author="ce-dev-2", head=head, reviews=reviews)
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=9, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3", "ce-dev-4"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    # The fresh non-author approval means the PR is no longer awaiting pickup,
    # but the stale CHANGES_REQUESTED review is still deterministically dismissed
    # with the ce-ops#151 audit trail before the item is skipped.
    assert result.items == ()
    assert len(forge.dismissals) == 1
    assert "reviews/11/dismissals" in forge.dismissals[0][0]
    assert "ce-ops#151" in (forge.dismissals[0][1] or "")
    assert forge.review_requests == []


def test_poll_review_pickup_rerequests_stale_reviewer_when_no_fresh_approval():
    head = "c" * 40
    reviews = [
        {"id": 11, "state": "CHANGES_REQUESTED", "commit_id": "old1", "user": {"login": "ce-dev-3"}},
    ]
    forge = _FakeReviewPickupForge(author="ce-dev-2", head=head, reviews=reviews)
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=10, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-3", "ce-dev-4"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert len(result.items) == 1
    item = result.items[0]
    assert item["reason"] == "stale_review_rerequest"
    assert item["assigned_reviewer"] == "ce-dev-3"
    assert item["re_request_review_ids"] == [11]
    assert forge.dismissals == []
    assert len(forge.review_requests) == 1
    assert '"ce-dev-3"' in (forge.review_requests[0][1] or "")


def test_poll_review_pickup_does_not_route_stale_reviewer_outside_governed_seats():
    head = "f" * 40
    reviews = [
        {"id": 12, "state": "CHANGES_REQUESTED", "commit_id": "old2", "user": {"login": "ce-dev-3"}},
    ]
    forge = _FakeReviewPickupForge(author="ce-dev-2", head=head, reviews=reviews)
    transport = _fake_transport([(200, {}, _body(_hit(repo="o/r", number=11, pr=True)))])

    result = review_pickup.poll_review_pickup(
        token="ghp_fake",
        reviewer_seats=["ce-dev-4"],
        gh_runner=forge.runner,
        transport=transport,
        repo="o/r",
        apply=True,
    )

    assert len(result.items) == 1
    item = result.items[0]
    assert item["reason"] == "awaiting_review"
    assert item["assigned_reviewer"] == "ce-dev-4"
    assert item["re_request_review_ids"] == [12]
    assert forge.dismissals == []
    assert len(forge.review_requests) == 1
    assert '"ce-dev-4"' in (forge.review_requests[0][1] or "")
    assert '"ce-dev-3"' not in (forge.review_requests[0][1] or "")


def test_poll_review_pickup_requires_seat_and_token():
    forge = _FakeReviewPickupForge()
    with pytest.raises(review_pickup.PickupError):
        review_pickup.poll_review_pickup(
            token="ghp_fake", reviewer_seats=[], gh_runner=forge.runner,
            transport=_fake_transport([]),
        )
    with pytest.raises(review_pickup.PickupError):
        review_pickup.poll_review_pickup(
            token="  ", reviewer_seats=["ce-dev-3"], gh_runner=forge.runner,
            transport=_fake_transport([]),
        )


def test_cev3_review_pickup_routes_with_json(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import v3_cli

    pat = tmp_path / "controller.pat"
    pat.write_text("ghp_t\n", encoding="utf-8")
    forge = _FakeReviewPickupForge(author="ce-dev-2", head="d" * 40)
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    monkeypatch.setattr(
        v3_cli,
        "_review_pickup_transport",
        lambda: _fake_transport([(200, {}, _body(_hit(repo="o/r", number=12, pr=True)))]),
    )
    monkeypatch.setattr(v3_cli, "_review_pickup_gh_runner", lambda identity, token: forge.runner)
    inbox_path = tmp_path / "awaiting-review.json"

    code = v3_cli.main([
        "review-pickup",
        "--identity", "controller",
        "--keys-dir", str(tmp_path),
        "--repo", "o/r",
        "--seat", "ce-dev-2,ce-dev-3",
        "--apply",
        "--once",
        "--interval", "0",
        "--inbox-path", str(inbox_path),
        "--json",
    ])

    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["mode"] == "once"
    assert out["inbox_path"] == str(inbox_path)
    assert out["awaiting_decision_count"] == 0
    assert out["items"][0]["assigned_reviewer"] == "ce-dev-3"
    assert out["items"][0]["requested"] is True
    assert json.loads(inbox_path.read_text(encoding="utf-8"))["records"] == []


def test_cev3_review_pickup_loop_requires_positive_interval(capsys):
    from creator_engine_validator import v3_cli

    code = v3_cli.main([
        "review-pickup",
        "--identity", "controller",
        "--repo", "o/r",
        "--seat", "ce-dev-3",
        "--loop",
        "--interval", "0",
        "--json",
    ])

    assert code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["mode"] == "loop"
    assert out["error"] == "review_pickup_input"
