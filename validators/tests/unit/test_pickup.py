"""Unit tests for the ce-ops#55/#182 autonomous forge work-pickup poller.

``creator_engine_validator.pickup`` is a per-seat READ-ONLY poller over the
GitHub Search API (``GET /search/issues``). It resolves Search hits into a
normalized work-item ``{repo, kind, number, url, reason, thread_id}``, using a
stable synthetic ``search:{reason}:{repo}:{kind}:{number}`` thread id because
Search has no notification thread id.

Per the CE Ring-0 launch refusals (CC-D-2 / CDX-D-1), the poller is read-only and NEVER
authors; actual work runs as a fresh governed lane via ``ce lane launch``. These tests
inject a fake HTTP transport and perform ZERO live network / subprocess.

S1 — observe-only. S2 — claim + dedup ledger (dry-run). S3 — ``ce lane launch`` wiring
behind a per-seat enable flag (canary, default OFF).
"""

import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import pickup
from creator_engine_validator.checks.active_work_ledger_schema import (
    validate_active_work_ledger_record,
)


# ---------------------------------------------------------------------------
# Fake Search API transport — records every (method, url, headers) call and
# returns a scripted (status, headers, body) per call. Mirrors the app_jwt seam.
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


def _empty_search():
    return (200, {}, _body())


def _empty_searches(count):
    return [_empty_search() for _ in range(count)]


def _queries_from_calls(calls):
    return [
        urllib.parse.parse_qs(urllib.parse.urlparse(call["url"]).query)["q"][0]
        for call in calls
    ]


def _assert_explicit_search_type(query):
    """Reject a Search ``q`` lacking exactly one ``is:pull-request``/``is:issue``.

    This is the offline stand-in for GitHub's issues-search ``HTTP 422`` ("Query
    must include 'is:issue' or 'is:pull-request'") that the ce-ops#182 belt feed
    tripped live. The fake transport calls this on every issued query.
    """
    terms = query.split()
    type_terms = sum(term in {"is:pull-request", "is:issue"} for term in terms)
    assert type_terms == 1, (
        "search query must carry exactly one is:pull-request/is:issue type "
        f"qualifier (GitHub returns HTTP 422 otherwise); got {query!r}"
    )


def _fake_transport(responses, calls=None):
    """Yield a scripted response per call. Each response is (status, headers, body).

    The fake mirrors GitHub's issues-search contract: every issued ``q`` MUST
    carry exactly one ``is:pull-request`` / ``is:issue`` type qualifier. A query
    lacking it is rejected here (an ``AssertionError``, standing in for GitHub's
    real ``HTTP 422: "Query must include 'is:issue' or 'is:pull-request'"``) so
    the ce-ops#182 untyped-query class of bug can NEVER slip past the offline
    tests again — no per-test opt-in required.
    """
    seq = list(responses)

    def transport(method, url, headers, body):
        if calls is not None:
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("q", [""])[0]
        _assert_explicit_search_type(query)
        status, resp_headers, resp_body = seq.pop(0)
        return status, dict(resp_headers), resp_body

    return transport


_ACTIONABLE_RESPONSES = [
    (200, {}, _body(_hit(number=10, pr=True))),
    _empty_search(),
    (200, {}, _body(_hit(number=11, pr=False))),
    _empty_search(),
    (200, {}, _body(_hit(number=12, pr=False))),
]


# ---------------------------------------------------------------------------
# poll() — Search API happy path, reason mapping, labels, rate limits.
# ---------------------------------------------------------------------------


def test_build_queries_maps_reasons_scopes_and_labels():
    specs = pickup.build_queries(labels=["team/feed", "ops,triage"], repo="o/r")
    assert [s.reason for s in specs] == [
        "review_requested",
        "assigned", "assigned",
        "mention", "mention",
        "labeled", "labeled",
        "labeled", "labeled",
        "labeled", "labeled",
    ]
    assert specs[0].query == "is:open is:pull-request review-requested:@me repo:o/r"
    assert specs[1].query == "is:open is:pull-request assignee:@me repo:o/r"
    assert specs[2].query == "is:open is:issue assignee:@me repo:o/r"
    assert specs[3].query == "is:open is:pull-request mentions:@me repo:o/r"
    assert specs[4].query == "is:open is:issue mentions:@me repo:o/r"
    assert specs[5].query == 'is:open is:pull-request label:"team/feed" repo:o/r'
    assert specs[6].query == 'is:open is:issue label:"team/feed" repo:o/r'
    assert specs[7].query == 'is:open is:pull-request label:"ops" repo:o/r'
    assert specs[8].query == 'is:open is:issue label:"ops" repo:o/r'
    assert specs[9].query == 'is:open is:pull-request label:"triage" repo:o/r'
    assert specs[10].query == 'is:open is:issue label:"triage" repo:o/r'
    for spec in specs:
        _assert_explicit_search_type(spec.query)


