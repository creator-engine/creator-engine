"""Controller Runtime Contract validation (RV1-020, PCO v1 Gate 2).

Validates Controller Runtime Contract records against
``schemas/controller-runtime-contract.schema.yaml`` plus the authority-boundary
and redaction-safe predicates that the schema alone cannot express.

Gate 2 scope is substrate/validator-only. This check:

* validates one declarative record at a time;
* classifies the Controller seat (host-local) and the harness authority
  boundary (Hermes/Claude Code/Codex ``IN``; OpenClaw ``SEAM``; hosted
  service/SaaS/GitHub connector not authorized for v1.0 kernel authority);
* refuses any secret or provider-authority value in any field;
* MUST NOT launch a pane, call Claude, call GitHub, call network APIs, or
  mutate runtime state.

Candidate discovery mirrors the existing PCO record validators: YAML files
outside ``schemas/`` and ``templates/`` whose loaded mapping has
``kind: controller-runtime-contract`` are scanned, while atomic ``*.tmp.*``
artifacts are skipped.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "controller_runtime_contract"
CONTRACT = "docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md"
SCHEMA = "schemas/controller-runtime-contract.schema.yaml"
KIND_VALUE = "controller-runtime-contract"

CODE_SCHEMA = "RV1-020"
CODE_AUTHORITY = "RV1-020-AUTH"
CODE_SECRET = "RV1-020-SECRET"
CODE_INVALID = "controller_runtime_contract_invalid_record"

# Harnesses that operate inside the host-local Controller seat for the v1.0 kernel.
IN_SEAT_HARNESSES = frozenset({"hermes", "claude-code", "codex"})
# OpenClaw remains a seam, not an in-seat harness.
SEAM_HARNESSES = frozenset({"openclaw"})
# Hosted authorities never hold v1.0 kernel authority.
UNAUTHORIZED_AUTHORITIES = frozenset({"hosted-service", "saas", "github-connector"})

# Exact key names that must never appear; substring matching is avoided so that
# structural keys such as ``state_boundary`` are not false-positives.
SECRET_KEY_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "account_name",
        "browser_session_cookie",
        "credential",
        "host_gh_token",
        "installation_id",
        "model_api_key",
        "oauth_token",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "secret_value",
        "session_cookie",
        "token",
    }
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
)


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_contract(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_controller_runtime_contract_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Controller Runtime Contract files under ``paths``."""
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
            if not _record_is_contract(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _pointer(parts: Iterable[str]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _secret_errors(value: Any, path: Path, parts: tuple[str, ...] = ()) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_parts = (*parts, key_text)
            if key_text.lower() in SECRET_KEY_NAMES:
                errors.append(
                    make_error(
                        CODE_SECRET,
                        path,
                        _pointer(child_parts),
                        "Controller Runtime Contracts must not carry secret or provider-authority fields",
                        CONTRACT,
                    )
                )
            errors.extend(_secret_errors(child, path, child_parts))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_secret_errors(child, path, (*parts, str(index))))
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                errors.append(
                    make_error(
                        CODE_SECRET,
                        path,
                        _pointer(parts),
                        "Controller Runtime Contracts must not store secret-shaped values",
                        CONTRACT,
                    )
                )
                break
    return errors


def _authority_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    boundary = record.get("authority_boundary")
    if not isinstance(boundary, dict):
        return []
    in_seat = boundary.get("in_seat_harnesses")
    seam = boundary.get("seam_harnesses")
    unauth = boundary.get("unauthorized_authorities")
    if not all(isinstance(v, list) for v in (in_seat, seam, unauth)):
        return []

    in_set = {x for x in in_seat if isinstance(x, str)}
    seam_set = {x for x in seam if isinstance(x, str)}
    unauth_set = {x for x in unauth if isinstance(x, str)}

    errors: list[ValidationError] = []

    if in_set != set(IN_SEAT_HARNESSES):
        missing = sorted(set(IN_SEAT_HARNESSES) - in_set)
        extra = sorted(in_set - set(IN_SEAT_HARNESSES))
        errors.append(
            make_error(
                CODE_AUTHORITY,
                path,
                "/authority_boundary/in_seat_harnesses",
                "in_seat_harnesses must be exactly {hermes, claude-code, codex}"
                + (f"; missing: {missing}" if missing else "")
                + (f"; unexpected: {extra}" if extra else ""),
                CONTRACT,
            )
        )
    if not SEAM_HARNESSES <= seam_set:
        errors.append(
            make_error(
                CODE_AUTHORITY,
                path,
                "/authority_boundary/seam_harnesses",
                "OpenClaw must be classified as a SEAM harness",
                CONTRACT,
            )
        )
    if SEAM_HARNESSES & in_set:
        errors.append(
            make_error(
                CODE_AUTHORITY,
                path,
                "/authority_boundary/in_seat_harnesses",
                "OpenClaw is a SEAM harness and must not be classified as in-seat",
                CONTRACT,
            )
        )
    if not UNAUTHORIZED_AUTHORITIES <= unauth_set:
        missing = sorted(set(UNAUTHORIZED_AUTHORITIES) - unauth_set)
        errors.append(
            make_error(
                CODE_AUTHORITY,
                path,
                "/authority_boundary/unauthorized_authorities",
                f"hosted service/SaaS/GitHub connector must be unauthorized; missing: {missing}",
                CONTRACT,
            )
        )
    leaked = sorted(UNAUTHORIZED_AUTHORITIES & in_set)
    if leaked:
        errors.append(
            make_error(
                CODE_AUTHORITY,
                path,
                "/authority_boundary/in_seat_harnesses",
                f"hosted/SaaS/GitHub-connector authority is never an in-seat Controller harness: {leaked}",
                CONTRACT,
            )
        )
    return errors


def validate_controller_runtime_contract_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one Controller Runtime Contract record against RV1-020."""
    errors = list(
        validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    )
    errors.extend(_secret_errors(record, path))
    errors.extend(_authority_errors(record, path))
    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_AUTHORITY, CODE_SECRET])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_controller_runtime_contract_records(paths):
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
                    "controller-runtime-contract record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_controller_runtime_contract_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
