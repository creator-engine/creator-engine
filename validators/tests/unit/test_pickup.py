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

import hashlib
import json
import re
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
from creator_engine_validator.checks.worktree_lease_schema import (
    validate_worktree_lease_record,
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
        assert spec.scope == pickup.SearchScope.repo("o/r")


def test_search_query_without_declared_scope_fails_closed():
    with pytest.raises(TypeError):
        pickup.SearchQuery("unsafe", "is:open is:pull-request")
    with pytest.raises(pickup.PickupError, match="SearchScope"):
        pickup.SearchQuery("unsafe", "is:open is:pull-request", scope=None)


def test_scoped_search_query_declared_scope_succeeds():
    spec = pickup.build_scoped_search_query(
        "review_requested",
        ["is:open", "is:pull-request", "review-requested:@me"],
        scope=pickup.SearchScope.viewer(),
    )
    assert spec.query == "is:open is:pull-request review-requested:@me"
    assert spec.scope == pickup.SearchScope.viewer()


def test_scoped_search_query_declared_scope_must_match_query_terms():
    with pytest.raises(pickup.PickupError, match="scope term"):
        pickup.SearchQuery(
            "unsafe",
            "is:open is:pull-request",
            scope=pickup.SearchScope.repo("o/r"),
        )


def test_manual_repo_scope_without_value_fails_closed():
    with pytest.raises(pickup.PickupError, match="valid owner/name"):
        pickup.SearchQuery(
            "unsafe",
            "is:open is:pull-request",
            scope=pickup.SearchScope("repo"),
        )


def test_manual_repo_scope_with_mismatched_term_fails_closed():
    with pytest.raises(pickup.PickupError, match="matching query term"):
        pickup.SearchQuery(
            "unsafe",
            "is:open is:pull-request repo:o/r",
            scope=pickup.SearchScope("repo", "o/r", ("repo:other/repo",)),
        )


def test_manual_viewer_scope_shape_fails_closed():
    with pytest.raises(pickup.PickupError, match="viewer search scope"):
        pickup.SearchQuery(
            "unsafe",
            "is:open is:pull-request review-requested:@me",
            scope=pickup.SearchScope("viewer", "someone", ()),
        )


def test_build_queries_declares_viewer_scope_when_repo_org_absent():
    specs = pickup.build_queries()
    assert specs
    assert {spec.scope for spec in specs} == {pickup.SearchScope.viewer()}


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


def test_cli_pickup_poll_heartbeat_marks_failed_poll(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    class CapturingHeartbeat:
        instances = []

        def __init__(self, path, **kwargs):
            self.path = path
            self.kwargs = kwargs
            self.last_pass_index = -1
            self.emissions = []
            self.instances.append(self)

        def emit(self, status, pass_index):
            self.emissions.append((status, pass_index))
            self.last_pass_index = pass_index

    CapturingHeartbeat.instances.clear()
    monkeypatch.setattr(ce_cli, "DaemonHeartbeatEmitter", CapturingHeartbeat)
    monkeypatch.setenv("CE_BELT_HEARTBEAT_PATH", str(tmp_path / "belt.json"))
    monkeypatch.setattr(pickup, "resolve_token", lambda **_kwargs: "token")
    monkeypatch.setattr(
        pickup,
        "poll",
        lambda **_kwargs: (_ for _ in ()).throw(pickup.PickupError("search unavailable")),
    )

    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-3", "--repo", "o/r", "--json",
    ])

    assert code == 2
    heartbeat = CapturingHeartbeat.instances[0]
    assert heartbeat.kwargs == {
        "daemon_id": "belt",
        "expected_interval_seconds": 120.0,
        "unit": "ce-belt-daemon.service",
        "scope": "user",
    }
    assert heartbeat.emissions == [("starting", 0), ("running", 1), ("failed", 1)]
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_cli_pickup_poll_heartbeat_resumes_pass_index_across_invocations(
    monkeypatch,
    tmp_path,
    capsys,
):
    """Per-invocation belt processes continue the persisted heartbeat index."""
    from creator_engine_validator import ce_cli
    from creator_engine_validator.daemon_heartbeat import read_heartbeat

    heartbeat_path = tmp_path / "belt.json"
    monkeypatch.setenv("CE_BELT_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.setattr(pickup, "resolve_token", lambda **_kwargs: "token")
    monkeypatch.setattr(pickup, "poll", lambda **_kwargs: pickup.PollResult())

    args = ["pickup", "poll", "--identity", "ce-dev-3", "--repo", "o/r", "--json"]
    assert ce_cli.main(args) == 0
    assert read_heartbeat(heartbeat_path)["pass_index"] == 1
    capsys.readouterr()

    assert ce_cli.main(args) == 0
    assert read_heartbeat(heartbeat_path)["pass_index"] == 2


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


def test_controller_review_request_own_pr_is_refused(tmp_path):
    forge = _FakeForge(pr_author="ce-dev-2")
    outcome = pickup.claim_item(
        _item(kind="review_request"), identity="ce-dev-2",
        gh_runner=forge.runner("ce-dev-2"), ledger_path=tmp_path / "l.ndjson",
        run_id="r", backoff_seconds=0,
        pr_author_lookup=lambda item, runner: "ce-dev-2",
    )
    assert outcome.claimed is False
    assert outcome.reason == "own_pr_review_refused"
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


def test_controller_review_request_foreign_pr_is_claimable(tmp_path):
    forge = _FakeForge()
    outcome = pickup.claim_item(
        _item(kind="review_request"), identity="ce-dev-2",
        gh_runner=forge.runner("ce-dev-2"), ledger_path=tmp_path / "l.ndjson",
        run_id="r", backoff_seconds=0,
        pr_author_lookup=lambda item, runner: "another-dev",
    )
    assert outcome.claimed is True
    assert "ce-dev-2" in forge.assignees


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
    assert seed.sha256 == hashlib.sha256(body.encode("utf-8")).hexdigest()


def _argv_value(argv, flag):
    idx = argv.index(flag)
    return argv[idx + 1]


def _assert_lane_launch_preconditions(argv, *, repo_root, ledger_root, identity, lane_id, role, lane_kind):
    """Offline stand-in for the launch gates the belt must satisfy before spawn."""
    from creator_engine_validator import brain_runtime, lane_runtime

    # ce-ops#198: the belt now dogfoods the installed ``ce`` console script as the
    # launch prefix, with a graceful fallback to the module form
    # (``<python> -m creator_engine_validator.ce_cli``) when ``ce`` is not on PATH
    # (a source-checkout / not-yet-dogfooded host). Accept either valid prefix so
    # this contract holds regardless of the test host's PATH; the ``lane launch``
    # subcommand and its flags follow whichever prefix the belt selected.
    assert argv[0] == "ce" or argv[:3] == [sys.executable, "-m", "creator_engine_validator.ce_cli"]
    launch_idx = argv.index("launch")
    assert argv[launch_idx - 1 : launch_idx + 1] == ["lane", "launch"]
    assert "--json" in argv
    assert _argv_value(argv, "--controller-id") == identity
    assert _argv_value(argv, "--lane-id") == lane_id
    assert _argv_value(argv, "--role") == role
    assert _argv_value(argv, "--lane-kind") == lane_kind
    assert _argv_value(argv, "--repo-root") == str(repo_root)
    assert _argv_value(argv, "--worktree-path") == str(repo_root)
    assert Path(_argv_value(argv, "--worktree-path")).is_dir()
    assert _argv_value(argv, "--ledger-root") == str(ledger_root)

    prompt = Path(_argv_value(argv, "--prompt"))
    assert prompt.is_file()
    prompt_sha = hashlib.sha256(prompt.read_bytes()).hexdigest()
    assert _argv_value(argv, "--prompt-sha") == prompt_sha

    claim_path = lane_runtime._claim_path(Path(ledger_root), identity, lane_id)
    assert claim_path.is_file()
    claim = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert claim["controller_id"] == identity
    assert claim["lane_id"] == lane_id
    assert "released_at" not in claim
    assert validate_active_work_ledger_record(claim, claim_path) == []

    state_root = Path(repo_root) / ".ce" / "state"
    verify = brain_runtime.verify_ledger(state_root)
    assert verify.ok, verify.errors
    payload = lane_runtime._build_lane_brain_bootstrap(state_root=state_root, role=role)
    assert payload["kind"] == "brain-bootstrap-context"


def test_launch_lane_invokes_lane_launch_with_seed_and_harness(tmp_path, monkeypatch):
    # Pin the launch prefix to the installed-``ce`` form so the assertion is
    # deterministic regardless of whether ``ce`` is on the test host's PATH
    # (ce-ops#198 made the default fall back to the module form when it is not).
    monkeypatch.setenv("CE_LANE_LAUNCH_BIN", "ce")
    calls = []
    item = _item(kind="review_requested")
    run_id = "r1"
    identity = "ce-dev-2"
    awl = tmp_path / "awl"
    lane_id = pickup._lane_id(item, run_id)

    def fake_spawn(argv):
        _assert_lane_launch_preconditions(
            argv,
            repo_root=tmp_path,
            ledger_root=awl,
            identity=identity,
            lane_id=lane_id,
            role="reviewer",
            lane_kind="review",
        )
        calls.append(argv)
        # ce-ops#205: a fully-governed ``ce lane launch --json`` reports
        # ``seat_lifecycle_state: "alive"`` (seat_lifecycle.REGISTRATION_STATE_GOVERNED),
        # NOT "launched"; the belt's success sentinel binds to that constant.
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "alive",
                               "pane_path": "/x", "record": {}}),
            stderr="",
        )

    result = pickup.launch_lane(
        item, identity=identity, run_id=run_id,
        claim_id="wclaim-abc", harness="claude",
        seed_root=tmp_path / "seeds", repo_root=str(tmp_path),
        ledger_root=str(awl), spawn=fake_spawn,
    )
    assert result.launched is True
    argv = calls[0]
    assert argv[:3] == ["ce", "lane", "launch"]
    assert "--prompt" in argv and "--prompt-sha" in argv
    # review_requested → a reviewer role lane; the harness rides --command.
    role_idx = argv.index("--role")
    assert argv[role_idx + 1] == "reviewer"
    cmd_idx = argv.index("--command")
    assert argv[cmd_idx + 1] == "claude"
    assert _argv_value(argv, "--worktree-path") == str(tmp_path)


