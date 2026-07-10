"""Guard docs against teaching ``ce`` verbs that the parser does not ship."""

from __future__ import annotations

import argparse
import importlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "documented_verbs"
CONTRACT = "docs/reference/cli.md"

CODE_UNSHIPPED = "VAL-DOCVERB-UNSHIPPED"
CODE_BASELINE = "VAL-DOCVERB-BASELINE"
CODE_STALE_BASELINE = "VAL-DOCVERB-STALE-BASELINE"

# Explicit seam for deliberate forward-teaching. Keep empty unless a reviewable
# diff intentionally documents a verb before it is exposed by the parser.
FORWARD_TEACHING_ALLOWLIST: frozenset[str] = frozenset()

# Current docs debt at gate introduction. Entries are repo-relative path,
# 1-based line, and the taught top-level verb. These warn while present, fail if
# duplicated elsewhere, and warn stale when docs are cleaned so the ratchet can
# shrink.
BASELINE_OFFENSES: frozenset[tuple[str, int, str]] = frozenset(
    {
        ("docs/adr/ADR-0001-v1-baseline-and-product-form.md", 75, "dev"),
        ("docs/adr/ADR-0001-v1-baseline-and-product-form.md", 83, "dev"),
        ("docs/architecture/seat-sentinel-contract.md", 108, "seat"),
        ("docs/architecture/v3-spec.md", 295, "spike"),
        ("docs/design/seat-side-preflight.md", 173, "preflight"),
        ("docs/design/seat-side-preflight.md", 173, "seat-preflight"),
        ("docs/design/worktree-debt-classified-sweep.md", 228, "worktree"),
        ("docs/design/worktree-debt-classified-sweep.md", 273, "worktree"),
        ("docs/design/worktree-debt-classified-sweep.md", 274, "worktree"),
        ("docs/design/worktree-debt-classified-sweep.md", 275, "worktree"),
        ("docs/governance/V1_CANONICAL_TERMINOLOGY.md", 108, "worktree"),
        ("docs/governance/V1_CANONICAL_TERMINOLOGY.md", 119, "worktree"),
        ("docs/governance/V1_CANONICAL_TERMINOLOGY.md", 280, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 31, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 32, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 33, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 34, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 36, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 37, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 44, "dev"),
        ("docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md", 56, "dev"),
        ("docs/governance/V1_PRODUCT_CONTRACT.md", 53, "dev"),
        ("docs/governance/V1_PRODUCT_CONTRACT.md", 93, "dev"),
        ("docs/governance/V1_PRODUCT_CONTRACT.md", 109, "dev"),
        ("docs/operations/CONTROLLER_BOOTSTRAP.md", 31, "identity"),
        ("docs/operations/CONTROLLER_BOOTSTRAP.md", 50, "identity"),
        ("docs/operations/CONTROLLER_BOOTSTRAP.md", 230, "identity"),
        ("docs/reference/cli.md", 7, "dev"),
        ("docs/reference/cli.md", 80, "conveyor"),
    }
)

_CE_VERB_RE = re.compile(r"(?<![\w-])ce\s+(?P<verb>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)(?![\w-])")
_INLINE_CODE_RE = re.compile(r"`+([^`\n]+?)`+")
_DOC_GLOB = "docs/**/*.md"


@dataclass(frozen=True)
class TaughtInvocation:
    path: Path
    rel_path: str
    line: int
    verb: str

    @property
    def baseline_key(self) -> tuple[str, int, str]:
        return (self.rel_path, self.line, self.verb)


def shipped_verbs() -> frozenset[str]:
    """Return top-level ``ce`` verbs registered on the argparse parser."""
    ce_cli = importlib.import_module("creator_engine_validator.ce_cli")
    parser = ce_cli._build_parser()
    verbs: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            verbs.update(str(name) for name in action.choices)
    return frozenset(verbs)


def _repo_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / "validators" / "creator_engine_validator" / "ce_cli.py").is_file():
            return candidate
    return None


