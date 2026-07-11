"""Unit tests for the shared work-claim runtime (ce-ops#38).

Covers the ticket parser, the structured + legacy marker parsers, malformed-marker
refusal, the deterministic state machine (winner selection, release matching,
staleness, explicit takeover), idempotency-key replay, and the fake-``GhRunner``
API call shapes. No test touches the network — every forge call goes through an
injected fake runner.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from creator_engine_validator import work_claims as wc

NOW = datetime(2026, 6, 12, 15, 0, 0, tzinfo=timezone.utc)
WK = "creator-engine/ce-ops:issue:38"


def _ts(delta=timedelta(0)):
    """Clock-relative ISO-``Z`` timestamp derived from ``NOW`` (ce-ops#57).

    The state-machine tests below pass ``now=NOW`` explicitly, so they are already
    date-independent; deriving the claim/stale fixtures from ``NOW`` keeps the
    active (``NOW - 1h``) vs stale (``NOW - 6h``) distinction honest under the 4h
    (14400s) fence and free of any hardcoded wall-clock-sensitive date.
    """
    return (NOW + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(autouse=True)
def _frozen_work_claim_clock(freeze_work_claim_clock):
    # Defense-in-depth: any code path here that defaults to wall-clock ``now``
    # still resolves to NOW, matching the explicit ``now=NOW`` call sites.
    freeze_work_claim_clock(NOW)


# --- fake GhRunner -----------------------------------------------------------


class FakeGh:
    """A stateful fake ``GhRunner`` answering GET-comments and POST-comment."""

    def __init__(self, comments=None, *, get_rc=0, post_rc=0, err="boom"):
        self.comments = [dict(c) for c in (comments or [])]
        self.next_id = max((c["id"] for c in self.comments), default=0) + 1
        self.calls: list[list[str]] = []
        self.posts: list[str] = []
        self.get_rc = get_rc
        self.post_rc = post_rc
        self.err = err

    def __call__(self, argv, input_text=None):
        self.calls.append(list(argv))
        method = argv[argv.index("--method") + 1] if "--method" in argv else "GET"
        if method == "POST":
            if self.post_rc != 0:
                return subprocess.CompletedProcess(argv, self.post_rc, stdout="", stderr=self.err)
            body = json.loads(input_text)["body"]
            cid = self.next_id
            self.next_id += 1
            self.comments.append(
                {"id": cid, "body": body, "created_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "user": {"login": "bot"}}
            )
            self.posts.append(body)
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps({"id": cid, "html_url": f"https://x/{cid}"}), stderr="")
        if self.get_rc != 0:
            return subprocess.CompletedProcess(argv, self.get_rc, stdout="", stderr=self.err)
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.comments), stderr="")


def _acquire_body(claim_id, holder="ce-dev-2", host="H", claimed_at=None,
                  stale_after=14400, idem="idem-1"):
    return wc.render_marker({
        "kind": "ce-work-claim", "schema_version": 1, "action": "acquire",
        "work_key": WK, "claim_id": claim_id, "holder": holder, "host": host,
        "claimed_at": claimed_at or _ts(timedelta(hours=-1)),
        "stale_after_seconds": stale_after, "idempotency_key": idem,
    })


def _comment(cid, body, created_at=None):
    return {"id": cid, "body": body, "created_at": created_at or _ts(timedelta(hours=-1)),
            "user": {"login": "bot"}}


# --- ticket parser -----------------------------------------------------------


@pytest.mark.parametrize("raw,repo", [
    ("creator-engine/ce-ops#38", None),
    ("creator-engine/ce-ops:issue:38", None),
    ("https://github.com/creator-engine/ce-ops/issues/38", None),
    ("38", "creator-engine/ce-ops"),
])
def test_parse_ticket_accepts_all_forms(raw, repo):
    key = wc.parse_ticket(raw, repo)
    assert key.work_key == WK
    assert key.repo_slug == "creator-engine/ce-ops"
    assert key.number == 38


def test_parse_ticket_rejects_bare_number_without_repo():
    with pytest.raises(wc.WorkClaimError):
        wc.parse_ticket("38")


def test_parse_ticket_rejects_garbage():
    with pytest.raises(wc.WorkClaimError):
        wc.parse_ticket("not-a-ticket")


# --- structured marker parser ------------------------------------------------


def test_parse_acquire_marker():
    m = wc.parse_comment(wc.Comment(1, _acquire_body("wclaim-a"), _ts(timedelta(hours=-1))))
    assert m.status == "acquire"
    assert m.work_key == WK
    assert m.claim_id == "wclaim-a"
    assert m.fields["holder"] == "ce-dev-2"


def test_parse_release_marker():
    body = wc.render_marker({
        "kind": "ce-work-claim", "schema_version": 1, "action": "release",
        "work_key": WK, "claim_id": "wclaim-a", "holder": "h", "host": "H",
        "released_at": "2026-06-12T14:30:00Z", "release_reason": "done",
    })
    m = wc.parse_comment(wc.Comment(2, body))
    assert m.status == "release" and m.claim_id == "wclaim-a"


def test_parse_takeover_marker():
    body = wc.render_marker({
        "kind": "ce-work-claim", "schema_version": 1, "action": "takeover",
        "work_key": WK, "claim_id": "wclaim-new", "supersedes_claim_id": "wclaim-old",
        "holder": "h", "host": "H", "claimed_at": "2026-06-12T14:30:00Z",
        "takeover_reason": "stale", "observed_stale_after_seconds": 14400,
    })
    m = wc.parse_comment(wc.Comment(3, body))
    assert m.status == "takeover"
    assert m.fields["supersedes_claim_id"] == "wclaim-old"


def test_malformed_structured_marker_is_invalid():
    # Sentinel present, JSON missing required fields → invalid.
    bad = f"{wc.SENTINEL}\n```json\n{{\"action\": \"acquire\"}}\n```"
    m = wc.parse_comment(wc.Comment(4, bad))
    assert m.status == "invalid"


def test_sentinel_with_no_json_is_invalid():
    m = wc.parse_comment(wc.Comment(5, f"{wc.SENTINEL}\nno json here"))
    assert m.status == "invalid"


def test_non_marker_comment_returns_none():
    assert wc.parse_comment(wc.Comment(6, "just a normal comment")) is None


# --- legacy lock parser ------------------------------------------------------


def test_legacy_lock_parser():
    m = wc.parse_comment(wc.Comment(7, "🔒 in-compose ce-dev-2 (spec composer)"))
    assert m.status == "legacy"
    assert m.fields["holder"] == "ce-dev-2"
    assert m.claim_id == "legacy-7"


def test_deliverable_marker_recognized():
    m = wc.parse_comment(wc.Comment(8, "📦 BANKED deliverable here"))
    assert m.status == "deliverable"


# --- state machine: winner, release, stale, takeover -------------------------


def test_legacy_lock_is_active_until_deliverable():
    legacy = _comment(1, "🔒 in-compose ce-dev-2", "2026-06-12T09:45:42Z")
    st = wc.compute_state([wc.Comment(**_strip(legacy))], WK, NOW)
    assert st.active is not None and st.active.holder == "ce-dev-2"
    assert st.active.kind == "legacy"


def test_legacy_lock_released_by_later_deliverable():
    legacy = wc.Comment(1, "🔒 in-compose ce-dev-2", "2026-06-12T09:45:42Z")
    deliverable = wc.Comment(2, "📦 BANKED", "2026-06-12T14:43:21Z")
    st = wc.compute_state([legacy, deliverable], WK, NOW)
    assert st.active is None


def test_deterministic_winner_earliest_claimed_at():
    a = wc.Comment(2, _acquire_body("wclaim-a", claimed_at=_ts(timedelta(minutes=-30))))
    b = wc.Comment(1, _acquire_body("wclaim-b", claimed_at=_ts(timedelta(hours=-1))))
    st = wc.compute_state([a, b], WK, NOW)
    assert st.active.claim_id == "wclaim-b"  # earlier claimed_at wins
    losers = [e for e in st.entries if e.status == "conflict"]
    assert [e.claim_id for e in losers] == ["wclaim-a"]


def test_winner_tie_break_by_comment_id():
    same = _ts(timedelta(hours=-1))
    a = wc.Comment(5, _acquire_body("wclaim-a", claimed_at=same))
    b = wc.Comment(3, _acquire_body("wclaim-b", claimed_at=same))
    st = wc.compute_state([a, b], WK, NOW)
    assert st.active.comment_id == 3  # lower comment id wins the tie


def test_release_matches_claim_id():
    acq = wc.Comment(1, _acquire_body("wclaim-a"))
    rel = wc.Comment(2, wc.render_marker({
        "kind": "ce-work-claim", "schema_version": 1, "action": "release",
        "work_key": WK, "claim_id": "wclaim-a", "holder": "h", "host": "H",
        "released_at": "2026-06-12T14:30:00Z", "release_reason": "done"}))
    st = wc.compute_state([acq, rel], WK, NOW)
    assert st.active is None
    assert any(e.claim_id == "wclaim-a" and e.status == "released" for e in st.entries)


def test_stale_status_does_not_release():
    old = wc.Comment(1, _acquire_body("wclaim-a", claimed_at=_ts(timedelta(hours=-6))))
    st = wc.compute_state([old], WK, NOW)  # claimed 6h ago, fence 4h
    assert st.active is not None  # stale ≠ released
    assert st.active.stale is True
    assert st.stale_count == 1


def test_explicit_takeover_supersedes():
    acq = wc.Comment(1, _acquire_body("wclaim-old", claimed_at=_ts(timedelta(hours=-6))))
    tk = wc.Comment(2, wc.render_marker({
        "kind": "ce-work-claim", "schema_version": 1, "action": "takeover",
        "work_key": WK, "claim_id": "wclaim-new", "supersedes_claim_id": "wclaim-old",
        "holder": "ce-dev-3", "host": "H3", "claimed_at": _ts(timedelta(minutes=-30)),
        "takeover_reason": "stale", "observed_stale_after_seconds": 14400}))
    st = wc.compute_state([acq, tk], WK, NOW)
    assert st.active.claim_id == "wclaim-new"
    assert any(e.claim_id == "wclaim-old" and e.status == "superseded" for e in st.entries)


def test_markers_for_other_work_keys_ignored():
    other = _acquire_body("wclaim-x", idem="i")
    other = other.replace(WK, "creator-engine/ce-ops:issue:99")
    st = wc.compute_state([wc.Comment(1, other)], WK, NOW)
    assert st.active is None


def test_invalid_marker_counted():
    bad = f"{wc.SENTINEL}\n```json\n{{\"action\": \"acquire\", \"work_key\": \"{WK}\"}}\n```"
    st = wc.compute_state([wc.Comment(1, bad)], WK, NOW)
    assert st.invalid_count == 1


# --- idempotency key replay --------------------------------------------------


def test_idempotency_key_yields_stable_claim_id():
    idem = wc.make_idempotency_key("ce-dev-2", "H", WK, "nonce-1")
    assert wc.make_claim_id(idem) == wc.make_claim_id(idem)
    assert wc.make_claim_id(idem) != wc.make_claim_id(idem + "x")


# --- fake GhRunner API call shapes -------------------------------------------


def test_status_reads_comments_via_runner():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-a"))])
    res = wc.status(wc.parse_ticket("creator-engine/ce-ops#38"), gh, now=NOW)
    assert res.ok and res.state.active.claim_id == "wclaim-a"
    # exactly one GET, no POST
    assert gh.posts == []
    assert any("/comments" in " ".join(c) for c in gh.calls)


def test_acquire_posts_then_rereads_and_wins():
    gh = FakeGh([])  # empty issue
    key = wc.parse_ticket("creator-engine/ce-ops#38")
    res = wc.acquire(key, gh, holder="ce-dev-2", host="H", now=NOW,
                     nonce="n1", backoff_seconds=0, sleep=lambda s: None)
    assert res.ok
    assert wc.SENTINEL in gh.posts[0]  # posted a structured acquire
    assert res.state.active.claim_id == res.claim_id


def test_acquire_refuses_foreign_active_before_posting():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-foreign", holder="other", host="X"))])
    key = wc.parse_ticket("creator-engine/ce-ops#38")
    res = wc.acquire(key, gh, holder="ce-dev-2", host="H", now=NOW,
                     nonce="n1", backoff_seconds=0, sleep=lambda s: None,
                     hard_block=False)
    assert not res.ok
    assert res.refusal_reason == "active_foreign_claim"
    assert gh.posts == []  # refuse BEFORE side effect


def test_block_if_active_foreign_claim_raises_on_active():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-foreign", holder="other", host="X"))])
    key = wc.parse_ticket("creator-engine/ce-ops#38")

    with pytest.raises(wc.WorkClaimRefused) as exc_info:
        wc.block_if_active_foreign_claim(key, gh, holder="ce-dev-2", host="H", now=NOW)

    assert "wclaim-foreign" in str(exc_info.value)
    assert exc_info.value.work_key == key
    assert exc_info.value.holder == "other"
    assert exc_info.value.host == "X"
    assert exc_info.value.claim_id == "wclaim-foreign"
    assert exc_info.value.claimed_at == _ts(timedelta(hours=-1))
    assert gh.posts == []


def test_block_if_active_foreign_claim_allows_stale(caplog):
    gh = FakeGh([_comment(
        1, _acquire_body("wclaim-stale", holder="other", host="X",
                         claimed_at=_ts(timedelta(hours=-6))),
    )])
    key = wc.parse_ticket("creator-engine/ce-ops#38")

    wc.block_if_active_foreign_claim(key, gh, holder="ce-dev-2", host="H", now=NOW)

    assert "stale foreign work claim remains seizable" in caplog.text
    assert gh.posts == []


def test_block_if_active_foreign_claim_allows_self():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-self", holder="ce-dev-2", host="H"))])
    key = wc.parse_ticket("creator-engine/ce-ops#38")

    wc.block_if_active_foreign_claim(key, gh, holder="ce-dev-2", host="H", now=NOW)

    assert gh.posts == []


def test_acquire_hard_block_true_raises_on_active_foreign():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-foreign", holder="other", host="X"))])
    key = wc.parse_ticket("creator-engine/ce-ops#38")

    with pytest.raises(wc.WorkClaimRefused, match="double-assignment blocked") as exc_info:
        wc.acquire(key, gh, holder="ce-dev-2", host="H", now=NOW,
                   nonce="n1", backoff_seconds=0, sleep=lambda s: None,
                   hard_block=True)

    assert exc_info.value.claim_id == "wclaim-foreign"
    assert gh.posts == []


def test_acquire_hard_block_false_returns_soft_refusal():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-foreign", holder="other", host="X"))])
    key = wc.parse_ticket("creator-engine/ce-ops#38")

    result = wc.acquire(key, gh, holder="ce-dev-2", host="H", now=NOW,
                        nonce="n1", backoff_seconds=0, sleep=lambda s: None,
                        hard_block=False)

    assert not result.ok
    assert result.refusal_reason == "active_foreign_claim"
    assert gh.posts == []


def test_acquire_loses_reread_release_and_fail_closed():
    # First GET empty, but the re-read surfaces an EARLIER foreign claim → we lose.
    gh = FakeGh([])
    key = wc.parse_ticket("creator-engine/ce-ops#38")
    original_call = gh.__call__
    state = {"posted": False}

    def runner(argv, input_text=None):
        method = argv[argv.index("--method") + 1] if "--method" in argv else "GET"
        if method == "GET" and state["posted"]:
            # inject an earlier-claimed foreign claim into the re-read
            gh.comments.insert(0, _comment(
                999, _acquire_body("wclaim-earlier", holder="other", host="X",
                                   claimed_at=_ts(timedelta(hours=-2)))))
            state["posted"] = False  # only once
        result = original_call(argv, input_text)
        if method == "POST":
            state["posted"] = True
        return result

    res = wc.acquire(key, runner, holder="ce-dev-2", host="H", now=NOW,
                     nonce="n1", backoff_seconds=0, sleep=lambda s: None)
    assert not res.ok
    assert res.refusal_reason == "lost_after_reread"
    # we posted our acquire AND a void-release for it
    assert any(wc.SENTINEL in p and '"action": "acquire"' in p for p in gh.posts)
    assert any('"action": "release"' in p for p in gh.posts)


def test_gh_unavailable_raises_work_claim_error():
    gh = FakeGh([], get_rc=1)
    key = wc.parse_ticket("creator-engine/ce-ops#38")
    with pytest.raises(wc.WorkClaimError):
        wc.status(key, gh, now=NOW)


def test_release_active_claim():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-a", holder="ce-dev-2", host="H"))])
    key = wc.parse_ticket("creator-engine/ce-ops#38")
    res = wc.release(key, gh, holder="ce-dev-2", host="H", now=NOW)
    assert res.ok and res.claim_id == "wclaim-a"
    assert any('"action": "release"' in p for p in gh.posts)


def test_release_refuses_foreign():
    gh = FakeGh([_comment(1, _acquire_body("wclaim-a", holder="other", host="X"))])
    key = wc.parse_ticket("creator-engine/ce-ops#38")
    res = wc.release(key, gh, holder="ce-dev-2", host="H", now=NOW)
    assert not res.ok and res.refusal_reason == "foreign_claim"
    assert gh.posts == []


def _strip(comment):
    return {"id": comment["id"], "body": comment["body"], "created_at": comment["created_at"]}
