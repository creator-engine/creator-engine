from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator.forge.automerge_policy import (
    AutoMergeClassPolicy,
    AutoMergePolicyState,
    AutoMergePolicyStateError,
    save_automerge_policy_state,
    load_decision_records,
)


def _decisions_dir(state_dir: Path) -> Path:
    path = state_dir / "automerge" / "decisions"
    path.mkdir(parents=True)
    return path


def _write_record(path: Path, **overrides) -> None:
    payload = {
        "decision": "GESTURE",
        "rationale": ["run_mode_dev", "class_auto_merge_false"],
        "gates": ["auto_back_gate"],
        "run_mode": "dev",
        "class_flag": False,
        "checks_green": False,
        "reviewDecision": "APPROVED",
        "pr_number": 313,
        "head_sha": "abc123",
        "created_at": "2026-06-28T00:00:00Z",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_load_decision_records_missing_dir_is_empty(tmp_path: Path) -> None:
    assert load_decision_records(tmp_path / ".ce/state") == []


def test_load_decision_records_returns_deterministic_json_objects(tmp_path: Path) -> None:
    state_dir = tmp_path / ".ce/state"
    decisions_dir = _decisions_dir(state_dir)
    _write_record(decisions_dir / "002.json", pr_number=2)
    _write_record(decisions_dir / "001.json", pr_number=1, decision="AUTO")

    records = load_decision_records(state_dir)

    assert [record["pr_number"] for record in records] == [1, 2]
    assert records[0]["decision"] == "AUTO"


def test_load_decision_records_rejects_malformed_json(tmp_path: Path) -> None:
    state_dir = tmp_path / ".ce/state"
    decisions_dir = _decisions_dir(state_dir)
    (decisions_dir / "bad.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(AutoMergePolicyStateError):
        load_decision_records(state_dir)


def test_automerge_status_human_output_maps_gesture_to_manual(tmp_path: Path, capsys) -> None:
    state_dir = tmp_path / ".ce/state"
    decisions_dir = _decisions_dir(state_dir)
    _write_record(decisions_dir / "313-abc123.json")

    result = ce_cli.main(["automerge-status", "--state-dir", str(state_dir)])

    assert result == 0
    out = capsys.readouterr().out
    assert "ce automerge-status: 1 decision record(s)" in out
    assert "PR #313: MANUAL" in out
    assert "rationale      : run_mode_dev, class_auto_merge_false" in out
    assert "gates          : auto_back_gate" in out
    assert "run_mode       : dev" in out
    assert "class_flag     : False" in out
    assert "timestamps     : created_at=2026-06-28T00:00:00Z" in out


def test_automerge_status_reports_policy_file_arming_state(tmp_path: Path, capsys) -> None:
    state_dir = tmp_path / ".ce/state"
    decisions_dir = _decisions_dir(state_dir)
    _write_record(decisions_dir / "313-abc123.json", decision="AUTO", run_mode="ceo")
    save_automerge_policy_state(
        state_dir / "automerge" / "policy.json",
        AutoMergePolicyState(
            run_mode="ceo",
            kill_switch=False,
            classes={"docs": AutoMergeClassPolicy(auto_merge=True)},
            enabling_decision_ref="ce-ops#313-enable",
        ),
    )

    result = ce_cli.main(["automerge-status", "--state-dir", str(state_dir)])

    assert result == 0
    out = capsys.readouterr().out
    assert "arming state   : ARMED(run_mode=ceo)" in out
    assert "enabling_ref   : ce-ops#313-enable" in out
    assert "kill_switch    : False" in out


def test_automerge_status_json_output_preserves_records(tmp_path: Path, capsys) -> None:
    state_dir = tmp_path / ".ce/state"
    decisions_dir = _decisions_dir(state_dir)
    _write_record(decisions_dir / "313-abc123.json", decision="AUTO")

    result = ce_cli.main(["automerge-status", "--state-dir", str(state_dir), "--json"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["state_dir"] == str(state_dir)
    assert payload["records"][0]["decision"] == "AUTO"


def test_automerge_status_reports_malformed_record(tmp_path: Path, capsys) -> None:
    state_dir = tmp_path / ".ce/state"
    decisions_dir = _decisions_dir(state_dir)
    (decisions_dir / "bad.json").write_text("{bad", encoding="utf-8")

    result = ce_cli.main(["automerge-status", "--state-dir", str(state_dir)])

    assert result == 1
    err = capsys.readouterr().err
    assert "ERROR: ce automerge-status: decision records unreadable" in err
