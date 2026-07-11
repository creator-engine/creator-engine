import json
import subprocess
from datetime import datetime, timezone

from creator_engine_validator.forge import review_acting, review_pickup


class _FakeGhRunner:
    def __init__(self, *, stdout='{"html_url": "https://example.test/comment/1"}', returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.calls = []

    def __call__(self, argv, input_text=None):
        self.calls.append((list(argv), input_text))
        if "GET" not in argv and any("/pulls/" in part for part in argv):
            number = int(next(part.rsplit("/", 1)[1] for part in argv if "/pulls/" in part))
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({
                "number": number,
                "base": {"repo": {"full_name": "owner/repo"}},
                "head": {"sha": "a" * 40},
            }), stderr="")
        return subprocess.CompletedProcess(argv, self.returncode, stdout=self.stdout, stderr="")


def _item(number=42, **overrides):
    item = {
        "repo": "owner/repo",
        "number": number,
        "head_sha": "a" * 40,
        "url": f"https://example.test/owner/repo/pull/{number}",
        "title": "Normal title",
        "assigned_reviewer": "ce-dev-3",
        "author": "ce-dev-4",
        "reason": "awaiting_review",
    }
    item.update(overrides)
    return item


def _clock():
    return datetime(2026, 7, 10, 16, 0, tzinfo=timezone.utc)


def _evidence(ctx, verdict="review verdict", **authority_overrides):
    authority = {
        "repo": ctx.repo,
        "pr_number": ctx.pr_number,
        "head_sha": ctx.head_sha,
        "actor": ctx.assigned_reviewer,
    }
    authority.update(authority_overrides)
    return json.dumps({
        "verdict": verdict,
        "reviewer": ctx.assigned_reviewer,
        "reviewer_authority": authority,
    })


def test_is_acting_enabled_defaults_off_and_requires_one():
    assert review_acting.is_acting_enabled({}) is False
    assert review_acting.is_acting_enabled({review_acting.ACTING_ENABLED_ENV: "0"}) is False
    assert review_acting.is_acting_enabled({review_acting.ACTING_ENABLED_ENV: "1"}) is True


def test_load_acting_ledger_missing_file_is_empty(tmp_path):
    assert review_acting.load_acting_ledger(tmp_path / "missing.ndjson") == []


def test_acting_ledger_ndjson_round_trip_and_key_shape(tmp_path):
    ledger = tmp_path / "acting" / "ledger.ndjson"
    record = {"thread_id": "review-acting:owner/repo:42", "item_id": "owner/repo:42", "action": "comment_posted"}
    review_acting.append_acting_ledger(ledger, record)

    assert review_acting.load_acting_ledger(ledger) == [record]
    assert review_acting.acting_ledger_key("owner/repo", 42) == (
        "review-acting:owner/repo:42", "owner/repo:42", "comment_posted"
    )
    assert review_acting.acting_ledger_keys([record]) == {review_acting.acting_ledger_key("owner/repo", 42)}


def test_run_acting_pass_skips_ledgered_pr(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    review_acting.append_acting_ledger(ledger, {
        "thread_id": "review-acting:owner/repo:42", "item_id": "owner/repo:42", "action": "comment_posted",
    })
    called = []

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=_FakeGhRunner(), acting_ledger_path=ledger,
        spawner=lambda ctx, runner: called.append(ctx) or "verdict",
    )

    assert len(result.skipped_dedup) == 1
    assert result.commented == ()
    assert called == []


def test_run_acting_pass_spawns_and_posts_comment(tmp_path):
    runner = _FakeGhRunner()
    spawned = []
    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=tmp_path / "ledger.ndjson",
        spawner=lambda ctx, received_runner: spawned.append((ctx, received_runner)) or _evidence(ctx),
        clock=_clock,
    )

    assert len(spawned) == 1
    assert spawned[0][1] is runner
    assert result.commented[0]["action"] == "comment_posted"
    post = next(call for call in runner.calls if "/issues/" in " ".join(call[0]))
    assert json.loads(post[1]) == {"body": "review verdict"}


def test_spawn_failure_logs_continues_and_is_durable(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    logs = []

    def spawn(ctx, runner):
        if ctx.pr_number == 42:
            raise RuntimeError("spawn refused")
        return _evidence(ctx, "verdict")

    result = review_acting.run_acting_pass(
        items=[_item(42), _item(43)], gh_runner=_FakeGhRunner(), acting_ledger_path=ledger,
        spawner=spawn, log_sink=logs.append, clock=_clock,
    )

    assert result.failed[0]["action"] == "spawn_failed"
    assert len(result.commented) == 1
    assert logs[0]["event"] == "review_acting_spawn_failed"
    assert review_acting.load_acting_ledger(ledger)[1]["action"] == "spawn_failed"


def test_run_acting_pass_refuses_head_drift_before_comment_post(tmp_path):
    calls = []

    def runner(argv, input_text=None):
        calls.append((list(argv), input_text))
        if any("/pulls/" in part for part in argv):
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({
                "number": 42,
                "base": {"repo": {"full_name": "owner/repo"}},
                "head": {"sha": "b" * 40},
            }), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout='{"html_url": "unexpected"}', stderr="")

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=tmp_path / "ledger.ndjson",
        spawner=lambda ctx, _: _evidence(ctx), clock=_clock,
    )

    assert result.failed[0]["action"] == "live_claim_mismatch"
    assert not any("/issues/" in " ".join(argv) for argv, _ in calls)


