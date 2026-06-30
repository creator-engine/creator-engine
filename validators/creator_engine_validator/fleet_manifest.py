"""Fleet manifest loader and schema validator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .loader import LoaderError, load_yaml
from .reporting import ValidationError, make_error
from .schema import validate_with_schema

SCHEMA = "schemas/fleet-manifest.schema.yaml"
CONTRACT = SCHEMA
CODE_MALFORMED = "fleet_manifest_malformed"
CODE_SCHEMA = "fleet_manifest_schema"

FLEET_MANIFEST_FILENAMES = frozenset({"fleet-manifest.yaml", "fleet-manifest.yml"})
ROOT_KEYS = frozenset({"project", "tier", "seats", "isolation", "secrets", "identity", "egress"})
_YAML_SUFFIXES = frozenset({".yaml", ".yml"})
_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        ".venv",
        "build",
        "dist",
        "node_modules",
        "__pycache__",
    }
)


@dataclass(frozen=True)
class LoadedFleetManifest:
    """Schema-valid fleet manifest payload and source path."""

    path: Path
    data: dict[str, Any]


class FleetManifestValidationError(ValueError):
    """Raised when a fleet manifest cannot be loaded as a valid descriptor."""

    def __init__(self, errors: Iterable[ValidationError]):
        self.errors = tuple(errors)
        super().__init__("; ".join(error.format() for error in self.errors))


def _is_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _YAML_SUFFIXES


def _is_excluded(path: Path) -> bool:
    return any(part.endswith(".egg-info") or part in _EXCLUDED_PARTS for part in path.parts)


def _yaml_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    candidates: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and _is_yaml(path) and not _is_excluded(path):
            resolved = path.resolve(strict=False)
            if resolved not in seen:
                seen.add(resolved)
                candidates.append(path)
        elif path.is_dir():
            for candidate in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml")):
                if not _is_yaml(candidate) or _is_excluded(candidate):
                    continue
                resolved = candidate.resolve(strict=False)
                if resolved in seen:
                    continue
                seen.add(resolved)
                candidates.append(candidate)
    return candidates


def _looks_like_manifest_text(path: Path) -> bool:
    if path.name.endswith(".schema.yaml"):
        return False
    if path.name in FLEET_MANIFEST_FILENAMES:
        return True
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    lowered_text = text.lower()
    if "kind: fleet-manifest" in lowered_text or "kind: 'fleet-manifest'" in lowered_text:
        return True
    return all(f"{key}:" in lowered_text for key in ROOT_KEYS)


def iter_fleet_manifest_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    """Return YAML files that identify as fleet manifests.

    Discovery is intentionally conservative but fail-closed for canonical
    filenames: `fleet-manifest.yaml` and `fleet-manifest.yml` are always treated
    as fleet manifests, even if their contents are malformed.
    """

    return tuple(path for path in _yaml_paths(paths) if _looks_like_manifest_text(path))


def validate_manifest_data(data: Any, path: Path) -> list[ValidationError]:
    if not isinstance(data, dict):
        return [make_error(CODE_MALFORMED, path, "", "fleet manifest must be a mapping", CONTRACT)]
    return validate_with_schema(data, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)


def load_fleet_manifest(path: str | Path) -> LoadedFleetManifest:
    manifest_path = Path(path)
    try:
        data = load_yaml(manifest_path)
    except LoaderError as exc:
        raise FleetManifestValidationError(
            [make_error(CODE_MALFORMED, manifest_path, "", str(exc), CONTRACT)]
        ) from exc

    errors = validate_manifest_data(data, manifest_path)
    if errors:
        raise FleetManifestValidationError(errors)
    return LoadedFleetManifest(path=manifest_path, data=data)
