"""Disabled-by-default, read-only snapshot retention inventory.

This module deliberately derives inventory disposition only.  It has no action,
locking, persistence, runtime, or deletion surface.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Literal, Mapping


REQUIRED_SOURCES = (
    "active_claim",
    "worktree",
    "evidence_pin",
    "detached_artifact",
)
Source = Literal["active_claim", "worktree", "evidence_pin", "detached_artifact"]
Status = Literal["protected", "clear", "blocked"]
Disposition = Literal["disabled", "protected", "unprotected", "blocked"]
_OPAQUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def _require_opaque(value: str, field: str) -> None:
    if not isinstance(value, str) or not _OPAQUE.fullmatch(value):
        raise ValueError(f"{field} must be a redaction-safe opaque identifier")


@dataclass(frozen=True)
class SnapshotIdentity:
    """Registrar-supplied identity; this type carries no location or retention data."""

    snapshot_id: str
    seat_id: str
    created_at: str
    content_sha256: str

    def __post_init__(self) -> None:
        _require_opaque(self.snapshot_id, "snapshot_id")
        _require_opaque(self.seat_id, "seat_id")
        if not isinstance(self.created_at, str) or not _UTC.fullmatch(self.created_at):
            raise ValueError("created_at must be an ISO-8601 UTC timestamp")
        if not isinstance(self.content_sha256, str) or not _SHA256.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be a lower-hex SHA-256")

    def to_record(self) -> dict[str, str]:
        return {
            "snapshot_id": self.snapshot_id,
            "seat_id": self.seat_id,
            "created_at": self.created_at,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ProtectionObservation:
    """One reader's immutable, redaction-safe protection fact."""

    source: Source
    status: Status
    snapshot_id: str
    source_ref: str
    generation: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.source not in REQUIRED_SOURCES:
            raise ValueError("source is not a supported protection source")
        if self.status not in {"protected", "clear", "blocked"}:
            raise ValueError("status is not a supported observation status")
        _require_opaque(self.snapshot_id, "snapshot_id")
        _require_opaque(self.source_ref, "source_ref")
        if self.generation is not None:
            _require_opaque(self.generation, "generation")
        if self.reason is not None:
            _require_opaque(self.reason, "reason")

    def to_record(self) -> dict[str, str | None]:
        return {
            "source": self.source,
            "status": self.status,
            "snapshot_id": self.snapshot_id,
            "source_ref": self.source_ref,
            "generation": self.generation,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class InventoryRequest:
    """Frozen registrar identity and expected source generations for one inventory pass."""

    identity: SnapshotIdentity
    source_generations: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, SnapshotIdentity):
            raise ValueError("identity must be a SnapshotIdentity")
        frozen = dict(self.source_generations)
        if set(frozen) != set(REQUIRED_SOURCES):
            raise ValueError("source_generations must name exactly the required sources")
        for source, generation in frozen.items():
            _require_opaque(source, "source")
            _require_opaque(generation, "source generation")
        object.__setattr__(self, "source_generations", MappingProxyType(frozen))


@dataclass(frozen=True)
class SnapshotInventory:
    """Deterministic inventory result; ``unprotected`` never confers action eligibility."""

    enabled: bool
    identity: SnapshotIdentity
    source_generations: Mapping[str, str]
    observations: tuple[ProtectionObservation, ...]
    disposition: Disposition

    def to_record(self) -> dict[str, object]:
        return {
            "schema_version": "1",
            "enabled": self.enabled,
            "identity": self.identity.to_record(),
            "source_generations": dict(sorted(self.source_generations.items())),
            "observations": [observation.to_record() for observation in self.observations],
            "disposition": self.disposition,
        }

    def serialize(self) -> str:
        return json.dumps(self.to_record(), sort_keys=True, separators=(",", ":"))


Reader = Callable[[SnapshotIdentity], ProtectionObservation]


def _blocked_observation(source: str, reason: str, generation: str | None) -> ProtectionObservation:
    return ProtectionObservation(
        source=source,  # type: ignore[arg-type]
        status="blocked",
        snapshot_id="blocked",
        source_ref=f"reader:{source}",
        generation=generation,
        reason=reason,
    )


def build_inventory(
    request: InventoryRequest,
    readers: Mapping[str, Reader],
    *,
    enabled: bool = False,
) -> SnapshotInventory:
    """Build a fail-closed inventory using only injected, read-only reader callables."""

    if not isinstance(request, InventoryRequest):
        raise ValueError("request must be an InventoryRequest")
    if not enabled:
        return SnapshotInventory(False, request.identity, request.source_generations, (), "disabled")

    observations: list[ProtectionObservation] = []
    for source in REQUIRED_SOURCES:
        expected_generation = request.source_generations[source]
        reader = readers.get(source)
        if not callable(reader):
            observations.append(_blocked_observation(source, "reader_unavailable", expected_generation))
            continue
        try:
            observation = reader(request.identity)
        except Exception:
            observations.append(_blocked_observation(source, "reader_unreadable", expected_generation))
            continue
        if not isinstance(observation, ProtectionObservation):
            observations.append(_blocked_observation(source, "reader_malformed", expected_generation))
            continue
        if observation.source != source:
            observations.append(_blocked_observation(source, "source_mismatch", expected_generation))
            continue
        if observation.snapshot_id != request.identity.snapshot_id:
            observations.append(_blocked_observation(source, "identity_mismatch", expected_generation))
            continue
        if observation.generation != expected_generation:
            observations.append(_blocked_observation(source, "generation_drift", expected_generation))
            continue
        observations.append(observation)

    statuses = {observation.status for observation in observations}
    if "blocked" in statuses:
        disposition: Disposition = "blocked"
    elif "protected" in statuses:
        disposition = "protected"
    else:
        disposition = "unprotected"
    return SnapshotInventory(True, request.identity, request.source_generations, tuple(observations), disposition)


__all__ = [
    "REQUIRED_SOURCES",
    "InventoryRequest",
    "ProtectionObservation",
    "SnapshotIdentity",
    "SnapshotInventory",
    "build_inventory",
]
