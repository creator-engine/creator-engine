import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from creator_engine_validator import work_claims
import creator_engine_validator.conveyor_seat_pull as seat_pull
from creator_engine_validator.conveyor_intake_queue import IntakeQueue, IntakeUnit
from creator_engine_validator.conveyor_seat_pull import SeatPullAdapter, VerifiedLaneLaunch


def _brief(root: Path, name: str = "brief.md") -> tuple[str, str]:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("controller-declared brief\n", encoding="utf-8")
    return name, hashlib.sha256(path.read_bytes()).hexdigest()


def _unit(brief_ref: str, brief_sha: str, **overrides: object) -> IntakeUnit:
    data: dict[str, object] = {
        "unit_id": "n11-canary", "brief_ref": brief_ref, "branch": "ce-n11-canary",
        "worktree": "/tmp/worktrees/ce-n11-canary", "priority": 10, "work_class": "M",
        "status": "pending", "created_at": "2026-07-10T00:00:00Z", "brief_sha": brief_sha,
        "territory_paths": ("docs/", "validators/"),
    }
    data.update(overrides)
    return IntakeUnit(**data)  # type: ignore[arg-type]


def _evidence(queue: IntakeQueue, unit: IntakeUnit, seat_id: str = "seat-a", *, collision_free: bool = True) -> None:
    paths = tuple(sorted(path.rstrip("/") for path in unit.territory_paths))
    digest = hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "kind": work_claims.KIND, "schema_version": work_claims.SCHEMA_VERSION, "action": "acquire",
        "work_key": "creator-engine/creator-engine:issue:11", "claim_id": "proof-claim",
        "holder": "controller-a", "host": "controller-host", "claimed_at": now,
        "stale_after_seconds": 14400, "idempotency_key": "proof-idempotency",
    }
    evidence = {
        "unit_id": unit.unit_id, "brief_sha256": unit.brief_sha, "seat_id": seat_id,
        "controller_id": "controller-a", "state": "active", "collision_free": collision_free,
        "territory_paths": list(paths), "territory_digest": digest,
        "work_claim": {"work_key": record["work_key"], "comments": [{"id": 1, "body": work_claims.render_marker(record), "created_at": now}]},
    }
    directory = queue.root / "controller-evidence"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{unit.unit_id}.json").write_text(json.dumps(evidence), encoding="utf-8")


def _adapter(queue: IntakeQueue, root: Path, launcher=lambda _launch: True) -> SeatPullAdapter:
    return SeatPullAdapter(
        queue, trusted_brief_root=root, trusted_worktree_root=Path("/tmp"),
        governed_lane_launcher=launcher,
    )


