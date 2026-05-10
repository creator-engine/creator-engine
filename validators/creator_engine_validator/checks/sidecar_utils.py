"""Helpers shared by sidecar checks."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

SIDECAR_KINDS = {
    "spec": ("spec.creator-engine.yml", "spec.creator-engine"),
    "plan": ("plan.creator-engine.yml", "plan.creator-engine"),
    "tasks": ("tasks.creator-engine.yml", "tasks.creator-engine"),
}


def is_under_malformed_examples(path: Path) -> bool:
    return "examples" in path.parts and "malformed" in path.parts


def sidecar_kind(path: Path) -> str | None:
    if "schemas" in path.parts or "templates" in path.parts:
        return None
    if path.suffix not in {".yml", ".yaml"}:
        return None
    for kind, (canonical, prefix) in SIDECAR_KINDS.items():
        if path.name == canonical or path.name.startswith(prefix + "."):
            return kind
    return None


def iter_sidecar_paths(paths: Iterable[Path], *, kind: str | None = None) -> list[Path]:
    seen: set[Path] = set()
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        explicit_malformed = is_under_malformed_examples(path)
        if path.is_file() and sidecar_kind(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [p for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml")) if sidecar_kind(p)]
            if not explicit_malformed:
                candidates = [p for p in candidates if not is_under_malformed_examples(p)]
        else:
            candidates = []
        for candidate in candidates:
            if kind is not None and sidecar_kind(candidate) != kind:
                continue
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.append(candidate)
    return found
