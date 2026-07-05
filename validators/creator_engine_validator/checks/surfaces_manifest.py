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
CONSISTENT_CHECK_NAME = "surfaces_manifest_consistent"
CONSISTENT_CONTRACT = "ce-ops#273"
CARRIER_CHECK_NAME = "surfaces_bump_has_carrier"
CARRIER_CONTRACT = "ce-ops#277"

CODE_MISSING_MANIFEST = "surfaces_manifest_missing"
CODE_MALFORMED = "surfaces_manifest_malformed"
CODE_MISSING_SURFACE = "surfaces_manifest_missing_surface"
CODE_MISSING_FIELD = "surfaces_manifest_missing_field"
CODE_PINNABLE_MISSING_DIGEST = "surfaces_manifest_pinnable_missing_digest"
CODE_PYTHON_DIGEST_WARNING = "surfaces_manifest_python_digest_pending"
CODE_CONSISTENCY_PINNABLE_MISSING_DIGEST = "surfaces_manifest_consistency_pinnable_missing_digest"
CODE_BASE_IMAGE_ARCH_DIGEST_MISSING = "surfaces_manifest_base_image_arch_digest_missing"
CODE_DOCKERFILE_FROM_MISSING_DIGEST = "surfaces_manifest_dockerfile_from_missing_digest"
CODE_DOCKERFILE_FROM_DIGEST_MISMATCH = "surfaces_manifest_dockerfile_from_digest_mismatch"
CODE_ARG_MISMATCH = "surfaces_manifest_arg_mismatch"
CODE_RUNSC_IMAGE_MISMATCH = "surfaces_manifest_runsc_image_mismatch"
CODE_REQUIREMENTS_PIN_MISMATCH = "surfaces_manifest_requirements_pin_mismatch"
CODE_BUMP_MISSING_CARRIER = "surfaces_bump_missing_carrier"

MANIFEST = Path("surfaces/manifest.yaml")
CARRIERS_DIR = Path("carriers")
CARRIER_GLOB = "surface-bump-*.md"
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
PHASE1_PENDING_DIGEST_SURFACES = frozenset({"codex", "claude-code", *PYTHON_DEP_SURFACES})
UNSET_DIGEST = "UNSET"
UNSET_DIGEST_ALLOWLIST = frozenset(
    {
        (
            "ce-seat-image",
            "UNSET",
            "ghcr.io/creator-engine/creator-engine/ce-seat",
            "creator-engine image",
            "manifest-list digest required before tenant launch use; UNSET until published",
            "2026-07-05",
        )
    }
)
EXPLICIT_IMAGE_ALIASES_BY_SURFACE = {
    "ce-seat-image": frozenset({"ce-seat"}),
    "codex": frozenset({"codex-runsc"}),
    "gvisor/runsc": frozenset({"runsc"}),
}
ZIG_ARCHES = frozenset({"linux-aarch64", "linux-x86_64"})
DUAL_ARCH_BASE_IMAGE_ARCHES = frozenset({"amd64", "arm64"})
ARCH_ALIASES = {
    "amd64": "amd64",
    "x86_64": "amd64",
    "linux/amd64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
    "linux/arm64": "arm64",
}
SHA_RE = re.compile(r"^[0-9a-f]{8,40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SEMVER_RE = re.compile(r"(?<!\d)\d+\.\d+\.\d+(?!\d)")
FROM_RE = re.compile(r"^\s*FROM\s+(?P<body>.+?)(?:\s+#.*)?\s*$", re.IGNORECASE)
ARG_RE = re.compile(r"^\s*ARG\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:=(?P<value>\S+))?", re.IGNORECASE)
REQ_PIN_RE = re.compile(r"^\s*(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^\s;#]+)")
SHELL_DEFAULT_RE = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-|-)(?P<value>[^}]+)\}")
RUNSC_IMAGE_DEFAULTS = (
    ("deploy/vps-runsc/run-vps-runsc.sh", "CE_VPS_IMAGE", "x86_64", False),
    ("deploy/dgx-runsc/run-codex-runsc.sh", "CE_DGX_IMAGE", "aarch64", True),
)


def _surface_key(name: object) -> str:
    return re.sub(r"[\s_]+", "-", str(name).strip().lower())


def _env_key(value: object) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip().upper()).strip("_")
    if key and key[0].isdigit():
        key = f"CE_{key}"
    return key


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