def test_controller_review_request_launches_reviewer_lane(tmp_path):
    item = _item(kind="review_request")
    seed = pickup.build_seed(
        item,
        identity="ce-dev-3",
        run_id="r1",
        claim_id="wclaim-review",
        seed_root=tmp_path / "seeds",
    )

    argv = pickup.build_lane_argv(
        item,
        identity="ce-dev-3",
        run_id="r1",
        harness="codex",
        seed=seed,
        repo_root=str(tmp_path),
        ledger_root=str(tmp_path / "awl"),
    )

    assert _argv_value(argv, "--role") == "reviewer"
    assert _argv_value(argv, "--lane-kind") == "review"
    assert _argv_value(argv, "--command") == "codex"
    assert "reviewer lane" in Path(seed.path).read_text(encoding="utf-8")


def test_build_lane_argv_can_use_python_module_compatibility_command(tmp_path):
    seed = pickup.build_seed(
        _item(kind="assigned"), identity="ce-dev-2", run_id="r1",
        claim_id="wclaim-abc", seed_root=tmp_path / "seeds",
    )
    argv = pickup.build_lane_argv(
        _item(kind="assigned"), identity="ce-dev-2", run_id="r1",
        harness="codex", seed=seed, repo_root=str(tmp_path),
        ledger_root=str(tmp_path / "awl"),
        ce_command=["python", "-m", "creator_engine_validator.ce_cli"],
    )
    assert argv[:5] == ["python", "-m", "creator_engine_validator.ce_cli", "lane", "launch"]


