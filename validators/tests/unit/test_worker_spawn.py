"""Unit tests for the ce-ops#163 REQ-2 worker-spawn runtime."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import worker_spawn


class FakeLauncher:
    def __init__(self):
        self.calls = []

    def launch(self, plan):
        self.calls.append(plan)
        return worker_spawn.WorkerLaunchOutcome(
            spawned=True,
            attached=False,
            plan={"harness": plan.harness, "session": plan.worker_id},
            terminal={"kind": "tmux", "session_id": plan.worker_id, "window_id": "worker"},
            events_ref=f"{plan.worktree_path}/.ce/state/workers/{plan.worker_id}/events.jsonl",
            seat_record_ref=f"{plan.worktree_path}/.ce/state/active-work-ledger/seats/{plan.worker_id}.yaml",
            seat_lifecycle_state="active",
        )


def _worktrees(tmp_path: Path) -> tuple[Path, Path]:
    parent = tmp_path / "controller"
    worker = tmp_path / "worker"
    parent.mkdir()
    worker.mkdir()
    return parent, worker


def test_plan_maps_researcher_to_read_only_and_hashes_prompt_file(tmp_path):
    parent, worker = _worktrees(tmp_path)
    prompt = tmp_path / "prompt.md"
    prompt.write_text("do research\n", encoding="utf-8")

    plan = worker_spawn.plan_worker_spawn(
        role="researcher",
        harness="claude",
        worktree=worker,
        scope_id="ce-ops#163",
        prompt_file=prompt,
        parent_worktree=parent,
        environ={},
        dry_run=True,
    )

    assert plan.role == "researcher"
    assert plan.lane_kind == "read-only"
    assert plan.prompt.ref == str(prompt)
    assert plan.prompt.sha256 == worker_spawn._hash_text("do research\n")
    assert plan.record_path == worker / ".ce/state/workers" / plan.worker_id / "worker.yaml"


def test_plan_rejects_unknown_role(tmp_path):
    _, worker = _worktrees(tmp_path)
    with pytest.raises(worker_spawn.InvalidWorkerRole):
        worker_spawn.plan_worker_spawn(
            role="foreman",
            harness="claude",
            worktree=worker,
            scope_id="ce-ops#163",
            brief="brief",
            environ={},
        )


def test_plan_rejects_unknown_harness(tmp_path):
    _, worker = _worktrees(tmp_path)
    with pytest.raises(worker_spawn.InvalidWorkerHarness):
        worker_spawn.plan_worker_spawn(
            role="implementer",
            harness="native-agent",
            worktree=worker,
            scope_id="ce-ops#163",
            brief="brief",
            environ={},
        )


def test_plan_rejects_same_worktree_as_parent(tmp_path):
    worker = tmp_path / "same"
    worker.mkdir()
    with pytest.raises(worker_spawn.InvalidWorkerWorktree):
        worker_spawn.plan_worker_spawn(
            role="implementer",
            harness="claude",
            worktree=worker,
            scope_id="ce-ops#163",
            brief="brief",
            parent_worktree=worker,
            environ={},
        )


def test_depth_bound_fails_closed(tmp_path):
    _, worker = _worktrees(tmp_path)
    with pytest.raises(worker_spawn.InvalidWorkerDepth):
        worker_spawn.plan_worker_spawn(
            role="implementer",
            harness="claude",
            worktree=worker,
            scope_id="ce-ops#163",
            brief="brief",
            depth=4,
            max_depth=3,
            environ={},
        )


def test_scrubbed_env_values_do_not_flow_to_record_or_child_env(tmp_path):
    parent, worker = _worktrees(tmp_path)
    env = {
        "PATH": "/bin",
        "GH_TOKEN": "ghp_super_secret",
        "GITHUB_TOKEN": "github_pat_secret",
        "MY_SERVICE_SECRET": "top-secret-value",
        "NORMAL_FLAG": "kept",
    }

    plan = worker_spawn.plan_worker_spawn(
        role="reviewer",
        harness="claude",
        worktree=worker,
        scope_id="ce-ops#163",
        brief="review this",
        parent_worktree=parent,
        environ=env,
    )
    record_text = yaml.safe_dump(plan.to_record(), sort_keys=True)

    assert "GH_TOKEN" in plan.scrubbed_env_names
    assert "GITHUB_TOKEN" in plan.scrubbed_env_names
    assert "MY_SERVICE_SECRET" in plan.scrubbed_env_names
    assert "GH_TOKEN" not in plan.child_env
    assert "GITHUB_TOKEN" not in plan.child_env
    assert "MY_SERVICE_SECRET" not in plan.child_env
    assert plan.child_env["NORMAL_FLAG"] == "kept"
    assert "ghp_super_secret" not in record_text
    assert "github_pat_secret" not in record_text
    assert "top-secret-value" not in record_text
    assert "review this" not in record_text


def test_dry_run_has_no_side_effect_and_does_not_call_launcher(tmp_path):
    parent, worker = _worktrees(tmp_path)
    launcher = FakeLauncher()

    result = worker_spawn.spawn_worker(
        role="implementer",
        harness="claude",
        worktree=worker,
        scope_id="ce-ops#163",
        brief="build it",
        dry_run=True,
        parent_worktree=parent,
        environ={},
        launcher=launcher,
    )

    assert result.written is False
    assert launcher.calls == []
    assert not result.record_path.exists()
    assert result.record["dry_run"] is True


def test_live_spawn_uses_injected_launcher_and_writes_value_free_record(tmp_path):
    parent, worker = _worktrees(tmp_path)
    launcher = FakeLauncher()
    env = {"GH_TOKEN": "ghp_super_secret", "PATH": "/bin"}

    result = worker_spawn.spawn_worker(
        role="verification",
        harness="claude",
        worktree=worker,
        scope_id="ce-ops#163",
        brief="verify it",
        parent_id="ce-dev-4",
        parent_worktree=parent,
        environ=env,
        launcher=launcher,
    )

    assert result.written is True
    assert len(launcher.calls) == 1
    assert "GH_TOKEN" not in launcher.calls[0].child_env
    record = yaml.safe_load(result.record_path.read_text(encoding="utf-8"))
    record_text = json.dumps(record, sort_keys=True)
    assert record["role"] == "verification"
    assert record["lane_kind"] == "audit"
    assert record["parent_id"] == "ce-dev-4"
    assert record["seat_refs"]["events_ref"]
    assert "ghp_super_secret" not in record_text
    assert "verify it" not in record_text
