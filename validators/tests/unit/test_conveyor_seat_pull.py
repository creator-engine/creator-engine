import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from pathlib import Path

from creator_engine_validator.conveyor_intake_queue import IntakeQueue, IntakeUnit
from creator_engine_validator.conveyor_seat_pull import SeatPullAdapter, VerifiedLaneLaunch


def _brief(root: Path, name: str = "brief.md") -> tuple[str, str]:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("controller-declared brief\n", encoding="utf-8")
    return name, hashlib.sha256(path.read_bytes()).hexdigest()


def _unit(brief_ref: str, brief_sha: str) -> IntakeUnit:
    return IntakeUnit(
        unit_id="n11-canary",
        brief_ref=brief_ref,
        branch="ce-n11-canary",
        worktree="/tmp/ce-n11-canary",
        priority=10,
        work_class="M",
        status="pending",
        created_at="2026-07-10T00:00:00Z",
        brief_sha=brief_sha,
        territory_paths=("validators/",),
    )


def _adapter(queue: IntakeQueue, root: Path, preflight=lambda _unit, _launch: True, launcher=lambda _launch: True):
    return SeatPullAdapter(
        queue,
        trusted_brief_root=root,
        territory_claim_preflight=preflight,
        governed_lane_launcher=launcher,
    )


def test_good_pull_hands_only_verified_pointer_and_lane_metadata(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    queue.stock(_unit(brief_ref, brief_sha))
    received: list[VerifiedLaneLaunch] = []

    def launcher(launch: VerifiedLaneLaunch) -> bool:
        received.append(launch)
        return True

    outcome = _adapter(queue, root, launcher=launcher).pull_one("seat-a", ttl_seconds=60)

    assert outcome.state == "launched"
    assert outcome.claim_state == "claimed"
    assert outcome.unit_id == "n11-canary"
    assert outcome.brief_sha256 == brief_sha
    assert len(received) == 1
    assert received[0].brief_path == root / brief_ref
    assert received[0].brief_sha256 == brief_sha
    assert not hasattr(received[0], "brief_contents")
    assert queue._claimed_path_for_unit("n11-canary") is not None


def test_empty_queue_is_a_deterministic_noop(tmp_path: Path):
    outcome = _adapter(IntakeQueue(tmp_path / "queue"), tmp_path).pull_one("seat-a")

    assert outcome.state == "empty"
    assert outcome.claim_state == "empty"
    assert outcome.unit_id is None


def test_sha_mismatch_and_legacy_sha_release_without_launch(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, _brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    queue.stock(_unit(brief_ref, "a" * 64))
    launches = []

    def launcher(launch: VerifiedLaneLaunch) -> bool:
        launches.append(launch)
        return True

    outcome = _adapter(queue, root, launcher=launcher).pull_one("seat-a")

    assert outcome.state == "blocked_released"
    assert outcome.detail is not None and "verification_refused" in outcome.detail
    assert launches == []
    assert [unit.unit_id for unit in queue.list_pending()] == ["n11-canary"]

    queue = IntakeQueue(tmp_path / "legacy-queue")
    queue.stock(_unit(brief_ref, "a" * 40))
    outcome = _adapter(queue, root).pull_one("seat-a")
    assert outcome.state == "blocked_released"
    assert "64-hex" in (outcome.detail or "")


def test_path_escape_and_symlink_are_refused_and_released(tmp_path: Path):
    root = tmp_path / "briefs"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()

    queue = IntakeQueue(tmp_path / "escape-queue")
    queue.stock(_unit("../outside.md", digest))
    assert _adapter(queue, root).pull_one("seat-a").state == "blocked_released"

    (root / "linked.md").symlink_to(outside)
    queue = IntakeQueue(tmp_path / "symlink-queue")
    queue.stock(_unit("linked.md", digest))
    outcome = _adapter(queue, root).pull_one("seat-a")
    assert outcome.state == "blocked_released"
    assert "symlink" in (outcome.detail or "")


def test_preflight_and_launcher_refusals_release_for_retry(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    queue.stock(_unit(brief_ref, brief_sha))

    outcome = _adapter(queue, root, preflight=lambda _unit, _launch: False).pull_one("seat-a")
    assert outcome.state == "blocked_released"
    assert outcome.detail == "territory_claim_refused"

    launches = []

    def refuse_launcher(launch: VerifiedLaneLaunch) -> bool:
        launches.append(launch)
        return False

    outcome = _adapter(queue, root, launcher=refuse_launcher).pull_one("seat-b")
    assert outcome.state == "blocked_released"
    assert outcome.detail == "launcher_refused"
    assert len(launches) == 1

    outcome = _adapter(queue, root).pull_one("seat-c")
    assert outcome.state == "launched"
    assert len(list(queue.claimed_dir.iterdir())) == 1


def test_concurrent_pulls_have_exactly_one_launcher_winner(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    queue.stock(_unit(brief_ref, brief_sha))
    launches: list[VerifiedLaneLaunch] = []

    def launcher(launch: VerifiedLaneLaunch) -> bool:
        launches.append(launch)
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda seat: _adapter(queue, root, launcher=launcher).pull_one(seat), ("seat-a", "seat-b")))

    assert [outcome.state for outcome in outcomes].count("launched") == 1
    assert [outcome.state for outcome in outcomes].count("empty") == 1
    assert len(launches) == 1


def test_adapter_handoff_has_no_inline_brief_or_authority_credential_mutation(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    queue.stock(_unit(brief_ref, brief_sha))
    environment_before = dict(os.environ)

    outcome = _adapter(queue, root).pull_one("seat-a")

    assert outcome.state == "launched"
    assert dict(os.environ) == environment_before
    handoff_fields = {field.name for field in fields(VerifiedLaneLaunch)}
    assert handoff_fields == {
        "unit_id",
        "brief_path",
        "brief_sha256",
        "branch",
        "worktree",
        "work_class",
        "territory_paths",
    }
