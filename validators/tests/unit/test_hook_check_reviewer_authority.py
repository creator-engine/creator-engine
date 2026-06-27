"""G2.007.2 — hook_check honors a bounded reviewer-authority envelope (mechanic + PR match).

The restricted mechanic gh pr review is allowed ONLY when a validated envelope authorizes that
exact mechanic AND the command's target PR; everything else denies. A raw loose token is not
honored (backward compatibility: no envelope => deny as before). Offline.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import hook_check as hc


def _envelope(**override) -> dict:
    rec = {
        "envelope_id": "rva-pr106-reviewer",
        "mechanic": "pr_review",
        "pr_number": 106,
        "head_sha": "aa02b0ceb192b38f52da0d99f798e1e2710a8a22",
        "actor": "ubuntuaws745-cmyk",
        "ratified_prompt_sha": "ae1b9db11155f4ad841ef3fa399cd508c64d1ff184d1e0d1437e859c0dacfe27",
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T10:43:13Z",
    }
    rec.update(override)
    return rec


def _ctx(auth):
    return hc.HookContext(posture="governed", manifest_paths=(), side_effect_authority=auth)


def _bash_event(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


# --- _mechanics_would_deny: the bounded decision ---
def test_pr_review_denied_without_authority():
    assert hc._mechanics_would_deny("gh pr review 106 --approve", _ctx(None)) is not None


def test_pr_review_allowed_with_matching_envelope():
    assert hc._mechanics_would_deny("gh pr review 106 --approve", _ctx(_envelope())) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh api -X POST repos/creator-engine/creator-engine/pulls/106/reviews -f event=APPROVE -f body=LGTM",
        "gh api --method POST repos/creator-engine/creator-engine/pulls/106/reviews --raw-field event=APPROVE --raw-field body=LGTM",
    ],
)
def test_gh_api_review_approve_denied_without_authority_at_runtime(command):
    decision = hc.evaluate(
        _bash_event(command),
        hc.HookContext(
            posture="governed",
            manifest_paths=(),
            side_effect_authority=None,
            seat_class="worker",
        ),
    )

    assert hc.classify_mechanics(command) == "pr_review"
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert "restricted mechanic (pr_review)" in decision.reason


def test_gh_api_review_approve_denied_even_with_matching_pr_review_envelope():
    command = "gh api -X POST repos/creator-engine/creator-engine/pulls/106/reviews -f event=APPROVE -f body=LGTM"
    decision = hc.evaluate(
        _bash_event(command),
        hc.HookContext(
            posture="governed",
            manifest_paths=(),
            side_effect_authority=_envelope(),
            seat_class="worker",
        ),
    )

    assert hc.classify_mechanics(command) == "pr_review"
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert "restricted mechanic (pr_review)" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        "curl -X POST https://api.github.com/repos/creator-engine/creator-engine/pulls/106/reviews -d event=APPROVE",
        "curl --request POST https://api.github.com/repos/creator-engine/creator-engine/pulls/106/reviews --data '{\"event\":\"APPROVE\"}'",
        "curl -X POST repos/creator-engine/creator-engine/pulls/106/reviews --data-raw '{\"event\" : \"approve\"}'",
        "curl --request POST /repos/creator-engine/creator-engine/pulls/106/reviews --data-binary '{\"EVENT\":\"APPROVE\"}'",
        "curl -X POST https://api.github.com/repos/creator-engine/creator-engine/pulls/106/reviews --data-binary @review.json",
        "curl --request POST /repos/creator-engine/creator-engine/pulls/106/reviews --data @-",
    ],
)
def test_curl_api_review_approve_denied_without_authority_at_runtime(command):
    decision = hc.evaluate(
        _bash_event(command),
        hc.HookContext(
            posture="governed",
            manifest_paths=(),
            side_effect_authority=None,
            seat_class="worker",
        ),
    )

    assert hc.classify_mechanics(command) == "pr_review"
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    gh_decision = hc.evaluate(
        _bash_event("gh api -X POST repos/creator-engine/creator-engine/pulls/106/reviews -f event=APPROVE"),
        hc.HookContext(
            posture="governed",
            manifest_paths=(),
            side_effect_authority=None,
            seat_class="worker",
        ),
    )
    assert decision.reason == gh_decision.reason


def test_curl_api_review_approve_denied_even_with_matching_pr_review_envelope():
    command = "curl -X POST https://api.github.com/repos/creator-engine/creator-engine/pulls/106/reviews -d event=APPROVE"
    decision = hc.evaluate(
        _bash_event(command),
        hc.HookContext(
            posture="governed",
            manifest_paths=(),
            side_effect_authority=_envelope(),
            seat_class="worker",
        ),
    )

    assert hc.classify_mechanics(command) == "pr_review"
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    gh_decision = hc.evaluate(
        _bash_event("gh api -X POST repos/creator-engine/creator-engine/pulls/106/reviews -f event=APPROVE"),
        hc.HookContext(
            posture="governed",
            manifest_paths=(),
            side_effect_authority=_envelope(),
            seat_class="worker",
        ),
    )
    assert decision.reason == gh_decision.reason


def test_pr_review_denied_on_wrong_pr():
    assert hc._mechanics_would_deny("gh pr review 999 --approve", _ctx(_envelope())) is not None


def test_pr_review_denied_on_mechanic_mismatch_envelope():
    # an envelope whose declared mechanic isn't pr_review never covers pr_review
    assert hc._mechanics_would_deny("gh pr review 106 --approve", _ctx(_envelope(mechanic="merge"))) is not None


@pytest.mark.parametrize("command", [
    "gh pr merge 106 --squash",
    "git push origin main",
    "gh pr comment 106 --body x",
    "ce launch --harness claude",
])
def test_other_restricted_mechanics_stay_denied_under_pr_review_envelope(command):
    assert hc._mechanics_would_deny(command, _ctx(_envelope())) is not None


def test_loose_string_token_not_honored():
    # backward-incompatible-by-design: the old raw token no longer authorizes anything
    assert hc._mechanics_would_deny("gh pr review 106 --approve", _ctx("ratified-token-xyz")) is not None


def test_non_mechanic_command_allowed():
    assert hc._mechanics_would_deny("git status", _ctx(None)) is None


# --- build_context: resolve a validated envelope (inline + ref); fail-closed on invalid ---
def test_build_context_resolves_inline_envelope():
    event = {"hook_event_name": "PreToolUse", "ce": {"posture": "governed", "reviewer_authority": _envelope()}}
    ctx = hc.build_context(event)
    assert isinstance(ctx.side_effect_authority, dict)
    assert ctx.side_effect_authority.get("pr_number") == 106
    assert hc._mechanics_would_deny("gh pr review 106 --approve", ctx) is None


def test_build_context_resolves_ref_envelope(tmp_path):
    env_file = tmp_path / "reviewer-authority.ce.yml"
    env_file.write_text(yaml.safe_dump({"reviewer_authority_envelope": _envelope()}), encoding="utf-8")
    event = {"hook_event_name": "PreToolUse", "ce": {"posture": "governed", "reviewer_authority_ref": "reviewer-authority.ce.yml"}}
    ctx = hc.build_context(event, posture_root=str(tmp_path))
    assert isinstance(ctx.side_effect_authority, dict) and ctx.side_effect_authority.get("pr_number") == 106


def test_build_context_invalid_envelope_resolves_to_none():
    event = {"hook_event_name": "PreToolUse", "ce": {"posture": "governed", "reviewer_authority": _envelope(mechanic="merge")}}
    assert hc.build_context(event).side_effect_authority is None


def test_build_context_no_authority_is_none():
    event = {"hook_event_name": "PreToolUse", "ce": {"posture": "governed"}}
    assert hc.build_context(event).side_effect_authority is None
