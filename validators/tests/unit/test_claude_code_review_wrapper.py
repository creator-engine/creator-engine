"""Wiring checks for the ``/code-review`` self-fire reviewer wrapper."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from creator_engine_validator import hook_check as hc
from creator_engine_validator.forge.cred_injection_proxy import (
    ContainedSeatReview,
    CredentialBinding,
    CredentialProxyRefused,
    OutboundTransportRequest,
    submit_contained_seat_pr_review,
)
from creator_engine_validator.forge.scoped_token import ScopedToken
from creator_engine_validator.forge.transport_deputy_policy import TransportRequest, evaluate


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "AGENTS.md"
COMMAND = REPO_ROOT / ".claude" / "commands" / "code-review.md"
REPO = "creator-engine/creator-engine"
HEAD_SHA = "a" * 40


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _binding() -> CredentialBinding:
    return CredentialBinding(
        installation_id=123,
        run_id="run-autoreview",
        policy_sha="0" * 64,
        permissions={"metadata": "read", "pull_requests": "write"},
        requested_ttl_seconds=300,
    )


class _FakeMinter:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, request):
        self.calls.append(request)
        return ScopedToken(
            run_id="run-autoreview",
            repo=request.repo,
            policy_sha=request.policy_sha,
            secret_name=request.secret_name,
            permissions=(("metadata", "read"), ("pull_requests", "write")),
            expires_at="2026-06-28T00:00:00Z",
            token_ref=f"{request.repo}@test",
            value="ghs_abcdefghijklmnopqrstuvwxyz1234567890",
        )


def _review(event: str) -> ContainedSeatReview:
    return ContainedSeatReview(
        seat_id="seat-reviewer-1",
        repo=REPO,
        pr_number=592,
        head_sha=HEAD_SHA,
        event=event,
        body="self-fire review body",
    )


def _reviewer_authority_envelope() -> dict[str, object]:
    return {
        "envelope_id": "rva-pr592-reviewer",
        "mechanic": "pr_review",
        "pr_number": 592,
        "head_sha": HEAD_SHA,
        "actor": "seat-reviewer-1",
        "ratified_prompt_sha": "b" * 64,
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-28T00:00:00Z",
    }


def _bash_event(command: str) -> dict[str, object]:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def test_agents_declares_one_self_fire_auto_review_line() -> None:
    text = _text(AGENTS)
    lines = [
        line
        for line in text.splitlines()
        if "Auto-review:" in line
        and "fresh-context reviewer worker" in line
    ]

    assert len(lines) == 1
    line = lines[0]
    assert "/code-review" in line
    assert ".claude/agents/reviewer.md" in line
    assert "before PR open and before merge" in line
    assert "`COMMENT` or `REQUEST_CHANGES`" in line
    assert "never `APPROVE`" in line


def test_code_review_command_uses_existing_reviewer_worker() -> None:
    text = _text(COMMAND)

    assert "description:" in text
    assert "fresh-context CE reviewer" in text
    assert ".claude/agents/reviewer.md" in text
    assert "subagent_type: reviewer" in text
    assert "read-only" in text


def test_code_review_command_posts_only_comment_or_request_changes() -> None:
    text = _text(COMMAND)

    assert '"event": "COMMENT | REQUEST_CHANGES"' in text
    assert "gh api -X POST repos/<owner>/<repo>/pulls/<pr>/reviews --input -" in text
    assert "anything other\n   than `COMMENT` or `REQUEST_CHANGES`" in text
    assert "convert that to `COMMENT`" in text

    forbidden_positive_approval_paths = [
        r"gh\s+pr\s+review[^\n]*--approve",
        r'"event"\s*:\s*"APPROVE"',
        r"\bevent\s*=\s*APPROVE\b",
    ]
    for pattern in forbidden_positive_approval_paths:
        assert re.search(pattern, text, flags=re.IGNORECASE) is None

    assert re.search(r"do not submit an approval\s+review event", text)
    assert "never emits approval" in text


def test_self_fire_review_path_never_posts_approve_event() -> None:
    minter = _FakeMinter()
    captured: list[OutboundTransportRequest] = []

    def capture_transport(request: OutboundTransportRequest) -> dict[str, int]:
        captured.append(request)
        payload = json.loads(request.body or "{}")
        assert payload["event"] in {"COMMENT", "REQUEST_CHANGES"}
        return {"id": 1000 + len(captured)}

    for event in ("COMMENT", "REQUEST_CHANGES"):
        result = submit_contained_seat_pr_review(
            _review(event),
            binding=_binding(),
            minter=minter,
            transport=capture_transport,
            worker_argv=("gh", "api", "-X", "POST", f"repos/{REPO}/pulls/592/reviews", "--input", "-"),
        )
        assert result.event == event
        assert result.applied is True

    emitted_events = [json.loads(request.body or "{}")["event"] for request in captured]
    assert emitted_events == ["COMMENT", "REQUEST_CHANGES"]

    with pytest.raises(CredentialProxyRefused):
        submit_contained_seat_pr_review(
            _review("APPROVE"),
            binding=_binding(),
            minter=minter,
            transport=capture_transport,
            worker_argv=("gh", "api", "-X", "POST", f"repos/{REPO}/pulls/592/reviews", "--input", "-"),
        )

    assert [json.loads(request.body or "{}")["event"] for request in captured] == emitted_events

    raw_decision = evaluate(
        TransportRequest(
            seat_id="seat-reviewer-1",
            role_profile="reviewer",
            host="api.github.com",
            method="POST",
            path=f"/repos/{REPO}/pulls/592/reviews",
            repo=REPO,
            pr=592,
            head_sha=HEAD_SHA,
            body=json.dumps({"event": "APPROVE", "body": "naive approval"}),
        )
    )
    assert raw_decision.allowed is False
    assert any(
        check.name == "contained_review_event_allowed" and not check.passed
        for check in raw_decision.checks
    )

    command = f"gh api -X POST repos/{REPO}/pulls/592/reviews -f event=APPROVE -f body=LGTM"
    hook_decision = hc.evaluate(
        _bash_event(command),
        hc.HookContext(
            posture="governed",
            manifest_paths=(),
            side_effect_authority=_reviewer_authority_envelope(),
            seat_class="worker",
        ),
    )
    assert hc.classify_mechanics(command) == "pr_review"
    assert hook_decision.decision == "deny"
    assert hook_decision.hook_specific_output["permissionDecision"] == "deny"
