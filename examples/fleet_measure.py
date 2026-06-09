#!/usr/bin/env python3
"""Measure CE dogfood fleet transcripts with the merged D.0 usage/spend meters.

This is intentionally a thin driver around:

* ``usage_tap.tap_transcript_file`` / ``usage_tap.fleet_token_rate``
* ``usage_tap.usage_turns_to_ledger``
* ``spend_gate.fleet_spend_meter``

It does not write the runtime spine and does not define a new baselined runner
module. The default corpus is the local Claude harness transcript directory used
by the v3/v3.5 dogfood fleet; pass ``--glob`` one or more times to measure a
different compatible corpus.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATORS_ROOT = REPO_ROOT / "validators"
if str(VALIDATORS_ROOT) not in sys.path:
    sys.path.insert(0, str(VALIDATORS_ROOT))

from creator_engine_validator.runner import spend_gate as sg
from creator_engine_validator.runner import usage_tap as ut

DEFAULT_TRANSCRIPT_GLOB = (
    "~/.claude/projects/-home-nefarious-projects-creator-engine-canonical/*.jsonl"
)
DEFAULT_FLEET_ID = "ce-v35-dogfood-fleet"
RATE_SOURCE = (
    "Anthropic Claude API pricing, fetched 2026-06-09: "
    "https://platform.claude.com/docs/en/about-claude/pricing"
)
RATE_NOTE = (
    "The D.0.2 meter has one cache_creation_input_tokens bucket. The default "
    "policy maps claude-opus-4-7/4-8 cache creation to the 1h cache-write rate "
    "because the measured Claude Code corpus is overwhelmingly 1h cache writes; "
    "pass --rates-json to override."
)
DEFAULT_MODEL_RATES = [
    {
        "model": "claude-opus-4-7",
        "input_per_mtok": 5.0,
        "output_per_mtok": 25.0,
        "cache_read_per_mtok": 0.5,
        "cache_write_per_mtok": 10.0,
    },
    {
        "model": "claude-opus-4-8",
        "input_per_mtok": 5.0,
        "output_per_mtok": 25.0,
        "cache_read_per_mtok": 0.5,
        "cache_write_per_mtok": 10.0,
    },
]


def _decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _decimal(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _policy_sha(model_rates: Any) -> str:
    body = json.dumps(model_rates, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_model_rates(path: str | Path | None) -> list[dict[str, Any]]:
    """Load a rate table from JSON or return the documented default table."""
    if path is None:
        return [dict(row) for row in DEFAULT_MODEL_RATES]
    with open(Path(path).expanduser(), encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        payload = payload.get("model_rates")
    if not isinstance(payload, list):
        raise ValueError("rates JSON must be a list or an object with model_rates")
    return payload


def expand_inputs(patterns: Sequence[str]) -> list[Path]:
    """Expand one or more transcript globs into a stable path list."""
    paths: list[Path] = []
    for pattern in patterns:
        expanded_pattern = str(Path(pattern).expanduser())
        matches = glob.glob(expanded_pattern)
        if matches:
            paths.extend(Path(match) for match in matches)
        else:
            literal = Path(expanded_pattern)
            if literal.exists():
                paths.append(literal)
    return sorted(set(paths))


def _selected(turns: Iterable[ut.UsageTurn], *, since: str | None, until: str | None) -> list[ut.UsageTurn]:
    out: list[ut.UsageTurn] = []
    for turn in turns:
        if ut.fleet_token_rate([turn], since=since, until=until).turn_count == 1:
            out.append(turn)
    return out


def _timestamp_range(turns: Iterable[ut.UsageTurn]) -> tuple[str | None, str | None]:
    pairs: list[tuple[datetime, str]] = []
    for turn in turns:
        parsed = sg._parse_ts(turn.recorded_at)
        if parsed is not None:
            pairs.append((parsed, turn.recorded_at))
    if not pairs:
        return None, None
    ordered = sorted(pairs, key=lambda item: item[0])
    return ordered[0][1], ordered[-1][1]


def _max_concurrent_runs(
    grouped_turns: dict[str, list[ut.UsageTurn]],
    *,
    since: str | None,
    until: str | None,
) -> int:
    """Return max overlap of run spans in the selected wall-clock window."""
    intervals: list[tuple[datetime, datetime]] = []
    for turns in grouped_turns.values():
        selected = _selected(turns, since=since, until=until)
        points = [sg._parse_ts(turn.recorded_at) for turn in selected]
        parsed = [point for point in points if point is not None]
        if parsed:
            intervals.append((min(parsed), max(parsed)))
    if not intervals:
        return 0
    instants = sorted({point for interval in intervals for point in interval})
    return max(
        sum(1 for start, end in intervals if start <= instant <= end)
        for instant in instants
    )


def _tokens_dict(meter: ut.FleetUsage) -> dict[str, Any]:
    return {
        "input_tokens": meter.input_tokens,
        "output_tokens": meter.output_tokens,
        "cache_creation_input_tokens": meter.cache_creation_input_tokens,
        "cache_read_input_tokens": meter.cache_read_input_tokens,
        "total_tokens": meter.total_tokens,
        "turns": meter.turn_count,
        "span_hours": _decimal(meter.span_hours),
        "tokens_per_hour": _decimal(meter.tokens_per_hour),
    }


def measure_transcripts(
    transcript_paths: Sequence[str | Path],
    *,
    model_rates: Any,
    fleet_id: str = DEFAULT_FLEET_ID,
    since: str | None = None,
    until: str | None = None,
    policy_sha: str | None = None,
) -> dict[str, Any]:
    """Measure a compatible transcript corpus and return JSON-serializable metrics."""
    paths = [Path(path).expanduser() for path in transcript_paths]
    policy = policy_sha or _policy_sha(model_rates)

    all_turns: list[ut.UsageTurn] = []
    path_turn_counts: dict[str, int] = {}
    for path in paths:
        turns = ut.tap_transcript_file(path)
        path_turn_counts[str(path)] = len(turns)
        all_turns.extend(turns)

    grouped_turns: dict[str, list[ut.UsageTurn]] = defaultdict(list)
    for turn in all_turns:
        grouped_turns[turn.session_id or "<missing-session>"].append(turn)

    ledger_bodies, unpriced_turns = ut.usage_turns_to_ledger(
        all_turns,
        model_rates=model_rates,
        fleet_id=fleet_id,
        policy_sha=policy,
        run_id_of=lambda turn: turn.session_id or "<missing-session>",
    )

    selected_turns = _selected(all_turns, since=since, until=until)
    selected_unpriced = _selected(unpriced_turns, since=since, until=until)
    fleet_tokens = ut.fleet_token_rate(all_turns, since=since, until=until)
    fleet_spend = sg.fleet_spend_meter(
        ledger_bodies,
        fleet_id=fleet_id,
        since=since,
        until=until,
    )
    selected_run_ids = {
        turn.session_id or "<missing-session>"
        for turn in selected_turns
    }

    per_run: list[dict[str, Any]] = []
    for run_id in sorted(selected_run_ids):
        run_turns = grouped_turns[run_id]
        selected_run_turns = _selected(run_turns, since=since, until=until)
        token_meter = ut.fleet_token_rate(run_turns, since=since, until=until)
        run_bodies = [body for body in ledger_bodies if body.get("run_id") == run_id]
        spend_meter = sg.fleet_spend_meter(
            run_bodies,
            fleet_id=fleet_id,
            since=since,
            until=until,
        )
        start, end = _timestamp_range(selected_run_turns)
        models = Counter(turn.model for turn in selected_run_turns)
        per_run.append(
            {
                "run_id": run_id,
                "fleet_id": fleet_id,
                "start": start,
                "end": end,
                "models": dict(sorted(models.items())),
                **_tokens_dict(token_meter),
                "cost_usd": _decimal(spend_meter.spend),
                "cost_per_hour_usd": _decimal(spend_meter.spend_per_hour),
                "ledger_record_count": spend_meter.record_count,
                "outcome": "not_derived_from_transcript",
                "graded_by": "not_derived_from_transcript",
            }
        )

    unpriced_by_model = Counter(turn.model for turn in selected_unpriced)
    unpriced_tokens = ut.fleet_token_rate(selected_unpriced, since=since, until=until)
    start, end = _timestamp_range(selected_turns)
    aggregate = {
        "fleet_id": fleet_id,
        "start": start,
        "end": end,
        "concurrent_n": _max_concurrent_runs(grouped_turns, since=since, until=until),
        "runs": len(selected_run_ids),
        "priced_runs": fleet_spend.run_count,
        **_tokens_dict(fleet_tokens),
        "total_cost_usd": _decimal(fleet_spend.spend),
        "cost_per_hour_usd": _decimal(fleet_spend.spend_per_hour),
        "ledger_record_count": fleet_spend.record_count,
        "prs_merged": None,
        "prs_merged_derivation": "not_derived_from_harness_transcripts",
        "auto_graded_percent": None,
        "auto_graded_derivation": "not_derived_from_harness_transcripts",
    }

    return {
        "methodology": {
            "driver": "examples/fleet_measure.py",
            "transcript_files": len(paths),
            "path_turn_counts": path_turn_counts,
            "since": since,
            "until": until,
            "fleet_id": fleet_id,
            "policy_sha": policy,
            "rate_source": RATE_SOURCE,
            "rate_note": RATE_NOTE,
            "codex_usage_note": (
                "Local Codex history/index JSONLs are not included unless passed "
                "explicitly and compatible with usage_tap's assistant usage shape."
            ),
        },
        "model_rates": model_rates,
        "fleet_aggregate": aggregate,
        "per_run": sorted(per_run, key=lambda row: (row.get("start") or "", row["run_id"])),
        "unpriced": {
            "turns": len(selected_unpriced),
            "models": dict(sorted(unpriced_by_model.items())),
            **_tokens_dict(unpriced_tokens),
        },
    }


def _print_summary(result: dict[str, Any]) -> None:
    aggregate = result["fleet_aggregate"]
    unpriced = result["unpriced"]
    print("CE fleet measurement")
    print(f"  files: {result['methodology']['transcript_files']}")
    print(f"  fleet_id: {aggregate['fleet_id']}")
    print(f"  window: {aggregate['start']} -> {aggregate['end']}")
    print(
        "  runs/turns/concurrent_n: "
        f"{aggregate['runs']}/{aggregate['turns']}/{aggregate['concurrent_n']}"
    )
    print(
        "  tokens/hr: "
        f"{aggregate['total_tokens']} tokens / {aggregate['tokens_per_hour'] or 'n/a'}"
    )
    print(
        "  cost/hr: "
        f"${aggregate['total_cost_usd']} / ${aggregate['cost_per_hour_usd'] or 'n/a'}"
    )
    if unpriced["turns"]:
        print(f"  unpriced turns: {unpriced['turns']} {unpriced['models']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--glob",
        action="append",
        dest="globs",
        help=(
            "Transcript glob or literal path. Repeatable. Defaults to the canonical "
            "Claude Code CE corpus."
        ),
    )
    parser.add_argument("--rates-json", help="JSON list or object with model_rates.")
    parser.add_argument("--fleet-id", default=DEFAULT_FLEET_ID)
    parser.add_argument("--since", help="Inclusive ISO-8601 wall-clock lower bound.")
    parser.add_argument("--until", help="Inclusive ISO-8601 wall-clock upper bound.")
    parser.add_argument("--json-out", help="Optional path to write full JSON metrics.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    patterns = args.globs or [DEFAULT_TRANSCRIPT_GLOB]
    paths = expand_inputs(patterns)
    if not paths:
        print("No transcript files matched.", file=sys.stderr)
        return 2

    rates = load_model_rates(args.rates_json)
    result = measure_transcripts(
        paths,
        model_rates=rates,
        fleet_id=args.fleet_id,
        since=args.since,
        until=args.until,
    )
    _print_summary(result)
    if args.json_out:
        out = Path(args.json_out).expanduser()
        out.write_text(
            json.dumps(result, indent=2, sort_keys=True, default=_json_default) + "\n",
            encoding="utf-8",
        )
        print(f"  json: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
