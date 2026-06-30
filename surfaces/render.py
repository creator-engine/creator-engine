"""Render rented-surface manifest values for builds and launch environments."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATORS_ROOT = REPO_ROOT / "validators"
if VALIDATORS_ROOT.is_dir():
    sys.path.insert(0, str(VALIDATORS_ROOT))

from creator_engine_validator.loader import LoaderError, load_yaml  # noqa: E402


DEFAULT_MANIFEST = REPO_ROOT / "surfaces" / "manifest.yaml"
PENDING_DIGEST_SURFACES = frozenset({"codex", "pyyaml", "jsonschema", "textual"})
ARCH_ALIASES = {
    "amd64": "amd64",
    "x86_64": "amd64",
    "linux/amd64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
    "linux/arm64": "arm64",
}


class RenderError(ValueError):
    """Raised when the manifest cannot be rendered safely."""


@dataclass(frozen=True)
class Rendered:
    """Rendered key/value pairs plus non-fatal warnings."""

    values: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...] = ()


def _surface_key(name: object) -> str:
    return re.sub(r"[\s_]+", "-", str(name).strip().lower())


def _env_key(value: object) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip().upper()).strip("_")
    if not key:
        raise RenderError(f"cannot derive environment key from {value!r}")
    if key[0].isdigit():
        key = f"CE_{key}"
    return key


def _is_host_only(surface: Mapping[str, Any]) -> bool:
    source = str(surface.get("source", "")).lower()
    custody = str(surface.get("custody", "")).lower()
    update_policy = str(surface.get("update_policy", "")).lower()
    return source.startswith("host:") or "host-only" in custody or "host inventory" in update_policy


def _load_surfaces(manifest: Path) -> list[Mapping[str, Any]]:
    try:
        data = load_yaml(manifest)
    except LoaderError as exc:
        raise RenderError(str(exc)) from exc

    if not isinstance(data, Mapping) or not isinstance(data.get("surfaces"), list):
        raise RenderError(f"{manifest}: expected a mapping with a surfaces list")

    surfaces: list[Mapping[str, Any]] = []
    for index, entry in enumerate(data["surfaces"]):
        if not isinstance(entry, Mapping):
            raise RenderError(f"{manifest}: surfaces[{index}] must be a mapping")
        if not entry.get("name"):
            raise RenderError(f"{manifest}: surfaces[{index}] must have a name")
        surfaces.append(entry)
    return surfaces


def _is_docker_image_source(source: object) -> bool:
    return isinstance(source, str) and source.startswith("docker.io/")


def _is_base_image_surface(surface: Mapping[str, Any]) -> bool:
    custody = str(surface.get("custody", "")).lower()
    return "docker-base-image" in custody and _is_docker_image_source(surface.get("source"))


def _normal_arch(value: object) -> str | None:
    if value is None:
        return None
    return ARCH_ALIASES.get(str(value).strip().lower())


def _digest_value(surface_name: object, arch: object, payload: object) -> str:
    if isinstance(payload, str):
        digest = payload
    elif isinstance(payload, Mapping):
        digest = payload.get("sha256")
    else:
        digest = None
    if not isinstance(digest, str) or not digest:
        raise RenderError(f"{surface_name}: commit_or_digest.{arch} must be a sha256 digest")
    return digest


def _digest_entries(
    prefix: str,
    digest: object,
    surface_name: object,
    *,
    build_args: bool,
    source: object,
    target_arch: str | None,
    base_image: bool,
) -> tuple[tuple[str, str], ...]:
    if isinstance(digest, str):
        if not digest:
            raise RenderError(f"{surface_name}: commit_or_digest must not be empty")
        if build_args and _is_docker_image_source(source):
            digest = digest.removeprefix("sha256:")
        return ((f"{prefix}_COMMIT_OR_DIGEST", digest),)
    if isinstance(digest, Mapping):
        if base_image and target_arch is not None:
            for arch, payload in digest.items():
                if _normal_arch(arch) != target_arch:
                    continue
                sha256 = _digest_value(surface_name, arch, payload)
                if build_args and _is_docker_image_source(source):
                    sha256 = sha256.removeprefix("sha256:")
                return ((f"{prefix}_COMMIT_OR_DIGEST", sha256),)
            raise RenderError(f"{surface_name}: commit_or_digest missing target architecture {target_arch!r}")

        entries: list[tuple[str, str]] = []
        for arch, payload in sorted(digest.items(), key=lambda item: str(item[0])):
            sha256 = _digest_value(surface_name, arch, payload)
            if isinstance(payload, Mapping):
                entries.append((f"{prefix}_{_env_key(arch)}_SHA256", sha256))
            else:
                if build_args and _is_docker_image_source(source):
                    sha256 = sha256.removeprefix("sha256:")
                entries.append((f"{prefix}_{_env_key(arch)}_COMMIT_OR_DIGEST", sha256))
        if not entries:
            raise RenderError(f"{surface_name}: commit_or_digest mapping must not be empty")
        return tuple(entries)
    raise RenderError(f"{surface_name}: commit_or_digest must be a string, mapping, or null")


def _source_value(surface: Mapping[str, Any], *, build_args: bool) -> str | None:
    source = surface.get("source")
    if not isinstance(source, str) or not source:
        return None
    version = surface.get("version")
    if build_args and isinstance(version, str) and version and source.endswith(f":{version}"):
        return source[: -(len(version) + 1)]
    return source


def _base_entries(
    surface: Mapping[str, Any],
    *,
    build_args: bool,
    target_arch: str | None,
) -> tuple[tuple[str, str], ...]:
    prefix = _env_key(surface["name"])
    entries: list[tuple[str, str]] = []
    version = surface.get("version")
    raw_source = surface.get("source")
    source = _source_value(surface, build_args=build_args)
    if source is not None:
        entries.append((f"{prefix}_SOURCE", source))
    if isinstance(version, str) and version:
        entries.append((f"{prefix}_VERSION", version))
    entries.extend(
        _digest_entries(
            prefix,
            surface.get("commit_or_digest"),
            surface["name"],
            build_args=build_args,
            source=raw_source,
            target_arch=target_arch,
            base_image=_is_base_image_surface(surface),
        )
    )
    return tuple(entries)


def _null_digest_warning(surface: Mapping[str, Any]) -> str:
    return f"{surface['name']}: commit_or_digest is null; no digest/ref value emitted"


def _collect_values(
    surfaces: Iterable[Mapping[str, Any]],
    *,
    build_args: bool,
    target_arch: str | None,
) -> Rendered:
    values: list[tuple[str, str]] = []
    warnings: list[str] = []

    for surface in surfaces:
        name = surface["name"]
        key = _surface_key(name)
        digest = surface.get("commit_or_digest")
        host_only = _is_host_only(surface)

        if digest is None:
            if host_only or key in PENDING_DIGEST_SURFACES:
                warnings.append(_null_digest_warning(surface))
                if not build_args:
                    partial = []
                    prefix = _env_key(name)
                    source = _source_value(surface, build_args=build_args)
                    version = surface.get("version")
                    if source is not None:
                        partial.append((f"{prefix}_SOURCE", source))
                    if isinstance(version, str) and version:
                        partial.append((f"{prefix}_VERSION", version))
                    values.extend(partial)
                continue
            raise RenderError(f"{name}: required pinnable surface has null commit_or_digest")

        if host_only:
            warnings.append(f"{name}: host-only surface has a pin; build args skipped")
            if build_args:
                continue

        values.extend(_base_entries(surface, build_args=build_args, target_arch=target_arch))

    return Rendered(values=tuple(sorted(values)), warnings=tuple(warnings))


def render_build_args(manifest: str | Path = DEFAULT_MANIFEST, *, arch: str | None = None) -> Rendered:
    """Return ``--build-arg KEY=VAL`` lines for manifest-pinned surfaces."""

    rendered = _collect_values(_load_surfaces(Path(manifest)), build_args=True, target_arch=_normal_arch(arch))
    return Rendered(
        values=tuple(("--build-arg", f"{key}={value}") for key, value in rendered.values),
        warnings=rendered.warnings,
    )


def render_launch_env(manifest: str | Path = DEFAULT_MANIFEST, *, arch: str | None = None) -> Rendered:
    """Return shell export lines for all renderable manifest values."""

    rendered = _collect_values(_load_surfaces(Path(manifest)), build_args=False, target_arch=_normal_arch(arch))
    return Rendered(
        values=tuple(("export", f"{key}={shlex.quote(value)}") for key, value in rendered.values),
        warnings=rendered.warnings,
    )


def _lines(rendered: Rendered) -> list[str]:
    return [f"{prefix} {assignment}" for prefix, assignment in rendered.values]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="path to surfaces/manifest.yaml",
    )
    parser.add_argument(
        "--arch",
        default=os.environ.get("TARGETARCH") or os.environ.get("CE_TARGETARCH"),
        help="target architecture for per-arch base-image digests (amd64 or arm64)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build-args", help="emit docker build --build-arg lines")
    subparsers.add_parser("launch-env", help="emit shell export lines")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        rendered = (
            render_build_args(args.manifest, arch=args.arch)
            if args.command == "build-args"
            else render_launch_env(args.manifest, arch=args.arch)
        )
    except RenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for warning in rendered.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for line in _lines(rendered):
        print(line)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
