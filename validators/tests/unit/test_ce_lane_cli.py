"""Unit tests for the ``ce`` CLI lane command family (RV1-030/031/032).

Drives ``creator_engine_validator.ce_cli.main`` directly. tmux is replaced by
a test double via the monkeypatchable adapter factory so refusals and the
record-write path can be exercised without a real tmux process.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator.tmux_adapter import TmuxPane


class FakeAdapter:
    kind = "tmux"

    def __init__(self, *, available: bool = True):
        self._available = available
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return self._available

    def ensure_pane(self, *, session, window, command):
        self.spawned.append((session, window, list(command)))
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3", pane_tty="/dev/pts/9", pane_pid=4242)


@pytest.fixture()
def use_fake_tmux(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: adapter)
    return adapter


def _prompt(tmp_path: Path) -> tuple[Path, str]:
    p = tmp_path / "prompt.md"
    p.write_text("gate3 prompt\n", encoding="utf-8")
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


def _ledger(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "active-work-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _claim(ledger: Path, controller="hermes-primary", lane="gate3-lane", *, released=False) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "record_timestamp": f"source-controlled:claims/{controller}/{lane}.yaml",
        "worktree_path": "/worktrees/gate3-lane",
        "envelope_ref": "envelopes/gate3.md",
        "branch": "implementer/gate3-lane",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller}/{lane}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller}/{lane}.yaml",
    }
    if released:
        record["released_at"] = "2026-05-25T04:05:00Z"
        record["release_reason"] = "completed"
    path = ledger / "claims" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _launch_argv(tmp_path, ledger, prompt, sha, **extra):
    argv = [
        "lane", "launch",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--role", "implementer",
        "--prompt", str(prompt),
        "--prompt-sha", sha,
        "--repo-root", str(tmp_path),
        "--ledger-root", str(ledger),
    ]
    for k, v in extra.items():
        flag = "--" + k.replace("_", "-")
        if v is True:
            argv.append(flag)
        else:
            argv.extend([flag, str(v)])
    return argv


def _pane_path(ledger, controller="hermes-primary", lane="gate3-lane"):
    return ledger / "panes" / controller / f"{lane}.yaml"


# ---------------------------------------------------------------------------
# --help reachability (argparse wiring)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["--help"],
    ["lane", "--help"],
    ["lane", "launch", "--help"],
    ["lane", "status", "--help"],
    ["lane", "verify", "--help"],
    ["lane", "archive", "--help"],
])
def test_help_is_reachable(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# Required RED tests — launch refusals before side effects
# ---------------------------------------------------------------------------


def test_ce_lane_launch_refuses_prompt_sha_mismatch_before_side_effects(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, _ = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, "0" * 64))
    assert ret != 0
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []


def test_ce_lane_launch_refuses_missing_live_claim_before_side_effects(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)  # no claim
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret != 0
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []


def test_ce_lane_launch_refuses_released_claim_before_side_effects(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger, released=True)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret != 0
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []


def test_ce_lane_launch_refuses_headless_or_non_tmux_for_visibility_required_role(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha, no_tmux=True))
    assert ret != 0
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []


def test_ce_lane_launch_refuses_tmux_unavailable_before_pane_write(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: FakeAdapter(available=False))
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret != 0
    assert not _pane_path(ledger).exists()


# ---------------------------------------------------------------------------
# Required RED test — launch writes a pane registry record bound to the claim
# ---------------------------------------------------------------------------


def test_ce_lane_launch_writes_pane_registry_record_bound_to_live_claim(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret == 0
    pane = _pane_path(ledger)
    assert pane.is_file()
    record = yaml.safe_load(pane.read_text(encoding="utf-8"))
    assert record["claim_ref"] == "claims/hermes-primary/gate3-lane.yaml"
    assert record["terminal"]["kind"] == "tmux"
    assert record["visibility"] == "operator_visible"
    assert use_fake_tmux.spawned, "tmux pane should have been spawned"


# ---------------------------------------------------------------------------
# Required RED test — status reads the live pane record
# ---------------------------------------------------------------------------


def test_ce_lane_status_reads_live_pane_record(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    capsys.readouterr()
    ret = ce_cli.main([
        "lane", "status",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--json",
    ])
    assert ret == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["record"]["lane_id"] == "gate3-lane"
    assert payload["record"]["terminal"]["kind"] == "tmux"


def test_ce_lane_status_missing_record_exits_nonzero(tmp_path):
    ledger = _ledger(tmp_path)
    ret = ce_cli.main([
        "lane", "status",
        "--controller-id", "hermes-primary",
        "--lane-id", "absent",
        "--ledger-root", str(ledger),
    ])
    assert ret != 0


# ---------------------------------------------------------------------------
# Required RED test — verify refuses missing stop line
# ---------------------------------------------------------------------------


def test_ce_lane_verify_refuses_missing_stop_line(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    transcript = tmp_path / "t.txt"
    transcript.write_text("no terminal line here\n", encoding="utf-8")
    ret = ce_cli.main([
        "lane", "verify",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--transcript", str(transcript),
        "--stop-line", "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION",
    ])
    assert ret != 0


def test_ce_lane_verify_ok_with_stop_line(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    stop = "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION"
    transcript = tmp_path / "t.txt"
    transcript.write_text(f"work\n{stop}\n", encoding="utf-8")
    ret = ce_cli.main([
        "lane", "verify",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--transcript", str(transcript),
        "--stop-line", stop,
    ])
    assert ret == 0


# ---------------------------------------------------------------------------
# Required RED test — archive hashes transcript bytes (CLI surface)
# ---------------------------------------------------------------------------


def test_ce_lane_archive_hashes_transcript_bytes(tmp_path, capsys):
    transcript = tmp_path / "pane.txt"
    body = b"transcript bytes\nstop\n"
    transcript.write_bytes(body)
    archive_root = tmp_path / "out"  # outside repo
    ret = ce_cli.main([
        "lane", "archive",
        "--transcript", str(transcript),
        "--archive-root", str(archive_root),
        "--batch-slug", "gate3",
        "--role", "implementer",
    ])
    assert ret == 0
    out = capsys.readouterr().out
    expected = hashlib.sha256(body).hexdigest()
    assert expected in out
