"""Unit tests for ce-ops#216 Unit 5 integrator runner."""

from __future__ import annotations

import builtins
from dataclasses import dataclass

import pytest

from creator_engine_validator.forge import integrator_runner as ir
from creator_engine_validator.forge.eviction_detection import RepairNeededEvent, RepairPollResult

REPO = "creator-engine/creator-engine"
PR = 216
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
        "mergeable": "MERGEABLE",
        "reason": "dirty",
        "review_decision": "APPROVED",
        "rollup_state": "SUCCESS",
    }
    data.update(overrides)
    return RepairNeededEvent(**data)


def _versions_conflict() -> str:
    return f'''from __future__ import annotations
V1_RUNTIME = frozenset({{
    "lane_runtime",
{_OURS}
    "ce_profile_path",
{_SEP}
    "ce_provenance",
{_THEIRS}
}})
V3_RUNTIME = frozenset({{
    "forge",
{_OURS}
    "forge.re_review",
{_SEP}
    "forge.user_install_discovery",
{_THEIRS}
}})
'''


def _append_only_conflict() -> str:
    return f"""existing
{_OURS}
beta
{_SEP}
alpha
{_THEIRS}
tail
"""


class FakeRepairAdapter:
    def __init__(self, conflicts: tuple[ir.ConflictSnapshot, ...]):
        self.conflicts = conflicts
        self.events: list[RepairNeededEvent] = []
        self.executor_adapter = object()

    def repair_work_item(self, event: RepairNeededEvent) -> ir.RepairWorkItem:
        self.events.append(event)
        return ir.RepairWorkItem(
            expected_base_sha=BASE,
            conflicts=self.conflicts,
            executor_adapter=self.executor_adapter,
        )


@dataclass(frozen=True)
class FakeExecutionResult:
    accepted: bool = True
    refusal_reason: str | None = None
    pushed: bool = True
    requeued: bool = True

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "refusal_reason": self.refusal_reason,
            "pushed": self.pushed,
            "requeued": self.requeued,
        }


def _poller(*, token, **_kwargs):
    assert token == "ghp_fake"
    return RepairPollResult(events=(_event(),), rate_limit={"remaining": 42})


def test_poll_detect_resolve_execute_happy_path():
    adapter = FakeRepairAdapter(
        (
            ir.ConflictSnapshot(
                path="validators/creator_engine_validator/_versions.py",
                conflicted_text=_versions_conflict(),
            ),
        )
    )
    calls = []

    def execute(event, plan, *, adapter):
        calls.append((event, plan, adapter))
        assert plan.expected_base_sha == BASE
        assert plan.resolver_result.resolved is True
        assert plan.resolver_result.content is None
        assert set(plan.files or {}) == set(plan.resolver_result.changed_paths)
        return FakeExecutionResult()

    result = ir.run_once(
        token="ghp_fake",
        repair_adapter=adapter,
        poller=_poller,
        execute_repair=execute,
    )

    assert result.executed_count == 1
    assert result.escalated_count == 0
    assert result.refused_count == 0
    assert result.outcomes[0].status == "executed"
    assert adapter.events == [_event()]
    assert len(calls) == 1
    assert calls[0][2] is adapter.executor_adapter


def test_multi_file_mechanical_repair_executes_as_one_atomic_batch():
    append_path = ".ce/registries/append-only.txt"
    adapter = FakeRepairAdapter(
        (
            ir.ConflictSnapshot(
                path="validators/creator_engine_validator/_versions.py",
                conflicted_text=_versions_conflict(),
            ),
            ir.ConflictSnapshot(
                path=append_path,
                conflicted_text=_append_only_conflict(),
            ),
        )
    )
    calls = []

    def execute(event, plan, *, adapter):
        calls.append((event, plan, adapter))
        assert plan.expected_base_sha == BASE
        assert plan.resolver_result.resolver == "integrator_runner_batch"
        assert plan.resolver_result.changed_paths == (
            ".ce/registries/append-only.txt",
            "validators/creator_engine_validator/_versions.py",
        )
        assert set(plan.files or {}) == set(plan.resolver_result.changed_paths)
        assert plan.files[append_path] == "existing\nalpha\nbeta\ntail\n"
        return FakeExecutionResult()

    result = ir.run_once(
        token="ghp_fake",
        repair_adapter=adapter,
        poller=_poller,
        execute_repair=execute,
    )

    assert result.executed_count == 1
    assert result.refused_count == 0
    assert len(calls) == 1
    assert calls[0][2] is adapter.executor_adapter