def test_build_queries_refuses_unscoped_label():
    with pytest.raises(pickup.PickupError) as exc:
        pickup.build_queries(labels=["ready"])
    assert "--label requires an explicit Search scope" in str(exc.value)


def test_poll_resolves_search_hits_and_reason_mapping():
    transport = _fake_transport(_ACTIONABLE_RESPONSES)
    result = pickup.poll(token="ghp_fake", transport=transport)

    kinds = {(i["kind"], i["number"]) for i in result.items}
    assert ("review_requested", 10) in kinds
    assert ("assigned", 11) in kinds
    assert ("mention", 12) in kinds
    assert len(result.items) == 3
    assert result.poll_interval == 300
    assert result.not_modified is False


def test_poll_item_shape_is_normalized_with_synthetic_thread_id():
    transport = _fake_transport([
        (200, {}, _body(_hit(repo="o/r", number=7, pr=True))),
        *_empty_searches(4),
    ])
    result = pickup.poll(token="ghp_fake", transport=transport)
    item = result.items[0]
    assert item["repo"] == "o/r"
    assert item["kind"] == "review_requested"
    assert item["number"] == 7
    assert item["reason"] == "review_requested"
    assert item["url"] == "https://github.com/o/r/pull/7"
    assert item["subject_type"] == "PullRequest"
    assert item["thread_id"] == "search:review_requested:o/r:review_requested:7"


def test_poll_label_option_maps_to_labeled_kind_and_adds_query():
    calls = []
    transport = _fake_transport([
        *_empty_searches(6),
        (200, {}, _body(_hit(repo="o/r", number=5, pr=False))),
    ], calls=calls)
    result = pickup.poll(token="ghp_fake", transport=transport, labels=["team/feed"], org="creator-engine")
    assert result.items[0]["kind"] == "labeled"
    assert result.items[0]["url"] == "https://github.com/o/r/issues/5"
    queries = _queries_from_calls(calls)
    assert queries[-2] == 'is:open is:pull-request label:"team/feed" org:creator-engine'
    assert queries[-1] == 'is:open is:issue label:"team/feed" org:creator-engine'
    for query in queries:
        _assert_explicit_search_type(query)


def test_poll_unscoped_label_fails_before_transport_call():
    calls = []

    def transport(method, url, headers, body):
        calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        raise AssertionError("transport should not be called for unscoped labels")

    with pytest.raises(pickup.PickupError) as exc:
        pickup.poll(token="ghp_fake", transport=transport, labels=["ready"])
    assert "--label requires an explicit Search scope" in str(exc.value)
    assert calls == []


def test_poll_dedupes_overlapping_queries_by_repo_number():
    transport = _fake_transport([
        (200, {}, _body(_hit(repo="o/r", number=7, pr=True))),
        (200, {}, _body(_hit(repo="o/r", number=7, pr=True))),
        *_empty_searches(3),
    ])
    result = pickup.poll(token="ghp_fake", transport=transport)
    assert len(result.items) == 1
    assert result.items[0]["reason"] == "review_requested"


def test_poll_default_poll_interval_when_header_absent():
    transport = _fake_transport(_empty_searches(5))
    result = pickup.poll(token="ghp_fake", transport=transport)
    assert result.poll_interval == pickup.DEFAULT_POLL_INTERVAL


def test_poll_sends_auth_header_api_version_and_search_url():
    calls = []
    transport = _fake_transport(_empty_searches(5), calls=calls)
    pickup.poll(token="ghp_secret", transport=transport)
    assert calls[0]["headers"]["Authorization"] == "Bearer ghp_secret"
    assert "X-GitHub-Api-Version" in calls[0]["headers"]
    assert "/search/issues?" in calls[0]["url"]
    parsed = urllib.parse.urlparse(calls[0]["url"])
    assert urllib.parse.parse_qs(parsed.query)["q"][0] == "is:open is:pull-request review-requested:@me"
    assert calls[0]["method"] == "GET"
    for query in _queries_from_calls(calls):
        _assert_explicit_search_type(query)


