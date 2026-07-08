from __future__ import annotations

from datetime import datetime

import pytest

from creator_engine_validator.brain_intent_materializer import CloseoutWindowPolicy


def _record(held_at_utc: str = "2026-07-08T12:00:00Z") -> dict:
    return {
        "held_reason": "brain_ledger_tail_unprovable",
        "materialization_key": "a" * 64,
        "held_at_utc": held_at_utc,
    }


def test_held_record_inside_window_is_advisory():
    status = CloseoutWindowPolicy.evaluate(_record(), now_fn=lambda: datetime(2026, 7, 8, 12, 10, 0))

    assert status.is_advisory is True
    assert status.is_hard_failure is False
    assert status.held_reason == "brain_ledger_tail_unprovable"
    assert status.materialization_key == "a" * 64


def test_held_record_past_window_is_hard_failure():
    status = CloseoutWindowPolicy.evaluate(_record(), now_fn=lambda: datetime(2026, 7, 8, 12, 31, 0))

    assert status.is_advisory is False
    assert status.is_hard_failure is True


def test_exactly_30_minutes_is_hard_failure_boundary():
    status = CloseoutWindowPolicy.evaluate(_record(), now_fn=lambda: datetime(2026, 7, 8, 12, 30, 0))

    assert status.is_advisory is False
    assert status.is_hard_failure is True


def test_injectable_clock_is_used():
    called = {"value": False}

    def now():
        called["value"] = True
        return datetime(2026, 7, 8, 12, 10, 0)

    CloseoutWindowPolicy.evaluate(_record(), now_fn=now)

    assert called["value"] is True


def test_deadline_is_30_minutes_after_held_at_with_z_suffix():
    status = CloseoutWindowPolicy.evaluate(_record("2026-07-08T12:05:00Z"), now_fn=lambda: datetime(2026, 7, 8, 12, 10, 0))

    assert status.deadline_utc == "2026-07-08T12:35:00Z"


def test_malformed_held_at_utc_raises():
    with pytest.raises(ValueError):
        CloseoutWindowPolicy.evaluate(_record("not-a-date"), now_fn=lambda: datetime(2026, 7, 8, 12, 10, 0))