def test_lane_launch_command_env_override_is_shell_split(monkeypatch):
    monkeypatch.setenv(
        pickup.CE_LANE_LAUNCH_BIN_ENV,
        "python -m creator_engine_validator.ce_cli",
    )
    assert pickup.lane_launch_command() == ["python", "-m", "creator_engine_validator.ce_cli"]


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
            stdout=json.dumps({"seat_lifecycle_state": "alive"}), stderr="")

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
            stdout=json.dumps({"seat_lifecycle_state": "alive"}), stderr="")

    kwargs = dict(
        identity="ce-dev-2", run_id="r1", claim_id="c", harness="codex",
        seed_root=tmp_path / "s", repo_root=str(tmp_path),
        ledger_root=str(awl), spawn=fake_spawn,
    )
    first = pickup.launch_lane(item, **kwargs)
    second = pickup.launch_lane(item, **kwargs)
    assert first.launched is True
    assert second.launched is True  # idempotent: live claim reused, no refusal/crash


def test_launch_lane_allocation_refusal_fails_closed_without_spawn(tmp_path, monkeypatch):
    """dev-1 review (ce-ops#200): when ``allocate_in_place`` REFUSES (raises), the
    belt must fail closed — return ``launched=False`` with the allocation-refused
    note and the correct computed ``lane_id``, and MUST NOT spawn ``ce lane launch``.

    The fail-OPEN bug was: a malformed/lease-uncovered existing claim was silently
    treated as a live no-op, so ``launch_lane`` proceeded to spawn a doomed lane
    that ``ce lane launch`` then rejected (G3-CLAIM-MISSING/schema). The fix makes
    the idempotency path fail closed (RAISE). Here we force the allocator to raise
    and assert the belt neither spawns nor reports ``launched``.
    """
    awl = tmp_path / "awl"
    identity = "ce-dev-2"
    run_id = "r1"
    item = _item(kind="review_requested", repo="o/r", number=10)
    expected_lane_id = pickup._lane_id(item, run_id)

    spawn_calls = []

    def spy_spawn(argv):
        spawn_calls.append(argv)  # must never be invoked on a refused allocation
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "alive"}), stderr="")

    # Force the in-place allocator to refuse (raise the conflict/allocation error
    # type ``launch_lane`` catches). This stands in for a malformed / lease-uncovered
    # existing claim that the fail-closed idempotency path now rejects.
    def refusing_allocate(*args, **kwargs):
        raise pickup.pco_allocator.PcoConflictError(
            "existing live claim is not lease-covered; refusing fail-closed (PCO-021)"
        )

    monkeypatch.setattr(pickup.pco_allocator, "allocate_in_place", refusing_allocate)

    result = pickup.launch_lane(
        item, identity=identity, run_id=run_id, claim_id="wclaim-abc",
        harness="claude", seed_root=tmp_path / "seeds", repo_root=str(tmp_path),
        ledger_root=str(awl), spawn=spy_spawn,
    )

    # (a) launched=False, allocation-refused note, correct computed lane_id.
    assert result.launched is False
    assert result.lane_id == expected_lane_id
    assert "lane claim allocation refused" in (result.note or "")
    assert "PCO-021" in (result.note or "")
    # (b) the spawn seam was NEVER invoked — no doomed lane spawned.
    assert spawn_calls == []


