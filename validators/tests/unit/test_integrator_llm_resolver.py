"""Unit tests for ce-ops#216 Integrator Phase-2 LLM resolver."""

from __future__ import annotations

from dataclasses import dataclass

from creator_engine_validator.forge import integrator_runner as ir
from creator_engine_validator.forge.eviction_detection import RepairNeededEvent, RepairPollResult
from creator_engine_validator.forge.integrator_llm_resolver import (
    LLMConflictInput,
    LLMRepairArtifact,
    conflict_input_from_text,
    resolve_conflict_text_with_llm,
    resolve_with_llm,
)

REPO = "creator-engine/creator-engine"
PR = 216
HEAD = "a" * 40
BASE = "b" * 40
PATH = "src/app.py"
CONFLICT = """def value():
<<<<<<< ours
    return "ours"
=======
    return "theirs"
>>>>>>> theirs
"""
RESOLVED = 'def value():\n    return "merged"\n'


class StubLLMClient:
    def __init__(self, artifact: LLMRepairArtifact):
        self.artifact = artifact
        self.calls: list[tuple[LLMConflictInput, bool]] = []

    def resolve_conflict(self, conflict: LLMConflictInput, *, read_only: bool) -> LLMRepairArtifact:
        assert read_only is True
        self.calls.append((conflict, read_only))
        return self.artifact


class BadReadOnlyClient:
    def resolve_conflict(self, conflict: LLMConflictInput, *, read_only: bool) -> LLMRepairArtifact:
        raise AssertionError("client should not be able to request write authority")


def _artifact(**overrides) -> LLMRepairArtifact:
    data = {
        "resolved_content": RESOLVED,
        "confidence": 0.82,
        "rationale": "merged both semantic branches",
        "resolution_type": "llm_resolved",
    }
    data.update(overrides)
    return LLMRepairArtifact(**data)


def test_happy_path_returns_resolved_artifact_from_structured_conflict_input():
    client = StubLLMClient(_artifact())

    artifact = resolve_conflict_text_with_llm(path=PATH, conflicted_text=CONFLICT, client=client)

    assert artifact == _artifact()
    assert len(client.calls) == 1
    conflict, read_only = client.calls[0]
    assert read_only is True
    assert conflict.path == PATH
    assert conflict.ours_content == 'def value():\n    return "ours"\n'
    assert conflict.theirs_content == 'def value():\n    return "theirs"\n'
    assert conflict.conflict_markers == ("<<<<<<< ours", "=======", ">>>>>>> theirs")


def test_escalate_path_returns_empty_content_and_unresolved_result():
    client = StubLLMClient(
        _artifact(
            resolved_content="proposed content must be discarded",
            confidence=0.7,
            rationale="semantic risk",
            resolution_type="escalate",
        )
    )

    artifact = resolve_conflict_text_with_llm(path=PATH, conflicted_text=CONFLICT, client=client)

    assert artifact.resolved_content == ""
    assert artifact.resolution_type == "escalate"


def test_confidence_below_threshold_triggers_escalate_without_content_proposal():
    client = StubLLMClient(_artifact(confidence=0.49))

    artifact = resolve_conflict_text_with_llm(path=PATH, conflicted_text=CONFLICT, client=client)

    assert artifact.resolution_type == "escalate"
    assert artifact.resolved_content == ""
    assert artifact.confidence == 0.49
    assert "confidence below" in artifact.rationale


def test_read_only_assertion_is_enforced_before_client_call():
    conflict = conflict_input_from_text(path=PATH, conflicted_text=CONFLICT)

    try:
        resolve_with_llm(conflict, client=BadReadOnlyClient())
    except AssertionError as exc:
        assert "write authority" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("stub should have observed enforced read_only=True")


@dataclass(frozen=True)
class FakeExecutionResult:
    accepted: bool = True
    refusal_reason: str | None = None

    def to_dict(self) -> dict:
        return {"accepted": self.accepted, "refusal_reason": self.refusal_reason}


class FakeRepairAdapter:
    def __init__(self, conflict: ir.ConflictSnapshot):
        self.conflict = conflict
        self.executor_adapter = object()

    def repair_work_item(self, event: RepairNeededEvent) -> ir.RepairWorkItem:
        return ir.RepairWorkItem(
            expected_base_sha=BASE,
            conflicts=(self.conflict,),
            executor_adapter=self.executor_adapter,
        )


def _event() -> RepairNeededEvent:
    return RepairNeededEvent(
        repo=REPO,
        pr_number=PR,
        head_sha=HEAD,
        merge_state_status="DIRTY",
        mergeable="MERGEABLE",
        reason="dirty",
        review_decision="APPROVED",
        rollup_state="SUCCESS",
    )


def _poller(*, token, **_kwargs):
    return RepairPollResult(events=(_event(),), rate_limit={"remaining": 1})


def test_runner_passes_llm_resolution_to_executor_only_when_not_escalate():
    client = StubLLMClient(_artifact(resolution_type="mechanical_assist"))
    adapter = FakeRepairAdapter(ir.ConflictSnapshot(path=PATH, conflicted_text=CONFLICT))
    calls = []

    def execute(event, plan, *, adapter):
        calls.append((event, plan, adapter))
        assert plan.resolver_result.resolver == "integrator_runner_batch"
        assert plan.files == {PATH: RESOLVED}
        return FakeExecutionResult()

    result = ir.run_once(
        token="ghp_fake",
        repair_adapter=adapter,
        poller=_poller,
        execute_repair=execute,
        llm_client=client,
    )

    assert result.executed_count == 1
    assert result.escalated_count == 0
    assert len(calls) == 1


def test_runner_escalates_llm_escalate_artifact_without_executing():
    client = StubLLMClient(_artifact(resolved_content="ignored", resolution_type="escalate"))
    adapter = FakeRepairAdapter(ir.ConflictSnapshot(path=PATH, conflicted_text=CONFLICT))

    def execute(_event, _plan, *, adapter):  # pragma: no cover - must not be called
        raise AssertionError("escalated LLM artifact must not execute")

    result = ir.run_once(
        token="ghp_fake",
        repair_adapter=adapter,
        poller=_poller,
        execute_repair=execute,
        llm_client=client,
    )

    assert result.executed_count == 0
    assert result.escalated_count == 1
    assert result.outcomes[0].status == "escalated"
