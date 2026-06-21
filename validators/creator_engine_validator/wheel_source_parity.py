"""Shared source-built first-party wheel/source parity gate.

The v1 packaging runtime and the shared brain probes both need this check. It
stays in a shared helper so probes can preserve the source-built wheel behavior
without importing the v1 ``packaging_runtime`` surface.
"""
from __future__ import annotations

import ast
import re
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Callable, Iterable

from .wheel_bake import WheelBakeError, WheelManifest, build_app_wheel_from_source

DISTRIBUTION_NAME = "creator-engine-validator"

BuildAppWheel = Callable[[Path | str, Path | str], WheelManifest]


def _normalize_name(name: str) -> str:
    """PEP 503 normalization (lower-case, runs of ``-_.`` collapse to ``-``)."""
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def _wheel_filename_parts(filename: str) -> tuple[str, str] | None:
    """Return ``(normalized distribution, version)`` from a wheel filename."""
    if not filename.endswith(".whl"):
        return None
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return None
    return _normalize_name(parts[0]), parts[1]


def _pyproject_version(path: Path | str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    version = tomllib.loads(p.read_text(encoding="utf-8")).get("project", {}).get("version")
    return version if isinstance(version, str) else None


def _source_declared_version(path: Path | str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return None


def _app_wheel_source_violations(root: Path, wheels: Iterable[Path]) -> list[str]:
    validators = root / "validators"
    source_root = validators / "creator_engine_validator"
    v: list[str] = []
    pyproject_version = _pyproject_version(validators / "pyproject.toml")
    source_version = _source_declared_version(source_root / "version.py")
    if pyproject_version is None:
        v.append(f"missing project version in {validators / 'pyproject.toml'}")
    if source_version is None:
        v.append(f"missing __version__ in {source_root / 'version.py'}")
    if pyproject_version and source_version and pyproject_version != source_version:
        v.append(
            f"pyproject version {pyproject_version!r} differs from "
            f"creator_engine_validator.version.__version__ {source_version!r}"
        )

    source_files = {
        path.relative_to(source_root).as_posix(): path
        for path in source_root.rglob("*.py")
        if path.is_file()
    }

    for wheel in wheels:
        parsed = _wheel_filename_parts(wheel.name)
        if parsed is None:
            v.append(f"invalid app wheel filename: {wheel.name}")
            continue
        wheel_dist, wheel_version = parsed
        if wheel_dist != DISTRIBUTION_NAME:
            v.append(
                f"app wheel {wheel.name} distribution must be {DISTRIBUTION_NAME!r}, "
                f"got {wheel_dist!r}"
            )
        if pyproject_version and wheel_version != pyproject_version:
            v.append(
                f"app wheel {wheel.name} version {wheel_version!r} differs from "
                f"pyproject version {pyproject_version!r}"
            )
        if source_version and wheel_version != source_version:
            v.append(
                f"app wheel {wheel.name} version {wheel_version!r} differs from "
                f"creator_engine_validator.version.__version__ {source_version!r}"
            )

        try:
            with zipfile.ZipFile(wheel) as zf:
                wheel_files = {
                    name.removeprefix("creator_engine_validator/")
                    for name in zf.namelist()
                    if name.startswith("creator_engine_validator/") and name.endswith(".py")
                }
                for rel in sorted(wheel_files - source_files.keys()):
                    v.append(f"app wheel {wheel.name} has no source file for {rel}")
                for rel in sorted(source_files.keys() - wheel_files):
                    v.append(f"app wheel {wheel.name} missing source file {rel}")
                for rel in sorted(source_files.keys() & wheel_files):
                    wheel_bytes = zf.read(f"creator_engine_validator/{rel}")
                    source_bytes = source_files[rel].read_bytes()
                    if wheel_bytes != source_bytes:
                        v.append(f"app wheel {wheel.name} differs from source file {rel}")
        except zipfile.BadZipFile:
            v.append(f"invalid app wheel zip archive: {wheel}")
    return v


def verify_wheel_matches_source(
    repo_root: Path | str,
    *,
    build_app_wheel: BuildAppWheel = build_app_wheel_from_source,
    wheel_bake_error: type[BaseException] = WheelBakeError,
) -> list[str]:
    """Build the app wheel from checkout source and report wheel/source drift.

    Installed end-user contexts may have only the wheel and no source checkout,
    so this remains a no-op when ``validators/creator_engine_validator`` is
    absent. In source-checkout contexts the gate must not silently pass just
    because ``validators/wheelhouse`` no longer commits a first-party app wheel:
    it builds a temporary wheel with the standard wheel-bake helper, then
    compares that built surface against the checkout source.
    """
    root = Path(repo_root)
    source_root = root / "validators" / "creator_engine_validator"
    if not source_root.is_dir():
        return []

    with tempfile.TemporaryDirectory(prefix="ce-app-wheel-") as tmp:
        out_dir = Path(tmp)
        try:
            manifest = build_app_wheel(root, out_dir)
        except wheel_bake_error as exc:
            return [f"app wheel build from source failed: {exc}"]
        wheel = out_dir / manifest.wheel_name
        if not wheel.is_file():
            return [f"app wheel build from source did not produce {wheel.name}"]
        return _app_wheel_source_violations(root, [wheel])
