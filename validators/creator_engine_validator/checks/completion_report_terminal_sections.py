"""Completion Report terminal-section cross-check (PCO Slice 0.5, warn-only).

Implements CR-003 from
``docs/operations/COMPLETION_REPORT_PROTOCOL.md`` §h.

For each Completion Report YAML sidecar discovered under the scanned
paths, this check looks for an adjacent Markdown body
(``<basename>.md``) and verifies that the three literal terminal
section headers appear in canonical order:

  1. ``Summary``
  2. ``Recommended immediate next step``
  3. ``Exact next Source prompt pointer+SHA256``

Slice 0.5 scope discipline:

* The check is **warn-only** in v1. Findings are returned via the
  ``warnings`` field of the CheckResult; the run still passes
  unless a separate check produces hard errors.
* The primary enforcer of terminal-section presence is the Hermes
  final-answer hook (Slice 0.5R). CR-003 provides CI-time
  defense-in-depth against drift between the YAML self-declaration
  in ``terminal_packet_sections_present`` and the rendered Markdown.

Records cite ``CR-003`` and the prose contract at
``docs/operations/COMPLETION_REPORT_PROTOCOL.md``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .completion_report_schema import iter_completion_report_records

CHECK_NAME = "completion_report_terminal_sections"
CONTRACT = "docs/operations/COMPLETION_REPORT_PROTOCOL.md"
CODE_TERMINAL = "CR-003"

CANONICAL_HEADERS: tuple[str, ...] = (
    "Summary",
    "Recommended immediate next step",
    "Exact next Source prompt pointer+SHA256",
)


def _header_positions(text: str) -> list[tuple[str, int]]:
    """Return ordered (header_text, line_index) tuples for every Markdown
    header line whose visible text matches one of the canonical headers."""
    positions: list[tuple[str, int]] = []
    header_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    for line_index, line in enumerate(text.splitlines()):
        match = header_pattern.match(line)
        if match is None:
            continue
        visible = match.group(2).strip().rstrip("#").strip()
        if visible in CANONICAL_HEADERS:
            positions.append((visible, line_index))
    return positions


def _terminal_section_violation(md_path: Path, text: str) -> str | None:
    """Return a human-readable violation message, or None if the body is OK."""
    positions = _header_positions(text)
    if len(positions) < 3:
        present = [h for h, _ in positions]
        missing = [h for h in CANONICAL_HEADERS if h not in present]
        return (
            "markdown body is missing canonical terminal section header(s) "
            f"{missing!r}; expected all three of "
            f"{list(CANONICAL_HEADERS)!r} in canonical order"
        )
    # Find the first occurrence index of each canonical header; require
    # canonical ordering on those first occurrences.
    first_index: dict[str, int] = {}
    for header, line_idx in positions:
        first_index.setdefault(header, line_idx)
    ordered = sorted(first_index.items(), key=lambda kv: kv[1])
    actual_order = tuple(name for name, _ in ordered)
    if actual_order != CANONICAL_HEADERS:
        return (
            f"canonical terminal headers appear in order {list(actual_order)!r}, "
            f"expected {list(CANONICAL_HEADERS)!r}"
        )
    return None


@register(CHECK_NAME, [CODE_TERMINAL])
def run(paths: Iterable[Path]) -> CheckResult:
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    warnings: list[ValidationError] = []
    for yaml_path in iter_completion_report_records(raw_paths):
        try:
            record = load_yaml(yaml_path)
        except LoaderError:
            continue
        if not isinstance(record, dict):
            continue
        md_path = yaml_path.with_suffix(".md")
        if not md_path.is_file():
            # Markdown body is optional; CR-003 only fires when a body
            # is present so authors can update the YAML sidecar before
            # writing the rendered body.
            continue
        try:
            md_text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        violation = _terminal_section_violation(md_path, md_text)
        if violation is None:
            continue
        warnings.append(
            make_error(
                CODE_TERMINAL,
                md_path,
                "/",
                violation,
                CONTRACT,
            )
        )
    return CheckResult(name=CHECK_NAME, errors=(), warnings=tuple(warnings))
