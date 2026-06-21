"""CC-G-D Ring 0 — per-surface end-to-end refusal sweep (strict TDD).

One end-to-end negative test per prohibited Claude surface (seat contract §5),
driven through the ``ce`` CLI with a fake tmux adapter and an injected
hook-pack confirmation seam. Each asserts (a) a non-zero exit, (b) the stable
``CC-D-*`` clause code in stderr, and (c) **no side effect** — no tmux spawn and
no Pane Registry record written. No real Claude binary, tmux session, or network
call is involved.

This is the HARD Ring 0 boundary: the launch/accept refusal happens before any
side effect and cannot be talked around in-band. It does not touch, arm, or
strengthen the committed RUNTIME/DEFEASIBLE hook-pack.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, ce_cli
from creator_engine_validator.tmux_adapter import TmuxPane


class FakeAdapter:
    kind = "tmux"

    def __init__(self, *, available: bool = True):
        self._available = available
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return self._available

    def session_exists(self, session: str) -> bool:
        return False

    def ensure_pane(self, *, session, window, command):
        self.spawned.append((session, window, list(command)))
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3")


@pytest.fixture()
def fake_launch(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: adapter)
    # Pack is NOT confirmed: skip-permissions must refuse; other surfaces refuse
    # regardless (the probe is only consulted for skip-permissions).
    monkeypatch.setattr(ce_cli.launch_runtime, "_confirm_pack", lambda r: False)
    return adapter


# (surface argv token, expected clause)
_LAUNCH_SURFACES = [
    ("--bare", "CC-D-1"),
    ("-p", "CC-D-2"),
    ("--print", "CC-D-2"),
    ("agents", "CC-D-3"),
    ("--agents", "CC-D-3"),
    ("--remote-control", "CC-D-4"),
    ("--setting-sources=user,local", "CC-D-5"),
    ("--dangerously-skip-permissions", "CC-D-6"),
    ("--mcp-config=/etc/global/mcp.json", "CC-D-7"),
]


@pytest.mark.parametrize("surface,clause", _LAUNCH_SURFACES)
def test_ce_launch_refuses_each_prohibited_surface(fake_launch, capsys, surface, clause):
    ret = ce_cli.main(["launch", "--harness", "claude", f"--claude-arg={surface}"])
    assert ret != 0, f"{surface!r} must refuse with a non-zero exit"
    err = capsys.readouterr().err
    assert "G6-LAUNCH-CLAUDE-REFUSED" in err
    assert clause in err, f"{surface!r} must report clause {clause}"
    assert fake_launch.spawned == [], f"{surface!r} must not spawn before refusal"


# ---------------------------------------------------------------------------
# Lane-level end-to-end refusal: proves NO Pane Registry record is written.
# ---------------------------------------------------------------------------


def _write_claim(ledger: Path, controller: str, lane: str) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "record_timestamp": f"source-controlled:claims/{controller}/{lane}.yaml",
        "worktree_path": "/worktrees/cc-g-d-lane",
        "envelope_ref": "none",
        "branch": "implementer/cc-g-d-lane",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller}/{lane}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller}/{lane}.yaml",
    }
    path = ledger / "claims" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _write_brain_ledger(state_root: Path) -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-claude-launch-0001",
        claim={"subject": "controller", "predicate": "bootstrap", "object": "ready"},
        scope="global",
        evidence_ref="validators/tests/integration/test_claude_launch_refusal.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


def test_ce_lane_launch_refuses_claude_bare_no_pane_written(tmp_path, monkeypatch, capsys):
    ledger = tmp_path / ".hermes" / "active-work-ledger"
    ledger.mkdir(parents=True)
    _write_claim(ledger, "hermes-primary", "cc-g-d-lane")
    _write_brain_ledger(tmp_path / ".ce" / "state")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("governed prompt\n", encoding="utf-8")
    prompt_sha = hashlib.sha256(prompt.read_bytes()).hexdigest()

    adapter = FakeAdapter()
    monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: adapter)
    monkeypatch.setattr(ce_cli.lane_runtime, "_confirm_pack", lambda r: True)

    ret = ce_cli.main(
        [
            "lane", "launch",
            "--controller-id", "hermes-primary",
            "--lane-id", "cc-g-d-lane",
            "--role", "implementer",
            "--prompt", str(prompt),
            "--prompt-sha", prompt_sha,
            "--repo-root", str(tmp_path),
            "--ledger-root", str(ledger),
            "--command", "claude",
            "--claude-arg=--bare",
        ]
    )
    assert ret != 0
    err = capsys.readouterr().err
    assert "G3-CLAUDE-REFUSED" in err and "CC-D-1" in err
    assert adapter.spawned == []
    assert not (ledger / "panes" / "hermes-primary" / "cc-g-d-lane.yaml").exists()
