from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest

import creator_engine_validator.model_drift_watcher as watcher_module
from creator_engine_validator.model_drift_watcher import (
    CANON_PROVENANCE_SHA256,
    CanonSeat,
    ModelCanon,
    ModelCanonError,
    ModelDriftConfigError,
    ModelDriftWatcher,
    Observation,
    load_config,
    load_model_canon,
    probe_seat,
)


def _canon() -> ModelCanon:
    return ModelCanon(
        CANON_PROVENANCE_SHA256,
        (CanonSeat("ce-vps-codex", "ce-vps-codex", "/home/ce/.codex/config.toml", "gpt-5.6-terra", "high", "0.144.1"),),
    )


def _observation(
    state: str,
    at: float,
    *,
    model: str | None = None,
    effort: str | None = None,
    version: str | None = None,
) -> Observation:
    return Observation("ce-vps-codex", state, at, model=model, effort=effort, version=version)


def test_tracked_canon_is_schema_valid_and_provenance_bound(repo_root: Path, tmp_path: Path):
    canon = load_model_canon(repo_root / "surfaces/model-canon.yaml")
    assert canon.provenance_sha256 == CANON_PROVENANCE_SHA256
    bad = tmp_path / "bad.yaml"
    bad.write_text("schema_version: 1\nprovenance_sha256: " + "0" * 64 + "\nseats: []\n", encoding="utf-8")
    with pytest.raises(ModelCanonError):
        load_model_canon(bad)


def test_probe_uses_fixed_argv_and_classifies_match_and_each_drift():
    calls: list[list[str]] = []
    def runner(argv, **kwargs):
        calls.append(argv)
        output = 'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "high"\n' if argv[-1].endswith("toml") else "codex 0.144.1\n"
        return subprocess.CompletedProcess(argv, 0, output, "")
    seat = _canon().seats[0]
    assert probe_seat(seat, runner=runner, now=1).state == "match"
    assert calls == [["docker", "exec", "ce-vps-codex", "cat", "/home/ce/.codex/config.toml"], ["docker", "exec", "ce-vps-codex", "codex", "--version"]]
    for config, version, expected in (("model = 'other'\nmodel_reasoning_effort = 'high'\n", "codex 0.144.1\n", "model_drift"), ("model = 'gpt-5.6-terra'\nmodel_reasoning_effort = 'low'\n", "codex 0.144.1\n", "effort_drift"), ("model = 'gpt-5.6-terra'\nmodel_reasoning_effort = 'high'\n", "codex 0.144.0\n", "version_drift")):
        def changed(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, config if argv[-1].endswith("toml") else version, "")
        assert probe_seat(seat, runner=changed, now=1).state == expected


@pytest.mark.parametrize("stderr,expected", [("No such container", "unknown_missing_container"), ("broken", "unknown_command_failure")])
def test_failed_observations_are_unknown(stderr: str, expected: str):
    def failing(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, "", stderr)
    assert probe_seat(_canon().seats[0], runner=failing, now=1).state == expected


def test_timeout_is_unknown():
    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 10)
    assert probe_seat(_canon().seats[0], runner=timeout, now=1).state == "unknown_timeout"


def test_debounce_alarm_clear_ack_and_restart_persistence(tmp_path: Path):
    state, inbox = tmp_path / "state.json", tmp_path / "inbox.ndjson"
    watcher = ModelDriftWatcher(_canon(), state_path=state, inbox_path=inbox, journal_sink=lambda _: None)
    assert watcher.observe([_observation("model_drift", 0)]) == []
    assert watcher.observe([_observation("model_drift", 60)]) == []
    alarms = watcher.observe([_observation("model_drift", 120)])
    assert len(alarms) == 1 and alarms[0]["journal_identifier"] == "ce-model-drift"
    watcher.state["seats"]["ce-vps-codex"]["acknowledged"] = True
    watcher.observe([_observation("unknown_timeout", 180)])
    restarted = ModelDriftWatcher(_canon(), state_path=state, inbox_path=inbox, journal_sink=lambda _: None)
    assert restarted.state["seats"]["ce-vps-codex"]["acknowledged"] is True
    restarted.observe([_observation("match", 240)])
    restarted.observe([_observation("match", 300)])
    assert restarted.state["seats"]["ce-vps-codex"]["active"] is False
    assert stat.S_IMODE(state.stat().st_mode) == 0o600


def test_dedicated_environment_rejects_credentials_unknowns_and_relative_paths():
    env = {"CE_MODEL_DRIFT_CANON": "/canon", "CE_MODEL_DRIFT_STATE_PATH": "/state", "CE_MODEL_DRIFT_LEASE_ROOT": "/leases", "CE_MODEL_DRIFT_INBOX_PATH": "/inbox", "CE_MODEL_DRIFT_CADENCE_SECONDS": "60"}
    assert load_config(env).cadence_seconds == 60
    with pytest.raises(ModelDriftConfigError): load_config({**env, "GH_TOKEN": "no"})
    with pytest.raises(ModelDriftConfigError): load_config({**env, "CE_MODEL_DRIFT_UNSAFE": "x"})
    with pytest.raises(ModelDriftConfigError): load_config({**env, "CE_MODEL_DRIFT_CANON": "relative"})


