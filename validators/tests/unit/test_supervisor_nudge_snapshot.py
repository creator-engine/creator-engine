from __future__ import annotations

import ast
from pathlib import Path

from creator_engine_validator.forge.supervisor_nudge_snapshot import (
    ContextCheckpointFact,
    CoverageFact,
    DuplicateFact,
    IdleSeatFact,
    PreflightCapacityFact,
    ProposalKind,
    QueueLimboFact,
    ReviewHeadFact,
    SupervisorFacts,
    classify_supervisor_facts,
)


def _kinds(facts: SupervisorFacts) -> list[tuple[str, str]]:
    return [(proposal.kind.value, proposal.subject) for proposal in classify_supervisor_facts(facts)]


def test_every_nudge_class_is_derived_only_from_injected_facts():
    facts = SupervisorFacts(
        reviews=(ReviewHeadFact("pr-960", "a" * 40, "b" * 40),),
        idle_seats=(IdleSeatFact("dev-4", "idle", 3, 3),),
        duplicates=(
            DuplicateFact("ce-n11", "work", 2),
            DuplicateFact("contained-suite", "validator", 2),
        ),
        capacities=(PreflightCapacityFact("contained-seat", 29, 30),),
        queue_limbo=(QueueLimboFact("ce-529", 2, 2),),
        coverage=(CoverageFact("dev-3", True, False),),
        checkpoints=(ContextCheckpointFact("continuity", 45, 45),),
    )

    assert _kinds(facts) == [
        ("context_checkpoint", "continuity"),
        ("duplicate_validator", "contained-suite"),
        ("duplicate_work", "ce-n11"),
        ("idle_seat_restock", "dev-4"),
        ("preflight_capacity", "contained-seat"),
        ("queue_limbo", "ce-529"),
        ("stale_review_head", "pr-960"),
        ("watcher_coverage_gap", "dev-3"),
    ]


def test_stale_review_proposal_is_bound_to_the_current_head_identity():
    same_head = SupervisorFacts(reviews=(ReviewHeadFact("pr-960", "a" * 40, "a" * 40),))
    changed_head = SupervisorFacts(reviews=(ReviewHeadFact("pr-960", "a" * 40, "b" * 40),))

    assert classify_supervisor_facts(same_head) == ()
    assert _kinds(changed_head) == [("stale_review_head", "pr-960")]


def test_thresholds_are_explicit_and_do_not_depend_on_a_clock():
    below = SupervisorFacts(
        idle_seats=(IdleSeatFact("dev-4", "idle", 2, 3),),
        capacities=(PreflightCapacityFact("contained", 30, 30),),
        queue_limbo=(QueueLimboFact("ce-529", 1, 2),),
        checkpoints=(ContextCheckpointFact("drill", 44, 45),),
    )

    assert classify_supervisor_facts(below) == ()


def test_output_is_stably_sorted_and_deduplicated():
    facts = SupervisorFacts(
        duplicates=(
            DuplicateFact("ce-529", "work", 2),
            DuplicateFact("ce-529", "work", 3),
        ),
        coverage=(CoverageFact("dev-4", False, True), CoverageFact("dev-4", True, False)),
    )

    assert _kinds(facts) == [
        (ProposalKind.DUPLICATE_WORK.value, "ce-529"),
        (ProposalKind.WATCHER_COVERAGE_GAP.value, "dev-4"),
    ]


def test_malformed_or_incoherent_facts_fail_closed_as_a_whole_snapshot():
    malformed = SupervisorFacts(
        reviews=(ReviewHeadFact("pr-960", "a" * 40, "b" * 40),),
        duplicates=(DuplicateFact("ce-529", "work", True),),
    )
    incoherent = SupervisorFacts(capacities=(PreflightCapacityFact("contained", -1, 30),))

    assert classify_supervisor_facts(malformed) == ()
    assert classify_supervisor_facts(incoherent) == ()
    assert classify_supervisor_facts({"reviews": ()}) == ()


def test_module_has_no_actuation_imports_or_calls():
    module = Path(__file__).parents[2] / "creator_engine_validator/forge/supervisor_nudge_snapshot.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module.split(".")[0])
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert imports <= {"__future__", "dataclasses", "enum"}
    assert not {"open", "exec", "eval", "input", "compile", "__import__"} & calls
