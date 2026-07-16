"""Strict unit tests for the disabled-by-default snapshot inventory seam."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from creator_engine_validator.schema import load_schema
from creator_engine_validator.snapshot_retention import (
    REQUIRED_SOURCES,
    InventoryRequest,
    ProtectionObservation,
    SnapshotIdentity,
    build_inventory,
)


IDENTITY = SnapshotIdentity(
    snapshot_id="snap-opaque-001",
    seat_id="seat-3",
    created_at="2026-07-16T00:00:00Z",
    content_sha256="a" * 64,
)


def _clear(source: str) -> ProtectionObservation:
    return ProtectionObservation(
        source=source,
        status="clear",
        snapshot_id=IDENTITY.snapshot_id,
        source_ref=f"registrar:{source}",
        generation="generation-1",
    )


def _readers(*, override: dict[str, object] | None = None):
    override = override or {}
    calls: list[str] = []

    def reader(source: str):
        def read(identity: SnapshotIdentity):
            assert identity == IDENTITY
            calls.append(source)
            result = override.get(source, _clear(source))
            if isinstance(result, BaseException):
                raise result
            return result

        return read

    return {source: reader(source) for source in REQUIRED_SOURCES}, calls


def _request() -> InventoryRequest:
    return InventoryRequest(identity=IDENTITY, source_generations={source: "generation-1" for source in REQUIRED_SOURCES})


def _validate(record: dict) -> None:
    errors = list(Draft202012Validator(load_schema("schemas/snapshot-retention-inventory.schema.yaml")).iter_errors(record))
    assert not errors, [error.message for error in errors]


def test_disabled_default_is_deterministic_and_calls_zero_readers():
    readers, calls = _readers()

    inventory = build_inventory(_request(), readers)

    assert inventory.disposition == "disabled"
    assert inventory.to_record() == {
        "schema_version": "1",
        "enabled": False,
        "identity": IDENTITY.to_record(),
        "source_generations": {source: "generation-1" for source in REQUIRED_SOURCES},
        "observations": [],
        "disposition": "disabled",
    }
    assert calls == []
    _validate(inventory.to_record())


def test_all_stable_clear_sources_yield_deterministic_unprotected_inventory():
    readers, calls = _readers()

    first = build_inventory(_request(), readers, enabled=True)
    second = build_inventory(_request(), readers, enabled=True)

    assert first.disposition == "unprotected"
    assert first.to_record() == second.to_record()
    assert calls == list(REQUIRED_SOURCES) * 2
    _validate(first.to_record())


@pytest.mark.parametrize("source", REQUIRED_SOURCES)
def test_each_source_independently_protects_and_sources_union(source: str):
    readers, _calls = _readers(override={source: replace(_clear(source), status="protected", reason="retained")})

    inventory = build_inventory(_request(), readers, enabled=True)

    assert inventory.disposition == "protected"


def test_multiple_sources_union_without_lowering_protection():
    readers, _calls = _readers(
        override={
            "active_claim": replace(_clear("active_claim"), status="protected"),
            "worktree": replace(_clear("worktree"), status="protected"),
        }
    )

    assert build_inventory(_request(), readers, enabled=True).disposition == "protected"


@pytest.mark.parametrize(
    "bad",
    [None, {"source": "active_claim"}, ValueError("unreadable")],
)
def test_missing_unreadable_or_malformed_reader_result_blocks(bad: object):
    readers, _calls = _readers(override={"active_claim": bad})

    assert build_inventory(_request(), readers, enabled=True).disposition == "blocked"


def test_missing_reader_duplicate_identity_and_generation_drift_block():
    readers, _calls = _readers()
    del readers["active_claim"]
    assert build_inventory(_request(), readers, enabled=True).disposition == "blocked"

    duplicated, _calls = _readers(
        override={
            "active_claim": [
                _clear("active_claim"),
                _clear("active_claim"),
            ]
        }
    )
    assert build_inventory(_request(), duplicated, enabled=True).disposition == "blocked"

    mismatched, _calls = _readers(
        override={"active_claim": replace(_clear("active_claim"), snapshot_id="snap-other")}
    )
    assert build_inventory(_request(), mismatched, enabled=True).disposition == "blocked"

    drifting, _calls = _readers(
        override={"active_claim": replace(_clear("active_claim"), generation="generation-2")}
    )
    assert build_inventory(_request(), drifting, enabled=True).disposition == "blocked"


@pytest.mark.parametrize("field", ["action", "delete", "timer", "command", "path_glob"])
def test_schema_rejects_unknown_or_action_surface_fields(field: str):
    readers, _calls = _readers()
    record = build_inventory(_request(), readers, enabled=True).to_record()
    record[field] = "forbidden"

    errors = list(Draft202012Validator(load_schema("schemas/snapshot-retention-inventory.schema.yaml")).iter_errors(record))
    assert errors


def test_identity_and_observations_exclude_path_age_size_and_delete_inference():
    assert set(IDENTITY.to_record()) == {"snapshot_id", "seat_id", "created_at", "content_sha256"}
    observation = _clear("active_claim").to_record()
    assert "path" not in observation
    assert "age" not in observation
    assert "size" not in observation
    assert "delete" not in observation


def test_deterministic_serialization_validates_against_strict_schema():
    readers, _calls = _readers()
    inventory = build_inventory(_request(), readers, enabled=True)

    assert inventory.serialize() == inventory.serialize()
    _validate(inventory.to_record())
