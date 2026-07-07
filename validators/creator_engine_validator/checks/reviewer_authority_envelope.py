"""G2.007.2 reviewer-venue side-effect-authority envelope validator.

A bounded, auditable authority record that lets a distinct CE-governed reviewer venue
legitimately perform exactly one restricted mechanic (``pr_review``) on exactly one PR.
It is resolved + honored by the Ring-2 hook (``hook_check``): a restricted mechanic is
allowed only when a valid envelope's ``mechanic`` equals the classified action AND the
command's target PR equals ``pr_number``; ``head_sha``/``actor``/``ratified_prompt_sha``
bind the grant for audit. Shape-only: no runtime, no secret values (``actor`` is a login
name, never a token).

Prose contract: ``docs/operations/REVIEWER_VENUE_AUTHORITY.md``.
"""
from __future__ import annotations

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
    _contains_secret,
    _normalize_token,
    _pointer,
)

CHECK_NAME = "reviewer_authority_envelope"
CONTRACT = "specs/v2/007-harness-seat-contract/spec.ce.yml#reviewer_authority_envelope"
SCHEMA_PATH = "schemas/reviewer-authority-envelope.schema.yaml"
KEY = "reviewer_authority_envelope"
SCOPE_TOKEN = "reviewer-authority-envelope"
PROTOCOL_DOC = "REVIEWER_VENUE_AUTHORITY.md"
SPEC_FEATURE_DIR = "007-harness-seat-contract"

CODE_SCHEMA = "VAL-RVA-SCHEMA"
CODE_MECHANIC = "VAL-RVA-MECHANIC"
CODE_BINDING = "VAL-RVA-BINDING"
CODE_ROLE = "VAL-RVA-ROLE"
CODE_MODE = "VAL-RVA-MODE"
CODE_SECRET = "VAL-RVA-SECRET"
CODE_NO_INLINE = "VAL-RVA-NO-INLINE"
CODE_CAPABILITY = "VAL-RVA-CAPABILITY"
CODE_SELF_REVIEW = "VAL-RVA-SELF-REVIEW"

MECHANICS = frozenset({"pr_review"})
CAPABILITIES = frozenset({"independent_review_venue"})
REQUIRED_BINDINGS = ("pr_number", "head_sha", "actor", "ratified_prompt_sha")

_YAML_SUFFIXES = {".yml", ".yaml"}
_MD_SUFFIXES = {".md", ".markdown"}


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _path_in_scope(path: Path) -> bool:
    parts = path.parts
    if SCOPE_TOKEN in parts:
        return True
    if path.name == PROTOCOL_DOC:
        return True
    for i in range(len(parts) - 2):
        if parts[i] == "specs" and parts[i + 1] == "v2" and parts[i + 2] == SPEC_FEATURE_DIR:
            return path.name == "spec.md"
    return False


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
            errors.append(make_error(CODE_NO_INLINE, path, _pointer(("line", line_no)), "reviewer-authority-envelope metadata belongs in sidecars/examples, not Markdown bodies", CONTRACT))
    return errors


def validate_reviewer_authority_envelope_file(path: Path) -> list[ValidationError]:
    path = Path(path)
    if path.suffix.lower() in _MD_SUFFIXES:
        return _validate_markdown(path)
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(CODE_SCHEMA, path, "", str(exc), SCHEMA_PATH)]
    return validate_reviewer_authority_envelope_record(data, path)


def validate_reviewer_authority_envelope_record(data: Any, path: Path | str) -> list[ValidationError]:
    """Validate a loaded ``{reviewer_authority_envelope: {...}}`` mapping (file or in-memory)."""
    path = Path(path)
    errors: list[ValidationError] = []
    try:
        errors.extend(validate_with_schema(data, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=SCHEMA_PATH))
    except Exception as exc:  # pragma: no cover - environment guard
        errors.append(make_error(CODE_SCHEMA, path, "", f"schema validation failed: {exc}", SCHEMA_PATH))
    if not isinstance(data, dict) or KEY not in data or not isinstance(data[KEY], dict):
        if not errors:
            errors.append(make_error(CODE_SCHEMA, path, "", "scoped YAML files must declare a reviewer_authority_envelope mapping", SCHEMA_PATH))
        return errors
    rec = data[KEY]
    pre = (KEY,)

    if _normalize_token(rec.get("mechanic", "")) not in MECHANICS:
        errors.append(make_error(CODE_MECHANIC, path, _pointer(pre + ("mechanic",)), "mechanic must be 'pr_review' (the only reviewer-venue mechanic this envelope authorizes)", CONTRACT))
    capability = rec.get("capability")
    if capability is not None and _normalize_token(capability) not in CAPABILITIES:
        errors.append(make_error(CODE_CAPABILITY, path, _pointer(pre + ("capability",)), "capability must be independent_review_venue when present", CONTRACT))
    for field in REQUIRED_BINDINGS:
        val = rec.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(make_error(CODE_BINDING, path, _pointer(pre + (field,)), f"{field} is a required authority binding (pr_number/head_sha/actor/ratified_prompt_sha)", CONTRACT))
    actor = str(rec.get("actor") or "").strip().lower()
    author = str(rec.get("target_pr_author") or "").strip().lower()
    if actor and author and actor == author:
        errors.append(make_error(CODE_SELF_REVIEW, path, _pointer(pre + ("target_pr_author",)), "target_pr_author must differ from actor (author≠reviewer invariant)", CONTRACT))

    role = _normalize_token(rec.get("emitting_role", ""))
    if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
        errors.append(make_error(CODE_ROLE, path, _pointer(pre + ("emitting_role",)), "emitting_role must be a canonical non-ratifying role; agent_ratifier/source are reserved-inactive", CONTRACT))
    if _normalize_token(rec.get("operating_mode", "")) not in OPERATING_MODES:
        errors.append(make_error(CODE_MODE, path, _pointer(pre + ("operating_mode",)), "operating_mode must be one of strict, auto, transcendence", CONTRACT))

    if _contains_secret(rec):
        errors.append(make_error(CODE_SECRET, path, _pointer(pre), "reviewer_authority_envelope must not carry secret/credential values; actor is a login name, never a token", CONTRACT))
    return errors


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_MECHANIC,
        CODE_BINDING,
        CODE_ROLE,
        CODE_MODE,
        CODE_SECRET,
        CODE_NO_INLINE,
        CODE_CAPABILITY,
        CODE_SELF_REVIEW,
    ],
)
def run_reviewer_authority_envelope(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in _iter_scanned_files(paths):
        errors.extend(validate_reviewer_authority_envelope_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