def test_poll_403_rate_limit_fails_closed_with_retry_after():
    transport = _fake_transport([(403, {"Retry-After": "120", "X-RateLimit-Reset": "1782000000"}, "{}")])
    with pytest.raises(pickup.PickupRateLimited) as exc:
        pickup.poll(token="ghp_fake", transport=transport)
    assert exc.value.status == 403
    assert exc.value.retry_after_seconds == 120
    assert exc.value.rate_limit_reset == "1782000000"


def test_poll_429_rate_limit_fails_closed():
    transport = _fake_transport([(429, {"Retry-After": "60"}, "{}")])
    with pytest.raises(pickup.PickupRateLimited) as exc:
        pickup.poll(token="ghp_fake", transport=transport)
    assert exc.value.status == 429
    assert exc.value.to_payload()["retry_after_seconds"] == 60


def test_poll_auth_error_is_fail_closed_and_redacted():
    transport = _fake_transport([(401, {}, '{"message":"Bad credentials"}')])
    with pytest.raises(pickup.PickupError) as exc:
        pickup.poll(token="ghp_secret_should_not_leak", transport=transport)
    assert "401" in str(exc.value)
    assert "ghp_secret_should_not_leak" not in str(exc.value)


def test_poll_requires_a_token():
    with pytest.raises(pickup.PickupError):
        pickup.poll(token="", transport=_fake_transport([_empty_search()]))


def test_fake_transport_rejects_untyped_query_like_github_422():
    """The fake transport mirrors GitHub's 422: a query lacking a type qualifier
    is rejected (this is what let the ce-ops#182 bug ship — the fake was lenient).

    We drive the transport directly with an untyped ``q`` (as the buggy belt feed
    issued) and assert it raises, proving an untyped query can't pass the offline
    tests anymore.
    """
    transport = _fake_transport([_empty_search()])
    untyped_url = f"{pickup._API_ROOT}/search/issues?" + urllib.parse.urlencode(
        {"q": "is:open review-requested:@me"}
    )
    with pytest.raises(AssertionError) as exc:
        transport("GET", untyped_url, {}, None)
    assert "is:pull-request" in str(exc.value) and "is:issue" in str(exc.value)


# ---------------------------------------------------------------------------
# Token resolution from env / ~/.ce-keys/ce-dev-N.pat
# ---------------------------------------------------------------------------


def test_resolve_token_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CE_PICKUP_TOKEN", "ghp_env")
    assert pickup.resolve_token(keys_dir=tmp_path, identity="ce-dev-2") == "ghp_env"


def test_resolve_token_reads_per_identity_pat(monkeypatch, tmp_path):
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_fromfile\n", encoding="utf-8")
    assert pickup.resolve_token(keys_dir=tmp_path, identity="ce-dev-2") == "ghp_fromfile"


def test_resolve_token_ambient_gh_requires_opt_in(monkeypatch, tmp_path):
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    monkeypatch.delenv("CE_PICKUP_ALLOW_AMBIENT_GH", raising=False)
    monkeypatch.setenv("GH_TOKEN", "gho_ambient")
    with pytest.raises(pickup.PickupError):
        pickup.resolve_token(keys_dir=tmp_path, identity="ce-dev-9")


def test_resolve_token_reads_ambient_gh_when_opted_in(monkeypatch, tmp_path):
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    proc = subprocess.CompletedProcess(["gh", "auth", "token"], 0, stdout="gho_ambient\n", stderr="")
    assert pickup.resolve_token(
        keys_dir=tmp_path,
        identity="ce-dev-9",
        allow_ambient_gh=True,
        gh_token_runner=lambda: proc,
    ) == "gho_ambient"


def test_resolve_token_missing_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    monkeypatch.delenv("CE_PICKUP_ALLOW_AMBIENT_GH", raising=False)
    with pytest.raises(pickup.PickupError):
        pickup.resolve_token(keys_dir=tmp_path, identity="ce-dev-9")


