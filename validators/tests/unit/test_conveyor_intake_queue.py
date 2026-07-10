import dataclasses
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from creator_engine_validator import conveyor_daemon_runner as runner
from creator_engine_validator.conveyor_daemon_runner import load_config
from creator_engine_validator.conveyor_intake_queue import (
    IntakeQueue,
    IntakeQueueReader,
    IntakeUnit,
)


class FakeLease:
    def __init__(self):
        self.released = False

    def release(self):
        self.released = True


def _unit(unit_id: str, *, priority: int = 10) -> IntakeUnit:
    return IntakeUnit(
        unit_id=unit_id,
        brief_ref=f"/briefs/{unit_id}.md",
        branch=f"ce-{unit_id}",
        worktree=f"/tmp/{unit_id}",
        priority=priority,
        work_class="S",
        status="pending",
        created_at="2026-07-08T00:00:00Z",
        brief_sha="a" * 40,
        territory_paths=("validators/", "docs/"),
    )


def _base_env(tmp_path: Path) -> dict[str, str]:
    secret_file = tmp_path / "signing-secret"
    secret_file.write_text("secret-value\n", encoding="utf-8")
    return {
        "CE_CONVEYOR_DAEMON_SEAT_PROBES": '[{"seat_id":"seat-a","argv":["python","--version"]}]',
        "CE_CONVEYOR_DAEMON_RUNTIME_ROOT": str(tmp_path / "runtime"),
        "CE_CONVEYOR_DAEMON_DISCOVERY_STATE": str(tmp_path / "state" / "discovery.json"),
        "GH_TOKEN": "gh-test-token",
        "CE_DAEMON_LEASE_ROOT": str(tmp_path / "leases"),
        "CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE": str(secret_file),
    }


