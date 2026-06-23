"""Unit tests for ce-ops#216 Unit 3 integrator executor."""

from __future__ import annotations

from creator_engine_validator.forge import integrator_executor as ie
from creator_engine_validator.forge.deterministic_resolvers import ResolverResult
from creator_engine_validator.forge.eviction_detection import RepairNeededEvent

REPO = "creator-engine/creator-engine"
PR = 373
HEAD = "a" * 40
BASE = "b" * 40
PATH = "validators/creator_engine_validator/_versions.py"
CONTENT = 'V3_RUNTIME = frozenset({"forge.integrator_executor"})\n'


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


def _resolved_result(**overrides) -> ResolverResult:
    data = {
        "resolver": "versions_module_registry_union",
        "applicable": True,
        "resolved": True,
        "unresolved": False,
        "changed_paths": (PATH,),
        "reason": "unioned module registry entries from both sides",
        "evidence": ("V3_RUNTIME=52",),
        "content": CONTENT,
    }
    data.update(overrides)
    return ResolverResult(**data)


class FakeExecutorAdapter:
    def __init__(self, refs: list[ie.ExecutorRefs] | None = None):
        self.refs = list(refs or [ie.ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE)])
        self.ref_reads: list[tuple[str, int]] = []
        self.applied: list[dict[str, str]] = []
        self.published: list[tuple[str, int]] = []

    def current_refs(self, repo: str, pr_number: int) -> ie.ExecutorRefs:
        self.ref_reads.append((repo, pr_number))
        if not self.refs:
            raise AssertionError("unexpected extra current_refs call")
        return self.refs.pop(0)

    def apply_resolved_content(self, repo: str, pr_number: int, files: dict[str, str]) -> tuple[str, ...]:
        assert (repo, pr_number) == (REPO, PR)
        self.applied.append(dict(files))
        return tuple(sorted(files))

    def push_and_requeue(self, repo: str, pr_number: int) -> ie.ExecutorPublishResult:
        self.published.append((repo, pr_number))
        return ie.ExecutorPublishResult(
            pushed=True,
            requeued=True,
            evidence=("queue=integrator", "token=ghs_SECRET_SHOULD_NOT_LEAK"),
        )


def test_executor_applies_only_resolved_content_after_head_and_base_race_checks():
    adapter = FakeExecutorAdapter(
        refs=[
            ie.ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE),
            ie.ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE),
        ]
    )
    plan = ie.ResolutionPlan(resolver_result=_resolved_result(), expected_base_sha=BASE)

    result = ie.execute_integrator_repair(_event(), plan, adapter=adapter)

    assert result.accepted is True
    assert result.refusal_reason is None
    assert result.applied_paths == (PATH,)
    assert result.pushed is True
    assert result.requeued is True
    assert adapter.ref_reads == [(REPO, PR), (REPO, PR)]
    assert adapter.applied == [{PATH: CONTENT}]
    assert adapter.published == [(REPO, PR)]
    rendered = repr(result.to_dict())
    assert "ghs_SECRET" not in rendered
    assert "<redacted>" in rendered


def test_executor_accepts_explicit_multi_file_resolution_plan():
    adapter = FakeExecutorAdapter(
        refs=[
            ie.ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE),
            ie.ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE),
        ]
    )
    other_path = "validators/tests/unit/test_version_boundary.py"
    plan = ie.ResolutionPlan(
        resolver_result=_resolved_result(changed_paths=(PATH, other_path), content=None),
        expected_base_sha=BASE,
        files={PATH: CONTENT, other_path: "assert len(ver.V3_RUNTIME) == 52\n"},
    )

    result = ie.execute_integrator_repair(_event(), plan, adapter=adapter)

    assert result.accepted is True
    assert result.applied_paths == (PATH, other_path)
    assert adapter.applied == [{PATH: CONTENT, other_path: "assert len(ver.V3_RUNTIME) == 52\n"}]
    assert adapter.published == [(REPO, PR)]


def test_executor_refuses_unresolved_or_semantic_result_before_any_write_authority_call():
    adapter = FakeExecutorAdapter()
    plan = ie.ResolutionPlan(
        resolver_result=_resolved_result(resolved=False, unresolved=True, content=None),
        expected_base_sha=BASE,
    )

    result = ie.execute_integrator_repair(_event().to_dict(), plan, adapter=adapter)

    assert result.accepted is False
    assert result.refusal_reason == "resolver_unresolved"
    assert result.applied_paths == ()
    assert result.pushed is False
    assert result.requeued is False
    assert adapter.ref_reads == []
    assert adapter.applied == []
    assert adapter.published == []


def test_executor_refuses_resolved_result_without_file_content_before_write():
    adapter = FakeExecutorAdapter()
    plan = ie.ResolutionPlan(resolver_result=_resolved_result(content=None), expected_base_sha=BASE)

    result = ie.execute_integrator_repair(_event(), plan, adapter=adapter)

    assert result.accepted is False
    assert result.refusal_reason == "missing_resolved_content"
    assert adapter.ref_reads == []
    assert adapter.applied == []
    assert adapter.published == []


def test_executor_aborts_before_write_when_head_or_base_moved():
    adapter = FakeExecutorAdapter(refs=[ie.ExecutorRefs(pr_head_sha="c" * 40, base_sha=BASE)])
    plan = ie.ResolutionPlan(resolver_result=_resolved_result(), expected_base_sha=BASE)

    result = ie.execute_integrator_repair(_event(), plan, adapter=adapter)

    assert result.accepted is False
    assert result.refusal_reason == "race_guard_head_moved"
    assert result.evidence == (f"expected_head={HEAD}", f"actual_head={'c' * 40}")
    assert adapter.applied == []
    assert adapter.published == []

    adapter = FakeExecutorAdapter(refs=[ie.ExecutorRefs(pr_head_sha=HEAD, base_sha="d" * 40)])
    result = ie.execute_integrator_repair(_event(), plan, adapter=adapter)

    assert result.accepted is False
    assert result.refusal_reason == "race_guard_base_moved"
    assert result.evidence == (f"expected_base={BASE}", f"actual_base={'d' * 40}")
    assert adapter.applied == []
    assert adapter.published == []


def test_executor_rechecks_race_guard_after_write_and_before_push_requeue():
    adapter = FakeExecutorAdapter(
        refs=[
            ie.ExecutorRefs(pr_head_sha=HEAD, base_sha=BASE),
            ie.ExecutorRefs(pr_head_sha=HEAD, base_sha="e" * 40),
        ]
    )
    plan = ie.ResolutionPlan(resolver_result=_resolved_result(), expected_base_sha=BASE)

    result = ie.execute_integrator_repair(_event(), plan, adapter=adapter)

    assert result.accepted is False
    assert result.refusal_reason == "race_guard_base_moved_before_push"
    assert result.applied_paths == (PATH,)
    assert result.pushed is False
    assert result.requeued is False
    assert adapter.applied == [{PATH: CONTENT}]
    assert adapter.published == []
