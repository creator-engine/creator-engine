"""ce-ops#216 Unit 5 - one-shot Integrator MVP runner.

The runner wires the already-landed integrator primitives into one bounded belt
tick:

Search API poll -> repair-needed event -> deterministic conflict resolver ->
executor race guard -> unresolved-conflict escalation.

It is not an always-on daemon. The write boundary remains in Unit 3's executor;
this module imports that API lazily so branches based on main fail closed until
``forge.integrator_executor`` lands.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .deterministic_resolvers import ResolverResult, resolve_conflict
from .eviction_detection import (
    RepairNeededEvent,
    RepairPollResult,
    Transport,
    poll_repair_needed,
)
from .github_repo_config import GhRunner
from .integrator_escalation import (
    ControllerEscalationEvent,
    EscalationContext,
    escalate_unresolved_results,
)


class IntegratorRunnerError(Exception):
    """Bad runner inputs or a missing dependency."""


class IntegratorExecutorUnavailable(IntegratorRunnerError):
    """Raised when Unit 3's executor API is not present on this base."""


@dataclass(frozen=True)
class ConflictSnapshot:
    """One conflicted file snapshot provided by the write-authority adapter."""

    path: str
    conflicted_text: str
    context_files: Mapping[str, str] | None = None


@dataclass(frozen=True)
class RepairWorkItem:
    """Adapter-owned material needed to resolve and execute one repair event."""

    expected_base_sha: str
    conflicts: tuple[ConflictSnapshot, ...]
    executor_adapter: Any


class IntegratorRepairAdapter(Protocol):
    """Read/write seam owned by the caller, not by the runner."""

    def repair_work_item(self, event: RepairNeededEvent) -> RepairWorkItem:
        """Return conflict snapshots, base SHA, and Unit 3 executor adapter."""


@dataclass(frozen=True)
class RunnerResolutionPlan:
    """Test-friendly shape matching Unit 3's ``ResolutionPlan`` attributes."""

    resolver_result: ResolverResult
    expected_base_sha: str
    files: Mapping[str, str] | None = None


ExecuteRepair = Callable[[RepairNeededEvent, Any], Any]
PollRepairNeeded = Callable[..., RepairPollResult]
PlanFactory = Callable[[ResolverResult, str, Mapping[str, str] | None], Any]


@dataclass(frozen=True)
class IntegratorEventOutcome:
    """Secret-free outcome for one repair-needed event."""

    event: RepairNeededEvent
    resolver_results: tuple[ResolverResult, ...]
    execution_results: tuple[Any, ...]
    escalation_events: tuple[ControllerEscalationEvent, ...]
    status: str
    refusal_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event.to_dict(),
            "resolver_results": [result.to_dict() for result in self.resolver_results],
            "execution_results": [_to_dict(result) for result in self.execution_results],
            "escalation_events": [event.to_dict() for event in self.escalation_events],
            "status": self.status,
            "refusal_reason": self.refusal_reason,
        }


@dataclass(frozen=True)
class IntegratorRunResult:
    """Outcome for one bounded integrator belt tick."""

    poll: RepairPollResult
    outcomes: tuple[IntegratorEventOutcome, ...]

    @property
    def executed_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.status == "executed")

    @property
    def escalated_count(self) -> int:
        return sum(len(outcome.escalation_events) for outcome in self.outcomes)

    @property
    def refused_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.status == "refused")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_count": len(self.poll.events),
            "executed_count": self.executed_count,
            "escalated_count": self.escalated_count,
            "refused_count": self.refused_count,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "rate_limit": dict(self.poll.rate_limit or {}),
        }


def run_once(
    *,
    token: str,
    repair_adapter: IntegratorRepairAdapter,
    repo: str | None = None,
    org: str | None = None,
    transport: Transport | None = None,
    gh_runner: GhRunner | None = None,
    poller: PollRepairNeeded | None = None,
    execute_repair: ExecuteRepair | None = None,
    plan_factory: PlanFactory | None = None,
    detected_at: str | None = None,
) -> IntegratorRunResult:
    """Run one Search-API-backed integrator repair tick.

    The detector is the existing Unit 1 Search API poller. The executor is Unit
    3's race-guarded write boundary, loaded lazily unless tests inject it.
    """

    poll = (poller or poll_repair_needed)(
        token=token,
        transport=transport,
        gh_runner=gh_runner,
        repo=repo,
        org=org,
        detected_at=detected_at,
    )
    outcomes = tuple(
        _handle_event(
            event,
            repair_adapter=repair_adapter,
            execute_repair=execute_repair,
            plan_factory=plan_factory,
        )
        for event in poll.events
    )
    return IntegratorRunResult(poll=poll, outcomes=outcomes)


