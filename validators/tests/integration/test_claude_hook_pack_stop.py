"""Integration tests for the committed ``ce-stop.sh`` hook (CC-G-C).

Per Source decision D2, the CC-G-C Stop hook is **advisory / observability
only**: it MUST NOT block, and it MUST NOT parse the transcript for closeout
text. Hard Stop blocking (closeout / completion-report pointer verification)
is deferred to the Ring 0 kernel (CC-G-D), which injects the deterministic
pointers this hook is forbidden from inferring. These tests run the real
POSIX-sh hook as a subprocess and prove it never emits a block and records a
best-effort advisory observation under the ignored ``.hermes/`` evidence root.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
pytestmark = pytest.mark.slow


REPO_ROOT = Path(__file__).resolve().parents[3]
STOP = REPO_ROOT / ".claude/hooks/ce-stop.sh"


def _build_governed_root(root: Path) -> Path:
    """A governed posture root with NO compliant closeout — exactly the state
    in which the Ring 2 Stop evaluator *would* block. CC-G-C must still not."""
    claims = root / ".hermes/active-work-ledger/claims/hermes-primary"
    panes = root / ".hermes/pane-registry"
    claims.mkdir(parents=True)
    panes.mkdir(parents=True)
    (claims / "lane.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: e2e-lane\n"
        'record_timestamp: "source-controlled:lane.yaml"\n'
        "worktree_path: /worktrees/e2e-lane\n"
        "envelope_ref: .hermes/handoff.md\n"
        "lease_seconds: 3600\n"
        'claimed_at: "source-controlled:lane.yaml"\n'
        'last_heartbeat_at: "source-controlled:lane.yaml"\n',
        encoding="utf-8",
    )
    (panes / "pane.yaml").write_text(
        "kind: pane-registry-record\n"
        "record_type: pane_identity\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: e2e-lane\n"
        "claim_ref: ../active-work-ledger/claims/hermes-primary/lane.yaml\n"
        "host_id: workstation-a\n"
        "pane_id: pane-e2e-001\n"
        "role: implementer\n"
        "status: active\n"
        'record_timestamp: "2026-05-26T00:00:00Z"\n'
        "visibility: operator_visible\n"
        "terminal:\n"
        "  kind: tmux\n"
        "  session_id: ce\n"
        "  window_id: w\n"
        "  pane_id: '1'\n"
        'registered_at: "2026-05-26T00:00:00Z"\n'
        "last_seen_at: source-controlled:pane.yaml\n",
        encoding="utf-8",
    )
    (root / ".hermes/handoff.md").write_text("# handoff\n", encoding="utf-8")
    return root


def _run_stop(project_dir: Path, event=None, stdin_text=None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    payload = stdin_text if stdin_text is not None else json.dumps(event or {"hook_event_name": "Stop"})
    return subprocess.run(
        [str(STOP)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
    )


def test_governed_stop_never_blocks(tmp_path):
    root = _build_governed_root(tmp_path)
    proc = _run_stop(root, {"hook_event_name": "Stop"})
    assert proc.returncode == 0
    # No blocking decision in any form.
    assert "block" not in proc.stdout
    out = proc.stdout.strip()
    if out:
        assert json.loads(out).get("decision") != "block"


def test_stop_logs_advisory_observation_under_hermes(tmp_path):
    proc = _run_stop(tmp_path, {"hook_event_name": "Stop"})
    assert proc.returncode == 0
    obs = tmp_path / ".hermes/cc-g-c-hook-observations/observations.ndjson"
    assert obs.is_file()
    record = json.loads(obs.read_text(encoding="utf-8").splitlines()[-1])
    assert record["hookEventName"] == "Stop"
    assert record["advisory"] is True
    assert record["blocking"] is False


def test_stop_does_not_parse_transcript(tmp_path):
    # A Stop event referencing a non-compliant transcript/closeout must not
    # cause a block: the hook must not read or evaluate transcript text.
    proc = _run_stop(
        tmp_path,
        {"hook_event_name": "Stop", "transcript_path": "/nonexistent/transcript.jsonl"},
    )
    assert proc.returncode == 0
    assert "block" not in proc.stdout


@pytest.mark.skip(
    reason="CC-G-D arms Stop closeout/completion-report pointer verification (D2); "
    "CC-G-C Stop is advisory/observability-only."
)
def test_stop_blocks_on_missing_completion_report_when_armed_by_cc_g_d(tmp_path):
    # FUTURE (CC-G-D / Ring 0): once the kernel injects a deterministic
    # completion_report_ref + closeout pointer into the Stop event, a governed
    # Stop whose completion report is missing or non-compliant must hard-block.
    # This is intentionally unimplemented in CC-G-C.
    raise AssertionError("Stop hard-block is not armed until CC-G-D")
