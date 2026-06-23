"""Unit tests for Pane Registry substrate checks (PCO-046..PCO-053)."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.pane_registry import (
    CHECK_NAME,
    CODE_CONTAINER_BINDING,
    CODE_DUPLICATE_LIVE_PANE,
    CODE_ID_FORMAT,
    CODE_LEDGER_BINDING,
    CODE_OPERATOR_VISIBLE,
    CODE_ROLE_STATUS,
    CODE_SCHEMA,
    run,
    validate_pane_registry_record,
)


def valid_pane_record() -> dict:
    return {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice3-impl",
        "claim_ref": "claims/hermes-primary/pco-slice3-impl.yaml",
        "host_id": "workstation-a",
        "pane_id": "pane-pco-slice3-impl-001",
        "role": "implementer",
        "status": "active",
        "record_timestamp": "2026-05-23T07:45:00Z",
        "registered_at": "2026-05-23T07:40:00Z",
        "last_seen_at": "source-controlled:pane-registry/pane-pco-slice3-impl-001.yaml",
        "visibility": "operator_visible",
        "terminal": {
            "kind": "tmux",
            "session_id": "ce-pco",
            "window_id": "slice3",
            "pane_id": "1",
        },
    }


def _write(path: Path, record: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record), encoding="utf-8")
    return path


def valid_claim_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice3-impl",
        "record_timestamp": "source-controlled:claims/hermes-primary/pco-slice3-impl.yaml",
        "worktree_path": "/worktrees/pco-slice3-impl",
        "envelope_ref": ".hermes/envelopes/pco-slice3.md",
        "lease_seconds": 3600,
        "claimed_at": "source-controlled:claims/hermes-primary/pco-slice3-impl.yaml",
        "last_heartbeat_at": "source-controlled:claims/hermes-primary/pco-slice3-impl.yaml",
    }


def valid_container_record() -> dict:
    image_sha = "sha256:" + "b" * 64
    policy_sha = "a" * 64
    return {
        "kind": "container-instance-record",
        "record_type": "container_instance",
        "schema_version": "1",
        "instance_id": "inst-pco-slice3-001",
        "policy_ref": {
            "policy_id": "podman-implementer-v1",
            "policy_sha": policy_sha,
            "image_sha": image_sha,
        },
        "image_sha": image_sha,
        "claim_id": "pco-slice3-impl",
        "lease_id": "lease-slice3-001",
        "started_at": "2026-05-23T07:41:00Z",
        "stopped_at": None,
        "exit_code": None,
        "mount_manifest_applied": [],
        "secret_grants": [],
        "egress_allowlist_applied": [],
        "enforcement_primitive": "pasta",
        "policy_sha": policy_sha,
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    for code in (
        CODE_SCHEMA,
        CODE_ID_FORMAT,
        CODE_ROLE_STATUS,
        CODE_OPERATOR_VISIBLE,
        CODE_LEDGER_BINDING,
        CODE_DUPLICATE_LIVE_PANE,
        CODE_CONTAINER_BINDING,
    ):
        assert code in checks[CHECK_NAME].frs


def test_well_formed_pane_record_passes_schema_and_local_predicates(tmp_path: Path):
    assert validate_pane_registry_record(valid_pane_record(), tmp_path / "pane.yaml") == []


def test_spec_protocol_optional_fields_are_admitted_by_strict_schema(tmp_path: Path):
    record = valid_pane_record()
    record.update(
        {
            "status": "starting",
            "claim_record_sha256": "0" * 64,
            "worktree_path": "/worktrees/pco-slice3-impl",
            "branch": "implementer/pco-slice3-pane-registry-substrate-implementation-20260523T074004Z",
            "envelope_ref": "envelopes/pco-slice3.md",
            "handoff_ref": "handoffs/pco-slice3.md",
            "recommended_prompt_ref": "prompts/next.md",
            "container_instance_id": "inst-pco-slice3-001",
            "container_instance_ref": "containers/inst-pco-slice3-001.yaml",
        }
    )

    assert validate_pane_registry_record(record, tmp_path / "pane.yaml") == []


def test_missing_registered_or_last_seen_fails_pco_046(tmp_path: Path):
    record = valid_pane_record()
    del record["registered_at"]
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)

    record = valid_pane_record()
    del record["last_seen_at"]
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_unknown_top_level_field_fails_pco_053(tmp_path: Path):
    record = valid_pane_record()
    record["unexpected"] = "not allowed"
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_forbidden_host_identity_surface_fails_pco_047(tmp_path: Path):
    record = valid_pane_record()
    record["host_id"] = "gpt-5-provider"
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_ID_FORMAT for error in errors)


def test_plain_terminal_does_not_satisfy_operator_visible_pco_049(tmp_path: Path):
    record = valid_pane_record()
    record["terminal"] = {"kind": "plain_terminal"}
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_OPERATOR_VISIBLE for error in errors)


# ---------------------------------------------------------------------------
# ce-ops#207 W2′: the headless (operator_inspectable) surface (C3 generalization).
# ---------------------------------------------------------------------------
def valid_headless_pane_record() -> dict:
    record = valid_pane_record()
    record["visibility"] = "operator_inspectable"
    record["terminal"] = {
        "kind": "headless",
        "surface_ref": "/state/dispatches/pco-slice3-impl/attach.sock",
        "pid": 4242,
    }
    return record


def valid_herdr_pane_record() -> dict:
    record = valid_pane_record()
    record["visibility"] = "operator_inspectable"
    record["terminal"] = {
        "kind": "herdr",
        "surface_ref": "/run/ce/herdr/control.sock",
        "pane_id": "pane-1",
        "pid": 4242,
    }
    return record


def test_headless_inspectable_record_validates(tmp_path: Path):
    record = valid_headless_pane_record()
    assert validate_pane_registry_record(record, tmp_path / "pane.yaml") == []


def test_herdr_inspectable_record_validates(tmp_path: Path):
    record = valid_herdr_pane_record()
    assert validate_pane_registry_record(record, tmp_path / "pane.yaml") == []


def test_herdr_inspectable_requires_pane_id_pco_046_and_pco_049(tmp_path: Path):
    record = valid_herdr_pane_record()
    del record["terminal"]["pane_id"]
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    assert any(error.code == CODE_OPERATOR_VISIBLE for error in errors)


def test_headless_inspectable_requires_surface_ref_pco_049(tmp_path: Path):
    record = valid_headless_pane_record()
    del record["terminal"]["surface_ref"]
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_OPERATOR_VISIBLE for error in errors)


def test_headless_inspectable_requires_pid_pco_046_and_pco_049(tmp_path: Path):
    # ce-ops#207 W2′ C3: a headless/operator_inspectable PTY record carrying a
    # surface_ref but NO pid is malformed. The seat pid is part of the headless
    # surface identity (control-socket ref + pid), so both the schema conditional
    # and the validator predicate must reject the missing-pid record.
    record = valid_headless_pane_record()
    del record["terminal"]["pid"]
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    # Schema conditional requires terminal.pid for the headless kind.
    assert any(error.code == CODE_SCHEMA for error in errors)
    # Validator surface predicate mirrors the schema and flags the missing pid.
    assert any(error.code == CODE_OPERATOR_VISIBLE for error in errors)


def test_inspectable_class_with_tmux_terminal_is_refused_pco_049(tmp_path: Path):
    # The declared visibility class must match its backing terminal kind.
    record = valid_headless_pane_record()
    record["terminal"] = {
        "kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3",
    }
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_OPERATOR_VISIBLE for error in errors)


def test_visible_class_with_headless_terminal_is_refused_pco_049(tmp_path: Path):
    record = valid_pane_record()  # visibility=operator_visible
    record["terminal"] = {"kind": "headless", "surface_ref": "/s/attach.sock", "pid": 9}
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_OPERATOR_VISIBLE for error in errors)


def test_visible_class_with_herdr_terminal_is_refused_pco_049(tmp_path: Path):
    record = valid_pane_record()  # visibility=operator_visible
    record["terminal"] = {
        "kind": "herdr",
        "surface_ref": "/run/ce/herdr/control.sock",
        "pane_id": "pane-1",
        "pid": 9,
    }
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_OPERATOR_VISIBLE for error in errors)


def test_terminal_status_requires_close_reason_pco_048(tmp_path: Path):
    record = valid_pane_record()
    record["status"] = "closed"
    record["closed_at"] = "2026-05-23T08:00:00Z"
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_ROLE_STATUS for error in errors)


def test_terminal_status_with_close_reason_passes_pco_048(tmp_path: Path):
    record = valid_pane_record()
    record["status"] = "closed"
    record["closed_at"] = "2026-05-23T08:00:00Z"
    record["close_reason"] = "completed"
    assert validate_pane_registry_record(record, tmp_path / "pane.yaml") == []


def test_invented_terminal_reason_field_is_refused_pco_053(tmp_path: Path):
    record = valid_pane_record()
    record["status"] = "closed"
    record["closed_at"] = "2026-05-23T08:00:00Z"
    record["terminal_reason"] = "completed"
    errors = validate_pane_registry_record(record, tmp_path / "pane.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_live_pane_must_bind_to_matching_live_claim_pco_050(tmp_path: Path):
    pane = valid_pane_record()
    _write(tmp_path / "panes" / "pane.yaml", pane)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_LEDGER_BINDING for error in result.errors)


def test_live_pane_matching_live_claim_passes_pco_050(tmp_path: Path):
    pane = valid_pane_record()
    claim_path = tmp_path / "claims" / "hermes-primary" / "pco-slice3-impl.yaml"
    _write(claim_path, valid_claim_record())
    _write(tmp_path / "panes" / "pane.yaml", pane)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_duplicate_active_claim_role_fails_pco_051(tmp_path: Path):
    claim_path = tmp_path / "claims" / "hermes-primary" / "pco-slice3-impl.yaml"
    _write(claim_path, valid_claim_record())
    _write(tmp_path / "panes" / "pane-a.yaml", valid_pane_record())
    pane_b = valid_pane_record()
    pane_b["pane_id"] = "pane-pco-slice3-impl-002"
    _write(tmp_path / "panes" / "pane-b.yaml", pane_b)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_DUPLICATE_LIVE_PANE for error in result.errors)


def test_terminal_history_duplicate_role_passes_pco_051(tmp_path: Path):
    claim_path = tmp_path / "claims" / "hermes-primary" / "pco-slice3-impl.yaml"
    _write(claim_path, valid_claim_record())
    _write(tmp_path / "panes" / "pane-a.yaml", valid_pane_record())
    pane_b = valid_pane_record()
    pane_b["pane_id"] = "pane-pco-slice3-impl-002"
    pane_b["status"] = "closed"
    pane_b["closed_at"] = "2026-05-23T08:00:00Z"
    pane_b["close_reason"] = "completed"
    _write(tmp_path / "panes" / "pane-b.yaml", pane_b)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_container_binding_must_match_existing_container_pco_052(tmp_path: Path):
    claim_path = tmp_path / "claims" / "hermes-primary" / "pco-slice3-impl.yaml"
    _write(claim_path, valid_claim_record())
    pane = valid_pane_record()
    pane["container_instance_ref"] = "containers/inst-pco-slice3-001.yaml"
    pane["container_instance_id"] = "inst-pco-slice3-001"
    _write(tmp_path / "panes" / "pane.yaml", pane)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_CONTAINER_BINDING for error in result.errors)


def test_container_binding_matching_container_passes_pco_052(tmp_path: Path):
    claim_path = tmp_path / "claims" / "hermes-primary" / "pco-slice3-impl.yaml"
    _write(claim_path, valid_claim_record())
    _write(tmp_path / "containers" / "inst-pco-slice3-001.yaml", valid_container_record())
    pane = valid_pane_record()
    pane["container_instance_ref"] = "containers/inst-pco-slice3-001.yaml"
    pane["container_instance_id"] = "inst-pco-slice3-001"
    _write(tmp_path / "panes" / "pane.yaml", pane)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_container_binding_claim_context_mismatch_fails_pco_052(tmp_path: Path):
    claim_path = tmp_path / "claims" / "hermes-primary" / "pco-slice3-impl.yaml"
    _write(claim_path, valid_claim_record())
    container = valid_container_record()
    container["claim_id"] = "other-claim"
    _write(tmp_path / "containers" / "inst-pco-slice3-001.yaml", container)
    pane = valid_pane_record()
    pane["container_instance_ref"] = "containers/inst-pco-slice3-001.yaml"
    pane["container_instance_id"] = "inst-pco-slice3-001"
    _write(tmp_path / "panes" / "pane.yaml", pane)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_CONTAINER_BINDING for error in result.errors)


# ---------------------------------------------------------------------------
# ce-ops#43 — the reaper tmux executor's pane-registry close step (§6.3).
# When a venue is torn down the executor marks the pane record closed/aborted
# with close_reason + closed_at, preserving terminal identity + worktree path,
# and the result must still validate against the pane-registry schema.
# ---------------------------------------------------------------------------

import json as _json
from types import SimpleNamespace as _NS

from creator_engine_validator import reaper_executors as _reaper_executors
from creator_engine_validator import seat_reaper as _seat_reaper


def _active_pane_record(controller_id="ctrl-x", lane_id="reap-lane", worktree="/tmp/wt"):
    return {
        "kind": "pane-registry-record", "record_type": "pane_identity", "schema_version": "1",
        "controller_id": controller_id, "lane_id": lane_id,
        "claim_ref": f"claims/{controller_id}/{lane_id}.yaml", "host_id": "ce-dev-1",
        "pane_id": "venue-pane", "role": "reviewer", "status": "active",
        "record_timestamp": "2026-06-13T11:55:00Z", "registered_at": "2026-06-13T11:55:00Z",
        "last_seen_at": "2026-06-13T11:55:00Z", "visibility": "operator_visible",
        "terminal": {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"},
        "worktree_path": worktree,
    }


def _pane_absent_runner(calls):
    """A fake tmux runner: pane already absent (list-panes empty) so kill is a no-op."""
    def runner(argv, **kw):
        argv = list(argv)
        calls.append(argv)
        if "list-panes" in argv:
            return _NS(returncode=0, stdout="", stderr="")  # no panes ⇒ absent
        return _NS(returncode=0, stdout="", stderr="")
    return runner


def _close_plan(tmp_path, *, release_reason, pane_registry_path):
    return _seat_reaper.RetirementPlan(
        seat_id="run-x", run_id="run-x", classification=_seat_reaper.CLASS_ELIGIBLE,
        release_reason=release_reason, state_root=tmp_path, dispatch={}, dispatch_path=tmp_path,
        events_path=tmp_path, archive_root=tmp_path, batch_slug="run-x", role="reviewer",
        terminal={"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"},
        harness_session_id=None, transcript_ref=None, archive_expected=False, lane_id="reap-lane",
        controller_id="ctrl-x", ledger_root=tmp_path, worktree_path=tmp_path / "wt",
        pane_registry_path=pane_registry_path,
    )


def test_reaper_close_venue_marks_pane_closed_completed_schema_valid(tmp_path):
    pane_path = tmp_path / "pane.yaml"
    pane_path.write_text(yaml.safe_dump(_active_pane_record(worktree=str(tmp_path / "wt"))), encoding="utf-8")
    calls = []
    executor = _reaper_executors.TmuxExecutor(runner=_pane_absent_runner(calls))
    result = executor.close_venue(_close_plan(tmp_path, release_reason="completed", pane_registry_path=pane_path))
    assert result.status in (_seat_reaper.STEP_SUCCEEDED, _seat_reaper.STEP_ALREADY_SATISFIED)
    rec = yaml.safe_load(pane_path.read_text())
    assert rec["status"] == "closed" and rec["close_reason"] == "completed" and rec["closed_at"]
    # terminal identity + worktree preserved
    assert rec["terminal"]["pane_id"] == "%3" and rec["worktree_path"] == str(tmp_path / "wt")
    # the transitioned record still validates against the pane-registry schema
    assert validate_pane_registry_record(rec, pane_path) == []


def test_reaper_close_venue_marks_pane_aborted_for_archive_then_retire(tmp_path):
    pane_path = tmp_path / "pane.yaml"
    pane_path.write_text(yaml.safe_dump(_active_pane_record()), encoding="utf-8")
    executor = _reaper_executors.TmuxExecutor(runner=_pane_absent_runner([]))
    result = executor.close_venue(_close_plan(tmp_path, release_reason="aborted", pane_registry_path=pane_path))
    assert result.status in (_seat_reaper.STEP_SUCCEEDED, _seat_reaper.STEP_ALREADY_SATISFIED)
    rec = yaml.safe_load(pane_path.read_text())
    assert rec["status"] == "aborted" and rec["close_reason"] == "aborted"
    assert validate_pane_registry_record(rec, pane_path) == []


def test_reaper_close_venue_pane_registry_write_failure_is_flagged(tmp_path):
    # a malformed (non-mapping) pane record → registry update fails → FAILED + flag,
    # so the policy stops before worktree release (§6.3).
    pane_path = tmp_path / "pane.yaml"
    pane_path.write_text("- not a mapping\n", encoding="utf-8")
    executor = _reaper_executors.TmuxExecutor(runner=_pane_absent_runner([]))
    result = executor.close_venue(_close_plan(tmp_path, release_reason="completed", pane_registry_path=pane_path))
    assert result.status == _seat_reaper.STEP_FAILED
    assert result.data.get("pane_registry_failed") is True
