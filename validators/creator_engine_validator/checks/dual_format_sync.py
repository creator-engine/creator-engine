"""PR-diff gate for tracked Markdown/HTML sibling pairs.

The repository's current convention is a committed ``.md`` file with a same-stem
``.html`` sibling. The paired HTML files do not carry source-hash markers, so
this gate only enforces that PRs touch both siblings together.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Final

from ..reporting import CheckResult, make_error
from . import register
from .git_helpers import repo_root_for, run_git

CHECK_NAME = "dual_format_sync"
CONTRACT = "ce validate-pr dual-format sync gate"
CODE_STALE_SIBLING: Final[str] = "dual_format_stale_sibling"
CODE_INVALID: Final[str] = "dual_format_git_failed"


def _tracked_files(repo_root: Path) -> set[str]:
    returncode, stdout, _stderr = run_git(["ls-files", "-z"], repo_root)
    if returncode != 0:
        return set()
    return {path for path in stdout.split("\0") if path}


def discover_sibling_pairs(repo_root: Path) -> dict[str, str]:
    """Return both directions of tracked ``.md`` <-> ``.html`` sibling pairs."""
    tracked = _tracked_files(repo_root)
    siblings: dict[str, str] = {}
    for path in tracked:
        if not path.endswith(".md"):
            continue
        html = f"{path[:-3]}.html"
        if html not in tracked:
            continue
        siblings[path] = html
        siblings[html] = path
    return siblings


def _changed_paths(repo_root: Path, base: str) -> tuple[set[str], CheckResult | None]:
    returncode, stdout, stderr = run_git(
        ["diff", "--name-only", "--find-renames", f"{base}..HEAD"],
        repo_root,
    )
    if returncode != 0:
        detail = stderr.strip() or "unknown error"
        return set(), CheckResult(
            name=CHECK_NAME,
            errors=(
                make_error(
                    CODE_INVALID,
                    "PR_DIFF",
                    "",
                    f"git diff --name-only --find-renames {base}..HEAD failed: {detail}",
                    CONTRACT,
                ),
            ),
        )
    return {line.strip() for line in stdout.splitlines() if line.strip()}, None


@register(CHECK_NAME, [CODE_STALE_SIBLING, CODE_INVALID])
def run(paths: Iterable[Path]) -> CheckResult:
    return CheckResult(name=CHECK_NAME)


def run_with_base(paths: Iterable[Path], base: str) -> CheckResult:
    """Fail when a PR touches one tracked md/html sibling without the other."""
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = repo_root_for(raw_paths[0])
    changed, failed = _changed_paths(repo_root, base)
    if failed is not None:
        return failed

    siblings = discover_sibling_pairs(repo_root)
    errors = []
    seen_pairs: set[tuple[str, str]] = set()
    for path in sorted(changed):
        sibling = siblings.get(path)
        if sibling is None:
            continue
        pair = tuple(sorted((path, sibling)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        if sibling in changed:
            continue
        errors.append(
            make_error(
                CODE_STALE_SIBLING,
                sibling,
                "",
                (
                    f"'{path}' changed without its tracked dual-format sibling "
                    f"'{sibling}'; update both files in the same PR"
                ),
                CONTRACT,
            )
        )

    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
