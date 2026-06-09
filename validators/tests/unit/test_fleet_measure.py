"""Tests for the D.0.3 fleet measurement driver."""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

from creator_engine_validator.runner import spend_gate as sg
from creator_engine_validator.runner import usage_tap as ut

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "examples" / "fleet_measure.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fleet_measure_sample.jsonl"

spec = importlib.util.spec_from_file_location("fleet_measure", MODULE_PATH)
fleet_measure = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet_measure
assert spec.loader is not None
spec.loader.exec_module(fleet_measure)

RATES = [
    {
        "model": "claude-opus-4-8",
        "input_per_mtok": 10.0,
        "output_per_mtok": 20.0,
        "cache_read_per_mtok": 1.0,
        "cache_write_per_mtok": 2.0,
    },
    {
        "model": "claude-opus-4-7",
        "input_per_mtok": 1.0,
        "output_per_mtok": 2.0,
        "cache_read_per_mtok": 0.1,
        "cache_write_per_mtok": 0.2,
    },
]


def _expected_cost(turns):
    return sum((sg.compute_cost(turn.usage, turn.model, RATES) for turn in turns), Decimal("0"))


def test_measure_transcripts_aggregates_tokens_spend_and_fleet_id():
    result = fleet_measure.measure_transcripts(
        [FIXTURE],
        model_rates=RATES,
        fleet_id="fleet-test",
        policy_sha="p" * 64,
    )

    aggregate = result["fleet_aggregate"]
    turns = ut.tap_transcript_file(FIXTURE)
    expected_cost = _expected_cost(turns)

    assert aggregate["fleet_id"] == "fleet-test"
    assert aggregate["runs"] == 2
    assert aggregate["priced_runs"] == 2
    assert aggregate["concurrent_n"] == 2
    assert aggregate["turns"] == 3
    assert aggregate["total_tokens"] == 1050
    assert aggregate["span_hours"] == "2"
    assert aggregate["tokens_per_hour"] == "525"
    assert aggregate["total_cost_usd"] == format(expected_cost, "f")
    assert aggregate["cost_per_hour_usd"] == format(expected_cost / Decimal("2"), "f")
    assert aggregate["ledger_record_count"] == 3
    assert result["unpriced"]["turns"] == 0

    per_run = {row["run_id"]: row for row in result["per_run"]}
    assert set(per_run) == {"session-a", "session-b"}
    assert per_run["session-a"]["fleet_id"] == "fleet-test"
    assert per_run["session-a"]["total_tokens"] == 700
    assert per_run["session-a"]["ledger_record_count"] == 2
    assert per_run["session-b"]["total_tokens"] == 350
    assert per_run["session-b"]["ledger_record_count"] == 1


def test_measure_transcripts_applies_wall_clock_window_to_tokens_and_spend():
    result = fleet_measure.measure_transcripts(
        [FIXTURE],
        model_rates=RATES,
        fleet_id="fleet-window",
        since="2026-06-08T00:30:00Z",
        until="2026-06-08T01:30:00Z",
    )

    aggregate = result["fleet_aggregate"]
    selected_turn = ut.tap_transcript_file(FIXTURE)[1]
    expected_cost = sg.compute_cost(selected_turn.usage, selected_turn.model, RATES)

    assert aggregate["fleet_id"] == "fleet-window"
    assert aggregate["runs"] == 1
    assert aggregate["priced_runs"] == 1
    assert aggregate["concurrent_n"] == 1
    assert aggregate["turns"] == 1
    assert aggregate["total_tokens"] == 350
    assert aggregate["span_hours"] == "1"
    assert aggregate["tokens_per_hour"] == "350"
    assert aggregate["total_cost_usd"] == format(expected_cost, "f")
    assert aggregate["cost_per_hour_usd"] == format(expected_cost, "f")
    assert [row["run_id"] for row in result["per_run"]] == ["session-b"]
