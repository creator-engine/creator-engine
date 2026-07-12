from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from creator_engine_validator import ce_cli, daemon_heartbeat_alarm as alarms


# NOW anchors the deterministic classifier tests: all boundary assertions (e.g.
# 181 s vs 180 s grace) share one fixed instant so skew is zero.
# The CLI-path test (test_cli_human_json_and_exit_contract) stamps its fixtures
# at CALL TIME via `base=datetime.now(timezone.utc)` because the production
# clock is used on that path — if the import-time anchor is reused, a slow CI
# serial suite (collection-to-execution > interval × grace_factor = 180 s)
# causes the "fresh" fixture to appear STALE.
NOW = datetime.now(timezone.utc)


def _heartbeat(daemon_id: str, *, status: str = "running", age: int = 0, interval: int = 60, base: datetime | None = None) -> dict[str, object]:
    anchor = base if base is not None else NOW
    return {
        "schema_version": 1,
        "daemon_id": daemon_id,
        "pass_index": 1,
        "ts": (anchor - timedelta(seconds=age)).isoformat().replace("+00:00", "Z"),
        "status": status,
        "expected_interval_seconds": interval,
    }


def _write(directory, daemon_id: str, **kwargs) -> None:
    directory.mkdir(exist_ok=True)
    (directory / f"{daemon_id}.json").write_text(json.dumps(_heartbeat(daemon_id, **kwargs)), encoding="utf-8")


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, "OK"),
        ({"age": 181}, "STALE"),
        ({"status": "failed", "age": 181}, "FAILED"),
        ({"status": "stopping", "age": 181}, "FAILED"),
        ({"status": "starting"}, "FAILED"),
    ],
)
def test_classification_matrix(tmp_path, kwargs, expected) -> None:
    _write(tmp_path, "belt", **kwargs)
    report = alarms.check_heartbeats(tmp_path, grace_factor=3, expected_daemons=("belt",), now=NOW)
    assert report["daemons"][0]["state"] == expected
    assert report["ok"] is (expected == "OK")


def test_missing_and_malformed_files_fail_closed_by_stem(tmp_path) -> None:
    (tmp_path / "broken.json").write_text("{nope", encoding="utf-8")
    report = alarms.check_heartbeats(tmp_path, grace_factor=3, expected_daemons=("belt",), now=NOW)
    assert {entry["daemon_id"]: entry["state"] for entry in report["daemons"]} == {"belt": "MISSING", "broken": "FAILED"}


def test_environment_overrides_and_invalid_values_retain_defaults(tmp_path) -> None:
    config = alarms.configuration_from_environment({"CE_HEARTBEAT_STATE_DIR": str(tmp_path), "CE_HEARTBEAT_GRACE_FACTOR": "4", "CE_HEARTBEAT_EXPECTED_DAEMONS": "belt,other"})
    assert config == (tmp_path, 4.0, ("belt", "other"))
    _, grace, expected = alarms.configuration_from_environment({"CE_HEARTBEAT_GRACE_FACTOR": "zero", "CE_HEARTBEAT_EXPECTED_DAEMONS": "BAD"})
    assert grace == 3.0 and expected == alarms.DEFAULT_EXPECTED_DAEMONS


def test_alarm_append_is_deduplicated_within_window(tmp_path) -> None:
    report = alarms.check_heartbeats(tmp_path, grace_factor=3, expected_daemons=("belt",), now=NOW)
    inbox = tmp_path / "inbox" / "daemon-alarms.ndjson"
    assert len(alarms.append_new_alarms(report, inbox, now=NOW)) == 1
    assert alarms.append_new_alarms(report, inbox, now=NOW + timedelta(seconds=1)) == []
    assert len(alarms.append_new_alarms(report, inbox, now=NOW + timedelta(seconds=301))) == 1


def test_cli_human_json_and_exit_contract(tmp_path, monkeypatch, capsys) -> None:
    _write(tmp_path, "belt", base=datetime.now(timezone.utc))
    monkeypatch.setenv("CE_HEARTBEAT_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("CE_HEARTBEAT_EXPECTED_DAEMONS", "belt")
    assert ce_cli.main(["heartbeat", "check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    monkeypatch.setenv("CE_HEARTBEAT_EXPECTED_DAEMONS", "belt,integrator")
    assert ce_cli.main(["heartbeat", "check"]) == 1
    assert "[FAIL] integrator: MISSING" in capsys.readouterr().out


def test_oneshot_timer_units_are_tailored_and_safe(repo_root) -> None:
    service = (repo_root / "deploy/systemd/ce-heartbeat-check.service").read_text(encoding="utf-8")
    timer = (repo_root / "deploy/systemd/ce-heartbeat-check.timer").read_text(encoding="utf-8")
    assert "Type=oneshot" in service
    assert "EnvironmentFile=-" in service and "Environment=" not in service
    assert "ExecStart=/usr/bin/env ce heartbeat check --json" in service
    assert "OnUnitActiveSec=5min" in timer and "Persistent=true" in timer
