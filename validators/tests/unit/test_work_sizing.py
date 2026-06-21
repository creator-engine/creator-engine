"""Unit tests for the F1 work-sizing pure ceremony."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

from jsonschema import Draft202012Validator

from creator_engine_validator.schema import load_schema
from creator_engine_validator.work_sizing import (
    MUTATION_CLASSES,
    WORK_CLASSES,
    size_ceremony,
)


SIZE_EXPECTATIONS = {
    "tiny": {
        "artifact_set": ("scope_card",),
        "decomposition_depth": 0,
    },
    "story": {
        "artifact_set": ("intent_line", "scope_record", "inline_tasks", "tasks.ce.yml"),
        "decomposition_depth": 1,
    },
    "feature": {
        "artifact_set": ("spec.md", "plan.md", "tasks.md", "tasks.ce.yml"),
        "decomposition_depth": 2,
    },
    "epic": {
        "artifact_set": ("prd.md", "per_feature_plan.md", "thin_slice_scope", "tasks.ce.yml"),
        "decomposition_depth": 3,
    },
}

RISK_EXPECTATIONS = {
    "none": {
        "ratification_gates": ("auto_back_gate",),
        "adr_required": False,
    },
    "docs": {
        "ratification_gates": ("auto_back_gate",),
        "adr_required": False,
    },
    "code": {
        "ratification_gates": ("distinct_review", "operator_merge"),
        "adr_required": False,
    },
    "schema": {
        "ratification_gates": ("operator_front_bet", "operator_merge"),
        "adr_required": True,
    },
    "deploy": {
        "ratification_gates": ("operator_front_bet", "operator_merge"),
        "adr_required": True,
    },
    "governance": {
        "ratification_gates": (
            "operator_front_bet",
            "operator_human_ratifier",
            "non_delegable",
            "ring1_push_block",
            "operator_merge",
        ),
        "adr_required": True,
    },
    "identity": {
        "ratification_gates": (
            "operator_front_bet",
            "operator_human_ratifier",
            "non_delegable",
            "ring1_push_block",
            "operator_merge",
        ),
        "adr_required": True,
    },
    "security": {
        "ratification_gates": (
            "operator_front_bet",
            "operator_human_ratifier",
            "non_delegable",
            "ring1_push_block",
            "operator_merge",
        ),
        "adr_required": True,
    },
    "attestation": {
        "ratification_gates": (
            "operator_front_bet",
            "operator_human_ratifier",
            "non_delegable",
            "ring1_push_block",
            "operator_merge",
        ),
        "adr_required": True,
    },
    "redaction": {
        "ratification_gates": (
            "operator_front_bet",
            "operator_human_ratifier",
            "non_delegable",
            "ring1_push_block",
            "operator_merge",
        ),
        "adr_required": True,
    },
}


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema("schemas/work-sizing.schema.yaml"))


def test_every_class_risk_pair_returns_schema_valid_record():
    validator = _schema_validator()
    assert tuple(WORK_CLASSES) == tuple(SIZE_EXPECTATIONS)
    assert tuple(MUTATION_CLASSES) == tuple(RISK_EXPECTATIONS)
    for work_class, mutation_class in product(WORK_CLASSES, MUTATION_CLASSES):
        record = size_ceremony(work_class, mutation_class)
        errors = sorted(validator.iter_errors(record), key=lambda err: list(err.path))
        assert errors == []


def test_size_axis_controls_only_depth_and_artifacts():
    for work_class, expected in SIZE_EXPECTATIONS.items():
        docs_record = size_ceremony(work_class, "docs")
        identity_record = size_ceremony(work_class, "identity")
        assert tuple(docs_record["artifact_set"]) == expected["artifact_set"]
        assert tuple(identity_record["artifact_set"]) == expected["artifact_set"]
        assert docs_record["decomposition_depth"] == expected["decomposition_depth"]
        assert identity_record["decomposition_depth"] == expected["decomposition_depth"]


def test_risk_axis_controls_only_gates_and_adr_requirement():
    for mutation_class, expected in RISK_EXPECTATIONS.items():
        tiny_record = size_ceremony("tiny", mutation_class)
        feature_record = size_ceremony("feature", mutation_class)
        assert tuple(tiny_record["ratification_gates"]) == expected["ratification_gates"]
        assert tuple(feature_record["ratification_gates"]) == expected["ratification_gates"]
        assert tiny_record["adr_required"] is expected["adr_required"]
        assert feature_record["adr_required"] is expected["adr_required"]


def test_size_and_risk_axes_are_independent():
    tiny_identity = size_ceremony("tiny", "identity")
    feature_docs = size_ceremony("feature", "docs")

    assert tiny_identity["decomposition_depth"] == 0
    assert tiny_identity["artifact_set"] == ["scope_card"]
    assert tiny_identity["adr_required"] is True
    assert "operator_human_ratifier" in tiny_identity["ratification_gates"]

    assert feature_docs["decomposition_depth"] == 2
    assert feature_docs["artifact_set"] == ["spec.md", "plan.md", "tasks.md", "tasks.ce.yml"]
    assert feature_docs["adr_required"] is False
    assert feature_docs["ratification_gates"] == ["auto_back_gate"]


def test_size_ceremony_is_deterministic_as_canonical_json_bytes():
    first = json.dumps(size_ceremony("story", "code"), sort_keys=True, separators=(",", ":")).encode()
    second = json.dumps(size_ceremony("story", "code"), sort_keys=True, separators=(",", ":")).encode()
    assert first == second


def test_unknown_work_or_mutation_class_fails_closed_with_value_free_error():
    for bad_work, bad_mutation in (("bogus", "docs"), ("tiny", "bogus")):
        try:
            size_ceremony(bad_work, bad_mutation)
        except ValueError as exc:
            message = str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("unknown enum should fail closed")
        assert "bogus" not in message
        assert "unknown " in message


def test_reproduces_design_a4_table_exactly():
    expected = {
        (work_class, mutation_class): {
            "artifact_set": list(size["artifact_set"]),
            "decomposition_depth": size["decomposition_depth"],
            "ratification_gates": list(risk["ratification_gates"]),
            "adr_required": risk["adr_required"],
        }
        for work_class, size in SIZE_EXPECTATIONS.items()
        for mutation_class, risk in RISK_EXPECTATIONS.items()
    }
    observed = {
        (work_class, mutation_class): {
            "artifact_set": size_ceremony(work_class, mutation_class)["artifact_set"],
            "decomposition_depth": size_ceremony(work_class, mutation_class)["decomposition_depth"],
            "ratification_gates": size_ceremony(work_class, mutation_class)["ratification_gates"],
            "adr_required": size_ceremony(work_class, mutation_class)["adr_required"],
        }
        for work_class, mutation_class in product(WORK_CLASSES, MUTATION_CLASSES)
    }
    assert observed == expected