# ---------------------------------------------------------------------------
# CLI surface — `ce pickup poll` (observe-only, JSON out).
# ---------------------------------------------------------------------------


def test_cli_pickup_poll_observe_only_emits_items(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_clitoken\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    monkeypatch.setattr(
        ce_cli, "_make_pickup_transport",
        lambda: _fake_transport(_ACTIONABLE_RESPONSES),
    )
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2",
        "--keys-dir", str(tmp_path), "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["count"] == 3
    assert out["poll_interval"] == 300
    # observe-only: no claim, no launch fields.
    kinds = {i["kind"] for i in out["items"]}
    assert kinds == {"review_requested", "assigned", "mention"}


def test_cli_pickup_poll_unscoped_label_fails_before_transport(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_clitoken\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)

    def should_not_make_transport():
        raise AssertionError("transport factory should not be called for unscoped labels")

    monkeypatch.setattr(ce_cli, "_make_pickup_transport", should_not_make_transport)
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2",
        "--keys-dir", str(tmp_path), "--label", "ready", "--json",
    ])
    assert code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "--label requires an explicit Search scope" in out["error"]


def test_cli_pickup_poll_scoped_label_still_emits_labeled_item(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_clitoken\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ce_cli,
        "_make_pickup_transport",
        lambda: _fake_transport([
            *_empty_searches(6),
            (200, {}, _body(_hit(repo="o/r", number=23, pr=False))),
        ], calls=calls),
    )
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2",
        "--keys-dir", str(tmp_path), "--label", "ready", "--org", "creator-engine", "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["items"][0]["kind"] == "labeled"
    queries = _queries_from_calls(calls)
    assert queries[-2] == 'is:open is:pull-request label:"ready" org:creator-engine'
    assert queries[-1] == 'is:open is:issue label:"ready" org:creator-engine'
    for query in queries:
        _assert_explicit_search_type(query)


def test_cli_pickup_poll_help_mentions_search_label_and_launch(capsys):
    from creator_engine_validator import ce_cli

    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["pickup", "poll", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Search API" in out
    assert "--label" in out
    assert "--enable-launch" in out


def test_cli_pickup_poll_rate_limit_json_fail_closed(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_clitoken\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    monkeypatch.setattr(
        ce_cli, "_make_pickup_transport",
        lambda: _fake_transport([(429, {"Retry-After": "60"}, "{}")]),
    )
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2",
        "--keys-dir", str(tmp_path), "--json",
    ])
    assert code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["backoff"]["status"] == 429
    assert out["backoff"]["retry_after_seconds"] == 60


def test_cli_pickup_poll_missing_token_exit_2(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    monkeypatch.delenv("CE_PICKUP_ALLOW_AMBIENT_GH", raising=False)
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-9", "--keys-dir", str(tmp_path),
    ])
    assert code == 2


# ===========================================================================
# S2 — claim + idempotency (dry-run).
# ===========================================================================

from creator_engine_validator import work_claims  # noqa: E402


class _FakeForge:
    """A shared in-memory GitHub issue/PR store driving a work_claims.GhRunner.

    Two pollers built over the SAME store race through one comment list, so the
    deterministic re-read winner in ``work_claims.acquire`` is exercised for real.
    Also tracks assignees so the self-assign side effect is observable.
    """

    def __init__(self, pr_author=None):
        self.comments: list[dict] = []
        self._next_id = 1
        self.assignees: list[str] = []
        self.pr_author = pr_author
        self.raw_calls: list[list[str]] = []
        self.read_threads: list[str] = []

    def runner(self, identity):
        def gh(argv, input_text=None):
            self.raw_calls.append(list(argv))
            return self._dispatch(list(argv), input_text, identity)
        return gh

    def _dispatch(self, argv, input_text, identity):
        # argv shape: ["gh", "api", ("--method", M)?, <path>, ("-f"|"--input" "-")?]
        method = "GET"
        path = ""
        i = 2  # skip "gh", "api"
        while i < len(argv):
            tok = argv[i]
            if tok == "--method":
                method = argv[i + 1]
                i += 2
                continue
            if tok in ("-f", "--input"):
                i += 2
                continue
            if not tok.startswith("-") and not path:
                path = tok.split("?", 1)[0]  # strip query string
            i += 1
        body = json.loads(input_text) if input_text else None

        if path.endswith("/comments") and method == "GET":
            return self._ok(self.comments)
        if path.endswith("/comments") and method == "POST":
            cid = self._next_id
            self._next_id += 1
            comment = {"id": cid, "body": body["body"],
                       "created_at": "2026-06-21T00:00:00Z",
                       "user": {"login": identity}}
            self.comments.append(comment)
            return self._ok({"id": cid, "html_url": f"https://github.com/x/y#c{cid}"})
        if path.endswith("/assignees") and method == "POST":
            for a in (body or {}).get("assignees", []):
                if a not in self.assignees:
                    self.assignees.append(a)
            return self._ok({"assignees": [{"login": a} for a in self.assignees]})
        if path.startswith("notifications/threads/") and method in ("PATCH", "DELETE"):
            self.read_threads.append(path.rsplit("/", 1)[-1])
            return self._ok({})
        return self._ok({})

    @staticmethod
    def _ok(payload):
        return subprocess.CompletedProcess([], 0, stdout=json.dumps(payload), stderr="")


