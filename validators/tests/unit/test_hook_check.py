"""Unit tests for the CC-G-B validator-backed hook bridge (``hook_check``).

These tests pin the deterministic decision logic that a future Claude
``command``-type hook (CC-G-C) will call via
``creator_engine_validator hook-check``. They exercise the pure
``evaluate(event, context)`` surface plus the posture predicate, scope,
mechanics, secret, and Stop/closeout semantics required by
``docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`` §5-§7.

Scope discipline: these tests never launch Claude, never spawn a pane,
never write ``.claude/**``, and never read real credential bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import hook_check
from creator_engine_validator.checks import mutation_class
from creator_engine_validator.checks import pane_registry


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples"


def _edit_event(file_path: str, tool: str = "Edit") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": file_path},
    }


def _bash_event(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def _read_event(file_path: str, tool_input_extra: dict | None = None) -> dict:
    tool_input = {"file_path": file_path}
    if tool_input_extra:
        tool_input.update(tool_input_extra)
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": tool_input,
    }


MANIFEST = ("validators/creator_engine_validator/hook_check.py", "schemas/completion-report.schema.yaml")


# --- Scope (PreToolUse Edit/Write/MultiEdit) -------------------------------


def test_governed_out_of_manifest_edit_is_advisory_allow():
    # G-i (v3 kickoff): a governed path-manifest mismatch is now ADVISORY
    # (allow-with-warning), not a hard deny — scope containment moved to the
    # PR-diff gate. Secret/mechanic denies stay hard (see below).
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_edit_event("README.md"), ctx)
    assert decision.posture == "governed"
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert decision.would_have_denied is True
    assert decision.hook_specific_output["permissionDecision"] == "allow"
    assert "manifest" in decision.reason.lower()
    assert decision.ok is True


def test_governed_in_manifest_edit_allows():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(
        _edit_event("validators/creator_engine_validator/hook_check.py"), ctx
    )
    assert decision.decision == "allow"
    assert decision.hook_specific_output["permissionDecision"] == "allow"


def test_governed_write_in_manifest_allows():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(
        _edit_event("schemas/completion-report.schema.yaml", tool="Write"), ctx
    )
    assert decision.decision == "allow"


def test_governed_multiedit_out_of_manifest_is_advisory_allow():
    # G-i: governed manifest mismatch is advisory for MultiEdit too.
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_edit_event("src/app.py", tool="MultiEdit"), ctx)
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert decision.would_have_denied is True


def test_ungoverned_out_of_manifest_edit_is_advisory_allow():
    ctx = hook_check.HookContext(posture="ungoverned", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_edit_event("README.md"), ctx)
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert decision.would_have_denied is True
    # advisory must still report what would have been denied
    assert "manifest" in decision.reason.lower()


def test_governed_evidence_root_write_allows():
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=MANIFEST,
        evidence_root=".hermes/cc-g-b-hook-bridge-implementation/",
    )
    decision = hook_check.evaluate(
        _edit_event(".hermes/cc-g-b-hook-bridge-implementation/20260526T000000Z/x.txt", tool="Write"),
        ctx,
    )
    assert decision.decision == "allow"


# --- Mechanics (PreToolUse Bash) -------------------------------------------


def test_governed_bash_git_push_denies():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 72 --squash",
        "gh pr review 72 --approve",
        "gh pr comment 72 --body hi",
        "git push --force origin main",
        "git branch -D landing/x",
        "npm publish",
    ],
)
def test_governed_bash_restricted_mechanics_deny(command):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny", command


def test_governed_bash_safe_command_allows():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git status --porcelain -uall"), ctx)
    assert decision.decision == "allow"


def test_mechanics_classification_reuses_reserved_restricted():
    # The mechanics seam must anchor to the shared mutation-class
    # reserved-restricted vocabulary rather than a bespoke parallel list.
    action = hook_check.classify_mechanics("git push origin main")
    assert action in mutation_class.RESERVED_RESTRICTED
    assert hook_check.classify_mechanics("gh pr merge 1") in mutation_class.RESERVED_RESTRICTED
    assert hook_check.classify_mechanics("git status") is None


def test_governed_bash_with_reviewer_authority_envelope_allows_matching_pr_review():
    # G2.007.2: a bounded, validated reviewer-authority envelope opens exactly its mechanic on
    # exactly its PR — a raw loose token no longer authorizes anything, and the envelope does not
    # open an unrelated mechanic.
    envelope = {
        "mechanic": "pr_review",
        "pr_number": 106,
        "head_sha": "aa02b0ceb192b38f52da0d99f798e1e2710a8a22",
        "actor": "ubuntuaws745-cmyk",
        "ratified_prompt_sha": "ae1b9db11155f4ad841ef3fa399cd508c64d1ff184d1e0d1437e859c0dacfe27",
        "emitting_role": "operator",
        "operating_mode": "strict",
    }
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST, side_effect_authority=envelope)
    assert hook_check.evaluate(_bash_event("gh pr review 106 --approve"), ctx).decision == "allow"
    # the same pr_review envelope does NOT open an unrelated restricted mechanic
    assert hook_check.evaluate(_bash_event("git push origin main"), ctx).decision == "deny"


def test_ungoverned_bash_restricted_is_advisory_allow():
    ctx = hook_check.HookContext(posture="ungoverned", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "allow"
    assert decision.would_have_denied is True


# --- Secrets (PreToolUse Read) ---------------------------------------------


@pytest.mark.parametrize(
    "file_path",
    [".env", ".env.production", "secrets/prod.yaml", "config/id_rsa", "app/credentials.json"],
)
def test_governed_secret_read_denies(file_path):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_read_event(file_path), ctx)
    assert decision.decision == "deny", file_path


def test_governed_normal_read_allows():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_read_event("README.md"), ctx)
    assert decision.decision == "allow"


def test_secret_reason_does_not_echo_tool_input_values():
    # The bridge must not reflect arbitrary tool_input fields (which a
    # caller might use to smuggle secret material) into the decision.
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    event = _read_event(".env", tool_input_extra={"injected": "SUPER_SECRET_VALUE_42"})
    decision = hook_check.evaluate(event, ctx)
    assert decision.decision == "deny"
    serialized = json.dumps(decision.to_dict())
    assert "SUPER_SECRET_VALUE_42" not in serialized


def test_ungoverned_secret_read_is_advisory_allow():
    ctx = hook_check.HookContext(posture="ungoverned", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_read_event(".env"), ctx)
    assert decision.decision == "allow"
    assert decision.would_have_denied is True


# --- Stop / completion-report closeout -------------------------------------


GOOD_CLOSEOUT = """## Summary

