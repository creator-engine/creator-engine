"""Pure READY-to-validation-attestation proposals.

This is deliberately a data reducer, not a validator or controller action.  A
caller supplies a point-in-time fact object and owns every observation,
validation run, queue operation, and transport decision.  In particular, this
module does not inspect process or filesystem state and has no forge surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Literal


AttestationState = Literal[
    "pending", "sha_mismatch", "validator_live", "attested_green", "failed"
]

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class ReadyAttestationFacts:
    """Injected, value-free evidence for one READY candidate.

    ``validation_sha`` is present once a validation attempt has selected a
    head.  Terminal evidence is complete only when it supplies an integer exit
    code and both failure counts.  Keeping structural and environment counts
    distinct prevents a caller from silently treating one kind of parity
    evidence as the other.
    """

    ready_sha: str
    validation_sha: str | None = None
    validator_live: bool = False
    exit_code: int | None = None
    structural_failures: int | None = None
    environment_failures: int | None = None


@dataclass(frozen=True)
class ReadyAttestationProposal:
    """A deterministic, non-actuating proposal for a supplied fact set."""

    state: AttestationState
    ready_sha: str | None
    validation_sha: str | None
    reason: str

    @property
    def dedup_key(self) -> str:
        """Return a stable key for coalescing identical proposals externally."""

        return sha256(self.serialized().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, str | None]:
        return {
            "state": self.state,
            "ready_sha": self.ready_sha,
            "validation_sha": self.validation_sha,
            "reason": self.reason,
            "dedup_key": self.dedup_key,
        }

    def serialized(self) -> str:
        """Return canonical JSON used by :attr:`dedup_key`."""

        return json.dumps(
            {
                "ready_sha": self.ready_sha,
                "reason": self.reason,
                "state": self.state,
                "validation_sha": self.validation_sha,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


def reduce_ready_attestation(facts: ReadyAttestationFacts) -> ReadyAttestationProposal:
    """Reduce injected facts into one fail-closed attestation proposal.

    SHA mismatch intentionally precedes a live-validator result: a validator
    working on a different head must never withhold or attest the supplied
    READY.  Any malformed or incoherent terminal evidence becomes ``failed``;
    no exception is used as an implicit permissive outcome.
    """

    ready_sha = _normalized_sha(facts.ready_sha)
    validation_sha = _normalized_sha(facts.validation_sha) if facts.validation_sha is not None else None
    if ready_sha is None:
        return _failed(None, validation_sha, "invalid_ready_sha")
    if facts.validation_sha is not None and validation_sha is None:
        return _failed(ready_sha, None, "invalid_validation_sha")
    if type(facts.validator_live) is not bool:
        return _failed(ready_sha, validation_sha, "invalid_validator_live")
    if validation_sha is not None and validation_sha != ready_sha:
        return ReadyAttestationProposal(
            "sha_mismatch", ready_sha, validation_sha, "validation_sha_differs_from_ready_sha"
        )
    if not _valid_exit_code(facts.exit_code):
        return _failed(ready_sha, validation_sha, "invalid_exit_evidence")
    if not _valid_failure_count(facts.structural_failures) or not _valid_failure_count(
        facts.environment_failures
    ):
        return _failed(ready_sha, validation_sha, "invalid_failure_evidence")
    if facts.validator_live:
        if facts.exit_code is not None or facts.structural_failures is not None or facts.environment_failures is not None:
            return _failed(ready_sha, validation_sha, "live_validator_has_terminal_evidence")
        return ReadyAttestationProposal("validator_live", ready_sha, validation_sha, "validator_is_live")
    if validation_sha is None:
        if facts.exit_code is None and facts.structural_failures is None and facts.environment_failures is None:
            return ReadyAttestationProposal("pending", ready_sha, None, "validation_not_started")
        return _failed(ready_sha, None, "terminal_evidence_without_validation_sha")
    if facts.exit_code is None:
        return _failed(ready_sha, validation_sha, "missing_exit_evidence")
    if facts.structural_failures is None or facts.environment_failures is None:
        return _failed(ready_sha, validation_sha, "missing_failure_evidence")
    if facts.exit_code != 0:
        return _failed(ready_sha, validation_sha, f"validator_exit_{facts.exit_code}")
    if facts.structural_failures:
        return _failed(ready_sha, validation_sha, "structural_failures_present")
    if facts.environment_failures:
        return _failed(ready_sha, validation_sha, "environment_failures_present")
    return ReadyAttestationProposal("attested_green", ready_sha, validation_sha, "terminal_green_evidence")


def _failed(ready_sha: str | None, validation_sha: str | None, reason: str) -> ReadyAttestationProposal:
    return ReadyAttestationProposal("failed", ready_sha, validation_sha, reason)


def _normalized_sha(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower()
    return normalized if _SHA_RE.fullmatch(normalized) else None


def _valid_exit_code(value: object) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 255)


def _valid_failure_count(value: object) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0)
