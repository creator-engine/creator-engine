"""PR-diff test-coupling gate.

This check is deliberately PR-local: when a diff adds or modifies non-test
source code, it must also add or modify a test file. Legitimate exemptions are
documented in the PR body with ``CE-TEST-COUPLING-EXEMPT``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Final

from ..reporting import CheckResult, make_error
from . import register
from .work_sizing_floor import ChangeStat, _repo_root_for, _run_git, parse_numstat

CHECK_NAME = "test_coupling"
CONTRACT = "ce validate-pr test-coupling gate"
CODE_MISSING_TEST = "VAL-TEST-COUPLING-MISSING-TEST"
CODE_INVALID = "VAL-TEST-COUPLING-INVALID"
OPT_OUT_MARKER: Final[str] = "CE-TEST-COUPLING-EXEMPT"

_SOURCE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".c",
        ".cc",
        ".cpp",
        ".cs",
        ".css",
        ".go",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".mjs",
        ".py",
        ".rs",
        ".sh",
        ".swift",
        ".ts",
        ".tsx",
    }
)
_CONFIG_NAMES: Final[frozenset[str]] = frozenset(
    {
        "dockerfile",
        "makefile",
    }
)


def _normalize_path(path: str) -> PurePosixPath:
    normalized = path.replace("\\", "/").strip("/")
    return PurePosixPath(normalized or ".")


def is_test_path(path: str) -> bool:
    pure = _normalize_path(path)
    parts = tuple(part.lower() for part in pure.parts)
    if "tests" in parts:
        return True
    name = pure.name.lower()
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def is_source_path(path: str) -> bool:
    pure = _normalize_path(path)
    if is_test_path(path):
        return False
    name = pure.name.lower()
    if name in _CONFIG_NAMES:
        return False
    return pure.suffix.lower() in _SOURCE_SUFFIXES


def has_opt_out_marker(pr_body: str | None) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9_-]){re.escape(OPT_OUT_MARKER)}(?![A-Za-z0-9_-])", pr_body or ""))


def coupling_projection(change_stats: Iterable[ChangeStat]) -> dict[str, int | bool]:
    source_files: set[str] = set()
    test_files: set[str] = set()
    source_added_lines = 0
    test_added_lines = 0

    for stat in change_stats:
        if stat.binary or stat.additions <= 0:
            continue
        if is_test_path(stat.path):
            test_files.add(stat.path)
            test_added_lines += stat.additions
        elif is_source_path(stat.path):
            source_files.add(stat.path)
            source_added_lines += stat.additions

    return {
        "source_files": len(source_files),
        "source_added_lines": source_added_lines,
        "test_files": len(test_files),
        "test_added_lines": test_added_lines,
        "requires_test": bool(source_files and not test_files),
    }


@register(CHECK_NAME, [CODE_MISSING_TEST, CODE_INVALID])
def run(paths: Iterable[Path]) -> CheckResult:
    return CheckResult(name=CHECK_NAME)


def run_with_base(
    paths: Iterable[Path],
    base: str,
    *,
    pr_body: str | None = None,
) -> CheckResult:
    """PR-diff gate for ``git diff --numstat --find-renames <base>..HEAD``."""
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    returncode, stdout, _stderr = _run_git(
        ["diff", "--numstat", "--find-renames", f"{base}..HEAD"],
        repo_root,
    )
    if returncode != 0:
        return CheckResult(
            name=CHECK_NAME,
            errors=(make_error(CODE_INVALID, "PR_DIFF", "", "git diff numstat failed", CONTRACT),),
        )

    if has_opt_out_marker(pr_body):
        return CheckResult(name=CHECK_NAME)

    try:
        projection = coupling_projection(parse_numstat(stdout))
    except ValueError:
        return CheckResult(
            name=CHECK_NAME,
            errors=(make_error(CODE_INVALID, "PR_DIFF", "", "git diff numstat failed", CONTRACT),),
        )

    if projection["source_files"] and not projection["test_files"]:
        return CheckResult(
            name=CHECK_NAME,
            errors=(
                make_error(
                    CODE_MISSING_TEST,
                    "PR_DIFF",
                    "tests",
                    "code changes require an added or modified test file, or PR body marker "
                    f"{OPT_OUT_MARKER} for a documented exemption",
                    CONTRACT,
                ),
            ),
        )
    return CheckResult(name=CHECK_NAME)
