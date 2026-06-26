"""Integration: a workspace bootstrapped via ``ce brain init`` passes the
lane-launch ``G3-BRAIN-BOOTSTRAP-REFUSED`` gate (ce-ops#206).

This is the end-to-end contract for the new genesis-bootstrap surface: a
freshly-installed CE workspace (no hand-run brain step) must come up able to
launch a governed lane. We drive both legs through the real ``ce`` CLI
(``ce brain init`` then ``ce lane launch``) so the gate the launch path
actually enforces is exercised, not a stand-in.

tmux is replaced by a test double via the monkeypatchable adapter factory so
no real terminal is required; the ledger and brain state live under
``tmp_path`` and no production worktree is mutated.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, ce_cli
from creator_engine_validator.tmux_adapter import TmuxPane
pytestmark = pytest.mark.slow



class FakeAdapter:
    kind = "tmux"

    def __init__(self) -> None:
        self.spawned: list[tuple[str, str, list[str], str | None]] = []

    def is_available(self) -> bool:
        return True

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append((session, window, list(command), cwd))
        return TmuxPane(
            session_id="$1", window_id="@2", pane_id="%3",
            pane_tty="/dev/pts/9", pane_pid=4242,
        )


@pytest.fixture()
def use_fake_tmux(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: adapter)
    return adapter


def _claim(ledger: Path, controller="hermes-primary", lane="gate3-lane") -> Path:
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
    path = ledger / "claims" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _prompt(tmp_path: Path) -> tuple[Path, str]:
    p = tmp_path / "prompt.md"
    p.write_text("gate3 prompt\n", encoding="utf-8")
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


def test_brain_init_then_lane_launch_passes_brain_gate(tmp_path, use_fake_tmux, capsys):
    # The lane-launch brain gate reads <repo-root>/.ce/state — mirror the
    # default state-root the brain commands resolve against.
    state_root = tmp_path / ".ce" / "state"
    assert not brain_runtime.ledger_path(state_root).is_file()

    # Leg 1: bootstrap the genesis ledger via the new CLI surface.
    assert ce_cli.main(["brain", "init", "--state-root", str(state_root)]) == 0
    assert brain_runtime.verify_ledger(state_root).ok is True
    capsys.readouterr()

    # Leg 2: a governed lane launch over the same workspace now passes the
    # G3-BRAIN-BOOTSTRAP-REFUSED gate and writes its pane registry record.
    ledger = tmp_path / ".hermes" / "active-work-ledger"
    ledger.mkdir(parents=True, exist_ok=True)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)

    ret = ce_cli.main(
        [
            "lane", "launch",
            "--controller-id", "hermes-primary",
            "--lane-id", "gate3-lane",
            "--role", "implementer",
            "--prompt", str(prompt),
            "--prompt-sha", sha,
            "--repo-root", str(tmp_path),
            "--ledger-root", str(ledger),
        ]
    )

    captured = capsys.readouterr()
    assert "G3-BRAIN-BOOTSTRAP-REFUSED" not in captured.err
    assert ret == 0
    assert use_fake_tmux.spawned, "lane launch should have spawned a pane"
    pane = ledger / "panes" / "hermes-primary" / "gate3-lane.yaml"
    assert pane.is_file()
