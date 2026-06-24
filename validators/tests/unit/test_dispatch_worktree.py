"""Offline PR-1 contract tests for the dispatch-worktree core."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess

from creator_engine_validator import dispatch_worktree as dw
from creator_engine_validator import pco_allocator, work_claims, worker_spawn


NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)
WK = work_claims.WorkKey("creator-engine", "ce-ops", 501)
WK_TWO = work_claims.WorkKey("creator-engine", "ce-ops", 502)


@dataclass
class FakeDispatchIO:
    claim_ok: bool = True
    claim_id: str = "claim-dispatch"
    claim_refusal_reason: str = "active_foreign_claim"
    allocate_raises: bool = False
    exec_rc: int = 0
    exec_raises: bool = False

    def __post_init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []
        self.allocations: list[dict[str, object]] = []
        self.execs: list[dict[str, object]] = []
        self.pushes: list[tuple[Path, str]] = []
        self.pco_release_attempts: list[tuple[str, str]] = []
        self.pco_release_effects: list[tuple[str, str]] = []
        self.pco_release_noops: list[tuple[str, str]] = []
        self.claim_releases: list[tuple[str, str | None]] = []
        self.best_effort_attempts: list[tuple[str, str | None, str | None]] = []
        self.best_effort_releases: list[tuple[str, str | None, str | None]] = []
        self.best_effort_noops: list[tuple[str, str | None, str | None]] = []
        self._released_pco: set[tuple[str, str]] = set()
        self._best_effort_claims: set[tuple[str, str | None, str | None]] = set()

    def install(self, monkeypatch) -> None:
        monkeypatch.setattr(work_claims, "acquire", self.acquire)
        monkeypatch.setattr(work_claims, "release", self.release_claim)
        monkeypatch.setattr(work_claims, "best_effort_release", self.best_effort_release)
        monkeypatch.setattr(pco_allocator, "allocate", self.allocate)
        monkeypatch.setattr(pco_allocator, "release", self.release_allocation)
        monkeypatch.setattr(worker_spawn, "scrub_worker_environment", self.scrub)

    def acquire(self, key, _runner, **_kwargs):
        work_key = key.work_key
        self.calls.append(("claim", work_key, None))
        return _claim_result(
            ok=self.claim_ok,
            work_key=work_key,
            claim_id=self.claim_id if self.claim_ok else None,
            refusal_reason=None if self.claim_ok else self.claim_refusal_reason,
            note="acquired" if self.claim_ok else "held by another controller",
        )

    def allocate(self, **kwargs) -> None:
        lane_id = str(kwargs["lane_id"])
        self.calls.append(("allocate", lane_id, str(kwargs["worktree_path"])))
        if self.allocate_raises:
            raise pco_allocator.PcoAllocatorError("allocator refused")
        self.allocations.append(dict(kwargs))

    def scrub(self, **kwargs):
        lane_id = str(kwargs["worker_id"])
        self.calls.append(("scrub", lane_id, None))
        return {"CE_FAKE_WORKER": lane_id}, {"scrubbed": True}

    def exec_fn(self, harness_cmd, *, cwd, env, brief_path):
        self.calls.append(("exec", str(cwd), None))
        if self.exec_raises:
            raise RuntimeError("executor exploded")
        self.execs.append(
            {
                "harness_cmd": tuple(harness_cmd),
                "cwd": Path(cwd),
                "env": dict(env),
                "brief_path": Path(brief_path),
            }
        )
        return subprocess.CompletedProcess(list(harness_cmd), self.exec_rc, "", "")

    def push_fn(self, worktree: Path, branch: str):
        self.calls.append(("push", str(worktree), branch))
        self.pushes.append((Path(worktree), branch))
        return subprocess.CompletedProcess(["git", "push", branch], 0, "", "")

    def release_allocation(self, **kwargs) -> None:
        lane_id = str(kwargs["lane_id"])
        reason = str(kwargs["release_reason"])
        key = (lane_id, reason)
        self.pco_release_attempts.append(key)
        if key in self._released_pco:
            self.pco_release_noops.append(key)
            return
        self._released_pco.add(key)
        self.pco_release_effects.append(key)
        self.calls.append(("pco-release", lane_id, reason))

    def release_claim(self, key, _runner, **kwargs):
        reason = kwargs.get("reason")
        self.calls.append(("claim-release", key.work_key, reason))
        self.claim_releases.append((key.work_key, reason))
        return _claim_result(
            ok=True,
            work_key=key.work_key,
            claim_id=kwargs.get("claim_id"),
            note="released",
        )

    def best_effort_release(self, key, _runner, claim_id, **kwargs) -> bool:
        reason = kwargs.get("reason")
        effect = (key.work_key, claim_id, reason)
        self.best_effort_attempts.append(effect)
        if effect in self._best_effort_claims:
            self.best_effort_noops.append(effect)
            return True
        self._best_effort_claims.add(effect)
        self.calls.append(("best-effort-release", key.work_key, reason))
        self.best_effort_releases.append(effect)
        return True


def _claim_result(
    *,
    ok: bool,
    work_key: str,
    claim_id: str | None = None,
    refusal_reason: str | None = None,
    note: str | None = None,
) -> work_claims.ClaimResult:
    return work_claims.ClaimResult(
        ok=ok,
        action="acquire" if ok else "acquire",
        work_key=work_key,
        state=work_claims.ClaimState(
            work_key=work_key,
            active=None,
            entries=[],
            invalid_count=0,
            comment_ids=[],
        ),
        refusal_reason=refusal_reason,
        claim_id=claim_id,
        note=note,
    )


def _spec(
    work_key: work_claims.WorkKey,
    *,
    branch: str = "dispatch/unit",
    brief_path: str = "/briefs/unit.md",
) -> dw.DispatchSpec:
    return dw.DispatchSpec(
        repo_root=Path("/repo/creator-engine"),
        ledger_root=Path("/repo/creator-engine/.ce/state/active-work-ledger"),
        worktree_root=Path("/tmp/ce-dispatch-worktrees"),
        controller_id="ce-worker",
        work_key=work_key,
        branch=branch,
        brief_path=Path(brief_path),
        harness_cmd=("python", "-m", "pytest"),
    )


def _dispatch(spec: dw.DispatchSpec, fake: FakeDispatchIO) -> dw.DispatchOutcome:
    return dw.dispatch(
        spec,
        gh_runner=lambda _argv, input_text=None: None,
        exec_fn=fake.exec_fn,
        push_fn=fake.push_fn,
        now=NOW,
    )


def test_happy_path_claim_wins_exec_pushes_and_releases_in_order(monkeypatch):
    fake = FakeDispatchIO(claim_id="claim-happy")
    fake.install(monkeypatch)

    outcome = _dispatch(_spec(WK), fake)

    assert outcome.dispatched is True
    assert outcome.stage == "complete"
    assert outcome.worktree_path != Path("/repo/creator-engine")
    assert fake.execs == [
        {
            "harness_cmd": ("python", "-m", "pytest"),
            "cwd": outcome.worktree_path,
            "env": {"CE_FAKE_WORKER": outcome.lane_id},
            "brief_path": Path("/briefs/unit.md"),
        }
    ]
    assert fake.pushes == [(outcome.worktree_path, outcome.branch)]
    assert [call[0] for call in fake.calls[-2:]] == ["pco-release", "claim-release"]
    assert fake.pco_release_effects == [(outcome.lane_id, "completed")]
    assert fake.claim_releases == [("creator-engine/ce-ops:issue:501", "completed")]


def test_foreign_claim_refuses_before_worktree_or_exec(monkeypatch):
    fake = FakeDispatchIO(claim_ok=False)
    fake.install(monkeypatch)

    outcome = _dispatch(_spec(WK), fake)

    assert outcome.dispatched is False
    assert outcome.stage == "claim"
    assert outcome.reason == "active_foreign_claim"
    assert fake.allocations == []
    assert fake.execs == []
    assert fake.pushes == []
    assert fake.calls == [("claim", "creator-engine/ce-ops:issue:501", None)]


def test_two_specs_with_different_work_keys_get_distinct_paths_and_branches(monkeypatch):
    fake = FakeDispatchIO()
    fake.install(monkeypatch)

    first = _dispatch(_spec(WK, branch="dispatch/one", brief_path="/briefs/one.md"), fake)
    fake.claim_id = "claim-two"
    second = _dispatch(_spec(WK_TWO, branch="dispatch/two", brief_path="/briefs/two.md"), fake)

    assert first.dispatched is True
    assert second.dispatched is True
    assert first.worktree_path != second.worktree_path
    assert first.branch != second.branch
    assert len({item["worktree_path"] for item in fake.allocations}) == 2
    assert len({item["branch"] for item in fake.allocations}) == 2


def test_exec_rc_one_aborts_without_push_and_releases_as_aborted(monkeypatch):
    fake = FakeDispatchIO(exec_rc=1)
    fake.install(monkeypatch)

    outcome = _dispatch(_spec(WK), fake)

    assert outcome.dispatched is False
    assert outcome.stage == "exec"
    assert outcome.exec_returncode == 1
    assert fake.pushes == []
    assert ("pco-release", outcome.lane_id, "aborted") in fake.calls
    assert fake.best_effort_releases == [
        ("creator-engine/ce-ops:issue:501", "claim-dispatch", "aborted")
    ]


def test_allocate_exception_best_effort_releases_claim_without_exec(monkeypatch):
    fake = FakeDispatchIO(claim_id="claim-allocate", allocate_raises=True)
    fake.install(monkeypatch)

    outcome = _dispatch(_spec(WK), fake)

    assert outcome.dispatched is False
    assert outcome.stage == "allocate"
    assert outcome.reason == "allocator refused"
    assert fake.execs == []
    assert fake.pushes == []
    assert fake.best_effort_releases == [
        ("creator-engine/ce-ops:issue:501", "claim-allocate", "aborted")
    ]
    assert not any(call[0] == "pco-release" for call in fake.calls)


def test_exec_exception_still_runs_releases_and_duplicate_release_is_noop(monkeypatch):
    fake = FakeDispatchIO(exec_raises=True)
    fake.install(monkeypatch)

    outcome = _dispatch(_spec(WK), fake)

    assert outcome.dispatched is False
    assert outcome.stage == "exec"
    assert outcome.reason == "exec failed: executor exploded"
    assert fake.pushes == []
    assert ("pco-release", outcome.lane_id, "aborted") in fake.calls
    assert fake.best_effort_releases == [
        ("creator-engine/ce-ops:issue:501", "claim-dispatch", "aborted")
    ]

    second = _dispatch(_spec(WK), fake)
    assert second.stage == "exec"
    assert [call for call in fake.calls if call[0] == "pco-release"] == [
        ("pco-release", outcome.lane_id, "aborted"),
    ]
    assert fake.pco_release_attempts == [
        (outcome.lane_id, "aborted"),
        (second.lane_id, "aborted"),
    ]
    assert fake.pco_release_noops == [(second.lane_id, "aborted")]
    assert fake.best_effort_attempts == [
        ("creator-engine/ce-ops:issue:501", "claim-dispatch", "aborted"),
        ("creator-engine/ce-ops:issue:501", "claim-dispatch", "aborted"),
    ]
    assert fake.best_effort_releases == [
        ("creator-engine/ce-ops:issue:501", "claim-dispatch", "aborted")
    ]
    assert fake.best_effort_noops == [
        ("creator-engine/ce-ops:issue:501", "claim-dispatch", "aborted")
    ]


def test_long_work_key_mints_pattern_valid_lane_id_no_longer_than_64_chars(monkeypatch):
    fake = FakeDispatchIO()
    fake.install(monkeypatch)
    long_work_key = work_claims.WorkKey(
        "creator-engine",
        "ce-ops",
        int(
            "123456789123456789123456789123456789"
            "123456789123456789123456789123456789"
        ),
    )

    outcome = _dispatch(_spec(long_work_key), fake)

    assert outcome.dispatched is True
    assert len(outcome.lane_id) <= 64
    assert re.fullmatch(r"[a-z][a-z0-9-]{2,63}", outcome.lane_id)