def test_stock_creates_pending_file(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")

    queue.stock(_unit("unit-a", priority=7))

    files = list((tmp_path / "intake-queue" / "pending").iterdir())
    assert len(files) == 1
    assert files[0].name == "00007-unit-a.yaml"


def test_claim_next_returns_oldest_pending(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("later", priority=20))
    queue.stock(_unit("earlier", priority=5))

    claimed = queue.claim_next()

    assert claimed is not None
    assert claimed.unit_id == "earlier"
    assert claimed.status == "claimed"
    assert not (tmp_path / "intake-queue" / "pending" / "00005-earlier.yaml").exists()
    assert (tmp_path / "intake-queue" / "claimed" / "00005-earlier.yaml").exists()


def test_claim_next_returns_none_when_empty(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")

    assert queue.claim_next() is None


def test_mark_done_moves_to_done(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a", priority=3))
    claimed = queue.claim_next()

    assert claimed is not None
    queue.mark_done(claimed.unit_id)

    assert not (tmp_path / "intake-queue" / "claimed" / "00003-unit-a.yaml").exists()
    assert (tmp_path / "intake-queue" / "done" / "00003-unit-a.yaml").exists()


def test_list_pending_returns_sorted_order(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("middle", priority=10))
    queue.stock(_unit("first", priority=1))
    queue.stock(_unit("last", priority=30))

    assert [unit.unit_id for unit in queue.list_pending()] == ["first", "middle", "last"]


def test_intake_queue_reader_plans_idle_seats(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a", priority=1))

    plans = list(IntakeQueueReader(queue, {"seat-a": False}))

    assert len(plans) == 1
    assert plans[0].seat_id == "seat-a"
    assert plans[0].unit.unit_id == "unit-a"
    assert plans[0].action == "WOULD_DISPATCH"


def test_intake_queue_reader_skips_busy_seats(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a", priority=1))

    assert list(IntakeQueueReader(queue, {"seat-a": True})) == []


def test_daemon_intake_planning_logs_bad_pending_file_and_continues(
    monkeypatch,
    tmp_path: Path,
    capsys,
):
    queue_root = tmp_path / "intake-queue"
    queue = IntakeQueue(queue_root)
    queue.stock(_unit("valid", priority=1))
    (queue_root / "pending" / "00000-bad.yaml").write_text("unit_id: [\n", encoding="utf-8")

    env = _base_env(tmp_path)
    env["CE_CONVEYOR_DAEMON_ITERATIONS"] = "2"
    env["CE_CONVEYOR_DAEMON_INTERVAL_SECONDS"] = "0.001"
    env["CE_CONVEYOR_INTAKE_ENABLED"] = "1"
    env["CE_CONVEYOR_INTAKE_QUEUE_ROOT"] = str(queue_root)
    lease = FakeLease()
    run_once_calls = 0

    class FakeDaemon:
        def __init__(self, **kwargs):
            self.discovery_runner = kwargs["discovery_runner"]

        def run_once(self):
            nonlocal run_once_calls
            run_once_calls += 1
            tuple(self.discovery_runner())

    monkeypatch.setattr(runner, "acquire", lambda *args, **kwargs: lease)
    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)
    monkeypatch.setattr(runner, "subprocess_probe_runner", lambda argv: "")

    assert runner.main(env) == 0

    err = capsys.readouterr().err
    assert run_once_calls == 2
    assert lease.released is True
    assert "conveyor-intake skipped pending file" in err
    assert "00000-bad.yaml" in err
    assert "conveyor-intake dry-run: WOULD_DISPATCH unit valid" in err


def test_load_config_intake_disabled_by_default(tmp_path: Path):
    config = load_config(_base_env(tmp_path))

    assert config.intake_enabled is False
    assert config.intake_queue_root is None


def test_load_config_intake_enabled_when_flag_set(tmp_path: Path):
    env = _base_env(tmp_path)
    env["CE_CONVEYOR_INTAKE_ENABLED"] = "1"
    env["CE_CONVEYOR_INTAKE_QUEUE_ROOT"] = str(tmp_path / "intake")

    config = load_config(env)

    assert config.intake_enabled is True
    assert config.intake_queue_root == tmp_path / "intake"


def test_brief_sha_is_required_and_nonempty_on_read(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    path = next(queue.pending_dir.iterdir())
    payload = path.read_text(encoding="utf-8").replace("brief_sha: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n", "")
    path.write_text(payload, encoding="utf-8")

    errors = []
    assert queue.list_pending(read_error_sink=lambda _path, error: errors.append(error)) == []
    assert isinstance(errors[0], ValueError)
    with pytest.raises(ValueError, match="brief_sha"):
        queue.stock(dataclasses.replace(_unit("empty-sha"), brief_sha=""))


def test_territory_paths_round_trip_and_publish_alias(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    unit = _unit("unit-a")

    queue.publish_entry(unit)

    assert queue.list_open()[0].territory_paths == ("validators/", "docs/")


def test_claim_entry_sets_lifecycle_fields(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))

    claimed = queue.claim_entry("seat-a", ttl_seconds=60, clock=lambda: "2026-07-10T12:00:00Z")

    assert claimed is not None
    assert claimed.claimed_by == "seat-a"
    assert claimed.claimed_at == "2026-07-10T12:00:00Z"
    assert claimed.claim_expires_at == "2026-07-10T12:01:00Z"


def test_concurrent_claimers_have_exactly_one_winner(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(lambda seat: queue.claim_entry(seat), ("seat-a", "seat-b")))

    assert sum(claim is not None for claim in claims) == 1
    assert len(list(queue.claimed_dir.iterdir())) == 1


def test_release_returns_entry_to_pending_and_rejects_wrong_claimer(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    assert queue.claim_entry("seat-a") is not None

    try:
        queue.release_entry("unit-a", "seat-b")
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong claimer must be refused")
    queue.release_entry("unit-a", "seat-a")

    assert [unit.unit_id for unit in queue.list_pending()] == ["unit-a"]
    assert queue.list_pending()[0].claimed_by is None


def test_stale_claim_is_reclaimed_and_recorded(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("expired"))
    assert queue.claim_entry("seat-a", ttl_seconds=1, clock=lambda: "2026-07-10T12:00:00Z") is not None

    claimed = queue.claim_entry("seat-b", clock=lambda: "2026-07-10T12:00:02Z")

    assert claimed is not None
    assert claimed.unit_id == "expired"
    assert claimed.claimed_by == "seat-b"
    assert _ledger_actions(queue) == ["claimed", "stale_reclaim", "claimed"]


def test_complete_rejects_wrong_claimer_and_ledger_tracks_lifecycle(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    assert queue.claim_entry("seat-a", clock=lambda: "2026-07-10T12:00:00Z") is not None

    try:
        queue.complete_entry("unit-a", "seat-b")
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong claimer must be refused")
    queue.complete_entry("unit-a", "seat-a", clock=lambda: "2026-07-10T12:01:00Z")

    ledger = _ledger_records(queue)
    assert [entry["action"] for entry in ledger] == ["claimed", "completed"]
    assert all(entry["unit_id"] == "unit-a" for entry in ledger)
    assert all(entry["brief_sha"] == "a" * 40 for entry in ledger)


def test_ledger_failure_does_not_abort_claim(monkeypatch, tmp_path: Path, capsys):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    original_open = Path.open

    def failing_ledger_open(path, *args, **kwargs):
        if path == queue.ledger_path and args and args[0] == "a":
            raise OSError("read-only queue root")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_ledger_open)

    claimed = queue.claim_entry("seat-a")

    assert claimed is not None
    assert "ledger append failed" in capsys.readouterr().err


def _ledger_records(queue: IntakeQueue) -> list[dict[str, str]]:
    return [json.loads(line) for line in queue.ledger_path.read_text(encoding="utf-8").splitlines()]


def _ledger_actions(queue: IntakeQueue) -> list[str]:
    return [entry["action"] for entry in _ledger_records(queue)]
