"""Parse ce-ops issue references from a merged PR's title and body.

Two distinct extraction paths:

1. **Title scan** — Any bare ``ce-ops#<N>`` token embedded in the PR title is
   collected.  CE PR titles follow the convention ``feat(ce-ops#NNN): ...``
   so the issue number is always present; no closing keyword is required.

2. **Body closing-keyword scan** — Lines (or sentences) in the PR body that
   start with a closing verb (``Closes``, ``Fixes``, ``Resolves``, and common
   inflections) followed by one or more ``ce-ops#<N>`` or
   ``creator-engine/ce-ops#<N>`` references are collected.

Results from both paths are merged and deduplicated in encounter order.

This module is intentionally stdlib-only so it can be imported both from the
``.github/scripts/ceops_autoclose.py`` workflow driver and from unit tests
without any additional dependencies.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Bare ce-ops#N token (used for title scan)
_BARE_REF_RE = re.compile(
    r"(?:creator-engine/)?ce-ops#(\d+)\b",
    re.IGNORECASE,
)

# Bare ce-NNN token in PR titles (e.g. "[ce-egress] ce-271 ...")
_BARE_CE_NUM_RE = re.compile(
    r"(?<![a-zA-Z0-9#-])ce-(\d+)(?![-a-zA-Z#])",
    re.IGNORECASE,
)

# Closing-keyword line/sentence pattern (used for body scan)
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
    m = _CLOSING_CLAUSE_RE.match(stripped)
    if not m:
        return
    for ref_match in _BARE_REF_RE.finditer(m.group("refs")):
        n = int(ref_match.group(1))
        if n not in seen:
            seen.add(n)
            numbers.append(n)


def parse_title_refs(title: str) -> list[int]:
    """Return ce-ops issue numbers found anywhere in *title*.

    No closing keyword is required. Two token forms are matched:
      - ``ce-ops#N`` / ``creator-engine/ce-ops#N``  (existing)
      - bare ``ce-N`` (e.g. ``[ce-egress] ce-271 ...``)  (new)

    Results are deduplicated in encounter order.
    """
    seen: set[int] = set()
    numbers: list[int] = []
    for m in _BARE_REF_RE.finditer(title):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            numbers.append(n)
    for m in _BARE_CE_NUM_RE.finditer(title):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            numbers.append(n)
    return numbers


def parse_body_closing_refs(body: str) -> list[int]:
    """Return ce-ops issue numbers guarded by closing keywords in *body*.

    Only refs preceded by ``Closes``, ``Fixes``, ``Resolves`` (and common
    inflections) are returned; bare mentions are ignored.
    """
    seen: set[int] = set()
    numbers: list[int] = []
    for raw_clause in _CLAUSE_SPLIT_RE.split(body):
        _extract_from_clause(raw_clause, seen, numbers)
    return numbers


def parse_acceptance_evidence(body: str) -> str | None:
    """Return the PR body's ``Acceptance-Evidence:`` value, when present."""
    for line in body.splitlines():
        m = _ACCEPTANCE_EVIDENCE_RE.match(line)
        if not m:
            continue
        value = m.group("value").strip()
        if value:
            return value
    return None


def parse_all_refs(title: str, body: str) -> list[int]:
    """Return deduplicated ce-ops issue numbers from title AND body.

    Title refs come first (in the order they appear), then body closing-keyword
    refs not already seen from the title.  Duplicates across both sources are
    collapsed in first-encounter order.
    """
    seen: set[int] = set()
    numbers: list[int] = []

    for n in parse_title_refs(title):
        if n not in seen:
            seen.add(n)
            numbers.append(n)

    for n in parse_body_closing_refs(body):
        if n not in seen:
            seen.add(n)
            numbers.append(n)

    return numbers