def _relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _git_tracked_docs(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", _DOC_GLOB],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    return [root / line.strip() for line in result.stdout.splitlines() if line.strip()]


def _fallback_docs(root: Path) -> list[Path]:
    docs_root = root / "docs"
    if not docs_root.is_dir():
        return []
    return sorted(path for path in docs_root.rglob("*.md") if path.is_file())


def iter_doc_paths(paths: Iterable[Path]) -> list[tuple[Path, Path]]:
    """Return ``(repo_root, doc_path)`` pairs, preferring tracked docs."""
    pairs: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        root = _repo_root_for(path) or (path if path.is_dir() else path.parent)
        candidates: list[Path]
        if path.is_file():
            candidates = [path] if path.suffix == ".md" else []
        else:
            tracked = _git_tracked_docs(root)
            candidates = tracked if tracked else _fallback_docs(path)
            if path != root:
                try:
                    scope = path.resolve()
                    candidates = [doc for doc in candidates if doc.resolve().is_relative_to(scope)]
                except OSError:
                    candidates = []
        for doc in candidates:
            resolved = doc.resolve()
            if resolved in seen or not doc.is_file():
                continue
            seen.add(resolved)
            pairs.append((root, doc))
    return pairs


def _code_segments(path: Path) -> Iterable[tuple[int, str]]:
    in_fence = False
    fence_marker: str | None = None
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in ("```", "~~~"):
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif fence_marker == marker:
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            yield line_no, line
            continue
        for match in _INLINE_CODE_RE.finditer(line):
            yield line_no, match.group(1)


def _taught_invocations_from_docs(docs: Iterable[tuple[Path, Path]]) -> list[TaughtInvocation]:
    invocations: list[TaughtInvocation] = []
    for root, doc in docs:
        rel_path = _relpath(doc, root)
        for line_no, code in _code_segments(doc):
            for match in _CE_VERB_RE.finditer(code):
                invocations.append(
                    TaughtInvocation(
                        path=doc,
                        rel_path=rel_path,
                        line=line_no,
                        verb=match.group("verb"),
                    )
                )
    return invocations


def taught_invocations(paths: Iterable[Path]) -> list[TaughtInvocation]:
    return _taught_invocations_from_docs(iter_doc_paths(paths))


def validate(paths: Iterable[Path]) -> tuple[list[ValidationError], list[ValidationError]]:
    docs = iter_doc_paths(paths)
    scanned_rel_paths = {_relpath(doc, root) for root, doc in docs}
    shipped = shipped_verbs()
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    used_baseline: set[tuple[str, int, str]] = set()

    for invocation in _taught_invocations_from_docs(docs):
        if invocation.verb in shipped or invocation.verb in FORWARD_TEACHING_ALLOWLIST:
            continue
        key = invocation.baseline_key
        if key in BASELINE_OFFENSES:
            if key in used_baseline:
                continue
            used_baseline.add(key)
            warnings.append(
                make_error(
                    CODE_BASELINE,
                    invocation.rel_path,
                    f"L{invocation.line}",
                    f"baseline docs debt still teaches unshipped ce verb {invocation.verb!r}; "
                    "remove or update the taught invocation to shrink BASELINE_OFFENSES",
                    CONTRACT,
                )
            )
            continue
        errors.append(
            make_error(
                CODE_UNSHIPPED,
                invocation.rel_path,
                f"L{invocation.line}",
                f"docs teach `ce {invocation.verb}` but the ce parser registry does not ship "
                f"top-level verb {invocation.verb!r}",
                CONTRACT,
            )
        )

    for rel_path, line, verb in sorted(BASELINE_OFFENSES - used_baseline):
        if rel_path not in scanned_rel_paths:
            continue
        warnings.append(
            make_error(
                CODE_STALE_BASELINE,
                rel_path,
                f"L{line}",
                f"baseline docs debt for unshipped ce verb {verb!r} is no longer present; "
                "remove this entry from BASELINE_OFFENSES",
                CONTRACT,
            )
        )
    return errors, warnings


@register(CHECK_NAME, [CODE_UNSHIPPED])
def run(paths: Iterable[Path]) -> CheckResult:
    errors, warnings = validate(paths)
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