def test_launch_lane_missing_repo_root_fails_closed_without_materializing_or_spawning(tmp_path, monkeypatch):
    """A typo/missing checkout must refuse before brain bootstrap, allocation, or spawn."""
    from creator_engine_validator import lane_runtime

    awl = tmp_path / "awl"
    missing_repo_root = tmp_path / "missing-checkout"
    identity = "ce-dev-2"
    run_id = "r1"
    item = _item(kind="assigned", repo="o/r", number=10)
    expected_lane_id = pickup._lane_id(item, run_id)
    spawn_calls = []
    allocate_calls = []

    def spy_spawn(argv):
        spawn_calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "alive"}), stderr="")

    def spy_allocate(*args, **kwargs):
        allocate_calls.append((args, kwargs))
        raise AssertionError("allocate_in_place must not run for an invalid repo root")

    monkeypatch.setattr(pickup.pco_allocator, "allocate_in_place", spy_allocate)

    result = pickup.launch_lane(
        item, identity=identity, run_id=run_id, claim_id="c",
        harness="codex", seed_root=missing_repo_root / "seeds",
        repo_root=str(missing_repo_root), ledger_root=str(awl), spawn=spy_spawn,
    )

    assert result.launched is False
    assert result.lane_id == expected_lane_id
    assert result.seed_path == str(missing_repo_root / "seeds" / f"{expected_lane_id}.seed.md")
    assert "repo/worktree invalid" in (result.note or "")
    assert spawn_calls == []
    assert allocate_calls == []
    assert not missing_repo_root.exists()
    assert not lane_runtime._claim_path(awl, identity, expected_lane_id).exists()