Did the thing.

## Recommended immediate next step

Ratify the next gate.

## Exact next Source prompt pointer+SHA256

path: foo.md
sha256: """ + ("0" * 64)


NO_NEXT_GATE_CLOSEOUT = """## Summary

Done.

## Recommended immediate next step

Nothing further.

## Exact next Source prompt pointer+SHA256

No next gate: roadmap milestone complete; awaiting Source direction.
"""


def test_stop_without_closeout_blocks():
    ctx = hook_check.HookContext(posture="governed", closeout_text="just some text, no sections")
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "block"
    assert decision.hook_specific_output["hookEventName"] == "Stop"
    assert "Summary" in decision.reason


def test_stop_with_full_closeout_allows():
    ctx = hook_check.HookContext(posture="governed", closeout_text=GOOD_CLOSEOUT)
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "allow"


def test_stop_with_no_next_gate_statement_allows():
    ctx = hook_check.HookContext(posture="governed", closeout_text=NO_NEXT_GATE_CLOSEOUT)
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "allow"


def test_stop_blocks_on_malformed_completion_report():
    malformed = EXAMPLES / "malformed/completion-reports/missing-envelope-sha256.yaml"
    ctx = hook_check.HookContext(
        posture="governed",
        closeout_text=GOOD_CLOSEOUT,
        completion_report_path=str(malformed),
    )
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "block"
    assert "CR-001" in decision.reason


def test_stop_allows_well_formed_completion_report():
    well_formed = EXAMPLES / "well-formed/completion-reports/class-a-example.yaml"
    ctx = hook_check.HookContext(
        posture="governed",
        closeout_text=GOOD_CLOSEOUT,
        completion_report_path=str(well_formed),
    )
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "allow"


# --- Decision JSON shape ---------------------------------------------------


def test_pretooluse_decision_to_dict_shape():
    # Pin the deny-shaped to_dict() via a still-hard deny (restricted mechanic);
    # the manifest mismatch is advisory post-G-i, so a deny case must come from a
    # secret/mechanic reason.
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    payload = decision.to_dict()
    assert payload["ok"] is True
    assert payload["hookEventName"] == "PreToolUse"
    assert payload["posture"] == "governed"
    assert payload["decision"] == "deny"
    assert payload["reason"]
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert hso["permissionDecisionReason"] == payload["reason"]


# --- Posture predicate (reuse of pane_registry posture inputs) -------------


def test_posture_governed_from_live_pane_and_claim():
    result = pane_registry.evaluate_posture([EXAMPLES / "well-formed/pane-registry"])
    assert result.posture == "governed"


def test_posture_ungoverned_with_no_live_claim(tmp_path):
    result = pane_registry.evaluate_posture([tmp_path])
    assert result.posture == "ungoverned"


def test_posture_ambiguous_live_claim_falls_closed_to_governed(tmp_path):
    # A live unreleased claim with no resolvable bound live pane is the
    # ambiguous-inside-a-lane case: §7 requires failing closed (governed).
    claim_dir = tmp_path / ".hermes/active-work-ledger/claims/hermes-primary"
    claim_dir.mkdir(parents=True)
    (claim_dir / "lane.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        "schema_version: \"1\"\n"
        "controller_id: hermes-primary\n"
        "lane_id: orphan-lane\n"
        "record_timestamp: \"source-controlled:lane.yaml\"\n"
        "worktree_path: /worktrees/orphan-lane\n"
        "envelope_ref: .hermes/envelopes/orphan.md\n"
        "lease_seconds: 3600\n"
        "claimed_at: \"source-controlled:lane.yaml\"\n"
        "last_heartbeat_at: \"source-controlled:lane.yaml\"\n",
        encoding="utf-8",
    )
    result = pane_registry.evaluate_posture([tmp_path])
    assert result.posture == "governed"
    assert result.ambiguous_fell_closed is True
