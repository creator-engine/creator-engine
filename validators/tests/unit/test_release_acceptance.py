from __future__ import annotations

from pathlib import Path

from creator_engine_validator import release_acceptance as ra


SOURCE_COMMIT = "a" * 40
ARTIFACT_DIGEST = "b" * 64
NOW = "2026-07-10T00:00:00Z"


def _new_record() -> dict:
    result = ra.new_rc_record(
        rc_id="v1.2.3-rc1",
        rc_ref="refs/tags/v1.2.3-rc1",
        source_commit=SOURCE_COMMIT,
        artifact_manifest_sha256=ARTIFACT_DIGEST,
        release_ticket_ref="ticket-510",
        actor="source",
        evidence_ref=".ce/evidence/rc-marked.json",
        now=NOW,
    )
    assert result.allowed
    assert result.record is not None
    return result.record


def _record_in_state(state: str) -> dict:
    record = _new_record()
    record["state"] = state
    record["state_updated_at"] = NOW
    if state in {ra.PROMOTION_RATIFIED, ra.PROMOTED, ra.DOGFOOD_RING_CONSUMED, ra.CLOSURE_READY, ra.CLOSED}:
        record["promotion_evidence"]["fresh_tenant_rehearsal_ref"] = ".ce/evidence/rehearsal.json"
        record["ratification_ref"] = ".ce/evidence/ratification.json"
    if state in {ra.DOGFOOD_RING_CONSUMED, ra.CLOSURE_READY, ra.CLOSED}:
        record["promotion_evidence"]["dogfood_ring_ref"] = ".ce/evidence/dogfood.json"
    if state == ra.CLOSED:
        record["closure_ref"] = ".ce/evidence/closure.json"
    return record


def _valid_rehearsal_bundle() -> dict:
    return {
        "schema_version": "1",
        "harness_version": "2026.07",
        "candidate": {
            "rc_id": "v1.2.3-rc1",
            "source_commit": SOURCE_COMMIT,
            "artifact_manifest_sha256": ARTIFACT_DIGEST,
            "observed_cli_source_commit": SOURCE_COMMIT,
        },
        "summary": {"failed": 0, "stubbed": 0},
        "stages": [{"name": "install"}, {"name": "first-hour"}],
        "fresh_tenant_context": {"mounted_developer_checkout": False},
        "container_image": "registry.example/ce@sha256:" + ARTIFACT_DIGEST,
    }


def test_state_record_lives_under_release_acceptance_dir(tmp_path: Path) -> None:
    assert ra.record_path(tmp_path, "v1.2.3-rc1") == (
        tmp_path / ".ce" / "release-acceptance" / "v1.2.3-rc1.yml"
    )


def test_state_machine_entries_match_design_table() -> None:
    assert ra.STATES == (
        "rc_marked",
        "rehearsal_required",
        "rehearsal_passed",
        "promotion_ratified",
        "promoted",
        "ring0_consumed",
        "closure_ready",
        "closed",
        "held",
        "superseded",
        "reopened",
    )
    assert ra.ENTRY_EVIDENCE[ra.RC_MARKED] == (
        "RC tag/ref",
        "source commit",
        "initial acceptance record",
        "release ticket ref",
    )
    assert ra.ENTRY_EVIDENCE[ra.REHEARSAL_REQUIRED] == ("record transition after RC marking",)


def test_initial_rc_marking_requires_actor_and_evidence_ref() -> None:
    refused = ra.new_rc_record(
        rc_id="v1.2.3-rc1",
        rc_ref="refs/tags/v1.2.3-rc1",
        source_commit=SOURCE_COMMIT,
        release_ticket_ref="ticket-510",
        actor="",
        evidence_ref=".ce/evidence/rc-marked.json",
    )

    assert not refused.allowed
    assert refused.reason == "governed_action_required"


