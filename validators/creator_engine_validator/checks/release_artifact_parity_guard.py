"""Release install artifact parity guard.

The public installer is served from ``docs/install.sh`` while versioned release
downloads carry a mirrored ``install.sh`` plus the release-local ``SHA256SUMS``
entry. This check keeps those three surfaces byte-for-byte bound.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register


CHECK_NAME = "release_artifact_parity_guard"
CODE_MISSING = "release_artifact_parity_missing"
CODE_SHA256SUMS = "release_artifact_parity_sha256s"
CODE_MISMATCH = "release_artifact_parity_mismatch"
CONTRACT = "docs/llms-install.md"

INSTALL_SH = "install.sh"
SHA256SUMS = "SHA256SUMS"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / "docs" / INSTALL_SH).is_file() and (candidate / "docs" / "downloads").is_dir():
            return candidate
    return None


def _release_dirs(repo_root: Path) -> list[Path]:
    downloads = repo_root / "docs" / "downloads"
    return sorted(path for path in downloads.iterdir() if path.is_dir())


def _parse_sha256s(path: Path) -> tuple[dict[str, str], list[ValidationError]]:
    entries: dict[str, str] = {}
    errors: list[ValidationError] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 2:
            errors.append(
                make_error(
                    CODE_SHA256SUMS,
                    path,
                    str(lineno),
                    "malformed SHA256SUMS line; expected '<sha256>  <filename>'",
                    CONTRACT,
                )
            )
            continue
        digest, filename = parts
        if not SHA256_RE.fullmatch(digest):
            errors.append(
                make_error(CODE_SHA256SUMS, path, str(lineno), f"invalid sha256 digest {digest!r}", CONTRACT)
            )
        if "/" in filename or "\\" in filename or filename in {".", ".."}:
            errors.append(
                make_error(
                    CODE_SHA256SUMS,
                    path,
                    str(lineno),
                    f"filename must be release-local: {filename!r}",
                    CONTRACT,
                )
            )
            continue
        if filename in entries:
            errors.append(make_error(CODE_SHA256SUMS, path, str(lineno), f"duplicate entry for {filename}", CONTRACT))
            continue
        entries[filename] = digest
    return entries, errors


def validate_repo(repo_root: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    served = repo_root / "docs" / INSTALL_SH
    if not served.is_file():
        return [make_error(CODE_MISSING, served, "", "missing served installer", CONTRACT)]

    served_digest = _sha256(served)
    release_dirs = _release_dirs(repo_root)
    if not release_dirs:
        return [
            make_error(
                CODE_MISSING,
                repo_root / "docs" / "downloads",
                "",
                "missing versioned release download directories",
                CONTRACT,
            )
        ]

    for release_dir in release_dirs:
        mirrored = release_dir / INSTALL_SH
        sums = release_dir / SHA256SUMS
        if not sums.is_file():
            errors.append(make_error(CODE_MISSING, sums, "", "missing release SHA256SUMS", CONTRACT))
            continue
        if not mirrored.is_file():
            errors.append(make_error(CODE_MISSING, mirrored, "", "missing mirrored installer", CONTRACT))
            continue

        entries, parse_errors = _parse_sha256s(sums)
        errors.extend(parse_errors)
        entry_digest = entries.get(INSTALL_SH)
        if entry_digest is None:
            errors.append(make_error(CODE_MISSING, sums, INSTALL_SH, "missing install.sh entry", CONTRACT))
            continue

        mirrored_digest = _sha256(mirrored)
        if served_digest != entry_digest or served_digest != mirrored_digest:
            errors.append(
                make_error(
                    CODE_MISMATCH,
                    release_dir,
                    INSTALL_SH,
                    "install artifact digests differ: "
                    f"docs/install.sh={served_digest}, SHA256SUMS[{INSTALL_SH}]={entry_digest}, "
                    f"{mirrored.relative_to(repo_root).as_posix()}={mirrored_digest}",
                    CONTRACT,
                )
            )
    return errors


@register(CHECK_NAME, [CODE_MISSING, CODE_SHA256SUMS, CODE_MISMATCH])
def run(paths: Iterable[Path]) -> CheckResult:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        root = _repo_root_for(Path(raw))
        if root is None:
            continue
        resolved = root.resolve()
        if resolved not in seen:
            seen.add(resolved)
            roots.append(root)

    errors: list[ValidationError] = []
    for root in roots:
        errors.extend(validate_repo(root))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
