from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from creator_engine_validator import v3_cli
from creator_engine_validator.forge import fleet_status
from creator_engine_validator.forge import integrator_belt


def _event(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _lifecycle(path: Path, *, seat_id: str, state: str, branch: str | None = None) -> None:
    record = {
        "kind": "seat-lifecycle-record",
        "record_type": "seat_lifecycle",
        "schema_version": "1",
        "seat": {"seat_id": seat_id, "host_id": "host-a"},
        "work": {},
        "dispatch": {},
        "lifecycle": {"state": state},
    }
    if branch:
        record["work"]["branch"] = branch
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")


def _candidate(**overrides) -> integrator_belt.DaemonPullRequest:
    data = {
        "repo": "o/r",
        "pr_number": 12,
        "title": "ready",
        "url": "https://github.com/o/r/pull/12",
        "head_ref": "feature",
        "head_sha": "a" * 40,
        "base_ref": "main",
        "review_decision": "APPROVED",
        "approving_review_commits": ("a" * 40,),
        "mergeable": "MERGEABLE",
        "merge_state_status": "CLEAN",
        "rollup_state": "SUCCESS",
        "checks": (),
        "changed_paths": (),
        "files_complete": True,
        "checks_complete": True,
        "is_draft": False,
    }
    data.update(overrides)
    return integrator_belt.DaemonPullRequest(**data)


def test_parse_last_pass_summary_reads_integrator_and_review_logs():
    lines = [
        "not json",
        json.dumps({"action": "daemon_pass_complete", "index": 1, "enqueue_count": 2}),
        json.dumps({"event": "review_pickup_pass_complete", "index": 3, "routes": 4, "skipped": 1}),
    ]

    integrator = fleet_status.parse_last_pass_summary(lines, kind="integrator")
    review = fleet_status.parse_last_pass_summary(lines, kind="review")

    assert integrator is not None
    assert integrator.summary["enqueue"] == 2
    assert integrator.summary["skip"] == 0
    assert review is not None
    assert review.index == 3
    assert review.summary == {"routes": 4, "skipped": 1, "dry_run": False}


def test_probe_process_uses_injected_runner_and_parses_pgrep_rows():
    calls = []

    def runner(argv):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="123 ce queue-daemon --loop\n", stderr="")

    probe = fleet_status.probe_process(r"queue-daemon.*--loop", runner=runner)

    assert calls == [["pgrep", "-af", r"queue-daemon.*--loop"]]
    assert probe.running is True
    assert probe.pids == (123,)
    assert probe.commands == ("ce queue-daemon --loop",)


def test_open_pr_board_projects_integrator_candidates(monkeypatch):
    fake_runner = object()
    captured = {}

    def fake_discover(**kwargs):
        captured.update(kwargs)
        return (_candidate(pr_number=7, review_decision="CHANGES_REQUESTED", merge_state_status="DIRTY"),)

    monkeypatch.setattr(fleet_status.integrator_belt, "discover_daemon_candidates", fake_discover)

    board = fleet_status.fetch_open_pr_board(repo="o/r", limit=17, gh_runner=fake_runner)

    assert captured["repo"] == "o/r"
    assert captured["org"] is None
    assert captured["first"] == 17
    assert captured["gh_runner"] is fake_runner
    assert board.count == 1
    assert board.items[0].number == 7
    assert board.items[0].review_decision == "CHANGES_REQUESTED"
    assert board.items[0].mergeable_state == "DIRTY"


def test_collect_fleet_status_reuses_seats_and_explicit_paths(tmp_path, monkeypatch):
    state_root = tmp_path / ".ce" / "state"
    ledger = state_root / "active-work-ledger"
    events = state_root / "dispatches" / "seat-live" / "events.jsonl"
    integrator_log = tmp_path / "integrator-daemon.log"
    review_log = tmp_path / "review-daemon.log"
    _event(events, {"event": "launched", "seat_id": "seat-live", "run_id": "run-1"})
    _lifecycle(ledger / "seats" / "host-a" / "seat-idle.yaml", seat_id="seat-idle", state="idle")
    integrator_log.write_text(
        json.dumps({"action": "daemon_pass_complete", "index": 2, "enqueue_count": 1}) + "\n",
        encoding="utf-8",
    )
    review_log.write_text(
        json.dumps({"event": "review_pickup_pass_complete", "index": 5, "routes": 2, "skipped": 3}) + "\n",
        encoding="utf-8",
    )

    def process_runner(argv):
        pattern = argv[-1]
        stdout = "10 ce queue-daemon --loop\n" if "queue-daemon" in pattern else ""
        return subprocess.CompletedProcess(argv, 0 if stdout else 1, stdout=stdout, stderr="")

    monkeypatch.setattr(
        fleet_status.integrator_belt,
        "discover_daemon_candidates",
        lambda **_kwargs: (_candidate(),),
    )

    status = fleet_status.collect_fleet_status(
        state_root=state_root,
        integrator_log=integrator_log,
        review_log=review_log,
        repo="o/r",
        process_runner=process_runner,
        gh_runner=object(),
    )

    assert status.seat_counts["total"] == 2
    assert status.seat_counts["working"] == 1
    assert status.seat_counts["idle"] == 1
    assert status.daemons[0].process.running is True
    assert status.daemons[0].last_pass is not None
    assert status.daemons[0].last_pass.summary["enqueue"] == 1
    assert status.daemons[1].process.running is False
    assert status.daemons[1].last_pass is not None
    assert status.daemons[1].last_pass.summary["routes"] == 2
    assert status.pull_requests.items[0].mergeable_state == "CLEAN"


def test_v3_cli_fleet_status_json_smoke(monkeypatch, capsys):
    fixture = fleet_status.FleetStatus(
        seats=(),
        seat_counts={"total": 0},
        daemons=(),
        pull_requests=fleet_status.PullRequestBoard(count=0, items=(), repo="o/r"),
    )
    captured = {}

    def fake_collect(**kwargs):
        captured.update(kwargs)
        return fixture

    monkeypatch.setattr(fleet_status, "collect_fleet_status", fake_collect)

    ret = v3_cli.main([
        "fleet",
        "status",
        "--root",
        "/tmp/state",
        "--repo",
        "o/r",
        "--json",
    ])

    assert ret == 0
    assert captured["repo"] == "o/r"
    out = json.loads(capsys.readouterr().out)
    assert out["seats"]["count"] == 0
    assert out["pull_requests"]["count"] == 0
