"""Shared forge hold-label sets for issue and PR gates."""
from __future__ import annotations

AWAITING_OPERATOR_LABELS = frozenset({"awaiting-operator", "hold", "awaiting-operator/hold"})

BLOCKING_LABELS = frozenset(
    {
        "blocked",
        "checkpoint",
        "checkpoint held",
        "checkpoint-held",
        "dependency-blocked",
        "dependencies-blocked",
        "do-not-claim",
        "do-not-pickup",
        "do not claim",
        "do not pickup",
        "held",
        "held checkpoint",
        "held-checkpoint",
        "hold",
        "on hold",
        "on-hold",
        "status:blocked",
        "status:checkpoint",
        "status:held",
        "status:hold",
        "status:on-hold",
        "status/checkpoint",
        "status/held",
        "status/hold",
        "status/on-hold",
        "waiting",
        "wip",
    }
)

BLOCKING_LABEL_PREFIXES = (
    "blocked:",
    "blocked/",
    "checkpoint:",
    "checkpoint/",
    "held:",
    "held/",
    "hold:",
    "hold/",
)

AWAITING_OPERATOR_HOLD_LABELS = BLOCKING_LABELS | AWAITING_OPERATOR_LABELS