def _item(kind="review_requested", repo="o/r", number=10, thread_id="t1"):
    return {
        "repo": repo, "kind": kind, "number": number,
        "url": f"https://github.com/{repo}/pull/{number}",
        "reason": kind, "thread_id": thread_id,
        "title": "x", "subject_type": "PullRequest",
    }


def test_claim_item_acquires_and_self_assigns(tmp_path):
    forge = _FakeForge(pr_author="someone-else")
    ledger = tmp_path / "pickup" / "ledger.ndjson"
    outcome = pickup.claim_item(
        _item(kind="assigned"), identity="ce-dev-2",
        gh_runner=forge.runner("ce-dev-2"), ledger_path=ledger,
        run_id="run-1", backoff_seconds=0,
    )
    assert outcome.claimed is True
    assert outcome.reason == "claimed"
    # self-assigned to the picking identity.
    assert "ce-dev-2" in forge.assignees
    # dedup ledger now records the claim.
    records = pickup.load_ledger(ledger)
    assert len(records) == 1
    assert records[0]["thread_id"] == "t1"


def test_claim_item_is_idempotent_via_ledger(tmp_path):
    forge = _FakeForge()
    ledger = tmp_path / "ledger.ndjson"
    item = _item(kind="assigned")
    first = pickup.claim_item(item, identity="ce-dev-2", gh_runner=forge.runner("ce-dev-2"),
                              ledger_path=ledger, run_id="run-1", backoff_seconds=0)
    assert first.claimed is True
    # Second pass over the same thread → dedup short-circuit, no new claim posted.
    posted_before = len(forge.comments)
    second = pickup.claim_item(item, identity="ce-dev-2", gh_runner=forge.runner("ce-dev-2"),
                               ledger_path=ledger, run_id="run-2", backoff_seconds=0)
    assert second.claimed is False
    assert second.reason == "already_seen"
    assert len(forge.comments) == posted_before  # no second acquire comment


def test_two_pollers_same_item_only_one_claims(tmp_path):
    # Both pollers share ONE forge store but are DISTINCT identities/ledgers.
    forge = _FakeForge()
    a = pickup.claim_item(_item(kind="assigned"), identity="ce-dev-2",
                          gh_runner=forge.runner("ce-dev-2"),
                          ledger_path=tmp_path / "a.ndjson", run_id="A", backoff_seconds=0)
    b = pickup.claim_item(_item(kind="assigned"), identity="ce-dev-3",
                          gh_runner=forge.runner("ce-dev-3"),
                          ledger_path=tmp_path / "b.ndjson", run_id="B", backoff_seconds=0)
    claimed = [o for o in (a, b) if o.claimed]
    assert len(claimed) == 1  # exactly one wins; the other fails closed
    loser = a if not a.claimed else b
    assert loser.reason in ("active_foreign_claim", "lost_after_reread", "stale_foreign_claim")


