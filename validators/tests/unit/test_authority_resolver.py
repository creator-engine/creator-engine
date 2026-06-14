"""Unit tests for the ce-ops#34 AuthorityResolver seam."""

from __future__ import annotations

from types import SimpleNamespace

from creator_engine_validator import authority_resolver as ar
from creator_engine_validator import coordination
from creator_engine_validator.orchestrator import ApprovedPlan

_POLICY_SHA = "a" * 64


def _scope(**overrides):
    base = {
        "kind": "scope-record",
        "record_type": "scope",
        "schema_version": "1",
        "scope_id": "demo-scope",
        "intent": "do the thing",
        "acceptance_criteria": ["it works"],
        "appetite": {"amount": 12.0, "unit": "$"},
        "mutation_class": "code",
        "ratification": {"approver_ref": "b" * 64, "ratified_scope_sha": "c" * 64},
    }
    base.update(overrides)
    return base


def test_dev_resolver_authorizes_existing_scope_dispatch_result():
    resolver = ar.DevAuthorityResolver()
    verdict = resolver.resolve(ar.ScopeRatifyDecision(scope=_scope(), runtime_policy={}))
    direct = coordination.assemble_dispatch(_scope(), {})
    assert verdict.status == "authorized"
    assert verdict.value == direct


def test_dev_resolver_authorizes_existing_plan_approval_result():
    plan = ApprovedPlan(
        run_id="run-1",
        policy_sha=_POLICY_SHA,
        approved_by="operator",
        approval_ref="forge#1",
    )

    def existing_gate(query, **kwargs):
        return plan

    verdict = ar.DevAuthorityResolver().resolve(
        ar.PlanApprovalDecision(query=object(), seat_identity="seat", resolver=existing_gate)
    )
    assert verdict.status == "authorized"
    assert verdict.value is plan


def test_dev_resolver_authorizes_existing_merge_gate_result():
    result = SimpleNamespace(would_merge=True, merged=False)
    verdict = ar.DevAuthorityResolver().resolve(ar.MergeDecision(gate_read=lambda: result))
    assert verdict.status == "authorized"
    assert verdict.value is result


def test_rs3_hostile_forge_context_cannot_authorize_any_dev_verdict():
    hostile = {
        "board_label": "ready",
        "labels": ["auto-ok", "ready"],
        "context": {"auto-ok": True, "ready": True},
    }
    resolver = ar.DevAuthorityResolver()

    scope_verdict = resolver.resolve(
        ar.ScopeRatifyDecision(
            scope=_scope(ratification=None),
            runtime_policy={},
            advisory_context=hostile,
        )
    )

    plan_verdict = resolver.resolve(
        ar.PlanApprovalDecision(
            query=object(),
            seat_identity="seat",
            resolver=lambda query, **kwargs: None,
            advisory_context=hostile,
        )
    )

    merge_result = SimpleNamespace(would_merge=False, merged=False)
    merge_verdict = resolver.resolve(
        ar.MergeDecision(gate_read=lambda: merge_result, advisory_context=hostile)
    )

    assert scope_verdict.status == "escalate"
    assert isinstance(scope_verdict.value, coordination.DispatchRefusal)
    assert scope_verdict.value.reason == "not_ratified"
    assert plan_verdict == ar.Verdict.escalate(
        "existing plan approval gate found no ratification", None
    )
    assert merge_verdict.status == "escalate"
    assert merge_verdict.value is merge_result
