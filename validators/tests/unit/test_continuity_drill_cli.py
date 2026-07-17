from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import ce_cli
from creator_engine_validator import continuity_drill_runtime as drill


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    current = path.parent
    while current != current.parent:
        current.chmod(0o700)
        if current.name == ".ce":
            break
        current = current.parent
    path.chmod(0o600)


def _seed_takeover_state(root: Path, predecessor: str = "ce-controller") -> None:
    state = root / ".ce" / "state"
    _write(
        state / "seats" / "host-a" / f"{predecessor}.yaml",
        f"record_type: seat_lifecycle\nseat_id: {predecessor}\n",
    )
    _write(
        state / "dispatches" / predecessor / "events.jsonl",
        json.dumps({"event": "launched", "seat_id": predecessor}) + "\n",
    )
    _write(state / "sessions" / f"{predecessor}-resume.json", '{"resume": true}\n')
    _write(state / "brain" / "assertions.yaml", "records: []\n")
    _write(state / "active-work-ledger" / "ledger.jsonl", "{}\n")
    _write(state / "merge-queue" / "queue.json", "[]\n")
    _write(state / "approval-wall" / "state.json", '{"armed": true}\n')
    _write(state / "watchers" / "manifest.yaml", "watchers: []\n")


def _patch_drill_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        ce_cli.launch_runtime,
        "_require_launch_pinned_foreman_contract",
        lambda: None,
    )
    monkeypatch.setattr(
        ce_cli.launch_runtime,
        "harness_binary_check",
        lambda harness, which=None: {
            "ok": True,
            "detail": f"{harness} resolved",
            "harness": harness,
            "binary": harness,
            "resolved": f"/usr/bin/{harness}",
        },
    )
    monkeypatch.setattr(
        drill.controller_posture,
        "_ring0_confirmed",
        lambda *, harness, repo_root: True,
    )
    monkeypatch.setattr(
        drill.controller_posture,
        "_ring1_active",
        lambda *, harness, repo_root: True,
    )
    monkeypatch.setattr(
        drill.controller_posture,
        "_approval_wall_armed",
        lambda repo_root: False,
    )


def _standby_liveness_json() -> str:
    return json.dumps(
        {
            "ring0_verify": {"ok": True},
            "initial_state": "AWAITING-OPERATOR",
        }
    )


def test_cadence_weekly_until_two_consecutive_clean_runs():
    first = drill.compute_cadence(as_of="2026-07-06", prior_runs=())
    assert first.phase == "weekly-until-two-clean-runs"
    assert first.required is True
    assert first.reason == "weekly_due"
    assert first.next_due == "2026-07-06"

    early = drill.compute_cadence(
        as_of="2026-07-06",
        prior_runs=(drill.parse_prior_run("2026-07-01:clean"),),
    )
    assert early.required is False
    assert early.reason == "weekly_not_due"
    assert early.consecutive_clean_runs == 1
    assert early.next_due == "2026-07-08"

    promotion_gated = drill.compute_cadence(
        as_of="2026-07-06",
        prior_runs=(
            drill.parse_prior_run("2026-07-01:clean"),
            drill.parse_prior_run("2026-06-24:clean"),
        ),
    )
    assert promotion_gated.phase == "promotion-gated"
    assert promotion_gated.required is False
    assert promotion_gated.reason == "two_consecutive_clean_runs_satisfied"
    assert promotion_gated.next_due == "before-controller-substrate-promotion"


def test_promotion_candidate_requires_drill_after_clean_streak():
    cadence = drill.compute_cadence(
        as_of="2026-07-06",
        prior_runs=(
            drill.parse_prior_run("2026-07-01:clean"),
            drill.parse_prior_run("2026-06-24:clean"),
        ),
        promotion_candidate=True,
    )

    assert cadence.phase == "promotion-gated"
    assert cadence.required is True
    assert cadence.reason == "controller_substrate_promotion"


def test_continuity_drill_json_proves_benign_gate_cycle_without_mutation(
    tmp_path, monkeypatch, capsys
):
    _seed_takeover_state(tmp_path)
    _patch_drill_pass(monkeypatch)
    monkeypatch.setattr(drill, "_current_run_at", lambda: "2026-07-06T17:00:00Z")
    monkeypatch.setattr(drill.seat_lifecycle, "default_host_id", lambda: "host-a")
    monkeypatch.setenv("CE_STANDBY_LIVENESS_JSON", _standby_liveness_json())
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--as-of",
            "2026-07-06",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "ce-continuity-drill-record"
    assert payload["run_at"] == "2026-07-06T17:00:00Z"
    assert payload["host_id"] == "host-a"
    assert payload["cadence"]["phase"] == "weekly-until-two-clean-runs"
    assert payload["cadence"]["required"] is True
    assert payload["benign_gate_cycle"]["without_predecessor_chat_history"] is True
    assert payload["benign_gate_cycle"]["proof_mode"] == "plan-only"
    assert payload["benign_gate_cycle"]["no_side_effects"] is True
    assert payload["benign_gate_cycle"]["forbidden_mechanics_present"] is False
    assert {item["present"] for item in payload["benign_gate_cycle"]["forbidden_mechanics"]} == {False}
    assert {action["execute"] for action in payload["benign_gate_cycle"]["takeover_actions"]} == {False}
    assert payload["takeover_evidence"]["dry_run"] is True
    assert payload["takeover_evidence"]["predecessor"]["detected"] is True
    assert payload["takeover_evidence"]["state_root_diagnostic"]["writable_durability"] == "not-proven"
    assert payload["standby_liveness"]["ok"] is True
    assert payload["status"] == "GREEN"
    assert payload["clean"] is True
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert after == before


