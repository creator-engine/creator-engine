"""Harness promotion matrix gate.

This checker is intentionally not registered in the generic per-path check
registry. It is a repo-wide promotion invariant, like the version-drift gate.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .. import harness_matrix
from ..reporting import CheckResult, ValidationError, make_error


CHECK_NAME = "harness_promotion_matrix"
CONTRACT = "harness promotion matrix gate"
CODE_GATE_WITHOUT_GREEN = "harness_promotion_gate_without_all_green"
CODE_DOC_MISMATCH = "harness_promotion_matrix_doc_mismatch"
CODE_MISSING_DOC = "harness_promotion_matrix_doc_missing"


def _repo_root_for(path: Path) -> Path | None:
    raw = path if path.is_absolute() else Path.cwd() / path
    start = raw if raw.is_dir() else raw.parent
    for candidate in (start, *start.parents):
        if (candidate / harness_matrix.DOC_PATH).is_file() and (
            candidate / "validators" / "creator_engine_validator" / "harness_matrix.py"
        ).is_file():
            return candidate
    return None


def _repo_roots(paths: Iterable[Path]) -> tuple[Path, ...]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        root = _repo_root_for(Path(path))
        if root is None:
            continue
        resolved = root.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(root)
    if not roots:
        root = _repo_root_for(Path.cwd())
        if root is not None:
            roots.append(root)
    return tuple(roots)


def evaluate(matrix: harness_matrix.HarnessMatrix) -> tuple[ValidationError, ...]:
    errors: list[ValidationError] = []
    for row in matrix.rows:
        if row.gate_capable.value != harness_matrix.GATE_YES:
            continue
        if harness_matrix.row_all_green(row):
            continue
        if harness_matrix.row_has_ratified_exception(row):
            continue
        errors.append(
            make_error(
                CODE_GATE_WITHOUT_GREEN,
                str(harness_matrix.DOC_PATH),
                f"{row.provider}/{row.ring}",
                (
                    "gate-capable row requires code-support, launch-wired, "
                    "live-proven, and promotion-approved all green, or a dated "
                    "Operator-ratified exception reference"
                ),
                CONTRACT,
            )
        )
    return tuple(errors)


def evaluate_repo(repo_root: Path) -> tuple[ValidationError, ...]:
    matrix = harness_matrix.build_matrix(repo_root=repo_root)
    errors = list(evaluate(matrix))
    doc_path = repo_root / harness_matrix.DOC_PATH
    try:
        actual = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(
            make_error(
                CODE_MISSING_DOC,
                str(harness_matrix.DOC_PATH),
                "",
                f"could not read rendered harness matrix: {exc}",
                CONTRACT,
            )
        )
        return tuple(errors)

    expected = harness_matrix.render_markdown(matrix)
    if actual != expected:
        errors.append(
            make_error(
                CODE_DOC_MISMATCH,
                str(harness_matrix.DOC_PATH),
                "",
                "rendered harness matrix is not synchronized with creator_engine_validator.harness_matrix",
                CONTRACT,
            )
        )
    return tuple(errors)


def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for root in _repo_roots(paths):
        errors.extend(evaluate_repo(root))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
