"""RV1-061 — governed-environment guard predicate (strict refusal-TDD).

These exercise the pure guard evaluator over injected
:class:`EnvironmentFacts`, one RED case per ungoverned-host clause defined in
``docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md`` §2/§4
(RED-G-1 .. RED-G-6). The evaluator is deterministic and side-effect-free so
``ce doctor`` can call it offline.
"""
from __future__ import annotations

import pytest

from creator_engine_validator import environment_guard as guard
from creator_engine_validator.packaging_runtime import PackagingContractResult


def _clean_packaging() -> PackagingContractResult:
    return PackagingContractResult(ok=True, violations=[], details={})


def _governed_facts(**overrides) -> guard.EnvironmentFacts:
    base = dict(
        version_info=(3, 14, 5),
        repo_root_is_git=True,
        hermes_ignored=True,
        tmux_available=True,
        podman_available=True,
        podman_rootless=True,
        uv_available=True,
        packaging=_clean_packaging(),
        hidden_continuation=False,
        active_work_ledger_present=True,
    )
    base.update(overrides)
    return guard.EnvironmentFacts(**base)


def _refusal_clauses(result: guard.GuardResult) -> set[str]:
    return {c.clause for c in result.refusals}


# ---------------------------------------------------------------------------
# PASS branch on a clean governed host
# ---------------------------------------------------------------------------


def test_clean_governed_host_passes():
    result = guard.evaluate(
        _governed_facts(), require_visible_launch=True, require_worker=True, check_packaging=True
    )
    assert result.ok
    assert result.refusals == []


# ---------------------------------------------------------------------------
# RED-G-1 — out-of-contract interpreter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version_info", [(3, 13, 13), (3, 15, 0)])
def test_red_g1_refuses_out_of_contract_interpreter(version_info):
    result = guard.evaluate(_governed_facts(version_info=version_info))
    assert not result.ok
    assert guard.CLAUSE_INTERPRETER in _refusal_clauses(result)


# ---------------------------------------------------------------------------
# RED-G-2 — missing tmux for a visibility-required launch
# ---------------------------------------------------------------------------


def test_red_g2_refuses_missing_tmux_when_visible_launch_required():
    result = guard.evaluate(_governed_facts(tmux_available=False), require_visible_launch=True)
    assert not result.ok
    assert guard.CLAUSE_TMUX in _refusal_clauses(result)


def test_red_g2_tmux_not_required_without_visible_launch_flag():
    # Missing tmux must NOT refuse a plain doctor run that does not require a launch.
    result = guard.evaluate(_governed_facts(tmux_available=False), require_visible_launch=False)
    assert result.ok


# ---------------------------------------------------------------------------
# RED-G-3 — rootless Podman missing, or rootful presented, for worker execution
# ---------------------------------------------------------------------------


def test_red_g3_refuses_missing_podman_when_worker_required():
    result = guard.evaluate(_governed_facts(podman_available=False), require_worker=True)
    assert not result.ok
    assert guard.CLAUSE_PODMAN in _refusal_clauses(result)


def test_red_g3_refuses_rootful_podman_when_worker_required():
    result = guard.evaluate(
        _governed_facts(podman_available=True, podman_rootless=False), require_worker=True
    )
    assert not result.ok
    assert guard.CLAUSE_PODMAN in _refusal_clauses(result)


def test_red_g3_podman_not_required_without_worker_flag():
    result = guard.evaluate(_governed_facts(podman_available=False), require_worker=False)
    assert result.ok


# ---------------------------------------------------------------------------
# RED-G-4 — ungoverned .hermes state-path posture
# ---------------------------------------------------------------------------


def test_red_g4_refuses_unignored_hermes_state_path():
    result = guard.evaluate(_governed_facts(hermes_ignored=False))
    assert not result.ok
    assert guard.CLAUSE_STATE_PATH in _refusal_clauses(result)


# ---------------------------------------------------------------------------
# RED-G-5 — unsafe hidden continuation
# ---------------------------------------------------------------------------


def test_red_g5_refuses_hidden_continuation():
    result = guard.evaluate(_governed_facts(hidden_continuation=True))
    assert not result.ok
    assert guard.CLAUSE_HIDDEN_CONTINUATION in _refusal_clauses(result)


# ---------------------------------------------------------------------------
# RED-G-6 — dependency / wheelhouse drift
# ---------------------------------------------------------------------------


def test_red_g6_refuses_packaging_drift_when_checked():
    drifted = PackagingContractResult(ok=False, violations=["requires-python drift"], details={})
    result = guard.evaluate(_governed_facts(packaging=drifted), check_packaging=True)
    assert not result.ok
    assert guard.CLAUSE_PACKAGING in _refusal_clauses(result)


def test_red_g6_packaging_not_enforced_when_unchecked():
    drifted = PackagingContractResult(ok=False, violations=["x"], details={})
    result = guard.evaluate(_governed_facts(packaging=drifted), check_packaging=False)
    assert result.ok


def test_red_g6_packaging_not_applicable_outside_ce_source_tree():
    drifted = PackagingContractResult(ok=False, violations=["missing wheelhouse"], details={})
    result = guard.evaluate(
        _governed_facts(packaging=drifted, ce_source_tree_context=False),
        check_packaging=True,
    )
    packaging = next(c for c in result.checks if c.clause == guard.CLAUSE_PACKAGING)
    assert result.ok
    assert packaging.applicable is False
    assert guard.CLAUSE_PACKAGING not in _refusal_clauses(result)


# ---------------------------------------------------------------------------
# Serialization for ce doctor --json
# ---------------------------------------------------------------------------


def test_guard_result_to_dict_names_each_clause():
    result = guard.evaluate(_governed_facts(), require_visible_launch=True, require_worker=True)
    payload = result.to_dict()
    assert payload["ok"] is True
    clauses = {c["clause"] for c in payload["checks"]}
    assert {
        guard.CLAUSE_INTERPRETER,
        guard.CLAUSE_TMUX,
        guard.CLAUSE_PODMAN,
        guard.CLAUSE_STATE_PATH,
        guard.CLAUSE_HIDDEN_CONTINUATION,
        guard.CLAUSE_PACKAGING,
    } <= clauses
