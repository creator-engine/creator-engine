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
        assert plan.record_path.is_file()
        record = yaml.safe_load(plan.record_path.read_text(encoding="utf-8"))
        assert record["launch_state"] == "reserved"
        assert record["seat_refs"] == {}
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


def test_clean_child_env_is_allowlisted_and_uses_isolated_home(tmp_path):
    parent, worker = _worktrees(tmp_path)
    controller_home = tmp_path / "controller-home"
    (controller_home / ".config" / "gh").mkdir(parents=True)
    (controller_home / ".ssh").mkdir()
    env = {
        "PATH": "/bin",
        "TERM": "xterm-256color",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TMPDIR": str(tmp_path / "tmp"),
        "HOME": str(controller_home),
        "GH_CONFIG_DIR": str(controller_home / ".config" / "gh"),
        "SSH_AUTH_SOCK": str(controller_home / ".ssh" / "agent.sock"),
        "GIT_SSH_COMMAND": f"ssh -F {controller_home / '.ssh' / 'config'}",
        "AWS_CONFIG_FILE": str(controller_home / ".aws" / "config"),
        "GOOGLE_APPLICATION_CREDENTIALS": str(controller_home / "gcp.json"),
        "GH_TOKEN": "ghp_super_secret",
        "GITHUB_TOKEN": "github_pat_secret",
        "MY_SERVICE_SECRET": "top-secret-value",
        "NORMAL_FLAG": "not-allowlisted",
    }
    (tmp_path / "tmp").mkdir()

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
    assert "HOME" in plan.scrubbed_env_names
    assert "GH_CONFIG_DIR" in plan.scrubbed_env_names
    assert "SSH_AUTH_SOCK" in plan.scrubbed_env_names
    assert "GIT_SSH_COMMAND" in plan.scrubbed_env_names
    assert "AWS_CONFIG_FILE" in plan.scrubbed_env_names
    assert "GOOGLE_APPLICATION_CREDENTIALS" in plan.scrubbed_env_names
    assert "NORMAL_FLAG" in plan.scrubbed_env_names
    assert "GH_TOKEN" not in plan.child_env
    assert "GITHUB_TOKEN" not in plan.child_env
    assert "MY_SERVICE_SECRET" not in plan.child_env
    assert "GH_CONFIG_DIR" not in plan.child_env
    assert "SSH_AUTH_SOCK" not in plan.child_env
    assert "GIT_SSH_COMMAND" not in plan.child_env
    assert "AWS_CONFIG_FILE" not in plan.child_env
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in plan.child_env
    assert "NORMAL_FLAG" not in plan.child_env
    assert plan.child_env["PATH"] == "/bin"
    assert plan.child_env["TERM"] == "xterm-256color"
    assert plan.child_env["LC_ALL"] == "C.UTF-8"
    assert plan.child_env["TMPDIR"] == str(tmp_path / "tmp")
    assert plan.child_env["HOME"] != str(controller_home)
    worker_home = Path(plan.child_env["HOME"])
    assert worker_home.is_relative_to(worker)
    worker_home.mkdir(parents=True)
    assert "ghp_super_secret" not in record_text
    assert "github_pat_secret" not in record_text
    assert "top-secret-value" not in record_text
    assert str(controller_home / ".config" / "gh") not in record_text
    assert str(controller_home / ".ssh" / "agent.sock") not in record_text
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
    assert Path(launcher.calls[0].child_env["HOME"]).is_dir()
    record = yaml.safe_load(result.record_path.read_text(encoding="utf-8"))
    record_text = json.dumps(record, sort_keys=True)
    assert record["role"] == "verification"
    assert record["lane_kind"] == "audit"
    assert record["parent_id"] == "ce-dev-4"
    assert record["launch_state"] == "launched"
    assert record["seat_refs"]["events_ref"]
    assert "ghp_super_secret" not in record_text
    assert "verify it" not in record_text


def test_existing_record_collision_fails_before_launcher(tmp_path):
    parent, worker = _worktrees(tmp_path)
    launcher = FakeLauncher()
    existing = worker / ".ce/state/workers/fixed-worker/worker.yaml"
    existing.parent.mkdir(parents=True)
    existing.write_text("launch_state: reserved\n", encoding="utf-8")

    with pytest.raises(worker_spawn.WorkerRecordCollision):
        worker_spawn.spawn_worker(
            role="implementer",
            harness="claude",
            worktree=worker,
            scope_id="ce-ops#163",
            brief="build it",
            parent_worktree=parent,
            environ={},
            worker_id="fixed-worker",
            launcher=launcher,
        )

    assert launcher.calls == []


def test_prelaunch_record_reservation_failure_fails_before_launcher(tmp_path, monkeypatch):
    parent, worker = _worktrees(tmp_path)
    launcher = FakeLauncher()

    def fail_reserve(path, payload):
        raise worker_spawn.WorkerRecordReservationFailed("synthetic reservation failure")

    monkeypatch.setattr(worker_spawn, "_reserve_worker_record", fail_reserve)

    with pytest.raises(worker_spawn.WorkerRecordReservationFailed):
        worker_spawn.spawn_worker(
            role="implementer",
            harness="claude",
            worktree=worker,
            scope_id="ce-ops#163",
            brief="build it",
            parent_worktree=parent,
            environ={},
            launcher=launcher,
        )

    assert launcher.calls == []


def test_default_launcher_passes_clean_env_and_pinned_cwd_to_launch_runtime(tmp_path, monkeypatch):
    parent, worker = _worktrees(tmp_path)
    captured = {}

    class FakeLaunchPlan:
        def to_dict(self):
            return {"harness": "claude"}

    class FakeLaunchResult:
        spawned = True
        attached = False
        plan = FakeLaunchPlan()
        terminal = {"kind": "tmux"}
        events_ref = "events.jsonl"
        seat_record_ref = "seat.yaml"
        seat_lifecycle_state = "active"

    def fake_launch(**kwargs):
        captured.update(kwargs)
        return FakeLaunchResult()

    monkeypatch.setattr(worker_spawn.launch_runtime, "launch", fake_launch)

    result = worker_spawn.spawn_worker(
        role="implementer",
        harness="claude",
        worktree=worker,
        scope_id="ce-ops#163",
        brief="build it",
        parent_worktree=parent,
        environ={
            "PATH": "/bin",
            "HOME": str(tmp_path / "controller-home"),
            "GH_CONFIG_DIR": str(tmp_path / "controller-home" / ".config" / "gh"),
            "SSH_AUTH_SOCK": str(tmp_path / "agent.sock"),
            "GH_TOKEN": "ghp_super_secret",
        },
    )

    assert result.written is True
    assert captured["repo_root"] == worker.resolve()
    assert captured["launch_cwd"] == worker.resolve()
    assert captured["launch_env"]["PATH"] == "/bin"
    assert captured["launch_env"]["HOME"] == str(worker / ".ce/state/workers" / result.plan.worker_id / "home")
    assert "GH_CONFIG_DIR" not in captured["launch_env"]
    assert "SSH_AUTH_SOCK" not in captured["launch_env"]
    assert "GH_TOKEN" not in captured["launch_env"]
