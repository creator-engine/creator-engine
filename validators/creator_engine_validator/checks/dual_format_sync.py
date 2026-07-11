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


def _tracked_files(repo_root: Path, ref: str | None = None) -> set[str]:
    args = ["ls-files", "-z"] if ref is None else ["ls-tree", "-r", "--name-only", "-z", ref]
    returncode, stdout, stderr = run_git(args, repo_root)
    if returncode != 0:
        detail = stderr.strip() or "unknown error"
        command = " ".join(args)
        raise RuntimeError(f"git {command} failed: {detail}")
    return {path for path in stdout.split("\0") if path}


def _pairs_for_files(tracked: set[str]) -> dict[str, str]:
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


def discover_sibling_pairs(repo_root: Path, base: str) -> dict[str, str]:
    """Return pairs that exist at either the comparison base or ``HEAD``."""
    siblings = _pairs_for_files(_tracked_files(repo_root, base))
    siblings.update(_pairs_for_files(_tracked_files(repo_root)))
    return siblings


def _diff_failure(base: str, detail: str) -> CheckResult:
    return CheckResult(
        name=CHECK_NAME,
        errors=(
            make_error(
                CODE_INVALID,
                "PR_DIFF",
                "",
                f"git diff --name-status -z --find-renames {base}..HEAD failed: {detail}",
                CONTRACT,
            ),
        ),
    )


def _parse_name_status(output: str) -> set[str]:
    """Parse ``git diff --name-status -z`` and retain both rename paths."""
    fields = output.split("\0")
    if fields and fields[-1] == "":
        fields.pop()

    changed: set[str] = set()
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        if not status or status[0] not in "ACDMRTUXB":
            raise ValueError(f"invalid name-status token {status!r}")
        path_count = 2 if status[0] in "CR" else 1
        if index + path_count > len(fields):
            raise ValueError(f"truncated name-status record for {status!r}")
        paths = fields[index : index + path_count]
        if any(not path for path in paths):
            raise ValueError(f"empty path in name-status record for {status!r}")
        changed.update(paths)
        index += path_count
    return changed


def _changed_paths(repo_root: Path, base: str) -> tuple[set[str], CheckResult | None]:
    returncode, stdout, stderr = run_git(
        ["diff", "--name-status", "-z", "--find-renames", f"{base}..HEAD"],
        repo_root,
    )
    if returncode != 0:
        detail = stderr.strip() or "unknown error"
        return set(), _diff_failure(base, detail)
    try:
        return _parse_name_status(stdout), None
    except ValueError as exc:
        return set(), _diff_failure(base, f"malformed output: {exc}")


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

    try:
        siblings = discover_sibling_pairs(repo_root, base)
    except RuntimeError as exc:
        return CheckResult(
            name=CHECK_NAME,
            errors=(
                make_error(
                    CODE_INVALID,
                    "TRACKED_FILES",
                    "",
                    str(exc),
                    CONTRACT,
                ),
            ),
        )
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
