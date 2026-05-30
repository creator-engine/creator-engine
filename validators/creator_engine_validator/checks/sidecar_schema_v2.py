"""v2 spec.ce.yml sidecar schema, no-inline metadata, and risk coverage checks.

G2.001.3 realizes two required-validation entries from the v2 foundation
substrate sidecar:

* ``VAL-SIDECAR-NO-INLINE`` — CE-specific metadata must live in ``*.ce.yml``
  sidecars/crosswalk/ADRs, not in standard Spec Kit Markdown metadata blocks.
* ``VAL-RISK-COVERAGE`` — risk-bearing specs require a non-empty
  ``risk_inventory``; every risk maps to required validation, and every
  required-validation entry maps back to a declared risk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "sidecar_schema_v2"
CONTRACT = "specs/v2/001-v2-foundation-substrate/spec.ce.yml#sidecar_schema_v2"
SCHEMA_PATH = "schemas/spec-ce-sidecar.schema.yaml"

CODE_INLINE_METADATA = "VAL-SIDECAR-NO-INLINE"
CODE_RISK_COVERAGE = "VAL-RISK-COVERAGE"
CODE_SCHEMA = "VAL-SIDECAR-SCHEMA"

_SCANNED_YAML_SUFFIXES = {".yml", ".yaml"}
_SCANNED_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_RISK_BEARING_MUTATION_CLASSES = {
    "governance",
    "identity",
    "security",
    "deploy",
    "attestation",
    "redaction",
    "state-boundary",
    "migration",
    "privileged-class",
}
_CE_METADATA_KEYS = {
    "authority_basis",
    "ce_metadata_kind",
    "controller_decidable_decisions",
    "crosswalk_ref",
    "hermes_write_freeze",
    "importer_contract",
    "migrated_v1_default_mode",
    "no_destructive_v1_removal",
    "operating_mode_relevance",
    "preserved_floors",
    "required_validation",
    "risk_inventory",
    "role_constraints",
    "role_enum_v2",
    "schema_status",
    "state_boundary",
    "terminology_canon",
}


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace("_", "-")


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _path_in_scope(path: Path) -> bool:
    parts = path.parts
    for i in range(len(parts) - 1):
        if parts[i] == "specs" and parts[i + 1] == "v2":
            return True
    return "sidecar-schema-v2" in parts


def _is_spec_ce_sidecar(path: Path) -> bool:
    return path.name == "spec.ce.yml"


def iter_spec_sidecars(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(p for p in path.rglob("spec.ce.yml") if p.is_file())
        else:
            candidates = []
        for candidate in candidates:
            if candidate.suffix not in _SCANNED_YAML_SUFFIXES or _is_tmp_artifact(candidate):
                continue
            if not _is_spec_ce_sidecar(candidate) or not _path_in_scope(candidate):
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def iter_markdown_files(paths: Iterable[Path]) -> list[Path]:
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
            if candidate.suffix.lower() not in _SCANNED_MARKDOWN_SUFFIXES or _is_tmp_artifact(candidate):
                continue
            if not _path_in_scope(candidate):
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _pointer(*parts: Any) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")}


def _list_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        return [value]
    return []


def _risk_bearing(data: dict[str, Any]) -> bool:
    if data.get("risk_inventory") is not None:
        return True
    authority = data.get("authority")
    if isinstance(authority, dict):
        if authority.get("privileged") is True:
            return True
        mutation_classes = {_normalize_token(v) for v in _list_values(authority.get("mutation_classes"))}
        if mutation_classes & _RISK_BEARING_MUTATION_CLASSES:
            return True
    requirements = data.get("requirements")
    if isinstance(requirements, list):
        return any(isinstance(req, dict) and _list_values(req.get("risk_refs")) for req in requirements)
    return False


def _validate_risk_coverage(data: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    risks = data.get("risk_inventory")
    validations = data.get("required_validation")
    requirements = data.get("requirements")

    if not _risk_bearing(data):
        return errors
    if not isinstance(risks, list) or not risks:
        errors.append(
            make_error(
                CODE_RISK_COVERAGE,
                path,
                "/risk_inventory",
                "risk-bearing v2 spec sidecars MUST declare a non-empty risk_inventory",
                CONTRACT,
            )
        )
        return errors
    if not isinstance(validations, list) or not validations:
        errors.append(
            make_error(
                CODE_RISK_COVERAGE,
                path,
                "/required_validation",
                "risk-bearing v2 spec sidecars MUST declare required_validation entries",
                CONTRACT,
            )
        )
        return errors

    risk_ids = _ids(risks)
    validation_ids = _ids(validations)
    referenced_validation_ids: set[str] = set()

    for index, risk in enumerate(risks):
        if not isinstance(risk, dict):
            continue
        risk_id = str(risk.get("id") or f"<risk:{index}>")
        refs = _list_values(risk.get("required_validation_refs"))
        if not refs:
            errors.append(
                make_error(
                    CODE_RISK_COVERAGE,
                    path,
                    _pointer("risk_inventory", index, "required_validation_refs"),
                    f"risk {risk_id} MUST map to at least one required_validation entry",
                    CONTRACT,
                )
            )
        for ref in refs:
            referenced_validation_ids.add(ref)
            if ref not in validation_ids:
                errors.append(
                    make_error(
                        CODE_RISK_COVERAGE,
                        path,
                        _pointer("risk_inventory", index, "required_validation_refs"),
                        f"risk {risk_id} references missing required_validation id {ref}",
                        CONTRACT,
                    )
                )

    for index, validation in enumerate(validations):
        if not isinstance(validation, dict):
            continue
        validation_id = validation.get("id")
        if validation_id and str(validation_id) not in referenced_validation_ids:
            errors.append(
                make_error(
                    CODE_RISK_COVERAGE,
                    path,
                    _pointer("required_validation", index, "id"),
                    f"required_validation {validation_id} is not referenced by any declared risk",
                    CONTRACT,
                )
            )

    if isinstance(requirements, list):
        for index, req in enumerate(requirements):
            if not isinstance(req, dict):
                continue
            for ref in _list_values(req.get("risk_refs")):
                if ref not in risk_ids:
                    errors.append(
                        make_error(
                            CODE_RISK_COVERAGE,
                            path,
                            _pointer("requirements", index, "risk_refs"),
                            f"requirement {req.get('id', index)} references missing risk id {ref}",
                            CONTRACT,
                        )
                    )
    return errors


def validate_spec_sidecar(path: Path) -> list[ValidationError]:
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(CODE_SCHEMA, path, "", str(exc), SCHEMA_PATH)]
    if not isinstance(data, dict):
        return [make_error(CODE_SCHEMA, path, "/", "spec.ce.yml sidecar must be a YAML mapping", SCHEMA_PATH)]

    errors = validate_with_schema(data, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=SCHEMA_PATH)
    errors.extend(_validate_risk_coverage(data, path))
    return errors


def validate_markdown_file(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [make_error(CODE_INLINE_METADATA, path, "", f"failed to read markdown: {exc}", CONTRACT)]

    def reject_inline_key(key: str, line_no: int) -> None:
        if key in _CE_METADATA_KEYS:
            errors.append(
                make_error(
                    CODE_INLINE_METADATA,
                    path,
                    f"/line/{line_no}",
                    f"CE metadata key {key!r} belongs in *.ce.yml sidecars/crosswalk/ADRs, not standard Spec Kit Markdown",
                    CONTRACT,
                )
            )

    if lines and lines[0].strip() == "---":
        for line_no, line in enumerate(lines[1:], start=2):
            stripped = line.strip()
            if stripped in {"---", "..."}:
                break
            key = stripped.split(":", 1)[0].strip() if ":" in stripped else ""
            reject_inline_key(key, line_no)

    in_fence = False
    fence_is_yaml = False
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
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
        key = stripped.split(":", 1)[0].strip() if ":" in stripped else ""
        reject_inline_key(key, line_no)
    return errors


@register(CHECK_NAME, [CODE_INLINE_METADATA, CODE_RISK_COVERAGE, CODE_SCHEMA])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for sidecar in iter_spec_sidecars(paths):
        errors.extend(validate_spec_sidecar(sidecar))
    for markdown in iter_markdown_files(paths):
        errors.extend(validate_markdown_file(markdown))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
