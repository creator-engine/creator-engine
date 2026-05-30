"""G2.002.0 operating-mode policy substrate validator.

The check intentionally defines only the docs/schema/validator substrate for the
future operating-mode runtime. It does not propagate operating mode into lane,
ledger, queue, connector, or assignment-envelope runtime records; those remain
G2.002.1+ work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "operating_mode_policy"
CONTRACT = "specs/v2/002-operating-mode-substrate/spec.ce.yml#operating_mode_policy"
SCHEMA_PATH = "schemas/operating-mode-policy.schema.yaml"

CODE_MODE_ENUM = "VAL-OPERATING-MODE-ENUM"
CODE_V1_DEFAULT = "VAL-AUTONOMY-DEFAULT"
CODE_AUTO_REQUIRES_POLICY = "VAL-AUTO-REQUIRES-OPERATOR-POLICY"
CODE_TRANSCENDENCE_REQUIRES_POLICY = "VAL-TRANSCENDENCE-REQUIRES-OPERATOR-POLICY"
CODE_PRIVILEGED_FLOOR_AGENT = "VAL-PRIVILEGED-FLOOR-AGENT-DELEGATION"
CODE_AGENT_RATIFIER_ACTIVE = "VAL-RATIFIER-REJECT-AGENT-RATIFIER-ACTIVE"
CODE_EMERGENCY_OVERRIDE = "VAL-EMERGENCY-OVERRIDE-OPERATOR-ONLY"
CODE_RESERVED_AUTONOMY_ACTIVE = "VAL-RATIFIER-REJECT-RESERVED-AUTONOMY-ACTIVE"
CODE_NO_INLINE = "VAL-OPERATING-MODE-NO-INLINE"
CODE_SCHEMA = "VAL-OPERATING-MODE-SCHEMA"
CODE_RISK_COVERAGE = "VAL-OPERATING-MODE-RISK-COVERAGE"

OPERATING_MODES = frozenset({"strict", "auto", "transcendence"})
AUTONOMY_CLASSES = frozenset(
    {
        "manual",
        "supervised",
        "delegated_non_privileged",
        "operator_ratified_privileged",
        "reserved_future_agent_ratification",
    }
)
PRIVILEGED_CLASSES = frozenset({"deploy", "governance", "identity", "security", "attestation", "redaction"})
INACTIVE_MARKERS = frozenset({"reserved_inactive", "reserved-inactive", "inactive", "none", "no_active_binding", "no-active-binding"})
OPERATOR_ONLY_MARKERS = frozenset({"operator_only", "operator-only", "operator"})
_SCANNED_YAML_SUFFIXES = {".yml", ".yaml"}
_SCANNED_MARKDOWN_SUFFIXES = {".md", ".markdown"}


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _path_in_scope(path: Path) -> bool:
    parts = path.parts
    for i in range(len(parts) - 2):
        if parts[i] == "specs" and parts[i + 1] == "v2" and parts[i + 2] == "002-operating-mode-substrate":
            return True
    return "operating-mode-policy" in parts


def iter_scanned_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        else:
            candidates = []
        for candidate in candidates:
            if _is_tmp_artifact(candidate) or not _path_in_scope(candidate):
                continue
            if candidate.suffix.lower() not in (_SCANNED_YAML_SUFFIXES | _SCANNED_MARKDOWN_SUFFIXES):
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


def _err(code: str, path: Path, parts: tuple[Any, ...], message: str, contract: str = CONTRACT) -> ValidationError:
    return make_error(code, path, _pointer(parts), message, contract)


def _subtree_has_token(value: Any, token: str) -> bool:
    wanted = _normalize_token(token)
    if isinstance(value, str):
        return _normalize_token(value) == wanted
    if isinstance(value, dict):
        return any(_normalize_token(k) == wanted or _subtree_has_token(v, token) for k, v in value.items())
    if isinstance(value, list):
        return any(_subtree_has_token(v, token) for v in value)
    return False


def _subtree_has_active_agent_ratifier(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalize_token(key) == "agent_ratifier":
                if not _is_reserved_agent_ratifier_placeholder(child):
                    return True
            if _subtree_has_active_agent_ratifier(child):
                return True
    elif isinstance(value, list):
        return any(_subtree_has_active_agent_ratifier(child) for child in value)
    elif isinstance(value, str):
        return _normalize_token(value) == "agent_ratifier"
    return False


def _is_reserved_agent_ratifier_placeholder(value: Any) -> bool:
    if not isinstance(value, dict):
        return _normalize_token(value) in INACTIVE_MARKERS
    status = _normalize_token(value.get("status", ""))
    active = value.get("active_authority", value.get("authority_binding", value.get("authority")))
    return status in INACTIVE_MARKERS and (active is None or _normalize_token(active) in INACTIVE_MARKERS)


def _operator_policy_pointer_present(policy: dict[str, Any]) -> bool:
    candidates = [
        policy.get("operator_policy_ref"),
        policy.get("operator_ratified_policy_ref"),
        policy.get("ratified_policy_ref"),
        policy.get("activation_record"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return True
        if isinstance(candidate, dict):
            values = [str(v).strip() for v in candidate.values() if v is not None]
            if values and any("operator" in k or "ratified" in k or k in {"sha256", "path", "prompt", "ratified_prompt"} for k in candidate):
                return True
    return False


def _validate_policy(policy: Any, path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if not isinstance(policy, dict):
        return [_err(CODE_SCHEMA, path, ("operating_mode_policy",), "operating_mode_policy must be a YAML mapping", SCHEMA_PATH)]

    try:
        errors.extend(validate_with_schema(policy, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=SCHEMA_PATH))
    except Exception as exc:  # keep validator fail-closed when jsonschema or schema loading breaks
        errors.append(_err(CODE_SCHEMA, path, ("operating_mode_policy",), f"schema validation failed: {exc}", SCHEMA_PATH))

    mode = _normalize_token(policy.get("operating_mode", ""))
    if mode not in OPERATING_MODES:
        errors.append(_err(CODE_MODE_ENUM, path, ("operating_mode_policy", "operating_mode"), "operating_mode must be one of strict, auto, transcendence"))

    autonomy_class = _normalize_token(policy.get("autonomy_class", ""))
    if autonomy_class and autonomy_class not in AUTONOMY_CLASSES:
        errors.append(_err(CODE_SCHEMA, path, ("operating_mode_policy", "autonomy_class"), "autonomy_class is not a recognized G2.002.0 value", SCHEMA_PATH))
    if autonomy_class == "reserved_future_agent_ratification":
        errors.append(
            _err(
                CODE_RESERVED_AUTONOMY_ACTIVE,
                path,
                ("operating_mode_policy", "autonomy_class"),
                "reserved_future_agent_ratification is a schema-visible placeholder and MUST NOT be active autonomy",
            )
        )

    migrated_default = _normalize_token(policy.get("default_for_migrated_v1_tenants", "strict"))
    if migrated_default != "strict":
        errors.append(_err(CODE_V1_DEFAULT, path, ("operating_mode_policy", "default_for_migrated_v1_tenants"), "migrated v1 tenants must default to strict"))

    if mode == "auto" and not _operator_policy_pointer_present(policy):
        errors.append(_err(CODE_AUTO_REQUIRES_POLICY, path, ("operating_mode_policy",), "auto mode requires an Operator-ratified policy pointer"))
    if mode == "transcendence" and not _operator_policy_pointer_present(policy):
        errors.append(_err(CODE_TRANSCENDENCE_REQUIRES_POLICY, path, ("operating_mode_policy",), "transcendence mode requires an Operator-ratified policy pointer"))

    floor = policy.get("privileged_floor")
    if isinstance(floor, dict):
        required = _normalize_token(floor.get("required_ratifier_role", ""))
        classes = {_normalize_token(v) for v in floor.get("privileged_mutation_classes", []) if v is not None}
        if (classes & PRIVILEGED_CLASSES or classes) and required != "operator":
            errors.append(
                _err(
                    CODE_PRIVILEGED_FLOOR_AGENT,
                    path,
                    ("operating_mode_policy", "privileged_floor", "required_ratifier_role"),
                    "privileged mutation classes require required_ratifier_role: operator",
                )
            )
        reviewer = floor.get("agent_reviewer")
        if isinstance(reviewer, str) and _normalize_token(reviewer) not in {"advisory_only", "advisory_only".replace("_", "-")}:  # normalized handles both
            errors.append(
                _err(
                    CODE_PRIVILEGED_FLOOR_AGENT,
                    path,
                    ("operating_mode_policy", "privileged_floor", "agent_reviewer"),
                    "agent_reviewer may be advisory_only only for privileged floors",
                )
            )
        ratifier = floor.get("agent_ratifier")
        if ratifier is not None and not _is_reserved_agent_ratifier_placeholder(ratifier):
            errors.append(
                _err(
                    CODE_AGENT_RATIFIER_ACTIVE,
                    path,
                    ("operating_mode_policy", "privileged_floor", "agent_ratifier"),
                    "agent_ratifier is reserved-inactive and MUST NOT carry active authority",
                )
            )
    else:
        errors.append(_err(CODE_PRIVILEGED_FLOOR_AGENT, path, ("operating_mode_policy", "privileged_floor"), "operating_mode_policy requires a privileged_floor mapping"))

    if _subtree_has_active_agent_ratifier(policy):
        errors.append(_err(CODE_AGENT_RATIFIER_ACTIVE, path, ("operating_mode_policy",), "agent_ratifier MUST NOT appear in active authority, ratifier, approval, override, runtime, or policy bindings"))

    emergency = policy.get("emergency_override")
    if emergency is not None and _normalize_token(emergency) not in OPERATOR_ONLY_MARKERS:
        errors.append(_err(CODE_EMERGENCY_OVERRIDE, path, ("operating_mode_policy", "emergency_override"), "emergency override must be Operator-only"))

    risk = policy.get("risk_coverage") or policy.get("risk_inventory")
    if risk is None:
        errors.append(_err(CODE_RISK_COVERAGE, path, ("operating_mode_policy", "risk_coverage"), "operating mode policy must declare risk coverage / validation refs"))

    return errors


def validate_markdown_file(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [_err(CODE_NO_INLINE, path, (), f"failed to read markdown: {exc}")]

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
                marker = stripped[3:].strip().lower()
                in_fence = True
                fence_is_yaml = marker in {"yaml", "yml"}
            else:
                in_fence = False
                fence_is_yaml = False
            continue
        if not fence_is_yaml:
            continue
        if stripped.split(":", 1)[0].strip() == "operating_mode_policy":
            errors.append(_err(CODE_NO_INLINE, path, ("line", line_no), "operating_mode_policy belongs in spec.ce.yml sidecars, not Spec Kit Markdown"))
    return errors


def validate_file(path: Path) -> list[ValidationError]:
    if path.suffix.lower() in _SCANNED_MARKDOWN_SUFFIXES:
        return validate_markdown_file(path)
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [_err(CODE_SCHEMA, path, (), str(exc), SCHEMA_PATH)]
    if not isinstance(data, dict):
        return [_err(CODE_SCHEMA, path, (), "operating mode policy file must be a YAML mapping", SCHEMA_PATH)]
    policy = data.get("operating_mode_policy")
    if policy is None:
        return [_err(CODE_MODE_ENUM, path, ("operating_mode_policy",), "scoped G2.002.0 policy files must declare operating_mode_policy")]
    return _validate_policy(policy, path)


@register(
    CHECK_NAME,
    [
        CODE_MODE_ENUM,
        CODE_V1_DEFAULT,
        CODE_AUTO_REQUIRES_POLICY,
        CODE_TRANSCENDENCE_REQUIRES_POLICY,
        CODE_PRIVILEGED_FLOOR_AGENT,
        CODE_AGENT_RATIFIER_ACTIVE,
        CODE_EMERGENCY_OVERRIDE,
        CODE_RESERVED_AUTONOMY_ACTIVE,
        CODE_NO_INLINE,
        CODE_SCHEMA,
        CODE_RISK_COVERAGE,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in iter_scanned_files(paths):
        errors.extend(validate_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
