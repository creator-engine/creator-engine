"""Controller-key record schema validation (PCO Slice 2.5A).

Validates controller-key records against ``schemas/controller-key.schema.yaml``.

Slice 2.5A scope is substrate-only:

* this check validates one controller-key record at a time;
* it records the public-key metadata shape needed by later PCO-024 lease
  signature verification;
* it MUST NOT generate keys, inspect private keys, verify lease signatures,
  allocate worktrees, launch panes, or interact with container runtimes.

Candidate discovery mirrors the existing PCO record validators: YAML files outside
``schemas/`` and ``templates/`` whose loaded mapping has
``kind: controller-key-record`` are scanned, while atomic ``*.tmp.*`` artifacts
are skipped.
"""

from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "controller_key_schema"
CONTRACT = "docs/operations/CONTROLLER_IDENTITY_PROTOCOL.md"
SCHEMA = "schemas/controller-key.schema.yaml"
KIND_VALUE = "controller-key-record"
CODE_SCHEMA = "PCO-025"
CODE_INVALID = "controller_key_invalid_record"

_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_FORBIDDEN_SECRET_FIELDS = {
    "private_key",
    "secret_value",
    "token",
    "credential",
    "pem_private_key",
    "host_gh_token",
}


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_controller_key(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_controller_key_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate controller-key files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
                and not _is_under_excluded(p)
                and not _is_tmp_artifact(p)
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
            if not _record_is_controller_key(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _pointer(parts: Iterable[str]) -> str:
    rendered = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _secret_field_errors(value: Any, path: Path, parts: tuple[str, ...] = ()) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_parts = (*parts, key_text)
            if key_text in _FORBIDDEN_SECRET_FIELDS:
                errors.append(
                    make_error(
                        CODE_SCHEMA,
                        path,
                        _pointer(child_parts),
                        "controller-key records must not contain private/secret material",
                        CONTRACT,
                    )
                )
            errors.extend(_secret_field_errors(child, path, child_parts))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_secret_field_errors(child, path, (*parts, str(index))))
    return errors


def _public_key_decode_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    public_key = record.get("public_key")
    if not isinstance(public_key, dict):
        return []
    value = public_key.get("value")
    if not isinstance(value, str):
        return []
    if "=" in value or not _BASE64URL_RE.fullmatch(value):
        return [
            make_error(
                CODE_SCHEMA,
                path,
                "/public_key/value",
                "public_key.value must be unpadded base64url",
                CONTRACT,
            )
        ]
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except (binascii.Error, ValueError):
        return [
            make_error(
                CODE_SCHEMA,
                path,
                "/public_key/value",
                "public_key.value must decode as unpadded base64url",
                CONTRACT,
            )
        ]
    if len(decoded) != 32:
        return [
            make_error(
                CODE_SCHEMA,
                path,
                "/public_key/value",
                "ed25519 public_key.value must decode to exactly 32 bytes",
                CONTRACT,
            )
        ]
    return []


def _revoked_status_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    if record.get("status") == "revoked" and "revoked_at" not in record:
        return [
            make_error(
                CODE_SCHEMA,
                path,
                "/revoked_at",
                "revoked controller-key records must include revoked_at",
                CONTRACT,
            )
        ]
    return []


def validate_controller_key_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one controller-key record against PCO-025."""
    errors = list(
        validate_with_schema(
            record,
            SCHEMA,
            path,
            code=CODE_SCHEMA,
            contract=CONTRACT,
        )
    )
    errors.extend(_secret_field_errors(record, path))
    errors.extend(_public_key_decode_errors(record, path))
    errors.extend(_revoked_status_errors(record, path))
    return errors


@register(CHECK_NAME, [CODE_SCHEMA])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_controller_key_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(
                make_error(
                    CODE_INVALID,
                    record_path,
                    "/",
                    "controller-key record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_controller_key_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
