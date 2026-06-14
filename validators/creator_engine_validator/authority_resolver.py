"""AuthorityResolver seam for CE v3 binding-plane decisions.

The resolver is deliberately thin in the RS-1 Dev lane: it delegates to the
existing binding gates and translates their existing outcomes into
``authorized`` / ``escalate`` verdicts. Advisory forge or board state may be
carried as context for observability, but it is never read to authorize.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from . import coordination

VerdictStatus = Literal["authorized", "escalate"]


@dataclass(frozen=True)
class Verdict:
    """Resolver verdict plus the existing gate result that callers already consume."""

    status: VerdictStatus
    reason: str
    value: Any = None

    @classmethod
    def authorized(cls, reason: str, value: Any) -> "Verdict":
        return cls("authorized", reason, value)

    @classmethod
    def escalate(cls, reason: str, value: Any = None) -> "Verdict":
        return cls("escalate", reason, value)


@dataclass(frozen=True)
class ScopeRatifyDecision:
    """Front-gate dispatch decision over a committed Scope and runtime policy."""

    scope: Any
    runtime_policy: dict[str, Any]
    advisory_context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanApprovalDecision:
    """Merge/readiness approval decision over the existing ``plan_approved`` gate."""

    query: Any
    seat_identity: str
    resolver: Callable[..., Any]
    gh_runner: Any = None
    authority: dict | None = None
    mutation_class: str | None = None
    changed_paths: Sequence[str] = ()
    advisory_context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MergeDecision:
    """Merge gate-read/apply decision over the existing merge composition."""

    gate_read: Callable[[], Any]
    advisory_context: Mapping[str, Any] = field(default_factory=dict)


AuthorityDecision = ScopeRatifyDecision | PlanApprovalDecision | MergeDecision


class AuthorityResolver(Protocol):
    """Resolve a binding-plane decision into an authorization verdict."""

    def resolve(self, decision: AuthorityDecision) -> Verdict:
        ...


class DevAuthorityResolver:
    """Dev mode: preserve today's per-act human gate exactly."""

    def resolve(self, decision: AuthorityDecision) -> Verdict:
        if isinstance(decision, ScopeRatifyDecision):
            return self._resolve_scope_ratify(decision)
        if isinstance(decision, PlanApprovalDecision):
            return self._resolve_plan_approval(decision)
        if isinstance(decision, MergeDecision):
            return self._resolve_merge(decision)
        raise TypeError(f"unsupported authority decision: {type(decision).__name__}")

    def _resolve_scope_ratify(self, decision: ScopeRatifyDecision) -> Verdict:
        result = coordination.assemble_dispatch(decision.scope, decision.runtime_policy)
        if isinstance(result, coordination.DispatchPlan):
            return Verdict.authorized("existing scope ratification gate accepted", result)
        return Verdict.escalate(result.reason, result)

    def _resolve_plan_approval(self, decision: PlanApprovalDecision) -> Verdict:
        result = decision.resolver(
            decision.query,
            seat_identity=decision.seat_identity,
            gh_runner=decision.gh_runner,
            authority=decision.authority,
            mutation_class=decision.mutation_class,
            changed_paths=decision.changed_paths,
        )
        if result is None:
            return Verdict.escalate("existing plan approval gate found no ratification", None)
        return Verdict.authorized("existing plan approval gate accepted", result)

    def _resolve_merge(self, decision: MergeDecision) -> Verdict:
        result = decision.gate_read()
        if bool(getattr(result, "would_merge", False) or getattr(result, "merged", False)):
            return Verdict.authorized("existing merge gate accepted", result)
        return Verdict.escalate("existing merge gate not satisfied", result)


DEV_AUTHORITY_RESOLVER = DevAuthorityResolver()
