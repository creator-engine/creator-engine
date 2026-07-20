"""Unit tests for the v3.5-D.0.1 live usage tap (transcript → spend-ledger; pure).

RED->GREEN against fixtures: a handful of transcript JSONL lines in the CONFIRMED
harness shape (one normal opus turn, one sidechain, one no-usage user line, one
malformed line); rates are injected; the only filesystem touch is exercised via a
tmp file. Cost is asserted to come from the shared ``spend_gate.compute_cost`` (NOT
reimplemented). ``usage_tap`` is imported directly (no ``__init__`` export — mirrors
``spend_gate``).
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from creator_engine_validator import runtime_evidence_spine as spine
from creator_engine_validator.runner import spend_gate as sg
from creator_engine_validator.runner import usage_tap as ut

# A live-policy-shaped rate table (read live from policy in production; injected here).
RATES = [
    {"model": "claude-opus-4-8", "input_per_mtok": 5.0, "output_per_mtok": 25.0},
]


def _assistant_line(*, session_id, model, ts, usage, sidechain=False):
    """Build one assistant JSONL line in the confirmed harness shape."""
    return json.dumps(
        {
            "type": "assistant",
            "sessionId": session_id,
            "timestamp": ts,
            "isSidechain": sidechain,
            "requestId": "req_x",
            "message": {"role": "assistant", "model": model, "usage": usage},
        }
    )


def _turn(ts, usage, *, session_id="sess", model="claude-opus-4-8"):
    return ut.UsageTurn(session_id=session_id, model=model, recorded_at=ts, usage=usage)


# A faithful opus usage blob — note the EXTRA keys the tap must ignore.
OPUS_USAGE = {
    "input_tokens": 2497,
    "output_tokens": 303,
    "cache_creation_input_tokens": 11468,
    "cache_read_input_tokens": 16272,
    "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
    "service_tier": "standard",
    "cache_creation": {"ephemeral_1h_input_tokens": 11468, "ephemeral_5m_input_tokens": 0},
    "iterations": [{"input_tokens": 2497, "output_tokens": 303, "type": "message"}],
}

NORMAL = _assistant_line(
    session_id="sess-1",
    model="claude-opus-4-8",
    ts="2026-06-08T07:34:22.526Z",
    usage=OPUS_USAGE,
)
SIDECHAIN = _assistant_line(
    session_id="sess-1",
    model="claude-opus-4-8",
    ts="2026-06-08T07:35:00.000Z",
    usage={"input_tokens": 10, "output_tokens": 5},
    sidechain=True,
)
USER_LINE = json.dumps(
    {
        "type": "user",
        "sessionId": "sess-1",
        "timestamp": "2026-06-08T07:33:00.000Z",
        "isSidechain": False,
        "message": {"role": "user", "content": "hi"},
    }
)
MALFORMED = "{not valid json,,,"

TRANSCRIPT_LINES = [USER_LINE, NORMAL, SIDECHAIN, MALFORMED]


# --- parse_transcript_usage: PURE extraction ---------------------------------
def test_parse_extracts_only_the_real_assistant_turn():
    turns = ut.parse_transcript_usage(TRANSCRIPT_LINES)
    assert len(turns) == 1
    turn = turns[0]
    assert turn.session_id == "sess-1"
    assert turn.model == "claude-opus-4-8"
    assert turn.recorded_at == "2026-06-08T07:34:22.526Z"
    # ONLY the 4 cost keys are retained; the extra usage keys are dropped.
    assert turn.usage == {
        "input_tokens": 2497,
        "output_tokens": 303,
        "cache_creation_input_tokens": 11468,
        "cache_read_input_tokens": 16272,
    }


def test_parse_skips_sidechain_user_malformed_and_blank():
    assert ut.parse_transcript_usage([SIDECHAIN]) == []
    assert ut.parse_transcript_usage([USER_LINE]) == []
    assert ut.parse_transcript_usage([MALFORMED]) == []
    assert ut.parse_transcript_usage(["", "   "]) == []


def test_parse_skips_assistant_without_model_or_without_usage():
    no_model = json.dumps(
        {
            "type": "assistant",
            "sessionId": "s",
            "timestamp": "t",
            "message": {"usage": {"input_tokens": 1, "output_tokens": 1}},
        }
    )
    no_usage = json.dumps(
        {
            "type": "assistant",
            "sessionId": "s",
            "timestamp": "t",
            "message": {"model": "claude-opus-4-8"},
        }
    )
    assert ut.parse_transcript_usage([no_model, no_usage]) == []


def test_parse_is_idempotent():
    assert ut.parse_transcript_usage(TRANSCRIPT_LINES) == ut.parse_transcript_usage(TRANSCRIPT_LINES)


def test_canonical_raw_tokens_excludes_cache_and_rejects_malformed_counts():
    assert ut.canonical_raw_tokens(OPUS_USAGE) == 2800
    assert ut.canonical_raw_tokens({"input_tokens": 0, "output_tokens": 7}) == 7
    for malformed in ({"input_tokens": -1, "output_tokens": 1}, {"input_tokens": "1", "output_tokens": 1}):
        with pytest.raises(ValueError):
            ut.canonical_raw_tokens(malformed)


# --- usage_turns_to_ledger: PURE projection, reusing spend_gate --------------
def test_usage_turns_to_ledger_reuses_compute_cost_and_builds_bodies():
    turns = ut.parse_transcript_usage(TRANSCRIPT_LINES)
    bodies, unpriced = ut.usage_turns_to_ledger(
        turns, model_rates=RATES, fleet_id="fleet-x", policy_sha="p" * 64
    )
    assert unpriced == []
    assert len(bodies) == 1
    body = bodies[0]
    # Cost is the SHARED spend_gate.compute_cost — proves no reimplementation drift.
    expected = sg.compute_cost(turns[0].usage, "claude-opus-4-8", RATES)
    assert body["amount"] == float(expected)
    assert body["run_id"] == "sess-1"  # defaults to session_id
    assert body["fleet_id"] == "fleet-x"
    assert body["model"] == "claude-opus-4-8"
    assert body["unit"] == "$"
    assert body["policy_sha"] == "p" * 64
    assert body["recorded_at"] == "2026-06-08T07:34:22.526Z"
    assert body["record_type"] == spine.RUNTIME_SPEND_LEDGER_RECORD_TYPE
    assert body["kind"] == spine.RUNTIME_SPEND_LEDGER_RECORD_KIND


def test_unpriced_model_lands_in_unpriced_not_silent_zero():
    turn = ut.UsageTurn(
        session_id="s",
        model="some-unpriced-model",
        recorded_at="t",
        usage={"input_tokens": 1_000_000, "output_tokens": 1_000_000},
    )
    bodies, unpriced = ut.usage_turns_to_ledger([turn], model_rates=RATES, fleet_id="f")
    assert bodies == []
    assert unpriced == [turn]


def test_run_id_of_override():
    turns = ut.parse_transcript_usage([NORMAL])
    bodies, _ = ut.usage_turns_to_ledger(
        turns, model_rates=RATES, fleet_id="f", run_id_of=lambda t: "run-42"
    )
    assert bodies[0]["run_id"] == "run-42"


# --- tap_transcript_file: the ONLY I/O edge ----------------------------------
def test_tap_transcript_file_reads_and_parses(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(TRANSCRIPT_LINES) + "\n", encoding="utf-8")
    turns = ut.tap_transcript_file(path)
    assert len(turns) == 1
    assert turns[0].model == "claude-opus-4-8"
    assert turns[0].usage["input_tokens"] == 2497


# --- fleet_token_rate: pure fleet tokens/hr projection -----------------------
def test_fleet_token_rate_sums_tokens_and_rates_by_span():
    turns = [
        _turn(
            "2026-06-08T00:00:00Z",
            {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 20,
            },
        ),
        _turn("2026-06-08T02:00:00Z", {"input_tokens": 200, "output_tokens": 50}),
    ]
    meter = ut.fleet_token_rate(turns)
    assert meter.input_tokens == 300
    assert meter.output_tokens == 100
    assert meter.cache_creation_input_tokens == 10
    assert meter.cache_read_input_tokens == 20
    assert meter.total_tokens == 430
    assert meter.turn_count == 2
    assert meter.span_hours == Decimal("2")
    assert meter.tokens_per_hour == Decimal("215")


def test_fleet_token_rate_single_turn_has_no_rate():
    meter = ut.fleet_token_rate([_turn("2026-06-08T00:00:00Z", {"input_tokens": 10, "output_tokens": 5})])
    assert meter.input_tokens == 10
    assert meter.output_tokens == 5
    assert meter.total_tokens == 15
    assert meter.turn_count == 1
    assert meter.span_hours is None
    assert meter.tokens_per_hour is None


def test_fleet_token_rate_wall_clock_filter_uses_same_filtered_turns_for_rate():
    turns = [
        _turn("2026-06-08T00:00:00Z", {"input_tokens": 10, "output_tokens": 0}),
        _turn("2026-06-08T01:00:00Z", {"input_tokens": 100, "output_tokens": 20}),
        _turn("2026-06-08T03:00:00Z", {"input_tokens": 200, "output_tokens": 20}),
    ]
    meter = ut.fleet_token_rate(
        turns,
        since="2026-06-08T00:30:00Z",
        until="2026-06-08T02:30:00Z",
    )
    assert meter.input_tokens == 100
    assert meter.output_tokens == 20
    assert meter.total_tokens == 120
    assert meter.turn_count == 1
    assert meter.span_hours == Decimal("2")
    assert meter.tokens_per_hour == Decimal("60")


def test_fleet_token_rate_empty_turns_zero_none():
    meter = ut.fleet_token_rate([])
    assert meter.input_tokens == 0
    assert meter.output_tokens == 0
    assert meter.total_tokens == 0
    assert meter.turn_count == 0
    assert meter.span_hours is None
    assert meter.tokens_per_hour is None


def test_fleet_token_rate_uses_spend_gate_timestamp_helpers():
    assert ut._parse_ts is sg._parse_ts
    assert ut._span_hours is sg._span_hours


def test_fleet_token_rate_is_deterministic():
    turns = [
        _turn("2026-06-08T00:00:00Z", {"input_tokens": 10, "output_tokens": 5}),
        _turn("2026-06-08T01:00:00Z", {"input_tokens": 20, "output_tokens": 5}),
    ]
    assert ut.fleet_token_rate(turns) == ut.fleet_token_rate(turns)
