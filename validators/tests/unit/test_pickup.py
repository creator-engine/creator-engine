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
