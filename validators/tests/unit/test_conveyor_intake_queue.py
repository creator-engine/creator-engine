import dataclasses
import json
import threading
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
import creator_engine_validator.conveyor_intake_queue as intake


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


def test_numeric_priority_ordering_handles_six_digits_and_tie_breaks_by_filename(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("one-hundred-thousand", priority=100000))
    queue.stock(_unit("ninety-nine-thousand", priority=99999))
    queue.stock(_unit("same-priority-b", priority=5))
    queue.stock(_unit("same-priority-a", priority=5))

    assert [unit.unit_id for unit in queue.list_pending()] == [
        "same-priority-a",
        "same-priority-b",
        "ninety-nine-thousand",
        "one-hundred-thousand",
    ]
    claimed = queue.claim_entry("seat-a")
    assert claimed is not None and claimed.unit_id == "same-priority-a"


@pytest.mark.parametrize("priority", [True, 1.0, -1])
def test_non_integer_or_negative_priority_is_rejected(priority, tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")

    with pytest.raises(ValueError, match="priority"):
        queue.stock(_unit("invalid-priority", priority=priority))


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
    claimed = queue.claim_entry("seat-a")
    assert claimed is not None

    try:
        queue.release_entry("unit-a", "seat-b")
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong claimer must be refused")
    queue.release_entry("unit-a", "seat-a", claim_token=claimed.claim_token)

    assert [unit.unit_id for unit in queue.list_pending()] == ["unit-a"]
    assert queue.list_pending()[0].claimed_by is None


def test_claim_tokens_fence_ownership_and_launching_claims_are_not_reclaimed(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    claimed = queue.claim_entry("seat-a", ttl_seconds=1, clock=lambda: "2026-07-10T12:00:00Z")
    assert claimed is not None and claimed.claim_token is not None
    with pytest.raises(PermissionError, match="token"):
        queue.fence_launch("unit-a", "seat-a", "0" * 64, clock=lambda: "2026-07-10T12:00:00Z")
    fenced = queue.fence_launch("unit-a", "seat-a", claimed.claim_token, clock=lambda: "2026-07-10T12:00:00Z")
    assert fenced.status == "launching"
    assert queue.claim_entry("seat-b", clock=lambda: "2026-07-10T12:00:02Z") is None


def test_release_move_failure_restores_owned_record(monkeypatch, tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    claimed = queue.claim_entry("seat-a")
    assert claimed is not None and claimed.claim_token is not None
    original_replace = queue.__class__.__module__
    import creator_engine_validator.conveyor_intake_queue as intake
    real_replace = intake.os.replace

    def fail_pending(source, destination):
        if Path(destination).parent == queue.pending_dir:
            raise OSError("injected move failure")
        return real_replace(source, destination)

    monkeypatch.setattr(intake.os, "replace", fail_pending)
    with pytest.raises(intake.IntakeTransitionError, match="release transition failed"):
        queue.release_entry("unit-a", "seat-a", claim_token=claimed.claim_token)
    restored = queue._claimed_path_for_unit("unit-a")
    assert restored is not None
    assert "status: claimed" in restored.read_text(encoding="utf-8")


def test_claim_write_failure_rolls_back_to_pending_and_ledger_failure_is_bounded(monkeypatch, tmp_path: Path, capsys):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    import creator_engine_validator.conveyor_intake_queue as intake
    real_write = intake._write_unit_atomic

    def fail_claim_write(path, unit):
        if path.parent == queue.claimed_dir:
            raise OSError("injected write failure")
        return real_write(path, unit)

    monkeypatch.setattr(intake, "_write_unit_atomic", fail_claim_write)
    with pytest.raises(intake.IntakeTransitionError, match="claim transition failed"):
        queue.claim_entry("seat-a")
    assert [unit.unit_id for unit in queue.list_pending()] == ["unit-a"]
    assert list(queue.claimed_dir.iterdir()) == []
    monkeypatch.setattr(intake, "_write_unit_atomic", real_write)
    claimed = queue.claim_entry("seat-a")
    assert claimed is not None
    assert "ledger append failed" not in capsys.readouterr().err


@pytest.mark.parametrize("window", ["destination", "source"])
@pytest.mark.parametrize("transition, destination", [
    ("release", "pending"),
    ("complete", "done"),
    ("reclaim", "pending"),
])
def test_post_rename_directory_fsync_failure_keeps_one_authoritative_record(
    monkeypatch, tmp_path: Path, transition: str, destination: str, window: str,
):
    """A post-rename fsync error must never recreate the old claimed record."""
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    claimed = queue.claim_entry("seat-a", ttl_seconds=1, clock=lambda: "2026-07-10T12:00:00Z")
    assert claimed is not None and claimed.claim_token is not None
    source = queue._claimed_path_for_unit("unit-a")
    assert source is not None
    target = queue.root / destination / source.name
    real_replace = intake.os.replace
    real_fsync_directory = intake._fsync_directory
    renamed = False
    failed = False

    def arm_after_rename(from_path, to_path):
        nonlocal renamed
        result = real_replace(from_path, to_path)
        if Path(from_path) == source and Path(to_path) == target:
            renamed = True
        return result

    def fail_one_window(path):
        nonlocal failed
        if renamed and not failed and Path(path) == (target.parent if window == "destination" else source.parent):
            failed = True
            raise OSError(f"injected {window} directory fsync failure")
        return real_fsync_directory(path)

    monkeypatch.setattr(intake.os, "replace", arm_after_rename)
    monkeypatch.setattr(intake, "_fsync_directory", fail_one_window)
    if transition == "release":
        queue.release_entry("unit-a", "seat-a", claim_token=claimed.claim_token)
    elif transition == "complete":
        queue.complete_entry(
            "unit-a", "seat-a", claim_token=claimed.claim_token, claim_generation=claimed.claim_generation,
        )
    else:
        queue._reclaim_stale("2026-07-10T12:00:02Z")

    assert failed
    assert not source.exists()
    assert target.exists()
    assert intake._read_unit(target).status == ("done" if transition == "complete" else "pending")


@pytest.mark.parametrize("status, destination", [("pending", "pending"), ("done", "done")])
def test_process_death_between_state_write_and_rename_is_recovered(tmp_path: Path, status: str, destination: str):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    claimed = queue.claim_entry("seat-a")
    assert claimed is not None
    claimed_path = queue._claimed_path_for_unit("unit-a")
    assert claimed_path is not None

    # This is the durable on-disk fixture a process death leaves after the
    # state write and before its location rename; no rollback mock is involved.
    stranded = dataclasses.replace(
        claimed,
        status=status,  # type: ignore[arg-type]
        claimed_by=None if status == "pending" else claimed.claimed_by,
        claimed_at=None if status == "pending" else claimed.claimed_at,
        claim_expires_at=None if status == "pending" else claimed.claim_expires_at,
        claim_token=None if status == "pending" else claimed.claim_token,
        launch_fenced_at=None if status == "pending" else claimed.launch_fenced_at,
    )
    intake._write_unit_atomic(claimed_path, stranded)

    queue._ensure_dirs()

    recovered = queue.root / destination / claimed_path.name
    assert recovered.exists()
    assert not claimed_path.exists()
    assert intake._read_unit(recovered).status == status


@pytest.mark.parametrize("status, destination", [("pending", "pending"), ("done", "done")])
@pytest.mark.parametrize("window", ["destination", "source"])
def test_recovery_post_rename_directory_fsync_failure_has_no_split_brain(
    monkeypatch, tmp_path: Path, status: str, destination: str, window: str,
):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    claimed = queue.claim_entry("seat-a")
    assert claimed is not None
    source = queue._claimed_path_for_unit("unit-a")
    assert source is not None
    stranded = dataclasses.replace(
        claimed,
        status=status,  # type: ignore[arg-type]
        claimed_by=None if status == "pending" else claimed.claimed_by,
        claimed_at=None if status == "pending" else claimed.claimed_at,
        claim_expires_at=None if status == "pending" else claimed.claim_expires_at,
        claim_token=None if status == "pending" else claimed.claim_token,
        launch_fenced_at=None if status == "pending" else claimed.launch_fenced_at,
    )
    intake._write_unit_atomic(source, stranded)
    target = queue.root / destination / source.name
    real_replace = intake.os.replace
    real_fsync_directory = intake._fsync_directory
    renamed = False
    failed = False

    def arm_after_rename(from_path, to_path):
        nonlocal renamed
        result = real_replace(from_path, to_path)
        if Path(from_path) == source and Path(to_path) == target:
            renamed = True
        return result

    def fail_one_window(path):
        nonlocal failed
        if renamed and not failed and Path(path) == (target.parent if window == "destination" else source.parent):
            failed = True
            raise OSError(f"injected {window} directory fsync failure")
        return real_fsync_directory(path)

    monkeypatch.setattr(intake.os, "replace", arm_after_rename)
    monkeypatch.setattr(intake, "_fsync_directory", fail_one_window)
    queue._recover_stranded_locations()

    assert failed
    assert not source.exists()
    assert target.exists()
    assert intake._read_unit(target).status == status


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
    claimed = queue.claim_entry("seat-a", clock=lambda: "2026-07-10T12:00:00Z")
    assert claimed is not None

    try:
        queue.complete_entry(
            "unit-a", "seat-b", claim_token=claimed.claim_token, claim_generation=claimed.claim_generation,
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong claimer must be refused")
    queue.complete_entry(
        "unit-a", "seat-a", claim_token=claimed.claim_token, claim_generation=claimed.claim_generation,
        clock=lambda: "2026-07-10T12:01:00Z",
    )

    ledger = _ledger_records(queue)
    assert [entry["action"] for entry in ledger] == ["claimed", "completed"]
    assert all(entry["unit_id"] == "unit-a" for entry in ledger)
    assert all(entry["brief_sha"] == "a" * 40 for entry in ledger)


def test_complete_refuses_stale_same_seat_claim_after_reclaim(tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    first = queue.claim_entry("seat-a", ttl_seconds=1, clock=lambda: "2026-07-10T12:00:00Z")
    assert first is not None

    successor = queue.claim_entry("seat-a", ttl_seconds=60, clock=lambda: "2026-07-10T12:00:02Z")
    assert successor is not None and successor.claim_generation == first.claim_generation + 1

    with pytest.raises(PermissionError, match="token|generation"):
        queue.complete_entry(
            "unit-a", "seat-a", claim_token=first.claim_token, claim_generation=first.claim_generation,
        )
    queue.complete_entry(
        "unit-a", "seat-a", claim_token=successor.claim_token, claim_generation=successor.claim_generation,
    )


def test_stale_reclaim_and_launch_fence_serialize_one_claim_transition(monkeypatch, tmp_path: Path):
    queue = IntakeQueue(tmp_path / "intake-queue")
    queue.stock(_unit("unit-a"))
    claimed = queue.claim_entry("seat-a", ttl_seconds=1, clock=lambda: "2026-07-10T12:00:00Z")
    assert claimed is not None and claimed.claim_token is not None
    import creator_engine_validator.conveyor_intake_queue as intake

    real_write = intake._write_unit_atomic
    reclaim_read = threading.Event()
    release_reclaim = threading.Event()
    fence_finished = threading.Event()
    fence_errors: list[BaseException] = []

    def pause_reclaim(path, unit):
        if path.parent == queue.claimed_dir and unit.status == "pending" and not reclaim_read.is_set():
            reclaim_read.set()
            assert release_reclaim.wait(2)
        return real_write(path, unit)

    monkeypatch.setattr(intake, "_write_unit_atomic", pause_reclaim)
    with ThreadPoolExecutor(max_workers=2) as executor:
        reclaimer = executor.submit(
            queue.claim_entry, "seat-b", ttl_seconds=60, clock=lambda: "2026-07-10T12:00:02Z",
        )
        assert reclaim_read.wait(2)

        def fence() -> None:
            try:
                queue.fence_launch("unit-a", "seat-a", claimed.claim_token, clock=lambda: "2026-07-10T12:00:00Z")
            except BaseException as exc:
                fence_errors.append(exc)
            finally:
                fence_finished.set()

        executor.submit(fence)
        assert not fence_finished.wait(0.05)
        release_reclaim.set()
        successor = reclaimer.result()
        assert successor is not None and successor.claimed_by == "seat-b"
        assert fence_finished.wait(2)

    assert len(fence_errors) == 1
    assert isinstance(fence_errors[0], (FileNotFoundError, PermissionError))
    current = queue._claimed_path_for_unit("unit-a")
    assert current is not None and "claimed_by: seat-b" in current.read_text(encoding="utf-8")


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