def test_new_rc_record_contains_minimum_state_fields_and_transition_log() -> None:
    record = _new_record()

    assert record["schema_version"] == "1"
    assert record["rc_id"] == "v1.2.3-rc1"
    assert record["rc_ref"] == "refs/tags/v1.2.3-rc1"
    assert record["source_commit"] == SOURCE_COMMIT
    assert record["artifact_manifest_sha256"] == ARTIFACT_DIGEST
    assert record["release_ticket_ref"] == "ticket-510"
    assert record["state"] == ra.RC_MARKED
    assert record["promotion_evidence"] == {
        "fresh_tenant_rehearsal_ref": None,
        "dogfood_ring_ref": None,
        "persistent_state_probe_refs": [],
    }
    assert record["transitions"] == [
        {
            "from": "none",
            "to": ra.RC_MARKED,
            "actor": "source",
            "evidence_ref": ".ce/evidence/rc-marked.json",
            "transitioned_at": NOW,
        }
    ]


def test_every_legal_transition_is_recorded_with_actor_and_evidence_ref() -> None:
    for old_state, allowed_targets in ra.LEGAL_TRANSITIONS.items():
        for new_state in allowed_targets:
            if old_state == ra.NONE:
                result = ra.new_rc_record(
                    rc_id="v1.2.3-rc1",
                    rc_ref="refs/tags/v1.2.3-rc1",
                    source_commit=SOURCE_COMMIT,
                    release_ticket_ref="ticket-510",
                    actor="source",
                    evidence_ref=f".ce/evidence/{new_state}.json",
                    now=NOW,
                )
            else:
                result = ra.transition_record(
                    _record_in_state(old_state),
                    new_state,
                    actor="source",
                    evidence_ref=f".ce/evidence/{new_state}.json",
                    now=NOW,
                )

            assert result.allowed, f"{old_state} -> {new_state}"
            assert result.old_state == old_state
            assert result.new_state == new_state
            assert result.record is not None
            assert result.record["state"] == new_state
            assert result.record["transitions"][-1]["actor"] == "source"
            assert result.record["transitions"][-1]["evidence_ref"] == f".ce/evidence/{new_state}.json"


def test_transition_entry_evidence_refs_are_bound_to_record_fields() -> None:
    record = _record_in_state(ra.REHEARSAL_REQUIRED)

    passed = ra.transition_record(
        record,
        ra.REHEARSAL_PASSED,
        actor="verifier",
        evidence_ref=".ce/evidence/rehearsal.json",
    )
    assert passed.record["promotion_evidence"]["fresh_tenant_rehearsal_ref"] == ".ce/evidence/rehearsal.json"

    ratified = ra.transition_record(
        _record_in_state(ra.REHEARSAL_PASSED),
        ra.PROMOTION_RATIFIED,
        actor="source",
        evidence_ref=".ce/evidence/ratification.json",
    )
    assert ratified.record["ratification_ref"] == ".ce/evidence/ratification.json"

    consumed = ra.transition_record(
        _record_in_state(ra.PROMOTED),
        ra.DOGFOOD_RING_CONSUMED,
        actor="source",
        evidence_ref=".ce/evidence/dogfood.json",
    )
    assert consumed.record["promotion_evidence"]["dogfood_ring_ref"] == ".ce/evidence/dogfood.json"

    closed = ra.transition_record(
        _record_in_state(ra.CLOSURE_READY),
        ra.CLOSED,
        actor="source",
        evidence_ref=".ce/evidence/closure.json",
    )
    assert closed.record["closure_ref"] == ".ce/evidence/closure.json"


def test_every_illegal_transition_is_refused() -> None:
    for old_state in ra.LEGAL_TRANSITIONS:
        for new_state in ra.STATES:
            if new_state in ra.LEGAL_TRANSITIONS[old_state]:
                continue

            result = ra.transition_record(
                _record_in_state(old_state) if old_state != ra.NONE else {"state": ra.NONE},
                new_state,
                actor="source",
                evidence_ref=f".ce/evidence/{new_state}.json",
            )

            assert not result.allowed, f"{old_state} -> {new_state}"
            assert result.reason == "illegal_transition"


