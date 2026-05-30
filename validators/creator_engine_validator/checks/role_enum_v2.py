"""v2 role-enum and privileged-floor enforcement (G2.001.2).

Realizes two required-validation entries from the ``G2.001.0`` foundation
substrate ``required_validation`` map:

* ``VAL-RATIFIER-REJECT`` — ``agent_ratifier`` is schema-present but
  reserved-inactive; any active authority / ratification binding to it is
  rejected.
* ``VAL-PRIVILEGED-FLOOR`` — privileged mutation classes and emergency governed
  override remain Operator-only in every mode; advisory agent roles may review
  and recommend but MUST NOT satisfy privileged ratifier / authority fields.

The check is intentionally scoped to new v2 artifacts under ``specs/v2/`` and to
its bundled ``role-enum-v2`` fixtures so it cannot regress v1 checks. It treats
structured YAML as the authority-bearing surface and avoids flagging descriptive
prose or the allowed ``agent_ratifier`` reserved-inactive enum placeholder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "role_enum_v2"
CONTRACT = "specs/v2/001-v2-foundation-substrate/spec.ce.yml#role_enum_v2"

CODE_AGENT_RATIFIER_ACTIVE = "VAL-RATIFIER-REJECT-AGENT-RATIFIER-ACTIVE"
CODE_PRIVILEGED_FLOOR_AGENT = "VAL-PRIVILEGED-FLOOR-AGENT-DELEGATION"
CODE_INVALID = "role_enum_v2_invalid_record"

AGENT_RATIFIER = "agent_ratifier"
AGENT_ROLES = frozenset({"agent_reviewer", AGENT_RATIFIER})
PRIVILEGED_MUTATION_CLASSES = frozenset(
    {"deploy", "governance", "identity", "security", "attestation", "redaction"}
)
INACTIVE_MARKERS = frozenset(
    {
        "reserved_inactive",
        "reserved-inactive",
        "inactive",
        "schema_present_only",
        "schema-present-only",
        "none",
        "no_active_binding",
        "no-active-binding",
    }
)
ADVISORY_MARKERS = frozenset({"advisory_only", "advisory-only", "review_only", "review-only"})

ROLE_BINDING_KEYS = frozenset(
    {
        "role",
        "roles",
        "ratifier",
        "ratifiers",
        "required_ratifier_role",
        "required_ratifier_roles",
        "ratifier_role",
        "ratifier_roles",
        "authorized_role",
        "authorized_roles",
        "authority_role",
        "authority_roles",
        "delegated_role",
        "delegated_roles",
        "active_role",
        "active_roles",
        "runtime_role",
        "runtime_roles",
        "actor_role",
        "actor_roles",
        "human_authority_role",
        "human_authority_roles",
        "machine_role",
        "machine_roles",
        "required_authority_role",
        "required_authority_roles",
        "approver_role",
        "approver_roles",
        "override_role",
        "override_roles",
    }
)

RATIFYING_OR_AUTHORITY_KEY_FRAGMENTS = frozenset(
    {
        "ratifier",
        "authority",
        "authorized",
        "delegated",
        "required",
        "approver",
        "override",
        "ratification",
        "policy",
        "ledger",
        "runtime",
        "active",
    }
)

_SCANNED_SUFFIXES = {".yml", ".yaml"}


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _is_role_binding_key(key: str) -> bool:
    norm = _normalize_token(key)
    return (
        norm in ROLE_BINDING_KEYS
        or norm.endswith("_role")
        or norm.endswith("_roles")
        or norm == "authority"
        or norm.endswith("_authority")
        or norm == "roles"
    )


def _is_authority_binding_key(key: str) -> bool:
    norm = _normalize_token(key)
    return any(fragment in norm for fragment in RATIFYING_OR_AUTHORITY_KEY_FRAGMENTS)


def _path_in_scope(path: Path) -> bool:
    parts = path.parts
    for i in range(len(parts) - 1):
        if parts[i] == "specs" and parts[i + 1] == "v2":
            return True
    return "role-enum-v2" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def iter_scanned_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(
                p for p in path.rglob("*") if p.is_file() and p.suffix in _SCANNED_SUFFIXES
            )
        else:
            candidates = []
        for candidate in candidates:
            if candidate.suffix not in _SCANNED_SUFFIXES or _is_tmp_artifact(candidate):
                continue
            if not _path_in_scope(candidate):
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


def _pointer(parts: tuple[str, ...]) -> str:
    rendered = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _iter_scalar_tokens(value: Any, parts: tuple[str, ...], owner: Any) -> Iterable[tuple[str, tuple[str, ...], Any]]:
    if isinstance(value, str):
        yield value, parts, owner
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key), (*parts, str(key)), value
            yield from _iter_scalar_tokens(child, (*parts, str(key)), child if isinstance(child, dict) else value)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_scalar_tokens(child, (*parts, str(index)), child if isinstance(child, dict) else owner)


def _iter_role_tokens(value: Any, parts: tuple[str, ...]) -> Iterable[tuple[str, tuple[str, ...], Any]]:
    yield from _iter_scalar_tokens(value, parts, value)


def _subtree_has_marker(value: Any, markers: frozenset[str]) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in markers
    if isinstance(value, dict):
        return any(_subtree_has_marker(child, markers) for child in value.values())
    if isinstance(value, list):
        return any(_subtree_has_marker(child, markers) for child in value)
    return False


def _is_reserved_ratifier_placeholder(owner: Any) -> bool:
    if isinstance(owner, str):
        return _normalize_token(owner) in INACTIVE_MARKERS
    if not isinstance(owner, dict):
        return False
    text_values = {_normalize_token(v) for v in owner.values() if isinstance(v, str)}
    if not (text_values & INACTIVE_MARKERS):
        return False
    # Reserved placeholders may document the future milestone, but must not carry active authority.
    authority = owner.get("authority") or owner.get("authority_binding") or owner.get("active_authority")
    if authority is None:
        return True
    return _normalize_token(authority) in INACTIVE_MARKERS


def _agent_ratifier_errors(value: Any, path: Path, parts: tuple[str, ...]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_parts = (*parts, str(key))
            if _normalize_token(key) == AGENT_RATIFIER and not _is_reserved_ratifier_placeholder(child):
                errors.append(
                    make_error(
                        CODE_AGENT_RATIFIER_ACTIVE,
                        path,
                        _pointer(child_parts),
                        "agent_ratifier is reserved-inactive and MUST NOT be bound to active "
                        "authority, policy, runtime, ledger, or ratification acts in v2 "
                        "(FR-014 / RV2-001-014)",
                        CONTRACT,
                    )
                )
            if _is_role_binding_key(str(key)):
                for token, token_parts, owner in _iter_role_tokens(child, child_parts):
                    if _normalize_token(token) == AGENT_RATIFIER and not _is_reserved_ratifier_placeholder(owner):
                        errors.append(
                            make_error(
                                CODE_AGENT_RATIFIER_ACTIVE,
                                path,
                                _pointer(token_parts),
                                "agent_ratifier is reserved-inactive and MUST NOT be bound to active "
                                "authority, policy, runtime, ledger, or ratification acts in v2 "
                                "(FR-014 / RV2-001-014)",
                                CONTRACT,
                            )
                        )
            errors.extend(_agent_ratifier_errors(child, path, child_parts))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_agent_ratifier_errors(child, path, (*parts, str(index))))
    return errors


def _contains_privileged_class(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in PRIVILEGED_MUTATION_CLASSES
    if isinstance(value, dict):
        return any(_contains_privileged_class(key) or _contains_privileged_class(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_privileged_class(child) for child in value)
    return False


def _is_privileged_context(node: dict[Any, Any]) -> bool:
    for key, child in node.items():
        norm_key = _normalize_token(key)
        if norm_key in {"privileged", "privileged_class", "privileged_classes"} and child is True:
            return True
        if "mutation_class" in norm_key and _contains_privileged_class(child):
            return True
        if norm_key in {"emergency_override", "emergency_governed_override"}:
            if isinstance(child, str):
                return _normalize_token(child) not in {"operator_only", "operator-only"}
            return True
    return False


def _role_token_is_agent(token: str) -> bool:
    norm = _normalize_token(token)
    return norm in AGENT_ROLES or norm.startswith("agent_")


def _key_is_agent_role_token(key: str) -> bool:
    norm = _normalize_token(key)
    return norm in AGENT_ROLES or (norm.startswith("agent_") and norm.count("_") == 1)


def _advisory_reviewer_context(parts: tuple[str, ...], owner: Any) -> bool:
    path_text = "/".join(_normalize_token(part) for part in parts)
    if "reviewer" not in path_text:
        return False
    return _subtree_has_marker(owner, ADVISORY_MARKERS)


def _privileged_floor_errors(value: Any, path: Path, parts: tuple[str, ...]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, dict):
        evaluate_current = not (parts and _normalize_token(parts[-1]) == "role_enum_v2")
        if evaluate_current and _is_privileged_context(value):
            for key, child in value.items():
                child_parts = (*parts, str(key))
                norm_key = _normalize_token(key)
                if "reviewer" in norm_key and _subtree_has_marker(value, ADVISORY_MARKERS):
                    continue
                if _key_is_agent_role_token(str(key)):
                    if _normalize_token(key) == AGENT_RATIFIER and _is_reserved_ratifier_placeholder(child):
                        continue
                    errors.append(
                        make_error(
                            CODE_PRIVILEGED_FLOOR_AGENT,
                            path,
                            _pointer(child_parts),
                            "privileged mutation classes and emergency governed override remain "
                            "Operator-only; agent roles may not satisfy privileged ratifier or "
                            "authority fields (FR-015 / RV2-001-015)",
                            CONTRACT,
                        )
                    )
                    continue
                if not (_is_role_binding_key(str(key)) or _is_authority_binding_key(str(key))):
                    continue
                for token, token_parts, owner in _iter_role_tokens(child, child_parts):
                    if not _role_token_is_agent(token):
                        continue
                    if _advisory_reviewer_context(token_parts, owner):
                        continue
                    errors.append(
                        make_error(
                            CODE_PRIVILEGED_FLOOR_AGENT,
                            path,
                            _pointer(token_parts),
                            "privileged mutation classes and emergency governed override remain "
                            "Operator-only; agent roles may not satisfy privileged ratifier or "
                            "authority fields (FR-015 / RV2-001-015)",
                            CONTRACT,
                        )
                    )
        for key, child in value.items():
            errors.extend(_privileged_floor_errors(child, path, (*parts, str(key))))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_privileged_floor_errors(child, path, (*parts, str(index))))
    return errors


def validate_file(path: Path) -> list[ValidationError]:
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(CODE_INVALID, path, "", str(exc), CONTRACT)]
    errors: list[ValidationError] = []
    errors.extend(_agent_ratifier_errors(data, path, ()))
    errors.extend(_privileged_floor_errors(data, path, ()))
    return errors


@register(CHECK_NAME, [CODE_AGENT_RATIFIER_ACTIVE, CODE_PRIVILEGED_FLOOR_AGENT, CODE_INVALID])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in iter_scanned_files(paths):
        errors.extend(validate_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
