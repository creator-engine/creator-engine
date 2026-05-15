"""Role boundary attribution audit (Phase 1).

Conservative audit check intended to surface possible
controller-seat-edit violations and other role-boundary breaches per
``docs/operations/CONTROLLER_BOUNDARY_POLICY.md`` §d and the R-011
risk row in ``docs/delivery/RISK_REGISTER.md``.

Phase 1 operates in two modes:

1. **Default (whole-tree scan)**: When invoked without ``--base``,
   the check is *advisory* and emits warnings (not errors) when it
   detects shape signals that are commonly correlated with
   controller-seat edits:

   - A handoff or recommended-prompt document whose front matter
     declares ``role: controller`` but whose body contains a tracked-
     file path manifest (controllers do not author tracked files).
   - A commit message in the recent log that names "controller" as
     the author of tracked-file content.

   The whole-tree mode is intentionally conservative. It is meant to
   give the verifier a starting point, not to fail CI on speculative
   evidence.

2. **--base <commit> mode**: When the validator is invoked through
   the ``verify-attribution`` CLI subcommand with a base commit, the
   check compares the changed files between ``<base>..HEAD`` against
   the active handoff manifests under ``.hermes/handoffs/`` (when
   present and readable) and emits errors when a changed file is not
   covered by any active handoff's manifest. This mode is best-effort:
   it depends on ``.hermes/`` being available in the worktree, which
   it is not in a fresh clone of the upstream repo.

The default whole-tree mode is what runs under
``creator_engine_validator check`` and ``creator_engine_validator
check-examples``. The ``--base`` mode runs only under
``verify-attribution``.

See:
  - ``docs/operations/CONTROLLER_BOUNDARY_POLICY.md``
  - ``docs/delivery/RISK_REGISTER.md`` R-011
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable, Sequence

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "role_boundary_attribution"
CONTRACT = "docs/operations/CONTROLLER_BOUNDARY_POLICY.md"

DOCUMENT_SUFFIXES: frozenset[str] = frozenset({".md"})

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        "__pycache__",
        "wheelhouse",
        "wheelhouse-dev",
        ".egg-info",
        ".mypy_cache",
        ".pytest_cache",
        ".git",
        "node_modules",
    }
)

FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Conservative regex pattern matching role declarations in front matter.
ROLE_PATTERN = re.compile(r"^role:\s*([A-Za-z_-]+)\s*$", re.MULTILINE)
KIND_PATTERN = re.compile(r"^kind:\s*([A-Za-z_-]+)\s*$", re.MULTILINE)
FENCE_OPEN = "```text\n"


def _iter_documents(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for root in paths:
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for candidate in sorted(root.rglob("*")):
                if any(part in SKIP_DIR_NAMES for part in candidate.parts):
                    continue
                if candidate.is_file():
                    candidates.append(candidate)
        for candidate in candidates:
            if candidate.suffix.lower() not in DOCUMENT_SUFFIXES:
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _front_matter(text: str) -> str | None:
    match = FRONT_MATTER_PATTERN.match(text)
    if match is None:
        return None
    return match.group(1)


def _body_after_front_matter(text: str) -> str:
    match = FRONT_MATTER_PATTERN.match(text)
    if match is None:
        return text
    return text[match.end():]


def _has_fenced_manifest(body: str) -> bool:
    return FENCE_OPEN in body


def scan_document(doc_path: Path, text: str) -> list[ValidationError]:
    warnings: list[ValidationError] = []
    fm_text = _front_matter(text)
    if fm_text is None:
        return warnings

    kind_match = KIND_PATTERN.search(fm_text)
    role_match = ROLE_PATTERN.search(fm_text)
    if kind_match is None or role_match is None:
        return warnings

    kind = kind_match.group(1)
    role = role_match.group(1)
    if kind not in {"hermes-handoff", "hermes-recommended-prompt"}:
        return warnings

    body = _body_after_front_matter(text)
    if role == "controller" and _has_fenced_manifest(body):
        warnings.append(
            make_error(
                "role_boundary_controller_manifest_shape",
                doc_path,
                "frontmatter.role",
                (
                    "document declares role=controller but body contains a fenced path manifest; "
                    "controllers do not author tracked-file content under their own envelope "
                    "(see docs/operations/CONTROLLER_BOUNDARY_POLICY.md §d)"
                ),
                CONTRACT,
            )
        )

    return warnings


def _run_git(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command, returning (returncode, stdout, stderr). Never raises."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def _repo_root_for(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "validators").is_dir():
            return candidate
    return Path.cwd()


def _hermes_handoff_manifest_paths(repo_root: Path) -> set[str]:
    """Read fenced manifests from any handoff in `.hermes/handoffs/` and return their union."""
    paths: set[str] = set()
    handoffs_dir = repo_root / ".hermes" / "handoffs"
    if not handoffs_dir.is_dir():
        return paths
    for handoff in sorted(handoffs_dir.glob("*.md")):
        try:
            text = handoff.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Find every fenced ```text block and treat each non-empty line as a path.
        idx = 0
        while True:
            open_idx = text.find(FENCE_OPEN, idx)
            if open_idx == -1:
                break
            start = open_idx + len(FENCE_OPEN)
            close_idx = text.find("```", start)
            if close_idx == -1:
                break
            body = text[start:close_idx].rstrip("\n")
            for line in body.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                # Heuristic: only treat as a path if it contains a slash and at most one space.
                if "/" in stripped and stripped.count(" ") == 0:
                    paths.add(stripped)
            idx = close_idx + 3
    return paths


def run_with_base(paths: Iterable[Path], base: str) -> CheckResult:
    """`verify-attribution --base <commit>` mode."""
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    errors: list[ValidationError] = []

    manifest_paths = _hermes_handoff_manifest_paths(repo_root)
    if not manifest_paths:
        errors.append(
            make_error(
                "role_boundary_no_active_handoff",
                str(repo_root / ".hermes" / "handoffs"),
                "",
                (
                    "verify-attribution --base requires at least one readable handoff under "
                    ".hermes/handoffs/ that declares a fenced path manifest; none was found"
                ),
                CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    returncode, stdout, stderr = _run_git(["diff", "--name-only", f"{base}..HEAD"], repo_root)
    if returncode != 0:
        errors.append(
            make_error(
                "role_boundary_git_diff_failed",
                str(repo_root),
                "",
                f"git diff --name-only {base}..HEAD failed: {stderr.strip() or 'unknown error'}",
                CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    changed = [line.strip() for line in stdout.splitlines() if line.strip()]
    for path in changed:
        if path not in manifest_paths:
            errors.append(
                make_error(
                    "role_boundary_attribution_unaccounted",
                    path,
                    "",
                    (
                        f"changed file '{path}' is not present in any active handoff manifest "
                        f"under .hermes/handoffs/; possible controller-seat edit "
                        "(R-011) — verify implementer-pane transcript shows authorship"
                    ),
                    CONTRACT,
                )
            )

    return CheckResult(name=CHECK_NAME, errors=tuple(errors))


@register(CHECK_NAME, ["R-011", "WH-003"])
def run(paths: Iterable[Path]) -> CheckResult:
    """Default whole-tree advisory mode. Returns warnings, not errors."""
    warnings: list[ValidationError] = []
    for doc in _iter_documents([Path(p) for p in paths] or [Path(".")]):
        try:
            text = doc.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        warnings.extend(scan_document(doc, text))
    return CheckResult(name=CHECK_NAME, warnings=tuple(warnings))
