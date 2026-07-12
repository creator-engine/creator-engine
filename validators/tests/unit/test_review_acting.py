import json
import subprocess
from datetime import datetime, timezone

from creator_engine_validator.forge import review_acting, review_pickup


class _FakeGhRunner:
    def __init__(
        self, *, stdout='{"html_url": "https://example.test/comment/1"}', returncode=0,
        head_sha="a" * 40,
    ):
        self.stdout = stdout
        self.returncode = returncode
        self.head_sha = head_sha
        self.calls = []

    def __call__(self, argv, input_text=None):
        self.calls.append((list(argv), input_text))
        if "GET" not in argv and any("/pulls/" in part for part in argv):
            number = int(next(part.rsplit("/", 1)[1] for part in argv if "/pulls/" in part))
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({
                "number": number,
                "base": {"repo": {"full_name": "owner/repo"}},
                "head": {"sha": self.head_sha},
            }), stderr="")
        return subprocess.CompletedProcess(argv, self.returncode, stdout=self.stdout, stderr="")


def _item(number=42, **overrides):
    item = {
        "repo": "owner/repo",
        "number": number,
        "head_sha": "a" * 40,
        "url": f"https://example.test/owner/repo/pull/{number}",
        "title": "Normal title",
        "assigned_reviewer": "reviewer-seat-a",
        "author": "author-seat-b",
        "reason": "awaiting_review",
    }
    item.update(overrides)
    return item


def _clock():
    return datetime(2026, 7, 10, 16, 0, tzinfo=timezone.utc)


def _evidence(ctx, verdict="COMMENT", **authority_overrides):
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


def test_versioned_authority_envelope_remains_dual_supported():
    ctx = review_acting._context_from_item(_item())
    assert review_acting._reviewer_verdict(json.dumps({
        "version": 1, "verdict": "COMMENT", "reviewer": ctx.assigned_reviewer,
        "authority": {"repo": ctx.repo, "pr_number": ctx.pr_number,
                      "head_sha": ctx.head_sha, "actor": ctx.assigned_reviewer},
    }), ctx) == "COMMENT"


def _claim(attempt):
    return {
        "action": "attempt_claimed",
        "repo": "owner/repo",
        "pr_number": 42,
        "head_sha": "a" * 40,
        "assigned_reviewer": "reviewer-seat-a",
        "attempt": attempt,
    }


def test_is_acting_enabled_defaults_off_and_requires_one():
    assert review_acting.is_acting_enabled({}) is False
    assert review_acting.is_acting_enabled({review_acting.ACTING_ENABLED_ENV: "0"}) is False
    assert review_acting.is_acting_enabled({review_acting.ACTING_ENABLED_ENV: "1"}) is True


def test_load_acting_ledger_missing_file_is_empty(tmp_path):
    assert review_acting.load_acting_ledger(tmp_path / "missing.ndjson") == []


def test_acting_ledger_ndjson_round_trip_and_key_shape(tmp_path):
    ledger = tmp_path / "acting" / "ledger.ndjson"
    head_sha = "a" * 40
    record = {
        "thread_id": f"review-acting:owner/repo:42:{head_sha}",
        "item_id": f"owner/repo:42:{head_sha}",
        "action": "comment_posted",
        "repo": "owner/repo",
        "pr_number": 42,
        "head_sha": head_sha,
    }
    review_acting.append_acting_ledger(ledger, record)

    assert review_acting.load_acting_ledger(ledger) == [record]
    assert review_acting.acting_ledger_key("owner/repo", 42, head_sha) == (
        f"review-acting:owner/repo:42:{head_sha}", f"owner/repo:42:{head_sha}", "comment_posted"
    )
    assert review_acting.acting_ledger_keys([record]) == {
        review_acting.acting_ledger_key("owner/repo", 42, head_sha)
    }


