"""Shared parser for the CE bootstrap ``artifact_manifest`` block."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable


class BootstrapManifestError(Exception):
    """Fail-closed bootstrap manifest parse error."""


@dataclass(frozen=True)
class BootstrapWheel:
    filename: str
    url: str
    sha256: str
    platforms: tuple[str, ...] = ("all",)


@dataclass(frozen=True)
class PythonAcquisition:
    platform: str
    tool: str
    version: str
    url: str
    sha256: str
    command: str


@dataclass(frozen=True)
class BootstrapManifest:
    artifact_manifest_version: int
    package_name: str
    package_version: str
    python_requires: str
    artifact_base_url: str
    sha256s_url: str
    sha256s_sha256: str
    install_sh_url: str
    install_sh_sha256s_entry: str
    answers_schema_url: str
    answers_schema_sha256: str
    app_wheel: str
    required_wheels: tuple[BootstrapWheel, ...]
    python_acquisitions: tuple[PythonAcquisition, ...]

    def wheel_by_filename(self) -> dict[str, BootstrapWheel]:
        return {wheel.filename: wheel for wheel in self.required_wheels}

    @property
    def python_acquisition(self) -> PythonAcquisition:
        return self.python_acquisition_for_platform("linux-x86_64-cp314")

    def python_acquisition_for_platform(self, platform: str) -> PythonAcquisition:
        for acquisition in self.python_acquisitions:
            if acquisition.platform == platform:
                return acquisition
        raise BootstrapManifestError(
            f"bad_bootstrap_manifest: python_acquisition missing for {platform}"
        )

    def wheels_for_platform(self, platform: str) -> tuple[BootstrapWheel, ...]:
        selected = tuple(
            wheel
            for wheel in self.required_wheels
            if "all" in wheel.platforms or platform in wheel.platforms
        )
        if self.app_wheel not in {wheel.filename for wheel in selected}:
            raise BootstrapManifestError(
                f"bad_bootstrap_manifest: app_wheel is not listed for {platform}"
            )
        return selected


def _strip_inline_comment(value: str) -> str:
    return value.split(" #", 1)[0].strip()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _parse_platforms(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ("all",)
    normalized = _strip_inline_comment(value).strip()
    if normalized in {"", "*", "all"}:
        return ("all",)
    platforms = tuple(part for part in re.split(r"[,\s]+", normalized) if part)
    return platforms or ("all",)


def parse_bootstrap_manifest(
    spec_bytes: bytes | str,
    *,
    error_cls: Callable[[str], Exception] = BootstrapManifestError,
) -> BootstrapManifest:
    """Parse the line-oriented ``artifact_manifest:`` block from llms-install.md."""
    text = spec_bytes.decode("utf-8") if isinstance(spec_bytes, bytes) else spec_bytes
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "artifact_manifest:")
    except StopIteration as exc:
        raise error_cls("missing_bootstrap_manifest: artifact_manifest block missing") from exc

    scalars: dict[str, str] = {}
    wheels: list[dict[str, str]] = []
    python_acquisitions: list[dict[str, str]] = []
    legacy_python_acquisition: dict[str, str] = {}
    section: str | None = None
    current_wheel: dict[str, str] | None = None
    current_python_acquisition: dict[str, str] | None = None

    for raw_line in lines[start + 1:]:
        if raw_line and not raw_line.startswith("  "):
            break
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line == "  required_wheels:":
            section = "required_wheels"
            continue
        if line == "  python_acquisition:":
            if current_wheel is not None:
                wheels.append(current_wheel)
                current_wheel = None
            section = "python_acquisition"
            continue
        if section == "required_wheels":
            if line.startswith("    - filename: "):
                if current_wheel is not None:
                    wheels.append(current_wheel)
                current_wheel = {"filename": _strip_inline_comment(line.split(": ", 1)[1])}
                continue
            if line.startswith("      ") and current_wheel is not None:
                key, sep, value = line.strip().partition(":")
                if sep:
                    current_wheel[key] = _strip_inline_comment(value)
                continue
        if section == "python_acquisition":
            if line.startswith("    - platform: "):
                if current_python_acquisition is not None:
                    python_acquisitions.append(current_python_acquisition)
                current_python_acquisition = {
                    "platform": _strip_inline_comment(line.split(": ", 1)[1])
                }
                continue
            if line.startswith("      ") and current_python_acquisition is not None:
                key, sep, value = line.strip().partition(":")
                if sep:
                    current_python_acquisition[key] = _strip_inline_comment(value)
                continue
            if line.startswith("    ") and current_python_acquisition is None:
                key, sep, value = line.strip().partition(":")
                if sep:
                    legacy_python_acquisition[key] = _strip_inline_comment(value)
                continue
            continue
        if line.startswith("  "):
            key, sep, value = line.strip().partition(":")
            if sep:
                scalars[key] = _strip_inline_comment(value)
    if current_wheel is not None:
        wheels.append(current_wheel)
    if current_python_acquisition is not None:
        python_acquisitions.append(current_python_acquisition)

    required_scalars = {
        "artifact_manifest_version",
        "package_name",
        "package_version",
        "python_requires",
        "artifact_base_url",
        "sha256s_url",
        "sha256s_sha256",
        "install_sh_url",
        "install_sh_sha256s_entry",
        "answers_schema_url",
        "answers_schema_sha256",
        "app_wheel",
    }
    missing = sorted(required_scalars - scalars.keys())
    if missing:
        raise error_cls("bad_bootstrap_manifest: missing " + ", ".join(missing))
    try:
        version = int(scalars["artifact_manifest_version"])
    except ValueError as exc:
        raise error_cls("bad_bootstrap_manifest: artifact_manifest_version must be an integer") from exc
    if version != 1:
        raise error_cls(f"bad_bootstrap_manifest: unsupported version {version}")
    for key in ("sha256s_sha256", "answers_schema_sha256"):
        if not _valid_sha256(scalars[key]):
            raise error_cls(f"bad_bootstrap_manifest: {key} is not a 64-hex digest")

    parsed_wheels: list[BootstrapWheel] = []
    for wheel in wheels:
        wheel_missing = sorted({"filename", "url", "sha256"} - wheel.keys())
        if wheel_missing:
            raise error_cls("bad_bootstrap_manifest: wheel entry missing " + ", ".join(wheel_missing))
        if not _valid_sha256(wheel["sha256"]):
            raise error_cls(f"bad_bootstrap_manifest: wheel {wheel['filename']} sha256 is not 64-hex")
        parsed_wheels.append(
            BootstrapWheel(wheel["filename"], wheel["url"], wheel["sha256"], _parse_platforms(wheel.get("platforms")))
        )
    if not parsed_wheels:
        raise error_cls("bad_bootstrap_manifest: required_wheels is empty")
    if scalars["app_wheel"] not in {wheel.filename for wheel in parsed_wheels}:
        raise error_cls("bad_bootstrap_manifest: app_wheel is not in required_wheels")

    required_python = {"tool", "version", "url", "sha256", "command"}
    if legacy_python_acquisition and not python_acquisitions:
        legacy_python_acquisition.setdefault("platform", "linux-x86_64-cp314")
        python_acquisitions.append(legacy_python_acquisition)
    parsed_python_acquisitions: list[PythonAcquisition] = []
    for acquisition in python_acquisitions:
        missing_python = sorted((required_python | {"platform"}) - acquisition.keys())
        if missing_python:
            raise error_cls("bad_bootstrap_manifest: python_acquisition missing " + ", ".join(missing_python))
        if not _valid_sha256(acquisition["sha256"]):
            raise error_cls("bad_bootstrap_manifest: python_acquisition sha256 is not 64-hex")
        parsed_python_acquisitions.append(
            PythonAcquisition(
                platform=acquisition["platform"],
                tool=acquisition["tool"],
                version=acquisition["version"],
                url=acquisition["url"],
                sha256=acquisition["sha256"],
                command=acquisition["command"],
            )
        )
    if not parsed_python_acquisitions:
        raise error_cls("bad_bootstrap_manifest: python_acquisition is empty")
    return BootstrapManifest(
        artifact_manifest_version=version,
        package_name=scalars["package_name"],
        package_version=scalars["package_version"],
        python_requires=scalars["python_requires"],
        artifact_base_url=scalars["artifact_base_url"],
        sha256s_url=scalars["sha256s_url"],
        sha256s_sha256=scalars["sha256s_sha256"],
        install_sh_url=scalars["install_sh_url"],
        install_sh_sha256s_entry=scalars["install_sh_sha256s_entry"],
        answers_schema_url=scalars["answers_schema_url"],
        answers_schema_sha256=scalars["answers_schema_sha256"],
        app_wheel=scalars["app_wheel"],
        required_wheels=tuple(parsed_wheels),
        python_acquisitions=tuple(parsed_python_acquisitions),
    )


def parse_sha256s(text: str) -> dict[str, str]:
    """Parse a SHA256SUMS file into ``{filename: digest}``."""
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        digest, filename = fields[0], fields[-1].lstrip("*")
        if _valid_sha256(digest):
            parsed[filename] = digest
    return parsed
