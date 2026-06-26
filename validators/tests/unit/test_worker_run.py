"""Unit tests for the ce-ops#259 governed worker-run surface."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import worker_run, worker_spawn


class FakeLauncher:
    def __init__(self):
        self.calls = []

    def launch(self, plan):
        self.calls.append(plan)
        return worker_spawn.WorkerLaunchOutcome(
            spawned=True,
            attached=False,
            terminal={
                "kind": "tmux",
                "session_id": plan.worker_id,
                "window_id": "worker",
                "pane_id": "%77",
            },
            events_ref=f"{plan.worktree_path}/events.jsonl",
            seat_record_ref=f"{plan.worktree_path}/seat.yaml",
            seat_lifecycle_state="active",
        )


class FakeSeeder:
    def __init__(self):
        self.calls = []

    def seed(self, **kwargs):
        self.calls.append(kwargs)
        return worker_run.render_seed_instruction(
            prompt_path=kwargs["prompt_path"],
            findings_path=kwargs["findings_path"],
        )


class FakeCollector:
    def __init__(self):
        self.calls = []

    def collect(self, **kwargs):
        self.calls.append(kwargs)
        kwargs["findings_path"].write_text(
            yaml.safe_dump(
                {
                    "status": "completed",
                    "summary": "round trip complete",
                    "findings": [{"kind": "finding", "message": "mocked"}],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return worker_run.normalize_findings(kwargs["findings_path"])


def _repo_with_roles(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    roles = root / ".claude" / "agents"
    roles.mkdir(parents=True)
    (roles / "architect_research.md").write_text(
        "---\n"
        "name: architect_research\n"
        "description: Read-only research role\n"
        "tools: Read, Grep, Glob, WebFetch, WebSearch\n"
        "---\n"
        "# Architect Research\n\nReturn findings only.\n",
        encoding="utf-8",
    )
    (roles / "implementer.md").write_text(
        "---\n"
        "name: implementer\n"
        "tools:\n"
        "  - Read\n"
        "  - Edit\n"
        "---\n"
        "# Implementer\n",
        encoding="utf-8",
    )
    return root


def test_resolve_role_definition_reads_agent_front_matter(tmp_path):
    root = _repo_with_roles(tmp_path)

    role = worker_run.resolve_role_definition("architect_research", repo_root=root)

    assert role.name == "architect_research"
    assert role.path == root / ".claude/agents/architect_research.md"
    assert role.tools == ("Read", "Grep", "Glob", "WebFetch", "WebSearch")
    assert len(role.sha256) == 64


def test_resolve_role_definition_fails_closed_without_role(tmp_path):
    root = _repo_with_roles(tmp_path)

    with pytest.raises(worker_run.MissingWorkerRunRole):
        worker_run.resolve_role_definition("", repo_root=root)


def test_resolve_role_definition_fails_closed_for_unknown_role(tmp_path):
    root = _repo_with_roles(tmp_path)

    with pytest.raises(worker_run.UnknownWorkerRunRole):
        worker_run.resolve_role_definition("unbounded_harness", repo_root=root)


def test_run_worker_role_launch_to_findings_round_trip_is_mockable(tmp_path):
    root = _repo_with_roles(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("Inspect the worker-run seam.\n", encoding="utf-8")
    launcher = FakeLauncher()
    seeder = FakeSeeder()
    collector = FakeCollector()

    result = worker_run.run_worker_role(
        role="architect_research",
        brief=brief,
        repo_root=root,
        worktree=root,
        run_id="ce259-roundtrip",
        worker_id="ce259-worker",
        launcher=launcher,
        seeder=seeder,
        collector=collector,
        environ={"PATH": "/bin"},
    )

    assert result.run_id == "ce259-roundtrip"
    assert result.role.name == "architect_research"
    assert result.findings["status"] == "completed"
    assert result.findings["findings"] == [{"kind": "finding", "message": "mocked"}]
    assert len(launcher.calls) == 1
    assert launcher.calls[0].role == "architect_research"
    assert launcher.calls[0].lane_kind == "read-only"
    assert launcher.calls[0].prompt.ref == str(result.prompt_path)
    assert "Inspect the worker-run seam." in result.prompt_path.read_text(encoding="utf-8")
    assert len(seeder.calls) == 1
    assert seeder.calls[0]["prompt_path"] == result.prompt_path
    assert seeder.calls[0]["findings_path"] == result.findings_path
    instruction = worker_run.render_seed_instruction(
        prompt_path=result.prompt_path,
        findings_path=result.findings_path,
    )
    assert str(result.prompt_path) in instruction
    assert str(result.findings_path) in instruction
    assert len(collector.calls) == 1


def test_run_worker_role_fails_closed_when_seed_fails(tmp_path):
    root = _repo_with_roles(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("Inspect the worker-run seam.\n", encoding="utf-8")
    launcher = FakeLauncher()
    collector = FakeCollector()

    class FailingSeeder:
        def seed(self, **kwargs):
            raise worker_run.WorkerRunSeedFailed("seed unavailable")

    with pytest.raises(worker_run.WorkerRunSeedFailed):
        worker_run.run_worker_role(
            role="architect_research",
            brief=brief,
            repo_root=root,
            worktree=root,
            run_id="ce259-seed-fails",
            worker_id="ce259-worker-seed-fails",
            launcher=launcher,
            seeder=FailingSeeder(),
            collector=collector,
            environ={"PATH": "/bin"},
        )

    assert len(launcher.calls) == 1
    assert collector.calls == []


def test_tmux_prompt_seeder_refuses_without_pane(tmp_path):
    root = _repo_with_roles(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("Inspect the worker-run seam.\n", encoding="utf-8")
    collector = FakeCollector()

    class NoPaneLauncher(FakeLauncher):
        def launch(self, plan):
            outcome = super().launch(plan)
            return worker_spawn.WorkerLaunchOutcome(
                spawned=outcome.spawned,
                attached=outcome.attached,
                terminal={"kind": "tmux", "session_id": plan.worker_id},
                events_ref=outcome.events_ref,
                seat_record_ref=outcome.seat_record_ref,
                seat_lifecycle_state=outcome.seat_lifecycle_state,
            )

    launcher = NoPaneLauncher()
    with pytest.raises(worker_run.WorkerRunSeedFailed, match="pane_id"):
        worker_run.run_worker_role(
            role="architect_research",
            brief=brief,
            repo_root=root,
            worktree=root,
            run_id="ce259-no-pane",
            worker_id="ce259-worker-no-pane",
            launcher=launcher,
            seeder=worker_run.TmuxPromptSeeder(),
            collector=collector,
            environ={"PATH": "/bin"},
        )

    assert len(launcher.calls) == 1
    assert collector.calls == []