def _handle_event(
    event: RepairNeededEvent,
    *,
    repair_adapter: IntegratorRepairAdapter,
    execute_repair: ExecuteRepair | None,
    plan_factory: PlanFactory | None,
) -> IntegratorEventOutcome:
    if not _event_is_live_action_eligible(event):
        return IntegratorEventOutcome(
            event=event,
            resolver_results=(),
            execution_results=(),
            escalation_events=(),
            status="refused",
            refusal_reason="event_not_approved_green",
        )

    work = repair_adapter.repair_work_item(event)
    resolved_pairs = tuple((snapshot, _resolve(snapshot)) for snapshot in work.conflicts)
    resolver_results = tuple(result for _, result in resolved_pairs)
    unresolved = tuple(
        _escalatable_result(snapshot, result)
        for snapshot, result in resolved_pairs
        if not result.resolved
    )
    if unresolved:
        escalations = escalate_unresolved_results(
            unresolved,
            context=EscalationContext(repo=event.repo, pr_number=event.pr_number, head_ref=event.head_sha),
        )
        return IntegratorEventOutcome(
            event=event,
            resolver_results=resolver_results,
            execution_results=(),
            escalation_events=escalations,
            status="escalated",
            refusal_reason="resolver_unresolved",
        )

    resolved = tuple(result for result in resolver_results if result.resolved)
    if not resolved:
        return IntegratorEventOutcome(
            event=event,
            resolver_results=resolver_results,
            execution_results=(),
            escalation_events=(),
            status="refused",
            refusal_reason="no_mechanical_resolution",
        )

    batch_result, files = _batch_resolution(resolved)
    if batch_result.unresolved or not batch_result.resolved:
        return IntegratorEventOutcome(
            event=event,
            resolver_results=resolver_results,
            execution_results=(),
            escalation_events=(),
            status="refused",
            refusal_reason=batch_result.reason,
        )

    execute, make_plan = _executor_api(execute_repair=execute_repair, plan_factory=plan_factory)
    execution_results = (
        execute(
            event,
            make_plan(batch_result, work.expected_base_sha, files),
            adapter=work.executor_adapter,
        ),
    )
    refused = tuple(
        result for result in execution_results if getattr(result, "refusal_reason", None)
    )
    return IntegratorEventOutcome(
        event=event,
        resolver_results=resolver_results,
        execution_results=execution_results,
        escalation_events=(),
        status="refused" if refused else "executed",
        refusal_reason=getattr(refused[0], "refusal_reason", None) if refused else None,
    )


def _resolve(snapshot: ConflictSnapshot) -> ResolverResult:
    return resolve_conflict(
        snapshot.path,
        snapshot.conflicted_text,
        context_files=dict(snapshot.context_files or {}),
    )


def _escalatable_result(snapshot: ConflictSnapshot, result: ResolverResult) -> ResolverResult:
    if result.unresolved:
        return result
    return ResolverResult(
        resolver=result.reason or "unrecognized_conflict_family",
        applicable=True,
        resolved=False,
        unresolved=True,
        changed_paths=(snapshot.path,),
        reason=f"no deterministic mechanical resolver: {result.reason}",
        evidence=result.evidence,
    )


def _batch_resolution(results: tuple[ResolverResult, ...]) -> tuple[ResolverResult, dict[str, str] | None]:
    files: dict[str, str] = {}
    evidence: list[str] = [f"resolved_results={len(results)}"]
    resolver_names: list[str] = []
    changed_paths: list[str] = []
    for result in results:
        resolver_names.append(result.resolver)
        paths = tuple(result.changed_paths)
        changed_paths.extend(paths)
        if result.content is None or len(paths) != 1:
            return (
                ResolverResult(
                    resolver="integrator_runner_batch",
                    applicable=True,
                    resolved=False,
                    unresolved=True,
                    changed_paths=tuple(sorted(changed_paths)),
                    reason="resolved_result_missing_single_file_content",
                    evidence=tuple(evidence),
                ),
                None,
            )
        path = paths[0]
        if path in files:
            return (
                ResolverResult(
                    resolver="integrator_runner_batch",
                    applicable=True,
                    resolved=False,
                    unresolved=True,
                    changed_paths=tuple(sorted(set(changed_paths))),
                    reason="duplicate_resolved_path",
                    evidence=tuple((*evidence, f"path={path}")),
                ),
                None,
            )
        files[path] = result.content
    paths = tuple(sorted(files))
    resolver_summary = ",".join(sorted(set(resolver_names)))
    return (
        ResolverResult(
            resolver="integrator_runner_batch",
            applicable=True,
            resolved=True,
            unresolved=False,
            changed_paths=paths,
            reason="aggregated mechanical repair batch",
            evidence=tuple((*evidence, f"files={len(files)}", f"resolvers={resolver_summary}")),
            content=None,
        ),
        {path: files[path] for path in paths},
    )


def _event_is_live_action_eligible(event: RepairNeededEvent) -> bool:
    evidence = event.to_dict().get("evidence") or {}
    return bool(evidence.get("approved") is True and evidence.get("all_green") is True)


def _executor_api(
    *,
    execute_repair: ExecuteRepair | None,
    plan_factory: PlanFactory | None,
) -> tuple[Callable[..., Any], PlanFactory]:
    if execute_repair is not None:
        return execute_repair, plan_factory or _runner_plan
    try:
        from .integrator_executor import ResolutionPlan, execute_integrator_repair
    except ModuleNotFoundError as exc:
        raise IntegratorExecutorUnavailable(
            "forge.integrator_executor is not available on this base; rebase after "
            "ce216-executor-race-guard / PR #383 lands"
        ) from exc
    return execute_integrator_repair, lambda result, base_sha, files=None: ResolutionPlan(
        resolver_result=result,
        expected_base_sha=base_sha,
        files=files,
    )


def _runner_plan(
    result: ResolverResult,
    expected_base_sha: str,
    files: Mapping[str, str] | None = None,
) -> RunnerResolutionPlan:
    return RunnerResolutionPlan(resolver_result=result, expected_base_sha=expected_base_sha, files=files)


def _to_dict(value: Any) -> Any:
    method = getattr(value, "to_dict", None)
    if callable(method):
        return method()
    if isinstance(value, Mapping):
        return dict(value)
    return value
