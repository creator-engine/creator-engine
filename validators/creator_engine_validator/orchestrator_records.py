"""Standalone validators for Orchestrator runtime records."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from .schema import load_schema

_SCHEMAS_BY_KIND = {
    "ce-orchestrator-checkpoint": "schemas/orchestrator-checkpoint.schema.yaml",
    "ce-orchestrator-territory-map": "schemas/orchestrator-territory-map.schema.yaml",
    "ce-orchestrator-harvest-packet": "schemas/orchestrator-harvest-packet.schema.yaml",
    "ce-orchestrator-operator-decision": "schemas/orchestrator-operator-decision.schema.yaml",
}


@lru_cache(maxsize=None)
def _validator_for_kind(kind: str) -> Draft202012Validator:
    try:
        schema_path = _SCHEMAS_BY_KIND[kind]
    except KeyError as exc:
        known = ", ".join(sorted(_SCHEMAS_BY_KIND))
        raise ValueError(f"unknown orchestrator record kind {kind!r}; expected one of: {known}") from exc
    return Draft202012Validator(load_schema(schema_path), format_checker=FormatChecker())


def validate_orchestrator_record(kind: str, record: Any) -> None:
    """Validate an Orchestrator runtime record against its kind-specific schema.

    Raises ``ValueError`` when ``kind`` is unknown and ``jsonschema.ValidationError``
    when the record does not satisfy the selected schema.
    """

    validator = _validator_for_kind(kind)
    errors = sorted(validator.iter_errors(record), key=lambda err: list(err.path))
    if errors:
        raise JsonSchemaValidationError.create_from(errors[0])


__all__ = ["validate_orchestrator_record"]
