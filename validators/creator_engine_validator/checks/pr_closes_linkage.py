"""PR manifest closes-linkage check (ce-ops#262)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "pr_closes_linkage"
CONTRACT = "ce-ops#262"
CODE_MISSING = "pr_closes_linkage_missing"
CODE_MISMATCH = "pr_closes_linkage_mismatch"

MANIFEST_DIR_PARTS = (".ce", "pr-manifests")
CE_PREFIX_PATTERN = re.compile(r"^ce(?P<number>\d+)-")
CLOSES_PATTERN = re.compile(r"^Closes creator-engine/ce-ops#(?P<number>\d+)\s*$", re.MULTILINE)


def _is_manifest_file(path: Path) -> bool:
    if path.suffix.lower() != ".md":
        return False
    parts = path.parts
    return len(parts) >= 3 and parts[-3:-1] == MANIFEST_DIR_PARTS


def _iter_manifest_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        candidates: list[Path] = []
        if path.is_file():
            if _is_manifest_file(path):
                candidates.append(path)
        elif path.is_dir():
            if path.name == MANIFEST_DIR_PARTS[-1] and path.parent.name == MANIFEST_DIR_PARTS[0]:
                candidates.extend(sorted(path.glob("*.md")))
            else:
                manifest_dir = path / MANIFEST_DIR_PARTS[0] / MANIFEST_DIR_PARTS[1]
                if manifest_dir.is_dir():
                    candidates.extend(sorted(manifest_dir.glob("*.md")))
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_manifest(path: Path, text: str) -> tuple[list[ValidationError], list[ValidationError]]:
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    prefix_match = CE_PREFIX_PATTERN.match(path.name)
    if prefix_match is None:
        return errors, warnings

    expected_number = prefix_match.group("number")
    closes_matches = list(CLOSES_PATTERN.finditer(text))
    if not closes_matches:
        warnings.append(
            make_error(
                CODE_MISSING,
                path,
                "Closes",
                f"manifest filename implies ce-ops#{expected_number} but no matching Closes line is present",
                CONTRACT,
            )
        )
        return errors, warnings

    for match in closes_matches:
        actual_number = match.group("number")
        if actual_number == expected_number:
            continue
        errors.append(
            make_error(
                CODE_MISMATCH,
                path,
                f"L{_line_of_offset(text, match.start())}",
                (
                    f"manifest filename implies ce-ops#{expected_number} but Closes line "
                    f"targets ce-ops#{actual_number}"
                ),
                CONTRACT,
            )
        )

    return errors, warnings


@register(CHECK_NAME, [CONTRACT])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    for manifest_path in _iter_manifest_files(raw_paths):
        try:
            text = manifest_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        manifest_errors, manifest_warnings = scan_manifest(manifest_path, text)
        errors.extend(manifest_errors)
        warnings.extend(manifest_warnings)
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
