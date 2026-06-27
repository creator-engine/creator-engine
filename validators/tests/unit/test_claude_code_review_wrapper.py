"""Wiring checks for the ``/code-review`` self-fire reviewer wrapper."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS = REPO_ROOT / "AGENTS.md"
COMMAND = REPO_ROOT / ".claude" / "commands" / "code-review.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
