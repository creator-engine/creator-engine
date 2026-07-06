from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import ce_cli


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    _write(
        state / "watchers" / "duty-manifest.yaml",
        (
            "kind: ce-controller-duty-manifest\n"
            "schema_version: 1\n"
            "duties:\n"
            "  - id: queue-watch\n"
            "    type: watcher\n"
            "    rearm_command: [ce, queue, status, --json]\n"
            "  - id: conveyor-daemon\n"
            "    type: daemon\n"
            "    rearm_command: [ce, conveyor-daemon, run, --dry-run]\n"
        ),
    )


def _patch_ring0_pass(monkeypatch) -> None:
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


def test_takeover_dry_run_text_reports_actions_without_mutation(tmp_path, monkeypatch, capsys):
    _seed_takeover_state(tmp_path)
    _patch_ring0_pass(monkeypatch)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    rc = ce_cli.main(
        [
            "takeover",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "ce takeover (dry-run): no state will be mutated" in out
    assert "predecessor: ce-controller (detected)" in out
    assert "Ring-0 verify: PASS" in out
    assert "initial state: AWAITING-OPERATOR" in out
    assert "enter-awaiting-operator" in out
    assert "would re-arm duties:" in out
    assert "re-arm-watcher queue-watch" in out
    assert "re-arm-daemon conveyor-daemon" in out
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert after == before


def test_takeover_dry_run_json_emits_evidence_packet(tmp_path, monkeypatch, capsys):
    _seed_takeover_state(tmp_path)
    _patch_ring0_pass(monkeypatch)

    rc = ce_cli.main(
        [
            "takeover",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "ce-takeover-evidence-packet"
    assert payload["predecessor"] == {"requested": "ce-controller", "detected": True}
    assert payload["selected_harness"] == "claude"
    assert payload["ring0_verify"]["ok"] is True
    assert payload["initial_state"] == "AWAITING-OPERATOR"
    assert {action["execute"] for action in payload["hydration_plan"]} == {False}
    assert payload["raw_controller_launch_refusal"]["code"] == (
        "READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED"
    )
    assert payload["raw_controller_launch_refusal"]["recovery_command"] == (
        f"ce takeover --from ce-controller --harness claude --repo-root {tmp_path} --dry-run"
    )
    rearm = payload["re_arm_plan"]
    assert rearm["status"] == "found"
    assert {action["execute"] for action in rearm["actions"]} == {False}
    assert {(action["duty_id"], action["duty_type"]) for action in rearm["actions"]} == {
        ("queue-watch", "watcher"),
        ("conveyor-daemon", "daemon"),
    }
    assert {source["name"] for source in payload["evidence_sources"]} >= {
        "lifecycle_records",
        "brain_bootstrap",
        "active_work_ledger",
        "merge_queue",
        "approval_wall",
        "watcher_manifest",
    }


def test_takeover_reports_missing_inputs_as_evidence_gaps(tmp_path, monkeypatch, capsys):
    _patch_ring0_pass(monkeypatch)

    rc = ce_cli.main(
        [
            "takeover",
            "--from",
            "missing-seat",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["predecessor"]["detected"] is False
    gap_names = {gap["name"] for gap in payload["evidence_gaps"]}
    assert "ce_state_root" in gap_names
    assert "watcher_manifest" in gap_names
    assert payload["re_arm_plan"]["status"] == "missing"


def test_takeover_duty_manifest_dry_run_never_executes_rearm_commands(
    tmp_path, monkeypatch, capsys
):
    _seed_takeover_state(tmp_path)
    marker = tmp_path / "marker-created-by-rearm"
    manifest = tmp_path / ".ce" / "state" / "watchers" / "duty-manifest.yaml"
    manifest.write_text(
        (
            "kind: ce-controller-duty-manifest\n"
            "schema_version: 1\n"
            "duties:\n"
            "  - id: marker-watch\n"
            "    type: watcher\n"
            f"    rearm_command: [sh, -c, 'touch {marker}']\n"
        ),
        encoding="utf-8",
    )
    _patch_ring0_pass(monkeypatch)

    rc = ce_cli.main(
        [
            "takeover",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["re_arm_plan"]["actions"][0]["command"] == [
        "sh",
        "-c",
        f"touch {marker}",
    ]
    assert not marker.exists()


def test_takeover_harness_validation_refusal_is_machine_readable(
    tmp_path, monkeypatch, capsys
):
    _seed_takeover_state(tmp_path)
    monkeypatch.setattr(
        ce_cli.launch_runtime,
        "_require_launch_pinned_foreman_contract",
        lambda: None,
    )
    monkeypatch.setattr(
        ce_cli.launch_runtime,
        "harness_binary_check",
        lambda harness, which=None: {
            "ok": False,
            "detail": "missing harness binary",
            "harness": harness,
            "binary": harness,
            "resolved": None,
        },
    )

    rc = ce_cli.main(
        [
            "takeover",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
            "--json",
        ]
    )

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ring0_verify"]["ok"] is False
    gates = payload["ring0_verify"]["launch_runtime_report"]["gates"]
    assert any(
        gate["name"] == "harness-binary" and gate["status"] == "WOULD-REFUSE"
        for gate in gates
    )


def test_takeover_live_execution_refuses_until_later_slice(tmp_path, capsys):
    rc = ce_cli.main(
        [
            "takeover",
            "--from",
            "ce-controller",
            "--harness",
            "claude",
            "--repo-root",
            str(tmp_path),
        ]
    )

    assert rc == 2
    err = capsys.readouterr().err
    assert "CE-TAKEOVER-LIVE-DEFERRED" in err