def test_review_requested_own_pr_is_refused(tmp_path):
    # The PR author IS the picking identity → independent-reviewer refusal.
    forge = _FakeForge(pr_author="ce-dev-2")
    outcome = pickup.claim_item(
        _item(kind="review_requested"), identity="ce-dev-2",
        gh_runner=forge.runner("ce-dev-2"), ledger_path=tmp_path / "l.ndjson",
        run_id="r", backoff_seconds=0,
        pr_author_lookup=lambda item, runner: "ce-dev-2",
    )
    assert outcome.claimed is False
    assert outcome.reason == "own_pr_review_refused"
    # nothing posted, nothing assigned — fully fail-closed.
    assert forge.comments == []
    assert forge.assignees == []


def test_review_requested_unknown_pr_author_is_refused_fail_closed(tmp_path):
    forge = _FakeForge()
    ledger = tmp_path / "l.ndjson"
    outcome = pickup.claim_item(
        _item(kind="review_requested"), identity="ce-dev-2",
        gh_runner=forge.runner("ce-dev-2"), ledger_path=ledger,
        run_id="r", backoff_seconds=0,
        pr_author_lookup=lambda item, runner: None,
    )
    assert outcome.claimed is False
    assert outcome.reason == "pr_author_unknown_refused"
    assert forge.comments == []
    assert forge.assignees == []
    assert not ledger.exists()


def test_review_requested_foreign_pr_is_claimable(tmp_path):
    forge = _FakeForge()
    outcome = pickup.claim_item(
        _item(kind="review_requested"), identity="ce-dev-2",
        gh_runner=forge.runner("ce-dev-2"), ledger_path=tmp_path / "l.ndjson",
        run_id="r", backoff_seconds=0,
        pr_author_lookup=lambda item, runner: "another-dev",
    )
    assert outcome.claimed is True


def test_ledger_key_uses_server_fields_not_wall_clock():
    # the dedup key is (thread_id, item_id, action) — no clock term.
    k = pickup.ledger_key("t1", "10", "claim")
    assert k == ("t1", "10", "claim")


# ===========================================================================
# S3 — `ce lane launch` wiring (canary, gated behind --enable-launch).
# ===========================================================================


def test_build_seed_writes_file_and_returns_sha(tmp_path):
    seed_dir = tmp_path / "seeds"
    seed = pickup.build_seed(_item(kind="assigned"), identity="ce-dev-2",
                             run_id="r1", claim_id="wclaim-abc", seed_root=seed_dir)
    assert Path(seed.path).is_file()
    body = Path(seed.path).read_text(encoding="utf-8")
    assert "o/r" in body and "#10" in body
    # the SHA matches the file bytes (the do_not_replan SHA-binding shape).
    import hashlib
    assert seed.sha256 == hashlib.sha256(body.encode("utf-8")).hexdigest()


def test_launch_lane_invokes_lane_launch_with_seed_and_harness(tmp_path):
    calls = []

    def fake_spawn(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "launched",
                               "pane_path": "/x", "record": {}}),
            stderr="",
        )

    result = pickup.launch_lane(
        _item(kind="review_requested"), identity="ce-dev-2", run_id="r1",
        claim_id="wclaim-abc", harness="claude",
        seed_root=tmp_path / "seeds", repo_root=str(tmp_path),
        ledger_root=str(tmp_path / "awl"), spawn=fake_spawn,
    )
    assert result.launched is True
    argv = calls[0]
    # invokes the lane CLI by module, independent of a bare `ce` executable on PATH.
    assert argv[0] == sys.executable
    assert argv[1:3] == ["-m", "creator_engine_validator.ce_cli"]
    assert argv[0] != "ce"
    assert argv[3:5] == ["lane", "launch"]
    assert "--prompt" in argv and "--prompt-sha" in argv
    # review_requested → a reviewer role lane; the harness rides --command.
    role_idx = argv.index("--role")
    assert argv[role_idx + 1] == "reviewer"
    cmd_idx = argv.index("--command")
    assert argv[cmd_idx + 1] == "claude"


def test_launch_lane_failure_does_not_mark_launched(tmp_path):
    def fake_spawn(argv):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

    result = pickup.launch_lane(
        _item(kind="assigned"), identity="ce-dev-2", run_id="r1", claim_id="c",
        harness="codex", seed_root=tmp_path / "s", repo_root=str(tmp_path),
        ledger_root=str(tmp_path / "awl"), spawn=fake_spawn,
    )
    assert result.launched is False


