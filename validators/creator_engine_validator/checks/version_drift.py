"""Current-version surface drift guard.

Unsigned docs and deploy defaults that present the current Creator Engine
release version must track ``validators/creator_engine_validator/version.py``.
Historical version mentions remain legal outside the declared current-version
surface set, or on annotated lines inside it.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Pattern

from ..reporting import CheckResult, ValidationError, make_error


CHECK_NAME = "version_drift_current_surfaces"
CONTRACT = "version-drift current surface gate"
CODE_STALE = "version_drift_stale_current_claim"
CODE_MISSING_SURFACE = "version_drift_missing_surface"
CODE_VERSION_SOURCE = "version_drift_version_source"
ANNOTATION = "ce-version-drift: allow-historical"
SEMVER_RE = r"(?P<version>\d+\.\d+\.\d+)"
SEMVER_LITERAL_RE = re.compile(r"\d+\.\d+\.\d+")


@dataclass(frozen=True)
class SurfacePattern:
    label: str
    regex: Pattern[str]


@dataclass(frozen=True)
class CurrentVersionSurface:
    path: str
    patterns: tuple[SurfacePattern, ...]


def _pattern(label: str, raw: str) -> SurfacePattern:
    return SurfacePattern(label=label, regex=re.compile(raw))


PACKAGE_PIN = _pattern(
    "creator-engine-validator package pin",
    rf"creator-engine-validator=={SEMVER_RE}",
)
PACKAGE_VERSION_TEXT = _pattern(
    "creator-engine-validator package version text",
    rf"creator-engine-validator[`'\"]?\s+version[`'\"]?\s+[`'\"]{SEMVER_RE}[`'\"]",
)
README_CE_VERSION_TEXT = _pattern(
    "README CE version text",
    rf"(?i)\b(?:current\s+release|(?:ce|creator[\s-]+engine)"
    rf"(?:\s+(?:v(?:ersion)?|release|current\s+release))?)"
    rf"\s*(?::|=|\bis\b)?\s*v?{SEMVER_RE}\b(?:\s+is\s+current)?",
)
CE_VALIDATOR_IMAGE = _pattern(
    "ce-validator image tag",
    rf"creator-engine/ce-validator:{SEMVER_RE}",
)
CE_RUNTIME_IMAGE = _pattern(
    "ce-runtime image tag",
    rf"(?:ghcr\.io/creator-engine/creator-engine/)?ce-runtime:{SEMVER_RE}",
)
CE_IMAGE_VERSION_ARG = _pattern(
    "CE_IMAGE_VERSION default",
    rf"\bCE_IMAGE_VERSION={SEMVER_RE}\b",
)
DOWNLOADS_VERSION_URL = _pattern(
    "current downloads URL",
    rf"/downloads/{SEMVER_RE}/",
)


CURRENT_VERSION_SURFACES: tuple[CurrentVersionSurface, ...] = (
    CurrentVersionSurface("README.md", (PACKAGE_PIN, PACKAGE_VERSION_TEXT, README_CE_VERSION_TEXT)),
    CurrentVersionSurface("docs/llms.txt", (DOWNLOADS_VERSION_URL,)),
    CurrentVersionSurface("deploy/oci/README.md", (CE_VALIDATOR_IMAGE,)),
    CurrentVersionSurface("deploy/oci/build-image.sh", (CE_VALIDATOR_IMAGE,)),
    CurrentVersionSurface("deploy/daemons/Dockerfile", (CE_VALIDATOR_IMAGE,)),
    CurrentVersionSurface("deploy/daemons/README.md", (CE_RUNTIME_IMAGE,)),
    CurrentVersionSurface("deploy/daemons/run-daemon-container.sh", (CE_RUNTIME_IMAGE,)),
    CurrentVersionSurface("deploy/runtime-image/Dockerfile", (CE_IMAGE_VERSION_ARG,)),
    CurrentVersionSurface("deploy/seat-image/Dockerfile", (CE_IMAGE_VERSION_ARG,)),
)


def _allowed_historical_versions(line: str) -> frozenset[str]:
    marker_at = line.find(ANNOTATION)
    if marker_at == -1:
        return frozenset()
    annotation_tail = line[marker_at + len(ANNOTATION) :]
    return frozenset(SEMVER_LITERAL_RE.findall(annotation_tail))


def _repo_root_for(path: Path) -> Path | None:
    raw = path if path.is_absolute() else Path.cwd() / path
    start = raw if raw.is_dir() else raw.parent
    for candidate in (start, *start.parents):
        if (candidate / "validators" / "creator_engine_validator" / "version.py").is_file():
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


def read_current_version(repo_root: Path) -> str:
    version_py = repo_root / "validators" / "creator_engine_validator" / "version.py"
    try:
        tree = ast.parse(version_py.read_text(encoding="utf-8"), filename=str(version_py))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError(f"could not read canonical version source {version_py}: {exc}") from exc
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
        break
    raise ValueError(f"no string __version__ assignment found in {version_py}")


def evaluate(
    repo_root: Path,
    *,
    current_version: str | None = None,
    surfaces: tuple[CurrentVersionSurface, ...] = CURRENT_VERSION_SURFACES,
) -> tuple[ValidationError, ...]:
    try:
        expected = current_version if current_version is not None else read_current_version(repo_root)
    except ValueError as exc:
        return (
            make_error(
                CODE_VERSION_SOURCE,
                "validators/creator_engine_validator/version.py",
                "",
                str(exc),
                CONTRACT,
            ),
        )

    errors: list[ValidationError] = []
    for surface in surfaces:
        path = repo_root / surface.path
        if not path.is_file():
            errors.append(
                make_error(
                    CODE_MISSING_SURFACE,
                    surface.path,
                    "",
                    "declared current-version surface is missing",
                    CONTRACT,
                )
            )
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(
                make_error(
                    CODE_MISSING_SURFACE,
                    surface.path,
                    "",
                    f"could not read declared current-version surface: {exc}",
                    CONTRACT,
                )
            )
            continue
        for lineno, line in enumerate(lines, start=1):
            allowed_historical = _allowed_historical_versions(line)
            for pattern in surface.patterns:
                for match in pattern.regex.finditer(line):
                    found = match.group("version")
                    if found == expected:
                        continue
                    if found in allowed_historical:
                        continue
                    errors.append(
                        make_error(
                            CODE_STALE,
                            surface.path,
                            str(lineno),
                            f"{pattern.label} is {found!r}; expected current release version {expected!r}",
                            CONTRACT,
                        )
                    )
    return tuple(errors)


def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for root in _repo_roots(paths):
        errors.extend(evaluate(root))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
