"""F1 work-sizing ceremony spine.

``size_ceremony(work_class, mutation_class)`` is deliberately small and pure:
no disk, subprocess, network, wall clock, randomness, classifier, dispatcher, or
datastore. It encodes the ratified A.4 thin-slice table as two independent axes:
size selects artifacts/decomposition depth; risk selects gates/ADR posture.
"""

from __future__ import annotations

from typing import Any, Final

WORK_CLASSES: Final[tuple[str, ...]] = ("XS", "S", "M", "L")
LEGACY_WORK_CLASS_ALIASES: Final[dict[str, str]] = {
    "tiny": "XS",
    "story": "S",
    "feature": "M",
    "epic": "L",
}
WORK_CLASS_ALIASES: Final[dict[str, str]] = {
    **{work_class: work_class for work_class in WORK_CLASSES},
    **{work_class.lower(): work_class for work_class in WORK_CLASSES},
    **LEGACY_WORK_CLASS_ALIASES,
}
WORK_CLASS_INPUTS: Final[tuple[str, ...]] = tuple(WORK_CLASS_ALIASES)
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

# CE ceremony tiers (depth/floor), not Agile work-item types.
_SIZE_TABLE: Final[dict[str, dict[str, Any]]] = {
    "XS": {
        "artifact_set": ("scope_card",),
        "decomposition_depth": 0,
    },
    "S": {
        "artifact_set": ("intent_line", "scope_record", "inline_tasks", "tasks.ce.yml"),
        "decomposition_depth": 1,
    },
    "M": {
        "artifact_set": ("spec.md", "plan.md", "tasks.md", "tasks.ce.yml"),
        "decomposition_depth": 2,
    },
    "L": {
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


def normalize_work_class(work_class: str) -> str:
    """Return the canonical XS/S/M/L work class, accepting legacy aliases."""
    normalized = WORK_CLASS_ALIASES.get(work_class.strip())
    if normalized is None:
        raise ValueError("unknown work_class")
    return normalized


def size_ceremony(work_class: str, mutation_class: str) -> dict[str, Any]:
    """Return the deterministic sizing record for ``work_class`` x ``mutation_class``.

    Unknown enum values fail closed with value-free messages: the exception does
    not echo the supplied value.
    """
    work_class = normalize_work_class(work_class)
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
