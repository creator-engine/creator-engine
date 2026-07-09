import json
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace

from creator_engine_validator.forge import review_dry_run
from creator_engine_validator.pickup_search import PickupRateLimited


class _FakeGhRunner:
    def __init__(self, *, stdout="[]", returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.calls = []

    def __call__(self, argv, input_text=None):
        self.calls.append((list(argv), input_text))
        return subprocess.CompletedProcess(
            argv,
            self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
        )


def _clock():
    return datetime(2026, 7, 9, 4, 0, tzinfo=timezone.utc)


def _item(*, repo="owner/repo", number=42, reviewer="reviewer-a", head_sha="h" * 40):
    return {
        "repo": repo,
        "number": number,
        "head_sha": head_sha,
        "assigned_reviewer": reviewer,
        "reason": "awaiting_review",
        "dry_run": True,
    }


def _result(*, items=(), skipped=()):
    return SimpleNamespace(items=tuple(items), skipped=tuple(skipped))


def test_is_operator_held_label_match():
    runner = _FakeGhRunner(stdout=json.dumps([{"name": "awaiting-operator"}]))

    assert review_dry_run.is_operator_held("owner/repo", 42, runner) is True
    assert runner.calls[0][0] == ["gh", "api", "--method", "GET", "repos/owner/repo/issues/42/labels"]


def test_is_operator_held_label_absent():
    runner = _FakeGhRunner(stdout="[]")

    assert review_dry_run.is_operator_held("owner/repo", 42, runner) is False


def test_is_operator_held_custom_held_label():
    runner = _FakeGhRunner(stdout=json.dumps([{"name": "on-hold"}]))

    assert review_dry_run.is_operator_held("owner/repo", 42, runner, held_label="on-hold") is True


def test_is_operator_held_held_list_file_match(tmp_path):
    held = tmp_path / "held.txt"
    held.write_text("owner/repo#42\n", encoding="utf-8")
    runner = _FakeGhRunner(stdout="[]")

    assert review_dry_run.is_operator_held("owner/repo", 42, runner, held_list_path=held) is True


def test_is_operator_held_held_list_bare_number_match(tmp_path):
    held = tmp_path / "held.txt"
    held.write_text("42\n", encoding="utf-8")
    runner = _FakeGhRunner(stdout="[]")

    assert review_dry_run.is_operator_held("other/repo", 42, runner, held_list_path=held) is True


def test_is_operator_held_held_list_miss(tmp_path):
    held = tmp_path / "held.txt"
    held.write_text("99\n", encoding="utf-8")
    runner = _FakeGhRunner(stdout="[]")

    assert review_dry_run.is_operator_held("owner/repo", 42, runner, held_list_path=held) is False


def test_is_operator_held_label_api_failure_fail_open():
    logs = []
    runner = _FakeGhRunner(stdout="", returncode=1, stderr="boom")

    assert review_dry_run.is_operator_held("owner/repo", 42, runner, log_sink=logs.append) is False
    assert logs[0]["event"] == "review_dry_run_operator_label_read_failed"


def test_run_dry_run_pass_would_assign_emitted(monkeypatch):
    monkeypatch.setattr(
        review_dry_run,
        "poll_review_pickup",
        lambda **kwargs: _result(items=[_item()]),
    )
    monkeypatch.setattr(review_dry_run, "is_operator_held", lambda *args, **kwargs: False)

    would_assign, would_skip = review_dry_run.run_dry_run_pass(
        token="ghp_fake",
        reviewer_seats=["reviewer-a"],
        gh_runner=_FakeGhRunner(),
        repo="owner/repo",
        clock=_clock,
    )

    assert would_skip == []
    assert would_assign == [{
        "event": "WOULD_ASSIGN",
        "repo": "owner/repo",
        "pr": 42,
        "head_sha": "h" * 40,
        "assigned_reviewer": "reviewer-a",
        "reason": "awaiting_review",
        "ts": "2026-07-09T04:00:00Z",
    }]


def test_run_dry_run_pass_operator_held_item_becomes_would_skip(monkeypatch):
    monkeypatch.setattr(
        review_dry_run,
        "poll_review_pickup",
        lambda **kwargs: _result(items=[_item()]),
    )
    monkeypatch.setattr(review_dry_run, "is_operator_held", lambda *args, **kwargs: True)

    would_assign, would_skip = review_dry_run.run_dry_run_pass(
        token="ghp_fake",
        reviewer_seats=["reviewer-a"],
        gh_runner=_FakeGhRunner(),
        repo="owner/repo",
        clock=_clock,
    )

    assert would_assign == []
    assert len(would_skip) == 1
    assert would_skip[0]["event"] == "WOULD_SKIP"
    assert would_skip[0]["skip_reason"] == "operator_held"
    assert would_skip[0]["head_sha"] == "h" * 40


def test_run_dry_run_pass_internally_skipped_items_become_would_skip(monkeypatch):
    monkeypatch.setattr(
        review_dry_run,
        "poll_review_pickup",
        lambda **kwargs: _result(
            skipped=[{
                "repo": "owner/repo",
                "number": 42,
                "head_sha": None,
                "reason": "draft_pull_request",
            }],
        ),
    )

    would_assign, would_skip = review_dry_run.run_dry_run_pass(
        token="ghp_fake",
        reviewer_seats=["reviewer-a"],
        gh_runner=_FakeGhRunner(),
        repo="owner/repo",
        clock=_clock,
    )

    assert would_assign == []
    assert would_skip == [{
        "event": "WOULD_SKIP",
        "repo": "owner/repo",
        "pr": 42,
        "head_sha": None,
        "skip_reason": "draft_pull_request",
        "ts": "2026-07-09T04:00:00Z",
    }]


def test_run_dry_run_pass_jsonl_feed_written(monkeypatch, tmp_path):
    monkeypatch.setattr(
        review_dry_run,
        "poll_review_pickup",
        lambda **kwargs: _result(items=[_item()]),
    )
    monkeypatch.setattr(review_dry_run, "is_operator_held", lambda *args, **kwargs: False)
    feed = tmp_path / "review" / "feed.jsonl"

    review_dry_run.run_dry_run_pass(
        token="ghp_fake",
        reviewer_seats=["reviewer-a"],
        gh_runner=_FakeGhRunner(),
        repo="owner/repo",
        feed_path=feed,
        clock=_clock,
    )

    lines = feed.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event"] == "WOULD_ASSIGN"


def test_run_dry_run_pass_feed_appended_across_passes(monkeypatch, tmp_path):
    numbers = iter([42, 43])

    def fake_poll(**kwargs):
        return _result(items=[_item(number=next(numbers))])

    monkeypatch.setattr(review_dry_run, "poll_review_pickup", fake_poll)
    monkeypatch.setattr(review_dry_run, "is_operator_held", lambda *args, **kwargs: False)
    feed = tmp_path / "feed.jsonl"

    for _ in range(2):
        review_dry_run.run_dry_run_pass(
            token="ghp_fake",
            reviewer_seats=["reviewer-a"],
            gh_runner=_FakeGhRunner(),
            repo="owner/repo",
            feed_path=feed,
            clock=_clock,
        )

    assert len(feed.read_text(encoding="utf-8").splitlines()) == 2


def test_run_dry_run_loop_bounded_iterations(monkeypatch):
    calls = []

    def fake_pass(**kwargs):
        calls.append(kwargs)
        return ([{"event": "WOULD_ASSIGN", "pr": len(calls)}], [])

    monkeypatch.setattr(review_dry_run, "run_dry_run_pass", fake_pass)

    result = review_dry_run.run_dry_run_loop(
        token="ghp_fake",
        reviewer_seats=["reviewer-a"],
        gh_runner=_FakeGhRunner(),
        repo="owner/repo",
        iterations=2,
        sleep=lambda seconds: None,
    )

    assert len(result) == 2
    assert len(calls) == 2


def test_run_dry_run_loop_rate_limited_pass_is_logged_and_continues(monkeypatch):
    calls = []
    logs = []

    def fake_pass(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise PickupRateLimited("slow down", status=429, retry_after_seconds=5)
        return ([{"event": "WOULD_ASSIGN", "pr": 42}], [])

    monkeypatch.setattr(review_dry_run, "run_dry_run_pass", fake_pass)

    result = review_dry_run.run_dry_run_loop(
        token="ghp_fake",
        reviewer_seats=["reviewer-a"],
        gh_runner=_FakeGhRunner(),
        repo="owner/repo",
        iterations=2,
        sleep=lambda seconds: None,
        log_sink=logs.append,
    )

    assert result == [([{"event": "WOULD_ASSIGN", "pr": 42}], [])]
    assert len(calls) == 2
    assert logs[0]["event"] == "review_dry_run_rate_limited"
    assert logs[0]["status"] == 429


def test_run_dry_run_pass_pins_dry_run_kwargs(monkeypatch):
    """Pin the dry-run invariant at assertion level: a refactor that flips
    apply/dry_run on the poll_review_pickup call must fail this test."""
    captured = {}

    def _capture(**kwargs):
        captured.update(kwargs)
        return _result(items=[])

    monkeypatch.setattr(review_dry_run, "poll_review_pickup", _capture)

    review_dry_run.run_dry_run_pass(
        token="ghp_fake",
        reviewer_seats=["reviewer-a"],
        gh_runner=_FakeGhRunner(),
        repo="owner/repo",
        clock=_clock,
    )

    assert captured["apply"] is False
    assert captured["dry_run"] is True