def test_launch_lane_allocates_active_work_claim_before_spawn(tmp_path):
    """ce-ops#200: poll/claim → ALLOCATE → launch → LAUNCHED_STATE.

    The belt's launch path must write the live, unreleased Active-Work claim YAML
    that ``ce lane launch`` hard-requires (RV1-030, G3-CLAIM-MISSING) BEFORE the
    spawn — otherwise every belt-launched lane refuses with exit 1. The fake spawn
    asserts the claim (and its lease) already exist at the moment ``lane launch``
    would run, in the SAME ledger root the argv forwards to ``--ledger-root``.
    """
    from creator_engine_validator import lane_runtime

    awl = tmp_path / "awl"
    identity = "ce-dev-2"
    run_id = "r1"
    item = _item(kind="review_requested", repo="o/r", number=10)
    expected_lane_id = pickup._lane_id(item, run_id)
    claim_path = lane_runtime._claim_path(awl, identity, expected_lane_id)
    lease_path = awl / "leases" / identity / f"{expected_lane_id}.yaml"

    seen = {}

    def fake_spawn(argv):
        # The allocation MUST have happened before the spawn (= before lane launch).
        seen["claim_exists_at_spawn"] = claim_path.is_file()
        seen["lease_exists_at_spawn"] = lease_path.is_file()
        # The argv forwards the SAME ledger root the claim was allocated under.
        lr_idx = argv.index("--ledger-root")
        seen["argv_ledger_root"] = argv[lr_idx + 1]
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "launched"}), stderr="")

    result = pickup.launch_lane(
        item, identity=identity, run_id=run_id, claim_id="wclaim-abc",
        harness="claude", seed_root=tmp_path / "seeds", repo_root=str(tmp_path),
        ledger_root=str(awl), spawn=fake_spawn,
    )

    assert result.launched is True
    assert result.lane_id == expected_lane_id
    assert seen["claim_exists_at_spawn"] is True
    assert seen["lease_exists_at_spawn"] is True
    assert seen["argv_ledger_root"] == str(awl)

    # The written claim is schema-valid, live (unreleased), and matches identity/lane
    # — exactly what lane launch's G3-CLAIM-MISSING gate checks.
    claim = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert claim["controller_id"] == identity
    assert claim["lane_id"] == expected_lane_id
    assert "released_at" not in claim
    assert validate_active_work_ledger_record(claim, claim_path) == []


def test_launch_lane_allocation_is_idempotent_on_repoll(tmp_path):
    """A re-poll of an already-claimed item must NOT double-allocate or crash."""
    awl = tmp_path / "awl"
    item = _item(kind="assigned", repo="o/r", number=10)

    def fake_spawn(argv):
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "launched"}), stderr="")

    kwargs = dict(
        identity="ce-dev-2", run_id="r1", claim_id="c", harness="codex",
        seed_root=tmp_path / "s", repo_root=str(tmp_path),
        ledger_root=str(awl), spawn=fake_spawn,
    )
    first = pickup.launch_lane(item, **kwargs)
    second = pickup.launch_lane(item, **kwargs)
    assert first.launched is True
    assert second.launched is True  # idempotent: live claim reused, no refusal/crash


def test_mark_thread_read_only_after_launched(tmp_path):
    forge = _FakeForge()
    calls = []

    def gh(argv, input_text=None):
        calls.append(list(argv))
        return subprocess.CompletedProcess([], 0, stdout="{}", stderr="")

    assert pickup.mark_thread_read("search:assigned:o/r:assigned:1", gh_runner=gh) is False
    assert calls == []

    assert pickup.mark_thread_read("t1", gh_runner=gh) is True
    # legacy notification ids can still be marked read.
    assert any("notifications/threads/t1" in a for c in calls for a in c)