def test_rc_marked_to_rehearsal_required_is_not_automatic_and_requires_governance() -> None:
    record = _new_record()

    assert record["state"] == ra.RC_MARKED
    assert [entry["to"] for entry in record["transitions"]] == [ra.RC_MARKED]

    refused = ra.transition_record(
        record,
        ra.REHEARSAL_REQUIRED,
        actor=None,
        evidence_ref=".ce/evidence/rehearsal-required.json",
    )
    assert not refused.allowed
    assert refused.reason == "governed_action_required"

    accepted = ra.transition_record(
        record,
        ra.REHEARSAL_REQUIRED,
        actor="source",
        evidence_ref=".ce/evidence/rehearsal-required.json",
    )
    assert accepted.allowed
    assert accepted.record["state"] == ra.REHEARSAL_REQUIRED


def test_rehearsal_promotion_refuses_slice1_bundle_missing_candidate_binding() -> None:
    slice1_bundle = {
        "schema_version": "1",
        "harness_version": "2026.07",
        "summary": {"failed": 0, "stubbed": 0},
        "stages": [{"name": "install"}, {"name": "first-hour"}],
    }

    decision = ra.check_rehearsal_promotion_evidence(_new_record(), slice1_bundle)

    assert not decision.allowed
    assert decision.reason == "evidence_format_insufficient"
    assert decision.details == ("missing rc_id", "missing source_commit")


def test_rehearsal_promotion_accepts_bound_zero_failure_zero_stub_bundle() -> None:
    decision = ra.check_rehearsal_promotion_evidence(
        _new_record(),
        _valid_rehearsal_bundle(),
        expected_stage_names=("install", "first-hour"),
    )

    assert decision.allowed


def test_rehearsal_promotion_refuses_disallowed_stubs_without_ratified_exception() -> None:
    bundle = _valid_rehearsal_bundle()
    bundle["summary"]["stubbed"] = 1

    decision = ra.check_rehearsal_promotion_evidence(_new_record(), bundle)

    assert not decision.allowed
    assert decision.reason == "disallowed_stubs"


def test_closure_integrity_requires_linked_acceptance_evidence_and_probe() -> None:
    record = _record_in_state(ra.CLOSURE_READY)
    record["promotion_evidence"]["persistent_state_probe_refs"] = [".ce/evidence/probe.json"]
    registry = {
        ".ce/evidence/rehearsal.json": {"accepted": True},
        ".ce/evidence/dogfood.json": {
            "accepted": True,
            "rc_id": "v1.2.3-rc1",
            "source_commit": SOURCE_COMMIT,
            "artifact_manifest_sha256": ARTIFACT_DIGEST,
        },
    }

    decision = ra.check_closure_integrity(
        record,
        release_ticket_ref="ticket-510",
        evidence_registry=registry,
        deploy_class_claims=[
            {
                "claim": "promoted",
                "persistent_state_probe_ref": ".ce/evidence/probe.json",
            }
        ],
    )

    assert decision.allowed


def test_closure_integrity_refuses_unlinked_release_ticket_close() -> None:
    record = _record_in_state(ra.PROMOTED)

    decision = ra.check_closure_integrity(record, release_ticket_ref="ticket-510")

    assert not decision.allowed
    assert decision.reason == "closure_state_invalid"


def test_closure_integrity_refuses_deploy_claim_without_persistent_probe() -> None:
    record = _record_in_state(ra.CLOSURE_READY)
    registry = {
        ".ce/evidence/rehearsal.json": {"accepted": True},
        ".ce/evidence/dogfood.json": {
            "accepted": True,
            "rc_id": "v1.2.3-rc1",
            "source_commit": SOURCE_COMMIT,
            "artifact_manifest_sha256": ARTIFACT_DIGEST,
        },
    }

    decision = ra.check_closure_integrity(
        record,
        release_ticket_ref="ticket-510",
        evidence_registry=registry,
        deploy_class_claims=["deployed"],
    )

    assert not decision.allowed
    assert decision.reason == "persistent_state_probe_missing"
