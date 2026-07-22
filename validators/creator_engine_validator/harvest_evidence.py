"""Structured evidence admission for controller harvest preparation.

Test-bearing work needs a negative observation from the named base (or prior
head) as well as its post-change green result.  This module deliberately
returns an audit-visible assessment rather than throwing away deficient seals:
callers can refuse harvest while retaining the reason for that refusal.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal


HarvestEvidenceStatus = Literal["ready", "flagged"]


@dataclass(frozen=True)
class HarvestEvidenceAssessment:
    """The named, side-effect-free admission result for a harvest evidence seal."""

    status: HarvestEvidenceStatus
    reason_code: str | None
    message: str
    test_bearing: bool | None
    payload: Mapping[str, object] | None

    @property
    def ready(self) -> bool:
        return self.status == "ready"


_REQUIRED_TEST_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("node_ids", "missing_test_node_ids", "test-bearing evidence must name exact test node ID(s)"),
    ("base_or_prior_head", "missing_base_or_prior_head", "test-bearing evidence must name its base or prior head"),
    ("red_command", "missing_red_command", "test-bearing evidence must name the RED command"),
    ("red_output", "missing_red_output", "test-bearing evidence must retain captured RED output"),
    ("green_command", "missing_green_command", "test-bearing evidence must name the GREEN command"),
    ("green_output", "missing_green_output", "test-bearing evidence must retain captured GREEN output"),
)


def parse_harvest_evidence(payload: Mapping[str, object] | None) -> HarvestEvidenceAssessment:
    """Parse and validate a data-only harvest seal payload without exceptions.

    A missing classification is not silently treated as non-test-bearing.  The
    sole exemption is an explicit ``{"test_bearing": false}`` declaration.
    """

    if payload is None:
        return _flagged(None, None, "missing_evidence_classification", "harvest evidence must explicitly classify test_bearing")
    if not isinstance(payload, Mapping):
        return _flagged(None, payload, "invalid_evidence_payload", "harvest evidence must be a mapping")

    test_bearing = payload.get("test_bearing")
    if not isinstance(test_bearing, bool):
        return _flagged(None, payload, "missing_test_bearing_classification", "harvest evidence test_bearing must be boolean")
    if not test_bearing:
        return HarvestEvidenceAssessment("ready", None, "explicit non-test-bearing exemption", False, payload)

    for field, code, message in _REQUIRED_TEST_FIELDS:
        value = payload.get(field)
        if field == "node_ids":
            present = isinstance(value, (list, tuple)) and bool(value) and all(
                isinstance(node, str) and node.strip() for node in value
            )
        else:
            present = isinstance(value, str) and bool(value.strip())
        if not present:
            return _flagged(True, payload, code, message)
    return HarvestEvidenceAssessment("ready", None, "test-bearing evidence includes base RED and post-change GREEN", True, payload)


def _flagged(
    test_bearing: bool | None,
    payload: Mapping[str, object] | object | None,
    reason_code: str,
    message: str,
) -> HarvestEvidenceAssessment:
    # Keep only mappings as structured raw evidence.  An invalid scalar is
    # still represented by the named reason, never raised away.
    retained = payload if isinstance(payload, Mapping) else None
    return HarvestEvidenceAssessment("flagged", reason_code, message, test_bearing, retained)


__all__ = ["HarvestEvidenceAssessment", "HarvestEvidenceStatus", "parse_harvest_evidence"]
