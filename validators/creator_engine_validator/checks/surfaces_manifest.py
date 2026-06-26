"""Rented-surface manifest completeness check (ce-ops#272)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import yaml

from ..reporting import CheckResult, ValidationError, make_error
from . import register


CHECK_NAME = "surfaces_manifest_complete"
CONTRACT = "ce-ops#272"

CODE_MISSING_MANIFEST = "surfaces_manifest_missing"
CODE_MALFORMED = "surfaces_manifest_malformed"
CODE_MISSING_SURFACE = "surfaces_manifest_missing_surface"
CODE_MISSING_FIELD = "surfaces_manifest_missing_field"
CODE_PINNABLE_MISSING_DIGEST = "surfaces_manifest_pinnable_missing_digest"
CODE_PYTHON_DIGEST_WARNING = "surfaces_manifest_python_digest_pending"

MANIFEST = Path("surfaces/manifest.yaml")
REQUIRED_FIELDS = frozenset(
    {
        "name",
        "version",
        "commit_or_digest",
        "source",
        "custody",
        "update_policy",
        "last_evaluated",
    }
)
KNOWN_SURFACES = frozenset(
    {
        "codex",
        "herdr",
        "zig-toolchain",
        "pyyaml",
        "jsonschema",
        "textual",
        "openbao",
        "gvisor/runsc",
        "gvproxy",
    }
)
PYTHON_DEP_SURFACES = frozenset({"pyyaml", "jsonschema", "textual"})
ZIG_ARCHES = frozenset({"linux-aarch64", "linux-x86_64"})
SHA_RE = re.compile(r"^[0-9a-f]{8,40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _surface_key(name: object) -> str:
    return re.sub(r"[\s_]+", "-", str(name).strip().lower())


def _repo_root_for(path: Path) -> Path | None:
    raw = Path(path)
    if not raw.is_absolute():
        raw = Path.cwd() / raw
    start = raw if raw.is_dir() else raw.parent
    for candidate in (start, *start.parents):
        if (candidate / MANIFEST).is_file():
            return candidate
        if (candidate / "validators" / "creator_engine_validator" / "checks").is_dir():
            return candidate
    return None


def _repo_roots(paths: Iterable[Path]) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        root = _repo_root_for(Path(raw))
        if root is None:
            continue
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(root)
    return roots


def _load_manifest(path: Path) -> tuple[list[dict[str, Any]], list[ValidationError]]:
    if not path.is_file():
        return [], [make_error(CODE_MISSING_MANIFEST, path, "", "missing surfaces manifest", CONTRACT)]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return [], [make_error(CODE_MALFORMED, path, "", f"could not parse YAML: {exc}", CONTRACT)]

    if not isinstance(data, dict) or not isinstance(data.get("surfaces"), list):
        return [], [
            make_error(CODE_MALFORMED, path, "surfaces", "expected a mapping with a surfaces list", CONTRACT)
        ]

    surfaces: list[dict[str, Any]] = []
    errors: list[ValidationError] = []
    for index, entry in enumerate(data["surfaces"]):
        if not isinstance(entry, dict):
            errors.append(
                make_error(CODE_MALFORMED, path, f"surfaces[{index}]", "surface entry must be a mapping", CONTRACT)
            )
            continue
        surfaces.append(entry)
    return surfaces, errors


def _missing_required_fields(path: Path, surfaces: list[dict[str, Any]]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for index, surface in enumerate(surfaces):
        name = surface.get("name", f"surfaces[{index}]")
        for field in sorted(REQUIRED_FIELDS - set(surface)):
            errors.append(
                make_error(
                    CODE_MISSING_FIELD,
                    path,
                    f"{name}.{field}",
                    f"surface {name!r} is missing required field {field!r}",
                    CONTRACT,
                )
            )
    return errors


def _index_surfaces(path: Path, surfaces: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[ValidationError]]:
    by_name: dict[str, dict[str, Any]] = {}
    errors: list[ValidationError] = []
    for surface in surfaces:
        key = _surface_key(surface.get("name", ""))
        if not key:
            continue
        if key in by_name:
            errors.append(
                make_error(CODE_MALFORMED, path, str(surface.get("name")), "duplicate surface name", CONTRACT)
            )
            continue
        by_name[key] = surface

    for expected in sorted(KNOWN_SURFACES - set(by_name)):
        errors.append(
            make_error(CODE_MISSING_SURFACE, path, expected, f"missing currently-known surface {expected!r}", CONTRACT)
        )
    return by_name, errors


def _validate_herdr(path: Path, surface: dict[str, Any] | None) -> list[ValidationError]:
    if surface is None:
        return []
    commit = surface.get("commit_or_digest")
    if not isinstance(commit, str) or not SHA_RE.fullmatch(commit):
        return [
            make_error(
                CODE_PINNABLE_MISSING_DIGEST,
                path,
                "herdr.commit_or_digest",
                "herdr must carry a fork commit SHA",
                CONTRACT,
            )
        ]
    return []


def _validate_zig(path: Path, surface: dict[str, Any] | None) -> list[ValidationError]:
    if surface is None:
        return []
    digests = surface.get("commit_or_digest")
    if not isinstance(digests, dict):
        return [
            make_error(
                CODE_PINNABLE_MISSING_DIGEST,
                path,
                "Zig toolchain.commit_or_digest",
                "Zig toolchain must carry per-architecture sha256 digests",
                CONTRACT,
            )
        ]

    errors: list[ValidationError] = []
    for arch in sorted(ZIG_ARCHES):
        entry = digests.get(arch)
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(
                make_error(
                    CODE_PINNABLE_MISSING_DIGEST,
                    path,
                    f"Zig toolchain.commit_or_digest.{arch}.sha256",
                    "Zig toolchain must carry a 64-hex sha256 digest for each supported architecture",
                    CONTRACT,
                )
            )
    return errors


def _python_digest_warnings(path: Path, by_name: dict[str, dict[str, Any]]) -> list[ValidationError]:
    warnings: list[ValidationError] = []
    for name in sorted(PYTHON_DEP_SURFACES):
        surface = by_name.get(name)
        if surface is not None and surface.get("commit_or_digest") is None:
            warnings.append(
                make_error(
                    CODE_PYTHON_DIGEST_WARNING,
                    path,
                    f"{surface.get('name')}.commit_or_digest",
                    "Python package digest is not in requirements pins yet; warning only in Phase 1",
                    CONTRACT,
                )
            )
    return warnings


def validate_repo(repo_root: Path) -> CheckResult:
    manifest = repo_root / MANIFEST
    surfaces, errors = _load_manifest(manifest)
    warnings: list[ValidationError] = []
    if surfaces:
        errors.extend(_missing_required_fields(manifest, surfaces))
        by_name, index_errors = _index_surfaces(manifest, surfaces)
        errors.extend(index_errors)
        errors.extend(_validate_herdr(manifest, by_name.get("herdr")))
        errors.extend(_validate_zig(manifest, by_name.get("zig-toolchain")))
        warnings.extend(_python_digest_warnings(manifest, by_name))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))


@register(CHECK_NAME, [CONTRACT])
def run(paths: Iterable[Path]) -> CheckResult:
    roots = _repo_roots(paths or [Path(".")])
    if not roots:
        roots = [Path.cwd()]

    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    for root in roots:
        result = validate_repo(root)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
