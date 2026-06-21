"""Brownfield baseline attestation schema and content-digest validation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .connector_substrate import _contains_secret

CHECK_NAME = "brownfield_baseline_attestation"
CONTRACT = "schemas/brownfield-baseline-attestation.schema.yaml"
SCHEMA = "schemas/brownfield-baseline-attestation.schema.yaml"
KIND_VALUE = "brownfield-baseline-attestation"

CODE_SCHEMA = "VAL-BROWNFIELD-BASELINE-ATTESTATION-SCHEMA"
CODE_INVALID = "VAL-BROWNFIELD-BASELINE-ATTESTATION-INVALID"
CODE_CONTENT_DIGEST = "VAL-BROWNFIELD-BASELINE-ATTESTATION-DIGEST"
CODE_SECRET = "VAL-BROWNFIELD-BASELINE-ATTESTATION-SECRET"
CODE_VALUE_FREE = "VAL-BROWNFIELD-BASELINE-ATTESTATION-VALUE-FREE"

_ATTESTOR_REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}:[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _is_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".yml", ".yaml"}


def _is_excluded(path: Path) -> bool:
    return (
        ".tmp." in path.name
        or "schemas" in path.parts
        or "templates" in path.parts
        or "wheelhouse" in path.parts
        or "__pycache__" in path.parts
    )


def _record_is_attestation(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_brownfield_baseline_attestations(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _is_yaml(path) and not _is_excluded(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                candidate
                for candidate in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _is_yaml(candidate) and not _is_excluded(candidate)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if not _record_is_attestation(data):
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _canonical_content_digest(record: dict[str, Any]) -> str:
    material = {key: value for key, value in record.items() if key != "content_digest"}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _attestor_ref_is_value_free(value: Any) -> bool:
    return isinstance(value, str) and bool(_ATTESTOR_REF_RE.fullmatch(value))


def validate_brownfield_baseline_attestation(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors = list(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    if not _attestor_ref_is_value_free(record.get("attestor_ref")):
        errors.append(
            make_error(
                CODE_VALUE_FREE,
                path,
                "/attestor_ref",
                "attestor_ref must be a value-free actor label pair like 'operator:peer-operator'; "
                "URLs, hostnames, filesystem paths, repository paths, and client-specific locators are refused",
                CONTRACT,
            )
        )
    if _contains_secret(record):
        errors.append(
            make_error(
                CODE_SECRET,
                path,
                "/",
                "brownfield baseline attestation records must not carry secret or credential values",
                CONTRACT,
            )
        )
    if errors:
        return errors
    if record.get("content_digest") != _canonical_content_digest(record):
        errors.append(
            make_error(
                CODE_CONTENT_DIGEST,
                path,
                "/content_digest",
                "content_digest must equal SHA256 of canonical record material excluding content_digest",
                CONTRACT,
            )
        )
    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_INVALID, CODE_CONTENT_DIGEST, CODE_SECRET, CODE_VALUE_FREE])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_brownfield_baseline_attestations(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "/", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(
                make_error(
                    CODE_INVALID,
                    record_path,
                    "/",
                    "brownfield baseline attestation must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_brownfield_baseline_attestation(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