def _path_is_manifest_for_root(path: Path, repo_root: Path) -> bool:
    raw = Path(path)
    if raw == MANIFEST:
        return True
    manifest = repo_root / MANIFEST
    if raw.is_absolute():
        return raw.resolve(strict=False) == manifest.resolve(strict=False)
    return (Path.cwd() / raw).resolve(strict=False) == manifest.resolve(strict=False)


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


def _surface_version(surface: dict[str, Any] | None) -> str | None:
    if surface is None:
        return None
    version = surface.get("version")
    return version if isinstance(version, str) and version else None


def _surface_commit_or_digest(surface: dict[str, Any] | None) -> object:
    if surface is None:
        return None
    return surface.get("commit_or_digest")


def _normal_sha256(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.removeprefix("sha256:")
    if SHA256_RE.fullmatch(stripped):
        return stripped
    return None


def _normal_arch(value: object) -> str | None:
    if value is None:
        return None
    return ARCH_ALIASES.get(str(value).strip().lower())


def _image_alias_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")


def _first_component_alias(value: str) -> str | None:
    first = value.split("-", 1)[0]
    if len(first) < 3:
        return None
    return first


def _surface_image_aliases(key: str) -> set[str]:
    normalized = _image_alias_key(key)
    aliases = {normalized}
    first = _first_component_alias(normalized)
    if first is not None:
        aliases.add(first)
    aliases.update(EXPLICIT_IMAGE_ALIASES_BY_SURFACE.get(key, ()))
    return {alias for alias in aliases if alias}


def _image_candidate_aliases(image: str) -> set[str]:
    aliases: set[str] = set()
    for var_name in re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", image):
        for suffix in ("_COMMIT_OR_DIGEST", "_SOURCE", "_VERSION"):
            if var_name.endswith(suffix):
                aliases.add(_image_alias_key(var_name[: -len(suffix)]))
                break

    reference = image.split("@", 1)[0]
    parts = [part for part in reference.split("/") if part]
    if not parts:
        return aliases
    parts[-1] = parts[-1].split(":", 1)[0]
    for part in parts:
        normalized = _image_alias_key(part)
        if not normalized:
            continue
        aliases.add(normalized)
        first = _first_component_alias(normalized)
        if first is not None:
            aliases.add(first)
    return aliases


def _unset_digest_allowlist_key(key: str, surface: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        key,
        str(surface.get("version", "")),
        str(surface.get("source", "")),
        str(surface.get("custody", "")),
        str(surface.get("update_policy", "")),
        str(surface.get("last_evaluated", "")),
    )


def _is_allowlisted_unset_digest(key: str, surface: dict[str, Any]) -> bool:
    return _unset_digest_allowlist_key(key, surface) in UNSET_DIGEST_ALLOWLIST


def _is_unpinned_digest(value: object) -> bool:
    return value is None or value == UNSET_DIGEST


def _is_host_only(surface: dict[str, Any]) -> bool:
    source = str(surface.get("source", "")).lower()
    custody = str(surface.get("custody", "")).lower()
    update_policy = str(surface.get("update_policy", "")).lower()
    return source.startswith("host:") or "host-only" in custody or "host inventory" in update_policy


def _is_base_image_surface(surface: dict[str, Any]) -> bool:
    source = str(surface.get("source", "")).lower()
    custody = str(surface.get("custody", "")).lower()
    return source.startswith("docker.io/") and "docker-base-image" in custody


def _pinnable_null_digest_errors(path: Path, by_name: dict[str, dict[str, Any]]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for key, surface in sorted(by_name.items()):
        commit_or_digest = surface.get("commit_or_digest")
        if (
            key in PHASE1_PENDING_DIGEST_SURFACES
            or _is_host_only(surface)
            or (not _is_unpinned_digest(commit_or_digest) and not _is_allowlisted_unset_digest(key, surface))
        ):
            continue
        if commit_or_digest == UNSET_DIGEST and _is_allowlisted_unset_digest(key, surface):
            continue
        name = surface.get("name", key)
        errors.append(
            make_error(
                CODE_CONSISTENCY_PINNABLE_MISSING_DIGEST,
                path,
                f"{name}.commit_or_digest",
                f"pinnable non-host-only surface {name!r} must carry a digest or commit",
                CONSISTENT_CONTRACT,
            )
        )
    return errors


def _iter_dockerfiles(repo_root: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in ("Dockerfile", "Dockerfile.*", "*.Dockerfile"):
        for path in repo_root.rglob(pattern):
            if not path.is_file() or ".git" in path.parts:
                continue
            resolved = path.resolve(strict=False)
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def _from_image_token(line: str) -> str | None:
    parsed = _from_image_and_platform(line)
    return parsed[0] if parsed is not None else None


def _from_image_and_platform(line: str) -> tuple[str, str | None] | None:
    match = FROM_RE.match(line)
    if not match:
        return None
    tokens = match.group("body").split()
    index = 0
    platform: str | None = None
    while index < len(tokens) and tokens[index].startswith("--"):
        if tokens[index].startswith("--platform="):
            platform = tokens[index].split("=", 1)[1]
        elif tokens[index] == "--platform" and index + 1 < len(tokens):
            platform = tokens[index + 1]
            index += 1
        index += 1
    if index >= len(tokens):
        return None
    return tokens[index], platform


def _matching_surface_for_image(image: str, by_name: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    image_aliases = _image_candidate_aliases(image)
    for key, surface in by_name.items():
        if _surface_image_aliases(key) & image_aliases:
            return key, surface
    return None


def _matches_manifest_arg_ref(image: str, surface: dict[str, Any]) -> bool:
    prefix = _env_key(surface.get("name", ""))
    if not prefix:
        return False
    return (
        f"${{{prefix}_SOURCE}}" in image
        and f"${{{prefix}_VERSION}}" in image
        and f"@sha256:${{{prefix}_COMMIT_OR_DIGEST}}" in image
    )


def _dockerfile_target_arch(path: Path, platform: str | None) -> str | None:
    explicit = _normal_arch(platform)
    if explicit is not None:
        return explicit
    normalized = path.as_posix()
    if normalized.endswith("deploy/vps-runsc/Dockerfile") or "/deploy/vps-runsc/" in normalized:
        return "amd64"
    if (
        normalized.endswith("deploy/dgx-runsc/Dockerfile")
        or normalized.endswith("deploy/dgx-controller-runsc/Dockerfile")
        or "/deploy/dgx-runsc/" in normalized
        or "/deploy/dgx-controller-runsc/" in normalized
    ):
        return "arm64"
    return None


def _surface_digest_for_arch(surface: dict[str, Any], arch: str | None) -> str | None:
    digest = _surface_commit_or_digest(surface)
    if isinstance(digest, str):
        return _normal_sha256(digest)
    if not isinstance(digest, dict) or arch is None:
        return None
    for raw_arch, payload in digest.items():
        if _normal_arch(raw_arch) != arch:
            continue
        if isinstance(payload, str):
            return _normal_sha256(payload)
        if isinstance(payload, dict):
            return _normal_sha256(payload.get("sha256"))
    return None


def _base_image_arch_digest_errors(repo_root: Path, by_name: dict[str, dict[str, Any]]) -> list[ValidationError]:
    used_arches: dict[str, set[str]] = {}
    surfaces_by_key: dict[str, dict[str, Any]] = {}
    for path in _iter_dockerfiles(repo_root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            parsed = _from_image_and_platform(line)
            if parsed is None:
                continue
            image, platform = parsed
            matched = _matching_surface_for_image(image, by_name)
            if matched is None:
                continue
            surface_key, surface = matched
            if not _is_base_image_surface(surface):
                continue
            arch = _dockerfile_target_arch(path, platform)
            if arch in DUAL_ARCH_BASE_IMAGE_ARCHES:
                used_arches.setdefault(surface_key, set()).add(arch)
                surfaces_by_key[surface_key] = surface

    errors: list[ValidationError] = []
    manifest = repo_root / MANIFEST
    for surface_key, arches in sorted(used_arches.items()):
        if not DUAL_ARCH_BASE_IMAGE_ARCHES.issubset(arches):
            continue
        surface = surfaces_by_key[surface_key]
        name = surface.get("name", surface_key)
        digest = _surface_commit_or_digest(surface)
        if not isinstance(digest, dict):
            errors.append(
                make_error(
                    CODE_BASE_IMAGE_ARCH_DIGEST_MISSING,
                    manifest,
                    f"{name}.commit_or_digest",
                    f"base image {name!r} is used by amd64 and arm64 Dockerfiles and must declare both arch digests",
                    CONSISTENT_CONTRACT,
                )
            )
            continue
        for arch in sorted(DUAL_ARCH_BASE_IMAGE_ARCHES):
            if _surface_digest_for_arch(surface, arch) is None:
                errors.append(
                    make_error(
                        CODE_BASE_IMAGE_ARCH_DIGEST_MISSING,
                        manifest,
                        f"{name}.commit_or_digest.{arch}",
                        f"base image {name!r} is used by amd64 and arm64 Dockerfiles and must declare a sha256 digest for {arch}",
                        CONSISTENT_CONTRACT,
                    )
                )
    return errors


def _dockerfile_errors(repo_root: Path, by_name: dict[str, dict[str, Any]]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for path in _iter_dockerfiles(repo_root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(
                make_error(CODE_MALFORMED, path, "", f"could not read Dockerfile: {exc}", CONSISTENT_CONTRACT)
            )
            continue
        for line_no, line in enumerate(lines, start=1):
            parsed = _from_image_and_platform(line)
            if parsed is None:
                continue
            image, platform = parsed
            if image.lower() == "scratch":
                continue
            matched = _matching_surface_for_image(image, by_name)
            if matched is None:
                continue
            surface_key, surface = matched
            if _matches_manifest_arg_ref(image, surface):
                continue
            manifest_digest = _surface_digest_for_arch(surface, _dockerfile_target_arch(path, platform))
            if manifest_digest is None:
                manifest_digest = _normal_sha256(_surface_commit_or_digest(surface))
            if manifest_digest is None:
                continue
            if "@sha256:" not in image:
                errors.append(
                    make_error(
                        CODE_DOCKERFILE_FROM_MISSING_DIGEST,
                        path,
                        f"line {line_no}",
                        f"Dockerfile FROM image {image!r} must use @sha256 digest form",
                        CONSISTENT_CONTRACT,
                    )
                )
                continue
            image_digest = image.rsplit("@sha256:", 1)[1].split(":", 1)[0]
            if image_digest != manifest_digest:
                errors.append(
                    make_error(
                        CODE_DOCKERFILE_FROM_DIGEST_MISMATCH,
                        path,
                        f"line {line_no}",
                        f"Dockerfile FROM image for {surface_key!r} must match manifest digest",
                        CONSISTENT_CONTRACT,
                    )
                )
    return errors


def _compatible_ref(actual: str, expected: str) -> bool:
    return actual == expected or actual.startswith(expected) or expected.startswith(actual)


def _arg_errors(repo_root: Path, by_name: dict[str, dict[str, Any]]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    zig_version = _surface_version(by_name.get("zig-toolchain"))
    herdr_ref = _surface_commit_or_digest(by_name.get("herdr"))
    for path in _iter_dockerfiles(repo_root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(lines, start=1):
            match = ARG_RE.match(line)
            if not match:
                continue
            name = match.group("name")
            value = (match.group("value") or "").strip("'\"")
            if name == "ZIG_VERSION" and zig_version is not None and value != zig_version:
                errors.append(
                    make_error(
                        CODE_ARG_MISMATCH,
                        path,
                        f"line {line_no}",
                        f"ZIG_VERSION default {value!r} must match manifest version {zig_version!r}",
                        CONSISTENT_CONTRACT,
                    )
                )
            if name in {"HERDR_SOURCE_REF", "HERDR_CE_REF"} and isinstance(herdr_ref, str):
                if not _compatible_ref(value, herdr_ref):
                    errors.append(
                        make_error(
                            CODE_ARG_MISMATCH,
                            path,
                            f"line {line_no}",
                            f"{name} default {value!r} must match manifest herdr ref {herdr_ref!r}",
                            CONSISTENT_CONTRACT,
                        )
                    )
    return errors


def _script_default(path: Path, variable: str) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for match in SHELL_DEFAULT_RE.finditer(text):
        if match.group("name") == variable:
            return match.group("value")
    return None


def _default_encodes_version(default: str) -> bool:
    tag = default.rsplit("/", 1)[-1].split("@", 1)[0]
    if ":" not in tag:
        return False
    return SEMVER_RE.search(tag.rsplit(":", 1)[1]) is not None


def _runsc_image_error(
    repo_root: Path,
    codex_version: str,
    script_path: str,
    variable: str,
    arch: str,
    exact: bool,
) -> ValidationError | None:
    path = repo_root / script_path
    default = _script_default(path, variable)
    if default is None or "codex" not in default.lower():
        return None

    expected = f"creator-engine/codex-runsc:{codex_version}-{arch}"
    if exact:
        matches = default == expected
    else:
        if not _default_encodes_version(default):
            return None
        matches = codex_version in default

    if matches:
        return None
    return make_error(
        CODE_RUNSC_IMAGE_MISMATCH,
        path,
        variable,
        f"{variable} default {default!r} must match expected {expected!r}",
        CONSISTENT_CONTRACT,
    )


def _runsc_image_errors(repo_root: Path, by_name: dict[str, dict[str, Any]]) -> list[ValidationError]:
    codex_version = _surface_version(by_name.get("codex"))
    if codex_version is None:
        return []
    errors: list[ValidationError] = []
    for script_path, variable, arch, exact in RUNSC_IMAGE_DEFAULTS:
        error = _runsc_image_error(repo_root, codex_version, script_path, variable, arch, exact)
        if error is not None:
            errors.append(error)
    return errors


def _requirement_pins(path: Path) -> dict[str, tuple[str, int]]:
    pins: dict[str, tuple[str, int]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return pins
    for line_no, line in enumerate(lines, start=1):
        match = REQ_PIN_RE.match(line)
        if match:
            pins[_surface_key(match.group("name"))] = (match.group("version"), line_no)
    return pins


def _requirements_errors(repo_root: Path, by_name: dict[str, dict[str, Any]]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    files = [repo_root / "validators" / "requirements.txt", repo_root / "validators" / "requirements-dev.txt"]
    pins_by_file = {path: _requirement_pins(path) for path in files}
    for surface_key in sorted(PYTHON_DEP_SURFACES):
        expected = _surface_version(by_name.get(surface_key))
        if expected is None:
            continue
        matches = [(path, pins[surface_key]) for path, pins in pins_by_file.items() if surface_key in pins]
        if not matches:
            errors.append(
                make_error(
                    CODE_REQUIREMENTS_PIN_MISMATCH,
                    repo_root / "validators",
                    surface_key,
                    f"requirements files must pin {surface_key!r} to manifest version {expected!r}",
                    CONSISTENT_CONTRACT,
                )
            )
            continue
        for path, (actual, line_no) in matches:
            if actual != expected:
                errors.append(
                    make_error(
                        CODE_REQUIREMENTS_PIN_MISMATCH,
                        path,
                        f"line {line_no}",
                        f"{surface_key!r} pin {actual!r} must match manifest version {expected!r}",
                        CONSISTENT_CONTRACT,
                    )
                )
    return errors


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


def validate_repo_consistent(repo_root: Path) -> CheckResult:
    manifest = repo_root / MANIFEST
    surfaces, errors = _load_manifest(manifest)
    if surfaces:
        errors.extend(_missing_required_fields(manifest, surfaces))
        by_name, index_errors = _index_surfaces(manifest, surfaces)
        errors.extend(index_errors)
        errors.extend(_pinnable_null_digest_errors(manifest, by_name))
        errors.extend(_base_image_arch_digest_errors(repo_root, by_name))
        errors.extend(_dockerfile_errors(repo_root, by_name))
        errors.extend(_arg_errors(repo_root, by_name))
        errors.extend(_runsc_image_errors(repo_root, by_name))
        errors.extend(_requirements_errors(repo_root, by_name))
    return CheckResult(name=CONSISTENT_CHECK_NAME, errors=tuple(errors))


def validate_repo_carrier(repo_root: Path) -> CheckResult:
    carriers = repo_root / CARRIERS_DIR
    if carriers.is_dir() and any(path.is_file() for path in carriers.glob(CARRIER_GLOB)):
        return CheckResult(name=CARRIER_CHECK_NAME)
    return CheckResult(
        name=CARRIER_CHECK_NAME,
        errors=(
            make_error(
                CODE_BUMP_MISSING_CARRIER,
                carriers,
                CARRIER_GLOB,
                "manifest bumps must include a surface-bump carrier",
                CARRIER_CONTRACT,
            ),
        ),
    )


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


@register(CONSISTENT_CHECK_NAME, [CONSISTENT_CONTRACT])
def run_consistent(paths: Iterable[Path]) -> CheckResult:
    roots = _repo_roots(paths or [Path(".")])
    if not roots:
        roots = [Path.cwd()]

    errors: list[ValidationError] = []
    for root in roots:
        result = validate_repo_consistent(root)
        errors.extend(result.errors)
    return CheckResult(name=CONSISTENT_CHECK_NAME, errors=tuple(errors))


@register(CARRIER_CHECK_NAME, [CARRIER_CONTRACT])
def run_carrier(paths: Iterable[Path]) -> CheckResult:
    input_paths = [Path(path) for path in paths]
    roots = _repo_roots(input_paths)
    if not roots:
        roots = [Path.cwd()]

    errors: list[ValidationError] = []
    for root in roots:
        if not any(_path_is_manifest_for_root(path, root) for path in input_paths):
            continue
        result = validate_repo_carrier(root)
        errors.extend(result.errors)
    return CheckResult(name=CARRIER_CHECK_NAME, errors=tuple(errors))
