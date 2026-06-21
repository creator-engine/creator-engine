"""Integration tests for ``ce lane launch`` end-to-end (RV1-030).

Two layers:

* a double-driven end-to-end that proves the written Pane Registry record
  passes the live ``pane_registry`` validator bound to its claim, and
* a real-tmux launch (skipped when tmux is unavailable) that genuinely
  spawns and then tears down a uniquely-named throwaway session.

No production worktree is mutated; the ledger lives under ``tmp_path`` and
any real tmux session is killed in teardown.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, lane_runtime
from creator_engine_validator.checks.pane_registry import run as pane_registry_run
from creator_engine_validator.tmux_adapter import TmuxAdapter, TmuxPane


class DoubleAdapter:
    kind = "tmux"

    def is_available(self) -> bool:
        return True

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        return TmuxPane(
            session_id="$1", window_id="@2", pane_id="%3",
            pane_tty="/dev/pts/0", pane_pid=1234, pane_cwd=(str(cwd) if cwd else None),
        )


def _ledger(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "active-work-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


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


def _write_brain_ledger(state_root: Path) -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-lane-tmux-0001",
        claim={"subject": "lane", "predicate": "bootstrap", "object": "ready"},
        scope="global",
        evidence_ref="validators/tests/integration/test_lane_launch_tmux.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


def test_launch_record_passes_live_pane_registry_check(tmp_path):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    _write_brain_ledger(tmp_path / ".ce" / "state")
    prompt, sha = _prompt(tmp_path)
    lane_runtime.launch(
        controller_id="hermes-primary",
        lane_id="gate3-lane",
        role="implementer",
        prompt=prompt,
        prompt_sha=sha,
        repo_root=tmp_path,
        ledger_root=ledger,
        tmux_adapter=DoubleAdapter(),
    )
    # The pane_registry check, run over the ledger root, must accept the
    # written record AND confirm it binds to the live claim (PCO-050).
    result = pane_registry_run([ledger])
    assert result.ok, [e.format() for e in result.errors]


@pytest.mark.xdist_group("real-tmux")
@pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux not installed")
def test_launch_spawns_real_tmux_session(tmp_path):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    _write_brain_ledger(tmp_path / ".ce" / "state")
    prompt, sha = _prompt(tmp_path)
    session = f"ce-gate3-test-{uuid.uuid4().hex[:8]}"
    try:
        result = lane_runtime.launch(
            controller_id="hermes-primary",
            lane_id="gate3-lane",
            role="implementer",
            prompt=prompt,
            prompt_sha=sha,
            repo_root=tmp_path,
            ledger_root=ledger,
            session=session,
            window="gate3",
            command=["sh", "-c", "sleep 30"],
            tmux_adapter=TmuxAdapter(),
        )
        # the session really exists now
        proc = subprocess.run(
            ["tmux", "has-session", "-t", session], capture_output=True
        )
        assert proc.returncode == 0
        record = yaml.safe_load(result.pane_path.read_text(encoding="utf-8"))
        assert record["terminal"]["kind"] == "tmux"
        assert record["terminal"]["session_id"]
        assert record["terminal"]["pane_id"]
    finally:
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
