from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from creator_engine_validator.forge import ratifier_queue_runtime as runtime


SHA_A = "a" * 40
SHA_B = "b" * 40
NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def _candidate(pr: int, sha: str, enqueued_at: str, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "pr_number": pr,
        "head_sha": sha,
        "branch": f"ce-{pr}",
        "enqueued_at": enqueued_at,
        "attestation_state": "pending",
        "last_checked_at": None,
        "checked_count": 0,
        "facts": {
            "ready_sha": sha,
            "validation_sha": sha,
            "validator_live": False,
            "exit_code": 0,
            "structural_failures": 0,
            "environment_failures": 0,
        },
    }
    value.update(overrides)
    return value


def _write_candidates(path: Path, candidates: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"version": 1, "candidates": candidates}), encoding="utf-8")


def test_runtime_orders_persists_and_replays_without_losing_dedup(tmp_path: Path):
    candidates = tmp_path / "candidates.json"
    state = tmp_path / "state" / "queue.json"
    _write_candidates(candidates, [
        _candidate(2, SHA_B, "2026-07-12T10:00:00Z"),
        _candidate(1, SHA_A, "2026-07-12T09:00:00Z"),
    ])

    first = runtime.run_once(candidates, state, clock=lambda: NOW)
    second = runtime.run_once(candidates, state, clock=lambda: NOW)

    assert [entry.candidate.pr_number for entry in first.entries] == [1, 2]
    assert [entry.status for entry in first.entries] == ["ATTESTED", "ATTESTED"]
    assert [entry.candidate.checked_count for entry in second.entries] == [2, 2]
    assert all(entry.candidate.last_checked_at == "2026-07-12T12:00:00Z" for entry in second.entries)
    assert stat.S_IMODE(state.stat().st_mode) == 0o600
    assert runtime.summary(second)["entries"][0]["dedup_identity"] == f"ratifier-queue:1:{SHA_A}"


def test_head_mismatch_is_stale_and_bad_evidence_is_blocked(tmp_path: Path):
    candidates = tmp_path / "candidates.json"
    stale = _candidate(1, SHA_A, "2026-07-12T09:00:00Z")
    stale["facts"] = {**stale["facts"], "validation_sha": SHA_B}  # type: ignore[index]
    blocked = _candidate(2, SHA_B, "2026-07-12T10:00:00Z")
    blocked["facts"] = {**blocked["facts"], "exit_code": 1}  # type: ignore[index]
    _write_candidates(candidates, [stale, blocked])

    result = runtime.run_once(candidates, tmp_path / "state.json", clock=lambda: NOW)

    assert [(entry.status, entry.reason) for entry in result.entries] == [
        ("STALE", "validation_sha_differs_from_ready_sha"),
        ("BLOCKED", "attestation_failed"),
    ]


def test_runtime_refuses_malformed_input_concurrent_writer_and_unsafe_state(tmp_path: Path):
    candidates = tmp_path / "candidates.json"
    state = tmp_path / "state.json"
    candidates.write_text('{"version": 2, "candidates": []}', encoding="utf-8")
    with pytest.raises(runtime.RatifierQueueRuntimeError, match="unsupported"):
        runtime.run_once(candidates, state, clock=lambda: NOW)

    _write_candidates(candidates, [_candidate(1, SHA_A, "2026-07-12T09:00:00Z")])
    runtime.run_once(candidates, state, clock=lambda: NOW)
    os.chmod(state, 0o644)
    with pytest.raises(runtime.RatifierQueueRuntimeError, match="owner-only"):
        runtime.run_once(candidates, state, clock=lambda: NOW)
