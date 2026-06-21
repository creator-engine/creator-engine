"""F1 work-sizing ceremony spine.

``size_ceremony(work_class, mutation_class)`` is deliberately small and pure:
no disk, subprocess, network, wall clock, randomness, classifier, dispatcher, or
datastore. It encodes the ratified A.4 thin-slice table as two independent axes:
size selects artifacts/decomposition depth; risk selects gates/ADR posture.
"""

from __future__ import annotations

from typing import Any, Final

WORK_CLASSES: Final[tuple[str, ...]] = ("tiny", "story", "feature", "epic")
MUTATION_CLASSES: Final[tuple[str, ...]] = (
    "none",
    "docs",
    "code",
    "schema",
    "deploy",
    "governance",
    "identity",
    "security",
    "attestation",
    "redaction",
)

_SIZE_TABLE: Final[dict[str, dict[str, Any]]] = {
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

_PRIVILEGED_RISKS: Final[frozenset[str]] = frozenset(
    {"governance", "identity", "security", "attestation", "redaction"}
)

_RISK_TABLE: Final[dict[str, dict[str, Any]]] = {
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
    **{
        risk: {
            "ratification_gates": (
                "operator_front_bet",
                "operator_human_ratifier",
                "non_delegable",
                "ring1_push_block",
                "operator_merge",
            ),
            "adr_required": True,
        }
        for risk in _PRIVILEGED_RISKS
    },
}


def size_ceremony(work_class: str, mutation_class: str) -> dict[str, Any]:
    """Return the deterministic sizing record for ``work_class`` x ``mutation_class``.

    Unknown enum values fail closed with value-free messages: the exception does
    not echo the supplied value.
    """
    if work_class not in _SIZE_TABLE:
        raise ValueError("unknown work_class")
    if mutation_class not in _RISK_TABLE:
        raise ValueError("unknown mutation_class")

    size = _SIZE_TABLE[work_class]
    risk = _RISK_TABLE[mutation_class]
    return {
        "kind": "sizing-record",
        "schema_version": "1",
        "intent_ref": "unbound",
        "work_class": work_class,
        "mutation_class": mutation_class,
        "artifact_set": list(size["artifact_set"]),
        "decomposition_depth": size["decomposition_depth"],
        "ratification_gates": list(risk["ratification_gates"]),
        "adr_required": bool(risk["adr_required"]),
    }

