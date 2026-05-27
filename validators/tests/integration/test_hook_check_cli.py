"""Integration tests for ``creator_engine_validator hook-check``.

Exercises the CLI seam a future Claude ``command``-type hook (CC-G-C)
will invoke: JSON-in (``--stdin`` / ``--input-json``), JSON-decision-out,
exit ``0`` for evaluated allow/deny/block decisions, non-zero only for
invalid input. No Claude launch, no pane spawn, no ``.claude/**`` writes.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from creator_engine_validator.cli import main


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples"


def _run(argv, capsys, stdin_text=None, monkeypatch=None):
    if stdin_text is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def test_hook_check_stdin_governed_deny(capsys, monkeypatch):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "README.md"},
        "ce": {"posture": "governed", "manifest_paths": ["schemas/x.yaml"]},
    }
    code, out = _run(["hook-check", "--stdin"], capsys, json.dumps(event), monkeypatch)
    assert code == 0  # deny is a decision, not a CLI crash
    payload = json.loads(out)
    assert payload["decision"] == "deny"
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert payload["posture"] == "governed"


def test_hook_check_input_json_file(capsys, tmp_path):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "schemas/x.yaml"},
        "ce": {"posture": "governed", "manifest_paths": ["schemas/x.yaml"]},
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event), encoding="utf-8")
    code, out = _run(["hook-check", "--input-json", str(event_file)], capsys)
    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "allow"


def test_hook_check_requires_an_input_mode(capsys):
    # Neither --stdin nor --input-json: invalid arguments -> non-zero exit.
    with pytest.raises(SystemExit) as exc:
        main(["hook-check"])
    assert exc.value.code != 0


def test_hook_check_invalid_json_exits_nonzero(capsys, monkeypatch):
    code, out = _run(["hook-check", "--stdin"], capsys, "{not json", monkeypatch)
    assert code != 0


def test_hook_check_stop_block_via_closeout_file(capsys, tmp_path, monkeypatch):
    closeout = tmp_path / "closeout.md"
    closeout.write_text("no canonical sections here", encoding="utf-8")
    event = {"hook_event_name": "Stop", "ce": {"posture": "governed"}}
    code, out = _run(
        ["hook-check", "--stdin", "--closeout-file", str(closeout)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "block"
    assert payload["hookSpecificOutput"]["hookEventName"] == "Stop"


def test_hook_check_posture_auto_governed_from_examples(capsys, monkeypatch):
    posture_root = EXAMPLES / "well-formed/pane-registry"
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "README.md"},
        "ce": {"manifest_paths": ["schemas/x.yaml"]},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--posture", "auto", "--posture-root", str(posture_root)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "governed"
    assert payload["decision"] == "deny"


def test_hook_check_posture_auto_ungoverned_empty(capsys, tmp_path, monkeypatch):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "README.md"},
        "ce": {"manifest_paths": ["schemas/x.yaml"]},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--posture", "auto", "--posture-root", str(tmp_path)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "ungoverned"
    assert payload["decision"] == "allow"
    assert payload["advisory"] is True


def test_hook_check_manifest_doc_parsing(capsys, monkeypatch):
    handoff = EXAMPLES / "well-formed/handoffs/example-handoff.md"
    # In-manifest path from the fenced ALLOWED_PATHS block -> allow.
    in_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "docs/example/file-a.md"},
        "ce": {"posture": "governed"},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--manifest-doc", str(handoff)],
        capsys,
        json.dumps(in_event),
        monkeypatch,
    )
    assert code == 0
    assert json.loads(out)["decision"] == "allow"

    out_event = dict(in_event)
    out_event["tool_input"] = {"file_path": "docs/example/not-listed.md"}
    code, out = _run(
        ["hook-check", "--stdin", "--manifest-doc", str(handoff)],
        capsys,
        json.dumps(out_event),
        monkeypatch,
    )
    assert code == 0
    assert json.loads(out)["decision"] == "deny"


def test_hook_check_end_to_end_governed_lane(capsys, tmp_path, monkeypatch):
    # Construct a governed posture root: a live tmux pane bound to a live
    # unreleased claim whose envelope_ref points at a handoff carrying a
    # fenced ALLOWED_PATHS manifest. This is the canonical hook path.
    root = tmp_path
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
    (root / ".hermes/handoff.md").write_text(
        "# handoff\n\nALLOWED_PATHS_COUNT=1\n"
        "ALLOWED_PATHS_SHA256=" + _sha_for(["docs/keep.md"]) + "\n\n"
        "```text\ndocs/keep.md\n```\n",
        encoding="utf-8",
    )

    base = {"hook_event_name": "PreToolUse", "tool_name": "Edit"}

    allow_event = dict(base, tool_input={"file_path": "docs/keep.md"})
    code, out = _run(
        ["hook-check", "--stdin", "--posture-root", str(root)],
        capsys,
        json.dumps(allow_event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "governed"
    assert payload["decision"] == "allow"

    deny_event = dict(base, tool_input={"file_path": "docs/other.md"})
    code, out = _run(
        ["hook-check", "--stdin", "--posture-root", str(root)],
        capsys,
        json.dumps(deny_event),
        monkeypatch,
    )
    assert code == 0
    assert json.loads(out)["decision"] == "deny"


def _sha_for(paths):
    import hashlib

    normalized = "\n".join(sorted(set(p for p in paths if p))) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
