"""Filesystem and YAML loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

CANONICAL_SIDECAR_NAMES = {
    "spec.md": "spec.creator-engine.yml",
    "plan.md": "plan.creator-engine.yml",
    "tasks.md": "tasks.creator-engine.yml",
}
TENANT_IDENTITY_FILENAME = "identity-record.yml"


class LoaderError(ValueError):
    """Raised when a file cannot be loaded as YAML."""


def load_yaml(path: str | Path) -> Any:
    """Load YAML with yaml.safe_load, returning an empty dict for empty files."""
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise LoaderError("PyYAML is required; install validators/requirements.txt") from exc

    p = Path(path)
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:
        raise LoaderError(f"failed to load YAML from {p}: {exc}") from exc
    return {} if data is None else data


def discover_sidecar(markdown_path: str | Path) -> Path | None:
    """Return the canonical Creator Engine sidecar adjacent to a Spec Kit file."""
    p = Path(markdown_path)
    sidecar_name = CANONICAL_SIDECAR_NAMES.get(p.name)
    if sidecar_name is None:
        return None
    candidate = p.with_name(sidecar_name)
    return candidate if candidate.exists() else None


def iter_sidecars(paths: Iterable[str | Path]) -> Iterable[Path]:
    """Yield canonical sidecars found by directory adjacency below paths."""
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        candidates: list[Path]
        if p.is_dir():
            candidates = sorted(p.rglob("*.md"))
        else:
            candidates = [p]
        for md in candidates:
            sidecar = discover_sidecar(md)
            if sidecar and sidecar not in seen:
                seen.add(sidecar)
                yield sidecar


def iter_tenant_identity_records(paths: Iterable[str | Path]) -> Iterable[Path]:
    """Yield tenant identity records under provided paths."""
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_file() and p.name == TENANT_IDENTITY_FILENAME:
            candidates = [p]
        elif p.is_dir():
            candidates = sorted(p.rglob(TENANT_IDENTITY_FILENAME))
        else:
            candidates = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                yield candidate