def test_cli_enable_launch_does_not_mark_synthetic_search_thread_read(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    forge = _FakeForge()
    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_t\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    responses = [
        _empty_search(),
        _empty_search(),
        (200, {}, _body(_hit(repo="o/r", number=21, pr=False))),
        *_empty_searches(2),
    ]
    monkeypatch.setattr(ce_cli, "_make_pickup_transport",
                        lambda: _fake_transport(responses))
    monkeypatch.setattr(ce_cli, "_make_pickup_gh_runner", lambda identity: forge.runner(identity))

    launched_argvs = []

    def fake_spawn(argv):
        launched_argvs.append(argv)
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "launched"}), stderr="")

    monkeypatch.setattr(ce_cli, "_make_pickup_lane_spawn", lambda: fake_spawn)

    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2", "--keys-dir", str(tmp_path),
        "--claim", "--enable-launch", "--harness", "codex",
        "--ledger-root", str(tmp_path / "pickup"),
        "--repo-root", str(tmp_path), "--lane-ledger-root", str(tmp_path / "awl"),
        "--run-id", "run-z", "--backoff-seconds", "0", "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    claim = out["claims"][0]
    assert claim["claimed"] is True
    assert claim["launched"] is True
    assert claim["would_launch"] is False
    assert launched_argvs  # the lane primitive was invoked
    assert claim["thread_marked_read"] is False
    assert forge.read_threads == []


def test_flag_off_stays_dry_run(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    forge = _FakeForge()
    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_t\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    responses = [
        _empty_search(),
        _empty_search(),
        (200, {}, _body(_hit(repo="o/r", number=11, pr=False))),
        *_empty_searches(2),
    ]
    monkeypatch.setattr(ce_cli, "_make_pickup_transport",
                        lambda: _fake_transport(responses))
    monkeypatch.setattr(ce_cli, "_make_pickup_gh_runner", lambda identity: forge.runner(identity))

    spawned = []
    monkeypatch.setattr(ce_cli, "_make_pickup_lane_spawn",
                        lambda: (lambda argv: spawned.append(argv)))

    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2", "--keys-dir", str(tmp_path),
        "--claim", "--ledger-root", str(tmp_path / "pickup"),
        "--run-id", "run-x", "--backoff-seconds", "0", "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["claims"][0]["would_launch"] is True
    assert out["claims"][0]["launched"] is False
    assert spawned == []  # flag OFF → no lane spawn at all


def test_cli_claim_without_launch_uses_default_state_root_and_records_ledger(
    monkeypatch, tmp_path, capsys
):
    from creator_engine_validator import ce_cli

    forge = _FakeForge()
    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_t\n", encoding="utf-8")
    state_root = tmp_path / ".ce" / "state"
    monkeypatch.setattr(ce_cli, "V3_LOCAL_STATE_ROOT", str(state_root))
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    responses = [
        _empty_search(),
        _empty_search(),
        (200, {}, _body(_hit(repo="o/r", number=11, pr=False))),
        *_empty_searches(2),
    ]
    monkeypatch.setattr(ce_cli, "_make_pickup_transport",
                        lambda: _fake_transport(responses))
    monkeypatch.setattr(ce_cli, "_make_pickup_gh_runner", lambda identity: forge.runner(identity))

    spawned = []
    monkeypatch.setattr(ce_cli, "_make_pickup_lane_spawn",
                        lambda: (lambda argv: spawned.append(argv)))

    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2", "--keys-dir", str(tmp_path),
        "--claim", "--run-id", "run-default-root", "--backoff-seconds", "0", "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    claim = out["claims"][0]
    assert claim["claimed"] is True
    assert claim["would_launch"] is True
    assert claim["launched"] is False
    assert spawned == []  # no --enable-launch → no lane spawn

    ledger = state_root / "pickup" / pickup.DEFAULT_LEDGER_NAME
    records = pickup.load_ledger(ledger)
    assert len(records) == 1
    assert records[0]["thread_id"] == "search:assigned:o/r:assigned:11"
    assert records[0]["run_id"] == "run-default-root"


def test_dry_run_cli_reports_would_launch(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    forge = _FakeForge()
    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_t\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    responses = [
        _empty_search(),
        _empty_search(),
        (200, {}, _body(_hit(repo="o/r", number=11, pr=False))),
        *_empty_searches(2),
    ]
    monkeypatch.setattr(ce_cli, "_make_pickup_transport",
                        lambda: _fake_transport(responses))
    monkeypatch.setattr(ce_cli, "_make_pickup_gh_runner", lambda identity: forge.runner(identity))
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2", "--keys-dir", str(tmp_path),
        "--claim", "--ledger-root", str(tmp_path / "pickup"), "--run-id", "run-x",
        "--backoff-seconds", "0", "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    # claimed, but dry-run (no --enable-launch): "would launch", not launched.
    claim = out["claims"][0]
    assert claim["claimed"] is True
    assert claim["launched"] is False
    assert claim["would_launch"] is True
