"""Code-synced operator runbook refusal-clause validator."""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "operator_runbook_refusal_sync"
RUNBOOK_RELATIVE = Path("docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md")
DOCS_RELATIVE = RUNBOOK_RELATIVE.parent.parent
OPERATIONS_RELATIVE = RUNBOOK_RELATIVE.parent
RUNBOOK_NAME = RUNBOOK_RELATIVE.name
CONTRACT = str(RUNBOOK_RELATIVE)

START_MARKER = "<!-- ce-launch-refusal-clauses:start -->"
END_MARKER = "<!-- ce-launch-refusal-clauses:end -->"

CODE_UNREADABLE = "VAL-OP-RUNBOOK-UNREADABLE"
CODE_MALFORMED = "VAL-OP-RUNBOOK-MALFORMED"
CODE_MISSING = "VAL-OP-RUNBOOK-MISSING-CLAUSE"
CODE_EXTRA = "VAL-OP-RUNBOOK-EXTRA-CLAUSE"
CODE_DUPLICATE = "VAL-OP-RUNBOOK-DUPLICATE-CLAUSE"

_CLAUSE_RE = re.compile(r"^(?:CC-D|CDX-D)-\d+$")
_SEPARATOR_RE = re.compile(r":?-{3,}:?")
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_LAUNCH_SPEC_PATHS = (
    _PACKAGE_ROOT / "claude_launch_spec.py",
    _PACKAGE_ROOT / "codex_launch_spec.py",
)


def _clause_sort_key(clause: str) -> tuple[str, int]:
    prefix, _, number = clause.rpartition("-")
    try:
        parsed = int(number)
    except ValueError:
        parsed = 0
    return prefix, parsed


def _clause_ids_from_module(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    found: list[str] = []
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id.startswith("CLAUSE_"):
                found.append(value.value)
    if not found:
        raise ValueError(f"{path} declares no string CLAUSE_* globals")
    return tuple(found)


def expected_clause_ids(module_paths: Iterable[Path] = _LAUNCH_SPEC_PATHS) -> tuple[str, ...]:
    """Return all string CLAUSE_* globals from the pure launcher spec sources."""

    found: set[str] = set()
    for path in module_paths:
        found.update(_clause_ids_from_module(Path(path)))
    return tuple(sorted(found, key=_clause_sort_key))


def _table_cells(row: str) -> tuple[str, ...]:
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return tuple(cell.strip() for cell in stripped.split("|"))


def _is_separator(row: str) -> bool:
    cells = _table_cells(row)
    return bool(cells) and all(_SEPARATOR_RE.fullmatch(cell) for cell in cells)


def parse_documented_clause_ids(text: str) -> tuple[str, ...]:
    """Parse the first column of the marked markdown table."""

    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise ValueError("runbook must contain exactly one refusal clause marker block")

    start = text.index(START_MARKER) + len(START_MARKER)
    end = text.index(END_MARKER)
    if end <= start:
        raise ValueError("refusal clause marker block is empty or inverted")

    rows = [
        line.strip()
        for line in text[start:end].splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(rows) < 3:
        raise ValueError("refusal clause block must contain a markdown table")

    header = _table_cells(rows[0])
    if not header or "clause" not in header[0].lower():
        raise ValueError("refusal clause table first column must be Clause ID")
    if not _is_separator(rows[1]):
        raise ValueError("refusal clause table must include a separator row")

    clauses: list[str] = []
    for row in rows[2:]:
        if _is_separator(row):
            continue
        cells = _table_cells(row)
        if not cells:
            raise ValueError("refusal clause table contains an empty row")
        clause = cells[0].strip().strip("`")
        if not _CLAUSE_RE.fullmatch(clause):
            raise ValueError(f"malformed clause id {clause!r}")
        clauses.append(clause)

    if not clauses:
        raise ValueError("refusal clause table contains no clause rows")
    return tuple(clauses)


def validate_runbook(path: Path, expected: Iterable[str] | None = None) -> list[ValidationError]:
    try:
        expected_set = set(expected_clause_ids() if expected is None else expected)
    except (OSError, SyntaxError, ValueError) as exc:
        return [
            make_error(
                CODE_UNREADABLE,
                path,
                "",
                f"launcher spec clause constants are unreadable: {exc}",
                CONTRACT,
            )
        ]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            make_error(
                CODE_UNREADABLE,
                path,
                "",
                f"operator runbook is unreadable: {exc}",
                CONTRACT,
            )
        ]

    try:
        documented = parse_documented_clause_ids(text)
    except ValueError as exc:
        return [
            make_error(
                CODE_MALFORMED,
                path,
                "",
                f"operator runbook refusal clause block is malformed: {exc}",
                CONTRACT,
            )
        ]

    errors: list[ValidationError] = []
    counts = Counter(documented)
    duplicates = sorted((clause for clause, count in counts.items() if count > 1), key=_clause_sort_key)
    if duplicates:
        errors.append(
            make_error(
                CODE_DUPLICATE,
                path,
                "",
                "operator runbook documents duplicate clauses: " + ", ".join(duplicates),
                CONTRACT,
            )
        )

    documented_set = set(documented)
    missing = sorted(expected_set - documented_set, key=_clause_sort_key)
    extra = sorted(documented_set - expected_set, key=_clause_sort_key)
    if missing:
        errors.append(
            make_error(
                CODE_MISSING,
                path,
                "",
                "operator runbook is missing launcher clauses: " + ", ".join(missing),
                CONTRACT,
            )
        )
    if extra:
        errors.append(
            make_error(
                CODE_EXTRA,
                path,
                "",
                "operator runbook documents unknown launcher clauses: " + ", ".join(extra),
                CONTRACT,
            )
        )
    return errors


def _cwd_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(Path.cwd().resolve(strict=False))
    except ValueError:
        return path


def _candidate_for_path(path: Path) -> Path | None:
    relative = _cwd_relative(path)
    if relative == Path("."):
        return path / RUNBOOK_RELATIVE
    if relative == DOCS_RELATIVE:
        return path / "operations" / RUNBOOK_NAME
    if relative == OPERATIONS_RELATIVE:
        return path / RUNBOOK_NAME
    if relative == RUNBOOK_RELATIVE:
        return path
    return None


def _candidate_runbooks(paths: Iterable[Path]) -> tuple[Path, ...]:
    raw_paths = [Path(path) for path in paths] or [Path(".")]
    candidates: list[Path] = []
    for path in raw_paths:
        candidate = _candidate_for_path(path)
        if candidate is not None:
            candidates.append(candidate)

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False))
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return tuple(deduped)


@register(
    CHECK_NAME,
    [CODE_UNREADABLE, CODE_MALFORMED, CODE_MISSING, CODE_EXTRA, CODE_DUPLICATE],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for runbook in _candidate_runbooks(Path(path) for path in paths):
        errors.extend(validate_runbook(runbook))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