def test_launch_lane_brain_bootstrap_refusal_fails_closed_without_spawn(tmp_path):
    """A corrupt repo-local brain ledger must refuse before allocation/spawn."""
    from creator_engine_validator import brain_runtime, lane_runtime

    awl = tmp_path / "awl"
    identity = "ce-dev-2"
    run_id = "r1"
    item = _item(kind="assigned", repo="o/r", number=10)
    expected_lane_id = pickup._lane_id(item, run_id)
    state_root = tmp_path / ".ce" / "state"
    ledger_path = brain_runtime.ledger_path(state_root)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    spawn_calls = []

    def spy_spawn(argv):
        spawn_calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "alive"}), stderr="")

    result = pickup.launch_lane(
        item, identity=identity, run_id=run_id, claim_id="c",
        harness="codex", seed_root=tmp_path / "s", repo_root=str(tmp_path),
        ledger_root=str(awl), spawn=spy_spawn,
    )

    assert result.launched is False
    assert result.lane_id == expected_lane_id
    assert "brain bootstrap refused" in (result.note or "")
    assert spawn_calls == []
    assert not lane_runtime._claim_path(awl, identity, expected_lane_id).exists()


def test_launch_lane_malformed_existing_claim_fails_closed_without_spawn(tmp_path):
    """End-to-end (no monkeypatch): a malformed unreleased claim already on disk at
    the lane's claim path makes the REAL ``allocate_in_place`` fail closed, so the
    belt does not spawn.

    This proves the fail-closed idempotency change at the allocator boundary, not
    just the ``launch_lane`` catch: a partial/truncated claim (missing required
    schema fields) is no longer silently accepted as a live no-op.
    """
    from creator_engine_validator import lane_runtime

    awl = tmp_path / "awl"
    identity = "ce-dev-2"
    run_id = "r1"
    item = _item(kind="assigned", repo="o/r", number=10)
    expected_lane_id = pickup._lane_id(item, run_id)

    # Plant a malformed (schema-invalid: missing required fields), UNRELEASED claim
    # at exactly the path the lane would use.
    claim_path = lane_runtime._claim_path(awl, identity, expected_lane_id)
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim_path.write_text(
        yaml.safe_dump({"kind": "active-work-ledger-record", "record_type": "claim"}),
        encoding="utf-8",
    )

    spawn_calls = []

    def spy_spawn(argv):
        spawn_calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "alive"}), stderr="")

    result = pickup.launch_lane(
        item, identity=identity, run_id=run_id, claim_id="c",
        harness="codex", seed_root=tmp_path / "s", repo_root=str(tmp_path),
        ledger_root=str(awl), spawn=spy_spawn,
    )

    assert result.launched is False
    assert result.lane_id == expected_lane_id
    assert "lane claim allocation refused" in (result.note or "")
    assert spawn_calls == []  # never spawned a doomed lane


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


def test_cli_enable_launch_offline_e2e_asserts_full_lane_contract(monkeypatch, tmp_path, capsys):
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
    awl = tmp_path / "awl"
    expected_item = _item(kind="assigned", repo="o/r", number=21)
    expected_lane_id = pickup._lane_id(expected_item, "run-z")

    def fake_spawn(argv):
        _assert_lane_launch_preconditions(
            argv,
            repo_root=tmp_path,
            ledger_root=awl,
            identity="ce-dev-2",
            lane_id=expected_lane_id,
            role="implementer",
            lane_kind="implementation",
        )
        assert _argv_value(argv, "--command") == "codex"
        launched_argvs.append(argv)
        return subprocess.CompletedProcess(
            argv, 0,
            stdout=json.dumps({"seat_lifecycle_state": "alive"}), stderr="")

    monkeypatch.setattr(ce_cli, "_make_pickup_lane_spawn", lambda: fake_spawn)

    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2", "--keys-dir", str(tmp_path),
        "--claim", "--enable-launch", "--harness", "codex",
        "--ledger-root", str(tmp_path / "pickup"),
        "--repo-root", str(tmp_path), "--lane-ledger-root", str(awl),
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


