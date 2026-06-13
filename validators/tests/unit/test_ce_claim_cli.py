"""Unit tests for the ``ce claim acquire|release|status`` CLI surface (ce-ops#38).

The CLI is exercised through ``ce_cli.main`` with a fake ``GhRunner`` injected via
``_make_gh_runner`` — no network. Asserts JSON output, exit-code contract
(0 ok / 1 refused / 2 bad-input), ambiguous-ticket refusal, unavailable-``gh``
behavior, conflict refusal, and the view-only cache write.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from creator_engine_validator import ce_cli, work_claims as wc

NOW = datetime(2026, 6, 12, 15, 0, 0, tzinfo=timezone.utc)
WK = "creator-engine/ce-ops:issue:38"


def _ts(delta=timedelta(0)):
    """Clock-relative ISO-``Z`` timestamp derived from the frozen ``NOW``.

    The ``ce claim`` command surface calls ``work_claims.acquire/status/release``
    without an explicit ``now``, so it reads wall-clock time. Expressing fixtures
    relative to ``NOW`` (active = ``NOW - 1h`` under the 4h fence) keeps them
    date-independent once the work-claim clock is frozen to ``NOW`` (ce-ops#57).
    """
    return (NOW + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(autouse=True)
def _frozen_work_claim_clock(freeze_work_claim_clock):
    freeze_work_claim_clock(NOW)


class FakeGh:
    def __init__(self, comments=None, *, get_rc=0, post_rc=0):
        self.comments = [dict(c) for c in (comments or [])]
        self.next_id = max((c["id"] for c in self.comments), default=0) + 1
        self.posts: list[str] = []
        self.get_rc = get_rc
        self.post_rc = post_rc

    def __call__(self, argv, input_text=None):
        method = argv[argv.index("--method") + 1] if "--method" in argv else "GET"
        if method == "POST":
            if self.post_rc != 0:
                return subprocess.CompletedProcess(argv, self.post_rc, stdout="", stderr="boom")
            body = json.loads(input_text)["body"]
            cid = self.next_id
            self.next_id += 1
            self.comments.append({"id": cid, "body": body, "created_at": _ts(),
                                  "user": {"login": "bot"}})
            self.posts.append(body)
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": cid}), stderr="")
        if self.get_rc != 0:
            return subprocess.CompletedProcess(argv, self.get_rc, stdout="", stderr="gh: not found")
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.comments), stderr="")


def _acquire_body(claim_id, holder="ce-dev-2", host="H", claimed_at=None):
    return wc.render_marker({
        "kind": "ce-work-claim", "schema_version": 1, "action": "acquire",
        "work_key": WK, "claim_id": claim_id, "holder": holder, "host": host,
        "claimed_at": claimed_at or _ts(timedelta(hours=-1)),
        "stale_after_seconds": 14400, "idempotency_key": "i"})


def _comment(cid, body):
    return {"id": cid, "body": body, "created_at": _ts(timedelta(hours=-1)), "user": {"login": "bot"}}


@pytest.fixture()
def patch_gh(monkeypatch):
    def _install(gh):
        monkeypatch.setattr(ce_cli, "_make_gh_runner", lambda: gh)
        # deterministic backoff for acquire
        monkeypatch.setattr(wc.time, "sleep", lambda s: None)
        return gh
    return _install


# --- status ------------------------------------------------------------------


def test_status_unclaimed_json(patch_gh, capsys):
    patch_gh(FakeGh([]))
    rc = ce_cli.main(["claim", "status", "creator-engine/ce-ops#38", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["work_key"] == WK
    assert out["active_claim"] is None
    assert out["comments_seen"] == 0


def test_status_held(patch_gh, capsys):
    patch_gh(FakeGh([_comment(1, _acquire_body("wclaim-a"))]))
    rc = ce_cli.main(["claim", "status", "creator-engine/ce-ops#38"])
    assert rc == 0
    assert "held by ce-dev-2@H" in capsys.readouterr().out


def test_status_ambiguous_ticket_is_exit_2(patch_gh, capsys):
    patch_gh(FakeGh([]))
    rc = ce_cli.main(["claim", "status", "38"])  # no --repo
    assert rc == 2
    assert "ambiguous" in capsys.readouterr().err.lower()


def test_status_bare_number_with_repo_ok(patch_gh, capsys):
    patch_gh(FakeGh([]))
    rc = ce_cli.main(["claim", "status", "38", "--repo", "creator-engine/ce-ops", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["work_key"] == WK


def test_status_unavailable_gh_is_exit_2(patch_gh, capsys):
    patch_gh(FakeGh([], get_rc=1))
    rc = ce_cli.main(["claim", "status", "creator-engine/ce-ops#38"])
    assert rc == 2


def test_status_invalid_marker_is_exit_1(patch_gh, capsys):
    bad = f"{wc.SENTINEL}\n```json\n{{\"action\": \"acquire\", \"work_key\": \"{WK}\"}}\n```"
    patch_gh(FakeGh([_comment(1, bad)]))
    rc = ce_cli.main(["claim", "status", "creator-engine/ce-ops#38"])
    assert rc == 1


def test_status_write_cache(patch_gh, tmp_path):
    patch_gh(FakeGh([_comment(1, _acquire_body("wclaim-a"))]))
    rc = ce_cli.main(["claim", "status", "creator-engine/ce-ops#38",
                      "--write-cache", str(tmp_path)])
    assert rc == 0
    cache_file = tmp_path / "claims" / "claims.json"
    assert cache_file.is_file()
    cache = json.loads(cache_file.read_text())
    assert cache["repo"] == "creator-engine/ce-ops"
    assert cache["active"]["claim_id"] == "wclaim-a"


# --- acquire -----------------------------------------------------------------


def test_acquire_clean_ok(patch_gh, capsys):
    gh = patch_gh(FakeGh([]))
    rc = ce_cli.main(["claim", "acquire", "creator-engine/ce-ops#38",
                      "--holder", "ce-dev-2", "--host", "H", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert any(wc.SENTINEL in p for p in gh.posts)


def test_acquire_conflict_is_exit_1(patch_gh, capsys):
    patch_gh(FakeGh([_comment(1, _acquire_body("wclaim-foreign", holder="other", host="X"))]))
    rc = ce_cli.main(["claim", "acquire", "creator-engine/ce-ops#38",
                      "--holder", "ce-dev-2", "--host", "H"])
    assert rc == 1
    assert "refused" in capsys.readouterr().err.lower()


# --- release -----------------------------------------------------------------


def test_release_by_claim_id_ok(patch_gh, capsys):
    gh = patch_gh(FakeGh([_comment(1, _acquire_body("wclaim-a", holder="ce-dev-2", host="H"))]))
    rc = ce_cli.main(["claim", "release", "creator-engine/ce-ops#38", "--claim-id", "wclaim-a"])
    assert rc == 0
    assert any('"action": "release"' in p for p in gh.posts)


def test_release_foreign_active_without_claim_id_is_exit_1(patch_gh, capsys):
    # No --claim-id → release targets the active claim only if it is ours; a
    # foreign holder/host (never this hostname) refuses.
    patch_gh(FakeGh([_comment(1, _acquire_body("wclaim-a", holder="other", host="not-this-host"))]))
    rc = ce_cli.main(["claim", "release", "creator-engine/ce-ops#38"])
    assert rc == 1
