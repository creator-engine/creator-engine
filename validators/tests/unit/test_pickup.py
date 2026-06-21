"""Unit tests for the ce-ops#55 autonomous forge work-pickup poller.

``creator_engine_validator.pickup`` is a per-seat READ-ONLY poller over the GitHub Notifications API
(``GET /notifications``) with conditional ``If-Modified-Since``/``Last-Modified`` and
``X-Poll-Interval`` honored; a 304 is a free no-op. It resolves each notification thread
into a normalized work-item ``{repo, kind, number, url, reason}`` and filters out
non-actionable reasons (``subscribed``/``comment``).

Per the CE Ring-0 launch refusals (CC-D-2 / CDX-D-1), the poller is read-only and NEVER
authors; actual work runs as a fresh governed lane via ``ce lane launch``. These tests
inject a fake HTTP transport and perform ZERO live network / subprocess.

S1 — observe-only. S2 — claim + dedup ledger (dry-run). S3 — ``ce lane launch`` wiring
behind a per-seat enable flag (canary, default OFF).
"""

import json
from pathlib import Path

import pytest

from creator_engine_validator import pickup


# ---------------------------------------------------------------------------
# Fake notifications transport — records every (method, url, headers) call and
# returns a scripted (status, headers, body) per call. Mirrors the app_jwt seam.
# ---------------------------------------------------------------------------


def _notif(thread_id, reason, *, subject_type="PullRequest", repo="creator-engine/ce-ops",
           number=42, url=None, title="x"):
    api = url or f"https://api.github.com/repos/{repo}/issues/{number}"
    return {
        "id": str(thread_id),
        "reason": reason,
        "repository": {"full_name": repo},
        "subject": {"title": title, "type": subject_type, "url": api},
        "updated_at": "2026-06-21T00:00:00Z",
    }


def _fake_transport(responses, calls=None):
    """Yield a scripted response per call. Each response is (status, headers, body)."""
    seq = list(responses)

    def transport(method, url, headers, body):
        if calls is not None:
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        status, resp_headers, resp_body = seq.pop(0)
        return status, dict(resp_headers), resp_body

    return transport


_ACTIONABLE_BODY = json.dumps([
    _notif("t1", "review_requested", number=10,
           url="https://api.github.com/repos/creator-engine/ce-ops/pulls/10"),
    _notif("t2", "assign", number=11),
    _notif("t3", "mention", number=12),
    _notif("t4", "subscribed", number=13),   # filtered
    _notif("t5", "comment", number=14),       # filtered
])


# ---------------------------------------------------------------------------
# poll() — happy path: resolves actionable threads, filters the rest.
# ---------------------------------------------------------------------------


def test_poll_resolves_actionable_items_and_filters_noise():
    transport = _fake_transport([(200, {"Last-Modified": "Sat, 21 Jun 2026 00:00:00 GMT"}, _ACTIONABLE_BODY)])
    result = pickup.poll(token="ghp_fake", transport=transport)

    kinds = {(i["kind"], i["number"]) for i in result.items}
    assert ("review_requested", 10) in kinds
    assert ("assigned", 11) in kinds
    assert ("mention", 12) in kinds
    # subscribed + comment reasons are non-actionable → filtered out.
    assert 13 not in {i["number"] for i in result.items}
    assert 14 not in {i["number"] for i in result.items}
    assert len(result.items) == 3


def test_poll_item_shape_is_normalized():
    body = json.dumps([_notif("t1", "review_requested", repo="o/r", number=7,
                              url="https://api.github.com/repos/o/r/pulls/7")])
    transport = _fake_transport([(200, {}, body)])
    result = pickup.poll(token="ghp_fake", transport=transport)
    item = result.items[0]
    assert item["repo"] == "o/r"
    assert item["kind"] == "review_requested"
    assert item["number"] == 7
    assert item["reason"] == "review_requested"
    # url is the human PR/issue url, derived from the api subject url.
    assert item["url"] == "https://github.com/o/r/pull/7"
    assert item["thread_id"] == "t1"


