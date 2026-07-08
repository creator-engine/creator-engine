from pathlib import Path

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
