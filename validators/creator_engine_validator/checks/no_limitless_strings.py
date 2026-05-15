"""No-LIMITLESS generic-path scan (FR-024, FR-024a, SC-004).

Enforces FR-024: the four generic-contract paths (``docs/contracts/``,
``schemas/``, ``validators/``, ``templates/``) MUST NOT contain
LIMITLESS-specific identifiers. LIMITLESS-specific values live only
under ``tenants/limitless/``.

When ``tenants/limitless/limitless-identifiers.yml`` is published per
FR-024a, the scanner uses its identifier list verbatim; otherwise it
falls back to the literal token ``limitless`` so that LIMITLESS-typed
content cannot enter generic-contract paths even pre-fixture.

The scanner is the only LIMITLESS scanner; the scanner module and its
test files legitimately reference LIMITLESS by name. Other generic-path
files may reference LIMITLESS only through one of the documented
self-reference phrases listed in ``SELF_REFERENCE_PHRASES`` (for
example, the CLI subcommand name ``scan-no-limitless``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "no_limitless_strings"
CONTRACT = "specs/001-v0-1-governance-substrate/contracts/validator-cli.contract.md"

GENERIC_PATHS: tuple[str, ...] = (
    "docs/contracts",
    "schemas",
    "validators",
    "templates",
)

DEFAULT_TOKENS: tuple[str, ...] = ("limitless",)

SELF_REFERENCE_FILES: frozenset[str] = frozenset(
    {
        "validators/creator_engine_validator/checks/no_limitless_strings.py",
        "validators/tests/unit/test_no_limitless_strings.py",
        "validators/tests/integration/test_no_limitless_strings.py",
    }
)

SELF_REFERENCE_PHRASES: tuple[str, ...] = (
    "scan-no-limitless",
    "no-limitless",
    "no_limitless",
    "no limitless",
    "limitless scanner",
    "limitless-specific",
)

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {"__pycache__", "wheelhouse", "wheelhouse-dev", ".egg-info", ".mypy_cache", ".pytest_cache"}
)

SKIP_SUFFIXES: frozenset[str] = frozenset(
    {".pyc", ".pyo", ".whl", ".tar", ".gz", ".zip", ".so", ".dylib", ".dll",
     ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".bin"}
)


def _repo_root_for(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "validators").is_dir():
            return candidate
    return Path.cwd()


def _load_tokens(repo_root: Path) -> tuple[str, ...]:
    """Load LIMITLESS identifiers from the tenant fixture if present."""
    identifiers_path = repo_root / "tenants" / "limitless" / "limitless-identifiers.yml"
    if not identifiers_path.is_file():
        return DEFAULT_TOKENS
    try:
        data = load_yaml(identifiers_path)
    except LoaderError:
        return DEFAULT_TOKENS
    if not isinstance(data, dict):
        return DEFAULT_TOKENS
    raw = data.get("identifiers")
    if not isinstance(raw, list):
        return DEFAULT_TOKENS
    tokens = tuple(
        sorted(
            {
                str(item).strip().lower()
                for item in raw
                if isinstance(item, str) and str(item).strip()
            }
        )
    )
    return tokens or DEFAULT_TOKENS


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def _iter_text_files(roots: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            candidates: list[Path] = [root]
        else:
            candidates = []
            for path in sorted(root.rglob("*")):
                if any(part in SKIP_DIR_NAMES for part in path.parts):
                    continue
                if path.is_file():
                    candidates.append(path)
        for path in candidates:
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def _scan_text(text: str, tokens: Iterable[str]) -> list[tuple[int, int, str]]:
    lower = text.lower()
    hits: list[tuple[int, int, str]] = []
    for token in tokens:
        needle = token.lower()
        if not needle:
            continue
        start = 0
        while True:
            idx = lower.find(needle, start)
            if idx == -1:
                break
            window = lower[max(0, idx - 32) : idx + len(needle) + 32]
            if not any(phrase in window for phrase in SELF_REFERENCE_PHRASES):
                line = text.count("\n", 0, idx) + 1
                line_start = text.rfind("\n", 0, idx) + 1
                col = idx - line_start + 1
                hits.append((line, col, token))
            start = idx + len(needle)
    hits.sort()
    return hits


def _resolve_scan_roots(paths: Iterable[Path]) -> tuple[Path, list[Path]]:
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    scan_roots: list[Path] = []
    repo_root_resolved = repo_root.resolve()
    for path in raw_paths:
        try:
            resolved = path.resolve()
        except OSError:
            scan_roots.append(path)
            continue
        if path.is_dir() and resolved == repo_root_resolved:
            for sub in GENERIC_PATHS:
                scan_roots.append(repo_root / sub)
        else:
            scan_roots.append(path)
    return repo_root, scan_roots


@register(CHECK_NAME, ["FR-024", "FR-024a", "SC-004"])
def run(paths: Iterable[Path]) -> CheckResult:
    repo_root, scan_roots = _resolve_scan_roots(paths)
    tokens = _load_tokens(repo_root)
    errors: list[ValidationError] = []
    for file_path in _iter_text_files(scan_roots):
        rel = _relative(file_path, repo_root)
        if rel in SELF_REFERENCE_FILES:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line, col, token in _scan_text(text, tokens):
            errors.append(
                make_error(
                    "FR-024",
                    file_path,
                    f"L{line}C{col}",
                    f"LIMITLESS-specific token '{token}' found in generic-contract path",
                    CONTRACT,
                )
            )
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
