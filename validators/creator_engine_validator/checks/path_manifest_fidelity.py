"""Path manifest fidelity check.

Verifies that any handoff, recommended-prompt, or assignment-envelope
document under a path the consumer scans declares a fenced path
manifest whose normalized count and SHA256 match the document's own
``*_PATHS_COUNT=`` and ``*_PATHS_SHA256=`` declarations.

Emits explicit error classes used by both the validator and human
operators to disambiguate failures:

- ``path_manifest_count_mismatch``
- ``path_manifest_hash_mismatch``
- ``path_manifest_missing_declaration``
- ``path_manifest_missing_block``
- ``path_manifest_init_py_corruption``

The ``path_manifest_init_py_corruption`` class is the verifier-side
backstop for the paste-pipeline regression in which
``<package>/checks/__init__.py`` arrives as
``<package>/checks/init.py``. It is emitted at error level whenever a
fenced manifest line or a free-text path reference in the document
body is the literal corrupted form, regardless of whether the
declared count/hash also fail.

See:
  - ``docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`` for the
    operating protocol.
  - ``docs/operations/NO_COPY_PASTE_PATTERN.md`` §i for the
    ``__init__.py`` regression class.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "path_manifest_fidelity"
CONTRACT = "docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md"

# Documents we scan: handoffs, recommended prompts, envelopes, and any
# file that declares the manifest-fidelity contract by including a
# `*_PATHS_COUNT=` line.
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

COUNT_PATTERN = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)_PATHS_COUNT=(?P<value>\d+)\s*$", re.MULTILINE)
HASH_PATTERN = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)_PATHS_SHA256=(?P<value>[0-9a-f]{64})\s*$", re.MULTILINE)
FENCE_OPEN = "```text\n"
FENCE_CLOSE = "```"

# Matches the corrupted-paste regression: any path segment ending in
# `/checks/init.py` (preceded by a non-underscore character so we do
# not match the well-formed `__init__.py`).
INIT_PY_CORRUPTION_PATTERN = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z0-9_./-]+/checks/init\.py)(?![A-Za-z0-9_])")


@dataclass(frozen=True)
class Declaration:
    name: str
    count: int
    sha256: str
    count_line: int
    hash_line: int


def _normalize_manifest(lines: list[str]) -> tuple[int, str, str]:
    """Normalize a manifest. Returns (count, sha256, normalized_text)."""
    unique_sorted = sorted({line for line in lines if line})
    normalized = "\n".join(unique_sorted) + "\n"
    return len(unique_sorted), hashlib.sha256(normalized.encode("utf-8")).hexdigest(), normalized


def _line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _find_first_fence_after(text: str, offset: int) -> tuple[int, int] | None:
    """Return (start, end) byte offsets of the first ```text fenced block after `offset`.

    `start` is the offset of the first character INSIDE the fence; `end`
    is the offset of the closing fence marker.
    """
    fence_idx = text.find(FENCE_OPEN, offset)
    if fence_idx == -1:
        return None
    start = fence_idx + len(FENCE_OPEN)
    close_idx = text.find(FENCE_CLOSE, start)
    if close_idx == -1:
        return None
    return start, close_idx


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


def _document_declares_manifest(text: str) -> bool:
    return COUNT_PATTERN.search(text) is not None or HASH_PATTERN.search(text) is not None


def scan_document(text: str, path: str | Path) -> list[ValidationError]:
    """Scan a single document. Returns a list of ValidationError, empty on success."""
    errors: list[ValidationError] = []
    path_str = str(path)

    # Scan for `<package>/checks/init.py` corruption anywhere in the document.
    for match in INIT_PY_CORRUPTION_PATTERN.finditer(text):
        line = _line_of_offset(text, match.start())
        errors.append(
            make_error(
                "path_manifest_init_py_corruption",
                path_str,
                f"L{line}",
                (
                    f"corrupted path '{match.group(1)}' appears in document — "
                    "expected '__init__.py' (R-012 paste-pipeline regression)"
                ),
                CONTRACT,
            )
        )

    declarations = list(COUNT_PATTERN.finditer(text))
    hashes = {h.group("name"): h for h in HASH_PATTERN.finditer(text)}

    if not declarations and not hashes:
        return errors

    # For each COUNT declaration, require a matching SHA256 and a fenced block.
    for count_match in declarations:
        name = count_match.group("name")
        try:
            declared_count = int(count_match.group("value"))
        except ValueError:
            declared_count = -1
        count_line = _line_of_offset(text, count_match.start())
        hash_match = hashes.get(name)
        if hash_match is None:
            errors.append(
                make_error(
                    "path_manifest_missing_declaration",
                    path_str,
                    f"L{count_line}",
                    f"{name}_PATHS_COUNT declared but no matching {name}_PATHS_SHA256 line found",
                    CONTRACT,
                )
            )
            continue
        declared_hash = hash_match.group("value")
        hash_line = _line_of_offset(text, hash_match.start())

        # Find the first fenced ```text block following the LATER of the two declarations.
        search_from = max(count_match.end(), hash_match.end())
        fence = _find_first_fence_after(text, search_from)
        if fence is None:
            errors.append(
                make_error(
                    "path_manifest_missing_block",
                    path_str,
                    f"L{hash_line}",
                    f"{name}_PATHS_SHA256 declared but no fenced ```text manifest block follows",
                    CONTRACT,
                )
            )
            continue

        body = text[fence[0] : fence[1]]
        # Remove a trailing newline produced by the closing fence indentation.
        if body.endswith("\n"):
            body = body[:-1]
        raw_lines = body.split("\n")
        normalized_lines = [line for line in raw_lines if line]
        actual_count, actual_hash, _ = _normalize_manifest(normalized_lines)
        block_line = _line_of_offset(text, fence[0])

        if actual_count != declared_count:
            errors.append(
                make_error(
                    "path_manifest_count_mismatch",
                    path_str,
                    f"L{count_line}",
                    (
                        f"{name}_PATHS_COUNT declared {declared_count} but fenced manifest "
                        f"at L{block_line} normalizes to {actual_count} unique path lines"
                    ),
                    CONTRACT,
                )
            )
        if actual_hash != declared_hash:
            errors.append(
                make_error(
                    "path_manifest_hash_mismatch",
                    path_str,
                    f"L{hash_line}",
                    (
                        f"{name}_PATHS_SHA256 declared {declared_hash} but recomputed SHA256 "
                        f"of normalized manifest at L{block_line} is {actual_hash}"
                    ),
                    CONTRACT,
                )
            )

    # Any HASH without a matching COUNT is also a missing-declaration error.
    declared_count_names = {m.group("name") for m in declarations}
    for name, hash_match in hashes.items():
        if name in declared_count_names:
            continue
        hash_line = _line_of_offset(text, hash_match.start())
        errors.append(
            make_error(
                "path_manifest_missing_declaration",
                path_str,
                f"L{hash_line}",
                f"{name}_PATHS_SHA256 declared but no matching {name}_PATHS_COUNT line found",
                CONTRACT,
            )
        )

    return errors


@register(CHECK_NAME, ["R-012", "WH-001"])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for doc in _iter_documents([Path(p) for p in paths] or [Path(".")]):
        try:
            text = doc.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not _document_declares_manifest(text):
            # Still scan for init.py corruption in free text, because the
            # regression can appear in any document that names paths.
            corruption_errors = [
                err for err in scan_document(text, doc) if err.code == "path_manifest_init_py_corruption"
            ]
            errors.extend(corruption_errors)
            continue
        errors.extend(scan_document(text, doc))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