def test_run_acting_pass_skips_ledgered_pr(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    head_sha = "a" * 40
    review_acting.append_acting_ledger(ledger, {
        "thread_id": f"review-acting:owner/repo:42:{head_sha}",
        "item_id": f"owner/repo:42:{head_sha}",
        "action": "comment_posted",
        "repo": "owner/repo",
        "pr_number": 42,
        "head_sha": head_sha,
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
    assert json.loads(post[1]) == {"body": "COMMENT"}


def test_spawn_failure_logs_continues_and_is_durable(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    logs = []

    def spawn(ctx, runner):
        if ctx.pr_number == 42:
            raise RuntimeError("spawn refused")
        return _evidence(ctx, "COMMENT")

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
        ("self", _item(author="reviewer-seat-a"), lambda ctx: _evidence(ctx)),
        ("approve", _item(), lambda ctx: _evidence(ctx, verdict="APPROVE")),
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


def test_default_spawner_uses_configured_provider_timeout(monkeypatch):
    observed = {}

    def fake_run(argv, **kwargs):
        observed.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    monkeypatch.setenv(review_acting.ACTING_SPAWN_COMMAND_ENV, "reviewer --head {head_sha}")
    monkeypatch.setenv("CE_REVIEW_SPAWN_TIMEOUT_SECONDS", "17")
    monkeypatch.setattr(review_acting.subprocess, "run", fake_run)
    review_acting.default_spawner(review_acting._context_from_item(_item()), _FakeGhRunner())
    assert observed["timeout"] == 17


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


def test_run_acting_pass_refuses_lone_cap_claim_without_spawning_or_github(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    ledger.write_text(json.dumps(_claim(review_acting.MAX_ATTEMPTS_PER_CLAIM)) + "\n", encoding="utf-8")
    runner = _FakeGhRunner()
    spawned = []

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=ledger,
        spawner=lambda ctx, _: spawned.append(ctx) or _evidence(ctx), clock=_clock,
    )

    assert result.failed[0]["action"] == "retry_exhausted"
    assert spawned == []
    assert runner.calls == []


def test_run_acting_pass_refuses_nonmonotonic_claim_sequence_without_acting(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    ledger.write_text(
        "\n".join(json.dumps(_claim(attempt)) for attempt in (2, 1)) + "\n",
        encoding="utf-8",
    )
    runner = _FakeGhRunner()
    spawned = []

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=ledger,
        spawner=lambda ctx, _: spawned.append(ctx) or _evidence(ctx), clock=_clock,
    )

    assert result.failed[0]["action"] == "ledger_unreadable"
    assert spawned == []
    assert runner.calls == []


def test_run_acting_pass_refuses_terminal_retry_evidence_without_acting(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    ledger.write_text(
        "\n".join((
            json.dumps(_claim(review_acting.MAX_ATTEMPTS_PER_CLAIM)),
            json.dumps({
                "action": "retry_exhausted", "repo": "owner/repo", "pr_number": 42,
                "head_sha": "a" * 40,
            }),
        )) + "\n",
        encoding="utf-8",
    )
    runner = _FakeGhRunner()
    spawned = []

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=ledger,
        spawner=lambda ctx, _: spawned.append(ctx) or _evidence(ctx), clock=_clock,
    )

    assert result.failed[0]["action"] == "retry_exhausted"
    assert spawned == []
    assert runner.calls == []


def test_run_acting_pass_refuses_action_after_terminal_evidence_without_acting(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    ledger.write_text(
        "\n".join((
            json.dumps(_claim(review_acting.MAX_ATTEMPTS_PER_CLAIM)),
            json.dumps({
                "action": "retry_exhausted", "repo": "owner/repo", "pr_number": 42,
                "head_sha": "a" * 40,
            }),
            json.dumps({
                "action": "spawn_failed", "repo": "owner/repo", "pr_number": 42,
                "head_sha": "a" * 40, "assigned_reviewer": "reviewer-seat-a",
            }),
        )) + "\n",
        encoding="utf-8",
    )
    runner = _FakeGhRunner()
    spawned = []

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=ledger,
        spawner=lambda ctx, _: spawned.append(ctx) or _evidence(ctx), clock=_clock,
    )

    assert result.failed[0]["action"] == "ledger_unreadable"
    assert spawned == []
    assert runner.calls == []


def test_claim_state_folds_m2_provider_outcomes_before_adapter_writes_them():
    ctx = review_acting._context_from_item(_item())
    retryable = (
        "SPAWN_REFUSED",
        "SPAWN_FAILED",
        "TIMEOUT",
        "STALE_HEAD",
        "MALFORMED_RESULT",
        "PARTIAL_OUTPUT",
        "REVIEWER_EXIT_NONZERO",
    )
    for action in retryable:
        state = review_acting._claim_state([_claim(1), {**_claim(1), "action": action}], ctx)
        assert state.max_attempt == 1
        assert state.submission_started is False

    uncertain = review_acting._claim_state(
        [_claim(1), {**_claim(1), "action": "UNCERTAIN_COMMENT"}], ctx,
    )
    assert uncertain.max_attempt == 1
    assert uncertain.submission_started is True


def test_dedup_is_head_scoped_and_survives_restart(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    first = review_acting.run_acting_pass(
        items=[_item()], gh_runner=_FakeGhRunner(), acting_ledger_path=ledger,
        spawner=lambda ctx, runner: _evidence(ctx, "COMMENT"),
    )
    same_head_restart = review_acting.run_acting_pass(
        items=[_item()], gh_runner=_FakeGhRunner(), acting_ledger_path=ledger,
        spawner=lambda ctx, runner: _evidence(ctx, "must not run"),
    )
    later_head = "b" * 40
    later = review_acting.run_acting_pass(
        items=[_item(head_sha=later_head)], gh_runner=_FakeGhRunner(head_sha=later_head),
        acting_ledger_path=ledger, spawner=lambda ctx, runner: _evidence(ctx, "COMMENT"),
    )
    later_head_restart = review_acting.run_acting_pass(
        items=[_item(head_sha=later_head)], gh_runner=_FakeGhRunner(head_sha=later_head),
        acting_ledger_path=ledger, spawner=lambda ctx, runner: _evidence(ctx, "must not run"),
    )

    assert len(first.commented) == 1
    assert len(same_head_restart.skipped_dedup) == 1
    assert len(later.commented) == 1
    assert len(later_head_restart.skipped_dedup) == 1


def test_run_acting_pass_refuses_malformed_ledger_without_acting(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    ledger.write_text('{"action": "comment_posted"}\nnot-json\n', encoding="utf-8")
    runner = _FakeGhRunner()
    logs = []

    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=ledger,
        spawner=lambda ctx, _: _evidence(ctx), log_sink=logs.append, clock=_clock,
    )

    assert result.failed[0]["action"] == "ledger_unreadable"
    assert runner.calls == []
    assert logs[0]["event"] == "review_acting_ledger_unreadable"
    assert "not-json" not in logs[0]["error"]


def test_run_acting_pass_refuses_semantically_malformed_posted_evidence_without_acting(tmp_path):
    cases = (
        ("missing", {"action": "comment_posted", "repo": "owner/repo", "pr_number": 42}),
        ("empty", {"action": "comment_posted", "repo": "owner/repo", "pr_number": 42, "head_sha": ""}),
        ("invalid", {"action": "comment_posted", "repo": "owner/repo", "pr_number": 42, "head_sha": "not-a-sha"}),
    )
    for label, record in cases:
        ledger = tmp_path / f"{label}.ndjson"
        ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")
        runner = _FakeGhRunner()
        spawned = []
        logs = []

        result = review_acting.run_acting_pass(
            items=[_item()], gh_runner=runner, acting_ledger_path=ledger,
            spawner=lambda ctx, _: spawned.append(ctx) or _evidence(ctx),
            log_sink=logs.append, clock=_clock,
        )

        assert result.failed[0]["action"] == "ledger_unreadable"
        assert runner.calls == []
        assert spawned == []
        assert "not-a-sha" not in logs[0]["error"]


def test_load_acting_ledger_normalizes_uppercase_posted_head_sha(tmp_path):
    ledger = tmp_path / "ledger.ndjson"
    ledger.write_text(json.dumps({
        "action": "comment_posted", "repo": "owner/repo", "pr_number": 42,
        "head_sha": "A" * 40,
    }) + "\n", encoding="utf-8")

    assert review_acting.load_acting_ledger(ledger)[0]["head_sha"] == "a" * 40


def test_run_acting_pass_refuses_unreadable_ledger_without_acting(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.ndjson"
    ledger.write_text("{}\n", encoding="utf-8")
    original_read_text = review_acting.Path.read_text

    def deny_ledger_read(path, *args, **kwargs):
        if path == ledger:
            raise OSError("denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(review_acting.Path, "read_text", deny_ledger_read)
    runner = _FakeGhRunner()
    result = review_acting.run_acting_pass(
        items=[_item()], gh_runner=runner, acting_ledger_path=ledger,
        spawner=lambda ctx, _: _evidence(ctx), clock=_clock,
    )

    assert result.failed[0]["action"] == "ledger_unreadable"
    assert runner.calls == []


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
        url="https://example.test/pull/42?a=1&b=2", title="$(would-run-if-shell)", assigned_reviewer="reviewer-seat-a",
        author="author-seat-b",
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
        token="token", reviewer_seats=["reviewer-seat-a"], gh_runner=runner, repo="owner/repo",
        apply=True, iterations=1, on_pass_items=lambda items, runner: received.append((items, runner)),
    )

    assert result.passes[0].items == expected
    assert received == [(expected, runner)]
