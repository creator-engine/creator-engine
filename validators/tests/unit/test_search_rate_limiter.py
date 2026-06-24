from __future__ import annotations

from creator_engine_validator.search_rate_limiter import (
    SearchRateLimiter,
    call_with_search_api_headroom,
)


def test_file_backed_limiter_reserves_slots_across_instances(tmp_path):
    now = 1000.0
    state = tmp_path / "search-rate.json"
    first = SearchRateLimiter(
        state,
        rate_per_minute=60,
        burst=1,
        jitter_seconds=0,
        clock=lambda: now,
    )
    second = SearchRateLimiter(
        state,
        rate_per_minute=60,
        burst=1,
        jitter_seconds=0,
        clock=lambda: now,
    )

    assert first.reserve_delay() == 0
    assert second.reserve_delay() == 1


def test_retry_wrapper_backs_off_and_retries_rate_limit(tmp_path):
    class Limited(Exception):
        retry_after_seconds = 7

    now = 100.0

    def clock():
        return now

    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    limiter = SearchRateLimiter(
        tmp_path / "search-rate.json",
        rate_per_minute=6000,
        burst=1,
        jitter_seconds=0,
        clock=clock,
        random_float=lambda: 0.0,
    )
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise Limited()
        return "ok"

    assert call_with_search_api_headroom(
        operation,
        limiter=limiter,
        is_rate_limited=lambda exc: isinstance(exc, Limited),
        retry_after_seconds=lambda exc: getattr(exc, "retry_after_seconds", None),
        sleep=sleep,
    ) == "ok"
    assert attempts["count"] == 2
    assert sleeps == [7.0]
