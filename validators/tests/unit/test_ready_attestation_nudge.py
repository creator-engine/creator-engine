"""Tests for the pure SL-3 READY-attestation reducer."""
from __future__ import annotations

from creator_engine_validator.forge.ready_attestation_nudge import (
    ReadyAttestationFacts,
    reduce_ready_attestation,
)
import creator_engine_validator.forge.ready_attestation_nudge as nudge


_SHA = "a" * 40
_OTHER_SHA = "b" * 40


def _reduce(**overrides):
    facts = ReadyAttestationFacts(ready_sha=_SHA, **overrides)
    return reduce_ready_attestation(facts)


def test_pending_when_validation_has_not_started():
    proposal = _reduce()
    assert proposal.state == "pending"
    assert proposal.reason == "validation_not_started"


def test_sha_mismatch_has_precedence_over_live_validator():
    proposal = _reduce(validation_sha=_OTHER_SHA, validator_live=True)
    assert proposal.state == "sha_mismatch"
    assert proposal.reason == "validation_sha_differs_from_ready_sha"


def test_live_validator_withholds_ready_until_terminal_evidence():
    proposal = _reduce(validation_sha=_SHA, validator_live=True)
    assert proposal.state == "validator_live"
    assert proposal.ready_sha == proposal.validation_sha == _SHA


def test_terminal_green_evidence_attests_exact_same_sha():
    proposal = _reduce(
        validation_sha=_SHA, exit_code=0, structural_failures=0, environment_failures=0
    )
    assert proposal.state == "attested_green"
    assert proposal.reason == "terminal_green_evidence"


def test_missing_or_invalid_exit_evidence_fails_closed():
    missing = _reduce(validation_sha=_SHA)
    invalid = _reduce(validation_sha=_SHA, exit_code=True, structural_failures=0, environment_failures=0)
    assert (missing.state, missing.reason) == ("failed", "missing_exit_evidence")
    assert (invalid.state, invalid.reason) == ("failed", "invalid_exit_evidence")


def test_failed_terminal_evidence_distinguishes_exit_and_failure_classes():
    exit_failure = _reduce(validation_sha=_SHA, exit_code=1, structural_failures=0, environment_failures=0)
    structural = _reduce(validation_sha=_SHA, exit_code=0, structural_failures=1, environment_failures=0)
    environment = _reduce(validation_sha=_SHA, exit_code=0, structural_failures=0, environment_failures=1)
    assert exit_failure.reason == "validator_exit_1"
    assert structural.reason == "structural_failures_present"
    assert environment.reason == "environment_failures_present"
    assert {exit_failure.state, structural.state, environment.state} == {"failed"}


def test_serialization_and_dedup_key_are_deterministic():
    first = _reduce(validation_sha=_SHA, exit_code=0, structural_failures=0, environment_failures=0)
    second = _reduce(validation_sha=_SHA, exit_code=0, structural_failures=0, environment_failures=0)
    assert first.serialized() == second.serialized()
    assert first.dedup_key == second.dedup_key
    assert first.to_dict()["dedup_key"] == first.dedup_key


def test_malformed_or_incoherent_facts_fail_closed():
    cases = (
        ReadyAttestationFacts(ready_sha="not-a-sha"),
        ReadyAttestationFacts(ready_sha=_SHA, validation_sha="bad"),
        ReadyAttestationFacts(ready_sha=_SHA, validator_live="yes"),  # type: ignore[arg-type]
        ReadyAttestationFacts(ready_sha=_SHA, exit_code=0),
        ReadyAttestationFacts(ready_sha=_SHA, exit_code=0, structural_failures=-1, environment_failures=0),
        ReadyAttestationFacts(ready_sha=_SHA, validator_live=True, exit_code=0, structural_failures=0, environment_failures=0),
        ReadyAttestationFacts(ready_sha=_SHA, exit_code=0, structural_failures=0, environment_failures=0),
    )
    assert all(reduce_ready_attestation(facts).state == "failed" for facts in cases)


def test_module_has_no_process_filesystem_network_queue_or_forge_actuation_surface():
    forbidden = {"subprocess", "socket", "requests", "urllib", "os", "pathlib", "queue", "gh"}
    assert forbidden.isdisjoint(vars(nudge))
    proposal = _reduce()
    assert proposal.state == "pending"  # reducer evaluation remains data-only