def test_poll_labeled_reason_maps_to_labeled_kind():
    body = json.dumps([_notif("t1", "labeled", subject_type="Issue", number=5,
                              url="https://api.github.com/repos/o/r/issues/5")])
    transport = _fake_transport([(200, {}, body)])
    result = pickup.poll(token="ghp_fake", transport=transport)
    assert result.items[0]["kind"] == "labeled"
    assert result.items[0]["url"] == "https://github.com/o/r/issues/5"


# ---------------------------------------------------------------------------
# Conditional requests — Last-Modified captured, sent back, 304 → empty no-op.
# ---------------------------------------------------------------------------


def test_poll_sends_if_modified_since_from_prior_last_modified():
    last_mod = "Sat, 21 Jun 2026 00:00:00 GMT"
    calls = []
    transport = _fake_transport([(304, {}, "")], calls=calls)
    result = pickup.poll(token="ghp_fake", transport=transport, last_modified=last_mod)
    assert calls[0]["headers"].get("If-Modified-Since") == last_mod


def test_poll_304_yields_empty_items_and_preserves_last_modified():
    last_mod = "Sat, 21 Jun 2026 00:00:00 GMT"
    transport = _fake_transport([(304, {}, "")])
    result = pickup.poll(token="ghp_fake", transport=transport, last_modified=last_mod)
    assert list(result.items) == []
    assert result.not_modified is True
    # carry the cursor forward unchanged so the next poll stays conditional.
    assert result.last_modified == last_mod


def test_poll_captures_new_last_modified_and_poll_interval():
    headers = {"Last-Modified": "Sat, 21 Jun 2026 01:00:00 GMT", "X-Poll-Interval": "120"}
    transport = _fake_transport([(200, headers, json.dumps([]))])
    result = pickup.poll(token="ghp_fake", transport=transport)
    assert result.last_modified == "Sat, 21 Jun 2026 01:00:00 GMT"
    assert result.poll_interval == 120


def test_poll_default_poll_interval_when_header_absent():
    transport = _fake_transport([(200, {}, json.dumps([]))])
    result = pickup.poll(token="ghp_fake", transport=transport)
    assert result.poll_interval == pickup.DEFAULT_POLL_INTERVAL


def test_poll_sends_auth_header_and_api_version():
    calls = []
    transport = _fake_transport([(200, {}, json.dumps([]))], calls=calls)
    pickup.poll(token="ghp_secret", transport=transport)
    assert calls[0]["headers"]["Authorization"] == "Bearer ghp_secret"
    assert "X-GitHub-Api-Version" in calls[0]["headers"]
    assert calls[0]["url"].endswith("/notifications")
    assert calls[0]["method"] == "GET"


def test_poll_requires_a_token():
    with pytest.raises(pickup.PickupError):
        pickup.poll(token="", transport=_fake_transport([(200, {}, "[]")]))


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


def test_resolve_token_missing_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
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
        lambda: _fake_transport([(200, {"X-Poll-Interval": "90"}, _ACTIONABLE_BODY)]),
    )
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-2",
        "--keys-dir", str(tmp_path), "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["count"] == 3
    assert out["poll_interval"] == 90
    # observe-only: no claim, no launch fields.
    kinds = {i["kind"] for i in out["items"]}
    assert kinds == {"review_requested", "assigned", "mention"}


def test_cli_pickup_poll_missing_token_exit_2(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    code = ce_cli.main([
        "pickup", "poll", "--identity", "ce-dev-9", "--keys-dir", str(tmp_path),
    ])
    assert code == 2


# ===========================================================================
# S2 — claim + idempotency (dry-run).
# ===========================================================================

import subprocess  # noqa: E402

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

    def runner(self, identity):
        def gh(argv, input_text=None):
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


def test_dry_run_cli_reports_would_launch(monkeypatch, tmp_path, capsys):
    from creator_engine_validator import ce_cli

    forge = _FakeForge()
    pat = tmp_path / "ce-dev-2.pat"
    pat.write_text("ghp_t\n", encoding="utf-8")
    monkeypatch.delenv("CE_PICKUP_TOKEN", raising=False)
    body = json.dumps([_notif("t1", "assign", repo="o/r", number=11,
                              url="https://api.github.com/repos/o/r/issues/11")])
    monkeypatch.setattr(ce_cli, "_make_pickup_transport",
                        lambda: _fake_transport([(200, {}, body)]))
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