def test_allocate_in_place_two_lanes_same_checkout_serializes(tmp_path):
    """Two DIFFERENT lanes for the SAME checkout must not both write a live claim.

    Regression for dev-3's race review (ce-ops#200): ``allocate_in_place`` held
    only the ``lane_id``-keyed lock, so two lanes targeting one ``worktree_path``
    acquired DIFFERENT locks, both passed ``_check_proposed_worktree_conflict``
    before either wrote, and both wrote live lease+claim records for one
    checkout (PCO-021 only requires lease COVERAGE, not uniqueness, so the guard
    still passed). The checkout-scoped lock serializes the critical section so at
    most ONE live claim+lease survives per checkout.

    Without the ``_checkout_lock`` this test fails: both threads succeed, leaving
    two live claims + two live leases. With it, exactly one wins and the other is
    refused with ``PcoConflictError``.
    """
    import threading

    from creator_engine_validator import pco_allocator

    ledger_root = tmp_path / "active-work-ledger"
    controller_id = "ce-dev-2"
    checkout = tmp_path / "checkout"
    checkout.mkdir()

    barrier = threading.Barrier(2)
    results: dict[str, object] = {}

    def _run(lane_id: str) -> None:
        # Rendezvous so both threads enter the critical section together,
        # deterministically exercising the race.
        barrier.wait()
        try:
            wrote = pco_allocator.allocate_in_place(
                ledger_root=ledger_root,
                lane_id=lane_id,
                controller_id=controller_id,
                worktree_path=checkout,
            )
            results[lane_id] = wrote
        except pco_allocator.PcoAllocatorError as exc:
            results[lane_id] = exc

    t1 = threading.Thread(target=_run, args=("lane-aaa",))
    t2 = threading.Thread(target=_run, args=("lane-bbb",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one lane wrote a live claim (returned True); the other was refused
    # (raised a conflict) or otherwise did NOT write a second live claim.
    successes = [lane for lane, r in results.items() if r is True]
    refusals = [lane for lane, r in results.items() if isinstance(r, Exception)]
    assert len(successes) == 1, f"expected exactly one winner, got {results!r}"
    assert len(refusals) == 1, f"expected exactly one refusal, got {results!r}"
    assert isinstance(refusals and results[refusals[0]], pco_allocator.PcoConflictError), (
        f"loser should raise PcoConflictError, got {results!r}"
    )

    # And on disk: at most one live (unreleased) claim + one live lease for the
    # checkout — the one-live-lane-per-checkout posture actually holds.
    live_claims = []
    for claim_file in (ledger_root / "claims").rglob("*.yaml"):
        if ".tmp." in claim_file.name:
            continue
        rec = yaml.safe_load(claim_file.read_text(encoding="utf-8"))
        if isinstance(rec, dict) and not rec.get("released_at"):
            live_claims.append(rec)
    assert len(live_claims) == 1, f"expected one live claim, found {len(live_claims)}"

    live_leases = []
    leases_dir = ledger_root / "leases"
    if leases_dir.is_dir():
        for lease_file in leases_dir.rglob("*.yaml"):
            if ".tmp." in lease_file.name:
                continue
            rec = yaml.safe_load(lease_file.read_text(encoding="utf-8"))
            if isinstance(rec, dict):
                live_leases.append(rec)
    assert len(live_leases) == 1, f"expected one live lease, found {len(live_leases)}"


def test_allocate_in_place_symlink_alias_of_same_checkout_is_refused(tmp_path):
    """Alias/symlink spelling of one physical checkout must collide everywhere.

    Regression for the dev-1/dev-3 review (ce-ops#200): the checkout lock keyed
    on ``os.path.realpath`` (so two spellings of one checkout serialize on the
    SAME lock), but ``_check_proposed_worktree_conflict`` /
    ``_existing_live_lease_covers`` compared RAW normalized strings. So lane-a via
    the alias path and lane-b via the real path of ONE physical checkout
    serialized on the lock yet slipped past conflict detection and BOTH allocated
    — two live claims for one checkout. With the canonical (realpath) checkout id
    applied consistently across lock + conflict scan + lease coverage +
    idempotency, lane-b is REFUSED and exactly one live claim+lease survives.

    Pre-fix: lane-b returns True (a second live claim). Post-fix: lane-b raises
    ``PcoConflictError`` and exactly one live claim + one live lease remains.
    """
    from creator_engine_validator import pco_allocator

    ledger_root = tmp_path / "active-work-ledger"
    controller_id = "ce-dev-2"

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(checkout, target_is_directory=True)

    # lane-a claims via the ALIAS (symlink) spelling.
    wrote_a = pco_allocator.allocate_in_place(
        ledger_root=ledger_root,
        lane_id="lane-a",
        controller_id=controller_id,
        worktree_path=alias,
    )
    assert wrote_a is True

    # lane-b targets the SAME physical checkout via its REAL path — it MUST be
    # refused (no second live claim for one checkout).
    with pytest.raises(pco_allocator.PcoConflictError):
        pco_allocator.allocate_in_place(
            ledger_root=ledger_root,
            lane_id="lane-b",
            controller_id=controller_id,
            worktree_path=checkout,
        )

    # On disk: exactly one live (unreleased) claim + one live lease for the
    # single physical checkout.
    live_claims = []
    for claim_file in (ledger_root / "claims").rglob("*.yaml"):
        if ".tmp." in claim_file.name:
            continue
        rec = yaml.safe_load(claim_file.read_text(encoding="utf-8"))
        if isinstance(rec, dict) and not rec.get("released_at"):
            live_claims.append(rec)
    assert len(live_claims) == 1, f"expected one live claim, found {len(live_claims)}"

    live_leases = []
    leases_dir = ledger_root / "leases"
    if leases_dir.is_dir():
        for lease_file in leases_dir.rglob("*.yaml"):
            if ".tmp." in lease_file.name:
                continue
            rec = yaml.safe_load(lease_file.read_text(encoding="utf-8"))
            if isinstance(rec, dict):
                live_leases.append(rec)
    assert len(live_leases) == 1, f"expected one live lease, found {len(live_leases)}"


# ---------------------------------------------------------------------------
# ce-ops#203: production-length lane ids must not overflow the PCO-020
# ``lease_id`` bound. The live canary post-#200 reached
# ``allocate_in_place`` but the lease write was REFUSED because the naive
# ``lease-<lane_id>-<14-digit stamp>`` derivation overflowed
# ``^[a-z0-9][a-z0-9-]{2,63}$`` (~69 chars > 64) for pickup's long lane ids.
# The #200 tests used SHORT synthetic lane ids (``lane-aaa``) and missed it.
# These tests reproduce production by feeding the REAL pickup lane format.
# ---------------------------------------------------------------------------

# pco_allocator's lease_id schema pattern (worktree-lease.schema.yaml).
_LEASE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def _production_pickup_lane_id() -> str:
    """The real pickup lane id for ce-ops#202 on ce-dev-2 (see pickup._lane_id):
    ``pickup-<repo>-<number>-<run_id>``. ~48 chars -- long enough that the naive
    ``lease-<lane>-<stamp>`` derivation overflowed the 64-char lease_id bound."""
    lane = pickup._lane_id(
        {"repo": "creator-engine/ce-ops", "number": 202}, "pickup-ce-dev-2"
    )
    # Sanity: this must actually be a LONG lane (the condition that triggered #203).
    assert len(lane) > 40, f"expected a production-length lane, got {lane!r} ({len(lane)})"
    return lane


def test_allocate_in_place_production_length_lane_writes_conformant_lease(tmp_path):
    """``allocate_in_place`` with a PRODUCTION-LENGTH pickup lane id must SUCCEED
    and write a lease whose ``lease_id`` satisfies the live PCO-020 schema.

    Pre-fix (naive ``lease-<lane>-<stamp>``): the lease write is REFUSED with
    ``PcoConflictError`` because ``lease_id`` is ~69 chars > the 64-char bound --
    exactly the live-canary failure. Post-fix (length-independent hashed id): the
    call returns ``True`` and the on-disk lease, claim, and event records each
    pass the live schema validators.
    """
    from creator_engine_validator import pco_allocator

    ledger_root = tmp_path / "active-work-ledger"
    controller_id = "ce-dev-2"
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    lane_id = _production_pickup_lane_id()

    # (a) The call SUCCEEDS -- _validate_proposed_allocation_state did not refuse.
    wrote = pco_allocator.allocate_in_place(
        ledger_root=ledger_root,
        lane_id=lane_id,
        controller_id=controller_id,
        worktree_path=checkout,
        envelope_ref="none",
    )
    assert wrote is True, "allocate_in_place must write a fresh claim for a long lane"

    # (b) Read records back from disk and validate against the LIVE schema checks.
    lease_path = ledger_root / "leases" / controller_id / f"{lane_id}.yaml"
    claim_path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"
    assert lease_path.is_file(), "lease record must be written"
    assert claim_path.is_file(), "claim record must be written"

    lease_rec = yaml.safe_load(lease_path.read_text(encoding="utf-8"))
    claim_rec = yaml.safe_load(claim_path.read_text(encoding="utf-8"))

    # The lease_id FIELD itself must match the bounded PCO-020 pattern.
    lease_id = lease_rec["lease_id"]
    assert _LEASE_ID_PATTERN.match(lease_id), (
        f"lease_id {lease_id!r} (len {len(lease_id)}) violates ^[a-z0-9][a-z0-9-]{{2,63}}$"
    )

    assert validate_worktree_lease_record(lease_rec, lease_path) == [], (
        "on-disk lease record must pass the live worktree-lease schema validator"
    )
    assert validate_active_work_ledger_record(claim_rec, claim_path) == [], (
        "on-disk claim record must pass the live active-work-ledger schema validator"
    )

    # The event record must also validate.
    event_files = [
        p for p in (ledger_root / "events").rglob("*.yaml") if ".tmp." not in p.name
    ]
    assert event_files, "an event record must be written"
    for event_path in event_files:
        event_rec = yaml.safe_load(event_path.read_text(encoding="utf-8"))
        assert validate_active_work_ledger_record(event_rec, event_path) == [], (
            f"on-disk event record {event_path} must pass the schema validator"
        )


def test_allocate_production_length_lane_writes_conformant_lease(tmp_path):
    """The same length-independence guarantee for the full ``allocate`` path.

    ``allocate``'s controller callers historically passed SHORT lane ids so this
    overflow never tripped here, but the bug was shared (both paths derived
    ``lease-<lane>-<stamp>``). Feeding a production-length lane proves
    ``allocate`` is also safe for long lanes. Uses a no-op git double so no real
    ``git worktree add`` runs.
    """
    from creator_engine_validator import pco_allocator

    # A worktree-style checkout (not the root) so allocate() does not refuse.
    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    (repo_root / ".git").write_text("gitdir: ../../.git/worktrees/test\n", encoding="utf-8")

    ledger_root = tmp_path / "active-work-ledger"
    controller_id = "ce-dev-2"
    lane_id = _production_pickup_lane_id()

    def _noop_git(*args, **kwargs):
        return None

    pco_allocator.allocate(
        repo_root=repo_root,
        ledger_root=ledger_root,
        lane_id=lane_id,
        worktree_path=tmp_path / "new-wt",
        envelope_ref="none",
        branch="test/branch",
        controller_id=controller_id,
        _git_fn=_noop_git,
    )

    lease_path = ledger_root / "leases" / controller_id / f"{lane_id}.yaml"
    assert lease_path.is_file(), "allocate must write a lease for a long lane"
    lease_rec = yaml.safe_load(lease_path.read_text(encoding="utf-8"))
    lease_id = lease_rec["lease_id"]
    assert _LEASE_ID_PATTERN.match(lease_id), (
        f"lease_id {lease_id!r} (len {len(lease_id)}) violates ^[a-z0-9][a-z0-9-]{{2,63}}$"
    )
    assert validate_worktree_lease_record(lease_rec, lease_path) == [], (
        "on-disk lease record must pass the live worktree-lease schema validator"
    )
