"""Unit tests for the foreman-delegation seat-class spine."""

from __future__ import annotations

import json
from itertools import product

import pytest

from creator_engine_validator.seat_class import (
    BASELINE_MUTATION_CLASSES,
    WORK_CLASSES,
    classify_work_class,
    foreman_would_deny,
    resolve_seat_class,
)


POLICY = {
    "delegation_required_mutation_classes": [
        "code",
        "schema",
        "deploy",
        "governance",
        "identity",
        "security",
    ]
}


@pytest.mark.parametrize(
    "tool,command,mutation_class,expected",
    [
        ("Read", "validators/creator_engine_validator/seat_class.py", "code", "coordination"),
        ("Grep", "seat_class", "code", "coordination"),
        ("Glob", "validators/**/*.py", "code", "coordination"),
        ("Bash", "git status --short", "code", "coordination"),
        ("Bash", "git -C . diff --stat", "code", "coordination"),
        ("Bash", "git show HEAD", "code", "coordination"),
        ("Bash", "gh issue view 163 --repo creator-engine/ce-ops", "docs", "coordination"),
        ("Bash", "gh pr view 294", "docs", "coordination"),
        ("Bash", "ce lane launch --help", "docs", "coordination"),
        ("Bash", "ce launch", "docs", "coordination"),
        ("Bash", "ce hud", "docs", "coordination"),
        ("Bash", "git merge feature", "deploy", "restricted"),
        ("Bash", "make deploy", "deploy", "restricted"),
        ("Bash", "npm publish", "deploy", "restricted"),
        ("Edit", "validators/creator_engine_validator/seat_class.py", "code", "implementation"),
        ("Write", "schemas/seat-class-policy.schema.yaml", "schema", "implementation"),
        ("MultiEdit", "validators/tests/unit/test_seat_class.py", "code", "implementation"),
        ("Bash", "python -m pytest validators/tests/unit/test_seat_class.py -q", "code", "implementation"),
        ("Bash", "make build", "code", "implementation"),
        ("Bash", "python scripts/generate.py", "code", "implementation"),
        ("UnknownTool", "anything", "docs", "implementation"),
    ],
)
def test_classify_work_class_representatives(tool, command, mutation_class, expected):
    assert classify_work_class(tool, command, mutation_class) == expected


def test_coordination_path_edit_is_coordination():
    prefixes = (".ce/state/", ".ce/changelog/", "brief.md", "docs/contracts/")
    assert classify_work_class(
        "Edit",
        ".ce/state/dispatches/run-1/brief.md",
        "governance",
        coordination_path_prefixes=prefixes,
    ) == "coordination"
    assert classify_work_class(
        "Write",
        "docs/contracts/seat-class-policy.md",
        "docs",
        coordination_path_prefixes=prefixes,
    ) == "coordination"


def test_coordination_path_prefixes_none_is_empty_and_total():
    assert (
        classify_work_class(
            "Edit",
            "docs/contracts/seat-class-policy.md",
            "docs",
            coordination_path_prefixes=None,
        )
        == "implementation"
    )


def test_foreman_would_deny_only_implementation_for_required_classes():
    reason = foreman_would_deny("foreman", "implementation", "code", POLICY)
    assert reason is not None
    assert "code" not in reason
    assert "ce-ops#163 REQ-3" in reason
    assert "foreman_delegation_required" in reason
    assert foreman_would_deny("foreman", "coordination", "code", POLICY) is None
    assert foreman_would_deny("foreman", "implementation", "docs", POLICY) is None
    assert foreman_would_deny("worker", "implementation", "code", POLICY) is None


def test_unknown_seat_class_fails_closed_to_foreman():
    assert foreman_would_deny("bogus", "implementation", "code", POLICY) is not None


def test_resolve_seat_class_fails_closed():
    assert resolve_seat_class(None) == "foreman"
    assert resolve_seat_class("") == "foreman"
    assert resolve_seat_class("bogus") == "foreman"
    assert resolve_seat_class("worker") == "worker"
    assert resolve_seat_class("FOREMAN") == "foreman"


def test_resolve_seat_class_absent_or_unknown_ignores_default_and_fails_closed():
    assert resolve_seat_class(None, default="worker") == "foreman"
    assert resolve_seat_class("", default="worker") == "foreman"
    assert resolve_seat_class("bogus", default="worker") == "foreman"
    assert resolve_seat_class("worker", default="foreman") == "worker"


def test_determinism_as_identical_json_bytes():
    kwargs = {
        "tool": "Bash",
        "command": "python -m pytest validators/tests/unit/test_seat_class.py -q",
        "mutation_class": "code",
    }
    first = json.dumps(classify_work_class(**kwargs), sort_keys=True).encode()
    second = json.dumps(classify_work_class(**kwargs), sort_keys=True).encode()
    assert first == second


def test_totality_over_work_classes_and_baseline_mutation_classes():
    assert WORK_CLASSES == frozenset({"coordination", "implementation", "restricted"})
    for work_class, mutation_class in product(WORK_CLASSES, BASELINE_MUTATION_CLASSES):
        foreman_would_deny("foreman", work_class, mutation_class, POLICY)