def test_unsafe_state_root_diagnostic_makes_drill_red_without_mutation(
    tmp_path, monkeypatch, capsys
):
    _seed_takeover_state(tmp_path)
    _patch_drill_pass(monkeypatch)
    (tmp_path / ".ce" / "state").chmod(0o755)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    diagnostic = payload["takeover_evidence"]["state_root_diagnostic"]
    assert rc == 1
    assert payload["status"] == "RED"
    assert diagnostic["status"] == "refused"
    assert "SRP-MODE" in diagnostic["error_codes"]
    assert diagnostic["nonce_created"] is False
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert after == before


def test_continuity_drill_records_standby_liveness_when_context_provided(
    tmp_path, monkeypatch, capsys
):
    _seed_takeover_state(tmp_path)
    _patch_drill_pass(monkeypatch)
    monkeypatch.setenv("CE_STANDBY_LIVENESS_JSON", _standby_liveness_json())

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["standby_liveness"]["ok"] is True
    assert payload["standby_liveness"]["evidence"]["initial_state"] == "AWAITING-OPERATOR"
    assert payload["status"] == "GREEN"
    assert payload["clean"] is True


def test_continuity_drill_rejects_raw_standby_liveness_env_flag(
    tmp_path, monkeypatch, capsys
):
    _seed_takeover_state(tmp_path)
    _patch_drill_pass(monkeypatch)
    monkeypatch.setenv("CE_STANDBY_LIVENESS", "1")

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "WARNING"
    assert payload["clean"] is False
    assert payload["standby_liveness"]["ok"] is False
    assert payload["standby_liveness"]["evidence"]["source"] == "CE_STANDBY_LIVENESS"
    assert "not accepted as standby proof" in payload["standby_liveness"]["note"]


def test_continuity_drill_rejects_direct_boolean_standby_liveness(
    tmp_path, monkeypatch
):
    _seed_takeover_state(tmp_path)
    _patch_drill_pass(monkeypatch)

    record = drill.build_record(
        predecessor="ce-controller",
        harness="claude",
        repo_root=tmp_path,
        standby_liveness=True,
    )

    assert record.status == "WARNING"
    assert record.clean is False
    assert record.standby_liveness.ok is False
    assert record.standby_liveness.evidence["source"] == "boolean"
    assert "structured ce takeover --dry-run --json" in record.standby_liveness.note


def test_continuity_drill_warns_when_standby_liveness_absent(
    tmp_path, monkeypatch, capsys
):
    _seed_takeover_state(tmp_path)
    _patch_drill_pass(monkeypatch)

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "WARNING"
    assert payload["clean"] is False
    assert payload["standby_liveness"]["ok"] is False
    assert payload["standby_liveness"]["note"] == drill.STANDBY_LIVENESS_ABSENT_NOTE


def test_continuity_drill_reports_missing_predecessor_as_not_clean(
    tmp_path, monkeypatch, capsys
):
    _patch_drill_pass(monkeypatch)

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "missing-seat",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--as-of",
            "2026-07-06",
            "--json",
        ]
    )

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["clean"] is False
    assert payload["takeover_evidence"]["predecessor"]["detected"] is False
    assert payload["benign_gate_cycle"]["no_side_effects"] is True


def test_continuity_drill_json_abort_record_on_exception_path(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(drill, "_current_run_at", lambda: "2026-07-06T17:01:00Z")
    monkeypatch.setattr(drill.seat_lifecycle, "default_host_id", lambda: "host-a")

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--prior-run",
            "not-a-run",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["kind"] == "ce-continuity-drill-record"
    assert payload["clean"] is False
    assert payload["aborted"] is True
    assert payload["error_code"] == "CE-CONTINUITY-DRILL-BAD-HISTORY"
    assert payload["run_at"] == "2026-07-06T17:01:00Z"
    assert payload["host_id"] == "host-a"
    assert payload["predecessor"] == "ce-controller"
    assert payload["selected_harness"] == "claude"
    assert "ERROR: ce continuity-drill refused [CE-CONTINUITY-DRILL-BAD-HISTORY]" in captured.err


def test_continuity_drill_json_abort_record_on_takeover_exception(tmp_path, monkeypatch, capsys):
    _patch_drill_pass(monkeypatch)
    monkeypatch.setattr(drill, "_current_run_at", lambda: "2026-07-06T17:02:00Z")
    monkeypatch.setattr(drill.seat_lifecycle, "default_host_id", lambda: "host-a")

    def fail_plan(**_kwargs):
        raise drill.takeover_runtime.LiveTakeoverNotImplemented("live takeover refused")

    monkeypatch.setattr(drill.takeover_runtime, "build_plan", fail_plan)

    rc = ce_cli.main(
        [
            "continuity-drill",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["clean"] is False
    assert payload["aborted"] is True
    assert payload["error_code"] == "CE-TAKEOVER-LIVE-DEFERRED"
    assert payload["run_at"] == "2026-07-06T17:02:00Z"
    assert payload["host_id"] == "host-a"
    assert "ERROR: ce continuity-drill refused [CE-TAKEOVER-LIVE-DEFERRED]" in captured.err