def test_run_acting_pass_refuses_unbound_stale_or_self_reviewer_evidence(tmp_path):
    cases = (
        ("malformed", _item(), lambda ctx: "not-json"),
        ("stale", _item(), lambda ctx: _evidence(ctx, head_sha="b" * 40)),
        ("self", _item(author="ce-dev-3"), lambda ctx: _evidence(ctx)),
    )
    for label, item, output in cases:
        calls = []
        runner = _FakeGhRunner()
        runner.calls = calls
        result = review_acting.run_acting_pass(
            items=[item], gh_runner=runner, acting_ledger_path=tmp_path / f"{label}.ndjson",
            spawner=lambda ctx, _: output(ctx), clock=_clock,
        )

        assert result.failed[0]["action"] == "reviewer_authority_invalid"
        assert not any("/issues/" in " ".join(argv) for argv, _ in calls)


def test_run_acting_pass_caps_durable_spawn_retries(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    spawned = []

    def fail_spawn(ctx, _):
        spawned.append(ctx)
        raise RuntimeError("transient spawn failure")

    results = [
        review_acting.run_acting_pass(
            items=[_item()], gh_runner=_FakeGhRunner(), acting_ledger_path=ledger,
            spawner=fail_spawn, clock=_clock,
        )
        for _ in range(review_acting.MAX_ATTEMPTS_PER_CLAIM + 1)
    ]

    assert len(spawned) == review_acting.MAX_ATTEMPTS_PER_CLAIM
    assert results[-1].failed[0]["action"] == "retry_exhausted"
    assert sum(
        record["action"] == "attempt_claimed"
        for record in review_acting.load_acting_ledger(ledger)
    ) == review_acting.MAX_ATTEMPTS_PER_CLAIM


def test_cross_restart_dedup_after_comment(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    first = review_acting.run_acting_pass(
        items=[_item()], gh_runner=_FakeGhRunner(), acting_ledger_path=ledger,
        spawner=lambda ctx, runner: _evidence(ctx, "verdict"),
    )
    second = review_acting.run_acting_pass(
        items=[_item()], gh_runner=_FakeGhRunner(), acting_ledger_path=ledger,
        spawner=lambda ctx, runner: _evidence(ctx, "must not run"),
    )

    assert len(first.commented) == 1
    assert len(second.skipped_dedup) == 1


def test_post_pr_comment_uses_only_issues_comments_endpoint():
    runner = _FakeGhRunner()

    assert review_acting.post_pr_comment("owner/repo", 42, "verdict", gh_runner=runner) == "https://example.test/comment/1"
    command = runner.calls[0][0]
    assert "repos/owner/repo/issues/42/comments" in command
    assert not any("pulls/42/reviews" in part for part in command)


def test_unconfigured_default_spawner_records_incident(tmp_path, monkeypatch):
    monkeypatch.delenv(review_acting.ACTING_SPAWN_COMMAND_ENV, raising=False)
    logs = []

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=_FakeGhRunner(), acting_ledger_path=tmp_path / "ledger.ndjson",
        log_sink=logs.append, clock=_clock,
    )

    assert result.failed[0]["action"] == "spawner_unconfigured"
    assert logs[0]["event"] == "review_acting_spawner_unconfigured"


def test_default_spawner_substitutes_template_without_shell_or_title_injection(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="verdict\n", stderr="")

    monkeypatch.setenv(
        review_acting.ACTING_SPAWN_COMMAND_ENV,
        "reviewer-spawn --repo {repo} --number {number} --head {head_sha} --url {url}",
    )
    monkeypatch.setattr(review_acting.subprocess, "run", fake_run)
    ctx = review_acting.ActingContext(
        repo="owner/repo", pr_number=42, head_sha="a" * 40,
        url="https://example.test/pull/42?a=1&b=2", title="$(would-run-if-shell)", assigned_reviewer="ce-dev-3",
        author="ce-dev-4",
    )

    assert review_acting.default_spawner(ctx, _FakeGhRunner()) == "verdict"
    argv, kwargs = calls[0]
    assert argv == [
        "reviewer-spawn", "--repo", "owner/repo", "--number", "42", "--head", "a" * 40,
        "--url", "https://example.test/pull/42?a=1&b=2",
    ]
    assert "$(would-run-if-shell)" not in argv
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 180


def test_review_pickup_loop_forwards_optional_on_pass_items(monkeypatch):
    received = []
    expected = (_item(),)

    def fake_poll(**kwargs):
        callback = kwargs.get("on_pass_items")
        if callback is not None:
            callback(expected, kwargs["gh_runner"])
        return review_pickup.ReviewPickupResult(items=expected)

    monkeypatch.setattr(review_pickup, "poll_review_pickup", fake_poll)
    runner = _FakeGhRunner()
    result = review_pickup.run_review_pickup_loop(
        token="token", reviewer_seats=["ce-dev-3"], gh_runner=runner, repo="owner/repo",
        apply=True, iterations=1, on_pass_items=lambda items, runner: received.append((items, runner)),
    )

    assert result.passes[0].items == expected
    assert received == [(expected, runner)]