def test_semantic_conflict_escalates_and_does_not_execute():
    adapter = FakeRepairAdapter(
        (
            ir.ConflictSnapshot(
                path="package-lock.json",
                conflicted_text=(
                    '{"lockfileVersion": 3,\n'
                    f"{_OURS}\n"
                    '"packages": {}\n'
                    f"{_SEP}\n"
                    '"dependencies": {}\n'
                    f"{_THEIRS}\n"
                    "}\n"
                ),
            ),
        )
    )

    def execute(_event, _plan, *, adapter):  # pragma: no cover - must not be called
        raise AssertionError("semantic conflict must not execute")

    result = ir.run_once(
        token="ghp_fake",
        repair_adapter=adapter,
        poller=_poller,
        execute_repair=execute,
    )

    assert result.executed_count == 0
    assert result.escalated_count == 1
    outcome = result.outcomes[0]
    assert outcome.status == "escalated"
    assert outcome.refusal_reason == "resolver_unresolved"
    assert outcome.execution_results == ()
    assert outcome.escalation_events[0].repo == REPO
    assert outcome.escalation_events[0].pr_number == PR


def test_unrecognized_conflict_family_escalates_instead_of_parking():
    adapter = FakeRepairAdapter(
        (
            ir.ConflictSnapshot(
                path="src/app.py",
                conflicted_text=f"{_OURS}\nx\n{_SEP}\ny\n{_THEIRS}\n",
            ),
        )
    )

    def execute(_event, _plan, *, adapter):  # pragma: no cover - must not be called
        raise AssertionError("unrecognized conflict must not execute")

    result = ir.run_once(
        token="ghp_fake",
        repair_adapter=adapter,
        poller=_poller,
        execute_repair=execute,
    )

    assert result.executed_count == 0
    assert result.escalated_count == 1
    outcome = result.outcomes[0]
    assert outcome.status == "escalated"
    assert outcome.escalation_events[0].paths == ("src/app.py",)
    assert "no deterministic mechanical resolver" in outcome.escalation_events[0].resolver_reason


def test_live_actions_stay_gated_fail_closed_when_event_is_not_approved_green():
    adapter = FakeRepairAdapter(
        (
            ir.ConflictSnapshot(
                path="validators/creator_engine_validator/_versions.py",
                conflicted_text=_versions_conflict(),
            ),
        )
    )

    def poller(*, token, **_kwargs):
        return RepairPollResult(events=(_event(review_decision="CHANGES_REQUESTED"),))

    def execute(_event, _plan, *, adapter):  # pragma: no cover - must not be called
        raise AssertionError("not-approved event must not execute")

    result = ir.run_once(
        token="ghp_fake",
        repair_adapter=adapter,
        poller=poller,
        execute_repair=execute,
    )

    assert result.executed_count == 0
    assert result.refused_count == 1
    assert result.outcomes[0].status == "refused"
    assert result.outcomes[0].refusal_reason == "event_not_approved_green"
    assert adapter.events == []


def test_missing_executor_dependency_is_precise_when_not_injected(monkeypatch):
    adapter = FakeRepairAdapter(
        (
            ir.ConflictSnapshot(
                path="validators/creator_engine_validator/_versions.py",
                conflicted_text=_versions_conflict(),
            ),
        )
    )
    real_import = builtins.__import__

    def missing_executor_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 1 and name == "integrator_executor":
            raise ModuleNotFoundError("simulated missing Unit 3 executor")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", missing_executor_import)

    with pytest.raises(ir.IntegratorExecutorUnavailable, match="PR #383"):
        ir.run_once(token="ghp_fake", repair_adapter=adapter, poller=_poller)
