"""Unit tests for the ce-ops#38 work-claim hook on the v3 dispatch paths.

Asserts that ``cev3 drive --spawn --ticket`` and ``cev3 review --spawn --ticket``
acquire + verify the work claim BEFORE any dispatch/venue side effect, that a
foreign active claim produces NO dispatch directory and NO seat spawn, and that a
spawn refusal AFTER the claim was acquired posts a best-effort structured release.

The seat-bridge subprocess legs and the forge ``GhRunner`` are both faked — no
network, no tmux.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from creator_engine_validator import v3_cli, v3_seat_bridge, work_claims as wc

APPROVER = "a" * 64
NOW = datetime(2026, 6, 12, 15, 0, 0, tzinfo=timezone.utc)
WK = "creator-engine/ce-ops:issue:38"


def _ts(delta=timedelta(0)):
    """Clock-relative ISO-``Z`` timestamp derived from the frozen ``NOW``.

    Fixtures express age relative to ``NOW`` so they stay date-independent: with
    ``stale_after_seconds = 14400`` (4h), ``NOW - 1h`` is active and ``NOW - 6h``
    is stale on any host date once the work-claim clock is frozen to ``NOW``.
    """
    return (NOW + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(autouse=True)
def _frozen_work_claim_clock(freeze_work_claim_clock):
    # The v3 dispatch claim path reads wall-clock time; freeze it to NOW so the
    # active-foreign fixture below cannot rot into a stale claim (ce-ops#57).
    freeze_work_claim_clock(NOW)


# --- forge fake --------------------------------------------------------------


class FakeGh:
    def __init__(self, comments=None):
        self.comments = [dict(c) for c in (comments or [])]
        self.next_id = max((c["id"] for c in self.comments), default=0) + 1
        self.posts: list[str] = []

    def __call__(self, argv, input_text=None):
        method = argv[argv.index("--method") + 1] if "--method" in argv else "GET"
        if method == "POST":
            body = json.loads(input_text)["body"]
            cid = self.next_id
            self.next_id += 1
            self.comments.append({"id": cid, "body": body, "created_at": _ts(),
                                  "user": {"login": "bot"}})
            self.posts.append(body)
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": cid}), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.comments), stderr="")


def _foreign_acquire(claim_id="wclaim-foreign"):
    # Active relative to NOW: claimed 1h ago against a 4h (14400s) stale fence.
    claimed = _ts(timedelta(hours=-1))
    body = wc.render_marker({
        "kind": "ce-work-claim", "schema_version": 1, "action": "acquire",
        "work_key": WK, "claim_id": claim_id, "holder": "other-controller", "host": "other-host",
        "claimed_at": claimed, "stale_after_seconds": 14400, "idempotency_key": "i"})
    return {"id": 1, "body": body, "created_at": claimed, "user": {"login": "x"}}


# --- bridge fakes ------------------------------------------------------------


def _fake_bridge(monkeypatch):
    calls: dict[str, list] = {"spawn": [], "seed": []}

    def fake_spawn(record):
        record.data["terminal"] = {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%9"}
        record.data["resource_bound"] = {"unit": "ce-seat-x"}
        record.data["spawned_at"] = "20260611T000000Z"
        v3_seat_bridge._write_record(record)
        calls["spawn"].append(record.run_id)
        return v3_seat_bridge.SpawnResult(run_id=record.run_id,
                                          terminal=dict(record.data["terminal"]),
                                          resource_bound={"unit": "ce-seat-x"})

    def fake_seed(record):
        calls["seed"].append(record.run_id)

    monkeypatch.setattr(v3_seat_bridge, "spawn_seat", fake_spawn)
    monkeypatch.setattr(v3_seat_bridge, "seed_brief", fake_seed)
    return calls


def _patch_gh(monkeypatch, gh):
    monkeypatch.setattr(v3_cli, "_make_gh_runner", lambda: gh)
    monkeypatch.setattr(wc.time, "sleep", lambda s: None)
    return gh


def _file_ready(tmp_path):
    v3_cli.main(["scope", "rate-limit-login", "--goal", "rate-limit POST /api/login",
                 "--done-when", "a", "--done-when", "b", "--done-when", "c",
                 "--change-type", "code", "--budget", "5", "--budget-unit", "$",
                 "--root", str(tmp_path)])
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])


# --- drive -------------------------------------------------------------------


def test_drive_spawn_with_ticket_claims_then_dispatches(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    gh = _patch_gh(monkeypatch, FakeGh([]))  # unclaimed issue
    _file_ready(tmp_path)
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--ticket",
                        "creator-engine/ce-ops#38", "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    run_id = payload["run_id"]
    # a structured acquire was posted, the seat spawned, dispatch landed on disk
    assert any(wc.SENTINEL in p and '"action": "acquire"' in p for p in gh.posts)
    assert calls["spawn"] == [run_id]
    assert (tmp_path / "dispatches" / run_id / "dispatch.yaml").is_file()


def test_drive_spawn_foreign_claim_refuses_no_dispatch(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    gh = _patch_gh(monkeypatch, FakeGh([_foreign_acquire()]))
    _file_ready(tmp_path)
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--ticket",
                        "creator-engine/ce-ops#38", "--root", str(tmp_path), "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    # ce-ops#57 date-bomb guard: the foreign fixture must be ACTIVE (not stale)
    # relative to NOW. If the dispatch path ever evaluated it against wall-clock
    # time again, this fixture would read stale and the reason would flip to
    # ``claim_stale_foreign_claim`` — that is exactly the #218 regression.
    foreign = _foreign_acquire()
    st = wc.compute_state([wc.Comment(foreign["id"], foreign["body"], foreign["created_at"])], WK, NOW)
    assert st.active is not None and st.active.stale is False
    assert payload["reason"] == "claim_active_foreign_claim"
    # refuse BEFORE side effect: no dispatch dir, no spawn, nothing posted
    assert calls["spawn"] == []
    assert gh.posts == []
    assert not (tmp_path / "dispatches").exists()


def test_drive_spawn_refusal_posts_best_effort_release(tmp_path, capsys, monkeypatch):
    _fake_bridge(monkeypatch)
    gh = _patch_gh(monkeypatch, FakeGh([]))

    def boom(record):
        raise v3_seat_bridge.SeatBridgeError("launch leg refused")

    monkeypatch.setattr(v3_seat_bridge, "spawn_seat", boom)
    _file_ready(tmp_path)
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--ticket",
                        "creator-engine/ce-ops#38", "--root", str(tmp_path), "--json"])
    assert code == 1
    # we acquired (posted) and then released best-effort on the refused leg
    assert any('"action": "acquire"' in p for p in gh.posts)
    assert any('"action": "release"' in p and "spawn-refused-before-side-effect" in p
               for p in gh.posts)


def test_drive_spawn_without_ticket_unchanged(tmp_path, capsys, monkeypatch):
    # No --ticket → legacy behavior, no forge call at all.
    calls = _fake_bridge(monkeypatch)
    gh = _patch_gh(monkeypatch, FakeGh([]))
    _file_ready(tmp_path)
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--root", str(tmp_path), "--json"])
    assert code == 0
    assert gh.posts == []  # the claim hook is inert without --ticket
    assert len(calls["spawn"]) == 1


# --- review ------------------------------------------------------------------


def _dispatch_with_pr(tmp_path, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    _file_ready(tmp_path)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        v3_cli.main(["drive", "rate-limit-login", "--spawn", "--root", str(tmp_path), "--json"])
    run_id = json.loads(buf.getvalue())["run_id"]
    path = tmp_path / "dispatches" / run_id / "dispatch.yaml"
    drec = yaml.safe_load(path.read_text(encoding="utf-8"))
    drec["change"] = {"branch": "b", "base": "main", "pr_number": 7, "head_sha": "d" * 40,
                      "manifest_paths": ["validators/x.py"], "opened_at": "2026-06-11T09:30:00Z"}
    path.write_text(yaml.safe_dump(drec, sort_keys=True), encoding="utf-8")
    return run_id


def test_review_spawn_with_ticket_claims_before_venue(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_with_pr(tmp_path, monkeypatch)
    gh = _patch_gh(monkeypatch, FakeGh([]))
    seen = {}

    def fake_venue(rec, *, controller_id, venue_root, ledger_root, seat_env_file=None):
        seen["called"] = True
        return v3_seat_bridge.SpawnResult(
            run_id=rec.run_id, terminal={"kind": "tmux", "session_id": "$5", "window_id": "@6", "pane_id": "%7"})

    monkeypatch.setattr(v3_seat_bridge, "spawn_review_venue", fake_venue)
    capsys.readouterr()
    code = v3_cli.main(["review", "rate-limit-login", "--run", run_id, "--reviewer-actor", "rev-login",
                        "--spawn", "--venue-root", str(tmp_path / "venues"),
                        "--ledger-root", str(tmp_path / "ledger"), "--ticket",
                        "creator-engine/ce-ops#38", "--root", str(tmp_path), "--json"])
    assert code == 0
    assert seen.get("called") is True
    assert any('"action": "acquire"' in p for p in gh.posts)


def test_review_spawn_foreign_claim_refuses_before_venue(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_with_pr(tmp_path, monkeypatch)
    gh = _patch_gh(monkeypatch, FakeGh([_foreign_acquire()]))
    seen = {}

    def fake_venue(rec, **_kw):
        seen["called"] = True
        return v3_seat_bridge.SpawnResult(run_id=rec.run_id, terminal={})

    monkeypatch.setattr(v3_seat_bridge, "spawn_review_venue", fake_venue)
    capsys.readouterr()
    code = v3_cli.main(["review", "rate-limit-login", "--run", run_id, "--reviewer-actor", "rev-login",
                        "--spawn", "--venue-root", str(tmp_path / "venues"),
                        "--ledger-root", str(tmp_path / "ledger"), "--ticket",
                        "creator-engine/ce-ops#38", "--root", str(tmp_path), "--json"])
    assert code == 1
    assert "called" not in seen  # venue never allocated
    assert gh.posts == []