def test_pending_alarm_survives_append_failure_and_retries_once_after_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state, inbox = tmp_path / "state.json", tmp_path / "inbox.ndjson"
    watcher = ModelDriftWatcher(_canon(), state_path=state, inbox_path=inbox, journal_sink=lambda _: None)
    watcher.observe([_observation("model_drift", 0)])
    watcher.observe([_observation("model_drift", 60)])
    original = watcher_module._append_ndjson
    monkeypatch.setattr(watcher_module, "_append_ndjson", lambda *_: (_ for _ in ()).throw(OSError("inbox unavailable")))
    with pytest.raises(OSError, match="inbox unavailable"):
        watcher.observe([_observation("model_drift", 120)])
    pending = watcher.state["seats"]["ce-vps-codex"]
    assert pending["alarm_pending"] is True
    event_id = pending["event_id"]
    assert pending["pending_alarm"]["event_id"] == event_id

    monkeypatch.setattr(watcher_module, "_append_ndjson", original)
    restarted = ModelDriftWatcher(_canon(), state_path=state, inbox_path=inbox, journal_sink=lambda _: None)
    assert restarted.observe([_observation("model_drift", 180)]) == []
    assert restarted.state["seats"]["ce-vps-codex"]["alarm_delivered"] is True
    records = [__import__("json").loads(line) for line in inbox.read_text(encoding="utf-8").splitlines()]
    assert [record["event_id"] for record in records] == [event_id]
    restarted.observe([_observation("model_drift", 240)])
    assert inbox.read_text(encoding="utf-8").count(event_id) == 1


def test_crash_after_append_is_deduplicated_and_pending_failure_does_not_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state, inbox = tmp_path / "state.json", tmp_path / "inbox.ndjson"
    watcher = ModelDriftWatcher(_canon(), state_path=state, inbox_path=inbox, journal_sink=lambda _: None)
    watcher.observe([_observation("model_drift", 0)])
    watcher.observe([_observation("model_drift", 60)])
    original = watcher_module._append_ndjson
    monkeypatch.setattr(watcher_module, "_append_ndjson", lambda *_: (_ for _ in ()).throw(OSError("append failed")))
    with pytest.raises(OSError):
        watcher.observe([_observation("model_drift", 120)])
    pending = watcher.state["seats"]["ce-vps-codex"]
    with pytest.raises(OSError):
        watcher.observe([_observation("match", 180)])
    assert watcher.state["seats"]["ce-vps-codex"]["alarm_pending"] is True
    monkeypatch.setattr(watcher_module, "_append_ndjson", original)

    # Simulate a process death after the fsynced append but before its state ack.
    original(inbox, pending["pending_alarm"])
    restarted = ModelDriftWatcher(_canon(), state_path=state, inbox_path=inbox, journal_sink=lambda _: None)
    restarted.observe([_observation("model_drift", 180)])
    assert restarted.state["seats"]["ce-vps-codex"]["alarm_delivered"] is True
    assert len(inbox.read_text(encoding="utf-8").splitlines()) == 1


def test_fingerprint_starts_immediately_and_resets_for_different_drift(tmp_path: Path):
    watcher = ModelDriftWatcher(_canon(), state_path=tmp_path / "state.json", inbox_path=tmp_path / "inbox.ndjson", journal_sink=lambda _: None)
    model = _observation("model_drift", 0, model="other", effort="high", version="0.144.1")
    effort = _observation("effort_drift", 60, model="gpt-5.6-terra", effort="low", version="0.144.1")
    watcher.observe([model])
    first = dict(watcher.state["seats"]["ce-vps-codex"])
    assert first["mismatch_count"] == 1 and first["first_seen"] == 0
    watcher.observe([effort])
    second = watcher.state["seats"]["ce-vps-codex"]
    assert second["mismatch_count"] == 1 and second["first_seen"] == 60
    assert second["fingerprint"] != first["fingerprint"]
    watcher.observe([_observation("unknown_timeout", 120)])
    assert watcher.state["seats"]["ce-vps-codex"]["fingerprint"] == second["fingerprint"]
    watcher.observe([_observation("effort_drift", 180, model="gpt-5.6-terra", effort="low", version="0.144.1")])
    watcher.observe([_observation("effort_drift", 240, model="gpt-5.6-terra", effort="low", version="0.144.1")])
    assert watcher.state["seats"]["ce-vps-codex"]["alarm_delivered"] is True
    watcher.observe([_observation("match", 300)])
    watcher.observe([_observation("match", 360)])
    assert watcher.state["seats"]["ce-vps-codex"]["active"] is False
