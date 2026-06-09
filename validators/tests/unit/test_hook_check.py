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
import shutil
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


# --- Gate B: posture-claim reachability (injection-first) ------------------
#
# The §7 hard-deny fires ONLY under posture=="governed" (see
# test_governed_bash_git_push_denies). Before Gate B a seat's posture was
# resolved by rglob-ing the WHOLE posture-root tree, which matched tracked
# examples/**/claims fixtures as live governing claims — load-bearing for
# worktree-seat governance, but a footgun. Gate B makes a seat's REAL ledger
# reachable via a launch-pinned --ledger-root (CE_LEDGER_ROOT) and scopes
# discovery to that ledger (else <posture_root>/.hermes/active-work-ledger),
# never the whole tree. The four tests below are the mandatory regression
# guards protecting the sacred push/deploy hard-deny.


def _write_real_ledger(ledger_root: Path, lane: str = "real-lane", controller: str = "hermes-primary") -> None:
    """Write a live claim + a cleanly-bound live tmux pane under a real ledger root.

    Mirrors the on-disk layout ``lane_runtime.launch`` writes: claims under
    ``claims/<controller>/<lane>.yaml`` and panes under ``panes/<controller>/<lane>.yaml``.
    """
    claims = ledger_root / "claims" / controller
    panes = ledger_root / "panes" / controller
    claims.mkdir(parents=True, exist_ok=True)
    panes.mkdir(parents=True, exist_ok=True)
    (claims / f"{lane}.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        'schema_version: "1"\n'
        f"controller_id: {controller}\n"
        f"lane_id: {lane}\n"
        f'record_timestamp: "source-controlled:claims/{controller}/{lane}.yaml"\n'
        f"worktree_path: /worktrees/{lane}\n"
        f"envelope_ref: .hermes/envelopes/{lane}.md\n"
        "lease_seconds: 3600\n"
        f'claimed_at: "source-controlled:claims/{controller}/{lane}.yaml"\n'
        f'last_heartbeat_at: "source-controlled:claims/{controller}/{lane}.yaml"\n',
        encoding="utf-8",
    )
    (panes / f"{lane}.yaml").write_text(
        "kind: pane-registry-record\n"
        "record_type: pane_identity\n"
        'schema_version: "1"\n'
        f"controller_id: {controller}\n"
        f"lane_id: {lane}\n"
        f"claim_ref: claims/{controller}/{lane}.yaml\n"
        "host_id: workstation-a\n"
        f"pane_id: pane-{lane}-001\n"
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


def _worktree_with_examples_footgun(base: Path) -> Path:
    """A worktree-like checkout carrying the tracked examples/** fixtures but NO
    real local ledger — exactly the layout that used to flip a worktree seat to
    governed via a fixture. Returns the worktree root."""
    wt = base / "wt"
    wt.mkdir(parents=True, exist_ok=True)
    shutil.copytree(EXAMPLES / "well-formed/pane-registry", wt / "examples/well-formed/pane-registry")
    return wt


def test_gate_b_regression_1_real_ledger_pinned_seat_governed_via_real_claim(tmp_path):
    # (1) A real allocated (ledger-pinned) worktree seat resolves `governed` via
    # its REAL claim — not any examples/** fixture. The worktree tree even carries
    # the examples footgun, yet the pinned ledger wins.
    real_ledger = tmp_path / "root" / ".hermes" / "active-work-ledger"
    _write_real_ledger(real_ledger, lane="real-lane")
    wt = _worktree_with_examples_footgun(tmp_path)

    posture, claim = hook_check._resolve_posture(
        {}, "auto", str(wt), ledger_root=str(real_ledger)
    )
    assert posture == "governed"
    # The binding is the REAL claim, never the example "pco-slice3-impl" fixture.
    assert claim is not None
    assert claim.record["lane_id"] == "real-lane"

    # And the public build_context() path agrees.
    ctx = hook_check.build_context(
        _edit_event("README.md"), posture_root=str(wt), ledger_root=str(real_ledger)
    )
    assert ctx.posture == "governed"


def test_gate_b_regression_2_unpinned_seat_is_ungoverned(tmp_path):
    # (2) An unallocated / unpinned seat resolves `ungoverned` (advisory). The
    # worktree carries the examples footgun but, with no ledger pin and no real
    # local ledger, the fixtures can no longer flip it to governed.
    wt = _worktree_with_examples_footgun(tmp_path)

    posture, claim = hook_check._resolve_posture({}, "auto", str(wt), ledger_root=None)
    assert posture == "ungoverned"
    assert claim is None

    ctx = hook_check.build_context(_edit_event("README.md"), posture_root=str(wt))
    assert ctx.posture == "ungoverned"


def test_gate_b_regression_3_git_push_under_governed_seat_is_hard_denied(tmp_path):
    # (3) THE SACRED INVARIANT: `git push` under a real governed seat is still
    # HARD-DENIED (decision=="deny"). This exercises the full posture-resolution
    # path (ledger pin -> governed) feeding the restricted-mechanic hard deny, so
    # the Gate B scope-out cannot silently downgrade the hard-deny to advisory.
    real_ledger = tmp_path / "root" / ".hermes" / "active-work-ledger"
    _write_real_ledger(real_ledger, lane="real-lane")
    wt = _worktree_with_examples_footgun(tmp_path)

    ctx = hook_check.build_context(
        _bash_event("git push origin main"),
        posture_root=str(wt),
        ledger_root=str(real_ledger),
    )
    assert ctx.posture == "governed"
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"


def test_gate_b_regression_4_examples_can_never_govern_over_root_checkout(tmp_path):
    # (4) No examples/** (or snapshot) path can ever be the governing claim,
    # evaluated over a root checkout — even when a real (but live-claim-free)
    # ledger directory is present. Discovery is scoped to the real ledger, so the
    # tracked fixtures are excluded by construction.
    root = tmp_path / "root-checkout"
    root.mkdir()
    # A real ledger dir that exists but holds no live claim.
    (root / ".hermes" / "active-work-ledger").mkdir(parents=True)
    shutil.copytree(EXAMPLES / "well-formed/pane-registry", root / "examples/well-formed/pane-registry")

    posture, claim = hook_check._resolve_posture({}, "auto", str(root), ledger_root=None)
    assert posture == "ungoverned"
    assert claim is None


def test_gate_b_ledger_root_via_ce_block_fallback(tmp_path):
    # The launch-pinned ledger root may also arrive in the event's ce extension
    # block (ce.ledger_root), mirroring ce.posture_root — build_context honors it.
    real_ledger = tmp_path / "root" / ".hermes" / "active-work-ledger"
    _write_real_ledger(real_ledger, lane="real-lane")
    wt = _worktree_with_examples_footgun(tmp_path)

    event = _edit_event("README.md")
    event["ce"] = {"ledger_root": str(real_ledger)}
    ctx = hook_check.build_context(event, posture_root=str(wt))
    assert ctx.posture == "governed"
