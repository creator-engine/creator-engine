"""Parse ce-ops issue references from merged pull request metadata.

Title references are visible directly.  Body references are visible only when
they are guarded by a closing keyword.  The public callables in this module
are the canonical grammar used by both installed validator consumers and the
source-checkout compatibility shim.
"""
from __future__ import annotations

import re

_BARE_REF_RE = re.compile(
    r"(?:creator-engine/)?ce-ops#(\d+)\b",
    re.IGNORECASE,
)
_BARE_CE_NUM_RE = re.compile(
    r"(?<![a-zA-Z0-9#-])ce-(\d+)(?![-a-zA-Z#])",
    re.IGNORECASE,
)
_KEYWORD = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
_REF_CLUSTER = (
    r"(?:creator-engine/)?ce-ops#\d+\b"
    r"(?:(?:[ \t]*(?:,|;)[ \t]*|[ \t]+and[ \t]+)"
    r"(?:creator-engine/)?ce-ops#\d+\b)*"
)
_CLOSING_CLAUSE_RE = re.compile(
    rf"^{_KEYWORD}(?:[ \t]+|[ \t]*:[ \t]*)(?P<refs>{_REF_CLUSTER})",
    re.IGNORECASE,
)
_CLAUSE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_ACCEPTANCE_EVIDENCE_RE = re.compile(r"^\s*Acceptance-Evidence\s*:\s*(?P<value>.*?)\s*$")


def _extract_from_clause(clause_text: str, seen: set[int], numbers: list[int]) -> None:
    """Append closing-keyword-guarded numbers from one clause into *numbers*."""
    stripped = _LIST_MARKER_RE.sub("", clause_text).strip()
    match = _CLOSING_CLAUSE_RE.match(stripped)
    if not match:
        return
    for ref_match in _BARE_REF_RE.finditer(match.group("refs")):
        number = int(ref_match.group(1))
        if number not in seen:
            seen.add(number)
            numbers.append(number)


def parse_title_refs(title: str) -> list[int]:
    """Return ce-ops references visible anywhere in *title*."""
    seen: set[int] = set()
    numbers: list[int] = []
    for match in _BARE_REF_RE.finditer(title):
        number = int(match.group(1))
        if number not in seen:
            seen.add(number)
            numbers.append(number)
    for match in _BARE_CE_NUM_RE.finditer(title):
        number = int(match.group(1))
        if number not in seen:
            seen.add(number)
            numbers.append(number)
    return numbers


def parse_body_closing_refs(body: str) -> list[int]:
    """Return only closing-keyword-guarded ce-ops references from *body*."""
    seen: set[int] = set()
    numbers: list[int] = []
    for raw_clause in _CLAUSE_SPLIT_RE.split(body):
        _extract_from_clause(raw_clause, seen, numbers)
    return numbers


def parse_acceptance_evidence(body: str) -> str | None:
    """Return the PR body's ``Acceptance-Evidence:`` value, when present."""
    for line in body.splitlines():
        match = _ACCEPTANCE_EVIDENCE_RE.match(line)
        if match:
            value = match.group("value").strip()
            if value:
                return value
    return None


def parse_all_refs(title: str, body: str) -> list[int]:
    """Return title refs followed by new closing-keyword-guarded body refs."""
    seen: set[int] = set()
    numbers: list[int] = []
    for number in (*parse_title_refs(title), *parse_body_closing_refs(body)):
        if number not in seen:
            seen.add(number)
            numbers.append(number)
    return numbers
