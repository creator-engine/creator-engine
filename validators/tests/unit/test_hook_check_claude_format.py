"""Tests for the CC-G-C additive Claude-hook presentation seam.

CC-G-C adds a Ring 2 *presentation* seam on top of the CC-G-B decision
engine without changing any decision semantics:

* ``HookDecision.to_claude_hook_dict()`` renders the minimal Claude Code
  hook output shape (``hookSpecificOutput.permissionDecision`` for
  ``PreToolUse``; ``{"decision": "block", ...}`` for ``Stop``);
* the ``hook-check`` CLI gains ``--format {raw,claude}`` (default ``raw``)
  so the existing raw decision dict stays byte-for-byte backward-compatible.

These are unit tests for the dataclass method plus CLI-level tests for the
flag. No Claude launch, no pane spawn, no ``.claude/**`` writes.
"""

from __future__ import annotations

import io
import json

from creator_engine_validator import brain_bootstrap
from creator_engine_validator.cli import main
from creator_engine_validator.hook_check import HookDecision


# --------------------------------------------------------------------------
# Task A — HookDecision.to_claude_hook_dict()
# --------------------------------------------------------------------------


def test_pretooluse_deny_claude_shape():
    decision = HookDecision(
        ok=True,
        hook_event_name="PreToolUse",
        posture="governed",
        decision="deny",
        reason="tracked path is outside the ratified path manifest",
        would_have_denied=True,
    )
    out = decision.to_claude_hook_dict()
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "tracked path is outside the ratified path manifest",
        }
    }
    # PreToolUse must not carry a top-level Stop-style decision key.
    assert "decision" not in out


def test_pretooluse_allow_claude_shape():
    decision = HookDecision(
        ok=True,
        hook_event_name="PreToolUse",
        posture="governed",
        decision="allow",
        reason="permitted under active manifest / mechanics / secret policy",
    )
    out = decision.to_claude_hook_dict()
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == decision.reason
    assert "decision" not in out


def test_ungoverned_advisory_maps_to_allow():
    decision = HookDecision(
        ok=True,
        hook_event_name="PreToolUse",
        posture="ungoverned",
        decision="allow",
        reason="advisory (ungoverned): would deny — tracked path is outside the ratified path manifest",
        advisory=True,
        would_have_denied=True,
    )
    out = decision.to_claude_hook_dict()
    # An ungoverned advisory deny must never hard-deny: it maps to allow.
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
    # The advisory context is preserved in the reason for observability.
    assert "advisory" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert out.get("decision") != "deny"


def test_stop_block_claude_shape():
    decision = HookDecision(
        ok=True,
        hook_event_name="Stop",
        posture="governed",
        decision="block",
        reason="closeout missing canonical terminal section(s)",
        would_have_denied=True,
    )
    out = decision.to_claude_hook_dict()
    assert out == {
        "decision": "block",
        "reason": "closeout missing canonical terminal section(s)",
    }


def test_stop_allow_emits_no_block():
    decision = HookDecision(
        ok=True,
        hook_event_name="Stop",
        posture="governed",
        decision="allow",
        reason="closeout satisfies the terminal-section contract",
    )
    out = decision.to_claude_hook_dict()
    assert out.get("decision") != "block"
    assert "block" not in json.dumps(out)


# --------------------------------------------------------------------------
# Task B — CLI ``--format {raw,claude}`` (default raw)
# --------------------------------------------------------------------------


def _run(argv, capsys, stdin_text=None, monkeypatch=None):
    if stdin_text is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


_GOVERNED_OUT_OF_MANIFEST = {
    "hook_event_name": "PreToolUse",
    "tool_name": "Edit",
    "tool_input": {"file_path": "README.md"},
    "ce": {"posture": "governed", "manifest_paths": ["schemas/x.yaml"]},
}

_GOVERNED_FOREMAN_IMPLEMENTATION = {
    "hook_event_name": "PreToolUse",
    "tool_name": "Edit",
    "tool_input": {"file_path": "validators/creator_engine_validator/hook_check.py"},
    "ce": {
        "posture": "governed",
        "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
        "mutation_class": "code",
    },
}


def test_cli_format_claude_pretooluse_advisory_allow(capsys, monkeypatch):
    # G-i (v3 kickoff): a governed path-manifest mismatch routed through the
    # live decision path is now an ADVISORY allow, not a hard deny. The minimal
    # Claude shape therefore maps to permissionDecision "allow" (an advisory
    # outcome never hard-denies), with the advisory context in the reason.
    code, out = _run(
        ["hook-check", "--stdin", "--format", "claude"],
        capsys,
        json.dumps(_GOVERNED_OUT_OF_MANIFEST),
        monkeypatch,
    )
    assert code == 0  # an advisory allow is a decision, not a CLI crash
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "allow"
    assert "advisory" in hso["permissionDecisionReason"]
    assert "manifest" in hso["permissionDecisionReason"].lower()
    # Minimal Claude shape: none of the raw decision-dict keys leak through.
    assert "ok" not in payload
    assert "decision" not in payload
    assert "posture" not in payload


def test_cli_format_claude_foreman_pretooluse_denies(capsys, monkeypatch):
    monkeypatch.delenv(brain_bootstrap.BOOTSTRAP_REF_ENV, raising=False)
    monkeypatch.delenv(brain_bootstrap.BOOTSTRAP_SHA256_ENV, raising=False)
    code, out = _run(
        ["hook-check", "--stdin", "--format", "claude"],
        capsys,
        json.dumps(_GOVERNED_FOREMAN_IMPLEMENTATION),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "worker delegation" in hso["permissionDecisionReason"]
    assert "ok" not in payload
    assert "posture" not in payload


def test_cli_format_raw_is_default_and_backward_compatible(capsys, monkeypatch):
    code, default_out = _run(
        ["hook-check", "--stdin"],
        capsys,
        json.dumps(_GOVERNED_OUT_OF_MANIFEST),
        monkeypatch,
    )
    assert code == 0
    default_payload = json.loads(default_out)
    # Raw shape retains the full CC-G-B decision dict. Post-G-i a governed
    # path-manifest mismatch is an advisory allow (allow-with-warning); the
    # raw dict surfaces the advisory flag + would_have_denied.
    assert default_payload["ok"] is True
    assert default_payload["decision"] == "allow"
    assert default_payload["advisory"] is True
    assert default_payload["wouldHaveDenied"] is True
    assert default_payload["posture"] == "governed"
    assert default_payload["hookSpecificOutput"]["permissionDecision"] == "allow"

    code, explicit_out = _run(
        ["hook-check", "--stdin", "--format", "raw"],
        capsys,
        json.dumps(_GOVERNED_OUT_OF_MANIFEST),
        monkeypatch,
    )
    assert code == 0
    # Explicit --format raw is identical to the default.
    assert json.loads(explicit_out) == default_payload


def test_cli_format_claude_stop_block(capsys, tmp_path, monkeypatch):
    closeout = tmp_path / "closeout.md"
    closeout.write_text("no canonical sections here", encoding="utf-8")
    event = {"hook_event_name": "Stop", "ce": {"posture": "governed"}}
    code, out = _run(
        ["hook-check", "--stdin", "--format", "claude", "--closeout-file", str(closeout)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "block"
    assert "reason" in payload
    assert "hookSpecificOutput" not in payload
