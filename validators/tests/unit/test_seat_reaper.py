"""ce-ops#43 — unit tests for the seat/venue retirement reaper POLICY (seat_reaper).

Fixtures use the REAL event schema + dispatch shape and a FAKE executor for every
irreversible substrate action, so CI never touches a live tmux/git/claude process.
The fake records its call log, which proves the archive-before-remove ORDERING the
policy enforces. The numbered ``test_<n>_<slug>`` functions are the §10 ratification
tests that live at the policy layer (the pco-release integration is test #8 in
``test_pco_allocator_cli.py``; the v3-boundary proof is test #14 in
``test_version_boundary.py``).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import reaper_executors, seat_reaper, seat_sentinel
from creator_engine_validator.seat_reaper import (
    STEP_FAILED,
    STEP_SUCCEEDED,
    RetirementPlan,
    StepResult,
)

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Fakes + fixtures
# ---------------------------------------------------------------------------


class FakeExecutor:
    """Records every irreversible call; writes a REAL archive file so the policy's
    archive verification (hash re-check) exercises real bytes."""

    substrate = "tmux"

    def __init__(
        self,
        archive_dir: Path,
        *,
        archive_status: str = STEP_SUCCEEDED,
        close_status: str = STEP_SUCCEEDED,
        release_status: str = STEP_SUCCEEDED,
        release_data: dict | None = None,
    ):
        self.calls: list[tuple] = []
        self._archive_dir = archive_dir
        self._archive_status = archive_status
        self._close_status = close_status
        self._release_status = release_status
        self._release_data = release_data or {}

    def archive_transcript(self, plan: RetirementPlan) -> StepResult:
        self.calls.append(("archive", plan.seat_id))
        if self._archive_status != STEP_SUCCEEDED:
            return StepResult(self._archive_status, "fake archive refusal")
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        p = self._archive_dir / f"{plan.seat_id}.txt"
        p.write_text("transcript bytes\n", encoding="utf-8")
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        return StepResult(STEP_SUCCEEDED, "archived", {"archive_path": str(p), "sha256": sha})

    def close_venue(self, plan: RetirementPlan) -> StepResult:
        self.calls.append(("close", plan.seat_id))
        return StepResult(self._close_status, "fake close")

    def release_worktree(self, plan: RetirementPlan) -> StepResult:
        self.calls.append(("release", plan.seat_id, plan.release_reason))
        return StepResult(self._release_status, "fake release", dict(self._release_data))

    @property
    def steps(self) -> list[str]:
        return [c[0] for c in self.calls]


def _dispatch(run_id: str, *, scope_id: str = "demo-scope", **extra) -> dict:
    rec = {
        "kind": "dispatch-record",
        "record_type": "dispatch",
        "schema_version": "1",
        "scope_id": scope_id,
        "run_id": run_id,
        "mutation_class": "code",
        "harness": "claude",
        "unattended": True,
        "session": "ce",
        "window": "drive",
        "terminal": {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"},
        "spawned_at": "20260613T115500Z",
    }
    rec.update(extra)
    return rec


def _launched(run_id: str, *, pid: int = 4242, ts: datetime = NOW) -> dict:
    return {
        "v": 1,
        "event": "launched",
        "ts": _ts(ts),
        "seat_id": run_id,
        "run_id": run_id,
        "writer": "launcher_wrapper",
        "pid": pid,
        "command_sha256": "ab" * 32,
    }


def _exited(run_id: str, *, ts: datetime = NOW, code: int = 0) -> dict:
    return {
        "v": 1,
        "event": "exited",
        "ts": _ts(ts),
        "seat_id": run_id,
        "run_id": run_id,
        "writer": "launcher_wrapper",
        "exit_code": code,
    }


def _write_seat(root: Path, seat_id: str, *, dispatch: dict | None = None, events=()) -> Path:
    d = root / "dispatches" / seat_id
    d.mkdir(parents=True, exist_ok=True)
    if dispatch is not None:
        (d / "dispatch.yaml").write_text(yaml.safe_dump(dispatch, sort_keys=True), encoding="utf-8")
    if events:
        (d / "events.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
        )
    return d


def _write_pane_record(ledger_root: Path, *, controller_id: str, lane_id: str, worktree: Path) -> Path:
    rec = {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "claim_ref": f"claims/{controller_id}/{lane_id}.yaml",
        "host_id": "ce-dev-1",
        "pane_id": "venue-pane",
        "role": "reviewer",
        "status": "active",
        "record_timestamp": "2026-06-13T11:55:00Z",
        "registered_at": "2026-06-13T11:55:00Z",
        "last_seen_at": "2026-06-13T11:55:00Z",
        "visibility": "operator_visible",
        "terminal": {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"},
        "worktree_path": str(worktree),
    }
    p = ledger_root / "panes" / controller_id / f"{lane_id}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(rec, sort_keys=True), encoding="utf-8")
    return p


def _clean_seat(root: Path, ledger_root: Path, *, run_id: str = "run-demo-scope-20260613T115000Z"):
    """A launched+exited (recent) seat with a pco worktree binding."""
    _write_seat(root, run_id, dispatch=_dispatch(run_id), events=[_launched(run_id), _exited(run_id)])
    _write_pane_record(
        ledger_root, controller_id="ctrl-x", lane_id=run_id, worktree=root / "wt" / run_id
    )
    return run_id


def _reap(root, **kw):
    kw.setdefault("now", NOW)
    kw.setdefault("pid_alive", lambda _pid: False)
    return seat_reaper.reap_once(root, **kw)


# ---------------------------------------------------------------------------
# §10.1 clean-terminal-reaps
# ---------------------------------------------------------------------------


def test_1_clean_terminal_reaps(tmp_path):
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    run_id = _clean_seat(root, ledger)
    fake = FakeExecutor(tmp_path / "arch")

    out = _reap(
        root,
        ledger_root=ledger,
        repo_root=tmp_path,
        executor_for=lambda _k: fake,
    )
    # reaps BEFORE cev3 collect ran (no runtime-evidence chain exists)
    assert not (root / "runs").exists()
    assert out["reaped"] == 1
    assert out["eligible"] == 1
    assert out["failed"] == 0
    assert fake.steps == ["archive", "close", "release"]
    # release used the clean-terminal reason
    assert ("release", run_id, "completed") in fake.calls
    # a reaper ledger entry was written
    ledger_entries = seat_reaper.load_reaper_ledger(root)
    assert len(ledger_entries) == 1 and ledger_entries[0]["seat_id"] == run_id


# ---------------------------------------------------------------------------
# §10.2 never-reaps-conserved
# ---------------------------------------------------------------------------


def test_2_never_reaps_conserved(tmp_path):
    root = tmp_path / "state"
    run_id = "run-conserved-20260613T110000Z"
    _write_seat(
        root,
        run_id,
        dispatch=_dispatch(run_id, conserve=True, conserve_reason="refused — evidence",
                           conserved_at="2026-06-13T11:00:00Z"),
        events=[_launched(run_id), _exited(run_id)],
    )
    fake = FakeExecutor(tmp_path / "arch")
    out = _reap(root, ledger_root=tmp_path / "ledger", repo_root=tmp_path, executor_for=lambda _k: fake)
    assert out["conserved"] == 1
    assert out["reaped"] == 0
    # the fake executor observed NO teardown of any kind
    assert fake.calls == []
    # dispatch + events preserved
    assert (root / "dispatches" / run_id / "dispatch.yaml").is_file()
    assert (root / "dispatches" / run_id / "events.jsonl").is_file()


# ---------------------------------------------------------------------------
# §10.3 unclean-stop-escalates
# ---------------------------------------------------------------------------


def test_3_unclean_stop_escalates(tmp_path):
    root = tmp_path / "state"
    run_id = "run-unclean-20260613T110000Z"
    # launched, NO exited, dead pid
    _write_seat(root, run_id, dispatch=_dispatch(run_id), events=[_launched(run_id, pid=999999)])
    fake = FakeExecutor(tmp_path / "arch")
    out = _reap(
        root, ledger_root=tmp_path / "ledger", repo_root=tmp_path,
        executor_for=lambda _k: fake, pid_alive=lambda _pid: False,
    )
    assert out["escalated"] == 1
    assert out["reaped"] == 0
    assert fake.calls == []  # no teardown
    esc = list((root / "escalations").glob("*.yaml"))
    assert len(esc) == 1
    rec = yaml.safe_load(esc[0].read_text())
    assert rec["escalation_id"].startswith("reaper-unclean-stop-")
    assert rec["kind"] == "escalation-record"


# ---------------------------------------------------------------------------
# §10.4 evidence-chain-folds-when-present
# ---------------------------------------------------------------------------


def test_4_evidence_chain_folds_when_present(tmp_path):
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    run_id = _clean_seat(root, ledger)
    # write a runtime-evidence chain whose last in-enum outcome is pr_merged
    runs = root / "runs"
    runs.mkdir(parents=True)
    (runs / f"{run_id}.runtime-evidence.yaml").write_text(
        yaml.safe_dump({"records": [{"outcome": "pr_opened"}, {"outcome": "pr_merged"}]}),
        encoding="utf-8",
    )
    # the read-only resolver folds the chain WITHOUT mutating events
    events = [_launched(run_id), _exited(run_id)]
    outcome, source = seat_reaper.resolve_outcome_readonly(events, root, run_id=run_id)
    assert outcome == "pr_merged"
    assert source == "runtime_evidence"

    fake = FakeExecutor(tmp_path / "arch")
    status = seat_reaper.reap_status(root, ledger_root=ledger, now=NOW, executor_for=lambda _k: fake,
                                     pid_alive=lambda _p: False)
    row = next(r for r in status["seats"] if r["run_id"] == run_id)
    assert row["outcome"] == "pr_merged" and row["outcome_source"] == "runtime_evidence"
    # chain presence is NOT a prerequisite — but here it strengthens the resolution
    out = _reap(root, ledger_root=ledger, repo_root=tmp_path, executor_for=lambda _k: fake)
    assert out["reaped"] == 1


# ---------------------------------------------------------------------------
# §10.5 unresolvable-past-grace-escalates
# ---------------------------------------------------------------------------


def test_5_unresolvable_past_grace_escalates(tmp_path):
    root = tmp_path / "state"
    run_id = "run-unresolved-20260613T010000Z"
    old = NOW - timedelta(seconds=seat_reaper.DEFAULT_GRACE_SECONDS + 600)
    _write_seat(
        root, run_id, dispatch=_dispatch(run_id),
        events=[_launched(run_id, ts=old), _exited(run_id, ts=old)],
    )
    fake = FakeExecutor(tmp_path / "arch")
    out = _reap(root, ledger_root=tmp_path / "ledger", repo_root=tmp_path, executor_for=lambda _k: fake)
    assert out["escalated"] == 1 and out["reaped"] == 0
    assert fake.calls == []
    rec = yaml.safe_load(next((root / "escalations").glob("*.yaml")).read_text())
    assert rec["escalation_id"].startswith("reaper-unresolved-outcome-")


def test_5b_unresolved_within_grace_is_eligible(tmp_path):
    # the SAME shape but a recent exit (collect simply has not run) is benign → eligible
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    run_id = _clean_seat(root, ledger)  # recent exit, no chain
    fake = FakeExecutor(tmp_path / "arch")
    out = _reap(root, ledger_root=ledger, repo_root=tmp_path, executor_for=lambda _k: fake)
    assert out["reaped"] == 1 and out["escalated"] == 0


# ---------------------------------------------------------------------------
# §10.6 archive-before-remove-ordering
# ---------------------------------------------------------------------------


def test_6_archive_before_remove_ordering(tmp_path):
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    _clean_seat(root, ledger)
    fake = FakeExecutor(tmp_path / "arch")
    _reap(root, ledger_root=ledger, repo_root=tmp_path, executor_for=lambda _k: fake)
    # the call log proves archive precedes pane-kill precedes release
    assert fake.steps == ["archive", "close", "release"]


def test_6b_archive_failure_halts_before_teardown(tmp_path):
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    _clean_seat(root, ledger)
    fake = FakeExecutor(tmp_path / "arch", archive_status=STEP_FAILED)
    out = _reap(root, ledger_root=ledger, repo_root=tmp_path, executor_for=lambda _k: fake)
    # archive failed for a seat that REQUIRES evidence → escalate_missing_archive, no teardown
    assert out["reaped"] == 0 and out["failed"] == 1 and out["escalated"] == 1
    assert fake.steps == ["archive"]  # never reached close/release
    rec = yaml.safe_load(next((root / "escalations").glob("*.yaml")).read_text())
    assert rec["escalation_id"].startswith("reaper-missing-archive-")


# ---------------------------------------------------------------------------
# §10.7 failed-spawn-archive-conserve
# ---------------------------------------------------------------------------


def test_7_failed_spawn_archive_then_retire(tmp_path):
    root = tmp_path / "state"
    run_id = "run-failed-spawn-20260613T110000Z"
    # spawn refused: terminal conserved for autopsy, spawn_failed_at stamped, NO conserve marker
    disp = _dispatch(run_id, spawn_failed_at="20260613T115500Z",
                     spawn_failure_reason="CC-D-6 refused: unconfirmed hook-pack")
    _write_seat(root, run_id, dispatch=disp, events=[_launched(run_id)])
    fake = FakeExecutor(tmp_path / "arch")
    out = _reap(root, ledger_root=tmp_path / "ledger", repo_root=tmp_path, executor_for=lambda _k: fake)
    # archive-then-retire is allowed (no conserve marker); evidence is preserved
    assert out["reaped"] == 1
    assert (root / "dispatches" / run_id / "dispatch.yaml").is_file()
    assert (root / "dispatches" / run_id / "events.jsonl").is_file()


def test_7b_failed_spawn_with_conserve_is_conserved(tmp_path):
    root = tmp_path / "state"
    run_id = "run-failed-conserved-20260613T110000Z"
    disp = _dispatch(run_id, spawn_failed_at="20260613T115500Z", conserve=True,
                     conserve_reason="keep for autopsy", conserved_at="2026-06-13T11:55:00Z")
    _write_seat(root, run_id, dispatch=disp, events=[_launched(run_id)])
    fake = FakeExecutor(tmp_path / "arch")
    out = _reap(root, ledger_root=tmp_path / "ledger", repo_root=tmp_path, executor_for=lambda _k: fake)
    assert out["conserved"] == 1 and out["reaped"] == 0
    assert fake.calls == []


# ---------------------------------------------------------------------------
# §10.9 root-checkout-refusal-escalates
# ---------------------------------------------------------------------------


def test_9_root_checkout_refusal_escalates(tmp_path):
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    _clean_seat(root, ledger)
    fake = FakeExecutor(
        tmp_path / "arch",
        release_status=STEP_FAILED,
        release_data={"root_checkout_refused": True},
    )
    out = _reap(root, ledger_root=ledger, repo_root=tmp_path, executor_for=lambda _k: fake)
    assert out["reaped"] == 0 and out["failed"] == 1 and out["escalated"] == 1
    # archive + close ran, release was attempted and refused — no bypass
    assert fake.steps == ["archive", "close", "release"]
    rec = yaml.safe_load(next((root / "escalations").glob("*.yaml")).read_text())
    assert rec["escalation_id"].startswith("reaper-root-checkout-refused-")


# ---------------------------------------------------------------------------
# §10.10 idempotent-once
# ---------------------------------------------------------------------------


def test_10_idempotent_once(tmp_path):
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    run_id = _clean_seat(root, ledger)
    fake = FakeExecutor(tmp_path / "arch")
    first = _reap(root, ledger_root=ledger, repo_root=tmp_path, executor_for=lambda _k: fake)
    assert first["reaped"] == 1
    calls_after_first = list(fake.calls)

    second = _reap(root, ledger_root=ledger, repo_root=tmp_path, executor_for=lambda _k: fake)
    # second pass: classified already_retired, NO new teardown, NO inflated reaped count
    assert second["reaped"] == 0 and second["already_retired"] == 1
    assert fake.calls == calls_after_first  # no double-kill / double-release
    assert len(seat_reaper.load_reaper_ledger(root)) == 1  # no double-append


# ---------------------------------------------------------------------------
# §10.13 unknown-substrate-escalates
# ---------------------------------------------------------------------------


def test_13_unknown_substrate_escalates(tmp_path):
    root = tmp_path / "state"
    run_id = "run-unknown-substrate-20260613T110000Z"
    disp = _dispatch(run_id)
    disp["terminal"] = {"kind": "container", "session_id": "x", "window_id": "y", "pane_id": "z"}
    _write_seat(root, run_id, dispatch=disp, events=[_launched(run_id), _exited(run_id)])
    out = _reap(
        root, ledger_root=tmp_path / "ledger", repo_root=tmp_path,
        executor_for=reaper_executors.default_executor_for,  # real selector → None for container
    )
    assert out["escalated"] == 1 and out["reaped"] == 0
    rec = yaml.safe_load(next((root / "escalations").glob("*.yaml")).read_text())
    assert rec["escalation_id"].startswith("reaper-unknown-executor-")


def test_13_herdr_substrate_escalates_until_close_executor_lands(tmp_path):
    # U3 wires launch/read/wait only. Do not invent an irreversible
    # `herdr pane close` API here; until a reviewed executor lands, reaper policy
    # escalates herdr seats as unsupported instead of guessing teardown.
    root = tmp_path / "state"
    run_id = "run-herdr-substrate-20260623T110000Z"
    disp = _dispatch(run_id)
    disp["terminal"] = {
        "kind": "herdr",
        "surface_ref": "herdr-surface-918aa1506d296ee1a72da70227854392",
        "pane_id": "pane-1",
        "pid": 4242,
    }
    _write_seat(root, run_id, dispatch=disp, events=[_launched(run_id), _exited(run_id)])
    out = _reap(
        root,
        ledger_root=tmp_path / "ledger",
        repo_root=tmp_path,
        executor_for=reaper_executors.default_executor_for,
    )
    assert out["escalated"] == 1 and out["reaped"] == 0
    rec = yaml.safe_load(next((root / "escalations").glob("*.yaml")).read_text())
    assert rec["escalation_id"].startswith("reaper-unknown-executor-")


# ---------------------------------------------------------------------------
# Determinism + read-only resolution + dedup
# ---------------------------------------------------------------------------


def test_status_is_deterministic_over_unchanged_state(tmp_path):
    root = tmp_path / "state"
    ledger = tmp_path / "ledger"
    _clean_seat(root, ledger)
    _write_seat(root, "run-unclean-x", dispatch=_dispatch("run-unclean-x"),
                events=[_launched("run-unclean-x", pid=999999)])
    a = seat_reaper.reap_status(root, ledger_root=ledger, now=NOW,
                                executor_for=reaper_executors.default_executor_for,
                                pid_alive=lambda _p: False)
    b = seat_reaper.reap_status(root, ledger_root=ledger, now=NOW,
                                executor_for=reaper_executors.default_executor_for,
                                pid_alive=lambda _p: False)
    assert a == b


def test_resolve_outcome_readonly_writes_nothing(tmp_path):
    root = tmp_path / "state"
    run_id = "run-x-20260613T110000Z"
    d = _write_seat(root, run_id, dispatch=_dispatch(run_id), events=[_launched(run_id), _exited(run_id)])
    before = (d / "events.jsonl").read_bytes()
    # no chain → unresolved, and the events file is byte-identical afterward
    events = list(seat_sentinel.iter_events_file(d / "events.jsonl"))
    outcome, source = seat_reaper.resolve_outcome_readonly(events, root, run_id=run_id)
    assert outcome is None and source == "unresolved"
    assert (d / "events.jsonl").read_bytes() == before


def test_escalation_dedup_reuses_same_id(tmp_path):
    root = tmp_path / "state"
    run_id = "run-unclean-dedup"
    _write_seat(root, run_id, dispatch=_dispatch(run_id), events=[_launched(run_id, pid=999999)])
    fake = FakeExecutor(tmp_path / "arch")
    first = _reap(root, ledger_root=tmp_path / "l", repo_root=tmp_path, executor_for=lambda _k: fake)
    assert first["escalated"] == 1 and first["escalations"][0]["reused"] is False
    second = _reap(root, ledger_root=tmp_path / "l", repo_root=tmp_path, executor_for=lambda _k: fake)
    assert second["escalated"] == 1 and second["escalations"][0]["reused"] is True
    # exactly one escalation file (deterministic id, no duplicate open escalation)
    assert len(list((root / "escalations").glob("*.yaml"))) == 1


def test_active_seat_is_skipped_not_reaped(tmp_path):
    root = tmp_path / "state"
    run_id = "run-live-20260613T115900Z"
    # launched, no exited, live pid, recent event → still running
    _write_seat(root, run_id, dispatch=_dispatch(run_id),
                events=[_launched(run_id, ts=NOW - timedelta(seconds=30))])
    fake = FakeExecutor(tmp_path / "arch")
    out = _reap(root, ledger_root=tmp_path / "l", repo_root=tmp_path,
                executor_for=lambda _k: fake, pid_alive=lambda _pid: True)
    assert out["skipped_active_or_unknown"] == 1 and out["reaped"] == 0 and out["escalated"] == 0
    assert fake.calls == []