def test_good_pull_uses_concrete_normal_claim_evidence_and_immutable_snapshot(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    received: list[VerifiedLaneLaunch] = []

    def launcher(launch: VerifiedLaneLaunch) -> bool:
        received.append(launch)
        return True

    outcome = _adapter(queue, root, launcher).pull_one("seat-a", ttl_seconds=60)

    assert (outcome.state, outcome.claim_state) == ("launched", "launching")
    assert len(received) == 1
    assert received[0].brief_path.parent.name == ".verified-snapshots"
    assert received[0].brief_path.read_bytes() == b"controller-declared brief\n"
    assert received[0].territory_paths == ("docs", "validators")
    assert received[0].claim_generation == 1
    claimed = queue._claimed_path_for_unit("n11-canary")
    assert claimed is not None and "status: launching" in claimed.read_text(encoding="utf-8")


def test_empty_queue_is_a_deterministic_noop(tmp_path: Path):
    outcome = _adapter(IntakeQueue(tmp_path / "queue"), tmp_path).pull_one("seat-a")
    assert (outcome.state, outcome.claim_state) == ("empty", "empty")


@pytest.mark.parametrize("ref", ["../brief.md", "linked.md"])
def test_bad_brief_reference_or_digest_releases_without_launch(tmp_path: Path, ref: str):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    if ref == "linked.md":
        (root / ref).symlink_to(root / brief_ref)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    outcome = _adapter(queue, root).pull_one("seat-a")
    assert outcome.state == "blocked_released"
    assert queue.list_pending()[0].unit_id == "n11-canary"


def test_component_symlink_and_post_preflight_source_swap_are_refused_or_snapshot_safe(monkeypatch, tmp_path: Path):
    root = tmp_path / "briefs"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "brief.md").write_text("controller-declared brief\n", encoding="utf-8")
    (root / "linked-dir").parent.mkdir(parents=True, exist_ok=True)
    (root / "linked-dir").symlink_to(outside, target_is_directory=True)
    digest = hashlib.sha256((outside / "brief.md").read_bytes()).hexdigest()
    queue = IntakeQueue(tmp_path / "symlink-queue")
    unit = _unit("linked-dir/brief.md", digest)
    queue.stock(unit)
    _evidence(queue, unit)
    assert _adapter(queue, root).pull_one("seat-a").state == "blocked_released"

    brief_ref, brief_sha = _brief(root, "safe.md")
    queue = IntakeQueue(tmp_path / "swap-queue")
    unit = _unit(brief_ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    original = seat_pull._validate_controller_evidence

    def swap_after_preflight(*args, **kwargs):
        original(*args, **kwargs)
        (root / brief_ref).write_text("replaced after preflight\n", encoding="utf-8")

    monkeypatch.setattr(seat_pull, "_validate_controller_evidence", swap_after_preflight)
    received: list[bytes] = []
    assert _adapter(queue, root, lambda launch: received.append(launch.brief_path.read_bytes()) or True).pull_one("seat-a").state == "launched"
    assert received == [b"controller-declared brief\n"]


def test_missing_released_or_colliding_controller_evidence_never_reaches_launcher(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    launched: list[VerifiedLaneLaunch] = []
    for suffix, evidence in (("missing", False), ("colliding", True)):
        queue = IntakeQueue(tmp_path / suffix)
        unit = _unit(brief_ref, brief_sha)
        queue.stock(unit)
        if evidence:
            _evidence(queue, unit, collision_free=False)
        result = _adapter(queue, root, lambda launch: launched.append(launch) or True).pull_one("seat-a")
        assert result.state == "blocked_released"
    assert launched == []


def test_metadata_refusal_happens_before_evidence_or_launcher(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha, branch="../bad", territory_paths=("docs", "docs/"))
    queue.stock(unit)
    outcome = _adapter(queue, root).pull_one("seat-a")
    assert outcome.state == "blocked_released"
    assert "verification_refused" in (outcome.detail or "")


def test_in_root_symlinked_worktree_is_refused_before_evidence_or_launcher(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    owned_worktrees = tmp_path / "worktrees"
    owned_worktrees.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (owned_worktrees / "linked").symlink_to(outside, target_is_directory=True)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha, worktree=str(owned_worktrees / "linked"))
    queue.stock(unit)
    adapter = SeatPullAdapter(
        queue, trusted_brief_root=root, trusted_worktree_root=owned_worktrees,
        governed_lane_launcher=lambda _launch: pytest.fail("launcher must not run"),
    )

    outcome = adapter.pull_one("seat-a")

    assert outcome.state == "blocked_released"
    assert "verification_refused:ValueError" in (outcome.detail or "")


def test_snapshot_directory_swap_to_symlink_is_refused(monkeypatch, tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    snapshots = root / ".verified-snapshots"
    snapshots.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    original_stat = seat_pull.os.stat
    swapped = False

    def swap_after_snapshot_check(path, *args, **kwargs):
        nonlocal swapped
        result = original_stat(path, *args, **kwargs)
        if (
            path == ".verified-snapshots"
            and kwargs.get("follow_symlinks") is False
            and kwargs.get("dir_fd") is not None
            and not swapped
        ):
            swapped = True
            snapshots.rename(root / ".verified-snapshots-original")
            snapshots.symlink_to(outside, target_is_directory=True)
        return result

    monkeypatch.setattr(seat_pull.os, "stat", swap_after_snapshot_check)

    outcome = _adapter(queue, root).pull_one("seat-a")

    assert swapped
    assert outcome.state == "blocked_released"
    assert "verification_refused:ValueError" in (outcome.detail or "")


def test_source_replacement_after_preflight_does_not_change_launched_snapshot(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    launched: list[bytes] = []

    def launcher(launch: VerifiedLaneLaunch) -> bool:
        (root / brief_ref).write_text("replaced after verification\n", encoding="utf-8")
        launched.append(launch.brief_path.read_bytes())
        return True

    assert _adapter(queue, root, launcher).pull_one("seat-a").state == "launched"
    assert launched == [b"controller-declared brief\n"]


def test_expired_claim_cannot_fence_and_slow_launch_has_one_owner(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    entered = threading.Event()
    release = threading.Event()
    launches: list[str] = []

    def slow_launcher(launch: VerifiedLaneLaunch) -> bool:
        entered.set()
        assert release.wait(2)
        launches.append(launch.unit_id)
        return True

    first_clock = iter(("2026-07-10T12:00:00Z", "2026-07-10T12:00:00Z"))
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            _adapter(queue, root, slow_launcher).pull_one, "seat-a", ttl_seconds=1,
            clock=lambda: next(first_clock),
        )
        assert entered.wait(2)
        # A later contender must not reclaim a fenced record even after the TTL.
        second = executor.submit(
            _adapter(queue, root).pull_one, "seat-b", ttl_seconds=1,
            clock=lambda: "2026-07-10T12:00:02Z",
        )
        assert second.result().state == "empty"
        release.set()
        assert first.result().state == "launched"
    assert launches == ["n11-canary"]


def test_launcher_refusal_releases_but_exception_is_retained_for_duplicate_safety(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    assert _adapter(queue, root, lambda _launch: False).pull_one("seat-a").state == "blocked_released"
    _evidence(queue, unit, "seat-b")
    assert _adapter(queue, root, lambda _launch: (_ for _ in ()).throw(RuntimeError())).pull_one("seat-b").state == "blocked_retained"


def test_handoff_has_no_inline_brief_or_credential_mutation(tmp_path: Path):
    root = tmp_path / "briefs"
    brief_ref, brief_sha = _brief(root)
    queue = IntakeQueue(tmp_path / "queue")
    unit = _unit(brief_ref, brief_sha)
    queue.stock(unit)
    _evidence(queue, unit)
    before = dict(os.environ)
    assert _adapter(queue, root).pull_one("seat-a").state == "launched"
    assert dict(os.environ) == before
    assert {field.name for field in fields(VerifiedLaneLaunch)} == {
        "unit_id", "brief_path", "brief_sha256", "branch", "worktree", "work_class",
        "territory_paths", "territory_digest", "claim_generation",
    }
