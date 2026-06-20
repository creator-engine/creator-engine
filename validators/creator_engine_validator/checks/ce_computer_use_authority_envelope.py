"""ce-ops#142 Phase 1 computer-use UI side-effect authority envelope validator.

This is the schema-plus-semantic envelope for browser-mediated UI side effects.
It deliberately stops short of live Ring-2 hook honoring: Phase 1 validates that
one record authorizes one closed mechanic/target pair, carries a DoR-complete
ratified prompt binding, and contains no token/2FA/credential material.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .connector_substrate import (
    EMITTING_ROLES,
    FORBIDDEN_ACTIVE_ROLES,
    OPERATING_MODES,
    _normalize_token,
    _pointer,
)

CHECK_NAME = "ce_computer_use_authority_envelope"
CONTRACT = "docs/contracts/computer-use-authority-envelope.md"
SCHEMA_PATH = "schemas/computer-use-authority-envelope.schema.yaml"
KEY = "computer_use_authority_envelope"
SCOPE_TOKEN = "computer-use-authority-envelope"
CONTRACT_DOCS = frozenset({"computer-use-authority-envelope.md", "computer-use-worker-harness.md"})

CODE_SCHEMA = "VAL-CUA-SCHEMA"
CODE_MECHANIC_TARGET = "VAL-CUA-MECHANIC-TARGET"
CODE_TARGET = "VAL-CUA-TARGET"
CODE_RATIFICATION = "VAL-CUA-RATIFICATION"
CODE_DOR = "VAL-CUA-DOR-INCOMPLETE"
CODE_ROLE = "VAL-CUA-ROLE"
CODE_MODE = "VAL-CUA-MODE"
CODE_SECRET = "VAL-CUA-SECRET"
CODE_NO_INLINE = "VAL-CUA-NO-INLINE"

MECHANIC_TO_TARGET = {
    "account_rename": "account",
    "app_rename": "app",
    "console_setting": "console_setting",
}
TARGET_TYPES = frozenset(MECHANIC_TO_TARGET.values())
TARGET_REQUIRED_FIELDS = {
    "account": ("current_login", "desired_login"),
    "app": ("app_slug", "desired_app_name"),
    "console_setting": ("console_surface", "setting_key", "desired_state_ref"),
}
MUTATION_CLASSES = frozenset({"docs", "code", "schema", "deploy", "governance", "identity", "security", "attestation", "redaction", "none"})
HUMAN_RATIFIER_ROLES = frozenset({"operator", "source", "ratifier"})

FORBIDDEN_UI_SECRET_KEYS = frozenset(
    {
        "2fa",
        "api_key",
        "apikey",
        "client_secret",
        "mfa",
        "otp",
        "password",
        "private_key",
        "recovery_code",
        "recovery_codes",
        "secret",
        "token",
        "totp",
        "two_factor_code",
        "verification_code",
    }
)
_UI_SECRET_TEXT_RE = re.compile(r"(?i)\b(2fa|two[- ]factor|mfa|otp|totp|recovery[- ]code|password|token)\b")
_TOKEN_VALUE_RE = re.compile(r"(gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_YAML_SUFFIXES = {".yml", ".yaml"}
_MD_SUFFIXES = {".md", ".markdown"}


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _path_in_scope(path: Path) -> bool:
    if SCOPE_TOKEN in path.parts:
        return True
    return path.name in CONTRACT_DOCS


def _iter_scanned_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    suffixes = _YAML_SUFFIXES | _MD_SUFFIXES
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        else:
            candidates = []
        for candidate in candidates:
            if _is_tmp_artifact(candidate) or candidate.suffix.lower() not in suffixes or not _path_in_scope(candidate):
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _validate_markdown(path: Path) -> list[ValidationError]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [make_error(CODE_NO_INLINE, path, "", f"failed to read markdown: {exc}", CONTRACT)]
    errors: list[ValidationError] = []
    in_fence = False
    fence_is_yaml = False
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if line_no == 1 and stripped == "---":
            in_fence = True
            fence_is_yaml = True
            continue
        if in_fence and fence_is_yaml and stripped in {"---", "..."}:
            in_fence = False
            fence_is_yaml = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not in_fence:
                in_fence = True
                fence_is_yaml = stripped[3:].strip().lower() in {"yaml", "yml"}
            else:
                in_fence = False
                fence_is_yaml = False
            continue
        if not fence_is_yaml:
            continue
        if stripped.split(":", 1)[0].strip() == KEY:
            errors.append(make_error(CODE_NO_INLINE, path, _pointer(("line", line_no)), "computer-use authority envelopes belong in sidecars/examples, not Markdown bodies", CONTRACT))
    return errors


def _scalar_text(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    return str(value)


def _contains_nonempty_scalar(value: Any) -> bool:
    text = _scalar_text(value)
    if text is not None:
        return bool(text.strip())
    if isinstance(value, dict):
        return any(_contains_nonempty_scalar(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_nonempty_scalar(child) for child in value)
    return False


def _contains_forbidden_ui_secret(value: Any) -> bool:
    text = _scalar_text(value)
    if text is not None:
        return bool(_TOKEN_VALUE_RE.search(text) or _UI_SECRET_TEXT_RE.search(text))
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalize_token(key) in FORBIDDEN_UI_SECRET_KEYS and _contains_nonempty_scalar(child):
                return True
            if _contains_forbidden_ui_secret(child):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden_ui_secret(child) for child in value)
    return False


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_nonempty_string(item) for item in value)


def validate_computer_use_authority_envelope_file(path: Path) -> list[ValidationError]:
    path = Path(path)
    if path.suffix.lower() in _MD_SUFFIXES:
        return _validate_markdown(path)
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(CODE_SCHEMA, path, "", str(exc), SCHEMA_PATH)]
    return validate_computer_use_authority_envelope_record(data, path)


def validate_computer_use_authority_envelope_record(data: Any, path: Path | str) -> list[ValidationError]:
    """Validate a loaded ``{computer_use_authority_envelope: {...}}`` mapping."""
    path = Path(path)
    errors: list[ValidationError] = []
    try:
        errors.extend(validate_with_schema(data, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=SCHEMA_PATH))
    except Exception as exc:  # pragma: no cover - environment guard
        errors.append(make_error(CODE_SCHEMA, path, "", f"schema validation failed: {exc}", SCHEMA_PATH))
    if not isinstance(data, dict) or KEY not in data or not isinstance(data[KEY], dict):
        if not errors:
            errors.append(make_error(CODE_SCHEMA, path, "", "scoped YAML files must declare a computer_use_authority_envelope mapping", SCHEMA_PATH))
        return errors

    rec = data[KEY]
    pre = (KEY,)

    mechanic = _normalize_token(rec.get("mechanic", ""))
    target = rec.get("target")
    target_type = _normalize_token(target.get("target_type", "")) if isinstance(target, dict) else ""

    if target_type not in TARGET_TYPES:
        errors.append(make_error(CODE_TARGET, path, _pointer(pre + ("target", "target_type")), "target_type must be one of account, app, console_setting", CONTRACT))

    expected_target = MECHANIC_TO_TARGET.get(mechanic)
    if expected_target is None:
        errors.append(make_error(CODE_MECHANIC_TARGET, path, _pointer(pre + ("mechanic",)), "mechanic must be one of account_rename, app_rename, console_setting", CONTRACT))
    elif target_type in TARGET_TYPES and target_type != expected_target:
        errors.append(make_error(CODE_MECHANIC_TARGET, path, _pointer(pre + ("target", "target_type")), f"mechanic {mechanic!r} requires target_type {expected_target!r}, not {target_type!r}", CONTRACT))

    if not _SHA256_RE.fullmatch(str(rec.get("ratified_prompt_sha", ""))):
        errors.append(make_error(CODE_RATIFICATION, path, _pointer(pre + ("ratified_prompt_sha",)), "ratified_prompt_sha must bind the grant to a lowercase 64-hex ratified prompt digest", CONTRACT))

    ratifier_role = _normalize_token(rec.get("ratifier_role", ""))
    if ratifier_role not in HUMAN_RATIFIER_ROLES:
        errors.append(make_error(CODE_RATIFICATION, path, _pointer(pre + ("ratifier_role",)), "ratifier_role must be a human-in-loop role: operator, source, or ratifier", CONTRACT))

    if _normalize_token(rec.get("mutation_class", "")) not in MUTATION_CLASSES:
        errors.append(make_error(CODE_DOR, path, _pointer(pre + ("mutation_class",)), "mutation_class must reuse the scope.schema.yaml taxonomy", CONTRACT))
    if not _nonempty_string_list(rec.get("acceptance_criteria")):
        errors.append(make_error(CODE_DOR, path, _pointer(pre + ("acceptance_criteria",)), "acceptance_criteria must be a non-empty list of testable criteria", CONTRACT))
    if isinstance(target, dict) and target_type in TARGET_REQUIRED_FIELDS:
        for field in TARGET_REQUIRED_FIELDS[target_type]:
            if not _nonempty_string(target.get(field)):
                errors.append(make_error(CODE_DOR, path, _pointer(pre + ("target", field)), f"target.{field} is required for target_type {target_type!r}", CONTRACT))
    elif not isinstance(target, dict):
        errors.append(make_error(CODE_DOR, path, _pointer(pre + ("target",)), "target must be a closed target mapping", CONTRACT))

    role = _normalize_token(rec.get("emitting_role", ""))
    if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
        errors.append(make_error(CODE_ROLE, path, _pointer(pre + ("emitting_role",)), "emitting_role must be a canonical non-ratifying role; source and agent_ratifier may not emit", CONTRACT))
    if _normalize_token(rec.get("operating_mode", "")) not in OPERATING_MODES:
        errors.append(make_error(CODE_MODE, path, _pointer(pre + ("operating_mode",)), "operating_mode must be one of strict, auto, transcendence", CONTRACT))

    if _contains_forbidden_ui_secret(rec):
        errors.append(make_error(CODE_SECRET, path, _pointer(pre), "computer_use_authority_envelope must not carry token, credential, 2FA/MFA/OTP, or recovery-code material", CONTRACT))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_MECHANIC_TARGET, CODE_TARGET, CODE_RATIFICATION, CODE_DOR, CODE_ROLE, CODE_MODE, CODE_SECRET, CODE_NO_INLINE],
)
def run_computer_use_authority_envelope(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in _iter_scanned_files(paths):
        errors.extend(validate_computer_use_authority_envelope_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))


def run(paths: Iterable[Path]) -> CheckResult:
    return run_computer_use_authority_envelope(paths)
