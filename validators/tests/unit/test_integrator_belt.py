"""Offline tests for the Integrator merge-queue belt poller."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creator_engine_validator import v3_cli
from creator_engine_validator.forge import integrator_belt as belt
from creator_engine_validator.forge.eviction_detection import RepairNeededEvent, RepairPollResult
from creator_engine_validator.forge.integrator_executor import ExecutorPublishResult, ExecutorRefs
from creator_engine_validator.forge.integrator_runner import ConflictSnapshot, RepairWorkItem

REPO = "creator-engine/creator-engine"
PR = 218
HEAD = "a" * 40
BASE = "b" * 40
_OURS = "<" * 7 + " ours"
_SEP = "=" * 7
_THEIRS = ">" * 7 + " theirs"


def _event(**overrides) -> RepairNeededEvent:
    data = {
        "repo": REPO,
        "pr_number": PR,
        "head_sha": HEAD,
        "merge_state_status": "DIRTY",
        "mergeable": "CONFLICTING",
        "reason": "dirty",
        "review_decision": "APPROVED",
        "rollup_state": "SUCCESS",
    }
    data.update(overrides)
    return RepairNeededEvent(**data)


def _append_conflict() -> str:
    return f"""existing
{_OURS}
beta
{_SEP}
alpha
{_THEIRS}
tail
"""


def _semantic_conflict() -> str:
    return f"""{{"lockfileVersion": 3,
{_OURS}
"packages": {{}}
{_SEP}
"dependencies": {{}}
{_THEIRS}
}}
"""


class FakeBeltAdapter:
    def __init__(self, conflicts: tuple[ConflictSnapshot, ...]):
        self.conflicts = conflicts
        self.applied: dict[str, str] = {}
        self.published = 0

    def repair_work_item(self, event: RepairNeededEvent) -> RepairWorkItem:
        return RepairWorkItem(
            expected_base_sha=BASE,
            conflicts=self.conflicts,
            executor_adapter=self,
        )

    def current_refs(self, repo: str, pr_number: int) -> ExecutorRefs:
        return ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE)

    def apply_resolved_content(self, repo: str, pr_number: int, files: dict[str, str]) -> tuple[str, ...]:
        self.applied.update(files)
        return tuple(sorted(files))

    def push_and_requeue(self, repo: str, pr_number: int) -> ExecutorPublishResult:
        self.published += 1
        return ExecutorPublishResult(pushed=True, requeued=True, evidence=("fake_requeue=true",))


def _poller(*, token, **_kwargs):
    assert token == "ghp_fake"
    return RepairPollResult(events=(_event(),), rate_limit={"remaining": 9})


def test_poll_loop_detects_resolves_executes_and_logs():
    adapter = FakeBeltAdapter(
        (
            ConflictSnapshot(
                path=".ce/registries/integrator-append.txt",
                conflicted_text=_append_conflict(),
            ),
        )
    )
    logs: list[dict] = []

    result = belt.run_poll_loop(
        token="ghp_fake",
        repair_adapter=adapter,
        repo=REPO,
        iterations=1,
        interval_seconds=0,
        poller=_poller,
        log_sink=lambda payload: logs.append(dict(payload)),
    )

    assert result.event_count == 1
    assert result.executed_count == 1
    assert result.escalated_count == 0
    assert result.refused_count == 0
    assert adapter.applied[".ce/registries/integrator-append.txt"] == "existing\nalpha\nbeta\ntail\n"
    assert adapter.published == 1
    assert [entry["action"] for entry in logs] == ["poll_start", "poll_complete", "event_outcome"]


def test_poll_loop_refuses_unscoped_fail_closed():
    # ce-ops#218 review: a live merge-queue belt must NOT poll/act across every PR a
    # token can see. run_poll_loop fails closed when neither repo nor org is scoped.
    adapter = FakeBeltAdapter(())
    raised = None
    try:
        belt.run_poll_loop(
            token="ghp_fake",
            repair_adapter=adapter,
            iterations=1,
            interval_seconds=0,
            poller=_poller,
        )
    except belt.IntegratorBeltError as exc:
        raised = exc
    assert raised is not None and "unscoped" in str(raised)
    assert adapter.published == 0

def test_live_action_runner_refuses_semantic_conflict_without_execute(tmp_path: Path):
    adapter = FakeBeltAdapter(
        (
            ConflictSnapshot(
                path="package-lock.json",
                conflicted_text=_semantic_conflict(),
            ),
        )
    )
    runner = belt.make_live_action_runner(
        action="enqueue",
        token="ghp_fake",
        repo=REPO,
        poller=_poller,
        repair_adapter=adapter,
    )

    result = runner(
        belt.LiveActionRequest(
            action="enqueue",
            request=tmp_path / "request.yaml",
            preview_root=tmp_path / "preview",
            repo_root=None,
            preview_id="preview-1",
        )
    )

    assert result.accepted is False
    assert result.refusal_reason == "integrator_belt_refused"
    assert "executed=0" in result.evidence
    assert "escalated=1" in result.evidence
    assert adapter.applied == {}
    assert adapter.published == 0


@dataclass(frozen=True)
class _CliResult:
    event_count: int = 0
    executed_count: int = 0
    escalated_count: int = 0
    refused_count: int = 0

    def to_dict(self) -> dict:
        return {
            "event_count": self.event_count,
            "executed_count": self.executed_count,
            "escalated_count": self.escalated_count,
            "refused_count": self.refused_count,
            "ticks": [],
        }


def test_ce_queue_poll_cli_is_bounded_and_json(monkeypatch, capsys):
    captured = {}

    monkeypatch.setattr(v3_cli.integrator_belt, "token_from_env", lambda name: "ghp_fake")
    monkeypatch.setattr(v3_cli.integrator_belt, "gh_runner_with_token", lambda token: object())
    monkeypatch.setattr(v3_cli.integrator_belt, "git_env_with_token", lambda token: {})
    monkeypatch.setattr(v3_cli.integrator_belt, "LiveGitHubRepairAdapter", lambda **kwargs: object())

    def fake_loop(**kwargs):
        captured.update(kwargs)
        return _CliResult()

    monkeypatch.setattr(v3_cli.integrator_belt, "run_poll_loop", fake_loop)

    ret = v3_cli.main([
        "queue-poll",
        "--repo", REPO,
        "--iterations", "1",
        "--interval-seconds", "0",
        "--json",
    ])

    assert ret == 0
    assert captured["token"] == "ghp_fake"
    assert captured["repo"] == REPO
    assert captured["iterations"] == 1
    assert '"event_count": 0' in capsys.readouterr().out
