from __future__ import annotations

import json

import pytest

from creator_engine_validator.forge.reviewer_terminal import (
    REVIEWED, UNVERIFIED_LEGACY, ReviewerTerminalRefused, parse_reviewer_terminal,
    require_reviewed_terminal,
)


def _terminal(**overrides):
    value = {
        "version": 2, "state": "REVIEWED", "repository": "owner/repo", "pr_number": 7,
        "head_sha": "a" * 40, "base": "main", "range": "main...head",
        "reviewer": "reviewer", "author": "author", "review_id": "dispatch-7",
        "verdict": "APPROVE", "verified": [{"claim": "diff", "evidence": "git diff main...HEAD: clean"}],
        "findings": [], "summary": "inspected", "timestamp": "2026-07-21T00:00:00Z",
    }
    value.update(overrides)
    return value


def test_valid_evidenced_reviewed_derives_counts_and_binds():
    terminal = require_reviewed_terminal(_terminal(), repository="owner/repo", pr_number=7,
                                         head_sha="a" * 40, event="APPROVE")
    assert terminal.state == REVIEWED
    assert terminal.counts == {"HIGH": 0, "MEDIUM": 0, "LOW": 0}


def test_reviewed_empty_verified_is_refused():
    with pytest.raises(ReviewerTerminalRefused):
        require_reviewed_terminal(_terminal(verified=[]))


def test_blocked_with_counts_is_refused():
    blocked = _terminal(state="BLOCKED", reason="branch unavailable",
                        blocker_evidence=[{"attempt": "git fetch", "result": "ref missing"}])
    for key in ("verdict", "verified", "findings", "summary"):
        blocked.pop(key)
    blocked["counts"] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    with pytest.raises(ReviewerTerminalRefused):
        require_reviewed_terminal(blocked)


def test_canonical_cannot_review_fixture_is_not_a_verdict():
    refusal = _terminal(state="CANNOT_REVIEW", reason="target ref absent",
                        blocker_evidence=[{"attempt": "git fetch --prune", "result": "ref absent"}])
    for key in ("verdict", "verified", "findings", "summary"):
        refusal.pop(key)
    parsed = parse_reviewer_terminal(json.dumps(refusal))
    assert parsed.state == "CANNOT_REVIEW"
    with pytest.raises(ReviewerTerminalRefused):
        require_reviewed_terminal(json.dumps(refusal))


def test_verified_none_and_count_only_prose_are_legacy_not_evidence():
    parsed = parse_reviewer_terminal("COMMENT — High 0, Medium 0, Low 0\nVerified: none")
    assert parsed.state == UNVERIFIED_LEGACY and not parsed.verified
    with pytest.raises(ReviewerTerminalRefused):
        require_reviewed_terminal("APPROVE — High 0, Medium 0, Low 0")
