"""Fleet manifest schema and CE-internal identifier guard."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ..fleet_manifest import (
    CONTRACT,
    FleetManifestValidationError,
    iter_fleet_manifest_paths,
    load_fleet_manifest,
)
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "fleet_manifest_guard"
CODE_INTERNAL_IDENTIFIER = "fleet_manifest_internal_identifier"

# Auditable denylist for CE-internal identifiers that must not appear in a
# per-project deployment manifest. Keep this list value-shaped: it should cover
# concrete repo, host, seat, infra, and endpoint identifiers, not broad product
# nouns that external deployments legitimately use.
INTERNAL_LITERAL_TOKENS = (
    "creator-engine/creator-engine",
    "creator-engine/ce-ops",
    "ce-ops#",
    "dev-1",
    "dev-2",
    "dev-3",
    "dev-4",
    "ce-dgx-codex",
    "ce-vps-codex",
    "DGX",
    "spark-b824",
    "dgx-spark",
    "Hetzner",
    "cedev2",
    "cedev4",
    "ce-kv/",
    "forge/",
    "ce-overwatch",
    "cedev1",
    "cedev3",
    "ubuntuaws745-cmyk",
)


@dataclass(frozen=True)
class InternalPattern:
    label: str
    pattern: re.Pattern[str]


INTERNAL_REGEX_PATTERNS = (
    InternalPattern("internal tailnet IP range", re.compile(r"(?<![\d.])100\.(?:\d{1,3}\.){2}\d{1,3}(?![\d.])")),
    InternalPattern("internal shared App", re.compile(r"\b(?:internal\s+shared\s+app|ce\s+shared\s+app|shared\s+ce\s+app)\b", re.IGNORECASE)),
    InternalPattern("herdr socket path", re.compile(r"(?:^|[\s:=])(?:/[^\s]*herdr[^\s]*\.sock|herdr[^\s]*\.sock)\b", re.IGNORECASE)),
    InternalPattern("internal brain endpoint", re.compile(r"\b(?:https?://)?[a-z0-9.-]*brain[a-z0-9.-]*:\d{2,5}\b", re.IGNORECASE)),
    InternalPattern("internal vLLM endpoint", re.compile(r"\b(?:https?://)?[a-z0-9.-]*vllm[a-z0-9.-]*:\d{2,5}\b", re.IGNORECASE)),
)


def _json_pointer(parts: tuple[str, ...]) -> str:
    if not parts:
        return "/"
    escaped = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped)


def _string_nodes(value: Any, parts: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            yield ((*parts, key_text), key_text)
            yield from _string_nodes(child, (*parts, key_text))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_nodes(child, (*parts, str(index)))
    elif isinstance(value, str):
        yield (parts, value)


def _internal_identifier_errors(path: Path, data: dict[str, Any]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    literal_tokens = tuple((token, token.lower()) for token in INTERNAL_LITERAL_TOKENS)
    seen: set[tuple[str, str]] = set()
    for parts, value in _string_nodes(data):
        lowered = value.lower()
        pointer = _json_pointer(parts)
        for token, lowered_token in literal_tokens:
            if lowered_token in lowered:
                key = (pointer, token)
                if key in seen:
                    continue
                seen.add(key)
                errors.append(
                    make_error(
                        CODE_INTERNAL_IDENTIFIER,
                        path,
                        pointer,
                        f"fleet manifest contains CE-internal identifier {token!r}",
                        CONTRACT,
                    )
                )
        for internal in INTERNAL_REGEX_PATTERNS:
            if internal.pattern.search(value):
                key = (pointer, internal.label)
                if key in seen:
                    continue
                seen.add(key)
                errors.append(
                    make_error(
                        CODE_INTERNAL_IDENTIFIER,
                        path,
                        pointer,
                        f"fleet manifest contains {internal.label}",
                        CONTRACT,
                    )
                )
    return errors


@register(CHECK_NAME, ["fleet-manifest-schema", CODE_INTERNAL_IDENTIFIER])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for path in iter_fleet_manifest_paths(paths):
        try:
            manifest = load_fleet_manifest(path)
        except FleetManifestValidationError as exc:
            errors.extend(exc.errors)
            continue
        errors.extend(_internal_identifier_errors(manifest.path, manifest.data))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
