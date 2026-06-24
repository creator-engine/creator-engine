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


class _FakeReviewPickupForge:
    def __init__(self, *, author="author-a", head="h" * 40, requested=None, reviews=None):
        self.author = author
        self.head = head
        self.requested = list(requested or [])
        self.reviews = list(reviews or [])
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
        if bare_path.endswith("/reviews") and method == "GET":
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.reviews), stderr="")
        if "/pulls/" in bare_path and method == "GET":
            payload = {
                "user": {"login": self.author},
                "head": {"sha": self.head},
                "requested_reviewers": [{"login": r} for r in self.requested],
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr=f"unexpected {method} {path}")


def test_review_pickup_query_is_typed_and_scoped():
    spec = review_pickup.review_pickup_query(repo="o/r")
    assert spec.reason == "awaiting_review"
    assert spec.query == "is:open is:pull-request repo:o/r"
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
        reviewer_seats=["ce-dev-4"],
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

    code = v3_cli.main([
        "review-pickup",
        "--identity", "controller",
        "--keys-dir", str(tmp_path),
        "--repo", "o/r",
        "--seat", "ce-dev-2,ce-dev-3",
        "--apply",
        "--json",
    ])

    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["items"][0]["assigned_reviewer"] == "ce-dev-3"
    assert out["items"][0]["requested"] is True
